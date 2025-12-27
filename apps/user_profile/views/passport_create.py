"""
Passport Creation API
Handles creating new game passports with structured identity.
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def create_passport(request):
    """
    Create a new game passport.
    
    Route: POST /api/passports/create/
    
    Body (JSON):
    {
        "game_id": 1,
        "ign": "PlayerName",
        "discriminator": "#NA1",  // optional
        "platform": "PC"  // optional
    }
    
    Returns:
        JSON: {success: true, passport: {...}}
    """
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.games.models import Game
    
    try:
        data = json.loads(request.body)
        game_id = data.get('game_id')
        ign = data.get('ign', '').strip()
        discriminator = data.get('discriminator', '').strip() or None
        platform = data.get('platform', '').strip() or None
        metadata = data.get('metadata', {})
        
        # Validate required fields
        if not game_id:
            return JsonResponse({'success': False, 'error': 'game_id is required'}, status=400)
        
        if not ign:
            return JsonResponse({'success': False, 'error': 'ign is required'}, status=400)
        
        # Get game
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid game'}, status=400)
        
        # Check if passport already exists for this game
        from apps.user_profile.models import GameProfile
        existing = GameProfile.objects.filter(user=request.user, game=game).first()
        if existing:
            return JsonResponse({
                'success': False,
                'error': f'You already have a passport for {game.name}'
            }, status=400)
        
        # Create passport using service
        try:
            passport = GamePassportService.create_or_update_passport(
                user=request.user,
                game=game,
                ign=ign,
                discriminator=discriminator,
                platform=platform,
                visibility='PUBLIC',  # Default to public
                metadata=metadata if isinstance(metadata, dict) else {}
            )
            
            # Log audit event
            from apps.user_profile.services.audit_service import AuditService
            AuditService.log_event(
                user=request.user,
                event_type='passport.created',
                after_state={
                    'game': game.name,
                    'ign': ign,
                    'discriminator': discriminator,
                    'platform': platform
                },
                request_meta={
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                }
            )
            
            return JsonResponse({
                'success': True,
                'passport': {
                    'id': passport.id,
                    'game': game.name,
                    'game_display': passport.game_display_name,
                    'ign': passport.ign,
                    'discriminator': passport.discriminator,
                    'platform': passport.platform,
                    'in_game_name': passport.in_game_name,
                    'visibility': passport.visibility,
                    'is_pinned': passport.is_pinned,
                    'is_lft': passport.is_lft,
                },
                'message': f'Passport created for {game.name}'
            })
        
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error creating passport: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'Failed to create passport'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in create_passport: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
