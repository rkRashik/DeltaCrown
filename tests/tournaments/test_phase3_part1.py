"""
Phase 3 Part 1 Tests.

Covers:
- P3-T01: TOC Bracket Generation UI (generate & reset endpoints)
- P3-T02: Drag-and-Drop Seeding Interface (reorder & publish endpoints)
- P3-T03: TOC Match Operations / Match Medic (all match-ops endpoints)

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import json
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match
from apps.tournaments.models.bracket import Bracket

User = get_user_model()

import uuid as _uuid


def _uid():
    return _uuid.uuid4().hex[:8]


def _make_game(**kwargs):
    uid = _uid()
    defaults = dict(
        name=f'Game-{uid}', slug=f'game-{uid}', short_code=uid[:4].upper(),
        category='FPS', display_name=f'Game {uid}', game_type='TEAM_VS_TEAM',
        is_active=True,
    )
    defaults.update(kwargs)
    return Game.objects.create(**defaults)


def _make_tournament(game, organizer, **kwargs):
    uid = _uid()
    now = timezone.now()
    defaults = dict(
        name=f'Tournament-{uid}',
        slug=f't-{uid}',
        description='Test tournament',
        organizer=organizer,
        game=game,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        participation_type=Tournament.SOLO,
        format='single_elimination',
        enable_check_in=True,
        check_in_minutes_before=30,
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    uid = _uid()
    uname = username or f'user-{uid}'
    defaults = dict(username=uname, email=f'{uname}@test.dc', password='test1234')
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_registration(tournament, user, **kwargs):
    defaults = dict(
        tournament=tournament,
        user=user,
        status='confirmed',
        registration_data={'game_id': f'gid-{_uid()}'},
    )
    defaults.update(kwargs)
    return Registration.objects.create(**defaults)


def _make_bracket(tournament, **kwargs):
    defaults = dict(
        tournament=tournament,
        format='single-elimination',
        total_rounds=2,
        total_matches=3,
        bracket_structure={'format': 'single-elimination'},
        seeding_method='slot-order',
        is_finalized=False,
    )
    defaults.update(kwargs)
    return Bracket.objects.create(**defaults)


def _make_match(tournament, bracket, **kwargs):
    defaults = dict(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=1,
        participant1_name='Player A',
        participant2_id=2,
        participant2_name='Player B',
        state='scheduled',
    )
    defaults.update(kwargs)
    return Match.objects.create(**defaults)


def _authed_client(user):
    client = Client()
    client.force_login(user)
    return client


# ===========================================================================
# P3-T01: Bracket Generation
# ===========================================================================

@pytest.mark.django_db
class TestBracketGeneration:
    """P3-T01: Generate bracket endpoint."""

    @patch('apps.tournaments.views.organizer_brackets.BracketEngineService')
    def test_generate_bracket_success(self, MockEngine):
        """Generate bracket creates bracket + matches."""
        from apps.tournament_ops.dtos import MatchDTO

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        _make_registration(tournament, _make_user())
        _make_registration(tournament, _make_user())

        # Mock engine response
        mock_dtos = [
            MatchDTO(round_number=1, match_number=1, team_a_id=1, team_b_id=2,
                     team1_name='P1', team2_name='P2'),
        ]
        MockEngine.return_value.generate_bracket_for_stage.return_value = mock_dtos

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/generate-bracket/',
            data=json.dumps({
                'format': 'single-elimination',
                'seeding_method': 'slot-order',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['match_count'] == 1

        # Bracket and match records created
        assert Bracket.objects.filter(tournament=tournament).exists()
        assert Match.objects.filter(tournament=tournament, is_deleted=False).count() == 1

    def test_generate_bracket_permission_denied(self):
        """Non-organizer cannot generate bracket."""
        organizer = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = _authed_client(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/generate-bracket/',
            data=json.dumps({'format': 'single-elimination'}),
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_generate_bracket_too_few_participants(self):
        """Cannot generate bracket with fewer than 2 confirmed participants."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        _make_registration(tournament, _make_user())  # Only 1

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/generate-bracket/',
            data=json.dumps({'format': 'single-elimination'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        data = resp.json()
        assert 'At least 2' in data['error']

    def test_generate_bracket_locked_when_matches_started(self):
        """Cannot generate bracket if matches already in progress."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        _make_match(tournament, bracket, state='live')
        _make_registration(tournament, _make_user())
        _make_registration(tournament, _make_user())

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/generate-bracket/',
            data=json.dumps({'format': 'single-elimination'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'matches already in progress' in resp.json()['error'].lower()


@pytest.mark.django_db
class TestBracketReset:
    """P3-T01: Reset bracket endpoint."""

    def test_reset_bracket_success(self):
        """Reset soft-deletes matches and removes bracket."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        _make_match(tournament, bracket, state='scheduled')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reset-bracket/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

        # Matches soft-deleted, bracket gone
        assert Match.objects.filter(tournament=tournament, is_deleted=False).count() == 0
        assert not Bracket.objects.filter(tournament=tournament).exists()

    def test_reset_bracket_locked(self):
        """Cannot reset when matches in progress."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        _make_match(tournament, bracket, state='live')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reset-bracket/',
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'matches already in progress' in resp.json()['error'].lower()

    def test_reset_bracket_permission_denied(self):
        """Non-organizer cannot reset bracket."""
        organizer = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = _authed_client(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reset-bracket/',
            content_type='application/json',
        )
        assert resp.status_code == 403


# ===========================================================================
# P3-T02: Seeding Reorder & Publish
# ===========================================================================

@pytest.mark.django_db
class TestSeedingReorder:
    """P3-T02: Drag-and-drop seed reorder endpoint."""

    def test_reorder_seeds_success(self):
        """Reorder seeds updates first-round match participants."""
        organizer = _make_user()
        player1 = _make_user()
        player2 = _make_user()
        player3 = _make_user()
        player4 = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        _make_registration(tournament, player1)
        _make_registration(tournament, player2)
        _make_registration(tournament, player3)
        _make_registration(tournament, player4)
        bracket = _make_bracket(tournament)
        m1 = _make_match(tournament, bracket,
                         match_number=1,
                         participant1_id=player1.id, participant1_name=player1.username,
                         participant2_id=player2.id, participant2_name=player2.username)
        m2 = _make_match(tournament, bracket,
                         match_number=2,
                         participant1_id=player3.id, participant1_name=player3.username,
                         participant2_id=player4.id, participant2_name=player4.username)

        # Reorder: swap player1 ↔ player3
        new_order = [player3.id, player2.id, player1.id, player4.id]

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reorder-seeds/',
            data=json.dumps({'order': new_order}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

        m1.refresh_from_db()
        m2.refresh_from_db()
        assert m1.participant1_id == player3.id
        assert m2.participant1_id == player1.id

    def test_reorder_seeds_finalized_lock(self):
        """Cannot reorder seeds if bracket is finalized."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        _make_bracket(tournament, is_finalized=True)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reorder-seeds/',
            data=json.dumps({'order': [1, 2]}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'locked' in resp.json()['error'].lower() or 'published' in resp.json()['error'].lower()

    def test_reorder_seeds_no_bracket(self):
        """Reorder fails if no bracket exists."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/reorder-seeds/',
            data=json.dumps({'order': [1, 2]}),
            content_type='application/json',
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestBracketPublish:
    """P3-T02: Publish (finalize) bracket endpoint."""

    @patch('apps.tournaments.views.organizer_brackets.BracketEditorService')
    def test_publish_bracket_success(self, MockEditor):
        """Publish sets is_finalized=True."""
        mock_result = MagicMock()
        mock_result.is_valid = True
        MockEditor.validate_bracket.return_value = mock_result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament, is_finalized=False)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/publish-bracket/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

        bracket.refresh_from_db()
        assert bracket.is_finalized is True

    def test_publish_already_published(self):
        """Cannot publish an already-published bracket."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        _make_bracket(tournament, is_finalized=True)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/publish-bracket/',
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'already' in resp.json()['error'].lower()


# ===========================================================================
# P3-T03: Match Operations / Match Medic
# ===========================================================================

@pytest.mark.django_db
class TestMatchMarkLive:
    """P3-T03: Mark match as live endpoint."""

    @patch('apps.tournaments.views.organizer_match_ops._get_service')
    def test_mark_live_success(self, mock_svc):
        result = MagicMock()
        result.success = True
        result.message = 'Match is now live.'
        result.match_id = 1
        result.new_state = 'live'
        result.warnings = []
        mock_svc.return_value.mark_match_live.return_value = result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='scheduled')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/mark-live/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_mark_live_permission_denied(self):
        """Non-organizer gets 403."""
        organizer = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket)

        client = _authed_client(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/mark-live/',
            content_type='application/json',
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMatchPause:
    """P3-T03: Pause match endpoint."""

    @patch('apps.tournaments.views.organizer_match_ops._get_service')
    def test_pause_success(self, mock_svc):
        result = MagicMock()
        result.success = True
        result.message = 'Match paused.'
        result.match_id = 1
        result.new_state = 'pending_result'
        result.warnings = []
        mock_svc.return_value.pause_match.return_value = result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='live')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/pause/',
            data=json.dumps({'reason': 'Technical break'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True


@pytest.mark.django_db
class TestMatchResume:
    """P3-T03: Resume match endpoint."""

    @patch('apps.tournaments.views.organizer_match_ops._get_service')
    def test_resume_success(self, mock_svc):
        result = MagicMock()
        result.success = True
        result.message = 'Match resumed.'
        result.match_id = 1
        result.new_state = 'live'
        result.warnings = []
        mock_svc.return_value.resume_match.return_value = result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='pending_result')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/resume/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True


@pytest.mark.django_db
class TestMatchForceComplete:
    """P3-T03: Force-complete match endpoint."""

    @patch('apps.tournaments.views.organizer_match_ops._get_service')
    def test_force_complete_success(self, mock_svc):
        result = MagicMock()
        result.success = True
        result.message = 'Force completed.'
        result.match_id = 1
        result.new_state = 'completed'
        result.warnings = []
        mock_svc.return_value.force_complete_match.return_value = result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='live')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-complete/',
            data=json.dumps({
                'reason': 'Player disconnected',
                'score1': 3,
                'score2': 1,
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_force_complete_requires_reason(self):
        """Force-complete without reason returns 400."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='live')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-complete/',
            data=json.dumps({'reason': ''}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'reason' in resp.json()['error'].lower()

    def test_force_complete_no_json(self):
        """Force-complete with invalid body returns 400."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='live')

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-complete/',
            data='not json',
            content_type='application/json',
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMatchAddNote:
    """P3-T03: Add moderator note endpoint."""

    @patch('apps.tournaments.views.organizer_match_ops._get_service')
    def test_add_note_success(self, mock_svc):
        result = MagicMock()
        result.success = True
        result.message = 'Note added.'
        result.match_id = 1
        result.new_state = None
        result.warnings = []
        mock_svc.return_value.add_moderator_note.return_value = result

        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/add-note/',
            data=json.dumps({'content': 'Player asked for a break'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_add_note_empty_content(self):
        """Empty note content returns 400."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/add-note/',
            data=json.dumps({'content': ''}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'content' in resp.json()['error'].lower() or 'note' in resp.json()['error'].lower()


@pytest.mark.django_db
class TestMatchForceStart:
    """P3-T03: Force-start match (bypass check-in) endpoint."""

    def test_force_start_success(self):
        """Force-start sets state=live, checks in both participants."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='check_in',
                            participant1_checked_in=False,
                            participant2_checked_in=False)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-start/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['new_state'] == 'live'

        match.refresh_from_db()
        assert match.state == 'live'
        assert match.participant1_checked_in is True
        assert match.participant2_checked_in is True
        assert match.started_at is not None

    def test_force_start_completed_match(self):
        """Cannot force-start a completed match."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='completed', winner_id=1, loser_id=2)

        client = _authed_client(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-start/',
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'cannot force-start' in resp.json()['error'].lower()

    def test_force_start_permission_denied(self):
        """Non-organizer cannot force-start."""
        organizer = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        match = _make_match(tournament, bracket, state='scheduled')

        client = _authed_client(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/match-ops/{match.id}/force-start/',
            content_type='application/json',
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMatchOpsTab:
    """P3-T03: Matches tab rendering with state filters."""

    def test_matches_tab_renders(self):
        """Matches tab loads successfully."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = _authed_client(organizer)
        resp = client.get(f'/tournaments/organizer/{tournament.slug}/matches/')
        assert resp.status_code == 200

    def test_matches_tab_active_filter(self):
        """Active filter shows live matches."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        _make_match(tournament, bracket, state='live', match_number=1)
        _make_match(tournament, bracket, state='scheduled', match_number=2)

        client = _authed_client(organizer)
        resp = client.get(f'/tournaments/organizer/{tournament.slug}/matches/?tab=matches&status=active')
        assert resp.status_code == 200
        # Context should only have the live match
        matches = resp.context.get('matches')
        if matches is not None:
            states = [m.state for m in matches]
            assert 'scheduled' not in states

    def test_matches_tab_stats(self):
        """Stats show correct counts."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        bracket = _make_bracket(tournament)
        _make_match(tournament, bracket, state='live', match_number=1)
        _make_match(tournament, bracket, state='completed', match_number=2, winner_id=1, loser_id=2)
        _make_match(tournament, bracket, state='scheduled', match_number=3)

        client = _authed_client(organizer)
        resp = client.get(f'/tournaments/organizer/{tournament.slug}/matches/')
        assert resp.status_code == 200
        assert resp.context.get('total_matches') == 3
        assert resp.context.get('active_matches') == 1
        assert resp.context.get('completed_matches') == 1
