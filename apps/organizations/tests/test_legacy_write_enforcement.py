"""
Tests for Phase 5 Legacy Write Enforcement (P5-T2).

Verifies that writes to legacy teams models are blocked during migration
while reads remain fully functional.
"""

import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.teams.models import Team, TeamMembership, TeamRankingBreakdown
from apps.user_profile.models import UserProfile
from apps.organizations.services.exceptions import LegacyWriteBlockedException

User = get_user_model()


@pytest.mark.django_db
class TestLegacyWriteBlocking:
    """Test that legacy writes are blocked by default."""
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_team_save_blocked(self):
        """Team.save() should raise LegacyWriteBlockedException when blocked."""
        team = Team(
            name="Test Team",
            tag="TT",
            game="valorant",
            region="Bangladesh"
        )
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            team.save()
        
        assert exc_info.value.error_code == "LEGACY_WRITE_BLOCKED"
        assert "save" in exc_info.value.details['operation']
        assert exc_info.value.details['model'] == "Team"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_team_delete_blocked(self, db):
        """Team.delete() should be blocked."""
        # Create team with bypass enabled
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team = Team.objects.create(
                name="Test Team",
                tag="TT",
                game="valorant"
            )
        
        # Now try to delete with blocking enabled
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            team.delete()
        
        assert exc_info.value.error_code == "LEGACY_WRITE_BLOCKED"
        assert "delete" in exc_info.value.details['operation']
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_team_update_blocked(self, db):
        """Team update (save existing) should be blocked."""
        # Create team with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team = Team.objects.create(
                name="Test Team",
                tag="TT",
                game="valorant"
            )
        
        # Try to update
        team.name = "Updated Team"
        
        with pytest.raises(LegacyWriteBlockedException):
            team.save()
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_membership_save_blocked(self, db):
        """TeamMembership.save() should be blocked."""
        # Create dependencies with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            user = User.objects.create_user(username="testuser", email="test@test.com")
            profile = UserProfile.objects.create(user=user)
            team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
        
        # Try to create membership
        membership = TeamMembership(
            team=team,
            profile=profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            membership.save()
        
        assert exc_info.value.details['model'] == "TeamMembership"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_ranking_breakdown_save_blocked(self, db):
        """TeamRankingBreakdown.save() should be blocked."""
        # Create team with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
        
        # Try to create ranking breakdown
        ranking = TeamRankingBreakdown(
            team=team,
            tournament_participation_points=100,
            final_total=100
        )
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            ranking.save()
        
        assert exc_info.value.details['model'] == "TeamRankingBreakdown"


@pytest.mark.django_db
class TestLegacyBulkOperationsBlocked:
    """Test that bulk operations are also blocked."""
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_bulk_create_blocked(self):
        """Team.objects.bulk_create() should be blocked."""
        teams = [
            Team(name=f"Team {i}", tag=f"T{i}", game="valorant")
            for i in range(3)
        ]
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            Team.objects.bulk_create(teams)
        
        assert exc_info.value.details['operation'] == "bulk_create"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_queryset_update_blocked(self, db):
        """Team.objects.filter().update() should be blocked."""
        # Create teams with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            Team.objects.create(name="Team 1", tag="T1", game="valorant")
            Team.objects.create(name="Team 2", tag="T2", game="valorant")
        
        # Try to bulk update
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            Team.objects.filter(game="valorant").update(region="India")
        
        assert exc_info.value.details['operation'] == "queryset_update"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_queryset_delete_blocked(self, db):
        """Team.objects.filter().delete() should be blocked."""
        # Create teams with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            Team.objects.create(name="Team 1", tag="T1", game="valorant")
            Team.objects.create(name="Team 2", tag="T2", game="valorant")
        
        # Try to bulk delete
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            Team.objects.filter(game="valorant").delete()
        
        assert exc_info.value.details['operation'] == "queryset_delete"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_bulk_update_blocked(self, db):
        """Team.objects.bulk_update() should be blocked."""
        # Create teams with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team1 = Team.objects.create(name="Team 1", tag="T1", game="valorant")
            team2 = Team.objects.create(name="Team 2", tag="T2", game="valorant")
        
        # Modify teams
        team1.region = "India"
        team2.region = "Bangladesh"
        
        # Try to bulk update
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            Team.objects.bulk_update([team1, team2], ['region'])
        
        assert exc_info.value.details['operation'] == "bulk_update"


@pytest.mark.django_db
class TestLegacyReadsStillWork:
    """Test that read operations are unaffected by write blocking."""
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_team_read_works(self, db):
        """Reading teams should work normally."""
        # Create team with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
        
        # Read operations should work
        fetched_team = Team.objects.get(id=team.id)
        assert fetched_team.name == "Test Team"
        
        # QuerySet operations should work
        teams = Team.objects.filter(game="valorant")
        assert teams.count() == 1
        assert teams[0].name == "Test Team"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_membership_read_works(self, db):
        """Reading memberships should work normally."""
        # Create data with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            user = User.objects.create_user(username="testuser", email="test@test.com")
            profile = UserProfile.objects.create(user=user)
            team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
            membership = TeamMembership.objects.create(
                team=team,
                profile=profile,
                role=TeamMembership.Role.PLAYER,
                status=TeamMembership.Status.ACTIVE
            )
        
        # Read operations should work
        fetched = TeamMembership.objects.get(id=membership.id)
        assert fetched.role == TeamMembership.Role.PLAYER
        
        # Related queries should work
        team_members = team.memberships.all()
        assert team_members.count() == 1
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_ranking_read_works(self, db):
        """Reading ranking data should work normally."""
        # Create data with bypass
        with override_settings(TEAM_LEGACY_WRITE_BYPASS_ENABLED=True):
            team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
            ranking = TeamRankingBreakdown.objects.create(
                team=team,
                tournament_participation_points=100,
                final_total=100
            )
        
        # Read operations should work
        fetched = TeamRankingBreakdown.objects.get(team=team)
        assert fetched.tournament_participation_points == 100


@pytest.mark.django_db
class TestLegacyBypassWorks:
    """Test that bypass killswitch allows writes when enabled."""
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=True
    )
    def test_bypass_allows_save(self):
        """When bypass is enabled, save should work."""
        team = Team(name="Test Team", tag="TT", game="valorant")
        
        # Should not raise exception
        team.save()
        
        assert team.id is not None
        assert Team.objects.count() == 1
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=True
    )
    def test_bypass_allows_delete(self, db):
        """When bypass is enabled, delete should work."""
        team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
        
        # Should not raise exception
        team.delete()
        
        assert Team.objects.count() == 0
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=True
    )
    def test_bypass_allows_bulk_create(self):
        """When bypass is enabled, bulk_create should work."""
        teams = [
            Team(name=f"Team {i}", tag=f"T{i}", game="valorant")
            for i in range(3)
        ]
        
        # Should not raise exception
        Team.objects.bulk_create(teams)
        
        assert Team.objects.count() == 3
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=True
    )
    def test_bypass_allows_queryset_update(self, db):
        """When bypass is enabled, QuerySet.update() should work."""
        Team.objects.create(name="Team 1", tag="T1", game="valorant")
        Team.objects.create(name="Team 2", tag="T2", game="valorant")
        
        # Should not raise exception
        Team.objects.filter(game="valorant").update(region="India")
        
        assert Team.objects.filter(region="India").count() == 2


