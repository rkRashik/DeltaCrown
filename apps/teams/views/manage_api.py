"""
Team Manage HQ — API Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Clean JSON APIs powering the team management console (/teams/<slug>/manage/).
Uses the organizations Team model (the source of truth for all teams).
All endpoints require authentication + team admin permission (OWNER or MANAGER).

Endpoints:
  GET  api/<slug>/manage/overview/       → Dashboard stats + pending items
  POST api/<slug>/manage/profile/        → Update team profile fields
  POST api/<slug>/manage/media/          → Upload logo / banner
  POST api/<slug>/manage/settings/       → Toggle team settings
  POST api/<slug>/manage/invite/         → Send member invite (inline)
  GET  api/<slug>/manage/join-requests/  → Pending join requests
  POST api/<slug>/manage/join-requests/<id>/handle/  → Approve / reject
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.organizations.models import Team
from apps.organizations.models.membership import TeamMembership
from apps.organizations.models.team_invite import TeamInvite
from apps.organizations.models.activity import TeamActivityLog
from apps.organizations.models.membership_event import TeamMembershipEvent
from apps.organizations.choices import (
    MembershipRole, MembershipStatus, MembershipEventType, RosterSlot,
    ActivityActionType,
)
from apps.notifications.services import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_admin_context(request, slug):
    """
    Resolve team + membership, verify admin permission.
    Returns (team, membership, error_response).
    """
    team = get_object_or_404(Team.objects.select_related('organization', 'created_by'), slug=slug)
    user = request.user

    membership = TeamMembership.objects.filter(
        team=team, user=user, status=MembershipStatus.ACTIVE,
    ).first()

    # Allow team creator even without membership row
    is_admin = (
        user.is_superuser
        or team.created_by == user
        or (membership and membership.role in (MembershipRole.OWNER, MembershipRole.MANAGER))
    )
    if not is_admin:
        return None, None, JsonResponse(
            {"success": False, "error": "Insufficient permissions."}, status=403
        )
    return team, membership, None


def _parse_body(request):
    """Parse JSON body or fall back to POST dict."""
    if request.content_type and "json" in request.content_type:
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return {}
    return request.POST


def _bool_val(v) -> bool:
    """Coerce a form/JSON value to bool."""
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "1", "on", "yes")


# ---------------------------------------------------------------------------
# 1. Overview / Dashboard
# ---------------------------------------------------------------------------

@login_required
@require_GET
def manage_overview(request, slug):
    """Return dashboard stats and pending counts."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    members_qs = team.vnext_memberships.filter(status=MembershipStatus.ACTIVE)
    pending_invites_qs = team.vnext_invites.filter(status="PENDING")

    return JsonResponse({
        "success": True,
        "stats": {
            "members_count": members_qs.count(),
            "pending_invites": pending_invites_qs.count(),
            "join_requests": 0,
            "tournaments_active": 0,
        },
        "team": {
            "name": team.name,
            "tag": team.tag,
            "game_id": team.game_id,
            "status": team.status,
            "visibility": team.visibility,
            "created_at": team.created_at.isoformat() if team.created_at else None,
        },
    })


