"""
Test Game Passport Service Schema Enforcement (GP-1 Task 5)

Tests that GamePassportService enforces the same schema validation rules as the admin form.
All validation is driven by GamePassportSchema (single source of truth).

Test Coverage:
1. Required identity fields per game
2. Invalid region rejection
3. Case-insensitive uniqueness for Riot IDs
4. Identity change cooldown enforcement
5. Identity change blocking when disabled
6. Alias creation on identity change
7. Unknown identity field rejection
8. Audit logging for all mutations
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command

from apps.user_profile.models import (
    GameProfile,
    GameProfileAlias,
    GameProfileConfig,
    GamePassportSchema
)
from apps.games.models import Game
from apps.user_profile.services.game_passport_service import GamePassportService
from apps.user_profile.models.audit import UserAuditEvent

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestServiceCreateValidation:
    """Test schema validation in create_passport()"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create Valorant game
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={
                'name': 'VALORANT',
                'display_name': 'VALORANT',
                'short_code': 'VAL',
                'is_active': True
            }
        )
        
        # Seed schema if missing
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        
        self.schema = GamePassportSchema.objects.get(game=self.valorant)
    
    def test_service_create_valorant_requires_riot_name_and_tagline(self):
        """Service should reject Valorant passport without riot_name+tagline"""
        with pytest.raises(ValidationError) as exc_info:
            GamePassportService.create_passport(
                user=self.user,
                game='valorant',
                ign='OnlyName',  # Missing discriminator
                region='NA'
            )
        
        # Should fail validation
        assert 'discriminator' in str(exc_info.value).lower() or 'required' in str(exc_info.value).lower()
    
    def test_service_create_valorant_accepts_valid_identity(self):
        """Service should accept valid Valorant identity"""
        passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='TestPlayer',
            discriminator='NA1',
            region='NA'
        )
        
        assert passport.id is not None
        assert passport.game.slug == 'valorant'
        assert passport.identity_key == 'testplayer#na1'  # Normalized lowercase
        assert passport.in_game_name == 'TestPlayer#NA1'  # Preserves case in display name
        assert passport.ign == 'testplayer'  # GP-2A: ign stored normalized (lowercase)
        assert passport.discriminator == 'na1'  # GP-2A: discriminator stored normalized
    
    def test_service_create_mlbb_requires_numeric_id_and_zone_id(self):
        """Service should reject MLBB passport without numeric_id+zone_id"""
        # Create MLBB game
        mlbb, _ = Game.objects.get_or_create(
            slug='mlbb',
            defaults={
                'name': 'Mobile Legends: Bang Bang',
                'display_name': 'Mobile Legends: Bang Bang',
                'short_code': 'MLBB',
                'is_active': True
            }
        )
        
        if not hasattr(mlbb, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        
        with pytest.raises(ValidationError) as exc_info:
            GamePassportService.create_passport(
                user=self.user,
                game='mlbb',
                ign='123456789',  # Missing discriminator (zone_id)
                region='SEA'
            )
        
        assert 'discriminator' in str(exc_info.value).lower() or 'required' in str(exc_info.value).lower()


class TestServiceRegionValidation:
    """Test region validation in service"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            username='regiontester',
            email='region@example.com',
            password='testpass123'
        )
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_service_blocks_invalid_region_not_in_schema(self):
        """Service should reject region not in schema.region_choices"""
        with pytest.raises(ValidationError) as exc_info:
            GamePassportService.create_passport(
                user=self.user,
                game='valorant',
                ign='Player',
                discriminator='NA1',
                region='INVALID_REGION'  # Not in schema
            )
        
        assert 'region' in str(exc_info.value).lower()
        assert 'invalid' in str(exc_info.value).lower()


class TestServiceUniquenessEnforcement:
    """Test case-insensitive uniqueness for Riot IDs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='pass')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_service_enforces_case_insensitive_uniqueness_for_riot(self):
        """Service should block duplicate Riot IDs with different case"""
        # User1 creates passport with "Shroud#NA1"
        passport1 = GamePassportService.create_passport(
            user=self.user1,
            game='valorant',
            ign='Shroud',
            discriminator='NA1',
            region='NA'
        )
        
        assert passport1.identity_key == 'shroud#na1'
        assert passport1.ign == 'shroud'  # GP-2A: normalized lowercase
        assert passport1.discriminator == 'na1'  # GP-2A: normalized lowercase
        
        # User2 tries to create passport with "shroud#na1" (lowercase) - should FAIL
        with pytest.raises(ValidationError) as exc_info:
            GamePassportService.create_passport(
                user=self.user2,
                game='valorant',
                ign='shroud',
                discriminator='na1',
                region='NA'
            )
        
        assert 'already registered' in str(exc_info.value).lower()


