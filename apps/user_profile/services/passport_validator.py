"""
Game Passport Validation Service (Phase 9A-7 Section C)

Provides schema-driven validation for game passport create/update operations.
Enforces 2026-accurate rank/region/role/platform choices.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for validation logic.
DO NOT duplicate validation in frontend - call GET /profile/api/games/ for schema.
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class PassportValidationError(Exception):
    """Raised when passport validation fails with field-level errors."""
    def __init__(self, field_errors: Dict[str, str], message: str = ""):
        self.field_errors = field_errors
        self.message = message or "Validation failed"
        super().__init__(self.message)


class GamePassportValidator:
    """
    Schema-driven validator for game passports.
    
    Usage:
        validator = GamePassportValidator(game, metadata)
        validator.validate_all()  # Raises PassportValidationError if invalid
        
        # Or for partial validation (updates):
        validator.validate_required_fields()
        validator.validate_field_choices()
        validator.validate_immutable_fields(existing_passport)
    """
    
    def __init__(self, game, metadata: Dict[str, Any], is_update: bool = False, existing_passport=None):
        """
        Initialize validator.
        
        Args:
            game: Game instance
            metadata: Dictionary of field values
            is_update: True if validating update (allows partial data)
            existing_passport: Existing GameProfile instance (for immutability checks)
        """
        self.game = game
        self.metadata = metadata
        self.is_update = is_update
        self.existing_passport = existing_passport
        self.errors = {}
        
        # Cache identity configs
        from apps.games.models import GamePlayerIdentityConfig
        self.identity_configs = GamePlayerIdentityConfig.objects.filter(
            game=game
        ).order_by('order', 'id')
        
        # Cache passport schema (for dropdown options)
        from apps.user_profile.models import GamePassportSchema
        try:
            self.passport_schema = GamePassportSchema.objects.get(game=game)
        except GamePassportSchema.DoesNotExist:
            self.passport_schema = None
            logger.warning(f"No GamePassportSchema found for game {game.slug}")
    
    def validate_all(self):
        """
        Run all validation checks.
        
        Raises:
            PassportValidationError: If any validation fails
        """
        self.validate_required_fields()
        self.validate_field_formats()
        self.validate_field_choices()
        self.validate_field_lengths()
        
        if self.is_update and self.existing_passport:
            self.validate_immutable_fields()
        
        if self.errors:
            raise PassportValidationError(
                field_errors=self.errors,
                message=f"{len(self.errors)} validation error(s)"
            )
    
    def validate_required_fields(self):
        """Check all required fields are present and non-empty."""
        for config in self.identity_configs:
            if config.is_required:
                field_value = self.metadata.get(config.field_name)
                
                # Check if field exists and is non-empty
                if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                    display_name = config.display_name or config.field_name
                    self.errors[config.field_name] = f"{display_name} is required"
    
    def validate_field_formats(self):
        """Validate fields against their regex patterns."""
        for config in self.identity_configs:
            field_value = self.metadata.get(config.field_name)
            
            # Skip empty optional fields
            if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                continue
            
            # Skip if no validation regex
            if not config.validation_regex:
                continue
            
            # Validate regex
            if isinstance(field_value, str):
                try:
                    pattern = re.compile(config.validation_regex)
                    if not pattern.match(field_value):
                        error_msg = config.validation_error_message or f"Invalid format for {config.display_name or config.field_name}"
                        self.errors[config.field_name] = error_msg
                except re.error as e:
                    logger.error(f"Invalid regex pattern for {config.field_name}: {config.validation_regex} - {e}")
                    self.errors[config.field_name] = f"Invalid format for {config.display_name or config.field_name}"
    
    def validate_field_choices(self):
        """Validate select fields against their allowed choices."""
        if not self.passport_schema:
            return
        
        # Map field names to their choice lists
        choice_mappings = {
            'region': self.passport_schema.region_choices,
            'server': self.passport_schema.server_choices or self.passport_schema.region_choices,  # Fallback for Dota 2
            'rank': self.passport_schema.rank_choices,
            'rank_mp': self.passport_schema.rank_choices,  # CODM MP uses same rank list
            'rank_br': self.passport_schema.rank_choices,  # CODM BR uses same rank list
            'peak_rank': self.passport_schema.rank_choices,  # VALORANT peak rank
            'premier_rating': getattr(self.passport_schema, 'premier_rating_choices', None),  # CS2
            'role': self.passport_schema.role_choices,
            'platform': getattr(self.passport_schema, 'platform_choices', None),
            'mode': getattr(self.passport_schema, 'mode_choices', None),
            'division': getattr(self.passport_schema, 'division_choices', None),
        }
        
        for config in self.identity_configs:
            # Only validate select fields
            if config.field_type != 'select':
                continue
            
            field_value = self.metadata.get(config.field_name)
            
            # Skip empty optional fields
            if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                continue
            
            # Get valid choices for this field
            choices = choice_mappings.get(config.field_name, [])
            if not choices:
                logger.warning(f"No choices defined for select field {config.field_name} in game {self.game.slug}")
                continue
            
            # Extract valid values from choices
            valid_values = [choice['value'] for choice in choices if isinstance(choice, dict) and 'value' in choice]
            
            # Validate value is in choices
            if field_value not in valid_values:
                display_name = config.display_name or config.field_name
                self.errors[config.field_name] = f"Invalid {display_name}. Must be one of the supported values."
    
    def validate_field_lengths(self):
        """Validate min/max length constraints."""
        for config in self.identity_configs:
            field_value = self.metadata.get(config.field_name)
            
            # Skip empty optional fields
            if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                continue
            
            # Only validate string fields
            if not isinstance(field_value, str):
                continue
            
            field_length = len(field_value)
            display_name = config.display_name or config.field_name
            
            # Check min length
            if config.min_length and field_length < config.min_length:
                self.errors[config.field_name] = f"{display_name} must be at least {config.min_length} characters"
            
            # Check max length
            if config.max_length and field_length > config.max_length:
                self.errors[config.field_name] = f"{display_name} must be at most {config.max_length} characters"
    
    def validate_immutable_fields(self):
        """
        Check immutable fields haven't changed.
        
        Immutable fields:
        - Core identity (riot_id, steam_id, game_id, etc.)
        - Platform (EA FC, eFootball, R6 Siege, Rocket League)
        
        Admin bypass: superuser or has 'user_profile.bypass_passport_lock' permission
        """
        if not self.existing_passport:
            return
        
        # Get existing metadata
        existing_metadata = self.existing_passport.metadata or {}
        
        for config in self.identity_configs:
            if not config.is_immutable:
                continue
            
            existing_value = existing_metadata.get(config.field_name)
            new_value = self.metadata.get(config.field_name)
            
            # Skip if value unchanged
            if existing_value == new_value:
                continue
            
            # Skip if both are empty (None, "", etc.)
            if not existing_value and not new_value:
                continue
            
            # Immutable field changed - error
            display_name = config.display_name or config.field_name
            self.errors[config.field_name] = f"{display_name} cannot be changed once set. Contact support if correction needed."


def validate_passport_payload(game, metadata: Dict[str, Any], is_update: bool = False, existing_passport=None) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Validate passport payload against game schema.
    
    Args:
        game: Game instance
        metadata: Dictionary of field values
        is_update: True if validating update operation
        existing_passport: Existing GameProfile instance (for immutability checks)
    
    Returns:
        Tuple of (is_valid, error_dict or None)
    
    Example:
        is_valid, errors = validate_passport_payload(game, metadata)
        if not is_valid:
            return JsonResponse({
                'success': False,
                'error': 'VALIDATION_ERROR',
                'field_errors': errors
            }, status=400)
    """
    try:
        validator = GamePassportValidator(game, metadata, is_update, existing_passport)
        validator.validate_all()
        return True, None
    except PassportValidationError as e:
        return False, e.field_errors