# ---------------------------------------------------------------------------
# 2. Profile Update (name, tag, tagline, description, region, socials)
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_update_profile(request, slug):
    """Update team profile text fields and social links."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    data = _parse_body(request)
    updated = []

    # --- Text fields ---
    _TEXT_MAP = {
        "name": ("name", 100),
        "tag": ("tag", 5),
        "tagline": ("tagline", 100),
        "description": ("description", 2000),
        "region": ("region", 50),
    }
    for key, (field, max_len) in _TEXT_MAP.items():
        if key in data and data[key]:
            val = str(data[key]).strip()[:max_len]
            if key == "tag":
                val = val.upper()
            setattr(team, field, val)
            updated.append(field)

    # --- Social links (org model uses _url suffix) ---
    _SOCIAL_MAP = {
        "twitter": "twitter_url",
        "instagram": "instagram_url",
        "youtube": "youtube_url",
        "twitch": "twitch_url",
    }
    for key, field in _SOCIAL_MAP.items():
        if key in data:
            setattr(team, field, str(data[key]).strip())
            updated.append(field)

    if updated:
        team.save(update_fields=updated + ['updated_at'])
        logger.info(
            "[AUDIT] Team profile updated: team=%s fields=%s by=%s",
            team.slug, updated, request.user.username,
        )
        # Audit trail
        try:
            TeamActivityLog.objects.create(
                team=team,
                action_type=ActivityActionType.UPDATE,
                actor_id=request.user.pk,
                actor_username=request.user.username,
                description=f"Profile updated: {', '.join(updated)}",
                metadata={"fields": updated},
            )
        except Exception:
            logger.exception("Failed to write profile activity log")

    return JsonResponse({"success": True, "message": "Profile updated.", "updated_fields": updated})


# ---------------------------------------------------------------------------
# 3. Media Upload (logo / banner / roster_image)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def manage_upload_media(request, slug):
    """Upload team logo or banner."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    media_type = request.POST.get("type", "logo")
    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"success": False, "error": "No file provided."}, status=400)

    ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")
    if not uploaded.name.lower().endswith(ALLOWED_EXT):
        return JsonResponse(
            {"success": False, "error": "Invalid file format. Use PNG, JPG, GIF, or WebP."},
            status=400,
        )

    MAX_MB = {"logo": 5, "banner": 10}
    limit = MAX_MB.get(media_type, 5)
    if uploaded.size > limit * 1024 * 1024:
        return JsonResponse(
            {"success": False, "error": f"File too large. Maximum {limit} MB."},
            status=400,
        )

    # Org model uses "banner" not "banner_image"
    FIELD_MAP = {"logo": "logo", "banner": "banner"}
    field_name = FIELD_MAP.get(media_type)
    if not field_name or not hasattr(team, field_name):
        return JsonResponse({"success": False, "error": "Invalid media type."}, status=400)

    field = getattr(team, field_name)
    field.save(uploaded.name, uploaded, save=True)

    logger.info(
        "[AUDIT] Team media uploaded: team=%s type=%s by=%s",
        team.slug, media_type, request.user.username,
    )
    # Audit trail
    try:
        TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.UPDATE,
            actor_id=request.user.pk,
            actor_username=request.user.username,
            description=f"{media_type.replace('_', ' ').title()} updated",
            metadata={"media_type": media_type, "filename": uploaded.name},
        )
    except Exception:
        logger.exception("Failed to write media activity log")
    return JsonResponse({
        "success": True,
        "message": f"{media_type.replace('_', ' ').title()} updated.",
        "url": getattr(team, field_name).url if getattr(team, field_name) else None,
    })


