# apps/user_profile/views/bounty_api.py
"""
Bounty API Endpoints - Interactive Owner Flows (Phase 2D + 2E)

Endpoints:
- POST /api/bounties/create/ - Create new bounty with escrow lock
- POST /api/bounties/<id>/accept/ - Accept open bounty
- POST /api/bounties/<id>/start/ - Start match (ACCEPTED → IN_PROGRESS)
- POST /api/bounties/<id>/submit-proof/ - Submit proof (IN_PROGRESS → PENDING_RESULT)
- POST /api/bounties/<id>/confirm-result/ - Confirm winner (COMPLETED + escrow release)
- POST /api/bounties/<id>/dispute/ - Raise dispute (DISPUTED + freeze escrow)
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
import json

from apps.user_profile.services import bounty_service
from apps.core.models import Game
from apps.user_profile.models import Bounty, BountyStatus


@login_required
@require_http_methods(["POST"])
def create_bounty(request):
    """
    Create new bounty with wallet escrow lock.
    
    POST /api/bounties/create/
    
    Body (JSON):
    {
        "title": "1v1 Aim Duel",
        "game_id": 1,
        "description": "First to 100k in Gridshot wins",
        "stake_amount": 500,
        "expires_in_hours": 72,
        "mode": "1v1"  # Optional
    }
    
    Returns:
        200: {"success": true, "bounty_id": 123, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Insufficient balance"}
    """
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Extract fields
    title = data.get("title", "").strip()
    game_id = data.get("game_id")
    description = data.get("description", "").strip()
    stake_amount = data.get("stake_amount")
    expires_in_hours = data.get("expires_in_hours", 72)
    mode = data.get("mode", "1v1")
    
    # Validate required fields
    if not title:
        return JsonResponse({"error": "Title is required"}, status=400)
    
    if not game_id:
        return JsonResponse({"error": "Game is required"}, status=400)
    
    if not stake_amount:
        return JsonResponse({"error": "Stake amount is required"}, status=400)
    
    # Validate stake amount
    try:
        stake_amount = int(stake_amount)
        if stake_amount < 100:
            return JsonResponse({"error": "Minimum stake is 100 DC"}, status=400)
        if stake_amount > 50000:
            return JsonResponse({"error": "Maximum stake is 50,000 DC"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid stake amount"}, status=400)
    
    # Validate game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status=400)
    
    # Validate expiry
    try:
        expires_in_hours = int(expires_in_hours)
        if expires_in_hours < 24:
            return JsonResponse({"error": "Minimum expiry is 24 hours"}, status=400)
        if expires_in_hours > 168:  # 1 week
            return JsonResponse({"error": "Maximum expiry is 168 hours (1 week)"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid expiry duration"}, status=400)
    
    # Create bounty via service
    try:
        bounty = bounty_service.create_bounty(
            creator=request.user,
            title=title,
            game=game,
            stake_amount=stake_amount,
            description=description,
            expires_in_hours=expires_in_hours,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        
        return JsonResponse({
            "success": True,
            "bounty_id": bounty.id,
            "message": f"Bounty created! {stake_amount} DC locked in escrow.",
            "stake_amount": stake_amount,
            "expires_at": bounty.expires_at.isoformat() if bounty.expires_at else None,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bounty creation error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while creating bounty"}, status=500)


@login_required
@require_http_methods(["POST"])
def accept_bounty(request, bounty_id):
    """
    Accept an open bounty.
    
    POST /api/bounties/<id>/accept/
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Cannot accept your own bounty"}
        404: {"error": "Bounty not found"}
    """
    
    # Validate bounty exists
    try:
        bounty = Bounty.objects.get(pk=bounty_id)
    except Bounty.DoesNotExist:
        return JsonResponse({"error": "Bounty not found"}, status=404)
    
    # Accept bounty via service
    try:
        acceptance = bounty_service.accept_bounty(
            bounty_id=bounty_id,
            acceptor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        
        return JsonResponse({
            "success": True,
            "message": f"Bounty accepted! Challenge {bounty.creator.username} to win {bounty.stake_amount} DC.",
            "bounty_id": bounty.id,
            "creator": bounty.creator.username,
            "stake_amount": bounty.stake_amount,
            "accepted_at": acceptance.accepted_at.isoformat(),
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bounty acceptance error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while accepting bounty"}, status=500)


# ============================================================================
# UP-PHASE2E: MATCH PROGRESSION ENDPOINTS
# ============================================================================

@login_required
@require_http_methods(["POST"])
def start_match(request, bounty_id):
    """
    Start match (ACCEPTED → IN_PROGRESS).
    
    POST /api/bounties/<id>/start/
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Only participants can start match"}
        404: {"error": "Bounty not found"}
    """
    
    try:
        bounty = Bounty.objects.get(pk=bounty_id)
    except Bounty.DoesNotExist:
        return JsonResponse({"error": "Bounty not found"}, status=404)
    
    try:
        bounty = bounty_service.start_match(
            bounty_id=bounty_id,
            started_by=request.user
        )
        
        return JsonResponse({
            "success": True,
            "message": "Match started! Good luck!",
            "bounty_id": bounty.id,
            "status": bounty.status,
            "started_at": bounty.started_at.isoformat() if bounty.started_at else None,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Match start error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while starting match"}, status=500)


@login_required
@require_http_methods(["POST"])
def submit_proof(request, bounty_id):
    """
    Submit match result with proof (IN_PROGRESS → PENDING_RESULT).
    
    POST /api/bounties/<id>/submit-proof/
    
    Body (JSON):
    {
        "claimed_winner_id": 123,
        "proof_url": "https://imgur.com/screenshot.png",
        "proof_type": "screenshot",  // screenshot, video, replay
        "description": "Final scoreboard showing 13-5 victory"
    }
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Only participants can submit results"}
        404: {"error": "Bounty not found"}
    """
    
    try:
        bounty = Bounty.objects.get(pk=bounty_id)
    except Bounty.DoesNotExist:
        return JsonResponse({"error": "Bounty not found"}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Extract fields
    claimed_winner_id = data.get("claimed_winner_id")
    proof_url = data.get("proof_url", "").strip()
    proof_type = data.get("proof_type", "screenshot")
    description = data.get("description", "").strip()
    
    # Validate required fields
    if not claimed_winner_id:
        return JsonResponse({"error": "Winner is required"}, status=400)
    
    if not proof_url:
        return JsonResponse({"error": "Proof URL is required"}, status=400)
    
    # Get winner user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        claimed_winner = User.objects.get(pk=claimed_winner_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Winner not found"}, status=400)
    
    try:
        proof = bounty_service.submit_result(
            bounty_id=bounty_id,
            submitted_by=request.user,
            claimed_winner=claimed_winner,
            proof_url=proof_url,
            proof_type=proof_type,
            description=description,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        return JsonResponse({
            "success": True,
            "message": "Result submitted! 24-hour dispute window started.",
            "bounty_id": bounty.id,
            "proof_id": proof.id,
            "claimed_winner": claimed_winner.username,
            "status": "PENDING_RESULT",
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Proof submission error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while submitting proof"}, status=500)


@login_required
@require_http_methods(["POST"])
def confirm_result(request, bounty_id):
    """
    Confirm match result and release escrow (PENDING_RESULT → COMPLETED).
    
    POST /api/bounties/<id>/confirm-result/
    
    Returns:
        200: {"success": true, "message": "...", "payout": 475}
        400: {"error": "..."}
        403: {"error": "..."}
        404: {"error": "Bounty not found"}
    """
    
    try:
        bounty = Bounty.objects.get(pk=bounty_id)
    except Bounty.DoesNotExist:
        return JsonResponse({"error": "Bounty not found"}, status=404)
    
    try:
        # Complete bounty (auto-confirm after dispute window)
        bounty = bounty_service.complete_bounty(bounty_id=bounty_id)
        
        return JsonResponse({
            "success": True,
            "message": f"Match confirmed! {bounty.winner.username} won {bounty.payout_amount} DC.",
            "bounty_id": bounty.id,
            "winner": bounty.winner.username,
            "payout": bounty.payout_amount,
            "platform_fee": bounty.platform_fee,
            "completed_at": bounty.completed_at.isoformat() if bounty.completed_at else None,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Result confirmation error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while confirming result"}, status=500)


@login_required
@require_http_methods(["POST"])
def raise_dispute(request, bounty_id):
    """
    Raise dispute contesting submitted result (PENDING_RESULT → DISPUTED).
    
    POST /api/bounties/<id>/dispute/
    
    Body (JSON):
    {
        "reason": "The screenshot is doctored. I have proof of the real score..."
    }
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Only participants can dispute"}
        404: {"error": "Bounty not found"}
    """
    
    try:
        bounty = Bounty.objects.get(pk=bounty_id)
    except Bounty.DoesNotExist:
        return JsonResponse({"error": "Bounty not found"}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Extract reason
    reason = data.get("reason", "").strip()
    
    # Validate reason
    if not reason:
        return JsonResponse({"error": "Dispute reason is required"}, status=400)
    
    if len(reason) < 50:
        return JsonResponse({"error": "Dispute reason must be at least 50 characters"}, status=400)
    
    try:
        dispute = bounty_service.raise_dispute(
            bounty_id=bounty_id,
            disputer=request.user,
            reason=reason,
        )
        
        return JsonResponse({
            "success": True,
            "message": "Dispute raised. A moderator will review your case.",
            "bounty_id": bounty.id,
            "dispute_id": dispute.id,
            "status": "DISPUTED",
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Dispute creation error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while raising dispute"}, status=500)
