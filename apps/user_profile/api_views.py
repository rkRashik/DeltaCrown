"""
API views for user profile game ID management
"""
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import UserProfile

logger = logging.getLogger(__name__)

# Game code to field name mapping
GAME_FIELD_MAP = {
    'valorant': 'riot_id',
    'efootball': 'efootball_id',
    'dota2': 'steam_id',
    'cs2': 'steam_id',
    'csgo': 'steam_id',
    'mlbb': 'mlbb_id',
    'pubg': 'pubg_mobile_id',
    'pubgm': 'pubg_mobile_id',
    'pubg_mobile': 'pubg_mobile_id',
    'freefire': 'free_fire_id',
    'free_fire': 'free_fire_id',
    'fc24': 'ea_id',
    'codm': 'codm_uid',
}


@login_required
@require_http_methods(["GET"])
def get_game_id(request):
    """
    Check if user has a game ID for the specified game
    
    GET /api/profile/get-game-id/?game=valorant
    Returns: {"has_game_id": true/false, "game_id": "value" (if exists)}
    """
    try:
        game_code = request.GET.get('game', '').lower()
        
        if not game_code:
            return JsonResponse({
                'success': False,
                'error': 'Game code is required'
            }, status=400)
        
        if game_code not in GAME_FIELD_MAP:
            return JsonResponse({
                'success': False,
                'error': f'Invalid game code: {game_code}'
            }, status=400)
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            # Profile doesn't exist - no game ID
            return JsonResponse({
                'success': True,
                'has_game_id': False
            })
        
        # Get the field name for this game
        field_name = GAME_FIELD_MAP[game_code]
        game_id_value = getattr(profile, field_name, '')
        
        # For MLBB, also check server ID
        if game_code == 'mlbb':
            mlbb_server_id = getattr(profile, 'mlbb_server_id', '')
            has_game_id = bool(game_id_value and mlbb_server_id)
            
            return JsonResponse({
                'success': True,
                'has_game_id': has_game_id,
                'game_ids': {
                    'mlbb_id': game_id_value if has_game_id else '',
                    'mlbb_server_id': mlbb_server_id if has_game_id else ''
                }
            })
        else:
            has_game_id = bool(game_id_value)
            
            return JsonResponse({
                'success': True,
                'has_game_id': has_game_id,
                'game_ids': {
                    field_name: game_id_value if has_game_id else ''
                }
            })
    
    except Exception as e:
        logger.error(f"Error checking game ID: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while checking game ID'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_game_id(request):
    """
    Update user's game ID for a specific game
    
    POST /api/profile/update-game-id/
    Body: {
        "game": "valorant",
        "riot_id": "Professor#TAG"
    }
    OR for MLBB:
    {
        "game": "mlbb",
        "mlbb_id": "123456789",
        "mlbb_server_id": "1234"
    }
    
    Returns: {"success": true, "message": "Game ID saved"}
    """
    try:
        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        
        game_code = data.get('game', '').lower()
        
        if not game_code:
            return JsonResponse({
                'success': False,
                'error': 'Game code is required'
            }, status=400)
        
        if game_code not in GAME_FIELD_MAP:
            return JsonResponse({
                'success': False,
                'error': f'Invalid game code: {game_code}'
            }, status=400)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Check if game_ids object is provided (new format)
        game_ids = data.get('game_ids', {})
        
        if game_ids:
            # New format: {"game": "valorant", "game_ids": {"riot_id": "value"}}
            for field_name, field_value in game_ids.items():
                if field_value and hasattr(profile, field_name):
                    setattr(profile, field_name, field_value.strip())
                    logger.info(f"User {request.user.username} updated {field_name}: {field_value}")
        else:
            # Old format: {"game": "valorant", "riot_id": "value"}
            field_name = GAME_FIELD_MAP[game_code]
            game_id_value = data.get(field_name, '').strip()
            
            if not game_id_value:
                return JsonResponse({
                    'success': False,
                    'error': f'{field_name} is required'
                }, status=400)
            
            setattr(profile, field_name, game_id_value)
            
            # For MLBB, also save server ID
            if game_code == 'mlbb':
                mlbb_server_id = data.get('mlbb_server_id', '').strip()
                if not mlbb_server_id:
                    return JsonResponse({
                        'success': False,
                        'error': 'Server ID is required for Mobile Legends'
                    }, status=400)
                profile.mlbb_server_id = mlbb_server_id
            
            logger.info(f"User {request.user.username} updated {field_name}: {game_id_value}")
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Game ID saved successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating game ID: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while saving game ID'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def profile_api(request, profile_id):
    """
    Get user profile data for modal display
    
    GET /api/profile/<profile_id>/
    Returns profile data for the player modal
    """
    try:
        # Get the requested profile
        try:
            profile = UserProfile.objects.get(id=profile_id)
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Profile not found'
            }, status=404)
        
        # Basic profile data
        profile_data = {
            'id': profile.id,
            'username': profile.user.username,
            'display_name': profile.display_name or profile.user.username,
            'avatar_url': profile.avatar.url if profile.avatar else None,
            'bio': profile.bio or '',
            'is_captain': False,  # This will be overridden by roster data
            'role': 'Player',  # This will be overridden by roster data
            'player_role': '',  # This will be overridden by roster data
            'game_id': '',  # This will be overridden by roster data
            'game_id_label': 'IGN',  # This will be overridden by roster data
            'mlbb_server_id': '',  # This will be overridden by roster data
            'social_links': {
                'twitter': profile.twitter or None,
                'discord_id': profile.discord_id or None,
                'youtube_link': profile.youtube_link or None,
                'twitch_link': profile.twitch_link or None,
                'instagram': profile.instagram or None,
            }
        }
        
        return JsonResponse({
            'success': True,
            'profile': profile_data
        })
    
    except Exception as e:
        logger.error(f"Error fetching profile {profile_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while fetching profile'
        }, status=500)
