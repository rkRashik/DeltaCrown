"""
GP-0 Game Passport Tests

Comprehensive test coverage for:
- CRUD operations
- Global uniqueness
- Identity change cooldown
- Alias history
- Pinning limits
- Privacy levels
- Audit events
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.test import TestCase

from apps.user_profile.models import GameProfile, GameProfileAlias, GameProfileConfig
from apps.user_profile.services.game_passport_service import GamePassportService
from apps.user_profile.models.audit import UserAuditEvent

User = get_user_model()


@pytest.mark.django_db
class TestGamePassportCreation:
    """Test passport creation and validation"""
    
    def test_create_valid_valorant_passport(self):
        """Should create passport with valid Riot ID"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id,
            request_ip='127.0.0.1'
        )
        
        from apps.games.models import Game
        game_obj = Game.objects.get(slug='valorant')
        assert passport.game == game_obj
        assert passport.ign == 'Player'
        assert passport.discriminator == '1234'
        assert passport.in_game_name == 'Player#1234'  # Auto-generated
        assert passport.identity_key == 'player#1234'  # Lowercase normalized
        assert passport.status == GameProfile.STATUS_ACTIVE
        assert passport.visibility == GameProfile.VISIBILITY_PUBLIC
        
        # Check audit event
        audit = UserAuditEvent.objects.filter(
            event_type='game_passport.created',
            object_id=passport.id
        ).first()
        assert audit is not None
    
    def test_create_invalid_valorant_format(self):
        """Should reject invalid Riot ID format"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        with pytest.raises(ValidationError) as exc:
            GamePassportService.create_passport(
                user=user,
                game='valorant',
                ign='ThisIsWayTooLongForARiotName',  # Invalid - exceeds 16 char max
                discriminator='1234',
                actor_user_id=user.id
            )
        
        # Validation error for IGN length
        assert 'ign' in str(exc.value).lower() or 'riot_name' in str(exc.value).lower() or 'max_length' in str(exc.value).lower()
    
    def test_create_duplicate_passport_same_user(self):
        """Should reject duplicate passport for same game"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        # Create first passport
        GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        # Try to create second passport for same game
        with pytest.raises(ValidationError) as exc:
            GamePassportService.create_passport(
                user=user,
                game='valorant',
                ign='Player',
                discriminator='5678',
                actor_user_id=user.id
            )
        
        assert 'already have' in str(exc.value).lower()
    
    def test_global_uniqueness_enforcement(self):
        """Should prevent two users from claiming same identity"""
        user1 = User.objects.create_user(username='player1', email='p1@test.com')
        user2 = User.objects.create_user(username='player2', email='p2@test.com')
        
        # User1 creates passport
        GamePassportService.create_passport(
            user=user1,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user1.id
        )
        
        # User2 tries to claim same identity (case insensitive)
        with pytest.raises(ValidationError) as exc:
            GamePassportService.create_passport(
                user=user2,
                game='valorant',
                ign='PLAYER',  # Different case, same normalized key
                discriminator='1234',
                actor_user_id=user2.id
            )
        
        assert 'already registered' in str(exc.value).lower() or 'already exists' in str(exc.value).lower()
    
    def test_create_cs2_passport_with_steam_id(self):
        """Should create CS2 passport with valid Steam ID"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='cs2',
            ign='76561198012345678',  # 17-digit Steam ID as IGN
            actor_user_id=user.id
        )
        
        assert passport.ign == '76561198012345678'
        assert passport.identity_key == '76561198012345678'
        assert passport.discriminator is None  # CS2 doesn't use discriminator
    
    def test_create_mlbb_passport_with_zone(self):
        """Should create MLBB passport with player_id and server_id"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='mlbb',
            ign='123456789',
            discriminator='1234',  # Server ID
            actor_user_id=user.id
        )
        
        assert passport.ign == '123456789'
        assert passport.discriminator == '1234'
        assert passport.identity_key == '123456789:1234'
        assert passport.in_game_name == '123456789:1234'  # Auto-generated