@pytest.mark.django_db
class TestLegacyWriteNotBlocked:
    """Test that writes work normally when blocking is disabled."""
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=False)
    def test_save_works_when_not_blocked(self):
        """When blocking is disabled, save should work normally."""
        team = Team(name="Test Team", tag="TT", game="valorant")
        
        # Should not raise exception
        team.save()
        
        assert team.id is not None
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=False)
    def test_delete_works_when_not_blocked(self, db):
        """When blocking is disabled, delete should work normally."""
        team = Team.objects.create(name="Test Team", tag="TT", game="valorant")
        
        # Should not raise exception
        team.delete()
        
        assert Team.objects.count() == 0
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=False)
    def test_bulk_operations_work_when_not_blocked(self):
        """When blocking is disabled, bulk operations should work."""
        teams = [
            Team(name=f"Team {i}", tag=f"T{i}", game="valorant")
            for i in range(3)
        ]
        
        # Should not raise exception
        Team.objects.bulk_create(teams)
        
        assert Team.objects.count() == 3
        
        # Update should work
        Team.objects.filter(game="valorant").update(region="India")
        assert Team.objects.filter(region="India").count() == 3


@pytest.mark.django_db
class TestExceptionDetails:
    """Test that LegacyWriteBlockedException provides correct details."""
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_exception_has_error_code(self):
        """Exception should have stable error_code."""
        team = Team(name="Test Team", tag="TT")
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            team.save()
        
        assert exc_info.value.error_code == "LEGACY_WRITE_BLOCKED"
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_exception_has_safe_message(self):
        """Exception should have user-friendly safe_message."""
        team = Team(name="Test Team", tag="TT")
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            team.save()
        
        assert "migration" in exc_info.value.safe_message.lower()
        assert "not available" in exc_info.value.safe_message.lower()
    
    @override_settings(
        TEAM_LEGACY_WRITE_BLOCKED=True,
        TEAM_LEGACY_WRITE_BYPASS_ENABLED=False
    )
    def test_exception_has_details(self):
        """Exception should include structured details."""
        team = Team(name="Test Team", tag="TT")
        
        with pytest.raises(LegacyWriteBlockedException) as exc_info:
            team.save()
        
        details = exc_info.value.details
        assert 'model' in details
        assert 'operation' in details
        assert 'table' in details
        assert 'phase' in details
        assert 'bypass_setting' in details
        
        assert details['model'] == 'Team'
        assert details['operation'] == 'save'
        assert details['table'] == 'teams_team'
        assert 'Phase 5' in details['phase']
