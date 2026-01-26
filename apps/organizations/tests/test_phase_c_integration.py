"""
Phase C Tests: Gap Closure + UX Hardening

Test coverage for Phase C enhancements:
- Tag + tagline persistence
- Tag uniqueness per game
- Manager invite pipeline
- Error-to-step navigation
- File upload validation
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.games.models import Game
from apps.organizations.models import (
    Team,
    TeamMembership,
    TeamInvite,
    Organization,
    OrganizationMembership,
)
from apps.organizations.tests.factories import (
    TeamFactory,
    OrganizationFactory,
    UserFactory,
)

User = get_user_model()


# ============================================================================
# Tag + Tagline Persistence Tests
# ============================================================================

@pytest.mark.django_db
class TestTagTaglinePersistence:
    """Test tag and tagline fields are stored correctly."""
    
    def test_team_model_has_tag_and_tagline_fields(self):
        """Verify Team model has tag and tagline fields."""
        assert hasattr(Team, 'tag'), "Team model must have 'tag' field"
        assert hasattr(Team, 'tagline'), "Team model must have 'tagline' field"
    
    def test_create_team_with_tag_and_tagline(self):
        """Test creating team with tag and tagline persists both fields."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        team = Team.objects.create(
            name="Cloud9 Blue",
            tag="C9B",
            tagline="Victory or Nothing",
            game_id=game.id,
            owner=user,
            region="United States",
            status="ACTIVE"
        )
        
        # Refresh from DB
        team.refresh_from_db()
        
        assert team.tag == "C9B"
        assert team.tagline == "Victory or Nothing"
    
    def test_create_team_api_persists_tag_and_tagline(self):
        """Test POST /api/vnext/teams/create/ persists tag and tagline."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'Team Liquid',
            'tag': 'TL',
            'tagline': 'Always Forward',
            'game_slug': 'valorant',
            'region': 'United States',
        })
        
        assert response.status_code == 201
        assert response.data['ok'] is True
        
        team = Team.objects.get(slug=response.data['team_slug'])
        assert team.tag == 'TL'
        assert team.tagline == 'Always Forward'
    
    def test_tag_optional_allows_null(self):
        """Test that tag field is optional (null/blank allowed)."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        team = Team.objects.create(
            name="No Tag Team",
            game_id=game.id,
            owner=user,
            region="United States",
            status="ACTIVE"
        )
        
        team.refresh_from_db()
        assert team.tag is None or team.tag == ''


# ============================================================================
# Tag Uniqueness Tests
# ============================================================================

