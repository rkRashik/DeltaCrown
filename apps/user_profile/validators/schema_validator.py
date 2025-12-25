"""
Game Passport Schema Validator (GP-1, GP-2A)

Shared validation module used by BOTH:
- GameProfileAdminForm (admin interface)
- GamePassportService (service layer + API)

Single source of truth for validation rules.
All validation logic is driven by GamePassportSchema.

GP-2A: Updated to work with structured identity fields (ign/discriminator/platform/region)
       while maintaining backward compatibility with JSON identity_data input.
"""

from typing import Dict, Tuple, Optional
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.user_profile.models import GamePassportSchema, GameProfile
from apps.games.models import Game


class ValidationResult:
    """Result of schema validation (GP-2A extended)"""
    
    def __init__(self, is_valid: bool, errors: Dict[str, str] = None, 
                 normalized_identity: Dict = None, identity_key: str = None,
                 in_game_name: str = None, 
                 ign: str = None, discriminator: str = None, 
                 platform: str = None, region: str = None):
        self.is_valid = is_valid
        self.errors = errors or {}
        self.normalized_identity = normalized_identity or {}
        self.identity_key = identity_key or ''
        self.in_game_name = in_game_name or ''
        # GP-2A: Structured identity fields
        self.ign = ign or ''
        self.discriminator = discriminator or ''
        self.platform = platform or ''
        self.region = region or ''
    
    def raise_if_invalid(self):
        """Raise ValidationError if invalid"""
        if not self.is_valid:
            error_messages = []
            for field_name, error_msg in self.errors.items():
                error_messages.append(f"{field_name}: {error_msg}")
            raise DjangoValidationError('; '.join(error_messages))


