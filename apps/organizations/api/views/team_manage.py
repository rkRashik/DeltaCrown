"""
Team Manage HQ API Views

5 endpoints for Team Manage (HQ) functionality:
1. GET /api/vnext/teams/<slug>/detail/ - Bootstrap data (team + members + permissions)
2. POST /api/vnext/teams/<slug>/members/add/ - Add member by email/username
3. POST /api/vnext/teams/<slug>/members/<id>/role/ - Change member role
4. POST /api/vnext/teams/<slug>/members/<id>/remove/ - Remove member
5. POST /api/vnext/teams/<slug>/settings/ - Update team settings

All endpoints enforce permissions:
- Creator (team.created_by) can manage everything
- MANAGER role can manage roster (add/remove/change roles)
- Organization admins can manage org-owned teams
"""

import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Team, TeamMembership, TeamMembershipEvent
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus, MembershipEventType
from apps.accounts.models import User
from apps.organizations.services.hub_cache import invalidate_hub_cache


def _check_manage_permissions(team, user):
    """
    Reusable permissions helper for Team Manage operations.
    
    Returns (has_permission: bool, reason: str or None)
    
    Allows:
    - Creator (team.created_by)
    - Team MANAGER role
    - Organization admin (for org-owned teams)
    """
    if not user.is_authenticated:
        return False, "Authentication required"
    
    # Superusers always have permission
    if user.is_superuser:
        return True, None
    
    # Creator always has permission
    if team.created_by_id == user.id:
        return True, None
    
    # Check team membership role (MANAGER or COACH)
    try:
        membership = team.vnext_memberships.get(user=user)
        if membership.role in (MembershipRole.MANAGER, MembershipRole.COACH):
            return True, None
    except TeamMembership.DoesNotExist:
        pass
    
    # Check organization admin (if org-owned team)
    if team.organization:
        if team.organization.admins.filter(id=user.id).exists():
            return True, None
    
    return False, "You do not have permission to manage this team"


