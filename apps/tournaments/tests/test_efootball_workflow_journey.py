"""eFootball pilot journeys (solo, single elimination), service level.

The planned pilot is FREE ENTRY, so the free flow is the primary acceptance journey; the
DeltaCoin entry-fee flow is kept as paid-flow coverage. Everything runs on a disposable
database with synthetic users. Lifecycle transitions are the ordinary guarded ones (no
``force``): the only fixture shortcut is moving ``tournament_start`` into the past, which
simulates the clock reaching the scheduled start. In-app notifications and WebSocket
broadcasts run through their normal test backends; email goes to the locmem outbox and any
outbound HTTP raises (see ``isolation``).
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.games.models.game import Game
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Match, Payment, Registration, Tournament
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import UserProfile

pytestmark = pytest.mark.django_db
User = get_user_model()
FEE = 100
START_BALANCE = 500


@pytest.fixture(autouse=True)
def isolation(settings):
    """No real email or outbound HTTP (payment providers, webhooks) can leave the test."""
    assert settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend'
    with patch('requests.sessions.Session.request', side_effect=AssertionError('outbound HTTP attempted')):
        yield


def _user(name):
    user = User.objects.create_user(username=name, email=f'{name}@example.test')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    DeltaCrownWallet.objects.create(profile=profile, cached_balance=START_BALANCE)
    return user


def _make_world(paid):
    organizer = _user('ef-organizer')
    players = [_user(f'ef-player-{n}') for n in range(1, 5)]
    outsider = _user('ef-outsider')
    game = Game.objects.create(
        name='eFootball', slug='efootball', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now()
    fee = {'has_entry_fee': True, 'entry_fee_amount': Decimal(FEE), 'payment_methods': [Tournament.DELTACOIN]} if paid else {}
    tournament = Tournament.objects.create(
        name='eFootball Pilot Cup', slug='efootball-pilot-cup', organizer=organizer, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2), tournament_end=now + timedelta(days=3),
        status=Tournament.DRAFT, **fee,
    )
    return organizer, players, outsider, tournament


@pytest.fixture
def world():
    """Free-entry pilot tournament (the primary journey)."""
    return _make_world(paid=False)


@pytest.fixture
def paid_world():
    """Same tournament with a 100 DeltaCoin entry fee (paid-flow coverage)."""
    return _make_world(paid=True)


def _to(tournament, status, actor):
    """Ordinary, guarded lifecycle transition (guards are NOT bypassed)."""
    return TournamentLifecycleService.transition(tournament.id, status, actor=actor)


def _register(tournament, user):
    return RegistrationService.register_participant(
        tournament.id, user, registration_data={'game_id': f'{user.username}-efootball'},
    )


def _get(match):
    return Match.objects.get(pk=match.pk)


def _confirm_entry(reg, user, organizer, paid):
    """Paid: the player pays with DeltaCoin. Free: registration is pending until the organizer approves."""
    if paid:
        RegistrationService.pay_with_deltacoin(reg.id, user)
    else:
        assert reg.status == Registration.PENDING
        RegistrationService.approve_registration(reg, organizer)
    reg.refresh_from_db()
    assert reg.status == Registration.CONFIRMED
    return reg


def _play(match, organizer, *, p1_wins):
    """Check both participants in, start, submit as a participant, confirm as organizer."""
    match = _get(match)
    for pid in (match.participant1_id, match.participant2_id):
        MatchService.check_in_participant(_get(match), pid)
    MatchService.transition_to_live(_get(match))
    scores = (2, 1) if p1_wins else (1, 2)
    MatchService.submit_result(_get(match), match.participant1_id, scores[0], scores[1])
    confirmed = MatchService.confirm_result(_get(match), organizer.id)
    assert confirmed.state == Match.COMPLETED
    return confirmed.winner_id


def _start_time_reached(tournament):
    """Fixture shortcut (not a transition bypass): the scheduled start time has now passed."""
    Tournament.objects.filter(pk=tournament.pk).update(tournament_start=timezone.now() - timedelta(minutes=1))


def _reach_published_bracket(world, paid=False):
    """Publish, open registration, register + confirm 4 players, close, go live, publish bracket."""
    organizer, players, _outsider, tournament = world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    registrations = [_confirm_entry(_register(tournament, p), p, organizer, paid) for p in players]
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    _start_time_reached(tournament)
    _to(tournament, Tournament.LIVE, organizer)
    TOCBracketsService.generate_bracket(tournament, organizer, {})
    TOCBracketsService.publish_bracket(tournament, organizer)
    round_one = list(Match.objects.filter(tournament=tournament, round_number=1).order_by('match_number'))
    return registrations, round_one


def _play_whole_tournament(organizer, tournament, round_one):
    winners = [_play(m, organizer, p1_wins=True) for m in round_one]
    final = Match.objects.get(tournament=tournament, round_number=2)
    assert {final.participant1_id, final.participant2_id} == set(winners)  # correct next opponents
    assert Match.objects.filter(tournament=tournament, round_number=2).count() == 1
    champion = _play(final, organizer, p1_wins=True)
    assert champion in winners
    tournament.refresh_from_db()
    assert tournament.status == Tournament.COMPLETED  # completes through the normal pipeline
    return champion


# -- primary pilot journey: FREE entry -----------------------------------------

def test_free_entry_pilot_journey(world):
    organizer, players, outsider, tournament = world
    assert not tournament.has_entry_fee

    registrations, round_one = _reach_published_bracket(world, paid=False)

    # No financial effects at all in a free tournament
    assert DeltaCrownTransaction.objects.count() == 0
    assert Payment.objects.count() == 0
    assert all(DeltaCrownWallet.objects.get(profile__user=p).cached_balance == START_BALANCE for p in players)

    # Duplicate registration is rejected and creates nothing
    with pytest.raises(ValidationError):
        _register(tournament, players[0])
    assert Registration.objects.filter(tournament=tournament, user=players[0]).count() == 1

    # Every confirmed player is seeded exactly once
    assert len(round_one) == 2
    seeded = [pid for m in round_one for pid in (m.participant1_id, m.participant2_id)]
    assert sorted(seeded) == sorted(r.user_id for r in registrations)

    _play_whole_tournament(organizer, tournament, round_one)

    # Still nothing financial after the whole tournament; the outsider never took part
    assert DeltaCrownTransaction.objects.count() == 0 and Payment.objects.count() == 0
    assert outsider.id not in seeded
    assert DeltaCrownWallet.objects.get(profile__user=outsider).cached_balance == START_BALANCE
    assert isinstance(mail.outbox, list)  # locmem only; nothing external


def test_free_entry_registration_rules(world):
    organizer, players, outsider, tournament = world
    with pytest.raises(ValidationError):  # still a draft
        _register(tournament, outsider)
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)

    first = _register(tournament, players[0])
    assert first.status == Registration.PENDING  # free entry still needs organizer approval
    with pytest.raises(ValidationError):  # same in-game ID used by a different player
        RegistrationService.register_participant(
            tournament.id, players[1], registration_data={'game_id': first.registration_data['game_id']},
        )
    with pytest.raises(ValidationError):  # same player twice
        _register(tournament, players[0])

    # Unapproved registrations do not count: the guard keeps registration open
    _register(tournament, players[1])
    with pytest.raises(ValidationError):
        _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    assert Tournament.objects.get(pk=tournament.pk).status == Tournament.REGISTRATION_OPEN

    # A full tournament waitlists the next player instead of confirming them
    for extra in players[2:]:
        _register(tournament, extra)
    waitlisted = _register(tournament, outsider)
    assert waitlisted.status == Registration.WAITLISTED
    assert DeltaCrownTransaction.objects.count() == 0


def test_lifecycle_guards_apply_without_force(world):
    organizer, players, _outsider, tournament = world
    with pytest.raises(ValidationError):  # cannot skip states
        _to(tournament, Tournament.LIVE, organizer)
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    for player in players:
        _confirm_entry(_register(tournament, player), player, organizer, paid=False)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)

    with pytest.raises(ValidationError):  # scheduled start is still in the future
        _to(tournament, Tournament.LIVE, organizer)
    _start_time_reached(tournament)
    _to(tournament, Tournament.LIVE, organizer)

    TOCBracketsService.generate_bracket(tournament, organizer, {})
    with pytest.raises(ValidationError):  # matches are still incomplete
        _to(tournament, Tournament.COMPLETED, organizer)


def test_waitlisted_player_cannot_be_approved_past_capacity(world):
    """Regression: approve_registration confirmed waitlisted registrations beyond max_participants."""
    organizer, players, outsider, tournament = world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    for player in players:
        _confirm_entry(_register(tournament, player), player, organizer, paid=False)
    waitlisted = _register(tournament, outsider)
    assert waitlisted.status == Registration.WAITLISTED

    with pytest.raises(ValidationError):
        RegistrationService.approve_registration(waitlisted, organizer)
    waitlisted.refresh_from_db()
    assert waitlisted.status == Registration.WAITLISTED
    confirmed = Registration.objects.filter(tournament=tournament, status=Registration.CONFIRMED).count()
    assert confirmed == tournament.max_participants

    # Freeing a slot makes the same approval valid
    Registration.objects.filter(tournament=tournament, user=players[0]).update(status=Registration.CANCELLED)
    RegistrationService.approve_registration(Registration.objects.get(pk=waitlisted.pk), organizer)
    assert Registration.objects.get(pk=waitlisted.pk).status == Registration.CONFIRMED


# -- paid-entry flow (DeltaCoin) is preserved -----------------------------------

def test_paid_entry_journey_to_champion(paid_world):
    organizer, players, _outsider, tournament = paid_world
    registrations, round_one = _reach_published_bracket(paid_world, paid=True)

    assert DeltaCrownTransaction.objects.count() == 4
    assert all(DeltaCrownWallet.objects.get(profile__user=p).cached_balance == START_BALANCE - FEE for p in players)

    with pytest.raises(ValidationError):  # duplicate registration
        _register(tournament, players[0])
    seeded = [pid for m in round_one for pid in (m.participant1_id, m.participant2_id)]
    assert sorted(seeded) == sorted(r.user_id for r in registrations)

    _play_whole_tournament(organizer, tournament, round_one)
    assert DeltaCrownTransaction.objects.count() == 4  # no extra financial effects after play


def test_payment_cannot_be_made_by_someone_else_or_charged_twice(paid_world):
    organizer, players, outsider, tournament = paid_world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    reg = _register(tournament, players[0])

    with pytest.raises(ValidationError):
        RegistrationService.pay_with_deltacoin(reg.id, outsider)
    assert DeltaCrownTransaction.objects.count() == 0

    first = RegistrationService.pay_with_deltacoin(reg.id, players[0])
    second = RegistrationService.pay_with_deltacoin(reg.id, players[0])  # repeated callback
    assert first[1].id == second[1].id
    assert DeltaCrownTransaction.objects.count() == 1
    assert DeltaCrownWallet.objects.get(profile__user=players[0]).cached_balance == START_BALANCE - FEE


def test_failed_payment_write_rolls_back_the_debit(paid_world):
    organizer, players, _outsider, tournament = paid_world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    reg = _register(tournament, players[0])

    with patch('apps.tournaments.services.registration_service.Payment.objects.create',
               side_effect=RuntimeError('db failure after debit')):
        with pytest.raises(RuntimeError):
            RegistrationService.pay_with_deltacoin(reg.id, players[0])

    reg.refresh_from_db()
    assert reg.status != Registration.CONFIRMED
    assert DeltaCrownTransaction.objects.count() == 0
    assert DeltaCrownWallet.objects.get(profile__user=players[0]).cached_balance == START_BALANCE


def test_registration_rejected_after_close_and_cancellation(paid_world):
    organizer, players, outsider, tournament = paid_world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    for player in players[:2]:
        RegistrationService.pay_with_deltacoin(_register(tournament, player).id, player)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    with pytest.raises(ValidationError):  # closed
        _register(tournament, outsider)
    _to(tournament, Tournament.CANCELLED, organizer)
    with pytest.raises(ValidationError):  # cancelled
        _register(tournament, outsider)
    assert not Registration.objects.filter(tournament=tournament, user=outsider).exists()


# -- match integrity (identical for free and paid; free used) --------------------

def test_result_submission_and_confirmation_guards(world):
    organizer, _players, outsider, _tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    match = round_one[0]

    with pytest.raises(ValidationError):  # not started yet
        MatchService.submit_result(_get(match), match.participant1_id, 2, 1)

    for pid in (match.participant1_id, match.participant2_id):
        MatchService.check_in_participant(_get(match), pid)
    MatchService.transition_to_live(_get(match))

    with pytest.raises(ValidationError):  # outsider cannot submit
        MatchService.submit_result(_get(match), outsider.id, 2, 1)
    with pytest.raises(ValidationError):  # no draws
        MatchService.submit_result(_get(match), match.participant1_id, 1, 1)
    with pytest.raises(ValidationError):  # nothing to confirm yet
        MatchService.confirm_result(_get(match), organizer.id)

    MatchService.submit_result(_get(match), match.participant1_id, 2, 1)
    MatchService.confirm_result(_get(match), organizer.id)

    with pytest.raises(ValidationError):  # repeated confirmation
        MatchService.confirm_result(_get(match), organizer.id)
    with pytest.raises(ValidationError):  # submission after completion
        MatchService.submit_result(_get(match), match.participant1_id, 0, 2)
    with pytest.raises(ValidationError):  # cannot cancel a completed match
        MatchService.cancel_match(_get(match), 'late', organizer.id)

    completed = _get(match)
    assert completed.state == Match.COMPLETED and completed.winner_id == match.participant1_id


def test_repeated_advancement_does_not_duplicate_the_next_match(world):
    organizer, _players, _outsider, tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    for m in round_one:
        _play(m, organizer, p1_wins=True)
    assert Match.objects.filter(tournament=tournament, round_number=2).count() == 1

    for m in round_one:  # replayed callbacks / recovery runs
        BracketService.update_bracket_after_match(_get(m))
    assert Match.objects.filter(tournament=tournament, round_number=2).count() == 1


def test_no_play_after_cancellation(world):
    organizer, _players, _outsider, _tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    match = round_one[0]
    MatchService.cancel_match(_get(match), 'organizer cancelled', organizer.id)

    with pytest.raises(ValidationError):
        MatchService.check_in_participant(_get(match), match.participant1_id)
    with pytest.raises(ValidationError):
        MatchService.submit_result(_get(match), match.participant1_id, 2, 1)
    assert _get(match).state == Match.CANCELLED


# -- organizer API authorization and reset guards --------------------------------

def _api(user=None):
    from rest_framework.test import APIClient

    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _post(client, slug, path, payload=None):
    return client.post(f'/api/toc/{slug}/brackets/{path}/', payload or {}, format='json', secure=True)


def test_bracket_generation_api_is_organizer_only(world):
    organizer, players, outsider, tournament = world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    for player in players:
        _confirm_entry(_register(tournament, player), player, organizer, paid=False)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    _start_time_reached(tournament)
    _to(tournament, Tournament.LIVE, organizer)

    for caller in (None, players[0], outsider):  # anonymous, a registered player, a stranger
        response = _post(_api(caller), tournament.slug, 'generate')
        assert response.status_code in (401, 403), (caller, response.status_code)
    assert not Match.objects.filter(tournament=tournament).exists()

    assert _post(_api(organizer), tournament.slug, 'generate').status_code == 201
    assert Match.objects.filter(tournament=tournament, round_number=1).count() == 2


def test_bracket_cannot_be_reset_after_matches_were_played(world):
    organizer, _players, outsider, tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    _play(round_one[0], organizer, p1_wins=True)
    before = Match.objects.filter(tournament=tournament).count()

    assert _post(_api(outsider), tournament.slug, 'reset').status_code in (401, 403)
    blocked = _post(_api(organizer), tournament.slug, 'reset')
    assert blocked.status_code in (403, 409)  # played fixtures need staff force
    forced = _post(_api(organizer), tournament.slug, 'reset', {'force': True})
    assert forced.status_code == 403  # organizers cannot override the gate

    assert Match.objects.filter(tournament=tournament).count() == before
    assert _get(round_one[0]).state == Match.COMPLETED


# -- real HTTP journey (Django test client + DRF client) ------------------------
# The service-level tests above prove the rules; these prove the pages/endpoints a player,
# organizer and stranger actually hit enforce and expose them.

def _web(user=None):
    from django.test import Client

    client = Client()
    if user is not None:
        client.force_login(user)
    return client


def _url(name, slug, **kw):
    from django.urls import reverse

    return reverse(f'tournaments:{name}', kwargs={'slug': slug, **kw})


# game_id + consent + the form's existing required Phone/WhatsApp contact (no new eligibility fields)
REGISTER_FORM = {'game_id': 'ef-player-1-efootball', 'terms_agreed': 'on', 'phone': '01700000000'}


def _open_registration(world):
    organizer, _players, _outsider, tournament = world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    return tournament


def test_http_discovery_and_visibility(world):
    organizer, players, _outsider, tournament = world
    anon = _web()

    # Draft tournaments are not exposed publicly (list or detail)
    assert tournament.name not in anon.get('/tournaments/', secure=True).content.decode()
    assert anon.get(_url('detail', tournament.slug), secure=True).status_code in (403, 404)

    _open_registration(world)
    listing = anon.get('/tournaments/', secure=True)
    assert listing.status_code == 200 and tournament.name in listing.content.decode()
    detail = anon.get(_url('detail', tournament.slug), secure=True)
    assert detail.status_code == 200
    assert _url('register', tournament.slug) in detail.content.decode()  # real registration CTA


def test_http_registration_journey_free_entry(world):
    organizer, players, outsider, tournament = world
    _open_registration(world)
    player = players[0]
    register_url = _url('register', tournament.slug)

    # Anonymous visitor is sent to login with a safe next URL
    redirect = _web().get(register_url, secure=True)
    assert redirect.status_code == 302 and 'next=' in redirect['Location'] and register_url in redirect['Location']

    client = _web(player)
    assert client.get(register_url, secure=True).status_code == 200  # form renders, no payment required
    # Required-field validation: no consent / no game id / no contact creates nothing
    for bad in ({'game_id': 'x', 'phone': '01700000000'}, {'terms_agreed': 'on', 'phone': '01700000000'}, {'game_id': 'x', 'terms_agreed': 'on'}):
        client.post(register_url, bad, secure=True)
    assert not Registration.objects.filter(tournament=tournament, user=player).exists()

    response = client.post(register_url, REGISTER_FORM, secure=True)
    assert response.status_code == 302
    registration = Registration.objects.get(tournament=tournament, user=player)
    assert registration.status == Registration.PENDING  # free entry waits for the organizer
    success = client.get(response['Location'], secure=True)
    assert success.status_code == 200

    # No money moved; duplicate submit creates nothing new
    assert DeltaCrownTransaction.objects.count() == 0 and Payment.objects.count() == 0
    client.post(register_url, REGISTER_FORM, secure=True)
    assert Registration.objects.filter(tournament=tournament, user=player).count() == 1

    # Another player cannot open this registration's success page
    other = _web(players[1]).get(response['Location'], secure=True)
    assert other.status_code in (302, 403, 404)


def test_http_registration_closed_is_refused(world):
    organizer, players, _outsider, tournament = world
    _open_registration(world)
    for early in players[:2]:  # the minimum field is needed before registration can close
        _confirm_entry(_register(tournament, early), early, organizer, paid=False)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    _web(players[2]).post(_url('register', tournament.slug), REGISTER_FORM, secure=True)
    assert not Registration.objects.filter(tournament=tournament, user=players[2]).exists()


def test_http_organizer_approval_and_player_status(world):
    organizer, players, outsider, tournament = world
    _open_registration(world)
    player = players[0]
    _web(player).post(_url('register', tournament.slug), REGISTER_FORM, secure=True)
    registration = Registration.objects.get(tournament=tournament, user=player)
    approve = f'/api/toc/{tournament.slug}/participants/{registration.id}/approve/'

    for caller in (None, player, outsider):  # anonymous, the applicant, a stranger
        assert _api(caller).post(approve, secure=True).status_code in (401, 403)
    registration.refresh_from_db()
    assert registration.status == Registration.PENDING

    assert _api(organizer).post(approve, secure=True).status_code == 200
    registration.refresh_from_db()
    assert registration.status == Registration.CONFIRMED
    _api(organizer).post(approve, secure=True)  # repeat must not corrupt state
    registration.refresh_from_db()
    assert registration.status == Registration.CONFIRMED
    assert Registration.objects.filter(tournament=tournament).count() == 1

    mine = _web(player).get('/tournaments/my/', secure=True)
    assert mine.status_code == 200 and tournament.name in mine.content.decode()
    assert DeltaCrownTransaction.objects.count() == 0


def test_http_match_journey_authority_and_consistency(world):
    organizer, players, outsider, tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    match = round_one[0]
    p1, p2 = (User.objects.get(pk=pid) for pid in (match.participant1_id, match.participant2_id))
    detail_url = _url('match_detail', tournament.slug, match_id=match.id)
    submit_url = _url('submit_result', tournament.slug, match_id=match.id)
    scores = {'participant1_score': 2, 'participant2_score': 1}

    # Public bracket renders; participants can find their assigned match
    assert _web().get(_url('bracket', tournament.slug), secure=True).status_code == 200
    for user in (p1, p2):
        assert _web(user).get(detail_url, secure=True).status_code == 200
    page = _web(p1).get('/tournaments/my/matches/', secure=True)
    assert page.status_code == 200

    # Not live yet: nobody can submit; strangers never can
    _web(p1).post(submit_url, scores, secure=True)
    assert _get(match).state != Match.COMPLETED and not _get(match).participant1_score
    for pid in (match.participant1_id, match.participant2_id):
        MatchService.check_in_participant(_get(match), pid)
    MatchService.transition_to_live(_get(match))

    assert _web(outsider).post(submit_url, scores, secure=True).status_code == 403
    assert _web().post(submit_url, scores, secure=True).status_code in (302, 403)
    assert _get(match).state == Match.LIVE

    ok = _web(p1).post(submit_url, scores, secure=True)
    assert ok.status_code == 200 and ok.json()['success'] is True
    assert _get(match).state != Match.COMPLETED  # a player submission alone is not final

    verify = f'/api/toc/{tournament.slug}/matches/{match.id}/verify/'
    body = {'action': 'confirm', **scores}
    for caller in (None, p2, outsider):
        assert _api(caller).post(verify, body, format='json', secure=True).status_code in (401, 403)
    assert _api(organizer).post(verify, body, format='json', secure=True).status_code == 200
    done = _get(match)
    assert done.state == Match.COMPLETED and done.winner_id == match.participant1_id

    # A late player resubmission cannot rewrite the finished result
    assert _web(p2).post(submit_url, {'participant1_score': 0, 'participant2_score': 3}, secure=True).status_code == 400
    after = _get(match)
    assert after.winner_id == match.participant1_id and after.state == Match.COMPLETED

    # Finish the event; public pages agree with stored state and the final uses the round-one winners
    other = _get(round_one[1])
    _play(other, organizer, p1_wins=True)
    final = Match.objects.get(tournament=tournament, round_number=2)
    assert {final.participant1_id, final.participant2_id} == {match.participant1_id, other.participant1_id}
    champion = _play(final, organizer, p1_wins=True)
    tournament.refresh_from_db()
    assert tournament.status == Tournament.COMPLETED
    champion_name = User.objects.get(pk=champion).username
    results = _web().get(_url('results', tournament.slug), secure=True)
    assert results.status_code == 200 and champion_name in results.content.decode()
    assert _web(User.objects.get(pk=champion)).get('/tournaments/my/', secure=True).status_code == 200


def test_organizer_correction_is_blocked_once_the_next_round_is_decided(world):
    """A feeder result may be corrected while nothing downstream was played, never after."""
    organizer, _players, _outsider, tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    first, second = round_one
    _play(first, organizer, p1_wins=True)
    _play(second, organizer, p1_wins=True)
    final = Match.objects.get(tournament=tournament, round_number=2)
    verify = f'/api/toc/{tournament.slug}/matches/{first.id}/verify/'
    flip = {'action': 'confirm', 'participant1_score': 0, 'participant2_score': 3}

    # Before the final starts, a correction re-seeds the final with the corrected winner
    assert _api(organizer).post(verify, flip, format='json', secure=True).status_code == 200
    final = _get(final)
    assert {final.participant1_id, final.participant2_id} == {first.participant2_id, second.participant1_id}

    champion = _play(final, organizer, p1_wins=True)
    tournament.refresh_from_db()
    assert tournament.status == Tournament.COMPLETED

    # After the final was played, neither correction path may rewrite the final's participants
    back = {'action': 'confirm', 'participant1_score': 3, 'participant2_score': 0}
    blocked = _api(organizer).post(verify, back, format='json', secure=True)
    assert blocked.status_code == 400
    score = _api(organizer).post(
        f'/api/toc/{tournament.slug}/matches/{first.id}/score/',
        {'participant1_score': 3, 'participant2_score': 0}, format='json', secure=True,
    )
    assert score.status_code == 400
    final = _get(final)
    assert {final.participant1_id, final.participant2_id} == {first.participant2_id, second.participant1_id}
    assert final.winner_id == champion and champion in (final.participant1_id, final.participant2_id)
    assert _get(first).winner_id == first.participant2_id


def test_solo_result_record_names_the_real_finalists(world, caplog):
    """Solo bracket slots hold user ids; the stored result must map them to the right registrations."""
    from apps.tournaments.models import TournamentResult

    organizer, _players, _outsider, tournament = world
    _registrations, round_one = _reach_published_bracket(world)
    # Registration ids differ from user ids here, so an id mix-up cannot pass by coincidence
    assert {r.id for r in Registration.objects.filter(tournament=tournament)}.isdisjoint(
        {m.participant1_id for m in round_one} | {m.participant2_id for m in round_one}
    )
    with caplog.at_level('WARNING'):
        _play_whole_tournament(organizer, tournament, round_one)

    final = Match.objects.get(tournament=tournament, round_number=2)
    assert final.bracket_id == round_one[0].bracket_id  # advancement keeps the final inside the bracket
    assert final.participant1_name and final.participant2_name
    result = TournamentResult.objects.get(tournament=tournament)
    assert result.winner.user_id == final.winner_id
    assert result.runner_up.user_id == final.loser_id
    assert 'WinnerDetermination failed' not in caplog.text
    # Completion side effects work: live bracket broadcast payload and the completion notification
    assert 'Failed to broadcast bracket_updated' not in caplog.text
    assert 'Notification step failed' not in caplog.text
    from apps.notifications.models import Notification
    assert Notification.objects.filter(recipient_id=final.winner_id, title__startswith='Tournament Complete').exists()