# ---------------------------------------------------------------------------
# 4. Settings Toggle (booleans + hero_template)
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_update_settings(request, slug):
    """Toggle team settings (only fields that exist on organizations.Team)."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    data = _parse_body(request)
    is_owner = (membership and membership.role == MembershipRole.OWNER) or request.user.is_superuser
    updated = []

    # Visibility (org model uses a CharField, not boolean)
    if "visibility" in data:
        val = str(data["visibility"]).strip().upper()
        if val in ("PUBLIC", "PRIVATE", "UNLISTED"):
            team.visibility = val
            updated.append("visibility")

    # Status (owner only)
    if "status" in data and is_owner:
        val = str(data["status"]).strip().upper()
        if val in ("ACTIVE", "SUSPENDED", "DISBANDED"):
            team.status = val
            updated.append("status")

    # Guard: only save fields that actually exist on the model
    _BOOL_SETTINGS = [
        "is_temporary",
    ]
    for field in _BOOL_SETTINGS:
        if field in data and hasattr(team, field):
            setattr(team, field, _bool_val(data[field]))
            updated.append(field)

    if updated:
        team.save(update_fields=updated + ['updated_at'])
        logger.info(
            "[AUDIT] Team settings updated: team=%s fields=%s by=%s",
            team.slug, updated, request.user.username,
        )
        # Audit trail
        try:
            TeamActivityLog.objects.create(
                team=team,
                action_type=ActivityActionType.UPDATE,
                actor_id=request.user.pk,
                actor_username=request.user.username,
                description=f"Settings changed: {', '.join(updated)}",
                metadata={"fields": updated},
            )
        except Exception:
            logger.exception("Failed to write settings activity log")

    return JsonResponse({"success": True, "message": "Settings saved.", "updated_fields": updated})


# ---------------------------------------------------------------------------
# 5. Invite Member (inline from manage page)
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_invite_member(request, slug):
    """Send an invitation to a user from the manage console."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    # Permission: OWNER or MANAGER (superusers and team creators bypass)
    if not (request.user.is_superuser or team.created_by == request.user) and (
        not membership or membership.role not in (MembershipRole.OWNER, MembershipRole.MANAGER)
    ):
        return JsonResponse({"success": False, "error": "Not allowed to invite."}, status=403)

    data = _parse_body(request)
    query = str(data.get("username_or_email", "")).strip()
    role = str(data.get("role", MembershipRole.PLAYER)).strip().upper()

    if not query:
        return JsonResponse({"success": False, "error": "Username or email is required."}, status=400)

    # Resolve target user (organizations model FK → User directly)
    from django.contrib.auth import get_user_model
    User = get_user_model()

    target_user = None
    try:
        target_user = User.objects.get(username__iexact=query)
    except User.DoesNotExist:
        try:
            target_user = User.objects.get(email__iexact=query)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found."}, status=404)

    # Guards
    if TeamMembership.objects.filter(team=team, user=target_user, status=MembershipStatus.ACTIVE).exists():
        return JsonResponse({"success": False, "error": "User is already a team member."}, status=400)

    if TeamInvite.objects.filter(team=team, invited_user=target_user, status="PENDING").exists():
        return JsonResponse({"success": False, "error": "User already has a pending invite."}, status=400)

    # Validate role
    valid_roles = {c[0] for c in MembershipRole.choices}
    if role not in valid_roles:
        role = MembershipRole.PLAYER

    invite = TeamInvite.objects.create(
        team=team,
        inviter=request.user,
        invited_user=target_user,
        role=role,
        status="PENDING",
        expires_at=timezone.now() + timedelta(days=7),
    )

    # Best-effort avatar
    avatar_url = None
    if hasattr(target_user, "profile") and hasattr(target_user.profile, "avatar") and target_user.profile.avatar:
        avatar_url = target_user.profile.avatar.url

    logger.info(
        "[AUDIT] Manage invite sent: team=%s invited=%s by=%s",
        team.slug, target_user.username, request.user.username,
    )
    # Audit trail
    try:
        TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.ROSTER_ADD,
            actor_id=request.user.pk,
            actor_username=request.user.username,
            description=f"Invited {target_user.username} as {role}",
            metadata={"invited_user": target_user.username, "role": role, "invite_id": invite.pk},
        )
    except Exception:
        logger.exception("Failed to write invite activity log")
    # Notification
    try:
        NotificationService.notify_vnext_team_invite_sent(
            recipient_user=target_user, team=team,
            inviter_user=request.user, role=role,
        )
    except Exception:
        logger.exception("Failed to send invite notification")
    return JsonResponse({
        "success": True,
        "message": f"Invitation sent to {target_user.username}.",
        "invite": {
            "id": invite.id,
            "username": target_user.username,
            "display_name": target_user.get_full_name() or target_user.username,
            "avatar_url": avatar_url,
            "role": invite.role,
            "created_at": invite.created_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# 6. Join Requests
# ---------------------------------------------------------------------------

@login_required
@require_GET
def manage_get_join_requests(request, slug):
    """Return pending join requests.

    The organizations app does not have a JoinRequest model yet.
    Return an empty list so the UI degrades gracefully.
    """
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err
    return JsonResponse({"success": True, "join_requests": []})


@login_required
@require_POST
@transaction.atomic
def manage_handle_join_request(request, slug, request_id):
    """Approve or reject a join request.

    Not yet implemented for organizations — always returns 404.
    """
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err
    return JsonResponse(
        {"success": False, "error": "Join requests are not supported yet."},
        status=404,
    )


# ---------------------------------------------------------------------------
# 7. Update Member Role
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_update_member_role(request, slug, membership_id):
    """
    Update a member's role, roster_slot, player_role, and/or captain status.

    Expects JSON or form body:
      role          – MembershipRole value (OWNER/MANAGER/COACH/PLAYER/SUBSTITUTE/ANALYST/SCOUT)
      roster_slot   – RosterSlot value (STARTER/SUBSTITUTE/COACH/ANALYST) [optional]
      player_role   – Free-text tactical role [optional]
      assign_captain – "true"/"false" to toggle tournament captain [optional]
    """
    team, admin_membership, err = _get_admin_context(request, slug)
    if err:
        return err

    target = TeamMembership.objects.filter(
        pk=membership_id, team=team, status=MembershipStatus.ACTIVE,
    ).select_related('user').first()

    if not target:
        return JsonResponse({"success": False, "error": "Member not found."}, status=404)

    data = _parse_body(request)
    new_role = data.get("role", "").strip().upper()
    roster_slot = data.get("roster_slot", "").strip().upper()
    player_role = data.get("player_role", "").strip()
    assign_captain = _bool_val(data.get("assign_captain", False))

    # Validate role
    valid_roles = {c[0] for c in MembershipRole.choices}
    if new_role and new_role not in valid_roles:
        return JsonResponse({"success": False, "error": f"Invalid role: {new_role}"}, status=400)

    # Only owners can promote to OWNER or MANAGER
    if new_role in (MembershipRole.OWNER, MembershipRole.MANAGER):
        is_owner = (
            team.created_by == request.user
            or (admin_membership and admin_membership.role == MembershipRole.OWNER)
        )
        if not is_owner:
            return JsonResponse(
                {"success": False, "error": "Only the owner can assign Owner/Manager roles."},
                status=403,
            )

    # Cannot demote yourself if you're the only OWNER
    if target.user == request.user and target.role == MembershipRole.OWNER and new_role != MembershipRole.OWNER:
        owner_count = TeamMembership.objects.filter(
            team=team, role=MembershipRole.OWNER, status=MembershipStatus.ACTIVE,
        ).count()
        if owner_count <= 1:
            return JsonResponse(
                {"success": False, "error": "Cannot demote the only owner. Transfer ownership first."},
                status=400,
            )

    old_role = target.role

    if new_role:
        target.role = new_role

    # Roster slot
    valid_slots = {c[0] for c in RosterSlot.choices}
    if roster_slot and roster_slot in valid_slots:
        target.roster_slot = roster_slot

    if player_role is not None:
        target.player_role = player_role

    # Tournament captain toggle
    if assign_captain and not target.is_tournament_captain:
        # Clear existing captain
        TeamMembership.objects.filter(
            team=team, is_tournament_captain=True, status=MembershipStatus.ACTIVE,
        ).exclude(pk=target.pk).update(is_tournament_captain=False)
        target.is_tournament_captain = True
    elif not assign_captain and target.is_tournament_captain:
        target.is_tournament_captain = False

    target.save()

    # Audit trail — MembershipEvent
    TeamMembershipEvent.objects.create(
        membership=target,
        team=team,
        user=target.user,
        actor=request.user,
        event_type=MembershipEventType.ROLE_CHANGED,
        old_role=old_role,
        new_role=target.role,
        metadata={"roster_slot": target.roster_slot, "player_role": target.player_role,
                  "is_captain": target.is_tournament_captain},
    )
    # Audit trail — ActivityLog
    try:
        TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.ROSTER_UPDATE,
            actor_id=request.user.pk,
            actor_username=request.user.username,
            description=f"Changed {target.user.username} role: {old_role} → {target.role}",
            metadata={"member": target.user.username, "old_role": old_role, "new_role": target.role},
        )
    except Exception:
        logger.exception("Failed to write role-change activity log")
    # Notification
    try:
        NotificationService.notify_roster_change(team, 'role_changed', target.user)
    except Exception:
        logger.exception("Failed to send role-change notification")

    logger.info(
        "[AUDIT] Role updated: team=%s member=%s %s→%s by=%s",
        team.slug, target.user.username, old_role, target.role, request.user.username,
    )
    return JsonResponse({
        "success": True,
        "message": f"Role for {target.user.username} updated to {target.role}.",
    })


# ---------------------------------------------------------------------------
# 8. Remove Member
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_remove_member(request, slug, membership_id):
    """
    Remove a member from the team.

    Expects JSON or form body:
      confirmation – Must match the member's username.
    """
    team, admin_membership, err = _get_admin_context(request, slug)
    if err:
        return err

    target = TeamMembership.objects.filter(
        pk=membership_id, team=team, status=MembershipStatus.ACTIVE,
    ).select_related('user').first()

    if not target:
        return JsonResponse({"success": False, "error": "Member not found."}, status=404)

    # Cannot remove yourself (use "leave team" flow)
    if target.user == request.user:
        return JsonResponse({"success": False, "error": "You cannot remove yourself. Use the leave team option."}, status=400)

    # Cannot remove the owner unless you're superuser
    if target.role == MembershipRole.OWNER and not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "Cannot remove the team owner."}, status=403)

    data = _parse_body(request)
    confirmation = data.get("confirmation", "").strip()
    if confirmation != target.user.username:
        return JsonResponse(
            {"success": False, "error": f'Type "{target.user.username}" to confirm removal.'},
            status=400,
        )

    # Soft-remove: set status to INACTIVE with leave metadata
    target.status = MembershipStatus.INACTIVE
    target.left_at = timezone.now()
    target.left_reason = f"Removed by {request.user.username}"
    target.save()

    # Audit trail — MembershipEvent
    TeamMembershipEvent.objects.create(
        membership=target,
        team=team,
        user=target.user,
        actor=request.user,
        event_type=MembershipEventType.REMOVED,
        old_role=target.role,
        old_status=MembershipStatus.ACTIVE,
        new_status=MembershipStatus.INACTIVE,
        metadata={"reason": "removed_by_admin"},
    )
    # Audit trail — ActivityLog
    try:
        TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.ROSTER_REMOVE,
            actor_id=request.user.pk,
            actor_username=request.user.username,
            description=f"Removed {target.user.username} from the team",
            metadata={"member": target.user.username, "role": target.role, "reason": "removed_by_admin"},
        )
    except Exception:
        logger.exception("Failed to write remove-member activity log")
    # Notification
    try:
        NotificationService.notify_roster_change(team, 'removed', target.user)
    except Exception:
        logger.exception("Failed to send remove-member notification")

    logger.info(
        "[AUDIT] Member removed: team=%s member=%s by=%s",
        team.slug, target.user.username, request.user.username,
    )
    return JsonResponse({
        "success": True,
        "message": f"{target.user.username} has been removed from the team.",
    })