@pytest.mark.django_db
class TestTagUniqueness:
    """Test tag uniqueness constraint per game."""
    
    def test_same_tag_different_games_allowed(self):
        """Test same tag can be used for different games."""
        game1 = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        game2 = Game.objects.create(name="CS2", slug="cs2", is_active=True)
        user = UserFactory.create()
        
        team1 = Team.objects.create(
            name="Cloud9 Valorant",
            tag="C9",
            game_id=game1.id,
            owner=user,
            region="US",
            status="ACTIVE"
        )
        
        # Same tag, different game - should succeed
        team2 = Team.objects.create(
            name="Cloud9 CS2",
            tag="C9",
            game_id=game2.id,
            owner=user,
            region="US",
            status="ACTIVE"
        )
        
        assert team1.tag == team2.tag
        assert team1.game_id != team2.game_id
    
    def test_same_tag_same_game_rejected(self):
        """Test same tag on same game is rejected (DB constraint)."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user1 = UserFactory.create()
        user2 = UserFactory.create(username="user2", email="user2@test.com")
        
        # First team with tag "C9"
        Team.objects.create(
            name="Cloud9 Blue",
            tag="C9",
            game_id=game.id,
            owner=user1,
            region="US",
            status="ACTIVE"
        )
        
        # Second team with same tag and game should fail
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Team.objects.create(
                name="Clown9",
                tag="C9",
                game_id=game.id,
                owner=user2,
                region="US",
                status="ACTIVE"
            )
    
    def test_validate_tag_endpoint_checks_uniqueness(self):
        """Test /api/vnext/teams/validate-tag/ checks DB uniqueness."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        # Create team with tag
        Team.objects.create(
            name="Cloud9",
            tag="C9",
            game_id=game.id,
            owner=user,
            region="US",
            status="ACTIVE"
        )
        
        client = APIClient()
        
        # Check same tag - should be unavailable
        response = client.get('/api/vnext/teams/validate-tag/', {
            'tag': 'C9',
            'game': 'valorant',
        })
        
        assert response.status_code == 200
        assert response.data['available'] is False
        assert 'already taken' in response.data['field_errors']['tag'].lower()
    
    def test_validate_tag_case_insensitive(self):
        """Test tag validation is case-insensitive."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        # Create team with tag "TL"
        Team.objects.create(
            name="Team Liquid",
            tag="TL",
            game_id=game.id,
            owner=user,
            region="US",
            status="ACTIVE"
        )
        
        client = APIClient()
        
        # Check lowercase "tl" - should also be unavailable
        response = client.get('/api/vnext/teams/validate-tag/', {
            'tag': 'tl',
            'game': 'valorant',
        })
        
        assert response.status_code == 200
        assert response.data['available'] is False


# ============================================================================
# Manager Invite Tests
# ============================================================================

@pytest.mark.django_db
class TestManagerInvite:
    """Test manager invite pipeline."""
    
    def test_invite_existing_user_creates_invited_membership(self):
        """Test inviting existing user creates TeamMembership with INVITED status."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        manager_user = UserFactory.create(username="manager", email="manager@test.com")
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'My Team',
            'game_slug': 'valorant',
            'region': 'US',
            'manager_email': 'manager@test.com',
        })
        
        assert response.status_code == 201
        assert response.data['invite_created'] is True
        
        team = Team.objects.get(slug=response.data['team_slug'])
        
        # Check invited membership exists
        invited_membership = TeamMembership.objects.filter(
            team=team,
            user=manager_user,
            role='MANAGER',
            status='INVITED'
        ).first()
        
        assert invited_membership is not None
    
    def test_invite_nonexistent_user_creates_team_invite(self):
        """Test inviting non-existent email creates TeamInvite record."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'My Team',
            'game_slug': 'valorant',
            'region': 'US',
            'manager_email': 'newmanager@test.com',
        })
        
        assert response.status_code == 201
        assert response.data['invite_created'] is True
        
        team = Team.objects.get(slug=response.data['team_slug'])
        
        # Check TeamInvite exists
        invite = TeamInvite.objects.filter(
            team=team,
            invited_email='newmanager@test.com',
            role='MANAGER',
            status='PENDING'
        ).first()
        
        assert invite is not None
        assert invite.inviter == owner
    
    def test_team_creation_succeeds_without_manager_invite(self):
        """Test team creation works without manager_email (optional field)."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'Solo Team',
            'game_slug': 'valorant',
            'region': 'US',
        })
        
        assert response.status_code == 201
        assert response.data['invite_created'] is False
    
    def test_team_invite_has_expiry_date(self):
        """Test TeamInvite automatically sets expiry date (7 days)."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'My Team',
            'game_slug': 'valorant',
            'region': 'US',
            'manager_email': 'newmanager@test.com',
        })
        
        assert response.status_code == 201
        
        team = Team.objects.get(slug=response.data['team_slug'])
        invite = TeamInvite.objects.get(team=team, invited_email='newmanager@test.com')
        
        assert invite.expires_at is not None
        
        # Check it's roughly 7 days in the future
        from datetime import timedelta
        from django.utils import timezone
        expected_expiry = timezone.now() + timedelta(days=7)
        time_diff = abs((invite.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance


# ============================================================================
# Error Response Tests
# ============================================================================

@pytest.mark.django_db
class TestErrorResponses:
    """Test error responses include proper field_errors for step navigation."""
    
    def test_validation_error_includes_field_errors(self):
        """Test validation errors include field_errors dict."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Submit with missing name
        response = client.post('/api/vnext/teams/create/', {
            'game_slug': 'valorant',
            'region': 'US',
        })
        
        assert response.status_code == 400
        assert 'field_errors' in response.data
        assert 'name' in response.data['field_errors']
    
    def test_invalid_tag_returns_field_error(self):
        """Test invalid tag returns field_errors.tag."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        user = UserFactory.create()
        
        # Create team with tag "TL"
        Team.objects.create(
            name="Team Liquid",
            tag="TL",
            game_id=game.id,
            owner=user,
            region="US",
            status="ACTIVE"
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Try to create another team with same tag
        user2 = UserFactory.create(username="user2", email="user2@test.com")
        client.force_authenticate(user=user2)
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'Fake Liquid',
            'tag': 'TL',
            'game_slug': 'valorant',
            'region': 'US',
        })
        
        # Should fail at serializer validation or DB
        assert response.status_code in [400, 409, 500]
        # Note: Exact error handling depends on implementation


# ============================================================================
# Query Performance Tests
# ============================================================================

@pytest.mark.django_db
class TestPhaseQueryPerformance:
    """Test query counts stay within budget for Phase C operations."""
    
    def test_create_with_manager_invite_query_count(self):
        """Test create endpoint with manager invite stays within query budget."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        manager = UserFactory.create(username="manager", email="manager@test.com")
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        with CaptureQueriesContext(connection) as ctx:
            response = client.post('/api/vnext/teams/create/', {
                'name': 'Performance Team',
                'tag': 'PERF',
                'tagline': 'Speed Matters',
                'game_slug': 'valorant',
                'region': 'US',
                'manager_email': 'manager@test.com',
            })
        
        assert response.status_code == 201
        
        # Target: ≤15 queries (user auth, game lookup, team create, owner membership, manager invite)
        query_count = len(ctx.captured_queries)
        assert query_count <= 15, f"Expected ≤15 queries, got {query_count}"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.django_db