class TestServiceIdentityChangeCooldown:
    """Test identity change cooldown enforcement"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username='cooldownuser', email='cool@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        
        # Create passport
        self.passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='Player',
            discriminator='NA1',
            region='NA'
        )
        
        # Get config
        self.config = GameProfileConfig.get_config()
    
    def test_service_blocks_identity_change_when_cooldown_active(self):
        """Service should block identity change when locked_until is in future"""
        # Change identity once
        updated = GamePassportService.update_passport_identity(
            user=self.user,
            game='valorant',
            ign='NewPlayer',
            discriminator='NA1',
            reason='Test change'
        )
        
        # locked_until should be set
        assert updated.locked_until is not None
        assert updated.locked_until > timezone.now()
        
        # Try to change again - should FAIL
        with pytest.raises(ValidationError) as exc_info:
            GamePassportService.update_passport_identity(
                user=self.user,
                game='valorant',
                ign='ThirdName',
                discriminator='NA1',
                reason='Blocked change'
            )
        
        assert 'locked' in str(exc_info.value).lower()
    
    def test_service_allows_identity_change_after_cooldown_expires(self):
        """Service should allow identity change after cooldown expires"""
        # Change identity once
        updated = GamePassportService.update_passport_identity(
            user=self.user,
            game='valorant',
            ign='NewPlayer',
            discriminator='NA1',
            reason='First change'
        )
        
        # Manually expire the lock (simulate time passing)
        updated.locked_until = timezone.now() - timedelta(days=1)
        updated.save()
        
        # Now change should succeed
        final = GamePassportService.update_passport_identity(
            user=self.user,
            game='valorant',
            ign='FinalName',
            discriminator='NA1',
            reason='Second change'
        )
        
        assert final.in_game_name == 'FinalName#NA1'
        assert final.identity_key == 'finalname#na1'
        assert final.ign == 'finalname'  # GP-2A: normalized lowercase
        assert final.discriminator == 'na1'  # GP-2A: normalized lowercase


class TestServiceIdentityChangeBlocking:
    """Test identity change blocking when config.allow_id_change = False"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username='blockeduser', email='blocked@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        
        # Create passport
        self.passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='Player',
            discriminator='NA1',
            region='NA'
        )
    
    def test_service_blocks_identity_change_when_allow_id_change_off(self):
        """Service should block identity change when config.allow_id_change = False"""
        # Disable identity changes
        config = GameProfileConfig.get_config()
        config.allow_id_change = False
        config.save()
        
        # Try to change identity - should FAIL
        with pytest.raises(PermissionDenied) as exc_info:
            GamePassportService.update_passport_identity(
                user=self.user,
                game='valorant',
                ign='NewPlayer',
                discriminator='NA1',
                reason='Blocked'
            )
        
        assert 'disabled' in str(exc_info.value).lower()


class TestServiceAliasCreation:
    """Test alias creation on identity change"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username='aliasuser', email='alias@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
        
        # Create passport
        self.passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='OldPlayer',
            discriminator='NA1',
            region='NA'
        )
    
    def test_service_creates_alias_on_identity_change(self):
        """Service should create GameProfileAlias when identity changes"""
        old_ign = self.passport.in_game_name
        
        # Change identity
        updated = GamePassportService.update_passport_identity(
            user=self.user,
            game='valorant',
            ign='NewPlayer',
            discriminator='NA1',
            reason='Name change test'
        )
        
        # Check alias was created
        aliases = GameProfileAlias.objects.filter(game_profile=updated)
        assert aliases.count() == 1
        
        alias = aliases.first()
        assert alias.old_in_game_name == old_ign
        assert alias.reason == 'Name change test'
        assert alias.changed_by_user_id == self.user.id


class TestServiceUnknownFields:
    """Test handling of unknown identity fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username='unknownuser', email='unknown@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_service_accepts_extra_metadata_fields(self):
        """Service should allow extra metadata fields for extensibility"""
        # Create passport with showcase metadata (not identity fields)
        passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='Player',
            discriminator='NA1',
            region='NA',
            metadata={
                'favorite_agent': 'Jett',  # Showcase field
                'rank': 'Immortal'  # Showcase field
            }
        )
        
        # Should succeed (showcase fields stored in metadata)
        assert passport.id is not None
        assert passport.ign == 'player'  # GP-2A: normalized
        assert passport.discriminator == 'na1'  # GP-2A: normalized
        assert passport.metadata.get('favorite_agent') == 'Jett'
        assert passport.metadata.get('rank') == 'Immortal'


class TestServiceAuditLogging:
    """Test audit logging for all mutations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username='audituser', email='audit@example.com', password='pass')
        
        self.valorant, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'name': 'VALORANT', 'display_name': 'VALORANT', 'short_code': 'VAL', 'is_active': True}
        )
        
        if not hasattr(self.valorant, 'passport_schema'):
            call_command('seed_game_passport_schemas')
    
    def test_service_logs_passport_creation(self):
        """Service should log passport creation"""
        passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='Player',
            discriminator='NA1',
            region='NA',
            request_ip='127.0.0.1'
        )
        
        # Check audit event
        events = UserAuditEvent.objects.filter(
            subject_user_id=self.user.id,
            event_type='game_passport.created'
        )
        
        assert events.count() >= 1
        event = events.first()
        assert event.object_type == 'GameProfile'
        assert event.object_id == passport.id
    
    def test_service_logs_identity_change(self):
        """Service should log identity changes"""
        # Create passport
        passport = GamePassportService.create_passport(
            user=self.user,
            game='valorant',
            ign='OldPlayer',
            discriminator='NA1',
            region='NA'
        )
        
        # Change identity
        GamePassportService.update_passport_identity(
            user=self.user,
            game='valorant',
            ign='NewPlayer',
            discriminator='NA1',
            reason='Audit test'
        )
        
        # Check audit event
        events = UserAuditEvent.objects.filter(
            subject_user_id=self.user.id,
            event_type='game_passport.identity_changed'
        )
        
        assert events.count() >= 1
        event = events.first()
        assert event.before_snapshot['in_game_name'] == 'OldPlayer#NA1'
        assert event.after_snapshot['in_game_name'] == 'NewPlayer#NA1'
