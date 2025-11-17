"""
Game ID Management API
======================
RESTful API endpoints for checking and saving user game IDs.
Used by modern team join flow.

Version: 1.0
Date: 2025-01-19
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json

from apps.user_profile.models import UserProfile


def _get_profile(user):
    """Get or create user profile."""
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'display_name': user.get_full_name() or user.username
        }
    )
    return profile


@login_required
@require_http_methods(["GET"])
def check_game_id_api(request, game_code: str):
    """
    Check if user has game ID for specified game.
    
    GET /api/profile/check-game-id/<game_code>/
    
    Response:
        {
            "has_game_id": true/false,
            "game_code": "valorant",
            "game_name": "Valorant"
        }
    """
    profile = _get_profile(request.user)
    
    # Game name mapping
    game_names = {
        'valorant': 'Valorant',
        'csgo': 'CS:GO',
        'cs2': 'Counter-Strike 2',
        'pubg': 'PUBG',
        'apex': 'Apex Legends',
        'lol': 'League of Legends',
        'dota2': 'Dota 2',
        'ow2': 'Overwatch 2',
        'r6': 'Rainbow Six Siege'
    }
    
    game_id = profile.get_game_id(game_code)
    
    return JsonResponse({
        'has_game_id': bool(game_id),
        'game_code': game_code,
        'game_name': game_names.get(game_code, game_code.upper())
    })


@login_required
@require_http_methods(["POST"])
@ensure_csrf_cookie
def save_game_id_api(request, game_code: str):
    """
    Save user's game ID for specified game.
    
    POST /api/profile/save-game-id/<game_code>/
    Body: {
        "riot_id": "PlayerName#1234"  // for Valorant
        "steam_id": "76561198..."      // for CS:GO/CS2
        "pubg_id": "PlayerName"        // for PUBG
        ...
    }
    
    Response:
        {
            "success": true,
            "message": "Game ID saved successfully"
        }
    """
    profile = _get_profile(request.user)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    # Game-specific field mapping
    game_id_fields = {
        'valorant': 'riot_id',
        'csgo': 'steam_id',
        'cs2': 'steam_id',
        'pubg': 'pubg_id',
        'apex': 'origin_id',
        'lol': 'summoner_name',
        'dota2': 'steam_id',
        'ow2': 'battle_net',
        'r6': 'uplay_username'
    }
    
    field_name = game_id_fields.get(game_code)
    if not field_name:
        return JsonResponse({
            'success': False,
            'error': f'Unsupported game: {game_code}'
        }, status=400)
    
    game_id_value = data.get(field_name)
    if not game_id_value:
        return JsonResponse({
            'success': False,
            'error': f'Missing required field: {field_name}'
        }, status=400)
    
    # Validation for specific formats
    if game_code == 'valorant':
        # Validate Riot ID format (Name#Tag)
        if '#' not in game_id_value:
            return JsonResponse({
                'success': False,
                'error': 'Riot ID must be in format: Name#Tag'
            }, status=400)
    
    # Save to profile
    try:
        # Use set_game_id method if available
        if hasattr(profile, 'set_game_id'):
            profile.set_game_id(game_code, game_id_value)
        else:
            # Fallback: set field directly
            setattr(profile, field_name, game_id_value)
            profile.save(update_fields=[field_name])
        
        return JsonResponse({
            'success': True,
            'message': 'Game ID saved successfully',
            'game_id': game_id_value
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to save game ID: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_all_game_ids_api(request):
    """
    Get all game IDs for current user.
    
    GET /api/profile/game-ids/
    
    Response:
        {
            "game_ids": {
                "valorant": "PlayerName#1234",
                "csgo": "76561198...",
                "pubg": null
            }
        }
    """
    profile = _get_profile(request.user)
    
    game_codes = ['valorant', 'csgo', 'cs2', 'pubg', 'apex', 'lol', 'dota2', 'ow2', 'r6']
    
    game_ids = {}
    for code in game_codes:
        game_id = profile.get_game_id(code)
        game_ids[code] = game_id if game_id else None
    
    return JsonResponse({
        'game_ids': game_ids
    })


@login_required
@require_http_methods(["DELETE"])
def delete_game_id_api(request, game_code: str):
    """
    Delete user's game ID for specified game.
    
    DELETE /api/profile/delete-game-id/<game_code>/
    
    Response:
        {
            "success": true,
            "message": "Game ID deleted successfully"
        }
    """
    profile = _get_profile(request.user)
    
    game_id_fields = {
        'valorant': 'riot_id',
        'csgo': 'steam_id',
        'cs2': 'steam_id',
        'pubg': 'pubg_id',
        'apex': 'origin_id',
        'lol': 'summoner_name',
        'dota2': 'steam_id',
        'ow2': 'battle_net',
        'r6': 'uplay_username'
    }
    
    field_name = game_id_fields.get(game_code)
    if not field_name:
        return JsonResponse({
            'success': False,
            'error': f'Unsupported game: {game_code}'
        }, status=400)
    
    try:
        setattr(profile, field_name, None)
        profile.save(update_fields=[field_name])
        
        return JsonResponse({
            'success': True,
            'message': 'Game ID deleted successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete game ID: {str(e)}'
        }, status=500)
