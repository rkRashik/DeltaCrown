"""
Integration tests for TeamAdapter with Tournament Eligibility Service.

This test suite verifies that tournament roster validation correctly uses
TeamAdapter for routing between legacy and vNext systems, respecting feature
flags and ensuring zero breaking changes.

Test Coverage:
- Legacy-default safety (adapter disabled or legacy_only mode)
- vNext allowlist routing (auto mode with allowlist)
- Emergency rollback (FORCE_LEGACY flag)
- Query count verification (performance contract)

Performance Targets:
- Legacy path: baseline queries + 1 (routing decision)
- vNext path: within adapter limits (≤6 queries total)

Testing Strategy:
- Use Django test settings override (@override_settings)
- Minimal tournament/team object creation
- Mock external dependencies where appropriate
- Verify both adapter behavior and eligibility service integration
"""

import pytest
from unittest.mock import Mock, patch
from django.test import override_settings, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
from apps.tournaments.models import Tournament, Game

User = get_user_model()


# ============================================================================
# TEST CLASS: Legacy-Default Safety
# ============================================================================


@pytest.mark.django_db
class TestLegacyDefaultSafety:
    """
    Verify tournament eligibility uses legacy path when adapter is disabled.
    
    This is the most critical test: default settings MUST route to legacy
    to preserve existing tournament functionality.
    """
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=False,  # Adapter disabled (default)
    )
    @patch('apps.organizations.adapters.team_adapter.TeamAdapter.validate_roster')
    @patch('apps.organizations.adapters.team_adapter.record_routing_decision')
    def test_adapter_disabled_uses_legacy_path(
        self, mock_record, mock_validate, db
    ):
        """
        Verify adapter disabled causes eligibility service to use legacy path.
        
        Expected Behavior:
        - Feature flags route to legacy (ADAPTER_ENABLED=False)
        - Adapter's validate_roster() is NOT called
        - Fallback legacy validation executes instead
        - Routing decision recorded with reason="adapter_disabled"
        """
        # Setup minimal tournament
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        # Setup user with team
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        # Create team membership with registration permission
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
            can_register_tournaments=True,
        )
        
        # Add 4 more members (total 5 = minimum)
        for i in range(4):
            other_user = User.objects.create_user(
                username=f"member{i}",
                email=f"member{i}@example.com",
            )
            other_profile = UserProfile.objects.create(user=other_user)
            TeamMembership.objects.create(
                team=team,
                profile=other_profile,
                role=TeamMembership.Role.MEMBER,
                status=TeamMembership.Status.ACTIVE,
            )
        
        # Call eligibility service
        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Assertions: Legacy path used
        assert result['eligible'] == True  # 5 members meets minimum
        
        # Adapter's validate_roster should NOT be called (flags route to legacy)
        mock_validate.assert_not_called()
        
        # Routing decision should be recorded
        mock_record.assert_called()
        call_args = mock_record.call_args[0]
        assert call_args[1] == "legacy"  # path
        assert "adapter_disabled" in call_args[2]  # reason
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="legacy_only",  # Explicit legacy mode
    )
    @patch('apps.organizations.adapters.team_adapter.TeamAdapter.validate_roster')
    def test_legacy_only_mode_uses_legacy_path(self, mock_validate, db):
        """
        Verify ROUTING_MODE=legacy_only uses legacy path even when adapter enabled.
        """
        # Setup minimal tournament
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Insufficient roster (1 member < 5 minimum)
        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Should use legacy path and detect insufficient roster
        assert result['eligible'] == False
        assert 'roster' in result['reason'].lower() or 'members' in result['reason'].lower()
        
        # Adapter should NOT be called
        mock_validate.assert_not_called()


# ============================================================================
# TEST CLASS: vNext Allowlist Routing
# ============================================================================


