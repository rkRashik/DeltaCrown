"""
Game Passport Service (Phase 9A-13 Consolidated)

Canonical service layer for ALL passport operations:
- CRUD operations with audit trail
- Identity change cooldown enforcement
- Alias history tracking
- Pinning/ordering management
- Privacy controls
- Teams/Tournaments integration (Phase 9A-12)
- Roster validation
- Identity payload building

This is the SINGLE SOURCE OF TRUTH for passport logic.
All other apps (teams, tournaments, etc.) MUST use this service.

Replaces:
- passport_service.py (Phase 9A-4 gap-filling - REMOVED)
- passport_integration.py (Phase 9A-12 helpers - MERGED HERE)

Version: 2.0 (Phase 9A-13 - January 2026)
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from apps.user_profile.models import GameProfile, GameProfileAlias, GameProfileConfig
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.services.audit import AuditService
from apps.user_profile.validators import GameValidators
from apps.user_profile.validators.schema_validator import GamePassportSchemaValidator
from apps.games.models import Game

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of passport validation for team/tournament actions.
    
    Attributes:
        is_valid: Whether passport meets all requirements
        errors: List of error messages (user-friendly)
        missing_fields: List of missing required field names
        passport: GameProfile instance if found, else None
        help_url: Link to passport settings page
    """
    is_valid: bool
    errors: List[str]
    missing_fields: List[str]
    passport: Optional[GameProfile] = None
    help_url: str = "/settings/#game-passports"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for API responses"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'missing_fields': self.missing_fields,
            'passport_id': self.passport.id if self.passport else None,
            'help_url': self.help_url,
        }


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
        
        # Delete using raw SQL to avoid ORM caching issues
        from django.db import connection
        with connection.cursor() as cursor:
            # Delete aliases first
            cursor.execute("DELETE FROM user_profile_gameprofilealias WHERE game_profile_id = %s", [passport_id])
            # Delete passport
            cursor.execute("DELETE FROM user_profile_gameprofile WHERE id = %s", [passport_id])
        
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
    
    # ===================================================================
    # TEAMS & TOURNAMENTS INTEGRATION (Phase 9A-12 - Merged from passport_integration.py)
    # ===================================================================
    
    @staticmethod
    def validate_passport_for_team_action(
        user: User, 
        game_slug: str, 
        action: str = 'create'
    ) -> ValidationResult:
        """
        Validate user has a complete passport for team/tournament actions.
        
        Used by:
        - Team creation (action='create')
        - Team invitation acceptance (action='join')
        - Tournament registration (action='register')
        
        Checks:
        - Passport exists
        - All required identity fields present
        - Passport not flagged
        
        Args:
            user: Django User instance
            game_slug: Game slug (e.g., 'valorant', 'cs2')
            action: Action type for error messaging ('create', 'join', 'register')
        
        Returns:
            ValidationResult with is_valid, errors, missing_fields, passport
        """
        # Get passport
        passport = GamePassportService.get_passport(user, game_slug)
        
        # Get game for messaging
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return ValidationResult(
                is_valid=False,
                errors=[f"Game '{game_slug}' not found"],
                missing_fields=['game'],
                passport=None
            )
        
        if not passport:
            # Contextual error message based on action
            action_verb = {
                'create': 'create a team',
                'join': 'join this team',
                'register': 'register for this tournament'
            }.get(action, 'perform this action')
            
            return ValidationResult(
                is_valid=False,
                errors=[f"You need a Game Passport for {game.display_name} to {action_verb}"],
                missing_fields=['passport'],
                passport=None
            )
        
        # Get identity config for required fields
        from apps.games.services.game_service import GameService
        identity_configs = GameService.get_identity_validation_rules(game)
        
        missing_fields = []
        errors = []
        
        # Check required identity fields
        for config in identity_configs:
            if config.is_required:
                field_value = getattr(passport, config.field_name, None)
                if not field_value:
                    missing_fields.append(config.field_name)
                    errors.append(
                        f"Missing required field: {config.display_name}"
                    )
        
        # Check verification status (if FLAGGED, block action)
        if passport.verification_status == 'FLAGGED':
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Your {game.display_name} passport is flagged. Please contact support."
                ],
                missing_fields=[],
                passport=passport
            )
        
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                missing_fields=missing_fields,
                passport=passport
            )
        
        # All checks passed
        return ValidationResult(
            is_valid=True,
            errors=[],
            missing_fields=[],
            passport=passport
        )
    
    @staticmethod
    def build_identity_payload(user: User, game_slug: str) -> Dict[str, Any]:
        """
        Build identity payload from user's passport for team/tournament operations.
        
        Used for:
        - Team roster display
        - Tournament registration auto-fill
        - Identity snapshots
        
        Args:
            user: Django User instance
            game_slug: Game slug (e.g., 'valorant', 'cs2')
        
        Returns:
            Dict with ign, rank, platform, region, server, etc. from passport
            Empty dict if passport not found
        """
        passport = GamePassportService.get_passport(user, game_slug)
        
        if not passport:
            return {}
        
        # Build payload from passport
        payload = {
            'user_id': user.id,
            'username': user.username,
            'game_slug': game_slug,
            'ign': passport.ign,
            'passport_id': passport.id,
            'verification_status': passport.verification_status,
            'created_at': passport.created_at.isoformat(),
            'updated_at': passport.updated_at.isoformat(),
        }
        
        # Add optional fields if present
        optional_fields = [
            'rank', 'division', 'platform', 'region', 'server', 'preferred_mode',
            'riot_id', 'riot_tagline', 'steam_id', 'ea_id', 'konami_id',
            'pubg_id', 'garena_id', 'activision_id', 'ubisoft_username',
            'epic_games_id', 'moonton_id'
        ]
        
        for field in optional_fields:
            value = getattr(passport, field, None)
            if value:
                payload[field] = value
        
        return payload
    
    @staticmethod
    def get_roster_passports_bulk(
        users: List[User], 
        game_slug: str
    ) -> Dict[int, Optional[GameProfile]]:
        """
        Bulk fetch passports for a roster of users.
        
        Optimized for tournament registration validation and team roster display.
        
        Args:
            users: List of Django User instances
            game_slug: Game slug (e.g., 'valorant', 'cs2')
        
        Returns:
            Dict mapping user_id -> GameProfile (or None if not found)
        """
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            logger.warning(f"Game not found: {game_slug}")
            return {user.id: None for user in users}
        
        user_ids = [user.id for user in users]
        
        passports = GameProfile.objects.filter(
            user_id__in=user_ids,
            game=game
        ).select_related('game')
        
        # Build mapping
        passport_map = {p.user_id: p for p in passports}
        
        # Ensure all user IDs are in map (with None for missing passports)
        for user_id in user_ids:
            if user_id not in passport_map:
                passport_map[user_id] = None
        
        return passport_map
    
    @staticmethod
    def validate_roster_passports(
        users: List[User], 
        game_slug: str
    ) -> Dict[str, Any]:
        """
        Validate all roster members have valid passports.
        
        Used for tournament registration pre-validation.
        
        Args:
            users: List of Django User instances
            game_slug: Game slug (e.g., 'valorant', 'cs2')
        
        Returns:
            Dict with:
                - is_valid (bool): All members have valid passports
                - errors (List[Dict]): Per-member errors
                - missing_count (int): Count of missing passports
                - total_members (int): Total roster size
        """
        passport_map = GamePassportService.get_roster_passports_bulk(users, game_slug)
        
        errors = []
        missing_count = 0
        
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return {
                'is_valid': False,
                'errors': [{'username': 'all', 'error': f"Game '{game_slug}' not found"}],
                'missing_count': len(users),
                'total_members': len(users),
            }
        
        # Get identity config for required fields
        from apps.games.services.game_service import GameService
        identity_configs = GameService.get_identity_validation_rules(game)
        required_fields = [c.field_name for c in identity_configs if c.is_required]
        
        for user in users:
            passport = passport_map.get(user.id)
            
            if not passport:
                errors.append({
                    'user_id': user.id,
                    'username': user.username,
                    'error': f"No passport for {game.display_name}",
                    'missing_fields': ['passport'],
                    'passport_url': f"/settings/#game-passports",
                })
                missing_count += 1
                continue
            
            # Check verification status
            if passport.verification_status == 'FLAGGED':
                errors.append({
                    'user_id': user.id,
                    'username': user.username,
                    'error': f"Passport is flagged for {game.display_name}",
                    'missing_fields': [],
                })
                continue
            
            # Check required fields
            member_missing_fields = []
            for field_name in required_fields:
                if not getattr(passport, field_name, None):
                    member_missing_fields.append(field_name)
            
            if member_missing_fields:
                errors.append({
                    'user_id': user.id,
                    'username': user.username,
                    'error': f"Missing required fields: {', '.join(member_missing_fields)}",
                    'missing_fields': member_missing_fields,
                    'passport_url': f"/settings/#game-passports",
                })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'missing_count': missing_count,
            'total_members': len(users),
        }
