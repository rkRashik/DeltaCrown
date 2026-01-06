"""
UP-PHASE15-SESSION3: Game Passports API
CRUD operations for GameProfile/GamePassport model.
PHASE 8B: Backend lock enforcement + verification status
PHASE 9A-13 Section C: Standardized error responses
PHASE 9A-15 Section A: Comprehensive error handling with request_id tracing
PHASE 9A-23: Schema-driven identity_key derivation + proper IntegrityError handling
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.conf import settings
import json
import logging
import uuid
import traceback as tb

from apps.common.api_responses import (
    error_response, success_response, validation_error_response,
    locked_error_response, duplicate_error_response, not_found_error_response
)

logger = logging.getLogger(__name__)


# Phase 9A-23: Schema-driven identity_key derivation
def derive_identity_key(game, metadata, schema_fields=None):
    """
    Derive deterministic identity_key from game schema.
    
    Rules:
    1. Pick first required + immutable field that looks like an ID
    2. Else first required field
    3. Else fallback to 'ign' if schema contains it
    4. Normalize: trim, lowercase
    
    Args:
        game: Game instance
        metadata: Dict of field values
        schema_fields: Optional pre-fetched schema configs
    
    Returns:
        Tuple of (identity_key, identity_source_field)
    
    Raises:
        DjangoValidationError if no identity can be derived
    """
    from apps.games.models import GamePlayerIdentityConfig
    
    if schema_fields is None:
        schema_fields = GamePlayerIdentityConfig.objects.filter(
            game=game
        ).order_by('order')
    
    # Priority 1: Required + Immutable fields (true identity)
    required_immutable = schema_fields.filter(
        is_required=True,
        is_immutable=True
    ).order_by('order')
    
    # ID-like field names (prefer these)
    id_patterns = [
        'user_id', 'konami_id', 'ea_id', 'epic_id', 'riot_id',
        'steam_id', 'player_id', 'uid', 'pubg_id', 'codm_uid',
        'uplay_id', 'xbox_gamertag', 'psn_id', 'game_id', 'owner_id'
    ]
    
    # Try ID-like required fields first
    for config in required_immutable:
        if config.field_name in id_patterns:
            value = metadata.get(config.field_name, '').strip()
            if value:
                identity_key = value.lower().replace(' ', '_')
                return identity_key, config.field_name
    
    # Priority 2: Any required + immutable field
    for config in required_immutable:
        value = metadata.get(config.field_name, '').strip()
        if value:
            identity_key = value.lower().replace(' ', '_')
            return identity_key, config.field_name
    
    # Priority 3: Any required field
    for config in schema_fields.filter(is_required=True).order_by('order'):
        value = metadata.get(config.field_name, '').strip()
        if value:
            identity_key = value.lower().replace(' ', '_')
            return identity_key, config.field_name
    
    # Priority 4: Fallback to IGN if schema has it
    ign_config = schema_fields.filter(field_name='ign').first()
    if ign_config:
        ign = metadata.get('ign', '').strip()
        if ign:
            return ign.lower().replace(' ', '_'), 'ign'
    
    # No identity found - determine which field to request
    if required_immutable.exists():
        first_required = required_immutable.first()
        raise DjangoValidationError({
            first_required.field_name: f'{first_required.display_name} is required to identify your account'
        })
    
    # Should never reach here if schema is configured properly
    raise DjangoValidationError({
        '__all__': 'Unable to determine player identity. Please ensure required fields are filled.'
    })


def safe_image_url(field):
    """Safely extract URL from ImageField, handling None and missing files."""
    try:
        if not field:
            return None
        return getattr(field, 'url', None)
    except Exception:
        return None


def check_passport_locked(passport, user):
    """
    Phase 8B/9A-4/9A-13: Check if passport is locked for editing.
    
    Returns:
        tuple: (is_locked, error_response or None)
        
    Rules:
        - If locked_until > now(): Deny edit/delete (403 LOCKED)
        - If verification_status == VERIFIED: Deny identity edits (403 VERIFIED_LOCK)
        - Admin/staff bypass: superuser or has 'user_profile.bypass_passport_lock' permission
    """
    # Admin/staff bypass
    if user.is_superuser or user.has_perm('user_profile.bypass_passport_lock'):
        return False, None
    
    # Check verification lock (Phase 9A-4)
    if passport.verification_status == 'VERIFIED':
        return True, locked_error_response(
            days_remaining=0,
            locked_until='',
            lock_type='VERIFIED_LOCK'
        )
    
    # Check time-based lock
    if passport.locked_until and passport.locked_until > timezone.now():
        days_left = (passport.locked_until - timezone.now()).days + 1
        return True, locked_error_response(
            days_remaining=days_left,
            locked_until=passport.locked_until.isoformat(),
            lock_type='LOCKED'
        )
    
    return False, None


@login_required
@require_http_methods(["GET"])
def list_game_passports_api(request):
    """
    List all game passports for current user.
    
    Route: GET /profile/api/game-passports/
    
    Returns:
        JSON: {success: true, data: {passports: [{...}, ...]}}
    """
    from apps.user_profile.models import GameProfile
    
    try:
        passports = GameProfile.objects.filter(
            user=request.user
        ).select_related('game').order_by('-is_pinned', 'game__name')
        
        # Phase 9A-28: Import cooldown model
        from apps.user_profile.models.cooldown import GamePassportCooldown
        
        passports_list = []
        for passport in passports:
            # Calculate lock status
            is_locked = passport.locked_until and passport.locked_until > timezone.now()
            days_left = (passport.locked_until - timezone.now()).days + 1 if is_locked else 0
            
            # Phase 9A-28: Check for active cooldown
            cooldown_data = None
            has_cooldown, cooldown_obj = GamePassportCooldown.check_cooldown(
                request.user, 
                passport.game, 
                cooldown_type='POST_DELETE'
            )
            if has_cooldown and cooldown_obj:
                cooldown_data = {
                    'is_active': True,
                    'type': cooldown_obj.cooldown_type,
                    'expires_at': cooldown_obj.expires_at.isoformat(),
                    'days_remaining': cooldown_obj.days_remaining(),
                    'reason': cooldown_obj.reason
                }
            
            passports_list.append({
                'id': passport.id,
                'game_id': passport.game.id,
                'game': {
                    'id': passport.game.id,
                    'name': passport.game.name,
                    'slug': passport.game.slug,
                    'icon': safe_image_url(passport.game.icon),
                },
                'ign': passport.ign,
                'region': passport.region,
                'rank_name': passport.rank_name,
                'is_pinned': passport.is_pinned,
                'passport_data': passport.metadata or {},
                'metadata': passport.metadata or {},  # Backward compatibility
                # Phase 8B/9A-4: Lock and verification status
                'locked_until': passport.locked_until.isoformat() if passport.locked_until else None,
                'is_locked': is_locked,
                'days_locked': days_left if is_locked else 0,
                'verification_status': getattr(passport, 'verification_status', 'PENDING'),
                'is_verified': passport.is_verified,
                # Phase 9A-4: Visibility
                'visibility': passport.visibility,
                # Phase 9A-28: Cooldown data
                'cooldown': cooldown_data,
            })
        
        return success_response({'passports': passports_list})
    
    except Exception as e:
        logger.error(f"Error listing game passports: {e}", exc_info=True)
        return error_response(
            error_code='SERVER_ERROR',
            message='Failed to retrieve passports',
            exception=e
        )


@login_required
@require_http_methods(["POST"])
def create_game_passport_api(request):
    """
    Create a new game passport.
    
    Route: POST /profile/api/game-passports/create/
    
    Body (JSON):
    {
        "game_id": 1,
        "metadata": {
            "riot_id": "PlayerName#TAG",  // Required for VALORANT
            "region": "NA",               // Required
            "rank": "diamond1",           // Optional
            "role": "duelist"             // Optional
        },
        "visibility": "PUBLIC",  // PUBLIC/PROTECTED/PRIVATE (default: PUBLIC)
        "pinned": false
    }
    
    Phase 9A-7 Section C: Schema-driven validation with 2026-accurate choices
    - All validation enforced by passport_validator service
    - Required fields from GamePlayerIdentityConfig (is_required=True)
    - Select fields validated against 2026-accurate dropdown options
    - Immutable fields protected (riot_id, steam_id, platform, etc.)
    - Regex validation for ID formats
    - Proper error codes: 400 (validation), 409 (duplicate), 404 (not found)
    
    Phase 9A-15 Section A: Comprehensive error handling
    - 400 INVALID_JSON: Malformed JSON in request body
    - 400 INVALID_PAYLOAD: TypeError/KeyError/ValueError during processing
    - 400 FIELD_ERRORS: Django ValidationError with field-level errors
    - 409 DUPLICATE: Passport already exists for this game
    - 403 LOCKED/VERIFIED_LOCK: Passport is locked
    - 500 SERVER_ERROR: Unexpected exceptions only (includes request_id + traceback in DEBUG)
    
    Returns:
        JSON: {success: true, passport: {...}} or {success: false, error: CODE, field_errors: {...}}
    """
    from apps.user_profile.models import GameProfile
    from apps.games.models import Game
    from apps.user_profile.services.passport_validator import (
        validate_passport_payload,
        validate_visibility,
        validate_pinned_count,
        check_duplicate_passport,
        derive_ign_from_metadata,
        derive_discriminator_from_metadata
    )
    from django.conf import settings
    
    # Phase 9A-15: Generate request_id for tracing
    request_id = str(uuid.uuid4())
    
    try:
        # Phase 9A-15: Catch JSON decode errors explicitly
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.warning(f"[GP CREATE] [{request_id}] Invalid JSON: {e}")
            return validation_error_response(
                field_errors={},
                message=f'Invalid JSON in request body: {str(e)}'
            )
        
        # Phase 9A-15: Catch payload normalization errors
        try:
            game_id = data.get('game_id')
            
            # Phase 9A-7: DEBUG logging for troubleshooting
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] User={request.user.username}, "
                    f"GameID={game_id}, PayloadKeys={list(data.keys())}, "
                    f"MetadataKeys={list(data.get('metadata', {}).keys())}, "
                    f"PassportDataKeys={list(data.get('passport_data', {}).keys())}"
                )
            
            # Validate game exists
            if not game_id:
                return validation_error_response(
                    field_errors={'game_id': 'Game ID is required'},
                    message='Game ID is required'
                )
            
            try:
                game = Game.objects.get(id=game_id)
            except Game.DoesNotExist:
                return not_found_error_response('game', game_id)
            
            # Extract metadata (support both 'metadata' and 'passport_data' keys)
            metadata = data.get('metadata', {}) or data.get('passport_data', {})
            if not isinstance(metadata, dict):
                metadata = {}
            
            # Backward compatibility: merge top-level fields into metadata
            if data.get('ign'):
                metadata.setdefault('ign', data['ign'])
            if data.get('region'):
                metadata.setdefault('region', data['region'])
            if data.get('rank'):
                metadata.setdefault('rank', data['rank'])
            if data.get('discriminator'):
                metadata.setdefault('discriminator', data['discriminator'])
                
        except (TypeError, KeyError, ValueError, AttributeError) as e:
            logger.warning(f"[GP CREATE] [{request_id}] Payload error: {e}")
            return validation_error_response(
                field_errors={},
                message=f'Invalid payload structure: {str(e)}'
            )
        
        # Phase 9A-7: DEBUG logging after merging
        if settings.DEBUG:
            logger.info(
                f"[GP CREATE] [{request_id}] Game={game.display_name}, "
                f"MergedMetadataKeys={list(metadata.keys())}, "
                f"MetadataSample={dict(list(metadata.items())[:3])}"
            )
        
        # Phase 9A-7: Check for duplicate first (return 409 CONFLICT)
        is_duplicate, existing_id = check_duplicate_passport(request.user, game)
        if is_duplicate:
            logger.info(f"[GP CREATE] [{request_id}] Duplicate passport detected: {existing_id}")
            return duplicate_error_response(
                message=f'You already have a {game.display_name} passport. Edit it instead.',
                metadata={'existing_passport_id': existing_id}
            )
        
        # Phase 9A-15: Catch Django ValidationError explicitly
        try:
            # Phase 9A-17: Enhanced DEBUG logging for 500 diagnosis
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] Starting validation for {game.display_name}, "
                    f"MetadataKeys={list(metadata.keys())}, MetadataValues={metadata}"
                )
            
            # Phase 9A-7: Schema-driven validation (2026-accurate)
            is_valid, validation_errors = validate_passport_payload(game, metadata, is_update=False)
            if not is_valid:
                if settings.DEBUG:
                    logger.warning(
                        f"[GP CREATE] [{request_id}] Validation failed for {game.display_name}: "
                        f"FieldErrors={validation_errors}"
                    )
                return validation_error_response(
                    field_errors=validation_errors,
                    message=f'{len(validation_errors)} validation error(s)'
                )
            
            # Validate visibility
            visibility = data.get('visibility', 'PUBLIC').upper()
            is_valid_visibility, visibility_error = validate_visibility(visibility)
            if not is_valid_visibility:
                return validation_error_response(
                    field_errors={'visibility': visibility_error},
                    message=visibility_error
                )
            
            # Validate pinned count (max 6)
            pinned = data.get('pinned', False)
            if pinned:
                can_pin, pin_error = validate_pinned_count(request.user)
                if not can_pin:
                    return validation_error_response(
                        field_errors={'pinned': pin_error},
                        message=pin_error
                    )
            
            # Phase 9A-23: Schema-driven identity_key derivation
            from apps.games.models import GamePlayerIdentityConfig
            
            schema_fields = GamePlayerIdentityConfig.objects.filter(
                game=game
            ).order_by('order')
            
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] Deriving identity for {game.display_name}, "
                    f"MetadataKeys={list(metadata.keys())}"
                )
            
            # Derive identity_key from schema (no hardcoded IGN requirement)
            try:
                identity_key, identity_source_field = derive_identity_key(game, metadata, schema_fields)
                
                if settings.DEBUG:
                    logger.info(
                        f"[GP CREATE] [{request_id}] Derived identity_key='{identity_key}' "
                        f"from field '{identity_source_field}'"
                    )
            except DjangoValidationError as e:
                logger.warning(f"[GP CREATE] [{request_id}] Identity derivation failed: {e}")
                if hasattr(e, 'error_dict'):
                    field_errors = {k: str(v[0]) if isinstance(v, list) else str(v) for k, v in e.error_dict.items()}
                else:
                    field_errors = {'__all__': str(e)}
                return validation_error_response(
                    field_errors=field_errors,
                    message='Unable to determine player identity from provided fields'
                )
            
            # Derive display columns (IGN can be optional now)
            ign = derive_ign_from_metadata(metadata) or identity_key  # Use identity_key as fallback
            discriminator = derive_discriminator_from_metadata(metadata)
            region = metadata.get('region', '').strip() or None
            rank = metadata.get('rank', '').strip() or None
            platform = metadata.get('platform', '').strip() or None
            
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] Columns: IGN={ign}, Disc={discriminator}, "
                    f"Region={region}, Rank={rank}, Platform={platform}"
                )
                
        except DjangoValidationError as e:
            logger.warning(f"[GP CREATE] [{request_id}] Django ValidationError: {e}")
            # Extract field errors from Django ValidationError
            if hasattr(e, 'error_dict'):
                field_errors = {k: [str(err) for err in v] for k, v in e.error_dict.items()}
            elif hasattr(e, 'error_list'):
                field_errors = {'__all__': [str(err) for err in e.error_list]}
            else:
                field_errors = {'__all__': [str(e)]}
            return validation_error_response(
                field_errors=field_errors,
                message='Validation error occurred'
            )
        except Exception as inner_e:
            # Phase 9A-17: Catch validation-phase exceptions separately
            logger.error(f"[GP CREATE] [{request_id}] Exception during validation: {inner_e}", exc_info=True)
            error_data = {
                'error_code': 'VALIDATION_EXCEPTION',
                'message': f'Validation error: {str(inner_e)}',
                'request_id': request_id
            }
            if settings.DEBUG:
                error_data['traceback'] = tb.format_exc()
                error_data['phase'] = 'validation'
            return JsonResponse(error_data, status=500)
        
        # Phase 9A-17: Create passport with try-except for DB errors
        try:
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] Creating GameProfile: "
                    f"User={request.user.username}, Game={game.slug}, IGN={ign}, "
                    f"identity_key={identity_key}, Region={region}, Rank={rank}, Platform={platform}, Visibility={visibility}"
                )
            
            # Phase 9A-23: Ensure all required fields have valid values
            in_game_name_value = ign or identity_key or "Unknown"
            game_display_name_value = game.display_name or game.name
            
            passport = GameProfile.objects.create(
                user=request.user,
                game=game,
                game_display_name=game_display_name_value,  # Phase 9A-23: Required field
                ign=ign or "",  # Can be empty for games without traditional IGN
                discriminator=discriminator,
                platform=platform,
                region=region or "",  # Phase 9A-23: Required field (empty string if not provided)
                rank_name=rank or "",
                is_pinned=pinned,
                visibility=visibility,
                metadata=metadata,
                identity_key=identity_key,  # Phase 9A-23: Set identity_key explicitly
                in_game_name=in_game_name_value,  # Phase 9A-23: Required field (never empty)
            )
            
            if settings.DEBUG:
                logger.info(
                    f"[GP CREATE] [{request_id}] SUCCESS PassportID={passport.id}, "
                    f"IGN={ign}, identity_key={identity_key}, in_game_name={in_game_name_value}, Platform={platform}"
                )
        except IntegrityError as ie:
            # Phase 9A-23: Proper error handling with correct error_code
            error_str = str(ie).lower()
            
            if settings.DEBUG:
                logger.warning(
                    f"[GP CREATE] [{request_id}] IntegrityError: {ie}, "
                    f"identity_source='{identity_source_field}', identity_key='{identity_key}'"
                )
            
            # Check constraint type
            if 'unique_game_identity' in error_str or ('identity_key' in error_str and 'unique' in error_str):
                # Global identity uniqueness violated (same identity_key exists for another user)
                field_errors = {
                    identity_source_field: f'This {identity_source_field.replace("_", " ").title()} is already linked to another account'
                }
                
                return JsonResponse({
                    'success': False,
                    'error_code': 'IDENTITY_ALREADY_IN_USE',
                    'message': f'This game identity is already linked to another account.',
                    'field_errors': field_errors,
                    'request_id': request_id
                }, status=409)
            
            elif ('unique' in error_str and 'user' in error_str and 'game' in error_str) or 'unique_together' in error_str:
                # User already has passport for this game (unique_together constraint)
                return JsonResponse({
                    'success': False,
                    'error_code': 'DUPLICATE_GAME_PASSPORT',
                    'message': f'You already have a {game.display_name} passport. Edit it instead.',
                    'field_errors': {},
                    'request_id': request_id
                }, status=409)
            
            elif 'null' in error_str and 'identity_key' in error_str:
                # NULL identity_key (should not happen with derive_identity_key)
                logger.error(f"[GP CREATE] [{request_id}] NULL identity_key - this should not happen!", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Could not determine player identity',
                    'field_errors': {identity_source_field: 'Required field is missing'},
                    'request_id': request_id
                }, status=400)
            
            # Unknown integrity error
            logger.error(f"[GP CREATE] [{request_id}] Unknown IntegrityError: {ie}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': 'An unexpected database error occurred',
                'field_errors': {},
                'request_id': request_id,
                'debug_error': str(ie) if settings.DEBUG else None
            }, status=500)
        except Exception as db_error:
            # Phase 9A-23: Handle other database errors with full details
            logger.error(
                f"[GP CREATE] [{request_id}] Unexpected DB error: {type(db_error).__name__}: {db_error}",
                exc_info=True
            )
            
            # In DEBUG mode, return detailed error information
            if settings.DEBUG:
                error_data = {
                    'error_code': 'SERVER_ERROR',
                    'message': f'Database error: {type(db_error).__name__}: {str(db_error)}',
                    'request_id': request_id,
                    'exception_type': type(db_error).__name__,
                    'exception_message': str(db_error),
                    'traceback': tb.format_exc(),
                    'phase': 'database_create'
                }
            else:
                error_data = {
                    'error_code': 'SERVER_ERROR',
                    'message': 'An unexpected database error occurred',
                    'request_id': request_id
                }
            
            return JsonResponse(error_data, status=500)
        
        return success_response({
            'passport': {
                'id': passport.id,
                'game': {
                    'id': game.id,
                    'name': game.name,
                    'slug': game.slug,
                    'icon': safe_image_url(game.icon),
                },
                'ign': passport.ign,
                'region': passport.region,
                'rank': passport.rank_name,
                'pinned': passport.is_pinned,
                'visibility': passport.visibility,
                'passport_data': passport.metadata or {},
            },
            'message': 'Passport created successfully'
        })
    
    except Exception as e:
        # Phase 9A-15: Only unexpected exceptions reach here
        logger.error(f"[GP CREATE] [{request_id}] Unexpected error: {e}", exc_info=True)
        error_data = {
            'error_code': 'SERVER_ERROR',
            'message': 'An unexpected error occurred',
            'request_id': request_id
        }
        if settings.DEBUG:
            error_data['traceback'] = tb.format_exc()
            error_data['exception_type'] = type(e).__name__
            error_data['exception_message'] = str(e)
        return JsonResponse(error_data, status=500)


@login_required
@require_http_methods(["POST"])
def update_game_passport_api(request):
    """
    Update an existing game passport.
    
    Route: POST /profile/api/game-passports/update/
    
    Body (JSON):
    {
        "id": 123,
        "metadata": {
            "riot_id": "PlayerName#TAG",  // IMMUTABLE - will error if changed
            "region": "EU",               // Can update
            "rank": "platinum2",          // Can update
            "role": "controller"          // Can update
        },
        "visibility": "PROTECTED",  // Can update
        "pinned": true              // Can update
    }
    
    Phase 9A-7 Section C: Schema-driven validation with immutability enforcement
    - All validation enforced by passport_validator service
    - Immutable fields protected (riot_id, steam_id, platform, etc.)
    - Select fields validated against 2026-accurate dropdown options
    - Proper error codes: 400 (validation), 403 (locked), 404 (not found)
    
    Phase 9A-15 Section A: Comprehensive error handling
    - Same error handling as create: JSON decode, payload errors, validation errors
    - 500 only for true unexpected exceptions with request_id + traceback in DEBUG
    
    Returns:
        JSON: {success: true, passport: {...}} or {success: false, error: CODE, field_errors: {...}}
    """
    from apps.user_profile.models import GameProfile
    from apps.user_profile.services.passport_validator import (
        validate_passport_payload,
        validate_visibility,
        validate_pinned_count,
        derive_ign_from_metadata,
        derive_discriminator_from_metadata
    )
    from django.conf import settings
    
    # Phase 9A-15: Generate request_id for tracing
    request_id = str(uuid.uuid4())
    
    try:
        # Phase 9A-15: Catch JSON decode errors explicitly
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.warning(f"[GP UPDATE] [{request_id}] Invalid JSON: {e}")
            return validation_error_response(
                field_errors={},
                message=f'Invalid JSON in request body: {str(e)}'
            )
        
        # Phase 9A-15: Extract and validate passport ID
        passport_id = data.get('id')
        
        if not passport_id:
            return validation_error_response(
                field_errors={'id': 'Passport ID is required'},
                message='Passport ID is required'
            )
        
        # Get passport (must belong to user)
        try:
            passport = GameProfile.objects.select_related('game').get(
                id=passport_id,
                user=request.user
            )
        except GameProfile.DoesNotExist:
            return not_found_error_response(
                resource_type='game passport',
                resource_id=passport_id
            )
        
        # Phase 8B/9A-4: Enforce locks (Fair Play Protocol + Verification)
        is_locked, lock_response = check_passport_locked(passport, request.user)
        if is_locked:
            return lock_response
        
        # Extract metadata
        metadata = passport.metadata.copy() if passport.metadata else {}
        if 'metadata' in data or 'passport_data' in data:
            new_metadata = data.get('metadata', {}) or data.get('passport_data', {})
            if isinstance(new_metadata, dict):
                metadata.update(new_metadata)
        
        # Backward compatibility: merge top-level fields
        if 'ign' in data and data['ign']:
            metadata['ign'] = data['ign']
        if 'region' in data:
            metadata['region'] = data['region']
        if 'rank' in data:
            metadata['rank'] = data['rank']
        if 'discriminator' in data:
            metadata['discriminator'] = data['discriminator']
        
        # Phase 9A-7: Schema-driven validation (including immutability check)
        is_valid, validation_errors = validate_passport_payload(
            passport.game,
            metadata,
            is_update=True,
            existing_passport=passport
        )
        if not is_valid:
            return validation_error_response(
                field_errors=validation_errors,
                message=f'{len(validation_errors)} validation error(s)'
            )
        
        # Validate visibility if provided
        if 'visibility' in data:
            visibility = data['visibility'].upper()
            is_valid_visibility, visibility_error = validate_visibility(visibility)
            if not is_valid_visibility:
                return validation_error_response(
                    field_errors={'visibility': visibility_error},
                    message=visibility_error
                )
            passport.visibility = visibility
        
        # Validate pinned count if changing to pinned
        pinned = data.get('pinned', passport.is_pinned)
        if pinned and not passport.is_pinned:
            can_pin, pin_error = validate_pinned_count(request.user, exclude_passport_id=passport.id)
            if not can_pin:
                return validation_error_response(
                    field_errors={'pinned': pin_error},
                    message=pin_error
                )
        
        # Derive database columns from metadata
        ign = derive_ign_from_metadata(metadata)
        discriminator = derive_discriminator_from_metadata(metadata)
        region = metadata.get('region', '').strip() or None
        rank = metadata.get('rank', '').strip() or None
        
        # Update passport
        if ign:
            passport.ign = ign
        if discriminator:
            passport.discriminator = discriminator
        
        passport.region = region
        passport.rank_name = rank or ""
        passport.is_pinned = pinned
        passport.metadata = metadata
        passport.save()
        
        return success_response({
            'passport': {
                'id': passport.id,
                'game': {
                    'id': passport.game.id,
                    'name': passport.game.name,
                    'slug': passport.game.slug,
                    'icon': safe_image_url(passport.game.icon),
                },
                'ign': passport.ign,
                'region': passport.region,
                'rank': passport.rank_name,
                'pinned': passport.is_pinned,
                'visibility': passport.visibility,
                'passport_data': passport.metadata or {},
            }
        })
    
    except Exception as e:
        # Phase 9A-15: Only unexpected exceptions reach here
        logger.error(f"[GP UPDATE] [{request_id}] Unexpected error: {e}", exc_info=True)
        error_data = {
            'error_code': 'SERVER_ERROR',
            'message': 'An unexpected error occurred',
            'request_id': request_id
        }
        if settings.DEBUG:
            error_data['traceback'] = tb.format_exc()
            error_data['exception_type'] = type(e).__name__
            error_data['exception_message'] = str(e)
        return JsonResponse(error_data, status=500)


@login_required
@require_http_methods(["POST"])
def delete_game_passport_api(request):
    """
    Delete a game passport.
    
    Route: POST /profile/api/game-passports/delete/
    
    Body (JSON):
    {
        "id": 123
    }
    
    Phase 9A-4: Never returns 500 - always structured JSON with proper error codes
    - 400: Bad request (missing ID, invalid JSON)
    - 403: Locked or verified passport
    - 404: Not found
    - 200: Success
    
    Phase 9A-15 Section A: Comprehensive error handling with request_id
    
    Returns:
        JSON: {success: true} or {success: false, error: CODE, message: string}
    """
    from apps.user_profile.models import GameProfile
    from django.conf import settings
    
    # Phase 9A-15: Generate request_id for tracing
    request_id = str(uuid.uuid4())
    
    try:
        # Phase 9A-15: Catch JSON decode errors explicitly
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.warning(f"[GP DELETE] [{request_id}] Invalid JSON: {e}")
            return validation_error_response(
                field_errors={},
                message=f'Invalid JSON in request body: {str(e)}'
            )
        
        # Phase 9A-15: Extract and validate payload
        passport_id = data.get('id')
        
        if not passport_id:
            return validation_error_response(
                field_errors={'id': 'Passport ID is required'},
                message='Passport ID is required'
            )
        
        # Get passport (must belong to user)
        try:
            passport = GameProfile.objects.get(id=passport_id, user=request.user)
        except GameProfile.DoesNotExist:
            return not_found_error_response(
                resource_type='game passport',
                resource_id=passport_id
            )
        
        # Phase 8B/9A-4: Enforce locks (Fair Play Protocol + Verification)
        is_locked, lock_response = check_passport_locked(passport, request.user)
        if is_locked:
            return lock_response
        
        # Delete passport
        passport.delete()
        logger.info(f"[GP DELETE] [{request_id}] SUCCESS PassportID={passport_id}")
        
        return success_response({'message': 'Passport deleted successfully'})
    
    except Exception as e:
        # Phase 9A-15: Only unexpected exceptions reach here
        logger.error(f"[GP DELETE] [{request_id}] Unexpected error: {e}", exc_info=True)
        error_data = {
            'error_code': 'SERVER_ERROR',
            'message': 'An unexpected error occurred',
            'request_id': request_id
        }
        if settings.DEBUG:
            error_data['traceback'] = tb.format_exc()
            error_data['exception_type'] = type(e).__name__
            error_data['exception_message'] = str(e)
        return JsonResponse(error_data, status=500)


@login_required
@require_http_methods(["POST"])
def check_identity_availability_api(request):
    """
    Phase 9A-22: Check if game identity is available (not already claimed).
    
    Route: POST /profile/api/game-passports/check-identity/
    
    Body (JSON):
    {
        "game_id": 1,
        "metadata": {
            "konami_id": "test123",
            "user_id": "ASHT-111-222-333",
            ...
        }
    }
    
    Returns:
        200: {available: true} or {available: false, field_errors: {...}}
        400: Validation error
        404: Game not found
    """
    from apps.user_profile.models import GameProfile
    from apps.games.models import Game, GamePlayerIdentityConfig
    
    request_id = str(uuid.uuid4())
    
    try:
        data = json.loads(request.body)
        game_id = data.get('game_id')
        metadata = data.get('metadata', {})
        
        if not game_id:
            return JsonResponse({
                'success': False,
                'error_code': 'INVALID_PAYLOAD',
                'message': 'game_id is required'
            }, status=400)
        
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return not_found_error_response('game', game_id)
        
        # Build identity_key from metadata (same logic as save)
        # Get required immutable fields from schema
        identity_parts = []
        configs = GamePlayerIdentityConfig.objects.filter(
            game=game,
            is_required=True,
            is_immutable=True
        ).order_by('order')
        
        for config in configs:
            value = metadata.get(config.field_name, '').strip()
            if value:
                identity_parts.append(value.lower())
        
        if not identity_parts:
            return JsonResponse({
                'success': False,
                'available': True,
                'message': 'No identity fields provided'
            }, status=200)
        
        identity_key = ':'.join(identity_parts)
        
        # Check if identity_key already exists for this game (excluding current user)
        existing = GameProfile.objects.filter(
            game=game,
            identity_key=identity_key
        ).exclude(user=request.user).first()
        
        if existing:
            # Identity is taken
            field_errors = {}
            for config in configs:
                field_name = config.field_name
                if metadata.get(field_name):
                    field_errors[field_name] = f'This {config.display_name} is already linked to another account'
            
            return JsonResponse({
                'success': True,
                'available': False,
                'field_errors': field_errors,
                'message': 'This game identity is already linked to another account'
            }, status=200)
        
        # Available
        return JsonResponse({
            'success': True,
            'available': True
        }, status=200)
        
    except json.JSONDecodeError as e:
        return validation_error_response(
            field_errors={},
            message=f'Invalid JSON: {str(e)}'
        )
    except Exception as e:
        logger.error(f"[GP CHECK ID] [{request_id}] Error: {e}", exc_info=True)
        return JsonResponse({
            'error_code': 'SERVER_ERROR',
            'message': 'An unexpected error occurred',
            'request_id': request_id
        }, status=500)
