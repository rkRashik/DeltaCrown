"""
Phase 3 Part 2 Tests.

Covers:
- P3-T04: Scheduling Panel (auto-schedule, bulk-shift, add break)
- P3-T05: Dispute Resolution (start review, resolve, escalate)
- P3-T06: Participant Data Control (manual add, DQ cascade)
- P3-T07: Swiss Rounds 2+ (bye fix, subsequent round pairing, Buchholz)
- P3-T08: 3rd Place & GF Reset (config passthrough)

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
from apps.tournaments.models.match import Match, Dispute
from apps.tournaments.models.bracket import Bracket
from apps.tournaments.models.security import AuditLog

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
# P3-T04: Scheduling Panel
# ===========================================================================

@pytest.mark.django_db
class TestAutoScheduleRound:
    """P3-T04: Auto-schedule round endpoint."""

    def test_auto_schedule_assigns_times(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m1 = _make_match(t, b, round_number=1, match_number=1)
        m2 = _make_match(t, b, round_number=1, match_number=2)
        m3 = _make_match(t, b, round_number=2, match_number=1)

        client = _authed_client(org)
        start = (timezone.now() + timedelta(hours=1)).isoformat()

        resp = client.post(
            f'/tournaments/organizer/{t.slug}/auto-schedule-round/',
            json.dumps({'round_number': 1, 'start_time': start, 'slot_duration': 30, 'gap_minutes': 5}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['scheduled_count'] == 2

        m1.refresh_from_db()
        m2.refresh_from_db()
        m3.refresh_from_db()
        assert m1.scheduled_time is not None
        assert m2.scheduled_time is not None
        assert m3.scheduled_time is None  # Round 2 not scheduled

        # Check gap: m2 should be 35 min after m1
        diff = (m2.scheduled_time - m1.scheduled_time).total_seconds()
        assert diff == 35 * 60  # 30 slot + 5 gap

    def test_auto_schedule_requires_auth(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        client = Client()
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/auto-schedule-round/',
            json.dumps({'round_number': 1, 'start_time': '2025-01-01T10:00:00'}),
            content_type='application/json',
        )
        assert resp.status_code == 302  # Redirect to login

    def test_auto_schedule_round_not_found(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/auto-schedule-round/',
            json.dumps({'round_number': 99, 'start_time': '2025-06-01T10:00:00'}),
            content_type='application/json',
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestBulkShiftMatches:
    """P3-T04: Bulk shift matches endpoint."""

    def test_bulk_shift_forward(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        base = timezone.now() + timedelta(hours=2)
        m1 = _make_match(t, b, round_number=1, match_number=1, scheduled_time=base)
        m2 = _make_match(t, b, round_number=2, match_number=1, scheduled_time=base + timedelta(hours=1))

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/bulk-shift-matches/',
            json.dumps({'delta_minutes': 30}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['shifted_count'] == 2

        m1.refresh_from_db()
        m2.refresh_from_db()
        diff1 = (m1.scheduled_time - base).total_seconds()
        assert abs(diff1 - 30 * 60) < 1  # 30 min forward

    def test_bulk_shift_skips_completed(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        base = timezone.now() + timedelta(hours=2)
        m1 = _make_match(t, b, round_number=1, match_number=1,
                         scheduled_time=base, state='completed',
                         winner_id=1, loser_id=2)
        m2 = _make_match(t, b, round_number=2, match_number=1, scheduled_time=base)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/bulk-shift-matches/',
            json.dumps({'delta_minutes': 15}),
            content_type='application/json',
        )
        data = resp.json()
        assert data['shifted_count'] == 1  # Only m2 shifted

    def test_bulk_shift_specific_round(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        base = timezone.now() + timedelta(hours=2)
        m1 = _make_match(t, b, round_number=1, match_number=1, scheduled_time=base)
        m2 = _make_match(t, b, round_number=2, match_number=1, scheduled_time=base)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/bulk-shift-matches/',
            json.dumps({'delta_minutes': 10, 'round_number': 2}),
            content_type='application/json',
        )
        data = resp.json()
        assert data['shifted_count'] == 1  # Only round 2


@pytest.mark.django_db
class TestAddScheduleBreak:
    """P3-T04: Add break endpoint."""

    def test_add_break_shifts_subsequent_rounds(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        base = timezone.now() + timedelta(hours=2)
        m1 = _make_match(t, b, round_number=1, match_number=1, scheduled_time=base)
        m2 = _make_match(t, b, round_number=2, match_number=1,
                         scheduled_time=base + timedelta(hours=1))

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/add-schedule-break/',
            json.dumps({'after_round': 1, 'break_minutes': 15}),
            content_type='application/json',
        )
        data = resp.json()
        assert data['success'] is True
        assert data['shifted_count'] == 1  # Only round 2 shifted

        m1.refresh_from_db()
        m2.refresh_from_db()
        # m1 unchanged
        assert m1.scheduled_time == base
        # m2 shifted by 15 min
        expected = base + timedelta(hours=1) + timedelta(minutes=15)
        diff = abs((m2.scheduled_time - expected).total_seconds())
        assert diff < 1


# ===========================================================================
# P3-T05: Dispute Resolution
# ===========================================================================

@pytest.mark.django_db
class TestDisputeStartReview:
    """P3-T05: Start review (change dispute status to under_review)."""

    def test_start_review_updates_status(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m = _make_match(t, b)

        d = Dispute.objects.create(
            match=m,
            initiated_by_id=org.id,
            reason='score_mismatch',
            description='Scores are wrong',
            status='open',
        )

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/update-dispute-status/{d.id}/',
            json.dumps({'status': 'under_review'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        d.refresh_from_db()
        assert d.status == 'under_review'


@pytest.mark.django_db
class TestDisputeResolve:
    """P3-T05: Resolve dispute via resolve endpoint."""

    def test_resolve_accept_a(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m = _make_match(t, b, participant1_id=10, participant2_id=20)

        d = Dispute.objects.create(
            match=m,
            initiated_by_id=org.id,
            reason='score_mismatch',
            description='Score dispute',
            status='open',
        )

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/resolve-dispute/{d.id}/',
            json.dumps({
                'decision': 'ACCEPT_A',
                'resolution_notes': 'A was correct',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'success'

        m.refresh_from_db()
        assert m.winner_id == 10
        assert m.loser_id == 20

        d.refresh_from_db()
        assert d.status == 'resolved'

    def test_resolve_reject(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m = _make_match(t, b)

        d = Dispute.objects.create(
            match=m,
            initiated_by_id=org.id,
            reason='other',
            description='Baseless',
            status='open',
        )

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/resolve-dispute/{d.id}/',
            json.dumps({
                'decision': 'REJECT',
                'resolution_notes': 'No evidence',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        d.refresh_from_db()
        assert d.status == 'resolved'

    def test_resolve_override_scores(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m = _make_match(t, b, participant1_id=10, participant2_id=20)

        d = Dispute.objects.create(
            match=m,
            initiated_by_id=org.id,
            reason='score_mismatch',
            description='Wrong scores',
            status='open',
        )

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/resolve-dispute/{d.id}/',
            json.dumps({
                'decision': 'OVERRIDE',
                'resolution_notes': 'Reviewed evidence',
                'final_score_a': 13,
                'final_score_b': 7,
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200

        m.refresh_from_db()
        assert m.participant1_score == 13
        assert m.participant2_score == 7
        assert m.winner_id == 10  # A wins with higher score

    def test_resolve_requires_notes(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        m = _make_match(t, b)

        d = Dispute.objects.create(
            match=m, initiated_by_id=org.id,
            reason='other', description='Test', status='open',
        )

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/resolve-dispute/{d.id}/',
            json.dumps({'decision': 'ACCEPT_A', 'resolution_notes': ''}),
            content_type='application/json',
        )
        assert resp.status_code == 400


# ===========================================================================
# P3-T06: Participant Data Control
# ===========================================================================

@pytest.mark.django_db
class TestAddParticipantManually:
    """P3-T06: Add participant manually endpoint."""

    def test_add_participant_success(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        player = _make_user(username='testplayer99')

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/add-participant/',
            json.dumps({'username': 'testplayer99'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['username'] == 'testplayer99'

        reg = Registration.objects.get(tournament=t, user=player)
        assert reg.status == 'confirmed'
        assert reg.registration_data.get('manual_add') is True

    def test_add_participant_creates_audit_log(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        player = _make_user(username='audittest')

        client = _authed_client(org)
        client.post(
            f'/tournaments/organizer/{t.slug}/add-participant/',
            json.dumps({'username': 'audittest'}),
            content_type='application/json',
        )

        audit = AuditLog.objects.filter(
            tournament_id=t.id, action='manual_add_participant'
        ).first()
        assert audit is not None
        assert 'audittest' in audit.metadata.get('details', '')

    def test_add_duplicate_participant_fails(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        player = _make_user()
        _make_registration(t, player)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/add-participant/',
            json.dumps({'username': player.username}),
            content_type='application/json',
        )
        assert resp.status_code == 409

    def test_add_nonexistent_user_fails(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/add-participant/',
            json.dumps({'username': 'ghostuser_xxx'}),
            content_type='application/json',
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDQCascade:
    """P3-T06: Disqualify with cascade to matches."""

    def test_dq_cascade_forfeits_future_matches(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        player = _make_user()
        reg = _make_registration(t, player)

        pid = player.id
        m1 = _make_match(t, b, round_number=1, match_number=1,
                         participant1_id=pid, participant2_id=99, state='scheduled')
        m2 = _make_match(t, b, round_number=2, match_number=1,
                         participant1_id=pid, participant2_id=88, state='scheduled')
        # Completed match should NOT be forfeited
        m3 = _make_match(t, b, round_number=1, match_number=2,
                         participant1_id=pid, participant2_id=77,
                         state='completed', winner_id=pid, loser_id=77)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/dq-cascade/{reg.id}/',
            json.dumps({'reason': 'Cheating detected'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['forfeited_count'] == 2

        reg.refresh_from_db()
        assert reg.status == 'cancelled'
        assert reg.registration_data.get('disqualified') is True

        m1.refresh_from_db()
        assert m1.state == 'forfeit'
        assert m1.winner_id == 99  # Opponent wins

        m2.refresh_from_db()
        assert m2.state == 'forfeit'
        assert m2.winner_id == 88

        m3.refresh_from_db()
        assert m3.state == 'completed'  # Unchanged

    def test_dq_cascade_requires_reason(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        player = _make_user()
        reg = _make_registration(t, player)

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/dq-cascade/{reg.id}/',
            json.dumps({'reason': ''}),
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_dq_cascade_creates_audit_entries(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        player = _make_user()
        reg = _make_registration(t, player)
        pid = player.id
        _make_match(t, b, round_number=1, match_number=1,
                    participant1_id=pid, participant2_id=50)

        client = _authed_client(org)
        client.post(
            f'/tournaments/organizer/{t.slug}/dq-cascade/{reg.id}/',
            json.dumps({'reason': 'Test DQ'}),
            content_type='application/json',
        )

        dq_log = AuditLog.objects.filter(
            tournament_id=t.id, action='disqualify_participant'
        ).first()
        assert dq_log is not None

        cascade_log = AuditLog.objects.filter(
            tournament_id=t.id, action='dq_cascade_forfeit'
        ).first()
        assert cascade_log is not None


# ===========================================================================
# P3-T07: Swiss Rounds 2+ (Bug Fixes + Pairing Logic)
# ===========================================================================

@pytest.mark.django_db
class TestSwissByeMatchFix:
    """P3-T07: Verify bye match uses correct DTO fields."""

    def test_bye_match_uses_team_a_id_and_state(self):
        """The bye match should use team_a_id/team_b_id and state, not team1_id/team2_id/status."""
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator
        from apps.tournament_ops.dtos import TournamentDTO, StageDTO, TeamDTO

        generator = SwissSystemGenerator()

        # Create 5 participants (odd number → forces bye)
        tournament_dto = TournamentDTO(
            id=1, name='Test Swiss', game_slug='test', stage='bracket',
            team_size=1, max_teams=8, status='in_progress',
            start_time=timezone.now(), ruleset={},
        )
        stage_dto = StageDTO(
            id=1, name='Main', type='swiss', order=1,
            config={'rounds_count': 3},
            metadata={'rounds_count': 3},
        )

        participants = [
            TeamDTO(id=i, name=f'Team {i}', captain_id=i, captain_name=f'Cap {i}',
                    member_ids=[i], member_names=[f'Cap {i}'], game='test',
                    is_verified=True, logo_url=None)
            for i in range(1, 6)  # 5 teams
        ]

        matches = generator.generate_bracket(tournament_dto, stage_dto, participants)

        # Find the bye match
        bye_matches = [m for m in matches if m.team2_name == 'BYE']
        assert len(bye_matches) >= 1

        bye = bye_matches[0]
        # Must use team_a_id (not team1_id)
        assert hasattr(bye, 'team_a_id')
        assert bye.team_a_id is not None
        assert bye.team_b_id is None
        # Must use state (not status)
        assert bye.state == 'pending'


class TestSwissSubsequentRound:
    """P3-T07: Verify Swiss pairing for rounds 2+."""

    def test_pairs_by_win_count(self):
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator

        gen = SwissSystemGenerator()
        standings = [
            {'team_id': 1, 'wins': 2, 'losses': 0, 'points': 10, 'buchholz': 3},
            {'team_id': 2, 'wins': 2, 'losses': 0, 'points': 8, 'buchholz': 2},
            {'team_id': 3, 'wins': 1, 'losses': 1, 'points': 6, 'buchholz': 2},
            {'team_id': 4, 'wins': 1, 'losses': 1, 'points': 5, 'buchholz': 1},
            {'team_id': 5, 'wins': 0, 'losses': 2, 'points': 3, 'buchholz': 3},
            {'team_id': 6, 'wins': 0, 'losses': 2, 'points': 2, 'buchholz': 1},
        ]
        previous = [(1, 6), (2, 5), (3, 4)]

        pairings = gen.generate_subsequent_round(3, standings, previous)
        assert len(pairings) == 3

        # 2-0 teams should pair together (1 vs 2)
        top_pair = pairings[0]
        assert set(top_pair) == {1, 2}

    def test_avoids_rematches(self):
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator

        gen = SwissSystemGenerator()
        standings = [
            {'team_id': 1, 'wins': 1, 'losses': 0, 'points': 5, 'buchholz': 1},
            {'team_id': 2, 'wins': 1, 'losses': 0, 'points': 4, 'buchholz': 1},
            {'team_id': 3, 'wins': 0, 'losses': 1, 'points': 2, 'buchholz': 1},
            {'team_id': 4, 'wins': 0, 'losses': 1, 'points': 1, 'buchholz': 1},
        ]
        previous = [(1, 2), (3, 4)]  # R1 pairings

        pairings = gen.generate_subsequent_round(2, standings, previous)
        assert len(pairings) == 2

        # Should NOT pair 1v2 or 3v4 again
        for a, b in pairings:
            if a and b:
                assert frozenset((a, b)) not in {frozenset((1, 2)), frozenset((3, 4))}

    def test_odd_count_bye(self):
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator

        gen = SwissSystemGenerator()
        standings = [
            {'team_id': 1, 'wins': 1, 'losses': 0, 'points': 5, 'buchholz': 1},
            {'team_id': 2, 'wins': 1, 'losses': 0, 'points': 4, 'buchholz': 1},
            {'team_id': 3, 'wins': 0, 'losses': 1, 'points': 2, 'buchholz': 0},
        ]
        previous = [(1, 3)]

        pairings = gen.generate_subsequent_round(2, standings, previous)
        # Should have 1 real pairing + 1 bye
        bye_pairings = [p for p in pairings if p[1] is None]
        assert len(bye_pairings) == 1
        # Lowest-ranked should get bye
        assert bye_pairings[0][0] == 3

    def test_buchholz_tiebreaker(self):
        """Higher Buchholz should be ranked higher when wins/points are tied."""
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator

        gen = SwissSystemGenerator()
        standings = [
            {'team_id': 1, 'wins': 1, 'losses': 0, 'points': 5, 'buchholz': 5},
            {'team_id': 2, 'wins': 1, 'losses': 0, 'points': 5, 'buchholz': 2},
            {'team_id': 3, 'wins': 0, 'losses': 1, 'points': 2, 'buchholz': 5},
            {'team_id': 4, 'wins': 0, 'losses': 1, 'points': 2, 'buchholz': 1},
        ]
        previous = [(1, 4), (2, 3)]

        pairings = gen.generate_subsequent_round(2, standings, previous)
        assert len(pairings) == 2
        # With Buchholz tiebreaker, team 1 (higher buch) should pair with team 2
        top_pair = pairings[0]
        assert set(top_pair) == {1, 2}

    def test_empty_standings_returns_empty(self):
        from apps.tournament_ops.services.bracket_generators.swiss import SwissSystemGenerator
        gen = SwissSystemGenerator()
        assert gen.generate_subsequent_round(2, [], []) == []


# ===========================================================================
# P3-T08: 3rd Place & Grand Finals Reset Config Passthrough
# ===========================================================================

@pytest.mark.django_db
class TestThirdPlaceConfig:
    """P3-T08: Verify third_place_match config passes through."""

    @patch('apps.tournaments.views.organizer_brackets.BracketEngineService')
    def test_third_place_config_passed_to_engine(self, MockEngine):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        for i in range(4):
            _make_registration(t, _make_user())

        mock_engine = MagicMock()
        mock_engine.generate_bracket_for_stage.return_value = [
            MagicMock(round_number=1, match_number=1, team_a_id=1, team_b_id=2,
                      team1_name='A', team2_name='B'),
            MagicMock(round_number=1, match_number=2, team_a_id=3, team_b_id=4,
                      team1_name='C', team2_name='D'),
            MagicMock(round_number=2, match_number=1, team_a_id=None, team_b_id=None,
                      team1_name='TBD', team2_name='TBD'),
        ]
        MockEngine.return_value = mock_engine

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/generate-bracket/',
            json.dumps({
                'format': 'single-elimination',
                'seeding_method': 'slot-order',
                'config': {'third_place_match': True},
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200

        call_args = mock_engine.generate_bracket_for_stage.call_args
        stage_dto = call_args.kwargs.get('stage') or call_args[1].get('stage') or call_args[0][1]
        assert stage_dto.config.get('third_place_match') is True

    @patch('apps.tournaments.views.organizer_brackets.BracketEngineService')
    def test_gf_reset_config_passed_to_engine(self, MockEngine):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        for i in range(4):
            _make_registration(t, _make_user())

        mock_engine = MagicMock()
        mock_engine.generate_bracket_for_stage.return_value = [
            MagicMock(round_number=1, match_number=1, team_a_id=1, team_b_id=2,
                      team1_name='A', team2_name='B'),
            MagicMock(round_number=1, match_number=2, team_a_id=3, team_b_id=4,
                      team1_name='C', team2_name='D'),
        ]
        MockEngine.return_value = mock_engine

        client = _authed_client(org)
        resp = client.post(
            f'/tournaments/organizer/{t.slug}/generate-bracket/',
            json.dumps({
                'format': 'double-elimination',
                'seeding_method': 'slot-order',
                'config': {'grand_finals_reset': True},
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200

        call_args = mock_engine.generate_bracket_for_stage.call_args
        stage_dto = call_args.kwargs.get('stage') or call_args[1].get('stage') or call_args[0][1]
        assert stage_dto.metadata.get('grand_finals_reset') is True


# ===========================================================================
# Schedule Tab — Round Data Context
# ===========================================================================

@pytest.mark.django_db
class TestScheduleTabContext:
    """P3-T04: Verify schedule tab passes round-by-round data."""

    def test_schedule_tab_includes_rounds_data(self):
        org = _make_user(is_staff=True)
        game = _make_game()
        t = _make_tournament(game, org)
        b = _make_bracket(t)
        _make_match(t, b, round_number=1, match_number=1)
        _make_match(t, b, round_number=1, match_number=2)
        _make_match(t, b, round_number=2, match_number=1)

        client = _authed_client(org)
        resp = client.get(f'/tournaments/organizer/{t.slug}/schedule/')
        assert resp.status_code == 200
        assert 'rounds_data' in resp.context
        assert len(resp.context['rounds_data']) == 2
        assert resp.context['rounds_data'][0]['round_number'] == 1
        assert resp.context['rounds_data'][0]['total'] == 2
        assert resp.context['rounds_data'][1]['round_number'] == 2
        assert resp.context['rounds_data'][1]['total'] == 1
