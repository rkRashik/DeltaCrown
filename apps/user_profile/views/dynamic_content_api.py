"""
Dynamic Content API Endpoints
Phase 14B: Eliminate hardcoded dropdown content

Provides JSON endpoints for:
- Available games list
- Social platform choices
- Privacy preset choices
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models_main import SocialLink, PrivacySettings
from apps.user_profile.models.game_passport_schema import GamePassportSchema
from django.conf import settings

import logging

logger = logging.getLogger(__name__)


def safe_image_url(field):
    """Safely extract URL from ImageField, handling None and missing files."""
    try:
        if not field:
            return None
        return getattr(field, 'url', None)
    except Exception:
        return None


@require_http_methods(["GET"])
@ensure_csrf_cookie
def get_available_games(request):
    """
    GET /api/games/
    Returns list of all available games for game passport creation with dynamic schemas.
    
    Phase 8A: Backend-Driven Schema Architecture
    Phase 9A-14: Added schema_version for frontend caching
    
    Returns per-game field configurations from GamePlayerIdentityConfig.
    
    Response:
    {
        "schema_version": "2026-01-05T14:32:15",  # Phase 9A-14: Cache key
        "games": [
            {
                "id": 1,
                "slug": "valorant",
                "display_name": "VALORANT",
                "icon_url": "...",
                "primary_color": "#ff4655",
                "passport_schema": [
                    {
                        "key": "riot_id",
                        "label": "Riot ID",
                        "type": "text",
                        "required": true,
                        "immutable": false,
                        "placeholder": "PlayerName#1234",
                        "help_text": "Your full Riot ID including tag"
                    }
                ],
                "rules": {
                    "lock_days": 30,
                    "one_passport": true,
                    "region_restricted": false
                }
            }
        ]
    }
    """
    try:
        # Phase 9A-14: Calculate schema version from latest updated timestamp
        # Version changes when any GamePlayerIdentityConfig or GamePassportSchema changes
        from django.db.models import Max
        
        config_updated = GamePlayerIdentityConfig.objects.aggregate(Max('updated_at'))['updated_at__max']
        schema_updated = GamePassportSchema.objects.aggregate(Max('updated_at'))['updated_at__max']
        
        # Use the most recent timestamp between configs and schemas
        if config_updated and schema_updated:
            schema_version_timestamp = max(config_updated, schema_updated)
        elif config_updated:
            schema_version_timestamp = config_updated
        elif schema_updated:
            schema_version_timestamp = schema_updated
        else:
            # No schemas exist yet, use fixed version
            from django.utils import timezone
            schema_version_timestamp = timezone.now()
        
        # Format as ISO 8601 string for cache key
        schema_version = schema_version_timestamp.isoformat()
        
        # Phase 9A-9: Use EXPLICIT query to avoid relationship issues
        # Get all active games without prefetch (we'll query configs explicitly)
        games = Game.objects.filter(is_active=True).order_by('display_name')
        
        games_data = []
        for game in games:
            # Phase 9A-6 FIX: Explicit query to avoid empty prefetch issues
            identity_configs = GamePlayerIdentityConfig.objects.filter(
                game=game
            ).order_by('order', 'id')
            
            # DEBUG diagnostics
            config_count = identity_configs.count()
            if settings.DEBUG and config_count == 0:
                logger.warning(
                    f"⚠️  Game '{game.display_name}' (slug={game.slug}) has ZERO identity configs. "
                    f"Run: python manage.py seed_identity_configs --game {game.slug}"
                )
            
            # Get GamePassportSchema for select field options (Phase 9A-7: all 8 choice types)
            try:
                game_schema = GamePassportSchema.objects.get(game=game)
                region_options = game_schema.region_choices or []
                rank_options = game_schema.rank_choices or []
                role_options = game_schema.role_choices or []
                platform_options = game_schema.platform_choices or []
                server_options = game_schema.server_choices or []
                mode_options = game_schema.mode_choices or []
                premier_rating_options = game_schema.premier_rating_choices or []
                division_options = game_schema.division_choices or []
            except GamePassportSchema.DoesNotExist:
                region_options = []
                rank_options = []
                role_options = []
                platform_options = []
                server_options = []
                mode_options = []
                premier_rating_options = []
                division_options = []
            
            # Serialize passport schema from GamePlayerIdentityConfig
            passport_schema = []
            
            for config in identity_configs:
                field_data = {
                    'key': config.field_name,
                    'label': config.display_name,
                    'type': config.field_type.lower() if config.field_type else 'text',
                    'required': config.is_required,
                    'immutable': config.is_immutable,
                    'placeholder': config.placeholder or '',
                    'help_text': config.help_text or '',
                    'validation_regex': config.validation_regex or '',
                    'min_length': config.min_length,
                    'max_length': config.max_length
                }
                
                # Phase 9A-7: Add options for select fields from GamePassportSchema
                if config.field_type and config.field_type.lower() == 'select':
                    # Map field name to appropriate options (2026 schema with 8 choice types)
                    if 'region' in config.field_name.lower():
                        field_data['options'] = region_options
                    elif 'rank' in config.field_name.lower():
                        field_data['options'] = rank_options
                    elif 'role' in config.field_name.lower():
                        field_data['options'] = role_options
                    elif 'platform' in config.field_name.lower():
                        field_data['options'] = platform_options
                    elif 'server' in config.field_name.lower():
                        field_data['options'] = server_options
                    elif 'mode' in config.field_name.lower():
                        field_data['options'] = mode_options
                    elif 'premier' in config.field_name.lower():
                        field_data['options'] = premier_rating_options
                    elif 'division' in config.field_name.lower():
                        field_data['options'] = division_options
                    else:
                        field_data['options'] = []
                
                passport_schema.append(field_data)
            
            # Backward compatibility: If no schema exists, provide basic fallback
            if not passport_schema:
                # PHASE 9A-6: Only warn, don't create fake schema
                logger.warning(
                    f"No passport_schema found for game: {game.display_name} (slug={game.slug}). "
                    f"Run: python manage.py seed_identity_configs --game {game.slug}"
                )
                passport_schema = [
                    {
                        'key': 'ign',
                        'label': 'In-Game Name',
                        'type': 'text',
                        'required': True,
                        'immutable': False,
                        'placeholder': '',
                        'help_text': '',
                        'validation_regex': '',
                        'min_length': None,
                        'max_length': None
                    },
                    {
                        'key': 'region',
                        'label': 'Region',
                        'type': 'text',
                        'required': False,
                        'immutable': False,
                        'placeholder': '',
                        'help_text': '',
                        'validation_regex': '',
                        'min_length': None,
                        'max_length': None
                    },
                    {
                        'key': 'rank_name',
                        'label': 'Rank',
                        'type': 'text',
                        'required': False,
                        'immutable': False,
                        'placeholder': '',
                        'help_text': '',
                        'validation_regex': '',
                        'min_length': None,
                        'max_length': None
                    }
                ]
            
            game_data = {
                'id': game.id,
                'slug': game.slug,
                'name': game.name,  # Backward compatibility (Phase 7B)
                'display_name': game.display_name,  # Phase 8A standard
                'icon_url': safe_image_url(game.icon),
                'primary_color': game.primary_color or '#7c3aed',
                'passport_schema': passport_schema,
                'rules': {
                    'lock_days': 30,  # Fair Play Protocol: 30-day ID lock
                    'one_passport': True,  # One passport per game per user
                    'region_restricted': game.has_servers  # Regional restrictions if game has servers
                }
            }
            
            # Phase 9A-6: DEBUG diagnostics
            if settings.DEBUG:
                game_data['_debug_identity_config_count'] = config_count
            
            games_data.append(game_data)
        
        return JsonResponse({
            'success': True,
            'schema_version': schema_version,  # Phase 9A-14: Cache invalidation key
            'games': games_data
        })
        
    except Exception as e:
        error_msg = f"Failed to fetch games list: {e.__class__.__name__}: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Phase 9A-9: Enhanced error response for debugging
        response_data = {
            'success': False,
            'error': 'Failed to load games'
        }
        
        # Include exception details in DEBUG mode
        if settings.DEBUG:
            import traceback
            response_data['error_detail'] = str(e)
            response_data['error_type'] = e.__class__.__name__
            response_data['traceback'] = traceback.format_exc()
        
        return JsonResponse(response_data, status=500)


@require_http_methods(["GET"])
@ensure_csrf_cookie
def get_social_platforms(request):
    """
    GET /api/social-links/platforms/
    Returns list of all supported social platforms
    
    Response:
    {
        "platforms": [
            {"value": "twitter", "label": "Twitter / X", "icon": "𝕏", "placeholder": "username"},
            {"value": "twitch", "label": "Twitch", "icon": "", "placeholder": "channel_name"}
        ]
    }
    """
    try:
        # Get platform choices from model
        platforms = SocialLink.PLATFORM_CHOICES
        
        # Platform metadata
        platform_meta = {
            'twitter': {'icon': '𝕏', 'placeholder': 'username', 'prefix': 'https://twitter.com/'},
            'twitch': {'icon': '', 'placeholder': 'channel_name', 'prefix': 'https://twitch.tv/'},
            'youtube': {'icon': '', 'placeholder': 'channel_id', 'prefix': 'https://youtube.com/'},
            'discord': {'icon': '', 'placeholder': 'username#0000', 'prefix': ''},
            'facebook': {'icon': '', 'placeholder': 'username', 'prefix': 'https://facebook.com/'},
            'instagram': {'icon': '', 'placeholder': 'username', 'prefix': 'https://instagram.com/'},
            'tiktok': {'icon': '', 'placeholder': '@username', 'prefix': 'https://tiktok.com/@'},
            'reddit': {'icon': '', 'placeholder': 'u/username', 'prefix': 'https://reddit.com/'},
            'steam': {'icon': '', 'placeholder': 'steam_id', 'prefix': 'https://steamcommunity.com/id/'},
            'github': {'icon': '', 'placeholder': 'username', 'prefix': 'https://github.com/'},
        }
        
        platforms_data = [
            {
                'value': value,
                'label': label,
                'icon': platform_meta.get(value, {}).get('icon', ''),
                'placeholder': platform_meta.get(value, {}).get('placeholder', 'username'),
                'prefix': platform_meta.get(value, {}).get('prefix', '')
            }
            for value, label in platforms
        ]
        
        return JsonResponse({
            'success': True,
            'platforms': platforms_data
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch social platforms: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load platforms'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_privacy_presets(request):
    """
    GET /api/privacy/presets/
    Returns available privacy preset options
    
    Response:
    {
        "presets": [
            {
                "value": "public",
                "label": "Public",
                "description": "Everyone can see your profile",
                "icon": "👁️"
            },
            ...
        ]
    }
    """
    try:
        presets = [
            {
                'value': 'public',
                'label': 'Public',
                'description': 'Everyone can see your full profile',
                'icon': '👁️',
                'settings': {
                    'show_email': False,
                    'show_phone': False,
                    'show_real_name': False,
                    'show_country': True,
                    'show_social_links': True,
                    'show_game_ids': True,
                    'show_match_history': True,
                    'show_teams': True,
                    'show_achievements': True,
                    'allow_friend_requests': True,
                    'allow_team_invites': True,
                    'allow_direct_messages': True
                }
            },
            {
                'value': 'protected',
                'label': 'Protected',
                'description': 'Only followers can see some details',
                'icon': '🔒',
                'settings': {
                    'show_email': False,
                    'show_phone': False,
                    'show_real_name': False,
                    'show_country': True,
                    'show_social_links': True,
                    'show_game_ids': True,
                    'show_match_history': False,  # Followers only
                    'show_teams': True,
                    'show_achievements': True,
                    'allow_friend_requests': True,
                    'allow_team_invites': True,
                    'allow_direct_messages': False  # Followers only
                }
            },
            {
                'value': 'private',
                'label': 'Private',
                'description': 'Minimal profile visibility',
                'icon': '🔐',
                'settings': {
                    'show_email': False,
                    'show_phone': False,
                    'show_real_name': False,
                    'show_country': False,
                    'show_social_links': False,
                    'show_game_ids': False,
                    'show_match_history': False,
                    'show_teams': False,
                    'show_achievements': False,
                    'allow_friend_requests': False,
                    'allow_team_invites': True,
                    'allow_direct_messages': False
                }
            }
        ]
        
        return JsonResponse({
            'success': True,
            'presets': presets
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch privacy presets: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load privacy presets'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_visibility_options(request):
    """
    GET /api/privacy/visibility-options/
    Returns available visibility options for game passports/content
    
    Response:
    {
        "options": [
            {"value": "public", "label": "Public", "icon": "🌍"},
            {"value": "followers", "label": "Followers Only", "icon": "👥"},
            {"value": "private", "label": "Private", "icon": "🔒"}
        ]
    }
    """
    try:
        options = [
            {
                'value': 'public',
                'label': 'Public',
                'description': 'Visible to everyone',
                'icon': '🌍'
            },
            {
                'value': 'followers',
                'label': 'Followers Only',
                'description': 'Only your followers can see this',
                'icon': '👥'
            },
            {
                'value': 'private',
                'label': 'Private',
                'description': 'Only you can see this',
                'icon': '🔒'
            }
        ]
        
        return JsonResponse({
            'success': True,
            'options': options
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch visibility options: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load visibility options'
        }, status=500)


@require_http_methods(["GET"])
def get_game_metadata(request, game_id):
    """
    GET /api/games/<game_id>/metadata/
    Returns game-specific metadata (regions, ranks) for dynamic admin forms
    
    Phase 15 Session 2: Dynamic admin forms (NO hardcoded lists)
    
    Response:
    {
        "success": true,
        "game": {"id": 1, "name": "VALORANT", "slug": "valorant"},
        "regions": [
            {"value": "na", "label": "North America"},
            {"value": "eu", "label": "Europe"}
        ],
        "ranks": [
            {"value": "iron", "label": "Iron"},
            {"value": "bronze", "label": "Bronze"}
        ],
        "schema": {
            "ign_label": "Riot ID",
            "discriminator_visible": true,
            "discriminator_label": "Tagline",
            "platform_visible": false,
            "region_required": true
        }
    }
    """
    try:
        from apps.games.models import Game
        from apps.user_profile.models import GamePassportSchema
        
        # Get game
        try:
            game = Game.objects.get(pk=game_id, is_active=True)
        except Game.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Game not found'
            }, status=404)
        
        # Get schema
        try:
            schema = GamePassportSchema.objects.get(game=game)
        except GamePassportSchema.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'No passport schema found for {game.name}'
            }, status=404)
        
        # Extract regions from schema
        regions = []
        if schema.region_choices:
            for choice in schema.region_choices:
                regions.append({
                    'value': choice.get('value', ''),
                    'label': choice.get('label', choice.get('value', ''))
                })
        
        # Extract ranks from schema
        ranks = []
        if schema.rank_choices:
            for choice in schema.rank_choices:
                ranks.append({
                    'value': choice.get('value', ''),
                    'label': choice.get('label', choice.get('value', ''))
                })
        
        # Extract field configuration for UI
        identity_fields = schema.identity_fields or {}
        schema_config = {
            'ign_label': 'IGN / Username',
            'ign_required': True,
            'discriminator_visible': False,
            'discriminator_label': 'Discriminator',
            'discriminator_required': False,
            'platform_visible': schema.platform_specific or False,
            'platform_label': 'Platform',
            'platform_required': False,
            'region_required': schema.region_required or False
        }
        
        # Customize labels based on identity fields
        if 'riot_name' in identity_fields:
            schema_config['ign_label'] = 'Riot ID'
            schema_config['ign_required'] = identity_fields['riot_name'].get('required', True)
        if 'tagline' in identity_fields:
            schema_config['discriminator_visible'] = True
            schema_config['discriminator_label'] = 'Tagline'
            schema_config['discriminator_required'] = identity_fields['tagline'].get('required', True)
        if 'steam_id64' in identity_fields:
            schema_config['ign_label'] = 'Steam ID64'
        if 'numeric_id' in identity_fields:
            schema_config['ign_label'] = 'Player ID'
        if 'zone_id' in identity_fields:
            schema_config['discriminator_visible'] = True
            schema_config['discriminator_label'] = 'Zone ID'
        
        return JsonResponse({
            'success': True,
            'game': {
                'id': game.id,
                'name': game.name,
                'slug': game.slug
            },
            'regions': regions,
            'ranks': ranks,
            'schema': schema_config
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch game metadata for game_id={game_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load game metadata'
        }, status=500)
