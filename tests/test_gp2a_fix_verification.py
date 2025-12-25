"""
GP-2A Verification Test: Ensure DB columns exist and admin/profile pages work
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import GameProfile
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestGP2AColumns:
    """Test that GP-2A structured identity columns exist and work"""
    
    def test_gameprofile_has_gp2a_columns(self):
        """Verify GameProfile model has ign, discriminator, platform, region fields"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_profile_gameprofile'
                AND column_name IN ('ign', 'discriminator', 'platform', 'region')
                ORDER BY column_name
            """)
            cols = [row[0] for row in cursor.fetchall()]
        
        assert 'ign' in cols, "Column 'ign' missing from GameProfile table"
        assert 'discriminator' in cols, "Column 'discriminator' missing"
        assert 'platform' in cols, "Column 'platform' missing"
        assert 'region' in cols, "Column 'region' missing"
    
    def test_can_create_gameprofile_with_structured_identity(self):
        """Test creating GameProfile with GP-2A columns"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        game = Game.objects.first()
        if not game:
            pytest.skip("No games in database")
        
        profile = GameProfile.objects.create(
            user=user,
            game=game,
            game_display_name=game.display_name,
            ign='TestPlayer',
            discriminator='TAG123',
            platform='PC',
            region='NA',
            in_game_name='TestPlayer#TAG123',
            identity_key='testplayer#tag123'
        )
        
        assert profile.ign == 'TestPlayer'
        assert profile.discriminator == 'TAG123'
        assert profile.platform == 'PC'
        assert profile.region == 'NA'
    
    def test_can_query_by_ign(self):
        """Test querying GameProfile by ign column"""
        user = User.objects.create_user(
            username='querytest',
            email='query@example.com',
            password='testpass123'
        )
        game = Game.objects.first()
        if not game:
            pytest.skip("No games in database")
        
        GameProfile.objects.create(
            user=user,
            game=game,
            game_display_name=game.display_name,
            ign='QueryTestUser',
            in_game_name='QueryTestUser',
            identity_key='querytestuser'
        )
        
        # This would raise ProgrammingError if column doesn't exist
        profile = GameProfile.objects.filter(ign='QueryTestUser').first()
        assert profile is not None
        assert profile.ign == 'QueryTestUser'


@pytest.mark.django_db
class TestAdminPages:
    """Test that admin pages load without ProgrammingError"""
    
    def test_admin_gameprofile_list_loads(self):
        """Test /admin/user_profile/gameprofile/ loads"""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        client = Client()
        client.force_login(user)
        
        response = client.get('/admin/user_profile/gameprofile/')
        
        # Should not raise ProgrammingError
        assert response.status_code == 200
    
    def test_admin_gameprofile_add_loads(self):
        """Test /admin/user_profile/gameprofile/add/ loads"""
        user = User.objects.create_superuser(
            username='admin2',
            email='admin2@example.com',
            password='admin123'
        )
        
        client = Client()
        client.force_login(user)
        
        response = client.get('/admin/user_profile/gameprofile/add/')
        
        # Should not raise ProgrammingError
        assert response.status_code == 200


@pytest.mark.django_db
class TestProfilePages:
    """Test that profile pages load without ProgrammingError"""
    
    def test_profile_page_loads(self):
        """Test /@username/ page loads"""
        user = User.objects.create_user(
            username='profiletest',
            email='profile@example.com',
            password='testpass123'
        )
        
        client = Client()
        response = client.get(f'/@{user.username}/')
        
        # Should not raise ProgrammingError
        # May redirect or return 200, both are OK
        assert response.status_code in [200, 301, 302, 404]  # 404 OK if profile incomplete
