"""
GP-1 Dynamic Admin Form Tests

Tests for schema-driven Game Passport admin with:
- Game dropdown limited to games.Game
- Dynamic identity field validation per game
- Region/rank/role choice enforcement
- Case-insensitive uniqueness
- Server-side normalization
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.core.management import call_command

from apps.games.models import Game
from apps.user_profile.models import GameProfile, GamePassportSchema
from apps.user_profile.admin.game_passports import GameProfileAdmin
from apps.user_profile.admin.forms import GameProfileAdminForm

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Seed games and schemas for testing"""
    with django_db_blocker.unblock():
        # Check if games already exist (prevent duplicate seeding)
        if not Game.objects.exists():
            # Seed games (we need to call the games seeding command)
            # For now, manually create the games needed for tests
            pass
        
        # Seed game passport schemas
        call_command('seed_game_passport_schemas')


@pytest.mark.django_db
class TestAdminGameChoicesLimitedToGameModel:
    """Test that game dropdown only shows games from games.Game"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure games are seeded"""
        if not Game.objects.exists():
            self._create_test_games()
        # Ensure schemas exist
        if not GamePassportSchema.objects.exists():
            call_command('seed_game_passport_schemas')
    
    def _create_test_games(self):
        """Create minimal test games"""
        games_data = [
            ('valorant', 'VALORANT', 'VAL'),
            ('cs2', 'Counter-Strike 2', 'CS2'),
            ('mlbb', 'Mobile Legends: Bang Bang', 'MLBB'),
        ]
        for slug, display_name, short_code in games_data:
            Game.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': display_name,
                    'display_name': display_name,
                    'short_code': short_code,
                }
            )
    
    def test_admin_form_game_queryset_uses_game_model(self):
        """Game field queryset should be limited to Game.objects.all()"""
        form = GameProfileAdminForm()
        
        # Should query from games.Game, not hardcoded GAME_CHOICES
        game_field = form.fields['game']
        assert game_field.queryset.model == Game
        
        # Count should match number of games in Game table
        game_count = Game.objects.count()
        assert game_field.queryset.count() == game_count
    
    def test_admin_form_shows_only_active_games(self):
        """Admin should show games from Game model"""
        form = GameProfileAdminForm()
        
        # Verify games exist
        assert form.fields['game'].queryset.count() >= 3
        
        # Verify some expected games exist
        game_slugs = list(form.fields['game'].queryset.values_list('slug', flat=True))
        assert 'valorant' in game_slugs or 'cs2' in game_slugs or 'mlbb' in game_slugs


@pytest.mark.django_db
class TestDynamicRequiredFieldsValorant:
    """Test Valorant identity validation (riot_name + tagline required)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        # Ensure Valorant game exists
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={
                'name': 'VALORANT',
                'display_name': 'VALORANT',
                'short_code': 'VAL',
            }
        )
        # Ensure schema exists
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        self.schema = GamePassportSchema.objects.get(game=self.valorant)
    
    def test_valorant_requires_riot_name_and_tagline(self):
        """Valorant schema requires riot_name and tagline"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {},  # Missing required fields
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'identity_data' in form.errors
    
    def test_valorant_accepts_valid_riot_id(self):
        """Valid Riot ID should pass validation"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'TestPlayer',
                'tagline': 'NA1'
            },
            'visibility': 'PUBLIC',
            'region': 'NA',  # Required for Valorant
            'status': 'ACTIVE',  # Required field
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid(), form.errors
        
        # Check computed values
        assert form.cleaned_data['in_game_name'] == 'TestPlayer#NA1'
        assert form.cleaned_data['identity_key'] == 'testplayer#na1'  # Normalized lowercase
    
    def test_valorant_normalizes_case(self):
        """Riot IDs should be normalized to lowercase in identity_key"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'MyPlayer',
                'tagline': 'EUW'
            },
            'visibility': 'PUBLIC',
            'region': 'EU',
            'status': 'ACTIVE',  # Required field
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid()
        
        # Identity key should be lowercase
        assert form.cleaned_data['identity_key'] == 'myplayer#euw'
        
        # Display name preserves original case
        assert form.cleaned_data['in_game_name'] == 'MyPlayer#EUW'


