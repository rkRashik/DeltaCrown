"""
Guest-to-Real Team Conversion Views (P4-T04)

Provides:
- Organizer invite-link generation endpoint
- Member claim page (conversion UI)
- Organizer partial conversion approval
- Status polling endpoint for AJAX
"""
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_GET

from apps.tournaments.models import Registration
from apps.tournaments.services.guest_conversion_service import GuestConversionService

logger = logging.getLogger(__name__)


@login_required
@require_POST
def generate_invite_link(request, registration_id):
    """
    Organizer generates an invite link for a guest team registration.
    Returns JSON with invite_token.
    """
    try:
        result = GuestConversionService.generate_invite_link(
            registration_id=registration_id,
            organizer=request.user,
        )
        return JsonResponse({
            'success': True,
            'invite_token': result['invite_token'],
            'invite_url': request.build_absolute_uri(
                f"/tournaments/{result['tournament_slug']}/join/{result['invite_token']}/"
            ),
        })
    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found.'}, status=404)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e.message)}, status=400)
    except Exception as e:
        logger.error("Error generating invite link: %s", e, exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error.'}, status=500)


@login_required
def conversion_page(request, invite_token):
    """
    Conversion page where invited members can claim their slots.
    GET: Render the conversion UI with roster status.
    POST: Claim a slot with game_id.
    """
    if request.method == 'POST':
        game_id = request.POST.get('game_id', '').strip()
        if not game_id:
            return JsonResponse({'success': False, 'error': 'Game ID is required.'}, status=400)

        try:
            result = GuestConversionService.claim_slot(
                invite_token=invite_token,
                user=request.user,
                game_id=game_id,
            )
            return JsonResponse(result)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e.message)}, status=400)
        except Exception as e:
            logger.error("Error claiming slot: %s", e, exc_info=True)
            return JsonResponse({'success': False, 'error': 'Server error.'}, status=500)

    # GET — render the conversion page
    try:
        status = GuestConversionService.get_conversion_status(invite_token)
    except ValidationError:
        return render(request, 'tournaments/registration/guest_conversion.html', {
            'error': 'Invalid or expired invite link.',
        }, status=404)

    return render(request, 'tournaments/registration/guest_conversion.html', {
        'status': status,
        'invite_token': invite_token,
        'user': request.user,
    })


@login_required
@require_POST
def approve_partial(request, registration_id):
    """
    Organizer approves a partial guest team conversion.
    """
    try:
        result = GuestConversionService.approve_partial_conversion(
            registration_id=registration_id,
            organizer=request.user,
        )
        return JsonResponse(result)
    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found.'}, status=404)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e.message)}, status=400)
    except Exception as e:
        logger.error("Error approving partial conversion: %s", e, exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error.'}, status=500)


@require_GET
def conversion_status_api(request, invite_token):
    """
    Polling endpoint: returns current conversion status as JSON.
    No auth required — read-only public status by token.
    """
    try:
        status = GuestConversionService.get_conversion_status(invite_token)
        return JsonResponse(status)
    except ValidationError:
        return JsonResponse({'error': 'Invalid invite link.'}, status=404)