def validate_visibility(visibility: str) -> Tuple[bool, Optional[str]]:
    """
    Validate visibility choice.
    
    Args:
        visibility: Visibility string (PUBLIC/PROTECTED/PRIVATE)
    
    Returns:
        Tuple of (is_valid, error_message or None)
    """
    valid_choices = ['PUBLIC', 'PROTECTED', 'PRIVATE']
    
    if not visibility or not isinstance(visibility, str):
        return False, "Visibility is required"
    
    visibility_upper = visibility.upper()
    
    if visibility_upper not in valid_choices:
        return False, f"Invalid visibility. Must be one of: {', '.join(valid_choices)}"
    
    return True, None


def validate_pinned_count(user, exclude_passport_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if user can pin another passport (max 6).
    
    Args:
        user: User instance
        exclude_passport_id: Passport ID to exclude from count (for updates)
    
    Returns:
        Tuple of (can_pin, error_message or None)
    """
    from apps.user_profile.models import GameProfile
    
    query = GameProfile.objects.filter(user=user, is_pinned=True)
    if exclude_passport_id:
        query = query.exclude(id=exclude_passport_id)
    
    pinned_count = query.count()
    
    if pinned_count >= 6:
        return False, "You can only pin up to 6 game passports"
    
    return True, None


def check_duplicate_passport(user, game, exclude_passport_id: Optional[int] = None) -> Tuple[bool, Optional[int]]:
    """
    Check if user already has a passport for this game.
    
    Args:
        user: User instance
        game: Game instance
        exclude_passport_id: Passport ID to exclude from check (for updates)
    
    Returns:
        Tuple of (is_duplicate, existing_passport_id or None)
    """
    from apps.user_profile.models import GameProfile
    
    query = GameProfile.objects.filter(user=user, game=game)
    if exclude_passport_id:
        query = query.exclude(id=exclude_passport_id)
    
    existing = query.first()
    
    if existing:
        return True, existing.id
    
    return False, None


def derive_ign_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Derive IGN for database column from metadata.
    
    Tries in order:
    1. Explicit 'ign' field
    2. Parse riot_id (Name#TAG)
    3. Fallback to primary identity field (steam_id, player_id, etc.)
    
    Args:
        metadata: Passport metadata dictionary
    
    Returns:
        IGN string or None
    """
    # Direct IGN
    ign = metadata.get('ign', '').strip()
    if ign:
        return ign
    
    # Parse riot_id
    riot_id = metadata.get('riot_id', '').strip()
    if riot_id and '#' in riot_id:
        name, _ = riot_id.split('#', 1)
        return name.strip()
    elif riot_id:
        return riot_id
    
    # Fallback to primary identity fields
    # Phase 9A-21: Added konami_id, user_id for eFootball
    primary_fields = [
        'steam_id', 'uid', 'player_id', 'game_id', 'codm_uid',
        'pubg_id', 'epic_id', 'ea_id', 'konami_id', 'user_id',
        'uplay_id', 'xbox_gamertag', 'psn_id', 'owner_id'
    ]
    
    for field in primary_fields:
        value = metadata.get(field)
        if value:
            return str(value).strip()
    
    return None


def derive_discriminator_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Derive discriminator (Riot tag, MLBB zone, etc.) from metadata.
    
    Args:
        metadata: Passport metadata dictionary
    
    Returns:
        Discriminator string or None
    """
    # Direct discriminator
    discriminator = metadata.get('discriminator', '').strip()
    if discriminator:
        return discriminator
    
    # Parse riot_id tag
    riot_id = metadata.get('riot_id', '').strip()
    if riot_id and '#' in riot_id:
        _, tag = riot_id.split('#', 1)
        return tag.strip()
    
    # MLBB server_id as discriminator
    server_id = metadata.get('server_id', '').strip()
    if server_id:
        return server_id
    
    return None