@pytest.mark.django_db
class TestIdentityChangeCooldown:
    """Test identity change cooldown enforcement"""
    
    def test_change_identity_without_cooldown(self):
        """Should allow identity change when not locked"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        # Create passport
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        # Change identity
        updated = GamePassportService.update_passport_identity(
            user=user,
            game='valorant',
            ign='NewName',
            discriminator='5678',
            reason='Rebranding',
            actor_user_id=user.id,
            request_ip='127.0.0.1'
        )
        
        assert updated.ign == 'NewName'
        assert updated.discriminator == '5678'
        assert updated.in_game_name == 'NewName#5678'
        assert updated.identity_key == 'newname#5678'
        assert updated.locked_until is not None
        assert updated.is_identity_locked() is True
        
        # Check alias created
        aliases = GameProfileAlias.objects.filter(game_profile=passport)
        assert aliases.count() == 1
        assert aliases[0].old_in_game_name == 'Player#1234'
        assert aliases[0].reason == 'Rebranding'
    
    def test_change_identity_during_cooldown(self):
        """Should reject identity change during cooldown"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        # Create and change identity
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        GamePassportService.update_passport_identity(
            user=user,
            game='valorant',
            ign='NewName',
            discriminator='5678',
            actor_user_id=user.id
        )
        
        # Try to change again immediately
        with pytest.raises(ValidationError) as exc:
            GamePassportService.update_passport_identity(
                user=user,
                game='valorant',
                ign='Another',
                discriminator='9999',
                actor_user_id=user.id
            )
        
        assert 'locked until' in str(exc.value).lower()
    
    def test_metadata_update_does_not_trigger_cooldown(self):
        """Should allow metadata updates without triggering cooldown"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        # Update metadata
        GamePassportService.update_passport_metadata(
            user=user,
            game='valorant',
            metadata={'peak_rank': 'Immortal'},
            rank_name='Diamond',
            actor_user_id=user.id
        )
        
        passport.refresh_from_db()
        assert passport.locked_until is None
        assert passport.metadata['peak_rank'] == 'Immortal'
        assert passport.rank_name == 'Diamond'
    
    def test_same_identity_update_does_not_lock(self):
        """Should not lock if identity key remains same"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        # "Change" to same identity (different case)
        GamePassportService.update_passport_identity(
            user=user,
            game='valorant',
            ign='PLAYER',  # Same normalized key
            discriminator='1234',
            actor_user_id=user.id
        )
        
        passport.refresh_from_db()
        assert passport.locked_until is None
        assert GameProfileAlias.objects.filter(game_profile=passport).count() == 0


