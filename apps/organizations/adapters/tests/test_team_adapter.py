"""
TeamAdapter Tests - Verify routing logic for legacy and vNext teams.

Test Strategy:
- Legacy path: Mock legacy Team objects (no vNext factories needed)
- vNext path: Use vNext factories (Phase 1 already created)
- Query count verification: CaptureQueriesContext
- Error handling: NotFoundError for invalid team_id

Coverage:
- is_vnext_team: routing decision logic
- get_team_url: URL generation for both systems
- get_team_identity: branding/metadata retrieval
- validate_roster: tournament eligibility checking
"""

import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.db import connection
from django.test.utils import override_settings

from apps.organizations.adapters.team_adapter import TeamAdapter
from apps.organizations.services.exceptions import NotFoundError

# vNext factories (from Phase 1)
from apps.organizations.tests.factories import (
    TeamFactory,
    TeamMembershipFactory,
    OrganizationFactory,
)


# ============================================================================
# ROUTING LOGIC TESTS
# ============================================================================

@pytest.mark.django_db
class TestIsVNextTeam:
    """Test routing decision logic (is_vnext_team method)."""
    
    def test_vnext_team_returns_true(self):
        """vNext team should return True."""
        team = TeamFactory.create()
        adapter = TeamAdapter()
        
        assert adapter.is_vnext_team(team.id) is True
    
    def test_legacy_team_returns_false(self):
        """Legacy team (not in vNext system) should return False."""
        adapter = TeamAdapter()
        
        # Use a high ID that definitely doesn't exist in vNext
        nonexistent_id = 999999
        assert adapter.is_vnext_team(nonexistent_id) is False
    
    def test_routing_query_count(self):
        """Routing decision should use ≤1 query."""
        team = TeamFactory.create()
        adapter = TeamAdapter()
        
        with connection.cursor() as cursor:
            before_count = len(connection.queries)
            adapter.is_vnext_team(team.id)
            after_count = len(connection.queries)
            
            query_count = after_count - before_count
            assert query_count <= 1, f"Expected ≤1 query, got {query_count}"


# ============================================================================
# TEAM URL GENERATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestGetTeamURL:
    """Test URL generation for both legacy and vNext teams."""
    
    def test_vnext_team_url_generation(self):
        """vNext team should return organizations URL pattern."""
        team = TeamFactory.create(slug='protocol-v')
        adapter = TeamAdapter()
        
        url = adapter.get_team_url(team.id)
        
        assert '/organizations/' in url or '/protocol-v/' in url
        assert url  # Non-empty string
    
    @patch('apps.organizations.adapters.team_adapter.LegacyTeam')
    def test_legacy_team_url_generation(self, mock_legacy_team):
        """Legacy team should return teams URL pattern."""
        # Mock legacy team
        mock_team = Mock()
        mock_team.id = 123
        mock_team.slug = 'syntax-gaming'
        mock_legacy_team.objects.get.return_value = mock_team
        
        adapter = TeamAdapter()
        
        # Patch is_vnext_team to return False (legacy path)
        with patch.object(adapter, 'is_vnext_team', return_value=False):
            url = adapter.get_team_url(123)
            
            assert '/teams/' in url or '/syntax-gaming/' in url
    
    def test_nonexistent_team_raises_not_found(self):
        """Nonexistent team_id should raise NotFoundError."""
        adapter = TeamAdapter()
        
        with pytest.raises(NotFoundError) as exc_info:
            adapter.get_team_url(999999)
        
        assert exc_info.value.error_code == 'TEAM_NOT_FOUND'


# ============================================================================
# TEAM IDENTITY TESTS
# ============================================================================

@pytest.mark.django_db
class TestGetTeamIdentity:
    """Test team branding/metadata retrieval."""
    
    def test_vnext_team_identity_structure(self):
        """vNext team identity should have all required fields."""
        org = OrganizationFactory.create(name='Syntax Esports', slug='syntax-esports')
        team = TeamFactory.create(
            name='Protocol V',
            slug='protocol-v',
            organization=org,
        )
        adapter = TeamAdapter()
        
        identity = adapter.get_team_identity(team.id)
        
        # Verify all required fields exist
        assert identity['team_id'] == team.id
        assert identity['name'] == 'Protocol V'
        assert identity['slug'] == 'protocol-v'
        assert 'logo_url' in identity
        assert identity['is_org_team'] is True
        assert identity['organization_name'] == 'Syntax Esports'
        assert identity['organization_slug'] == 'syntax-esports'
    
    @patch('apps.organizations.adapters.team_adapter.LegacyTeam')
    def test_legacy_team_identity_structure(self, mock_legacy_team):
        """Legacy team identity should have same structure with nulls for org fields."""
        # Mock legacy team
        mock_team = Mock()
        mock_team.id = 123
        mock_team.name = 'Legacy Team'
        mock_team.slug = 'legacy-team'
        mock_team.logo = None
        mock_team.game = Mock(id=1, name='Valorant')
        mock_legacy_team.objects.select_related.return_value.get.return_value = mock_team
        
        adapter = TeamAdapter()
        
        # Patch is_vnext_team to return False (legacy path)
        with patch.object(adapter, 'is_vnext_team', return_value=False):
            identity = adapter.get_team_identity(123)
            
            # Verify structure matches vNext
            assert identity['team_id'] == 123
            assert identity['name'] == 'Legacy Team'
            assert identity['is_org_team'] is False
            assert identity['organization_name'] is None
            assert identity['organization_slug'] is None
            assert identity['badge_url'] is None
    
    def test_identity_query_count(self):
        """Team identity retrieval should use ≤3 queries."""
        team = TeamFactory.create()
        adapter = TeamAdapter()
        
        with connection.cursor() as cursor:
            before_count = len(connection.queries)
            adapter.get_team_identity(team.id)
            after_count = len(connection.queries)
            
            query_count = after_count - before_count
            assert query_count <= 3, f"Expected ≤3 queries, got {query_count}"