@require_http_methods(["GET"])
@login_required
def team_detail(request, slug):
    """
    GET /api/vnext/teams/<slug>/detail/
    
    Bootstrap data for Team Manage HQ.
    
    Returns:
    - Team info (name, slug, tag, game, org, created, status, visibility)
    - Members list (id, username, email, role, joined_at)
    - User permissions (can_manage, can_remove_self, is_creator)
    - Ranking data (score, tier, rank)
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check membership (must be member, creator, org admin, or superuser to view)
    if not request.user.is_superuser:
        if not team.vnext_memberships.filter(user=request.user).exists():
            if team.created_by != request.user:
                if not (team.organization and team.organization.admins.filter(id=request.user.id).exists()):
                    return JsonResponse({'error': 'You are not a member of this team'}, status=403)
    
    # Check manage permissions
    can_manage, _ = _check_manage_permissions(team, request.user)
    
    # Build members list
    members = []
    for membership in team.vnext_memberships.select_related('user').order_by('-role', '-joined_at'):
        members.append({
            'id': membership.id,
            'username': membership.user.username,
            'email': membership.user.email,
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
        })
    
    # Get ranking data (safe defaults: 0-point team rule)
    ranking_data = {'score': 0, 'tier': 'UNRANKED', 'rank': None}
    try:
        latest_snapshot = team.ranking_snapshots.latest('created_at')
        ranking_data = {
            'score': latest_snapshot.score if latest_snapshot.score is not None else 0,
            'tier': latest_snapshot.tier if latest_snapshot.tier else 'UNRANKED',
            'rank': latest_snapshot.global_rank,
        }
    except Exception:
        # No snapshot exists - use safe defaults
        pass
    
    response = {
        'team': {
            'id': team.id,
            'name': team.name,
            'slug': team.slug,
            'tag': team.tag,
            'game_id': team.game_id,
            'organization': team.organization.name if team.organization else None,
            'created_at': team.created_at.isoformat() if team.created_at else None,
            'status': team.status,
            'visibility': team.visibility,
            'member_count': len(members),
        },
        'members': members,
        'permissions': {
            'can_manage': can_manage,
            'can_remove_self': True,  # All members can leave
            'is_creator': team.created_by_id == request.user.id,
        },
        'ranking': ranking_data,
    }
    
    return JsonResponse(response)


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def add_member(request, slug):
    """
    POST /api/vnext/teams/<slug>/members/add/
    
    Add member to team by email or username.
    
    Required params:
    - identifier: email or username
    - role: MembershipRole value (default: PLAYER)
    
    Enforces:
    - Manage permissions
    - User must exist
    - User not already a member
    - Role is valid
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check permissions
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    # Parse params
    identifier = request.POST.get('identifier', '').strip()
    role = request.POST.get('role', MembershipRole.PLAYER).strip()
    
    if not identifier:
        return JsonResponse({'error': 'identifier required (email or username)'}, status=400)
    
    # Validate role
    if role not in [choice[0] for choice in MembershipRole.choices]:
        return JsonResponse({'error': f'Invalid role: {role}'}, status=400)
    
    # Platform rule: OWNER role forbidden in vNext (use created_by + permissions)
    if role == MembershipRole.OWNER:
        return JsonResponse({
            'error': 'OWNER role cannot be assigned. Use MANAGER role for team administration.'
        }, status=400)
    
    # Find user by email or username
    user = None
    if '@' in identifier:
        try:
            user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            return JsonResponse({'error': f'User not found with email: {identifier}'}, status=404)
    else:
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            return JsonResponse({'error': f'User not found with username: {identifier}'}, status=404)
    
    # Check if already a member
    if team.vnext_memberships.filter(user=user).exists():
        return JsonResponse({'error': f'{user.username} is already a member of this team'}, status=400)
    
    # Platform rule: One active team per user per game
    # Check if user has active membership on another active team with same game_id
    existing_active_membership = TeamMembership.objects.filter(
        user=user,
        game_id=team.game_id,
        status=MembershipStatus.ACTIVE
    ).select_related('team').exclude(
        team=team  # Exclude current team (already caught by duplicate check above)
    ).filter(
        team__status=TeamStatus.ACTIVE  # Only check active teams
    ).first()
    
    if existing_active_membership:
        return JsonResponse({
            'error': f'User already has an active team for this game: {existing_active_membership.team.name}'
        }, status=400)
    
    # Create membership
    membership = TeamMembership.objects.create(
        team=team,
        user=user,
        role=role,
        status=MembershipStatus.ACTIVE,
        game_id=team.game_id,
    )
    
    # Create JOINED event (append-only ledger)
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=user,
        actor=request.user,
        event_type=MembershipEventType.JOINED,
        new_role=role,
        new_status=MembershipStatus.ACTIVE,
        metadata={},
    )
    
    # Invalidate hub cache (roster change may affect featured teams display)
    invalidate_hub_cache(game_id=team.game_id)
    
    return JsonResponse({
        'success': True,
        'member': {
            'id': membership.id,
            'username': user.username,
            'email': user.email,
            'role': role,
            'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
        }
    })


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def change_role(request, slug, membership_id):
    """
    POST /api/vnext/teams/<slug>/members/<id>/role/
    
    Change member's role.
    
    Required params:
    - role: MembershipRole value
    
    Enforces:
    - Manage permissions
    - Cannot change own role
    - Cannot change creator's role
    - Role is valid
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check permissions
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    # Get membership
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Cannot change own role
    if membership.user_id == request.user.id:
        return JsonResponse({'error': 'Cannot change your own role'}, status=400)
    
    # Cannot change creator's role
    if membership.user_id == team.created_by_id:
        return JsonResponse({'error': 'Cannot change the creator\'s role'}, status=400)
    
    # Parse role
    new_role = request.POST.get('role', '').strip()
    if not new_role:
        return JsonResponse({'error': 'role required'}, status=400)
    
    # Validate role
    if new_role not in [choice[0] for choice in MembershipRole.choices]:
        return JsonResponse({'error': f'Invalid role: {new_role}'}, status=400)
    
    # Platform rule: OWNER role forbidden in vNext (use created_by + permissions)
    if new_role == MembershipRole.OWNER:
        return JsonResponse({
            'error': 'OWNER role cannot be assigned. Use MANAGER role for team administration.'
        }, status=400)
    
    # Store old role for event
    old_role = membership.role
    
    # Update role
    membership.role = new_role
    membership.save(update_fields=['role'])
    
    # Create ROLE_CHANGED event (append-only ledger)
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=membership.user,
        actor=request.user,
        event_type=MembershipEventType.ROLE_CHANGED,
        old_role=old_role,
        new_role=new_role,
        metadata={},
    )
    
    return JsonResponse({
        'success': True,
        'member': {
            'id': membership.id,
            'username': membership.user.username,
            'role': new_role,
        }
    })


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def remove_member(request, slug, membership_id):
    """
    POST /api/vnext/teams/<slug>/members/<id>/remove/
    
    Remove member from team.
    
    Enforces:
    - Manage permissions OR self-removal
    - Cannot remove creator
    - Team must have at least 1 member after removal
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Get membership
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Check permissions: manage OR self-removal
    is_self_removal = membership.user_id == request.user.id
    if not is_self_removal:
        has_permission, reason = _check_manage_permissions(team, request.user)
        if not has_permission:
            return JsonResponse({'error': reason}, status=403)
    
    # Cannot remove creator
    if membership.user_id == team.created_by_id:
        return JsonResponse({'error': 'Cannot remove the team creator'}, status=400)
    
    # Check team will have at least 1 member
    if team.vnext_memberships.count() <= 1:
        return JsonResponse({'error': 'Cannot remove last member from team'}, status=400)
    
    # Store user info before deletion
    username = membership.user.username
    user = membership.user
    old_status = membership.status
    is_self = is_self_removal
    
    # Update membership status and left_at
    membership.status = MembershipStatus.INACTIVE
    membership.left_at = timezone.now()
    membership.save(update_fields=['status', 'left_at'])
    
    # Create REMOVED or LEFT event (append-only ledger)
    event_type = MembershipEventType.LEFT if is_self else MembershipEventType.REMOVED
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=user,
        actor=request.user,
        event_type=event_type,
        old_status=old_status,
        new_status=MembershipStatus.INACTIVE,
        metadata={'reason': 'self_removal' if is_self else 'removed_by_manager'},
    )
    
    # Invalidate hub cache (roster change may affect featured teams display)
    invalidate_hub_cache(game_id=team.game_id)
    
    return JsonResponse({
        'success': True,
        'removed': username,
    })


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def update_settings(request, slug):
    """
    POST /api/vnext/teams/<slug>/settings/
    
    Update team settings (tagline, description, social links).
    
    Optional params:
    - tagline: string (max 100 chars)
    - description: string (max 500 chars)
    - twitter: string
    - discord: string
    - website: string
    
    Enforces:
    - Manage permissions
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check permissions
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    # Parse params
    tagline = request.POST.get('tagline', '').strip()
    description = request.POST.get('description', '').strip()
    twitter = request.POST.get('twitter', '').strip()
    discord = request.POST.get('discord', '').strip()
    website = request.POST.get('website', '').strip()
    
    # Validate lengths
    if len(tagline) > 100:
        return JsonResponse({'error': 'Tagline must be 100 characters or less'}, status=400)
    if len(description) > 500:
        return JsonResponse({'error': 'Description must be 500 characters or less'}, status=400)
    
    # Update team fields (if fields exist on model)
    updated_fields = []
    if hasattr(team, 'tagline'):
        team.tagline = tagline
        updated_fields.append('tagline')
    if hasattr(team, 'description'):
        team.description = description
        updated_fields.append('description')
    if hasattr(team, 'twitter'):
        team.twitter = twitter
        updated_fields.append('twitter')
    if hasattr(team, 'discord'):
        team.discord = discord
        updated_fields.append('discord')
    if hasattr(team, 'website'):
        team.website = website
        updated_fields.append('website')
    
    if updated_fields:
        team.save(update_fields=updated_fields)
    
    return JsonResponse({
        'success': True,
        'message': 'Team settings updated',
    })


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def update_profile(request, slug):
    """
    POST /api/vnext/teams/<slug>/profile/
    
    Update comprehensive team profile (name, tagline, description, colors, socials, tournament ops).
    
    Optional params:
    - name: string (max 100 chars)
    - tagline: string (max 100 chars)
    - description: text
    - region: string (max 50 chars)
    - primary_color: hex color (e.g., #3B82F6)
    - accent_color: hex color (e.g., #10B981)
    - twitter_url: URL
    - instagram_url: URL
    - youtube_url: URL
    - twitch_url: URL
    - preferred_server: string (max 50 chars)
    - emergency_contact_discord: string (max 50 chars)
    - emergency_contact_phone: string (max 20 chars)
    
    Enforces:
    - Manage permissions (MANAGER+ role)
    - Name uniqueness (slug will be regenerated if name changes)
    - Hex color validation
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check permissions
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    # Parse params
    name = request.POST.get('name', '').strip()
    tagline = request.POST.get('tagline', '').strip()
    description = request.POST.get('description', '').strip()
    region = request.POST.get('region', '').strip()
    primary_color = request.POST.get('primary_color', '').strip()
    accent_color = request.POST.get('accent_color', '').strip()
    twitter_url = request.POST.get('twitter_url', '').strip()
    instagram_url = request.POST.get('instagram_url', '').strip()
    youtube_url = request.POST.get('youtube_url', '').strip()
    twitch_url = request.POST.get('twitch_url', '').strip()
    preferred_server = request.POST.get('preferred_server', '').strip()
    emergency_contact_discord = request.POST.get('emergency_contact_discord', '').strip()
    emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
    
    # Handle file uploads
    logo = request.FILES.get('logo')
    banner = request.FILES.get('banner')
    
    # Validate lengths
    if name and len(name) > 100:
        return JsonResponse({'error': 'Team name must be 100 characters or less'}, status=400)
    if tagline and len(tagline) > 100:
        return JsonResponse({'error': 'Tagline must be 100 characters or less'}, status=400)
    if region and len(region) > 50:
        return JsonResponse({'error': 'Region must be 50 characters or less'}, status=400)
    
    # Validate hex colors
    hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
    if primary_color and not hex_pattern.match(primary_color):
        return JsonResponse({'error': 'Primary color must be in hex format (e.g., #3B82F6)'}, status=400)
    if accent_color and not hex_pattern.match(accent_color):
        return JsonResponse({'error': 'Accent color must be in hex format (e.g., #10B981)'}, status=400)
    
    # Update team fields - check if field is in POST data
    if 'name' in request.POST:
        name = request.POST.get('name', '').strip()
        if name:  # Name must not be empty if provided
            if name != team.name:
                new_slug = slugify(name)
                if Team.objects.filter(slug=new_slug).exclude(id=team.id).exists():
                    return JsonResponse({'error': f'A team with the name "{name}" already exists'}, status=400)
                team.name = name
                team.slug = new_slug
    
    if 'tagline' in request.POST:
        team.tagline = request.POST.get('tagline', '').strip()
    
    if 'description' in request.POST:
        team.description = request.POST.get('description', '').strip()
    
    if 'region' in request.POST:
        team.region = request.POST.get('region', '').strip()
    
    if 'primary_color' in request.POST:
        primary_color = request.POST.get('primary_color', '').strip()
        if primary_color:
            team.primary_color = primary_color
    
    if 'accent_color' in request.POST:
        accent_color = request.POST.get('accent_color', '').strip()
        if accent_color:
            team.accent_color = accent_color
    
    # Social links - allow empty to clear
    if 'twitter_url' in request.POST:
        team.twitter_url = request.POST.get('twitter_url', '').strip()
    if 'instagram_url' in request.POST:
        team.instagram_url = request.POST.get('instagram_url', '').strip()
    if 'youtube_url' in request.POST:
        team.youtube_url = request.POST.get('youtube_url', '').strip()
    if 'twitch_url' in request.POST:
        team.twitch_url = request.POST.get('twitch_url', '').strip()
    
    # Tournament ops
    if 'preferred_server' in request.POST:
        team.preferred_server = request.POST.get('preferred_server', '').strip()
    if 'emergency_contact_discord' in request.POST:
        team.emergency_contact_discord = request.POST.get('emergency_contact_discord', '').strip()
    if 'emergency_contact_phone' in request.POST:
        team.emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
    
    # Handle file uploads
    if logo:
        team.logo = logo
    if banner:
        team.banner = banner
    
    team.save()
    
    # Invalidate hub cache (branding changes may affect display)
    # TODO: Implement when hub caching is ready
    # invalidate_hub_cache(game_id=team.game_id)
    
    return JsonResponse({
        'success': True,
        'message': 'Team profile updated successfully',
        'team': {
            'name': team.name,
            'slug': team.slug,
            'tagline': team.tagline,
        }
    })


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def change_member_status(request, slug, membership_id):
    """
    POST /api/vnext/teams/<slug>/members/<id>/status/
    
    Change member's status (for moderation: suspend, ban, warn).
    
    Required params:
    - status: MembershipStatus value (ACTIVE, SUSPENDED, etc.)
    - reason: Explanation for status change (required for SUSPENDED)
    
    Optional params:
    - duration_days: Suspension duration (for temporary suspensions)
    
    Enforces:
    - Manage permissions (creator OR manager OR org admin)
    - Cannot change creator's status
    - Reason required for SUSPENDED status
    
    Creates STATUS_CHANGED event with reason in metadata.
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check permissions
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    # Get membership
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Cannot change creator's status
    if membership.user_id == team.created_by_id:
        return JsonResponse({'error': 'Cannot change the creator\'s status'}, status=400)
    
    # Parse params
    new_status = request.POST.get('status', '').strip()
    reason_text = request.POST.get('reason', '').strip()
    duration_days = request.POST.get('duration_days', '').strip()
    
    if not new_status:
        return JsonResponse({'error': 'status required'}, status=400)
    
    # Validate status
    if new_status not in [choice[0] for choice in MembershipStatus.choices]:
        return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)
    
    # Require reason for SUSPENDED status
    if new_status == MembershipStatus.SUSPENDED and not reason_text:
        return JsonResponse({'error': 'reason required for SUSPENDED status'}, status=400)
    
    # Store old status for event
    old_status = membership.status
    
    # Update status
    membership.status = new_status
    membership.save(update_fields=['status'])
    
    # Build metadata
    metadata = {'reason': reason_text} if reason_text else {}
    if duration_days and duration_days.isdigit():
        metadata['duration_days'] = int(duration_days)
    
    # Create STATUS_CHANGED event (append-only ledger)
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=membership.user,
        actor=request.user,
        event_type=MembershipEventType.STATUS_CHANGED,
        old_status=old_status,
        new_status=new_status,
        metadata=metadata,
    )
    
    return JsonResponse({
        'success': True,
        'member': {
            'id': membership.id,
            'username': membership.user.username,
            'status': new_status,
            'reason': reason_text,
        }
    })
