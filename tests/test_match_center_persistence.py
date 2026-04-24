"""End-to-end persistence + render verification for the Match Center.

Covers:
* Save round-trip via the TOC config API persists to MatchCenterConfig.
* Per-match overrides survive across requests.
* Public match_detail render reflects the saved config.
* Save under a missing-table scenario returns success=false WITHOUT 500
  and echoes the user's submitted values back.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient


User = get_user_model()


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='mc_organizer', email='mc@toc.test', password='pass1234',
    )


@pytest.fixture
def game(db):
    from apps.games.models import Game
    return Game.objects.create(
        slug='mc-test-game', name='MC Test Game', is_active=True,
        primary_color='#3B82F6', secondary_color='#8B5CF6', accent_color='#06B6D4',
    )


@pytest.fixture
def tournament(db, organizer, game):
    from apps.tournaments.models.tournament import Tournament
    now = timezone.now()
    return Tournament.objects.create(
        name='MC Persistence Tournament',
        slug='mc-persistence-tournament',
        description='Match Center persistence test',
        organizer=organizer, game=game,
        format='single_elimination', participation_type='team',
        max_participants=8, min_participants=2,
        prize_pool=Decimal('100.00'),
        registration_start=now - timedelta(days=14),
        registration_end=now - timedelta(days=7),
        tournament_start=now - timedelta(days=1),
        status='live',
    )


@pytest.fixture
def match(db, tournament):
    from apps.tournaments.models.match import Match
    return Match.objects.create(
        tournament=tournament,
        round_number=1, match_number=1,
        participant1_id=1, participant2_id=2,
        participant1_name='Alpha', participant2_name='Bravo',
        participant1_score=2, participant2_score=1,
        state=Match.COMPLETED,
        winner_id=1, loser_id=2,
        scheduled_time=timezone.now() - timedelta(hours=1),
    )


@pytest.fixture
def organizer_client(organizer):
    client = APIClient()
    client.force_login(organizer)
    return client


@pytest.mark.django_db
class TestMatchCenterPersistence:
    """End-to-end verification of save → reload → public render."""

    def test_post_then_get_persists_global_config(self, organizer_client, tournament):
        url = reverse('toc_api:match-center-config', kwargs={'slug': tournament.slug})
        payload = {
            'enabled': True,
            'show_media': False,
            'show_stats': True,
            'show_fan_pulse': True,
            'theme': 'tactical',
            'poll_question': 'Who wins the grand final?',
            'poll_option_a': 'Alpha Squad',
            'poll_option_b': 'Bravo Crew',
            'auto_refresh_seconds': 45,
            'match_overrides': {},
        }

        post = organizer_client.post(url, payload, format='json')
        assert post.status_code == 200, post.content
        body = post.json()
        assert body.get('success') is True
        cfg = body['config']
        assert cfg['theme'] == 'tactical'
        assert cfg['poll_question'] == 'Who wins the grand final?'
        assert cfg['auto_refresh_seconds'] == 45
        assert cfg['show_media'] is False

        # Re-fetch and verify persistence (no in-memory leakage from POST).
        get = organizer_client.get(url)
        assert get.status_code == 200
        cfg2 = get.json()['config']
        assert cfg2['theme'] == 'tactical'
        assert cfg2['poll_question'] == 'Who wins the grand final?'
        assert cfg2['poll_option_a'] == 'Alpha Squad'
        assert cfg2['poll_option_b'] == 'Bravo Crew'
        assert cfg2['auto_refresh_seconds'] == 45
        assert cfg2['show_media'] is False
        assert cfg2['show_stats'] is True

    def test_match_overrides_persist_with_text_url_and_bool(
        self, organizer_client, tournament, match,
    ):
        url = reverse('toc_api:match-center-config', kwargs={'slug': tournament.slug})
        payload = {
            'enabled': True,
            'theme': 'cyber',
            'poll_question': 'Series MVP?',
            'poll_option_a': 'A', 'poll_option_b': 'B',
            'show_media': True, 'show_stats': True, 'show_fan_pulse': True,
            'auto_refresh_seconds': 20,
            'match_overrides': {
                str(match.id): {
                    'headline': 'Grand Final Showdown',
                    'subline': 'Best of 5 — Map 3',
                    'stream_url': 'https://www.twitch.tv/deltacrown',
                    'show_fan_pulse': False,
                },
            },
        }

        post = organizer_client.post(url, payload, format='json')
        assert post.status_code == 200, post.content
        body = post.json()
        assert body.get('success') is True
        overrides = body['config']['match_overrides']
        assert str(match.id) in overrides
        item = overrides[str(match.id)]
        assert item['headline'] == 'Grand Final Showdown'
        assert item['subline'] == 'Best of 5 — Map 3'
        assert item['stream_url'] == 'https://www.twitch.tv/deltacrown'
        assert item['show_fan_pulse'] is False
        assert body.get('invalid_urls') == []

        # Empty text fields drop the key; an empty per-match dict drops
        # the whole entry.
        clear = dict(payload)
        clear['match_overrides'] = {str(match.id): {}}
        post2 = organizer_client.post(url, clear, format='json')
        assert post2.status_code == 200
        assert post2.json()['config']['match_overrides'] == {}

    def test_invalid_stream_url_rejected_but_other_fields_save(
        self, organizer_client, tournament, match,
    ):
        url = reverse('toc_api:match-center-config', kwargs={'slug': tournament.slug})
        payload = {
            'enabled': True, 'theme': 'cyber',
            'poll_question': 'q', 'poll_option_a': 'a', 'poll_option_b': 'b',
            'show_media': True, 'show_stats': True, 'show_fan_pulse': True,
            'auto_refresh_seconds': 20,
            'match_overrides': {
                str(match.id): {
                    'headline': 'Keep me',
                    'stream_url': 'javascript:alert(1)',  # rejected
                },
            },
        }
        post = organizer_client.post(url, payload, format='json')
        assert post.status_code == 200
        body = post.json()
        assert body['success'] is True
        invalid = body.get('invalid_urls') or []
        assert any(item.get('field') == 'stream_url' for item in invalid)
        item = body['config']['match_overrides'][str(match.id)]
        assert item['headline'] == 'Keep me'
        assert 'stream_url' not in item

    def test_database_error_returns_success_false_without_500(
        self, organizer_client, tournament,
    ):
        """When the table is missing in production, save must NOT 500.

        It must echo the submitted values back so the JS layer can keep
        them in the form rather than blanking them with defaults.
        """
        url = reverse('toc_api:match-center-config', kwargs={'slug': tournament.slug})
        payload = {
            'enabled': True, 'theme': 'arena',
            'poll_question': 'Pick a side',
            'poll_option_a': 'Left', 'poll_option_b': 'Right',
            'show_media': False, 'show_stats': True, 'show_fan_pulse': False,
            'auto_refresh_seconds': 30,
            'match_overrides': {},
        }

        with patch(
            'apps.tournaments.api.toc.match_center_service.MatchCenterConfig.objects.get_or_create',
            side_effect=DatabaseError('relation "toc_match_center_config" does not exist'),
        ):
            response = organizer_client.post(url, payload, format='json')

        assert response.status_code == 200, response.content
        body = response.json()
        assert body['success'] is False
        assert 'error' in body and body['error']
        # Echoed values reflect what the user submitted, not defaults.
        cfg = body['config']
        assert cfg['theme'] == 'arena'
        assert cfg['poll_question'] == 'Pick a side'
        assert cfg['poll_option_a'] == 'Left'
        assert cfg['poll_option_b'] == 'Right'
        assert cfg['auto_refresh_seconds'] == 30
        assert cfg['show_media'] is False
        assert cfg['show_fan_pulse'] is False

    def test_football_stats_post_match_override_persists(
        self, organizer_client, tournament, match,
    ):
        """Organizer can re-submit football stats AFTER a match is completed.

        This is the "post-match override path" — score endpoint accepts
        the same payload regardless of state, persists football_stats to
        lobby_info, and the next list call surfaces them again so the
        editor can pre-fill from saved values.
        """
        from apps.tournaments.models.match import Match
        # Simulate: match already completed (it is, per fixture).
        assert match.state == Match.COMPLETED

        url = reverse('toc_api:match-score', kwargs={
            'slug': tournament.slug, 'pk': match.id,
        })
        body = {
            'participant1_score': 2,
            'participant2_score': 2,
            'winner_side': '1',
            'football_stats': {
                'team1': {
                    'display_name': 'Alpha', 'goals': 2, 'penalties': 4,
                    'possession_pct': 58, 'shots': 12, 'shots_on_target': 6,
                    'passes_completed': 412, 'pass_accuracy_pct': 88,
                },
                'team2': {
                    'display_name': 'Bravo', 'goals': 2, 'penalties': 3,
                    'possession_pct': 42, 'shots': 9, 'shots_on_target': 4,
                    'passes_completed': 318, 'pass_accuracy_pct': 81,
                },
                'has_penalties': True,
            },
        }
        resp = organizer_client.post(url, body, format='json')
        assert resp.status_code == 200, resp.content

        match.refresh_from_db()
        stats = (match.lobby_info or {}).get('football_stats') or {}
        assert stats.get('has_penalties') is True
        assert stats['team1']['penalties'] == 4
        assert stats['team1']['possession_pct'] == 58
        assert stats['team2']['shots_on_target'] == 4
        assert stats['team2']['pass_accuracy_pct'] == 81

        # And the list serializer surfaces them so the editor can pre-fill.
        from apps.tournaments.api.toc.matches_service import TOCMatchesService
        listed = TOCMatchesService.get_matches(tournament)
        first = next(
            (m for m in listed['matches'] if m['id'] == match.id), None,
        )
        assert first is not None
        lobby_in_list = first.get('lobby_info') or {}
        assert lobby_in_list.get('football_stats')
        assert lobby_in_list['football_stats']['team1']['penalties'] == 4

    def test_public_match_detail_reflects_saved_config(
        self, organizer_client, tournament, match,
    ):
        url = reverse('toc_api:match-center-config', kwargs={'slug': tournament.slug})
        payload = {
            'enabled': True,
            'show_media': True, 'show_stats': True, 'show_fan_pulse': False,
            'theme': 'tactical',
            'poll_question': 'Who clutches?',
            'poll_option_a': 'Alpha Esports',
            'poll_option_b': 'Bravo Esports',
            'auto_refresh_seconds': 60,
            'match_overrides': {
                str(match.id): {
                    'headline': 'Clutch or kick',
                    'subline': 'Decider map',
                },
            },
        }
        save = organizer_client.post(url, payload, format='json')
        assert save.status_code == 200 and save.json().get('success') is True

        # Now resolve the public presentation as the live view does.
        from apps.tournaments.views.live import _resolve_match_center_presentation
        match.refresh_from_db()
        presentation = _resolve_match_center_presentation(match, request=None)
        assert presentation['theme'] == 'tactical'
        assert presentation['poll_question'] == 'Who clutches?'
        assert presentation['poll_option_a'] == 'Alpha Esports'
        assert presentation['poll_option_b'] == 'Bravo Esports'
        assert presentation['show_fan_pulse'] is False
        assert presentation['auto_refresh_seconds'] == 60
        assert presentation['headline'] == 'Clutch or kick'
        assert presentation['subline'] == 'Decider map'
