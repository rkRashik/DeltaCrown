"""
Tests for P0 Loadout Models - HardwareGear, GameConfig

Tests:
- HardwareGear model validation and constraints
- GameConfig model validation and constraints
- Uniqueness constraints (one hardware per category per user, one config per game per user)
- Privacy controls (is_public field)
- Service helper functions
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.user_profile.models import HardwareGear, GameConfig
from apps.games.models import Game
from apps.user_profile.services.loadout_service import (
    get_user_hardware,
    get_user_game_configs,
    get_user_game_config,
    get_complete_loadout,
    has_loadout,
)

User = get_user_model()


# ===========================
# FIXTURES
# ===========================

@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def user2(db):
    """Create a second test user."""
    return User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123'
    )


@pytest.fixture
def game_valorant(db):
    """Create Valorant game."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        description='Tactical FPS'
    )


@pytest.fixture
def game_cs2(db):
    """Create CS2 game."""
    return Game.objects.create(
        name='Counter-Strike 2',
        slug='cs2',
        description='Competitive FPS'
    )


# ===========================
# HARDWAREGEAR TESTS
# ===========================

@pytest.mark.django_db
class TestHardwareGear:
    """Test HardwareGear model validation and behavior."""
    
    def test_create_mouse_hardware(self, user):
        """Test creating mouse hardware."""
        mouse = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro X Superlight',
            specs={
                'dpi': 800,
                'polling_rate': 1000,
                'weight_grams': 63
            },
            is_public=True
        )
        
        assert mouse.category == 'MOUSE'
        assert mouse.brand == 'Logitech'
        assert mouse.model == 'G Pro X Superlight'
        assert mouse.specs['dpi'] == 800
        assert mouse.is_public is True
    
    def test_create_keyboard_hardware(self, user):
        """Test creating keyboard hardware."""
        keyboard = HardwareGear.objects.create(
            user=user,
            category='KEYBOARD',
            brand='Razer',
            model='Huntsman Mini',
            specs={
                'switch_type': 'Linear Optical',
                'layout': '60%',
                'wireless': False
            },
            is_public=True
        )
        
        assert keyboard.category == 'KEYBOARD'
        assert keyboard.brand == 'Razer'
        assert keyboard.specs['switch_type'] == 'Linear Optical'
    
    def test_unique_hardware_per_category_per_user(self, user):
        """Test uniqueness constraint: one hardware per category per user."""
        # Create first mouse
        HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro X Superlight'
        )
        
        # Try to create second mouse for same user (should fail)
        with pytest.raises(IntegrityError):
            HardwareGear.objects.create(
                user=user,
                category='MOUSE',
                brand='Razer',
                model='DeathAdder V3 Pro'
            )
    
    def test_multiple_hardware_categories_allowed(self, user):
        """Test user can have hardware in multiple categories."""
        mouse = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        keyboard = HardwareGear.objects.create(
            user=user,
            category='KEYBOARD',
            brand='Razer',
            model='Huntsman'
        )
        
        headset = HardwareGear.objects.create(
            user=user,
            category='HEADSET',
            brand='HyperX',
            model='Cloud II'
        )
        
        assert user.hardware_gear.count() == 3
        assert mouse.category == 'MOUSE'
        assert keyboard.category == 'KEYBOARD'
        assert headset.category == 'HEADSET'
    
    def test_different_users_same_hardware(self, user, user2):
        """Test different users can have same hardware model."""
        mouse1 = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro X Superlight'
        )
        
        mouse2 = HardwareGear.objects.create(
            user=user2,
            category='MOUSE',
            brand='Logitech',
            model='G Pro X Superlight'
        )
        
        assert mouse1.brand == mouse2.brand
        assert mouse1.model == mouse2.model
        assert mouse1.user != mouse2.user
    
    def test_empty_brand_rejected(self, user):
        """Test empty brand is rejected."""
        hardware = HardwareGear(
            user=user,
            category='MOUSE',
            brand='',  # Empty
            model='Test Model'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            hardware.save()
        
        assert 'brand' in str(exc_info.value).lower()
    
    def test_empty_model_rejected(self, user):
        """Test empty model is rejected."""
        hardware = HardwareGear(
            user=user,
            category='MOUSE',
            brand='Test Brand',
            model=''  # Empty
        )
        
        with pytest.raises(ValidationError) as exc_info:
            hardware.save()
        
        assert 'model' in str(exc_info.value).lower()
    
    def test_purchase_url_validation(self, user):
        """Test purchase URL validation (uses affiliate URL validator)."""
        hardware = HardwareGear(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro',
            purchase_url='https://amazon.com/product/123'
        )
        
        # Should pass (Amazon whitelisted)
        hardware.save()
        assert hardware.purchase_url == 'https://amazon.com/product/123'
    
    def test_purchase_url_invalid_domain_rejected(self, user):
        """Test non-whitelisted purchase URL is rejected."""
        hardware = HardwareGear(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro',
            purchase_url='https://malicious-site.com/product'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            hardware.save()
        
        assert 'purchase_url' in str(exc_info.value)
    
    def test_privacy_default_public(self, user):
        """Test is_public defaults to True."""
        hardware = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        assert hardware.is_public is True
    
    def test_privacy_can_be_private(self, user):
        """Test hardware can be set to private."""
        hardware = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro',
            is_public=False
        )
        
        assert hardware.is_public is False


# ===========================
# GAMECONFIG TESTS
# ===========================

@pytest.mark.django_db
class TestGameConfig:
    """Test GameConfig model validation and behavior."""
    
    def test_create_valorant_config(self, user, game_valorant):
        """Test creating Valorant game config."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={
                'sensitivity': 0.45,
                'dpi': 800,
                'crosshair_style': 'small_dot',
                'resolution': '1920x1080'
            },
            notes='Tournament setup',
            is_public=True
        )
        
        assert config.game == game_valorant
        assert config.settings['sensitivity'] == 0.45
        assert config.settings['dpi'] == 800
        assert config.notes == 'Tournament setup'
        assert config.is_public is True
    
    def test_create_cs2_config(self, user, game_cs2):
        """Test creating CS2 game config."""
        config = GameConfig.objects.create(
            user=user,
            game=game_cs2,
            settings={
                'sensitivity': 1.2,
                'dpi': 800,
                'viewmodel_fov': 68,
                'resolution': '1280x960'
            },
            is_public=True
        )
        
        assert config.game == game_cs2
        assert config.settings['sensitivity'] == 1.2
        assert config.settings['viewmodel_fov'] == 68
    
    def test_unique_config_per_user_per_game(self, user, game_valorant):
        """Test uniqueness constraint: one config per user per game."""
        # Create first config
        GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        # Try to create second config for same user + game (should fail)
        with pytest.raises(IntegrityError):
            GameConfig.objects.create(
                user=user,
                game=game_valorant,
                settings={'sensitivity': 0.50}
            )
    
    def test_multiple_game_configs_allowed(self, user, game_valorant, game_cs2):
        """Test user can have configs for multiple games."""
        valorant_config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45, 'dpi': 800}
        )
        
        cs2_config = GameConfig.objects.create(
            user=user,
            game=game_cs2,
            settings={'sensitivity': 1.2, 'dpi': 800}
        )
        
        assert user.game_configs.count() == 2
        assert valorant_config.game == game_valorant
        assert cs2_config.game == game_cs2
    
    def test_different_users_same_game(self, user, user2, game_valorant):
        """Test different users can have configs for same game."""
        config1 = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        config2 = GameConfig.objects.create(
            user=user2,
            game=game_valorant,
            settings={'sensitivity': 0.50}
        )
        
        assert config1.game == config2.game
        assert config1.user != config2.user
        assert config1.settings != config2.settings
    
    def test_settings_must_be_dict(self, user, game_valorant):
        """Test settings must be a dictionary."""
        config = GameConfig(
            user=user,
            game=game_valorant,
            settings='not a dict'  # Invalid
        )
        
        with pytest.raises(ValidationError) as exc_info:
            config.save()
        
        assert 'settings' in str(exc_info.value).lower()
    
    def test_notes_max_length(self, user, game_valorant):
        """Test notes cannot exceed 500 characters."""
        config = GameConfig(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45},
            notes='x' * 501  # Too long
        )
        
        with pytest.raises(ValidationError) as exc_info:
            config.save()
        
        assert 'notes' in str(exc_info.value).lower()
    
    def test_get_effective_dpi(self, user, game_valorant):
        """Test eDPI calculation (sensitivity * DPI)."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={
                'sensitivity': 0.45,
                'dpi': 800
            }
        )
        
        edpi = config.get_effective_dpi()
        assert edpi == 360.0  # 0.45 * 800
    
    def test_get_effective_dpi_missing_values(self, user, game_valorant):
        """Test eDPI returns None if sensitivity or dpi missing."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={
                'crosshair_style': 'small_dot'
                # No sensitivity or dpi
            }
        )
        
        edpi = config.get_effective_dpi()
        assert edpi is None
    
    def test_privacy_default_public(self, user, game_valorant):
        """Test is_public defaults to True."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        assert config.is_public is True
    
    def test_privacy_can_be_private(self, user, game_valorant):
        """Test config can be set to private."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45},
            is_public=False
        )
        
        assert config.is_public is False


# ===========================
# SERVICE HELPER TESTS
# ===========================

@pytest.mark.django_db
class TestLoadoutService:
    """Test loadout service helper functions."""
    
    def test_get_user_hardware(self, user):
        """Test get_user_hardware returns user's hardware."""
        mouse = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        keyboard = HardwareGear.objects.create(
            user=user,
            category='KEYBOARD',
            brand='Razer',
            model='Huntsman'
        )
        
        hardware = get_user_hardware(user)
        assert hardware.count() == 2
        assert mouse in hardware
        assert keyboard in hardware
    
    def test_get_user_hardware_by_category(self, user):
        """Test get_user_hardware filters by category."""
        HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        HardwareGear.objects.create(
            user=user,
            category='KEYBOARD',
            brand='Razer',
            model='Huntsman'
        )
        
        mouse_only = get_user_hardware(user, category='MOUSE')
        assert mouse_only.count() == 1
        assert mouse_only.first().category == 'MOUSE'
    
    def test_get_user_hardware_public_only(self, user):
        """Test get_user_hardware filters by is_public."""
        HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro',
            is_public=True
        )
        
        HardwareGear.objects.create(
            user=user,
            category='KEYBOARD',
            brand='Razer',
            model='Huntsman',
            is_public=False
        )
        
        public_only = get_user_hardware(user, public_only=True)
        assert public_only.count() == 1
        assert public_only.first().category == 'MOUSE'
    
    def test_get_user_game_configs(self, user, game_valorant, game_cs2):
        """Test get_user_game_configs returns user's configs."""
        val_config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        cs2_config = GameConfig.objects.create(
            user=user,
            game=game_cs2,
            settings={'sensitivity': 1.2}
        )
        
        configs = get_user_game_configs(user)
        assert configs.count() == 2
        assert val_config in configs
        assert cs2_config in configs
    
    def test_get_user_game_config(self, user, game_valorant):
        """Test get_user_game_config returns specific game config."""
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        result = get_user_game_config(user, 'valorant')
        assert result == config
        assert result.game == game_valorant
    
    def test_get_user_game_config_not_found(self, user):
        """Test get_user_game_config returns None if not found."""
        result = get_user_game_config(user, 'nonexistent-game')
        assert result is None
    
    def test_get_complete_loadout(self, user, game_valorant):
        """Test get_complete_loadout returns hardware + configs."""
        mouse = HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        config = GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        loadout = get_complete_loadout(user)
        assert 'hardware' in loadout
        assert 'game_configs' in loadout
        assert loadout['hardware']['MOUSE'] == mouse
        assert config in loadout['game_configs']
    
    def test_has_loadout_with_hardware(self, user):
        """Test has_loadout returns True if user has hardware."""
        HardwareGear.objects.create(
            user=user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro'
        )
        
        assert has_loadout(user) is True
    
    def test_has_loadout_with_configs(self, user, game_valorant):
        """Test has_loadout returns True if user has configs."""
        GameConfig.objects.create(
            user=user,
            game=game_valorant,
            settings={'sensitivity': 0.45}
        )
        
        assert has_loadout(user) is True
    
    def test_has_loadout_empty(self, user):
        """Test has_loadout returns False if user has no loadout."""
        assert has_loadout(user) is False
