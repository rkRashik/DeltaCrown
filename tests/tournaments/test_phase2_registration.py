"""
Phase 2 Registration System Tests.

Covers:
- P2-T01: Guest Team Registration Mode
- P2-T02: Guest Team Cap & Soft Friction
- P2-T03: Duplicate Player Detection
- P2-T04: Waitlist Logic & Promotion

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.registration_service import RegistrationService

User = get_user_model()


# ===========================================================================
# Helpers (same pattern as Phase 1)
# ===========================================================================

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
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        participation_type=Tournament.TEAM,
        format='single_elimination',
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    uid = _uid()
    uname = username or f'user-{uid}'
    defaults = dict(username=uname, email=f'{uname}@test.dc', password='test1234')
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _guest_team_data(uid=None, members=None):
    """Build valid guest_team_data dict."""
    uid = uid or _uid()
    if members is None:
        members = [
            {'game_id': f'player1#{uid}', 'display_name': f'Player1-{uid}'},
            {'game_id': f'player2#{uid}', 'display_name': f'Player2-{uid}'},
            {'game_id': f'player3#{uid}', 'display_name': f'Player3-{uid}'},
        ]
    return {
        'team_name': f'GuestTeam-{uid}',
        'team_tag': uid[:4].upper(),
        'captain': {'game_id': members[0]['game_id'], 'display_name': members[0]['display_name']},
        'members': members,
        'justification': 'New team, not yet registered on the platform.',
    }


# ===========================================================================
# P2-T01: Guest Team Registration Mode
# ===========================================================================

@pytest.mark.django_db
class TestGuestTeamRegistration:
    """P2-T01: Guest team registration creates valid Registration records."""

    def test_guest_team_creates_registration(self):
        """Guest team registration creates a Registration with is_guest_team=True."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        reg = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'captain#{_uid()}'},
        )

        assert reg.is_guest_team is True
        assert reg.user == user
        assert reg.team_id is None
        assert reg.status == Registration.PENDING
        assert 'guest_team' in reg.registration_data
        assert reg.registration_data['guest_team']['team_name'].startswith('GuestTeam-')

    def test_guest_team_stores_member_data(self):
        """Guest team data preserves all member details in registration_data JSON."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)
        uid = _uid()
        members = [
            {'game_id': f'p1#{uid}', 'display_name': 'Alpha'},
            {'game_id': f'p2#{uid}', 'display_name': 'Bravo'},
        ]
        gtd = _guest_team_data(uid=uid, members=members)

        reg = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            is_guest_team=True,
            guest_team_data=gtd,
            registration_data={'game_id': f'captain#{uid}'},
        )

        stored = reg.registration_data['guest_team']
        assert len(stored['members']) == 2
        assert stored['members'][0]['game_id'] == f'p1#{uid}'
        assert stored['team_tag'] == uid[:4].upper()

    def test_guest_team_rejected_for_solo_tournament(self):
        """Guest teams cannot be used in solo tournaments."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO, max_guest_teams=5,
        )

        with pytest.raises(ValidationError, match="only allowed for team"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=_guest_team_data(),
                registration_data={'game_id': f'solo#{_uid()}'},
            )

    def test_guest_team_requires_team_name(self):
        """Missing team_name in guest_team_data raises ValidationError."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        bad_data = _guest_team_data()
        bad_data['team_name'] = ''

        with pytest.raises(ValidationError, match="team name is required"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=bad_data,
                registration_data={'game_id': f'x#{_uid()}'},
            )

    def test_guest_team_requires_team_tag(self):
        """Missing team_tag raises ValidationError."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        bad_data = _guest_team_data()
        bad_data['team_tag'] = ''

        with pytest.raises(ValidationError, match="team tag is required"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=bad_data,
                registration_data={'game_id': f'x#{_uid()}'},
            )

    def test_guest_team_tag_max_6_chars(self):
        """Team tag longer than 6 characters is rejected."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        bad_data = _guest_team_data()
        bad_data['team_tag'] = 'TOOLONG7'

        with pytest.raises(ValidationError, match="6 characters"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=bad_data,
                registration_data={'game_id': f'x#{_uid()}'},
            )

    def test_guest_team_requires_at_least_one_member(self):
        """Empty members list raises ValidationError."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        bad_data = _guest_team_data()
        bad_data['members'] = []

        with pytest.raises(ValidationError, match="At least one team member"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=bad_data,
                registration_data={'game_id': f'x#{_uid()}'},
            )


# ===========================================================================
# P2-T02: Guest Team Cap & Soft Friction
# ===========================================================================