@pytest.mark.django_db
class TestDynamicRequiredFieldsMLBB:
    """Test MLBB identity validation (numeric_id + zone_id required)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='mlbbplayer',
            email='mlbb@example.com',
            password='testpass123'
        )
        self.mlbb, _ = Game.objects.get_or_create(
            slug='mlbb',
            defaults={
                'name': 'Mobile Legends: Bang Bang',
                'display_name': 'Mobile Legends: Bang Bang',
                'short_code': 'MLBB',
            }
        )
        if not hasattr(self.mlbb, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        self.schema = GamePassportSchema.objects.get(game=self.mlbb)
    
    def test_mlbb_requires_numeric_id_and_zone_id(self):
        """MLBB schema requires numeric_id and zone_id"""
        form_data = {
            'user': self.user.id,
            'game': self.mlbb.id,
            'identity_data': {
                'numeric_id': '123456789'
                # Missing zone_id
            },
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'identity_data' in form.errors
    
    def test_mlbb_accepts_valid_identity(self):
        """Valid MLBB identity should pass validation"""
        form_data = {
            'user': self.user.id,
            'game': self.mlbb.id,
            'identity_data': {
                'numeric_id': '123456789',
                'zone_id': '1234'
            },
            'visibility': 'PUBLIC',
            'region': 'SEA',  # Required for MLBB
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid(), form.errors
        
        # Check computed values
        assert form.cleaned_data['in_game_name'] == '123456789 (1234)'
        assert form.cleaned_data['identity_key'] == '123456789_1234'


@pytest.mark.django_db
class TestRegionChoicesEnforced:
    """Test that region choices are validated against schema"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='regiontest',
            email='region@example.com',
            password='testpass123'
        )
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL'}
        )
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_invalid_region_rejected(self):
        """Invalid region values should be rejected"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'Player',
                'tagline': 'TEST'
            },
            'visibility': 'PUBLIC',
            'region': 'INVALID',  # Not in Valorant schema
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'region' in form.errors
        assert 'Invalid region' in str(form.errors['region'])
    
    def test_valid_region_accepted(self):
        """Valid region from schema should be accepted"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'Player',
                'tagline': 'TEST'
            },
            'visibility': 'PUBLIC',
            'region': 'NA',  # Valid for Valorant
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid(), form.errors
    
    def test_region_required_when_schema_requires(self):
        """Region must be provided if schema.region_required=True"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'Player',
                'tagline': 'TEST'
            },
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
            # Missing region (required for Valorant)
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'region' in form.errors


@pytest.mark.django_db
class TestUniquenessCaseInsensitiveForRiotIDs:
    """Test case-insensitive uniqueness for Riot games"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL'}
        )
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_duplicate_identity_case_insensitive_rejected(self):
        """Duplicate identity (different case) should be rejected"""
        # Create first passport
        passport1 = GameProfile.objects.create(
            user=self.user1,
            game=self.valorant,
            in_game_name='Player#NA1',
            identity_key='player#na1',  # Lowercase
            visibility='PUBLIC',
            region='NA',
            metadata={
                'riot_name': 'Player',
                'tagline': 'NA1'
            }
        )
        
        # Try to create second passport with same identity (different case)
        form_data = {
            'user': self.user2.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'PLAYER',  # Different case
                'tagline': 'na1'        # Different case
            },
            'visibility': 'PUBLIC',
            'region': 'NA',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'identity_data' in form.errors
        assert 'already registered' in str(form.errors['identity_data'])
    
    def test_same_user_can_edit_their_passport(self):
        """User should be able to edit their own passport (not trigger uniqueness)"""
        # Create passport
        passport = GameProfile.objects.create(
            user=self.user1,
            game=self.valorant,
            in_game_name='Player#NA1',
            identity_key='player#na1',
            visibility='PUBLIC',
            region='NA',
            metadata={
                'riot_name': 'Player',
                'tagline': 'NA1'
            }
        )
        
        # Edit same passport (case change)
        form_data = {
            'user': self.user1.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'PLAYER',  # Change case
                'tagline': 'NA1'
            },
            'visibility': 'PRIVATE',  # Change visibility
            'region': 'NA',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data, instance=passport)
        assert form.is_valid(), form.errors


@pytest.mark.django_db
class TestSteamGameIdentityValidation:
    """Test Steam games (CS2, Dota 2) identity validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='steamuser',
            email='steam@example.com',
            password='testpass123'
        )
        self.cs2, _ = Game.objects.get_or_create(
            slug='cs2',
            defaults={'name': 'Counter-Strike 2', 'display_name': 'Counter-Strike 2', 'short_code': 'CS2'}
        )
        if not hasattr(self.cs2, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_cs2_requires_steam_id64(self):
        """CS2 requires steam_id64 field"""
        form_data = {
            'user': self.user.id,
            'game': self.cs2.id,
            'identity_data': {},  # Missing steam_id64
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'identity_data' in form.errors
    
    def test_cs2_accepts_valid_steam_id64(self):
        """Valid Steam ID64 should pass"""
        form_data = {
            'user': self.user.id,
            'game': self.cs2.id,
            'identity_data': {
                'steam_id64': '76561198012345678'
            },
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid(), form.errors
        
        # Check computed values
        assert form.cleaned_data['in_game_name'] == '76561198012345678'
        assert form.cleaned_data['identity_key'] == '76561198012345678'


@pytest.mark.django_db
class TestRoleChoicesEnforced:
    """Test that role choices are validated against schema"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='roletest',
            email='role@example.com',
            password='testpass123'
        )
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL'}
        )
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_invalid_role_rejected(self):
        """Invalid role values should be rejected"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'Player',
                'tagline': 'TEST'
            },
            'visibility': 'PUBLIC',
            'region': 'NA',
            'main_role': 'INVALID_ROLE',  # Not in Valorant schema
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'main_role' in form.errors
    
    def test_valid_role_accepted(self):
        """Valid role from schema should be accepted"""
        form_data = {
            'user': self.user.id,
            'game': self.valorant.id,
            'identity_data': {
                'riot_name': 'Player',
                'tagline': 'TEST'
            },
            'visibility': 'PUBLIC',
            'region': 'NA',
            'main_role': 'duelist',  # Valid for Valorant
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert form.is_valid(), form.errors


@pytest.mark.django_db
class TestSchemaNotConfiguredError:
    """Test error handling when schema doesn't exist"""
    
    def test_form_rejects_game_without_schema(self):
        """Form should reject games that don't have a schema configured"""
        # This test assumes a game might exist without schema
        # In production, all games should have schemas
        
        user = User.objects.create_user(
            username='noschemauser',
            email='noschema@example.com',
            password='testpass123'
        )
        
        # Create a game without schema (for testing)
        test_game = Game.objects.create(
            name='Test Game Without Schema',
            display_name='Test Game',
            slug='test-no-schema',
            short_code='TEST'
        )
        
        form_data = {
            'user': user.id,
            'game': test_game.id,
            'identity_data': {'test': 'data'},
            'visibility': 'PUBLIC',
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'game' in form.errors
        assert 'No passport schema configured' in str(form.errors['game'])