class GamePassportSchemaValidator:
    """
    Schema-driven validator for Game Passports (GP-1, GP-2A).
    
    Uses GamePassportSchema to:
    - Validate identity fields (required/optional)
    - Normalize identity data (lowercase for Riot IDs)
    - Compute identity_key (for uniqueness)
    - Validate region/rank/role choices
    - Enforce global uniqueness
    
    GP-2A: Primary validation now uses structured fields (ign/discriminator/platform/region).
           Legacy JSON identity_data input is converted to structured fields automatically.
    
    This is the single source of truth for validation logic.
    """
    
    @staticmethod
    def validate_structured(
        game: Game,
        ign: str = None,
        discriminator: str = None,
        platform: str = None,
        region: str = None,
        main_role: str = None,
        user=None,
        passport_id: int = None
    ) -> ValidationResult:
        """
        GP-2A: Validate Game Passport using structured identity fields.
        
        This is the PRIMARY validation method going forward.
        
        Args:
            game: Game instance (must be valid Game object)
            ign: In-game name / username (required for most games)
            discriminator: Discriminator / Tag / Zone (required for Riot, MLBB)
            platform: Platform identifier (required for some games)
            region: Player region (optional or required per schema)
            main_role: Player role (optional)
            user: User instance (for uniqueness check)
            passport_id: Existing passport ID (for updates, exclude from uniqueness check)
        
        Returns:
            ValidationResult: Validation result with normalized data
        """
        errors = {}
        
        # 1. Get schema for game
        try:
            schema = GamePassportSchema.objects.get(game=game)
        except GamePassportSchema.DoesNotExist:
            errors['game'] = (
                f'No passport schema configured for {game.display_name}. '
                'Please run: python manage.py seed_game_passport_schemas'
            )
            return ValidationResult(is_valid=False, errors=errors)
        
        # 2. Convert structured fields to identity_data dict for schema validation
        identity_data = {}
        game_slug = game.slug if game else None
        
        # Map structured fields to schema field names
        if game_slug in ['valorant', 'lol', 'tft']:
            # Riot games: ign → riot_name, discriminator → tagline
            if ign:
                identity_data['riot_name'] = ign
            if discriminator:
                identity_data['tagline'] = discriminator
        elif game_slug == 'mlbb':
            # MLBB: ign → numeric_id, discriminator → zone_id
            if ign:
                identity_data['numeric_id'] = ign
            if discriminator:
                identity_data['zone_id'] = discriminator
        elif game_slug in ['cs2', 'dota2']:
            # Steam games: ign → steam_id64
            if ign:
                identity_data['steam_id64'] = ign
        elif game_slug == 'eafc':
            # EA FC: ign → ea_id, platform → platform
            if ign:
                identity_data['ea_id'] = ign
            if platform:
                identity_data['platform'] = platform
        elif game_slug == 'efootball':
            # eFootball: ign → konami_id, platform → platform
            if ign:
                identity_data['konami_id'] = ign
            if platform:
                identity_data['platform'] = platform
        elif game_slug == 'r6':
            # Rainbow Six: ign → ubisoft_username, platform → platform
            if ign:
                identity_data['ubisoft_username'] = ign
            if platform:
                identity_data['platform'] = platform
        elif game_slug in ['fortnite', 'rocketleague']:
            # Epic games: ign → epic_id
            if ign:
                identity_data['epic_id'] = ign
        else:
            # Generic: ign → player_id or in_game_name
            if ign:
                identity_data['player_id'] = ign
        
        # 3. Validate identity_data using schema
        if not identity_data:
            errors['ign'] = 'Identity fields are required. Please provide at least an IGN.'
            return ValidationResult(is_valid=False, errors=errors)
        
        is_valid_identity, identity_errors = schema.validate_identity_data(identity_data)
        if not is_valid_identity:
            # Map schema field errors back to structured field names
            for field_name, error_msg in identity_errors.items():
                if field_name in ['riot_name', 'steam_id64', 'numeric_id', 'ea_id', 'konami_id', 'ubisoft_username', 'epic_id', 'player_id']:
                    errors['ign'] = error_msg
                elif field_name in ['tagline', 'zone_id']:
                    errors['discriminator'] = error_msg
                elif field_name == 'platform':
                    errors['platform'] = error_msg
                else:
                    errors[field_name] = error_msg
        
        # 4. Normalize identity data
        normalized_identity = schema.normalize_identity_data(identity_data)
        
        # 5. Compute in_game_name (preserves original case)
        in_game_name = schema.format_identity(identity_data)
        
        # 6. Compute identity_key (uses normalized data)
        identity_key = schema.compute_identity_key(normalized_identity)
        
        # 7. Validate region
        if region:
            if not schema.validate_region(region):
                region_values = [
                    choice['value'] if isinstance(choice, dict) else choice
                    for choice in (schema.region_choices or [])
                ]
                allowed_regions = ', '.join(region_values) if region_values else '(none configured)'
                errors['region'] = (
                    f'Invalid region "{region}". '
                    f'Allowed regions for {game.display_name}: {allowed_regions}'
                )
        elif schema.region_required:
            errors['region'] = f'Region is required for {game.display_name}.'
        
        # 8. Validate role
        if main_role:
            if not schema.validate_role(main_role):
                role_values = [
                    choice['value'] if isinstance(choice, dict) else choice
                    for choice in (schema.role_choices or [])
                ]
                allowed_roles = ', '.join(role_values) if role_values else '(none configured)'
                errors['main_role'] = (
                    f'Invalid role "{main_role}". '
                    f'Allowed roles for {game.display_name}: {allowed_roles}'
                )
        
        # 9. Enforce global uniqueness (case-insensitive via normalized identity_key)
        if user:
            existing_profiles = GameProfile.objects.filter(
                game=game,
                identity_key=identity_key
            )
            
            if passport_id:
                existing_profiles = existing_profiles.exclude(pk=passport_id)
            
            if existing_profiles.exists():
                errors['ign'] = (
                    f'This identity is already registered for {game.display_name}.'
                )
        
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        
        # Extract normalized structured fields from normalized_identity
        normalized_ign = ign
        normalized_discriminator = discriminator
        normalized_platform = platform
        normalized_region = region
        
        # Apply normalization (lowercase for Riot)
        if game_slug in ['valorant', 'lol', 'tft']:
            normalized_ign = normalized_identity.get('riot_name', ign)
            normalized_discriminator = normalized_identity.get('tagline', discriminator)
        
        return ValidationResult(
            is_valid=True,
            normalized_identity=normalized_identity,
            identity_key=identity_key,
            in_game_name=in_game_name,
            ign=normalized_ign or ign,
            discriminator=normalized_discriminator or discriminator,
            platform=normalized_platform or platform,
            region=normalized_region or region
        )
    
    @staticmethod
    def validate_full_passport(
        game: Game,
        identity_data: Dict,
        region: str = None,
        main_role: str = None,
        user=None,
        passport_id: int = None
    ) -> ValidationResult:
        """
        LEGACY: Validate Game Passport using JSON identity_data dict.
        
        This method provides backward compatibility for existing code.
        Internally converts identity_data to structured fields and calls validate_structured().
        
        Args:
            game: Game instance (must be valid Game object)
            identity_data: Identity fields dict (e.g., {"riot_name": "...", "tagline": "..."})
            region: Player region (optional or required per schema)
            main_role: Player role (optional)
            user: User instance (for uniqueness check)
            passport_id: Existing passport ID (for updates, exclude from uniqueness check)
        
        Returns:
            ValidationResult: Validation result with normalized data
        """
        if not identity_data:
            return ValidationResult(
                is_valid=False,
                errors={'identity_data': 'Identity fields are required.'}
            )
        
        # Convert identity_data dict to structured fields
        game_slug = game.slug if game else None
        ign = None
        discriminator = None
        platform = None
        
        if game_slug in ['valorant', 'lol', 'tft']:
            # Riot games: riot_name → ign, tagline → discriminator
            ign = identity_data.get('riot_name')
            discriminator = identity_data.get('tagline')
        elif game_slug == 'mlbb':
            # MLBB: numeric_id → ign, zone_id → discriminator
            ign = str(identity_data.get('numeric_id', '')) if identity_data.get('numeric_id') else None
            discriminator = str(identity_data.get('zone_id', '')) if identity_data.get('zone_id') else None
        elif game_slug in ['cs2', 'dota2']:
            # Steam games: steam_id64 → ign
            ign = identity_data.get('steam_id64')
        elif game_slug == 'eafc':
            # EA FC: ea_id → ign, platform → platform
            ign = identity_data.get('ea_id')
            platform = identity_data.get('platform')
        elif game_slug == 'efootball':
            # eFootball: konami_id → ign, platform → platform
            ign = identity_data.get('konami_id')
            platform = identity_data.get('platform')
        elif game_slug == 'r6':
            # Rainbow Six: ubisoft_username → ign, platform → platform
            ign = identity_data.get('ubisoft_username')
            platform = identity_data.get('platform')
        elif game_slug in ['fortnite', 'rocketleague']:
            # Epic games: epic_id → ign
            ign = identity_data.get('epic_id')
        else:
            # Generic: Try common field names
            ign = identity_data.get('player_id') or identity_data.get('in_game_name') or identity_data.get('username')
        
        # Call new structured validation method
        return GamePassportSchemaValidator.validate_structured(
            game=game,
            ign=ign,
            discriminator=discriminator,
            platform=platform,
            region=region,
            main_role=main_role,
            user=user,
            passport_id=passport_id
        )
    
    @staticmethod
    def validate_identity_only(game: Game, identity_data: Dict) -> ValidationResult:
        """
        Validate just identity fields (without region/role/uniqueness).
        
        Useful for pre-validation checks.
        
        Args:
            game: Game instance
            identity_data: Identity fields dict
        
        Returns:
            ValidationResult: Validation result
        """
        errors = {}
        
        # Get schema
        try:
            schema = GamePassportSchema.objects.get(game=game)
        except GamePassportSchema.DoesNotExist:
            errors['game'] = f'No passport schema configured for {game.display_name}.'
            return ValidationResult(is_valid=False, errors=errors)
        
        # Validate identity_data
        if not identity_data:
            errors['identity_data'] = 'Identity fields are required.'
            return ValidationResult(is_valid=False, errors=errors)
        
        is_valid, identity_errors = schema.validate_identity_data(identity_data)
        if not is_valid:
            errors.update(identity_errors)
            return ValidationResult(is_valid=False, errors=errors)
        
        # Normalize
        normalized_identity = schema.normalize_identity_data(identity_data)
        identity_key = schema.compute_identity_key(normalized_identity)
        in_game_name = schema.format_identity(identity_data)
        
        return ValidationResult(
            is_valid=True,
            normalized_identity=normalized_identity,
            identity_key=identity_key,
            in_game_name=in_game_name
        )
    
    @staticmethod
    def check_uniqueness(
        game: Game,
        identity_key: str,
        exclude_passport_id: int = None
    ) -> Tuple[bool, Optional[GameProfile]]:
        """
        Check if identity_key is globally unique for this game.
        
        Args:
            game: Game instance
            identity_key: Normalized identity key
            exclude_passport_id: Passport ID to exclude from check (for updates)
        
        Returns:
            Tuple[bool, Optional[GameProfile]]: (is_unique, existing_passport_or_none)
        """
        existing = GameProfile.objects.filter(
            game=game,
            identity_key=identity_key
        )
        
        if exclude_passport_id:
            existing = existing.exclude(pk=exclude_passport_id)
        
        if existing.exists():
            return False, existing.first()
        
        return True, None
