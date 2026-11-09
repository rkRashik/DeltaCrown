"""Regression tests for the Batch 0A broken-route repairs (frontend audit F1-F5).

F1 /tournaments/<slug>/spectate/        F2 /spectator/ (+ legacy detail redirects)
F3 /competition/bounties/               F4 /@<user>/activity/
F5 /me/tournaments/

All data is synthetic and local to the test database.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models import Match, Registration, Tournament
from apps.user_profile.models import PrivacySettings, UserProfile
from apps.user_profile.models.activity import UserActivity

pytestmark = pytest.mark.django_db
User = get_user_model()


def _user(name):
    user = User.objects.create_user(username=name, email=f'{name}@example.test', password='pw-12345!')
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def game():
    return Game.objects.create(
        name='eFootball', display_name='eFootball', slug='efootball', short_code='EFB',
        category='SPORTS', game_type='1V1', is_active=True,
    )


@pytest.fixture
def organizer():
    return _user('b0a_organizer')


def _tournament(game, organizer, slug, status, **extra):
    now = timezone.now()
    return Tournament.objects.create(
        name=f'Cup {slug}', slug=slug, organizer=organizer, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=8, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2), tournament_end=now + timedelta(days=3),
        status=status, **extra,
    )


@pytest.fixture
def live_cup(game, organizer):
    cup = _tournament(game, organizer, 'b0a-live', Tournament.LIVE)
    players = [_user(f'b0a_p{i}') for i in range(1, 5)]
    for player in players:
        Registration.objects.create(tournament=cup, user=player, status=Registration.CONFIRMED)
    p1, p2, p3, p4 = players
    Match.objects.create(
        tournament=cup, round_number=1, match_number=1, state=Match.COMPLETED,
        participant1_id=p1.id, participant1_name=p1.username, participant2_id=p2.id, participant2_name=p2.username,
        participant1_score=2, participant2_score=1, winner_id=p1.id, loser_id=p2.id, completed_at=timezone.now(),
    )
    Match.objects.create(
        tournament=cup, round_number=1, match_number=2, state=Match.SCHEDULED,
        participant1_id=p3.id, participant1_name=p3.username, participant2_id=p4.id, participant2_name=p4.username,
        scheduled_time=timezone.now() + timedelta(hours=3),
    )
    return cup, players


# ---------------------------------------------------------------- F1 ----------
class TestSpectatePage:
    def test_live_tournament_renders_every_tab_anonymously(self, client, live_cup):
        cup, players = live_cup
        url = reverse('tournaments:spectate', kwargs={'slug': cup.slug})
        for tab in ('bracket', 'standings', 'matches'):
            response = client.get(url, {'tab': tab}, secure=True)
            assert response.status_code == 200, tab
        body = client.get(url, {'tab': 'matches'}, secure=True).content.decode()
        assert players[0].username in body and players[3].username in body
        assert players[0].email not in body  # public names only

    def test_standings_tab_lists_the_confirmed_players(self, client, live_cup):
        cup, players = live_cup
        body = client.get(reverse('tournaments:spectate', kwargs={'slug': cup.slug}), {'tab': 'standings'}, secure=True).content.decode()
        for player in players:
            assert player.username in body

    def test_completed_tournament_is_available(self, client, game, organizer):
        cup = _tournament(game, organizer, 'b0a-done', Tournament.COMPLETED)
        assert client.get(reverse('tournaments:spectate', kwargs={'slug': cup.slug}), secure=True).status_code == 200

    @pytest.mark.parametrize('status', [
        Tournament.DRAFT, Tournament.PENDING_APPROVAL, Tournament.REGISTRATION_OPEN, Tournament.PUBLISHED, Tournament.CANCELLED,
    ])
    def test_other_statuses_are_not_found(self, client, game, organizer, status):
        cup = _tournament(game, organizer, f'b0a-{status}', status)
        assert client.get(reverse('tournaments:spectate', kwargs={'slug': cup.slug}), secure=True).status_code == 404

    def test_unknown_slug_and_deleted_tournament_are_not_found(self, client, live_cup):
        cup, _players = live_cup
        assert client.get(reverse('tournaments:spectate', kwargs={'slug': 'no-such-cup'}), secure=True).status_code == 404
        Tournament.objects.filter(pk=cup.pk).update(is_deleted=True)
        assert client.get(reverse('tournaments:spectate', kwargs={'slug': cup.slug}), secure=True).status_code == 404


# ---------------------------------------------------------------- F2 ----------
class TestSpectatorDirectory:
    def test_empty_directory_renders(self, client):
        response = client.get('/spectator/', secure=True)
        assert response.status_code == 200
        assert 'No Active Tournaments' in response.content.decode()

    def test_lists_only_public_live_and_open_tournaments(self, client, game, organizer, live_cup):
        cup, _players = live_cup
        open_cup = _tournament(game, organizer, 'b0a-open', Tournament.REGISTRATION_OPEN)
        for hidden_status, slug in ((Tournament.DRAFT, 'b0a-draft'), (Tournament.PENDING_APPROVAL, 'b0a-pending'),
                                    (Tournament.COMPLETED, 'b0a-finished'), (Tournament.CANCELLED, 'b0a-cancelled')):
            _tournament(game, organizer, slug, hidden_status)
        deleted = _tournament(game, organizer, 'b0a-deleted', Tournament.LIVE)
        Tournament.objects.filter(pk=deleted.pk).update(is_deleted=True)

        response = client.get('/spectator/', secure=True)
        assert response.status_code == 200
        body = response.content.decode()
        assert f'href="/tournaments/{cup.slug}/spectate/"' in body  # live -> spectate page
        assert f'href="/tournaments/{open_cup.slug}/"' in body      # open -> tournament page
        for hidden in ('b0a-draft', 'b0a-pending', 'b0a-finished', 'b0a-cancelled', 'b0a-deleted'):
            assert f'Cup {hidden}' not in body
        assert '4 Confirmed participants' in body
        # no unsupported realtime claims
        assert 'WebSocket' not in body and 'Auto-refresh' not in body

    def test_directory_does_not_count_unconfirmed_registrations(self, client, game, organizer):
        cup = _tournament(game, organizer, 'b0a-count', Tournament.REGISTRATION_OPEN)
        Registration.objects.create(tournament=cup, user=_user('b0a_c1'), status=Registration.CONFIRMED)
        Registration.objects.create(tournament=cup, user=_user('b0a_c2'), status=Registration.PENDING)
        assert '1 Confirmed participants' in client.get('/spectator/', secure=True).content.decode()

    def test_legacy_tournament_page_redirects_to_canonical_page(self, client, game, organizer, live_cup):
        cup, _players = live_cup
        live = client.get(f'/spectator/tournaments/{cup.id}/', secure=True)
        assert live.status_code == 302 and live['Location'] == f'/tournaments/{cup.slug}/spectate/'
        open_cup = _tournament(game, organizer, 'b0a-open2', Tournament.REGISTRATION_OPEN)
        opened = client.get(f'/spectator/tournaments/{open_cup.id}/', secure=True)
        assert opened.status_code == 302 and opened['Location'] == f'/tournaments/{open_cup.slug}/'
        draft = _tournament(game, organizer, 'b0a-draft2', Tournament.DRAFT)
        assert client.get(f'/spectator/tournaments/{draft.id}/', secure=True).status_code == 404
        assert client.get('/spectator/tournaments/999999/', secure=True).status_code == 404

    def test_legacy_match_page_redirects_and_hides_draft_matches(self, client, game, organizer, live_cup):
        cup, _players = live_cup
        match = Match.objects.filter(tournament=cup).first()
        redirect = client.get(f'/spectator/matches/{match.id}/', secure=True)
        assert redirect.status_code == 302
        assert redirect['Location'] == f'/tournaments/{cup.slug}/matches/{match.id}/'
        draft = _tournament(game, organizer, 'b0a-draft3', Tournament.DRAFT)
        hidden = Match.objects.create(
            tournament=draft, round_number=1, match_number=1, state=Match.SCHEDULED,
            participant1_id=1, participant2_id=2,
        )
        assert client.get(f'/spectator/matches/{hidden.id}/', secure=True).status_code == 404


# ---------------------------------------------------------------- F3 ----------
class TestBountyBoard:
    def test_public_board_is_deliberately_unavailable_not_a_server_error(self, client):
        for user in (None, _user('b0a_bounty_viewer')):
            if user:
                client.force_login(user)
            response = client.get('/competition/bounties/', secure=True)
            assert response.status_code == 404

    def test_view_renders_nothing_about_rewards_or_wagering(self):
        """The view itself must raise 404 before querying or rendering any bounty/reward data."""
        from django.http import Http404
        from django.test import RequestFactory
        from apps.competition.views import bounty_board

        with pytest.raises(Http404) as raised:
            bounty_board(RequestFactory().get('/competition/bounties/'))
        message = str(raised.value).lower()
        assert 'reward' not in message and 'cash' not in message and 'wager' not in message


# ---------------------------------------------------------------- F4 ----------
def _activity(user, event_type, **metadata):
    return UserActivity.objects.create(user=user, event_type=event_type, metadata=metadata)


class TestPublicActivityPage:
    @pytest.fixture
    def player(self):
        player = _user('b0a_active')
        _activity(player, 'tournament_registered', registration_id=987654, reason='secret-reason', actor_user_id=424242)
        _activity(player, 'coins_earned', amount=77123)  # economy event: never public
        return player

    def _get(self, client, username='b0a_active', **params):
        return client.get(f'/@{username}/activity/', params, secure=True)

    def test_anonymous_sees_public_events_without_metadata(self, client, player):
        response = self._get(client)
        assert response.status_code == 200
        body = response.content.decode()
        assert 'Registered for Tournament' in body
        for leaked in ('987654', 'secret-reason', '424242', '77123', 'Earned DeltaCoins', player.email):
            assert leaked not in body

    def test_owner_sees_all_own_event_labels_but_never_metadata(self, client, player):
        client.force_login(player)
        body = self._get(client).content.decode()
        assert 'Earned DeltaCoins' in body and 'Registered for Tournament' in body
        for leaked in ('987654', 'secret-reason', '424242', '77123'):
            assert leaked not in body

    def test_activity_toggle_hides_feed_from_others_but_not_the_owner(self, client, player):
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=player.profile)
        privacy.show_activity_feed = False
        privacy.save()
        body = self._get(client).content.decode()
        assert 'keeps their activity private' in body
        assert 'Registered for Tournament' not in body
        client.force_login(player)
        assert 'Registered for Tournament' in self._get(client).content.decode()

    def test_private_account_shows_the_private_profile_page(self, client, player):
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=player.profile)
        privacy.is_private_account = True
        privacy.save()
        response = self._get(client)
        assert response.status_code == 200
        body = response.content.decode()
        assert 'Registered for Tournament' not in body

    def test_unknown_user_is_not_found_and_bad_page_is_tolerated(self, client, player):
        assert self._get(client, username='nobody-here').status_code == 404
        assert self._get(client, page='abc').status_code == 200
        assert self._get(client, page='999').status_code == 200

    def test_empty_states_differ_for_owner_and_visitors(self, client):
        quiet = _user('b0a_quiet')
        assert "hasn't participated in any events yet" in client.get('/@b0a_quiet/activity/', secure=True).content.decode()
        client.force_login(quiet)
        owner_body = client.get('/@b0a_quiet/activity/', secure=True).content.decode()
        assert 'Start competing in tournaments' in owner_body and 'Browse Tournaments' in owner_body

    def test_page_is_not_indexed(self, client, player):
        assert 'noindex' in self._get(client).content.decode().lower()


# ---------------------------------------------------------------- F5 ----------
class TestLegacyMyTournaments:
    def test_anonymous_is_sent_to_login(self, client):
        response = client.get('/me/tournaments/', secure=True)
        assert response.status_code == 302 and '/login' in response['Location'] and 'next=' in response['Location']

    def test_signed_in_player_is_redirected_to_the_canonical_page(self, client):
        client.force_login(_user('b0a_mine'))
        response = client.get('/me/tournaments/', secure=True)
        assert response.status_code == 302 and response['Location'] == '/tournaments/my/'
        assert client.get(response['Location'], secure=True).status_code == 200

    def test_query_string_is_preserved(self, client):
        client.force_login(_user('b0a_mine2'))
        assert client.get('/me/tournaments/?status=active', secure=True)['Location'] == '/tournaments/my/?status=active'
