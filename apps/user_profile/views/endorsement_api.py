"""
UP-PHASE2E PART 2: Bounty Endorsement API

Extends the existing tournament endorsement system to support 1v1 bounty matches.
Key differences from tournament endorsements:
- For bounties: Endorse OPPONENT (not teammate)
- For bounties: Only after COMPLETED status
- For bounties: Both participants can endorse each other

Skills available (matching existing SkillType):
- Sharp Aim (aim)
- Tactical Genius (shotcalling)
- Fair Play (support) 
- Clutch Performer (clutch)
- Team Leader (igl)
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction

from apps.user_profile.models import Bounty, BountyStatus
from apps.user_profile.models.endorsements import SkillEndorsement, SkillType
from apps.user_profile.services import bounty_service

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def award_bounty_endorsement(request, bounty_id):
    """
    Award skill endorsement to bounty opponent after completion.
    
    POST /api/bounties/<id>/endorse/
    
    Body (JSON):
    {
        "skill": "aim",  // aim, shotcalling, clutch, support, igl, entry_fragging
        "receiver_id": 123  // Optional: opponent user ID (auto-detected if omitted)
    }
    
    Rules:
    - Bounty must be COMPLETED
    - Only participants (creator/acceptor) can endorse
    - Cannot endorse yourself
    - One endorsement per bounty per participant
    - Can only endorse opponent (not self)
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        403: {"error": "Permission denied"}
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
    
    # Extract skill
    skill = data.get("skill", "").strip().lower()
    if not skill:
        return JsonResponse({"error": "Skill is required"}, status=400)
    
    # Validate skill
    valid_skills = [choice[0] for choice in SkillType.choices]
    if skill not in valid_skills:
        return JsonResponse({
            "error": f"Invalid skill. Must be one of: {', '.join(valid_skills)}"
        }, status=400)
    
    # Permission checks
    endorser = request.user
    
    # Check if bounty is completed
    if bounty.status != BountyStatus.COMPLETED:
        return JsonResponse({
            "error": f"Cannot endorse: bounty is {bounty.status}. Only completed bounties can be endorsed."
        }, status=400)
    
    # Check if user is participant
    if endorser not in [bounty.creator, bounty.acceptor]:
        return JsonResponse({
            "error": "Only bounty participants can award endorsements"
        }, status=403)
    
    # Determine opponent (receiver)
    receiver_id = data.get("receiver_id")
    if receiver_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            receiver = User.objects.get(pk=receiver_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Receiver not found"}, status=400)
    else:
        # Auto-detect opponent
        receiver = bounty.acceptor if endorser == bounty.creator else bounty.creator
    
    # Prevent self-endorsement
    if endorser.id == receiver.id:
        return JsonResponse({"error": "Cannot endorse yourself"}, status=400)
    
    # Verify receiver is opponent
    if receiver not in [bounty.creator, bounty.acceptor]:
        return JsonResponse({
            "error": f"{receiver.username} was not a participant in this bounty"
        }, status=400)
    
    try:
        with transaction.atomic():
            # Check for duplicate endorsement
            existing = SkillEndorsement.objects.filter(
                bounty=bounty,
                endorser=endorser
            ).first()
            
            if existing:
                return JsonResponse({
                    "error": f"You already endorsed {existing.receiver.username} for this bounty"
                }, status=400)
            
            # Create endorsement (bounty-specific, no match)
            endorsement = SkillEndorsement.objects.create(
                bounty=bounty,
                match=None,  # Bounty endorsements don't link to tournament matches
                endorser=endorser,
                receiver=receiver,
                skill_name=skill,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            return JsonResponse({
                "success": True,
                "message": f"Endorsed {receiver.username} for {skill.replace('_', ' ').title()}!",
                "endorsement_id": endorsement.id,
                "receiver": receiver.username,
                "skill": skill,
            })
    
    except Exception as e:
        # Check for unique constraint violation
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return JsonResponse({
                "error": "You already endorsed your opponent for this bounty"
            }, status=400)
        
        logger.error(f"Endorsement creation error: {e}", exc_info=True)
        return JsonResponse({
            "error": "An error occurred while creating endorsement"
        }, status=500)