@pytest.mark.django_db
class TestGuestTeamCap:
    """P2-T02: Tournament enforces max_guest_teams cap."""

    def test_guest_team_blocked_when_disabled(self):
        """max_guest_teams=0 rejects guest team registrations."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=0)

        with pytest.raises(ValidationError, match="does not allow guest team"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=_guest_team_data(),
                registration_data={'game_id': f'x#{_uid()}'},
            )

    def test_guest_team_cap_enforced(self):
        """Cannot exceed max_guest_teams limit."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=1)

        # First guest team succeeds
        user1 = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'a#{_uid()}'},
        )

        # Second guest team is blocked
        user2 = _make_user()
        with pytest.raises(ValidationError, match="Guest team slots are full"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user2,
                is_guest_team=True,
                guest_team_data=_guest_team_data(),
                registration_data={'game_id': f'b#{_uid()}'},
            )

    def test_one_guest_team_per_user_per_tournament(self):
        """Same user cannot register two guest teams in one tournament."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        # First works
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'a#{_uid()}'},
        )

        # Second from same user fails
        with pytest.raises(ValidationError, match="already submitted a guest team"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                is_guest_team=True,
                guest_team_data=_guest_team_data(),
                registration_data={'game_id': f'b#{_uid()}'},
            )

    def test_cancelled_guest_doesnt_count_toward_cap(self):
        """Cancelled guest registrations free up cap slots."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=1)

        user1 = _make_user()
        reg = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'a#{_uid()}'},
        )

        # Cancel it
        reg.status = Registration.CANCELLED
        reg.save(update_fields=['status'])

        # New user can now register a guest team
        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'b#{_uid()}'},
        )
        assert reg2.is_guest_team is True


# ===========================================================================
# P2-T03: Duplicate Player Detection
# ===========================================================================

@pytest.mark.django_db
class TestDuplicatePlayerDetection:
    """P2-T03: Same game ID cannot appear in two active registrations."""

    def test_duplicate_game_id_blocked(self):
        """Second registration with same game_id is rejected."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO,
        )
        gid = f'DupePlayer#{_uid()}'

        user1 = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': gid},
        )

        user2 = _make_user()
        with pytest.raises(ValidationError, match="already registered"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user2,
                registration_data={'game_id': gid},
            )

    def test_duplicate_game_id_case_insensitive(self):
        """Game ID duplicate check is case-insensitive."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO,
        )
        uid = _uid()

        user1 = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': f'Player#{uid}'},
        )

        user2 = _make_user()
        with pytest.raises(ValidationError, match="already registered"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user2,
                registration_data={'game_id': f'PLAYER#{uid}'},
            )

    def test_cancelled_registration_allows_reuse(self):
        """Game ID from a cancelled registration can be reused."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO,
        )
        gid = f'Freed#{_uid()}'

        user1 = _make_user()
        reg = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': gid},
        )

        # Cancel
        reg.status = Registration.CANCELLED
        reg.save(update_fields=['status'])

        # Different user can now use the same game_id
        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            registration_data={'game_id': gid},
        )
        assert reg2.registration_data['game_id'] == gid

    def test_guest_team_member_id_blocks_solo_duplicate(self):
        """Game ID appearing in guest team members blocks a solo registration with same ID."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, max_guest_teams=5)

        uid = _uid()
        shared_gid = f'shared#{uid}'

        # Register guest team with shared_gid as a member
        user1 = _make_user()
        members = [
            {'game_id': shared_gid, 'display_name': 'SharedPlayer'},
            {'game_id': f'other#{uid}', 'display_name': 'Other'},
        ]
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            is_guest_team=True,
            guest_team_data=_guest_team_data(uid=uid, members=members),
            registration_data={'game_id': f'captain#{uid}'},
        )

        # Another user trying to register with the same game ID is blocked
        user2 = _make_user()
        with pytest.raises(ValidationError, match="already registered as a member"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user2,
                is_guest_team=True,
                guest_team_data=_guest_team_data(),
                registration_data={'game_id': shared_gid},
            )

    def test_no_game_id_skips_check(self):
        """If game_id is empty no duplicate check runs."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO,
        )

        user1 = _make_user()
        reg1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': ''},
        )

        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            registration_data={'game_id': ''},
        )
        assert reg1.id != reg2.id


# ===========================================================================
# P2-T04: Waitlist Logic & Promotion
# ===========================================================================

@pytest.mark.django_db
class TestWaitlistAutoAssign:
    """P2-T04: Registrations beyond capacity go to waitlist."""

    def test_at_capacity_goes_to_waitlist(self):
        """Registration at max_participants gets WAITLISTED status."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        # Fill both slots
        for _ in range(2):
            u = _make_user()
            reg = RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=u,
                registration_data={'game_id': f'fill#{_uid()}'},
            )
            assert reg.status == Registration.PENDING

        # Third goes to waitlist
        user3 = _make_user()
        reg3 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user3,
            registration_data={'game_id': f'wl#{_uid()}'},
        )
        assert reg3.status == Registration.WAITLISTED
        assert reg3.waitlist_position == 1

    def test_waitlist_position_increments(self):
        """Multiple waitlisted registrations get sequential positions."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        # Fill both slots
        for _ in range(2):
            u = _make_user()
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=u,
                registration_data={'game_id': f'fill#{_uid()}'},
            )

        # Waitlist entries
        positions = []
        for i in range(3):
            u = _make_user()
            r = RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=u,
                registration_data={'game_id': f'w{i}#{_uid()}'},
            )
            positions.append(r.waitlist_position)

        assert positions == [1, 2, 3]

    def test_guest_team_always_pending_not_waitlisted(self):
        """Guest teams get PENDING (for organizer review), not WAITLISTED even when full."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            max_guest_teams=5,
        )

        # Fill both slots with guest teams
        user1 = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'a#{_uid()}'},
        )
        filler = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=filler,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'fill#{_uid()}'},
        )

        # Third guest team still PENDING, not WAITLISTED
        user3 = _make_user()
        reg3 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user3,
            is_guest_team=True,
            guest_team_data=_guest_team_data(),
            registration_data={'game_id': f'b#{_uid()}'},
        )
        assert reg3.status == Registration.PENDING