# ---------------------------------------------------------------------------
# 9. Cancel Invite
# ---------------------------------------------------------------------------

@login_required
@require_POST
@transaction.atomic
def manage_cancel_invite(request, slug, invite_id):
    """Cancel a pending team invite."""
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    invite = TeamInvite.objects.filter(
        pk=invite_id, team=team, status="PENDING",
    ).first()

    if not invite:
        return JsonResponse({"success": False, "error": "Invite not found or already handled."}, status=404)

    invite.status = "CANCELLED"
    invite.responded_at = timezone.now()
    invite.save()

    logger.info(
        "[AUDIT] Invite cancelled: team=%s invite=%d by=%s",
        team.slug, invite.pk, request.user.username,
    )
    # Audit trail
    try:
        invited_name = getattr(invite.invited_user, 'username', 'unknown')
        TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.ROSTER_REMOVE,
            actor_id=request.user.pk,
            actor_username=request.user.username,
            description=f"Cancelled invite for {invited_name}",
            metadata={"invite_id": invite.pk, "invited_user": invited_name},
        )
    except Exception:
        logger.exception("Failed to write cancel-invite activity log")
    return JsonResponse({"success": True, "message": "Invite cancelled."})


# ---------------------------------------------------------------------------
# 10. Recent Activity Feed
# ---------------------------------------------------------------------------