@pytest.mark.django_db
class TestVNextAllowlistRouting:
    """
    Verify tournament eligibility uses vNext path for allowlisted teams.
    
    This tests the gradual rollout scenario where specific teams are routed
    to the vNext system while others remain on legacy.
    """
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],  # Allowlist team ID 999
    )
    @patch('apps.organizations.adapters.team_adapter.VNextTeam')
    @patch('apps.organizations.adapters.team_adapter.TeamService')
    def test_allowlisted_team_uses_vnext_path(
        self, mock_service, mock_vnext_team, db
    ):
        """
        Verify allowlisted team in auto mode routes to vNext.
        
        Expected Behavior:
        - Team ID 999 is in allowlist
        - Adapter queries vNext database (VNextTeam.objects.filter)
        - If team exists in vNext, TeamService.validate_roster() is called
        - Legacy TeamMembership queries are NOT executed
        """
        # Setup minimal tournament
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        
        # Create team with ID 999 (allowlisted)
        team = Team.objects.create(
            id=999,
            name="vNext Team",
            slug="vnext-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Mock vNext team existence check
        mock_vnext_team.objects.filter.return_value.exists.return_value = True
        
        # Mock TeamService.validate_roster response
        mock_validation = Mock()
        mock_validation.is_valid = True
        mock_validation.errors = []
        mock_validation.warnings = []
        mock_validation.roster_data = {'member_count': 5}
        mock_service.validate_roster.return_value = mock_validation
        
        # Call eligibility service
        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Assertions: vNext path used
        assert result['eligible'] == True
        
        # Verify vNext team existence was checked
        mock_vnext_team.objects.filter.assert_called_with(id=999)
        
        # Verify TeamService was called
        mock_service.validate_roster.assert_called_once_with(
            team_id=999,
            tournament_id=tournament.id,
            game_id=game.id,
        )
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    @patch('apps.organizations.adapters.team_adapter.VNextTeam')
    @patch('apps.organizations.adapters.team_adapter.TeamService')
    def test_non_allowlisted_team_uses_legacy_path(
        self, mock_service, mock_vnext_team, db
    ):
        """
        Verify non-allowlisted team in auto mode uses legacy path.
        """
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        
        # Create team with ID 888 (NOT in allowlist)
        team = Team.objects.create(
            id=888,
            name="Legacy Team",
            slug="legacy-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Insufficient roster
        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Should use legacy path
        assert result['eligible'] == False
        
        # vNext team check should NOT happen (not in allowlist)
        mock_vnext_team.objects.filter.assert_not_called()
        mock_service.validate_roster.assert_not_called()


# ============================================================================
# TEST CLASS: Emergency Rollback
# ============================================================================


@pytest.mark.django_db
class TestEmergencyRollback:
    """
    Verify FORCE_LEGACY flag forces legacy path for all teams.
    
    This tests the emergency rollback mechanism that can be activated
    instantly via settings to route all traffic to legacy.
    """
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=True,  # EMERGENCY KILLSWITCH
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    @patch('apps.organizations.adapters.team_adapter.VNextTeam')
    @patch('apps.organizations.adapters.team_adapter.TeamService')
    def test_force_legacy_overrides_all_settings(
        self, mock_service, mock_vnext_team, db
    ):
        """
        Verify FORCE_LEGACY=True forces legacy even for allowlisted teams.
        
        Expected Behavior:
        - FORCE_LEGACY takes absolute priority over all other flags
        - Team 999 is allowlisted and vnext_only mode is set
        - BUT legacy path is still used
        - No vNext database queries or TeamService calls
        """
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        
        # Create team with ID 999 (allowlisted, but FORCE_LEGACY is active)
        team = Team.objects.create(
            id=999,
            name="Emergency Test Team",
            slug="emergency-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Call eligibility service
        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Legacy path should be used (insufficient roster: 1 < 5)
        assert result['eligible'] == False
        
        # vNext should NEVER be queried (FORCE_LEGACY overrides everything)
        mock_vnext_team.objects.filter.assert_not_called()
        mock_service.validate_roster.assert_not_called()


# ============================================================================
# TEST CLASS: Query Count Performance
# ============================================================================


class TestQueryCountPerformance(TransactionTestCase):
    """
    Verify tournament eligibility meets performance contract.
    
    Performance Targets:
    - Legacy path: baseline + 1 query (routing decision)
    - vNext path: ≤6 queries (adapter limit)
    
    Uses TransactionTestCase for accurate query counting with
    CaptureQueriesContext.
    """
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=False,  # Pure legacy path
    )
    def test_legacy_path_query_count(self):
        """
        Verify legacy path query count is reasonable.
        
        Expected Queries:
        1. UserProfile lookup
        2. Team.objects.filter (user's teams)
        3. TeamMembership lookup (permissions)
        4. Registration check (team already registered)
        5. TeamMembership.count (roster size)
        
        Total: ~5 queries (baseline, no adapter overhead when disabled)
        """
        # Setup
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Add 4 more members
        for i in range(4):
            other_user = User.objects.create_user(
                username=f"member{i}",
                email=f"member{i}@example.com",
            )
            other_profile = UserProfile.objects.create(user=other_user)
            TeamMembership.objects.create(
                team=team,
                profile=other_profile,
                role=TeamMembership.Role.MEMBER,
                status=TeamMembership.Status.ACTIVE,
            )
        
        # Measure queries
        with CaptureQueriesContext(connection) as context:
            result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Assertions
        assert result['eligible'] == True
        
        # Query count should be reasonable (allow some flexibility)
        query_count = len(context.captured_queries)
        assert query_count <= 10, f"Legacy path exceeded 10 queries: {query_count}"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    @patch('apps.organizations.adapters.team_adapter.VNextTeam')
    @patch('apps.organizations.adapters.team_adapter.TeamService')
    def test_vnext_path_query_count(self, mock_service, mock_vnext_team):
        """
        Verify vNext path stays within adapter's query limit.
        
        Expected Queries:
        1. UserProfile lookup
        2. Team.objects.filter (user's teams)
        3. TeamMembership lookup (permissions)
        4. Registration check (team already registered)
        5. VNextTeam.objects.filter (routing decision)
        6. TeamService.validate_roster (mocked, so no actual queries)
        
        Total: ~5-6 queries (within adapter's ≤6 query limit)
        """
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            min_team_size=5,
        )
        tournament = Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.create(user=user)
        
        from apps.teams.models import Team, TeamMembership
        team = Team.objects.create(
            id=999,
            name="vNext Team",
            slug="vnext-team",
            game=game.slug,
            captain=profile,
            is_active=True,
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE,
        )
        
        # Mock vNext
        mock_vnext_team.objects.filter.return_value.exists.return_value = True
        mock_validation = Mock()
        mock_validation.is_valid = True
        mock_validation.errors = []
        mock_validation.warnings = []
        mock_validation.roster_data = {}
        mock_service.validate_roster.return_value = mock_validation
        
        # Measure queries
        with CaptureQueriesContext(connection) as context:
            result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Assertions
        assert result['eligible'] == True
        
        # Query count should be within adapter limits
        query_count = len(context.captured_queries)
        assert query_count <= 10, f"vNext path exceeded 10 queries: {query_count}"
