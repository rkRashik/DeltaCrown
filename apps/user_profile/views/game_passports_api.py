"""
UP-PHASE15-SESSION3: Game Passports API
CRUD operations for GameProfile/GamePassport model.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
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


@login_required
@require_http_methods(["GET"])
def list_game_passports_api(request):
    """
    List all game passports for current user.
    
    Route: GET /profile/api/game-passports/
    
    Returns:
        JSON: {success: true, passports: [{...}, ...]}
    """
    from apps.user_profile.models import GameProfile
    
    try:
        passports = GameProfile.objects.filter(
            user=request.user
        ).select_related('game').order_by('-is_pinned', 'game__name')
        
        passports_list = []
        for passport in passports:
            passports_list.append({
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
                'passport_data': passport.metadata or {},
            })
        
        return JsonResponse({
            'success': True,
            'passports': passports_list
        })
    
    except Exception as e:
        logger.error(f"Error listing game passports: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def create_game_passport_api(request):
    """
    Create a new game passport.
    
    Route: POST /profile/api/game-passports/create/
    
    Body (JSON):
    {
        "game_id": 1,
        "ign": "PlayerName",
        "region": "NA",
        "rank": "Diamond",
        "pinned": false,
        "passport_data": {...}  // Additional game-specific fields
    }
    
    Returns:
        JSON: {success: true, passport: {...}}
    """
    from apps.user_profile.models import GameProfile
    from apps.games.models import Game
    
    try:
        data = json.loads(request.body)
        game_id = data.get('game_id')
        ign = data.get('ign', '').strip()
        region = data.get('region', '').strip() or None
        rank = data.get('rank', '').strip() or None
        pinned = data.get('pinned', False)
        metadata = data.get('passport_data', {}) or data.get('metadata', {})
        
        # Validation
        if not game_id or not ign:
            return JsonResponse({
                'success': False,
                'error': 'Game ID and IGN are required'
            }, status=400)
        
        # Validate game exists
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Game not found'
            }, status=404)
        
        # Check if user already has passport for this game
        existing = GameProfile.objects.filter(user=request.user, game=game).first()
        if existing:
            return JsonResponse({
                'success': False,
                'error': f'You already have a passport for {game.name}. Please edit it instead.'
            }, status=400)
        
        # Validate pinned count (max 6)
        if pinned:
            pinned_count = GameProfile.objects.filter(user=request.user, is_pinned=True).count()
            if pinned_count >= 6:
                return JsonResponse({
                    'success': False,
                    'error': 'You can only pin up to 6 game passports'
                }, status=400)
        
        # Create passport
        passport = GameProfile.objects.create(
            user=request.user,
            game=game,
            ign=ign,
            region=region,
            rank_name=rank or "",
            is_pinned=pinned,
            metadata=metadata,
        )
        
        return JsonResponse({
            'success': True,
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
                'passport_data': passport.metadata or {},
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating game passport: {e}", exc_info=True)
        # Include actual error in response during development
        import traceback
        error_detail = str(e) if not hasattr(e, 'messages') else ', '.join(e.messages)
        return JsonResponse({
            'success': False,
            'error': 'Server error',
            'detail': error_detail,
            'trace': traceback.format_exc()[:500]
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_game_passport_api(request):
    """
    Update an existing game passport.
    
    Route: POST /profile/api/game-passports/update/
    
    Body (JSON):
    {
        "id": 123,
        "ign": "NewPlayerName",
        "region": "EU",
        "rank": "Master",
        "pinned": true,
        "passport_data": {...}
    }
    
    Returns:
        JSON: {success: true, passport: {...}}
    """
    from apps.user_profile.models import GameProfile
    
    try:
        data = json.loads(request.body)
        passport_id = data.get('id')
        
        if not passport_id:
            return JsonResponse({
                'success': False,
                'error': 'Passport ID is required'
            }, status=400)
        
        # Get passport (must belong to user)
        try:
            passport = GameProfile.objects.select_related('game').get(
                id=passport_id,
                user=request.user
            )
        except GameProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Game passport not found or access denied'
            }, status=404)
        
        # Update fields
        ign = data.get('ign', '').strip()
        region = data.get('region', '').strip() or None
        rank = data.get('rank', '').strip() or None
        pinned = data.get('pinned', passport.is_pinned)
        metadata = data.get('passport_data', passport.metadata) or data.get('metadata', passport.metadata)
        
        if ign:
            passport.ign = ign
        
        passport.region = region
        passport.rank_name = rank or ""
        passport.metadata = metadata
        
        # Validate pinned count
        if pinned and not passport.is_pinned:
            pinned_count = GameProfile.objects.filter(user=request.user, is_pinned=True).count()
            if pinned_count >= 6:
                return JsonResponse({
                    'success': False,
                    'error': 'You can only pin up to 6 game passports'
                }, status=400)
        
        passport.is_pinned = pinned
        passport.save()
        
        return JsonResponse({
            'success': True,
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
                'passport_data': passport.metadata or {},
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating game passport: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


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
    
    Returns:
        JSON: {success: true}
    """
    from apps.user_profile.models import GameProfile
    
    try:
        data = json.loads(request.body)
        passport_id = data.get('id')
        
        if not passport_id:
            return JsonResponse({
                'success': False,
                'error': 'Passport ID is required'
            }, status=400)
        
        # Get and delete passport (must belong to user)
        try:
            passport = GameProfile.objects.get(id=passport_id, user=request.user)
            passport.delete()
        except GameProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Game passport not found or access denied'
            }, status=404)
        
        return JsonResponse({'success': True})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error deleting game passport: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
