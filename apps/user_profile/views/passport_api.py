"""
Game Passport Frontend API Endpoints (GP-FE-MVP-01)

Mutation endpoints for passport management:
- toggle_lft: Toggle looking-for-team status
- set_visibility: Change privacy level
- pin_passport: Pin/unpin passport
- reorder_passports: Change pinned order

All use GamePassportService (NO JSON writes)
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError, PermissionDenied
import logging
import json

from apps.user_profile.services.game_passport_service import GamePassportService
from apps.user_profile.models import GameProfile

logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def toggle_lft(request):
    """Toggle LFT status for a passport"""
    try:
        data = json.loads(request.body)
        game = data.get('game')
        
        if not game:
            return JsonResponse({'success': False, 'error': 'Game required'}, status=400)
        
        # Get current passport to determine new LFT value
        try:
            passport = GameProfile.objects.get(user=request.user, game=game)
            new_lft = not passport.is_lft
        except GameProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Passport not found'}, status=404)
        
        # Use set_lft service method
        passport = GamePassportService.set_lft(
            user=request.user,
            game=game,
            is_lft=new_lft,
            actor_user_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'is_lft': passport.is_lft,
            'game': passport.game,
            'message': f"{'Activated' if passport.is_lft else 'Deactivated'} Looking for Team"
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error toggling LFT for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def set_visibility(request):
    """Set visibility for a passport"""
    try:
        data = json.loads(request.body)
        game = data.get('game')
        visibility = data.get('visibility')
        
        if not game or not visibility:
            return JsonResponse({'success': False, 'error': 'Game and visibility required'}, status=400)
        
        # Validate visibility choice
        valid_choices = [choice[0] for choice in GameProfile.VISIBILITY_CHOICES]
        if visibility not in valid_choices:
            return JsonResponse({'success': False, 'error': f'Invalid visibility. Must be one of: {", ".join(valid_choices)}'}, status=400)
        
        # Set via service
        passport = GamePassportService.set_visibility(
            user=request.user,
            game=game,
            visibility=visibility,
            actor_user_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'visibility': passport.visibility,
            'game': passport.game,
            'message': f"Privacy set to {passport.get_visibility_display()}"
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error setting visibility for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def pin_passport(request):
    """Pin or unpin a passport"""
    try:
        data = json.loads(request.body)
        game = data.get('game')
        should_pin = data.get('pin', True)
        
        if not game:
            return JsonResponse({'success': False, 'error': 'Game required'}, status=400)
        
        # Pin/unpin via service
        if should_pin:
            passport = GamePassportService.pin_passport(
                user=request.user,
                game=game,
                actor_user_id=request.user.id
            )
        else:
            passport = GamePassportService.unpin_passport(
                user=request.user,
                game=game,
                actor_user_id=request.user.id
            )
        
        return JsonResponse({
            'success': True,
            'is_pinned': passport.is_pinned,
            'pinned_order': passport.pinned_order,
            'game': passport.game.slug if passport.game else None,
            'message': f"{'Pinned' if passport.is_pinned else 'Unpinned'} {passport.game_display_name}"
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error pinning passport for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def reorder_passports(request):
    """Reorder pinned passports"""
    try:
        data = json.loads(request.body)
        game_order = data.get('game_order', [])
        
        if not game_order or not isinstance(game_order, list):
            return JsonResponse({'success': False, 'error': 'game_order array required'}, status=400)
        
        # Reorder via service
        passports = GamePassportService.reorder_pinned_passports(
            user=request.user,
            game_order=game_order,
            actor_user_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'game_order': [p.game for p in passports],
            'message': f"Reordered {len(passports)} passports"
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error reordering passports for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["DELETE", "POST"])
def delete_passport(request, passport_id):
    """Delete a game passport with validation"""
    try:
        # Get the passport
        try:
            passport = GameProfile.objects.select_related('game').get(id=passport_id, user=request.user)
        except GameProfile.DoesNotExist:
            logger.error(f"Passport {passport_id} not found for user {request.user.id}")
            return JsonResponse({'success': False, 'error': 'Passport not found'}, status=404)
        
        # Get game name and slug
        game_name = passport.game.display_name
        game_slug = passport.game.slug
        
        logger.info(f"Attempting to delete passport {passport_id} for user {request.user.id}, game: {game_slug}")
        
        # Check if user is in an active team using this game
        from apps.organizations.models import TeamMembership
        active_team = TeamMembership.objects.filter(
            user=request.user,
            team__game_id=passport.game_id,
            status=TeamMembership.Status.ACTIVE
        ).select_related('team').first()
        
        if active_team:
            logger.info(f"Cannot delete passport {passport_id} - user in active team: {active_team.team.name}")
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete {game_name} passport while in team "{active_team.team.name}". Leave the team first.'
            }, status=400)
        
        # Capture snapshot BEFORE deletion
        before_snapshot = {
            'game': game_name,
            'ign': passport.ign,
            'discriminator': passport.discriminator,
            'platform': passport.platform,
            'region': passport.region,
        }
        
        # Delete via service (includes audit logging)
        logger.info(f"Calling GamePassportService.delete_passport for user {request.user.username}, game {game_slug}")
        deleted = GamePassportService.delete_passport(
            user=request.user,
            game=game_slug,
            actor_user_id=request.user.id
        )
        
        if not deleted:
            logger.error(f"GamePassportService.delete_passport returned False for passport {passport_id}")
            return JsonResponse({'success': False, 'error': 'Failed to delete passport'}, status=500)
        
        # Additional audit event (using captured snapshot)
        from apps.user_profile.services.audit import AuditService
        
        AuditService.record_event(
            subject_user_id=request.user.id,
            actor_user_id=request.user.id,
            event_type='game_passport.deleted',
            source_app='user_profile',
            object_type='GameProfile',
            object_id=passport_id,
            before_snapshot=before_snapshot,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        logger.info(f"Successfully deleted passport {passport_id} for user {request.user.id}")
        return JsonResponse({
            'success': True,
            'message': f'{game_name} passport deleted successfully'
        }, status=200)
        
    except ValidationError as e:
        logger.error(f"ValidationError deleting passport {passport_id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error deleting passport {passport_id} for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)
