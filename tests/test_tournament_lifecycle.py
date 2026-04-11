# tests/test_tournament_lifecycle.py
"""
Tournament lifecycle and bounty model tests.

Covers:
- Tournament state machine transitions (allowed/disallowed)
- Tournament format choices and constant completeness
- TournamentBounty model structure and soft-delete
- User bounty (peer-to-peer) soft-delete integration
- Competition bounty soft-delete verification
"""
import pytest
from decimal import Decimal


class TestTournamentStatusMachine:
    """Verify Tournament model status constants and transition rules."""

    def test_model_importable(self):
        from apps.tournaments.models.tournament import Tournament
        assert Tournament is not None

    def test_status_constants_defined(self):
        from apps.tournaments.models.tournament import Tournament
        expected = {
            'draft', 'pending_approval', 'published',
            'registration_open', 'registration_closed',
            'live', 'completed', 'cancelled', 'archived',
        }
        actual = {c[0] for c in Tournament.STATUS_CHOICES}
        assert actual == expected

    def test_format_choices_complete(self):
        from apps.tournaments.models.tournament import Tournament
        formats = {c[0] for c in Tournament.FORMAT_CHOICES}
        assert 'single_elimination' in formats
        assert 'double_elimination' in formats
        assert 'round_robin' in formats
        assert 'swiss' in formats
        assert 'group_playoff' in formats

    def test_allowed_transitions_keys_match_statuses(self):
        from apps.tournaments.models.tournament import Tournament
        transition_keys = set(Tournament.ALLOWED_TRANSITIONS.keys())
        status_values = {c[0] for c in Tournament.STATUS_CHOICES}
        assert transition_keys == status_values, (
            f"Transition keys missing: {status_values - transition_keys}, "
            f"Extra keys: {transition_keys - status_values}"
        )

    def test_draft_can_reach_published(self):
        from apps.tournaments.models.tournament import Tournament
        assert 'published' in Tournament.ALLOWED_TRANSITIONS[Tournament.DRAFT]

    def test_draft_can_reach_cancelled(self):
        from apps.tournaments.models.tournament import Tournament
        assert 'cancelled' in Tournament.ALLOWED_TRANSITIONS[Tournament.DRAFT]

    def test_live_cannot_go_back_to_registration(self):
        from apps.tournaments.models.tournament import Tournament
        assert 'registration_open' not in Tournament.ALLOWED_TRANSITIONS[Tournament.LIVE]

    def test_completed_can_only_archive(self):
        from apps.tournaments.models.tournament import Tournament
        allowed = Tournament.ALLOWED_TRANSITIONS[Tournament.COMPLETED]
        assert allowed == frozenset({'archived'})

    def test_archived_is_terminal(self):
        from apps.tournaments.models.tournament import Tournament
        assert len(Tournament.ALLOWED_TRANSITIONS[Tournament.ARCHIVED]) == 0

    def test_cancelled_can_only_archive(self):
        from apps.tournaments.models.tournament import Tournament
        allowed = Tournament.ALLOWED_TRANSITIONS[Tournament.CANCELLED]
        assert allowed == frozenset({'archived'})

    def test_registration_open_leads_to_closed_or_cancelled(self):
        from apps.tournaments.models.tournament import Tournament
        allowed = Tournament.ALLOWED_TRANSITIONS[Tournament.REGISTRATION_OPEN]
        assert 'registration_closed' in allowed
        assert 'cancelled' in allowed

    def test_no_self_transitions(self):
        """No state should allow transitioning to itself."""
        from apps.tournaments.models.tournament import Tournament
        for state, targets in Tournament.ALLOWED_TRANSITIONS.items():
            assert state not in targets, f"Self-transition detected: {state}"

    def test_tournament_uses_soft_delete(self):
        from apps.tournaments.models.tournament import Tournament
        from apps.common.models import SoftDeleteModel
        assert issubclass(Tournament, SoftDeleteModel)


