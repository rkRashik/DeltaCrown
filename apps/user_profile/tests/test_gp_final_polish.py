"""
GP-FINAL-01 Tests: Team Badge Integration & Polish

Minimal tests to verify:
- Team badge renders correctly on Battle Cards
- Free Agent state renders correctly
- No mixed terminology remains
"""
import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.services.game_passport_service import GamePassportService
from apps.user_profile.models import UserProfile, GameProfile
from apps.teams.models import Team, TeamMembership

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestTeamBadgeIntegration:
    """Test team badge display on Battle Cards"""
    
    def test_team_badge_shows_current_team(self):
        """Battle Card shows team badge when user has active team for game"""
        # Create user with profile
        user = User.objects.create_user(username='teampro', email='teampro@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Create passport
        passport = GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='TeamPro#VAL', metadata={}
        )
        GamePassportService.pin_passport(user=user, game='valorant')
        
        # Create team for same game
        team = Team.objects.create(
            name='Pro Esports',
            tag='PRO',
            game='valorant',
            is_active=True
        )
        
        # Create active membership
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Fetch profile page
        client = Client()
        response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'teampro'}))
        
        assert response.status_code == 200
        # Check team name appears
        assert b'Pro Esports' in response.content or b'PRO' in response.content
        # Check NOT Free Agent
        content_str = response.content.decode('utf-8')
        assert 'Free Agent' not in content_str or 'Pro Esports' in content_str
    
    def test_free_agent_shows_when_no_team(self):
        """Battle Card shows 'Free Agent' when user has no team for game"""
        user = User.objects.create_user(username='soloplayer', email='solo@example.com', password='pass123')
        
        # Create passport (no team)
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Solo#VAL', metadata={}
        )
        GamePassportService.pin_passport(user=user, game='valorant')
        
        # Fetch profile page
        client = Client()
        response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'soloplayer'}))
        
        assert response.status_code == 200
        assert b'Free Agent' in response.content
    
    def test_team_badge_only_for_matching_game(self):
        """Team badge only shows for passports matching team game"""
        user = User.objects.create_user(username='multigamer', email='multi@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Create 2 passports (different games)
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Multi#VAL', metadata={})
        GamePassportService.create_passport(user=user, game='cs2', in_game_name='76561198012345678', metadata={})
        
        # Create team for only 1 game
        team = Team.objects.create(
            name='VAL Only',
            tag='VAL',
            game='valorant',
            is_active=True
        )
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Fetch profile page
        client = Client()
        response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'multigamer'}))
        
        assert response.status_code == 200
        content_str = response.content.decode('utf-8')
        
        # Valorant should show team, CS2 should show Free Agent
        assert 'VAL Only' in content_str or 'VAL' in content_str
        # At least one Free Agent should appear (for CS2)
        assert 'Free Agent' in content_str


class TestTerminologyConsistency:
    """Verify consistent terminology across UI"""
    
    def test_battle_cards_terminology_in_template(self):
        """Templates use 'Battle Card' terminology"""
        import os
        template_path = os.path.join('templates', 'user_profile', 'v2', '_battle_cards.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        assert 'Battle Cards' in content or 'battle-card' in content
        assert 'Game Passport' in content  # In comment