@pytest.mark.django_db
class TestPinningSystem:
    """Test passport pinning and ordering"""
    
    def test_pin_passport(self):
        """Should pin passport successfully"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        GamePassportService.pin_passport(user=user, game='valorant', pin=True)
        
        passport.refresh_from_db()
        assert passport.is_pinned is True
        assert passport.pinned_order == 1
    
    def test_max_pinned_limit(self):
        """Should enforce max pinned games limit"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        config = GameProfileConfig.get_config()
        config.max_pinned_games = 2
        config.save()
        
        # Create and pin 2 passports
        for i, game in enumerate(['valorant', 'cs2']):
            if game == 'valorant':
                passport = GamePassportService.create_passport(
                    user=user,
                    game=game,
                    ign=f'Player{i+1}',
                    discriminator='1234',
                    actor_user_id=user.id
                )
            else:  # cs2
                passport = GamePassportService.create_passport(
                    user=user,
                    game=game,
                    ign=f'7656119801234567{i}',
                    actor_user_id=user.id
                )
            GamePassportService.pin_passport(user=user, game=game, pin=True)
        
        # Create 3rd passport
        GamePassportService.create_passport(
            user=user,
            game='dota2',
            ign='76561198012345679',
            actor_user_id=user.id
        )
        
        # Try to pin 3rd
        with pytest.raises(ValidationError) as exc:
            GamePassportService.pin_passport(user=user, game='dota2', pin=True)
        
        assert 'maximum' in str(exc.value).lower()
    
    def test_reorder_pinned_passports(self):
        """Should reorder pinned passports"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        # Create 3 passports and pin them
        games = ['valorant', 'cs2', 'dota2']
        for i, game in enumerate(games):
            if game == 'valorant':
                GamePassportService.create_passport(
                    user=user,
                    game=game,
                    ign=f'Player{i+1}',
                    discriminator='1234',
                    actor_user_id=user.id
                )
            else:  # cs2, dota2
                GamePassportService.create_passport(
                    user=user,
                    game=game,
                    ign=f'7656119801234567{i}',
                    actor_user_id=user.id
                )
            GamePassportService.pin_passport(user=user, game=game, pin=True)
        
        # Reorder
        new_order = ['dota2', 'valorant', 'cs2']
        GamePassportService.reorder_pinned_passports(user=user, game_order=new_order)
        
        # Check order
        from apps.games.models import Game
        passports = GameProfile.objects.filter(user=user, is_pinned=True).order_by('pinned_order')
        assert [p.game.slug for p in passports] == new_order


@pytest.mark.django_db
class TestPrivacyControls:
    """Test visibility and privacy settings"""
    
    def test_set_visibility_public(self):
        """Should set visibility to PUBLIC"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            visibility=GameProfile.VISIBILITY_PRIVATE,
            actor_user_id=user.id
        )
        
        GamePassportService.set_visibility(
            user=user,
            game='valorant',
            visibility=GameProfile.VISIBILITY_PUBLIC
        )
        
        passport.refresh_from_db()
        assert passport.visibility == GameProfile.VISIBILITY_PUBLIC
    
    def test_set_lft_flag(self):
        """Should set looking-for-team flag"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        GamePassportService.set_lft(user=user, game='valorant', is_lft=True)
        
        passport.refresh_from_db()
        assert passport.is_lft is True


@pytest.mark.django_db
class TestAuditTrail:
    """Test audit event recording"""
    
    def test_creation_audit(self):
        """Should record audit event on creation"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id,
            request_ip='192.168.1.1'
        )
        
        audit = UserAuditEvent.objects.filter(
            event_type='game_passport.created',
            object_id=passport.id
        ).first()
        
        assert audit is not None
        assert audit.subject_user_id == user.id
        assert audit.ip_address == '192.168.1.1'
        assert audit.after_snapshot['identity_key'] == 'player#1234'
    
    def test_identity_change_audit(self):
        """Should record audit event on identity change"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        GamePassportService.update_passport_identity(
            user=user,
            game='valorant',
            ign='NewName',
            discriminator='5678',
            actor_user_id=user.id
        )
        
        audit = UserAuditEvent.objects.filter(
            event_type='game_passport.identity_changed',
            object_id=passport.id
        ).first()
        
        assert audit is not None
        assert audit.before_snapshot['identity_key'] == 'player#1234'
        assert audit.after_snapshot['identity_key'] == 'newname#5678'
    
    def test_deletion_audit(self):
        """Should record audit event on deletion"""
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        passport_id = passport.id
        GamePassportService.delete_passport(user=user, game='valorant', actor_user_id=user.id)
        
        audit = UserAuditEvent.objects.filter(
            event_type='game_passport.deleted',
            object_id=passport_id
        ).first()
        
        assert audit is not None
        assert audit.before_snapshot['identity_key'] == 'player#1234'


@pytest.mark.django_db
class TestConfigManagement:
    """Test configuration singleton"""
    
    def test_config_singleton(self):
        """Should return same config instance"""
        config1 = GameProfileConfig.get_config()
        config2 = GameProfileConfig.get_config()
        
        assert config1.id == config2.id
        assert GameProfileConfig.objects.count() == 1
    
    def test_config_defaults(self):
        """Should have correct default values"""
        config = GameProfileConfig.get_config()
        
        assert config.cooldown_days == 30
        assert config.allow_id_change is True
        assert config.max_pinned_games == 3
        assert config.require_region is False
        assert config.enable_ip_smurf_detection is False
    
    def test_disable_id_changes(self):
        """Should block identity changes when disabled"""
        config = GameProfileConfig.get_config()
        config.allow_id_change = False
        config.save()
        
        user = User.objects.create_user(username='player1', email='p1@test.com')
        
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            ign='Player',
            discriminator='1234',
            actor_user_id=user.id
        )
        
        with pytest.raises(PermissionDenied):
            GamePassportService.update_passport_identity(
                user=user,
                game='valorant',
                ign='NewName',
                discriminator='5678',
                actor_user_id=user.id
            )
