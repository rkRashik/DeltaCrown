"""eFootball pilot journey (solo, single elimination, DeltaCoin entry fee), service level.

Synthetic users/wallets on a disposable database; no providers are contacted. Notifications
and WebSocket broadcasts run through their normal (test) backends; nothing external is called.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.games.models.game import Game
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Match, Registration, Tournament
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import UserProfile

pytestmark = pytest.mark.django_db
User = get_user_model()
FEE = 100


def _user(name):
    user = User.objects.create_user(username=name, email=f'{name}@example.test')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    DeltaCrownWallet.objects.create(profile=profile, cached_balance=500)
    return user


@pytest.fixture
def world(db):
    organizer = _user('ef-organizer')
    players = [_user(f'ef-player-{n}') for n in range(1, 5)]
    outsider = _user('ef-outsider')
    game = Game.objects.create(
        name='eFootball', slug='efootball', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now()
    tournament = Tournament.objects.create(
        name='eFootball Pilot Cup', slug='efootball-pilot-cup', organizer=organizer, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=4, min_participants=2,
        has_entry_fee=True, entry_fee_amount=Decimal(FEE), payment_methods=[Tournament.DELTACOIN],
        registration_start=now - timedelta(days=2), registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2), tournament_end=now + timedelta(days=3),
        status=Tournament.DRAFT,
    )
    return organizer, players, outsider, tournament


def _to(tournament, status, actor):
    return TournamentLifecycleService.transition(tournament.id, status, actor=actor, force=True)


def _register(tournament, user):
    return RegistrationService.register_participant(
        tournament.id, user, registration_data={'game_id': f'{user.username}-efootball'},
    )


def _get(match):
    return Match.objects.get(pk=match.pk)


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


def _reach_published_bracket(world):
    """Publish, open registration, register + pay 4 players, close, go live, publish bracket."""
    organizer, players, _outsider, tournament = world
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    registrations = []
    for player in players:
        reg = _register(tournament, player)
        RegistrationService.pay_with_deltacoin(reg.id, player)
        reg.refresh_from_db()
        assert reg.status == Registration.CONFIRMED
        registrations.append(reg)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    _to(tournament, Tournament.LIVE, organizer)
    TOCBracketsService.generate_bracket(tournament, organizer, {})
    TOCBracketsService.publish_bracket(tournament, organizer)
    round_one = list(Match.objects.filter(tournament=tournament, round_number=1).order_by('match_number'))
    return registrations, round_one


def test_organizer_to_champion_journey(world):
    organizer, players, _outsider, tournament = world
    registrations, round_one = _reach_published_bracket(world)

    assert DeltaCrownTransaction.objects.count() == 4
    assert all(DeltaCrownWallet.objects.get(profile__user=p).cached_balance == 500 - FEE for p in players)

    # Duplicate registration is rejected and creates nothing
    with pytest.raises(ValidationError):
        _register(tournament, players[0])
    assert Registration.objects.filter(tournament=tournament, user=players[0]).count() == 1

    assert len(round_one) == 2
    seeded = [pid for m in round_one for pid in (m.participant1_id, m.participant2_id)]
    assert sorted(seeded) == sorted(r.user_id for r in registrations)  # each player exactly once

    # Round one: the first-listed participant wins both matches
    winners = [_play(m, organizer, p1_wins=True) for m in round_one]
    final = Match.objects.get(tournament=tournament, round_number=2)
    assert {final.participant1_id, final.participant2_id} == set(winners)  # correct next opponents
    assert Match.objects.filter(tournament=tournament, round_number=2).count() == 1

    champion = _play(final, organizer, p1_wins=True)
    assert champion in winners

    tournament.refresh_from_db()
    assert tournament.status == Tournament.COMPLETED
    assert DeltaCrownTransaction.objects.count() == 4  # no extra financial effects after play


# -- negative scenarios -------------------------------------------------------

def test_registration_rejected_outside_open_state_and_after_cancellation(world):
    organizer, _players, outsider, tournament = world
    with pytest.raises(ValidationError):  # still a draft
        _register(tournament, outsider)
    _to(tournament, Tournament.PUBLISHED, organizer)
    _to(tournament, Tournament.REGISTRATION_OPEN, organizer)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
    with pytest.raises(ValidationError):  # closed
        _register(tournament, outsider)
    _to(tournament, Tournament.CANCELLED, organizer)
    with pytest.raises(ValidationError):  # cancelled
        _register(tournament, outsider)
    assert not Registration.objects.filter(tournament=tournament, user=outsider).exists()


def test_payment_cannot_be_made_by_someone_else_or_charged_twice(world):
    organizer, players, outsider, tournament = world
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
    assert DeltaCrownWallet.objects.get(profile__user=players[0]).cached_balance == 500 - FEE


def test_failed_payment_write_rolls_back_the_debit(world):
    organizer, players, _outsider, tournament = world
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
    assert DeltaCrownWallet.objects.get(profile__user=players[0]).cached_balance == 500


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


# -- organizer API authorization and reset guards ------------------------------

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
        RegistrationService.pay_with_deltacoin(_register(tournament, player).id, player)
    _to(tournament, Tournament.REGISTRATION_CLOSED, organizer)
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
