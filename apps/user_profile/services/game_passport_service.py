"""
Game Passport Service (GP-0)

First-class game identity management with:
- CRUD operations
- Identity change cooldown enforcement
- Alias history tracking
- Pinning/ordering management
- Privacy controls
- Full audit trail

NO verification system - removed in GP-0.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
import logging

from apps.user_profile.models import GameProfile, GameProfileAlias, GameProfileConfig
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.services.audit import AuditService
from apps.user_profile.validators import GameValidators
from apps.user_profile.validators.schema_validator import GamePassportSchemaValidator
from apps.games.models import Game

User = get_user_model()
logger = logging.getLogger(__name__)


class GamePassportService:
    """
    Game Passport management service.
    
    All passport operations go through this service to ensure:
    - Validation (per-game rules)
    - Uniqueness (global identity_key)
    - Cooldown enforcement
    - Alias tracking
    - Audit logging
    """
    
    @staticmethod
    @transaction.atomic
    def create_passport(
        user: User,
        game: str,
        ign: str = None,
        discriminator: str = None,
        platform: str = None,
        region: str = '',
        in_game_name: str = None,
        metadata: Dict = None,
        visibility: str = GameProfile.VISIBILITY_PUBLIC,
        actor_user_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> GameProfile:
        """
        Create a new game passport (GP-2A structured identity).
        
        Args:
            user: User creating the passport
            game: Game slug
            ign: In-game name/username (primary identity field)
            discriminator: Discriminator/tag/zone (for Riot, MLBB)
            platform: Platform identifier (for cross-platform games)
            region: Player region
            in_game_name: Display name (auto-computed if not provided)
            metadata: Showcase/config fields only (NOT identity)
            visibility: Privacy level
            actor_user_id: Who is creating (defaults to user)
            request_ip: Request IP for audit
        
        Returns:
            GameProfile: Created passport
        
        Raises:
            ValidationError: Invalid game, IGN format, or duplicate
        """
        # Get config
        config = GameProfileConfig.get_config()
        
        # Validate region requirement
        if config.require_region and not region:
            raise ValidationError("Region is required")
        
        # Get Game instance for validation
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        # Check if user already has passport for this game
        if GameProfile.objects.filter(user=user, game=game_obj).exists():
            raise ValidationError(f"You already have a {game} passport")
        
        # Validate using GP-2A structured validator
        result = GamePassportSchemaValidator.validate_structured(
            game=game_obj,
            ign=ign,
            discriminator=discriminator,
            platform=platform,
            region=region,
            main_role=None,
            user=user,
            passport_id=None
        )
        
        if not result.is_valid:
            error_messages = [f"{k}: {v}" for k, v in result.errors.items()]
            raise ValidationError("; ".join(error_messages))
        
        # Use validated values
        identity_key = result.identity_key
        if not in_game_name:  # Use computed name if not provided
            in_game_name = result.in_game_name
        
        # metadata should only contain showcase/config fields (NOT identity)
        if metadata is None:
            metadata = {}
        
        # Create passport with structured identity columns
        passport = GameProfile.objects.create(
            user=user,
            game=game_obj,
            in_game_name=in_game_name,
            identity_key=identity_key,
            ign=result.ign or ign,
            discriminator=result.discriminator or discriminator,
            platform=result.platform or platform,
            region=region,
            metadata=metadata,
            visibility=visibility,
            status=GameProfile.STATUS_ACTIVE
        )
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.created',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            after_snapshot={
                'game': game,
                'in_game_name': in_game_name,
                'identity_key': identity_key,
                'region': region,
                'visibility': visibility
            },
            metadata={
                'game': game,
                'identity_key': identity_key
            },
            ip_address=request_ip
        )
        
        logger.info(f"Game passport created: user={user.username} game={game} identity={identity_key}")
        return passport
    
    @staticmethod
    @transaction.atomic
    def update_passport_identity(
        user: User,
        game: str,
        ign: str = None,
        discriminator: str = None,
        platform: str = None,
        region: str = None,
        reason: str = '',
        actor_user_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> GameProfile:
        """
        Update passport identity (GP-2A structured fields).
        
        Enforces:
        - Identity change cooldown
        - Global uniqueness
        - Alias history tracking
        
        Args:
            user: Passport owner
            game: Game slug
            ign: New in-game name/username
            discriminator: New discriminator/tag/zone
            platform: New platform identifier
            region: New region (optional update)
            reason: Reason for change
            actor_user_id: Who is updating
            request_ip: Request IP
        
        Returns:
            GameProfile: Updated passport
        
        Raises:
            ValidationError: Invalid, locked, or duplicate
        """
        # Get Game instance first
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        # Get passport
        try:
            passport = GameProfile.objects.select_for_update().get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            raise ValidationError(f"No {game} passport found")
        
        # Get config
        config = GameProfileConfig.get_config()
        
        # Check if identity changes are allowed
        if not config.allow_id_change:
            raise PermissionDenied("Identity changes are currently disabled")
        
        # Check cooldown lock
        if passport.is_identity_locked():
            raise ValidationError(
                f"Identity locked until {passport.locked_until.strftime('%Y-%m-%d')}. "
                f"Please wait before changing again."
            )
        
        # Use current values as defaults if not provided
        if region is None:
            region = passport.region
        
        # Validate using GP-2A structured validator
        result = GamePassportSchemaValidator.validate_structured(
            game=game_obj,
            ign=ign,
            discriminator=discriminator,
            platform=platform,
            region=region,
            main_role=passport.main_role,
            user=user,
            passport_id=passport.id
        )
        
        if not result.is_valid:
            error_messages = [f"{k}: {v}" for k, v in result.errors.items()]
            raise ValidationError("; ".join(error_messages))
        
        # Use validated values
        new_identity_key = result.identity_key
        new_in_game_name = result.in_game_name
        
        # Check if identity actually changed
        if passport.identity_key == new_identity_key:
            # No change, just return passport
            return passport
        
        # Capture old state for alias
        old_in_game_name = passport.in_game_name
        old_identity_key = passport.identity_key
        old_ign = passport.ign
        old_discriminator = passport.discriminator
        old_platform = passport.platform
        old_region = passport.region
        
        # Create alias history with structured fields
        GameProfileAlias.objects.create(
            game_profile=passport,
            old_in_game_name=old_in_game_name,
            old_ign=old_ign,
            old_discriminator=old_discriminator,
            old_platform=old_platform,
            old_region=old_region,
            changed_by_user_id=actor_user_id or user.id,
            request_ip=request_ip,
            reason=reason
        )
        
        # Update passport with new structured identity
        passport.in_game_name = new_in_game_name
        passport.identity_key = new_identity_key
        passport.ign = result.ign or ign
        passport.discriminator = result.discriminator or discriminator
        passport.platform = result.platform or platform
        passport.region = region
        
        # Set cooldown lock
        passport.locked_until = timezone.now() + timedelta(days=config.cooldown_days)
        passport.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.identity_changed',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            before_snapshot={
                'in_game_name': old_in_game_name,
                'identity_key': old_identity_key
            },
            after_snapshot={
                'in_game_name': new_in_game_name,
                'identity_key': new_identity_key
            },
            metadata={
                'game': game,
                'reason': reason,
                'locked_until': passport.locked_until.isoformat()
            },
            ip_address=request_ip
        )
        
        logger.info(
            f"Identity changed: user={user.username} game={game} "
            f"old={old_identity_key} new={new_identity_key}"
        )
        
        return passport
    
    @staticmethod
    @transaction.atomic
    def update_passport_metadata(
        user: User,
        game: str,
        metadata: Dict,
        rank_name: str = None,
        main_role: str = None,
        actor_user_id: Optional[int] = None
    ) -> GameProfile:
        """
        Update passport metadata without changing identity.
        
        Does NOT trigger cooldown.
        
        Args:
            user: Passport owner
            game: Game slug
            metadata: New metadata dict
            rank_name: Optional rank update
            main_role: Optional role update
            actor_user_id: Who is updating
        
        Returns:
            GameProfile: Updated passport
        """
        # Get Game instance
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        try:
            passport = GameProfile.objects.get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            raise ValidationError(f"No {game} passport found")
        
        # Capture old state
        old_metadata = passport.metadata.copy()
        old_rank = passport.rank_name
        old_role = passport.main_role
        
        # Update
        passport.metadata = metadata
        if rank_name is not None:
            passport.rank_name = rank_name
        if main_role is not None:
            passport.main_role = main_role
        passport.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.metadata_updated',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            before_snapshot={
                'metadata': old_metadata,
                'rank_name': old_rank,
                'main_role': old_role
            },
            after_snapshot={
                'metadata': metadata,
                'rank_name': passport.rank_name,
                'main_role': passport.main_role
            },
            metadata={'game': game}
        )
        
        return passport
    
    @staticmethod
    @transaction.atomic
    def pin_passport(
        user: User,
        game: str,
        pin: bool = True,
        actor_user_id: Optional[int] = None
    ) -> GameProfile:
        """
        Pin or unpin a passport.
        
        Enforces max_pinned_games from config.
        
        Args:
            user: Passport owner
            game: Game slug
            pin: True to pin, False to unpin
            actor_user_id: Who is pinning
        
        Returns:
            GameProfile: Updated passport
        
        Raises:
            ValidationError: Max pinned limit reached
        """
        # Get Game instance
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        try:
            passport = GameProfile.objects.get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            raise ValidationError(f"No {game} passport found")
        
        config = GameProfileConfig.get_config()
        
        if pin:
            # Check max pinned
            pinned_count = GameProfile.objects.filter(user=user, is_pinned=True).count()
            if pinned_count >= config.max_pinned_games:
                raise ValidationError(
                    f"Maximum {config.max_pinned_games} pinned passports allowed"
                )
            
            # Pin
            passport.is_pinned = True
            # Auto-assign pinned_order
            max_order = GameProfile.objects.filter(
                user=user, is_pinned=True
            ).aggregate(Max('pinned_order'))['pinned_order__max'] or 0
            passport.pinned_order = max_order + 1
        else:
            # Unpin
            passport.is_pinned = False
            passport.pinned_order = None
        
        passport.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.pinned' if pin else 'game_passport.unpinned',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            metadata={
                'game': game,
                'is_pinned': pin,
                'pinned_order': passport.pinned_order
            }
        )
        
        return passport
    
    @staticmethod
    @transaction.atomic
    def reorder_pinned_passports(
        user: User,
        game_order: List[str],
        actor_user_id: Optional[int] = None
    ) -> List[GameProfile]:
        """
        Reorder pinned passports.
        
        Args:
            user: Passport owner
            game_order: List of game slugs in desired order
            actor_user_id: Who is reordering
        
        Returns:
            List[GameProfile]: Reordered passports
        """
        passports = []
        for idx, game in enumerate(game_order, start=1):
            try:
                game_obj = Game.objects.get(slug=game)
                passport = GameProfile.objects.get(user=user, game=game_obj, is_pinned=True)
                passport.pinned_order = idx
                passport.save()
                passports.append(passport)
            except (Game.DoesNotExist, GameProfile.DoesNotExist):
                continue
        
        # Audit log (use first passport ID as reference)
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.reordered',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passports[0].id if passports else None,
            metadata={
                'game_order': game_order,
                'passport_ids': [p.id for p in passports]
            }
        )
        
        return passports
    
    @staticmethod
    @transaction.atomic
    def set_visibility(
        user: User,
        game: str,
        visibility: str,
        actor_user_id: Optional[int] = None
    ) -> GameProfile:
        """
        Set passport visibility.
        
        Args:
            user: Passport owner
            game: Game slug
            visibility: PUBLIC, PROTECTED, or PRIVATE
            actor_user_id: Who is updating
        
        Returns:
            GameProfile: Updated passport
        """
        # Get Game instance
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        try:
            passport = GameProfile.objects.get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            raise ValidationError(f"No {game} passport found")
        
        old_visibility = passport.visibility
        passport.visibility = visibility
        passport.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.visibility_changed',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            before_snapshot={'visibility': old_visibility},
            after_snapshot={'visibility': visibility},
            metadata={'game': game}
        )
        
        return passport
    
    @staticmethod
    @transaction.atomic
    def set_lft(
        user: User,
        game: str,
        is_lft: bool,
        actor_user_id: Optional[int] = None
    ) -> GameProfile:
        """
        Set looking-for-team flag.
        
        Args:
            user: Passport owner
            game: Game slug
            is_lft: True if looking for team
            actor_user_id: Who is updating
        
        Returns:
            GameProfile: Updated passport
        """
        # Get Game instance
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            raise ValidationError(f"Invalid game: {game}")
        
        try:
            passport = GameProfile.objects.get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            raise ValidationError(f"No {game} passport found")
        
        passport.is_lft = is_lft
        passport.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.lft_changed',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport.id,
            metadata={
                'game': game,
                'is_lft': is_lft
            }
        )
        
        return passport
    
    @staticmethod
    @transaction.atomic
    def delete_passport(
        user: User,
        game: str,
        actor_user_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> bool:
        """
        Delete a game passport.
        
        Args:
            user: Passport owner
            game: Game slug
            actor_user_id: Who is deleting
            request_ip: Request IP
        
        Returns:
            bool: True if deleted
        """
        # Get Game instance
        try:
            game_obj = Game.objects.get(slug=game)
        except Game.DoesNotExist:
            return False
        
        try:
            passport = GameProfile.objects.get(user=user, game=game_obj)
        except GameProfile.DoesNotExist:
            return False
        
        passport_id = passport.id
        identity_key = passport.identity_key
        
        # Delete (cascades to aliases)
        passport.delete()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_passport.deleted',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport_id,
            before_snapshot={
                'game': game,
                'identity_key': identity_key
            },
            metadata={'game': game},
            ip_address=request_ip
        )
        
        logger.info(f"Passport deleted: user={user.username} game={game}")
        return True
    
    @staticmethod
    def get_passport(user: User, game: str) -> Optional[GameProfile]:
        """Get single passport"""
        try:
            game_obj = Game.objects.get(slug=game)
            return GameProfile.objects.get(user=user, game=game_obj)
        except (Game.DoesNotExist, GameProfile.DoesNotExist):
            return None
    
    @staticmethod
    def get_all_passports(user: User) -> List[GameProfile]:
        """Get all passports for user (ordered: pinned first)"""
        return list(GameProfile.objects.filter(user=user))
    
    @staticmethod
    def get_alias_history(user: User, game: str) -> List[GameProfileAlias]:
        """Get identity change history for a passport"""
        try:
            game_obj = Game.objects.get(slug=game)
            passport = GameProfile.objects.get(user=user, game=game_obj)
            return list(passport.aliases.all())
        except (Game.DoesNotExist, GameProfile.DoesNotExist):
            return []