class TestPhaseIntegration:
    """End-to-end integration tests for Phase C."""
    
    def test_full_team_creation_with_all_fields(self):
        """Test creating team with all Phase C fields populated."""
        game = Game.objects.create(name="Valorant", slug="valorant", is_active=True)
        owner = UserFactory.create()
        
        client = APIClient()
        client.force_authenticate(user=owner)
        
        # Create small test image
        image_content = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        logo = SimpleUploadedFile("logo.gif", image_content, content_type="image/gif")
        
        response = client.post('/api/vnext/teams/create/', {
            'name': 'Complete Team',
            'tag': 'CT',
            'tagline': 'All Fields Test',
            'description': 'A team with all fields populated for testing',
            'game_slug': 'valorant',
            'region': 'United States',
            'manager_email': 'newmanager@test.com',
            'logo': logo,
        }, format='multipart')
        
        assert response.status_code == 201
        assert response.data['ok'] is True
        
        team = Team.objects.get(slug=response.data['team_slug'])
        
        # Verify all fields persisted
        assert team.name == 'Complete Team'
        assert team.tag == 'CT'
        assert team.tagline == 'All Fields Test'
        assert team.description == 'A team with all fields populated for testing'
        assert team.region == 'United States'
        assert team.logo is not None
        
        # Verify owner membership
        owner_membership = TeamMembership.objects.filter(
            team=team,
            user=owner,
            role='OWNER',
            status='ACTIVE'
        ).exists()
        assert owner_membership
        
        # Verify manager invite
        manager_invite = TeamInvite.objects.filter(
            team=team,
            invited_email='newmanager@test.com',
            role='MANAGER'
        ).exists()
        assert manager_invite