@login_required
@require_GET
def manage_activity(request, slug):
    """Return recent activity log entries for the team.

    Supports optional query parameters for filtering:
        ?type=roster|tournament|settings|profile
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?limit=N (max 50)
    """
    team, membership, err = _get_admin_context(request, slug)
    if err:
        return err

    try:
        limit = min(int(request.GET.get("limit", 20)), 50)
    except (ValueError, TypeError):
        limit = 20

    qs = TeamActivityLog.objects.filter(team=team)

    # Optional filters
    action_type = request.GET.get("type", "").strip()
    if action_type:
        qs = qs.filter(action_type__icontains=action_type)

    date_from = request.GET.get("from", "").strip()
    if date_from:
        try:
            from datetime import date as date_type
            parts = date_from.split("-")
            dt_from = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
            qs = qs.filter(timestamp__date__gte=dt_from)
        except (ValueError, IndexError):
            pass

    date_to = request.GET.get("to", "").strip()
    if date_to:
        try:
            from datetime import date as date_type
            parts = date_to.split("-")
            dt_to = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
            qs = qs.filter(timestamp__date__lte=dt_to)
        except (ValueError, IndexError):
            pass

    activities = qs.order_by('-timestamp')[:limit]

    items = []
    for a in activities:
        items.append({
            "id": a.pk,
            "type": a.action_type,
            "action_type": a.action_type,
            "actor": a.actor_username,
            "description": a.description,
            "timestamp": a.timestamp.isoformat(),
            "time_ago": _time_ago(a.timestamp),
            "metadata": a.metadata or {},
        })

    return JsonResponse({"success": True, "activities": items})


def _time_ago(dt):
    """Return a human-readable time-ago string."""
    from django.utils.timesince import timesince
    return f"{timesince(dt)} ago"