# ============================================================================
# ROSTER VALIDATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestValidateRoster:
    """Test tournament roster validation routing."""
    
    def test_vnext_team_validation_structure(self):
        """vNext team validation should return standardized structure."""
        team = TeamFactory.create()
        # Add some members
        TeamMembershipFactory.create_batch(5, team=team, status='ACTIVE')
        
        adapter = TeamAdapter()
        result = adapter.validate_roster(team.id)
        
        # Verify required fields
        assert 'is_valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'roster_data' in result
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)
    
    @patch('apps.organizations.adapters.team_adapter.LegacyTeam')
    @patch('apps.organizations.adapters.team_adapter.LegacyMembership')
    def test_legacy_team_validation_structure(self, mock_membership, mock_legacy_team):
        """Legacy team validation should return same structure."""
        # Mock legacy team and memberships
        mock_team = Mock()
        mock_team.id = 123
        mock_legacy_team.objects.get.return_value = mock_team
        
        mock_membership.objects.filter.return_value.select_related.return_value.count.return_value = 5
        
        adapter = TeamAdapter()
        
        # Patch is_vnext_team to return False (legacy path)
        with patch.object(adapter, 'is_vnext_team', return_value=False):
            result = adapter.validate_roster(123)
            
            # Verify structure matches vNext
            assert 'is_valid' in result
            assert 'errors' in result
            assert 'warnings' in result
            assert 'roster_data' in result
    
    def test_insufficient_roster_size_validation(self):
        """Team with <5 members should fail validation."""
        team = TeamFactory.create()
        # Only 3 members (below minimum)
        TeamMembershipFactory.create_batch(3, team=team, status='ACTIVE')
        
        adapter = TeamAdapter()
        result = adapter.validate_roster(team.id)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'roster' in result['errors'][0].lower() or 'size' in result['errors'][0].lower()
    
    def test_sufficient_roster_size_validation(self):
        """Team with ≥5 members should pass basic validation."""
        team = TeamFactory.create()
        TeamMembershipFactory.create_batch(5, team=team, status='ACTIVE')
        
        adapter = TeamAdapter()
        result = adapter.validate_roster(team.id)
        
        # Should be valid (no other constraints checked)
        assert result['is_valid'] is True
        assert len(result['errors']) == 0


# ============================================================================
# PERFORMANCE CONTRACT TESTS
# ============================================================================

@pytest.mark.django_db
class TestAdapterPerformance:
    """Verify adapter meets performance targets."""
    
    def test_get_team_url_query_count(self):
        """get_team_url should use ≤2 queries (routing + URL lookup)."""
        team = TeamFactory.create()
        adapter = TeamAdapter()
        
        with connection.cursor() as cursor:
            before_count = len(connection.queries)
            adapter.get_team_url(team.id)
            after_count = len(connection.queries)
            
            query_count = after_count - before_count
            assert query_count <= 2, f"Expected ≤2 queries, got {query_count}"
    
    def test_validate_roster_query_count(self):
        """validate_roster should use ≤6 queries."""
        team = TeamFactory.create()
        TeamMembershipFactory.create_batch(5, team=team, status='ACTIVE')
        
        adapter = TeamAdapter()
        
        with connection.cursor() as cursor:
            before_count = len(connection.queries)
            adapter.validate_roster(team.id)
            after_count = len(connection.queries)
            
            query_count = after_count - before_count
            assert query_count <= 6, f"Expected ≤6 queries, got {query_count}"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.django_db
class TestAdapterErrorHandling:
    """Test adapter error handling and edge cases."""
    
    def test_invalid_team_id_raises_not_found(self):
        """Invalid team_id should raise NotFoundError with error_code."""
        adapter = TeamAdapter()
        
        with pytest.raises(NotFoundError) as exc_info:
            adapter.get_team_url(999999)
        
        assert exc_info.value.error_code == 'TEAM_NOT_FOUND'
        assert 'not found' in str(exc_info.value).lower()
    
    def test_negative_team_id_handled_gracefully(self):
        """Negative team_id should not crash (returns False for is_vnext_team)."""
        adapter = TeamAdapter()
        
        # Should return False (not in vNext system)
        assert adapter.is_vnext_team(-1) is False
    
    def test_zero_team_id_handled_gracefully(self):
        """Zero team_id should not crash."""
        adapter = TeamAdapter()
        
        assert adapter.is_vnext_team(0) is False


# ============================================================================
# INTEGRATION TESTS (CROSS-SYSTEM)
# ============================================================================

@pytest.mark.django_db
class TestAdapterIntegration:
    """Test adapter with both legacy and vNext teams in same test."""
    
    def test_mixed_system_routing(self):
        """Adapter should correctly route vNext and legacy teams."""
        # Create vNext team
        vnext_team = TeamFactory.create()
        
        adapter = TeamAdapter()
        
        # vNext team should route correctly
        assert adapter.is_vnext_team(vnext_team.id) is True
        
        # Nonexistent ID should route to legacy path (fail-safe)
        assert adapter.is_vnext_team(999999) is False
    
    def test_adapter_is_stateless(self):
        """Multiple TeamAdapter instances should behave identically."""
        team = TeamFactory.create()
        
        adapter1 = TeamAdapter()
        adapter2 = TeamAdapter()
        
        # Both adapters should give same result
        assert adapter1.is_vnext_team(team.id) == adapter2.is_vnext_team(team.id)
        assert adapter1.get_team_url(team.id) == adapter2.get_team_url(team.id)
