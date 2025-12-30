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

from apps.games.models import Game
from apps.user_profile.models_main import SocialLink, PrivacySettings

import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@ensure_csrf_cookie
def get_available_games(request):
    """
    GET /api/games/
    Returns list of all available games for game passport creation
    
    Response:
    {
        "games": [
            {"id": 1, "name": "VALORANT", "slug": "valorant", "icon_url": "..."},
            {"id": 2, "name": "CS2", "slug": "cs2", "icon_url": "..."}
        ]
    }
    """
    try:
        games = Game.objects.filter(is_active=True).order_by('name')
        
        games_data = [
            {
                'id': game.id,
                'name': game.name,
                'slug': game.slug,
                'short_name': getattr(game, 'short_name', game.name),
                'icon_url': game.icon.url if hasattr(game, 'icon') and game.icon else None,
                'color': getattr(game, 'brand_color', '#6366f1')
            }
            for game in games
        ]
        
        return JsonResponse({
            'success': True,
            'games': games_data
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch games list: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load games'
        }, status=500)


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