class TestTournamentBountyModel:
    """Verify TournamentBounty model structure and soft-delete."""

    def test_model_importable(self):
        from apps.tournaments.models.bounty import TournamentBounty
        assert TournamentBounty is not None

    def test_uses_soft_delete(self):
        from apps.tournaments.models.bounty import TournamentBounty
        from apps.common.models import SoftDeleteModel
        assert issubclass(TournamentBounty, SoftDeleteModel)

    def test_has_soft_delete_fields(self):
        from apps.tournaments.models.bounty import TournamentBounty
        field_names = {f.name for f in TournamentBounty._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_has_soft_delete_methods(self):
        from apps.tournaments.models.bounty import TournamentBounty
        assert hasattr(TournamentBounty, 'soft_delete')
        assert hasattr(TournamentBounty, 'restore')

    def test_bounty_type_choices_complete(self):
        from apps.tournaments.models.bounty import TournamentBounty
        types = {c[0] for c in TournamentBounty.BOUNTY_TYPE_CHOICES}
        assert 'mvp' in types
        assert 'stat_leader' in types
        assert 'community_vote' in types
        assert 'special_achievement' in types
        assert 'custom' in types

    def test_source_choices_complete(self):
        from apps.tournaments.models.bounty import TournamentBounty
        sources = {c[0] for c in TournamentBounty.SOURCE_CHOICES}
        assert 'prize_pool' in sources
        assert 'sponsor' in sources
        assert 'platform' in sources

    def test_claim_status_choices_complete(self):
        from apps.tournaments.models.bounty import TournamentBounty
        statuses = {c[0] for c in TournamentBounty.CLAIM_STATUS_CHOICES}
        assert 'pending' in statuses
        assert 'claimed' in statuses
        assert 'paid_out' in statuses

    def test_has_assign_method(self):
        from apps.tournaments.models.bounty import TournamentBounty
        assert hasattr(TournamentBounty, 'assign')

    def test_uuid_primary_key(self):
        from apps.tournaments.models.bounty import TournamentBounty
        pk_field = TournamentBounty._meta.pk
        assert pk_field.name == 'id'
        from django.db.models import UUIDField
        assert isinstance(pk_field, UUIDField)


class TestUserBountySoftDelete:
    """Verify user_profile Bounty model has soft-delete."""

    def test_model_importable(self):
        from apps.user_profile.models.bounties import Bounty
        assert Bounty is not None

    def test_uses_soft_delete(self):
        from apps.user_profile.models.bounties import Bounty
        from apps.common.models import SoftDeleteModel
        assert issubclass(Bounty, SoftDeleteModel)

    def test_has_soft_delete_fields(self):
        from apps.user_profile.models.bounties import Bounty
        field_names = {f.name for f in Bounty._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_bounty_status_choices_exist(self):
        from apps.user_profile.models.bounties import BountyStatus
        assert BountyStatus.OPEN == 'open'
        assert BountyStatus.COMPLETED == 'completed'
        assert BountyStatus.EXPIRED == 'expired'
        assert BountyStatus.CANCELLED == 'cancelled'

    def test_bounty_type_choices_exist(self):
        from apps.user_profile.models.bounties import BountyType
        assert BountyType.SOLO == 'solo'
        assert BountyType.TEAM == 'team'


class TestCompetitionBountySoftDelete:
    """Verify competition Bounty model has soft-delete."""

    def test_model_importable(self):
        try:
            from apps.competition.models.bounty import Bounty
            assert Bounty is not None
        except ImportError:
            pytest.skip("competition.models.bounty not available")

    def test_uses_soft_delete(self):
        try:
            from apps.competition.models.bounty import Bounty
            from apps.common.models import SoftDeleteModel
            assert issubclass(Bounty, SoftDeleteModel)
        except ImportError:
            pytest.skip("competition.models.bounty not available")


class TestMatchModelSoftDelete:
    """Verify Match model uses soft-delete."""

    def test_model_importable(self):
        from apps.tournaments.models.match import Match
        assert Match is not None

    def test_uses_soft_delete(self):
        from apps.tournaments.models.match import Match
        from apps.common.models import SoftDeleteModel
        assert issubclass(Match, SoftDeleteModel)

    def test_has_soft_delete_fields(self):
        from apps.tournaments.models.match import Match
        field_names = {f.name for f in Match._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names

    def test_match_status_choices_exist(self):
        from apps.tournaments.models.match import Match
        statuses = {c[0] for c in Match.STATE_CHOICES}
        assert 'scheduled' in statuses
        assert 'live' in statuses
        assert 'completed' in statuses
        assert 'disputed' in statuses


class TestSoftDeleteModelInterface:
    """Verify the base SoftDeleteModel contract."""

    def test_soft_delete_model_is_abstract(self):
        from apps.common.models import SoftDeleteModel
        assert SoftDeleteModel._meta.abstract is True

    def test_soft_delete_has_required_fields(self):
        from apps.common.models import SoftDeleteModel
        field_names = {f.name for f in SoftDeleteModel._meta.local_fields}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_soft_delete_has_required_methods(self):
        from apps.common.models import SoftDeleteModel
        assert hasattr(SoftDeleteModel, 'soft_delete')
        assert hasattr(SoftDeleteModel, 'restore')

    def test_is_deleted_default_false(self):
        from apps.common.models import SoftDeleteModel
        field = SoftDeleteModel._meta.get_field('is_deleted')
        assert field.default is False

    def test_is_deleted_is_indexed(self):
        from apps.common.models import SoftDeleteModel
        field = SoftDeleteModel._meta.get_field('is_deleted')
        assert field.db_index is True