@pytest.mark.django_db
class TestWaitlistPromotion:
    """P2-T04: Waitlist promotion mechanics."""

    def test_promote_specific_registration(self):
        """Promote a specific waitlisted registration by ID."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        user1 = _make_user()
        reg1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': f'a#{_uid()}'},
        )
        filler = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=filler,
            registration_data={'game_id': f'fill#{_uid()}'},
        )

        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            registration_data={'game_id': f'b#{_uid()}'},
        )
        assert reg2.status == Registration.WAITLISTED

        # Cancel first to free a slot
        reg1.status = Registration.CANCELLED
        reg1.save(update_fields=['status'])

        # Promote
        promoted = RegistrationService.promote_from_waitlist(
            tournament_id=tournament.id,
            registration_id=reg2.id,
            promoted_by=organizer,
        )
        assert promoted.id == reg2.id
        promoted.refresh_from_db()
        assert promoted.status == Registration.PENDING
        assert promoted.waitlist_position is None

    def test_fifo_promotion(self):
        """Auto-promote picks the lowest waitlist_position."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        user1 = _make_user()
        reg1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': f'a#{_uid()}'},
        )
        filler = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=filler,
            registration_data={'game_id': f'fill#{_uid()}'},
        )

        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            registration_data={'game_id': f'b#{_uid()}'},
        )

        user3 = _make_user()
        reg3 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user3,
            registration_data={'game_id': f'c#{_uid()}'},
        )

        assert reg2.waitlist_position == 1
        assert reg3.waitlist_position == 2

        # Cancel first
        reg1.status = Registration.CANCELLED
        reg1.save(update_fields=['status'])

        # Auto-promote (FIFO)
        promoted = RegistrationService.auto_promote_waitlist(tournament.id)
        assert promoted.id == reg2.id
        promoted.refresh_from_db()
        assert promoted.status == Registration.PENDING

        # Reg3 should now be position 1
        reg3.refresh_from_db()
        assert reg3.waitlist_position == 1

    def test_promote_fails_when_full(self):
        """Cannot promote when tournament is still at capacity."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        user1 = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': f'a#{_uid()}'},
        )
        filler = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=filler,
            registration_data={'game_id': f'fill#{_uid()}'},
        )

        user2 = _make_user()
        reg2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user2,
            registration_data={'game_id': f'b#{_uid()}'},
        )
        assert reg2.status == Registration.WAITLISTED

        # Try to promote without freeing a slot
        with pytest.raises(ValidationError, match="still at capacity"):
            RegistrationService.promote_from_waitlist(
                tournament_id=tournament.id,
                registration_id=reg2.id,
            )

    def test_auto_promote_returns_none_when_empty(self):
        """Auto-promote returns None if no one is on the waitlist."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=16,
            participation_type=Tournament.SOLO,
        )

        result = RegistrationService.auto_promote_waitlist(tournament.id)
        assert result is None

    def test_waitlist_reorder_after_promote(self):
        """After promoting position 1, remaining positions reorder to 1, 2, ...."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, max_participants=2,
            participation_type=Tournament.SOLO,
        )

        user1 = _make_user()
        reg1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user1,
            registration_data={'game_id': f'a#{_uid()}'},
        )
        filler = _make_user()
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=filler,
            registration_data={'game_id': f'fill#{_uid()}'},
        )

        waitlisted = []
        for i in range(3):
            u = _make_user()
            r = RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=u,
                registration_data={'game_id': f'w{i}#{_uid()}'},
            )
            waitlisted.append(r)

        # Cancel slot holder
        reg1.status = Registration.CANCELLED
        reg1.save(update_fields=['status'])

        # Promote first
        RegistrationService.promote_from_waitlist(
            tournament_id=tournament.id,
            registration_id=waitlisted[0].id,
        )

        # Check remaining are reordered
        waitlisted[1].refresh_from_db()
        waitlisted[2].refresh_from_db()
        assert waitlisted[1].waitlist_position == 1
        assert waitlisted[2].waitlist_position == 2


# ===========================================================================
# P2-T01 + T02 Model fields
# ===========================================================================

@pytest.mark.django_db
class TestPhase2ModelFields:
    """Verify model-level field existence and defaults."""

    def test_registration_is_guest_team_default(self):
        """Registration.is_guest_team defaults to False."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(
            game, organizer, participation_type=Tournament.SOLO,
        )
        reg = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            registration_data={'game_id': f'x#{_uid()}'},
        )
        assert reg.is_guest_team is False

    def test_tournament_max_guest_teams_default(self):
        """Tournament.max_guest_teams defaults to 0."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        assert tournament.max_guest_teams == 0
