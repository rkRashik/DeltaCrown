"""
Team Manage HQ API Views

Endpoints for Team Manage (HQ) functionality:
1. GET  /api/vnext/teams/<slug>/detail/ - Bootstrap data (team + members + permissions)
2. POST /api/vnext/teams/<slug>/members/add/ - Add member by email/username
3. POST /api/vnext/teams/<slug>/members/<id>/role/ - Change member role
4. POST /api/vnext/teams/<slug>/members/<id>/remove/ - Remove member
5. POST /api/vnext/teams/<slug>/settings/ - Update team settings
6. POST /api/vnext/teams/<slug>/profile/ - Update team profile
7. POST /api/vnext/teams/<slug>/members/<id>/status/ - Change member status
8. POST /api/vnext/teams/<slug>/members/<id>/roster-photo/ - Upload roster photo
9. POST /api/vnext/teams/<slug>/owner-privacy/ - Toggle owner privacy
10. POST /api/vnext/teams/<slug>/roster/lock/ - Toggle roster lock
11. POST /api/vnext/teams/<slug>/leave/ - Leave team (self-removal)
12. POST /api/vnext/teams/<slug>/disband/ - Delete/disband team
13. POST /api/vnext/teams/<slug>/transfer-ownership/ - Transfer ownership
14. POST /api/vnext/teams/<slug>/invite-link/ - Generate invite link
15. GET  /api/vnext/teams/<slug>/activity/ - Activity timeline

All endpoints enforce permissions:
- Creator (team.created_by) can manage everything
- MANAGER role can manage roster (add/remove/change roles)
- Organization admins can manage org-owned teams
"""

import json
import re
import uuid

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Team, TeamMembership, TeamMembershipEvent
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus, MembershipEventType, RosterSlot
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


def _get_user_role(team, user):
    """Get user's membership role for the given team."""
    if not user.is_authenticated:
        return 'GUEST'
    if user.is_superuser:
        return 'OWNER'
    if team.created_by_id == user.id:
        return 'OWNER'
    try:
        membership = team.vnext_memberships.get(user=user)
        return membership.role
    except TeamMembership.DoesNotExist:
        return 'GUEST'


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
    
    # Build members list with full roster data
    members = []
    for membership in team.vnext_memberships.select_related('user', 'user__profile').order_by('-role', '-joined_at'):
        # Resolve avatar: roster_image > user profile avatar > None
        avatar_url = None
        if membership.roster_image:
            avatar_url = membership.roster_image.url
        elif hasattr(membership.user, 'profile') and membership.user.profile.avatar:
            avatar_url = membership.user.profile.avatar.url
        
        # Resolve display name: membership display_name > profile display_name > username
        display_name = membership.display_name
        if not display_name and hasattr(membership.user, 'profile'):
            display_name = getattr(membership.user.profile, 'display_name', '')
        if not display_name:
            display_name = membership.user.username
        
        members.append({
            'id': membership.id,
            'user_id': membership.user_id,
            'username': membership.user.username,
            'email': membership.user.email,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'role': membership.role,
            'roster_slot': membership.roster_slot or '',
            'player_role': membership.player_role or '',
            'is_tournament_captain': membership.is_tournament_captain,
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
    
    # Fetch game-specific roles for the team's game (In-Game Role dropdown)
    game_roles = []
    if team.game_id:
        try:
            from apps.games.models import GameRole
            for gr in GameRole.objects.filter(game_id=team.game_id, is_active=True).order_by('order', 'role_name'):
                game_roles.append({
                    'id': gr.id,
                    'role_name': gr.role_name,
                    'role_code': gr.role_code,
                    'icon': gr.icon,
                    'color': gr.color,
                })
        except Exception:
            pass  # games app not installed or table missing
    
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
            'roster_locked': team.roster_locked,
            'invite_code': team.invite_code or '',
            'discord_webhook_url': team.discord_webhook_url or '',
            'website_url': team.website_url or '',
        },
        'members': members,
        'permissions': {
            'can_manage': can_manage,
            'can_remove_self': True,  # All members can leave
            'is_creator': team.created_by_id == request.user.id,
            'user_role': _get_user_role(team, request.user),
        },
        'ranking': ranking_data,
        'game_roles': game_roles,
        'choices': {
            'membership_roles': [
                {'value': c[0], 'label': c[1]}
                for c in MembershipRole.choices if c[0] != MembershipRole.OWNER
            ],
            'roster_slots': [
                {'value': c[0], 'label': c[1]}
                for c in RosterSlot.choices
            ],
        },
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
    
    # Parse params — support both JSON body and form POST
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = request.POST
    
    identifier = (data.get('identifier') or data.get('username_or_email') or '').strip()
    role = (data.get('role') or MembershipRole.PLAYER).strip()
    
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
    
    # Sync primary_team on user profile
    try:
        from apps.organizations.services.profile_sync import sync_primary_team
        sync_primary_team(user)
    except Exception:
        pass  # Non-critical sync
    
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
    
    Change member's role, roster slot, in-game role, captain flag.
    
    Required params:
    - role: MembershipRole value
    
    Optional params:
    - player_role: In-game tactical role (e.g. 'Duelist', 'IGL')
    - roster_slot: Roster slot (STARTER, SUBSTITUTE, COACH, ANALYST)
    - is_tournament_captain: 'true'/'false' - Tournament captain flag
    - display_name: Custom display name for this team roster
    
    Enforces:
    - Manage permissions (or self-edit for roster fields only)
    - Cannot change org role on creator
    - Role is valid
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Get membership
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Check permissions — allow self-edit for roster fields
    is_self = membership.user_id == request.user.id
    has_permission, reason = _check_manage_permissions(team, request.user)
    
    if not has_permission and not is_self:
        return JsonResponse({'error': reason}, status=403)
    
    # Parse params — support both JSON body and form POST
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = request.POST
    
    # Self-edit restrictions: members can only change their own roster fields
    # (player_role, roster_slot, display_name) — NOT org role or captain flag
    ROSTER_SELF_FIELDS = {'player_role', 'roster_slot', 'display_name'}
    if is_self and not has_permission:
        # Non-admin self-edit: strip any fields they're not allowed to change
        data = {k: v for k, v in data.items() if k in ROSTER_SELF_FIELDS}
        if not data:
            return JsonResponse({'error': 'No editable fields provided'}, status=400)
    
    # If self-edit by admin/owner: allow roster fields but NOT their own org role change
    if is_self and has_permission:
        submitted_role = (data.get('role', '') or '').strip()
        if submitted_role and submitted_role != membership.role:
            return JsonResponse({'error': 'Cannot change your own organizational role. Use Transfer Ownership instead.'}, status=400)
    
    # Cannot change creator's org role (must use transfer ownership)
    if not is_self and membership.user_id == team.created_by_id:
        submitted_role = (data.get('role', '') or '').strip()
        if submitted_role and submitted_role != membership.role:
            return JsonResponse({'error': 'Cannot change the creator\'s role. Use Transfer Ownership.'}, status=400)
    
    # Parse params — support both JSON body and form POST
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = request.POST
    
    # Parse role
    new_role = data.get('role', '').strip() if data.get('role') else ''
    if not new_role:
        # For swapSlot calls that only send roster_slot
        new_role = membership.role
    
    # Validate role
    valid_roles = [choice[0] for choice in MembershipRole.choices]
    if new_role not in valid_roles:
        return JsonResponse({'error': f'Invalid role: {new_role}'}, status=400)
    
    # Platform rule: OWNER role forbidden in vNext (use created_by + permissions)
    if new_role == MembershipRole.OWNER:
        return JsonResponse({
            'error': 'OWNER role cannot be assigned. Use MANAGER role for team administration.'
        }, status=400)
    
    # Parse optional roster fields
    player_role = (data.get('player_role') or '').strip()
    roster_slot = (data.get('roster_slot') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    is_captain_raw = (data.get('is_tournament_captain') or data.get('assign_captain') or '').strip().lower()
    
    # Validate roster_slot if provided
    valid_slots = [choice[0] for choice in RosterSlot.choices]
    if roster_slot and roster_slot not in valid_slots:
        return JsonResponse({'error': f'Invalid roster slot: {roster_slot}'}, status=400)
    
    # Validate player_role against GameRole if provided
    if player_role and team.game_id:
        try:
            from apps.games.models import GameRole
            valid_game_roles = list(
                GameRole.objects.filter(game_id=team.game_id, is_active=True)
                .values_list('role_name', flat=True)
            )
            if valid_game_roles and player_role not in valid_game_roles:
                return JsonResponse({'error': f'Invalid in-game role: {player_role}'}, status=400)
        except Exception:
            pass  # No validation if games app unavailable
    
    # Store old role for event
    old_role = membership.role
    
    # Track what changed for metadata
    changes = {}
    update_fields = []
    
    # Update membership role
    if new_role != membership.role:
        changes['role'] = {'old': membership.role, 'new': new_role}
        membership.role = new_role
        update_fields.append('role')
    
    # Update player_role (in-game tactical role)
    if 'player_role' in data:
        if player_role != membership.player_role:
            changes['player_role'] = {'old': membership.player_role, 'new': player_role}
        membership.player_role = player_role
        update_fields.append('player_role')
    
    # Update roster_slot
    if 'roster_slot' in data:
        if roster_slot != (membership.roster_slot or ''):
            changes['roster_slot'] = {'old': membership.roster_slot or '', 'new': roster_slot}
        membership.roster_slot = roster_slot or None
        update_fields.append('roster_slot')
    
    # Update display_name
    if 'display_name' in data:
        if display_name != membership.display_name:
            changes['display_name'] = {'old': membership.display_name, 'new': display_name}
        membership.display_name = display_name
        update_fields.append('display_name')
    
    # Update tournament captain flag
    if is_captain_raw in ('true', 'false'):
        new_captain = is_captain_raw == 'true'
        if new_captain != membership.is_tournament_captain:
            changes['is_tournament_captain'] = {'old': membership.is_tournament_captain, 'new': new_captain}
            # If setting new captain, unset previous captain on team
            if new_captain:
                team.vnext_memberships.filter(
                    is_tournament_captain=True, status=MembershipStatus.ACTIVE
                ).exclude(id=membership.id).update(is_tournament_captain=False)
            membership.is_tournament_captain = new_captain
            update_fields.append('is_tournament_captain')
    
    if update_fields:
        membership.save(update_fields=update_fields)
    
    # Create ROLE_CHANGED event with detailed metadata
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=membership.user,
        actor=request.user,
        event_type=MembershipEventType.ROLE_CHANGED,
        old_role=old_role,
        new_role=new_role,
        metadata=changes if changes else {},
    )
    
    return JsonResponse({
        'success': True,
        'member': {
            'id': membership.id,
            'username': membership.user.username,
            'role': membership.role,
            'player_role': membership.player_role,
            'roster_slot': membership.roster_slot or '',
            'display_name': membership.display_name,
            'is_tournament_captain': membership.is_tournament_captain,
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
    
    # Sync primary_team on user profile (may clear it if no other teams)
    try:
        from apps.organizations.services.profile_sync import sync_primary_team
        sync_primary_team(user)
    except Exception:
        pass
    
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
    
    # Parse params — support both JSON body and form POST
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = request.POST
    
    name = data.get('name', '').strip() if data.get('name') else ''
    tagline = data.get('tagline', '').strip() if data.get('tagline') is not None else ''
    description = data.get('description', '').strip() if data.get('description') is not None else ''
    region = data.get('region', '').strip() if data.get('region') else ''
    primary_color = data.get('primary_color', '').strip() if data.get('primary_color') else ''
    accent_color = data.get('accent_color', '').strip() if data.get('accent_color') else ''
    twitter_url = data.get('twitter_url', '').strip() if data.get('twitter_url') is not None else ''
    instagram_url = data.get('instagram_url', '').strip() if data.get('instagram_url') is not None else ''
    youtube_url = data.get('youtube_url', '').strip() if data.get('youtube_url') is not None else ''
    twitch_url = data.get('twitch_url', '').strip() if data.get('twitch_url') is not None else ''
    preferred_server = data.get('preferred_server', '').strip() if data.get('preferred_server') else ''
    emergency_contact_discord = data.get('emergency_contact_discord', '').strip() if data.get('emergency_contact_discord') else ''
    emergency_contact_phone = data.get('emergency_contact_phone', '').strip() if data.get('emergency_contact_phone') else ''
    
    # Handle file uploads (only from multipart form)
    logo = request.FILES.get('logo')
    banner = request.FILES.get('banner')
    
    # Validate lengths
    if name and len(name) > 100:
        return JsonResponse({'error': 'Team name must be 100 characters or less'}, status=400)
    if tagline and len(tagline) > 200:
        return JsonResponse({'error': 'Tagline must be 200 characters or less'}, status=400)
    if description and len(description) > 1000:
        return JsonResponse({'error': 'Description must be 1000 characters or less'}, status=400)
    if region and len(region) > 50:
        return JsonResponse({'error': 'Region must be 50 characters or less'}, status=400)
    
    # Validate hex colors
    hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
    if primary_color and not hex_pattern.match(primary_color):
        return JsonResponse({'error': 'Primary color must be in hex format (e.g., #3B82F6)'}, status=400)
    if accent_color and not hex_pattern.match(accent_color):
        return JsonResponse({'error': 'Accent color must be in hex format (e.g., #10B981)'}, status=400)
    
    # ── Change Restrictions ──────────────────────────────────────────
    # Game: permanently locked after creation (cannot change)
    if 'game_id' in data or 'game' in data:
        return JsonResponse({'error': 'Game cannot be changed after team creation. Create a new team for a different game.'}, status=400)
    
    # Name, Tag, Region: 30-day cooldown between changes
    now = timezone.now()
    CHANGE_COOLDOWN_DAYS = 30
    
    # Check active tournament registration (prevents changes during tournament)
    has_active_tournament = False
    try:
        from apps.tournaments.models import TournamentRegistration
        has_active_tournament = TournamentRegistration.objects.filter(
            team_id=team.id,
            status__in=['REGISTERED', 'CHECKED_IN', 'IN_PROGRESS']
        ).exists()
    except (ImportError, Exception):
        pass
    
    if has_active_tournament:
        restricted_fields = []
        if 'name' in data and data.get('name', '').strip() and data.get('name', '').strip() != team.name:
            restricted_fields.append('name')
        if 'tag' in data and (data.get('tag') or '').strip() != (team.tag or ''):
            restricted_fields.append('tag')
        if 'region' in data and (data.get('region') or '').strip() and (data.get('region') or '').strip() != team.region:
            restricted_fields.append('region')
        if restricted_fields:
            return JsonResponse({
                'error': f'Cannot change {", ".join(restricted_fields)} during an active tournament. Complete or withdraw first.'
            }, status=400)
    
    # Cooldown checks for name/tag/region
    def _check_cooldown(field_name, changed_at_field, current_val, new_val):
        if new_val and new_val != current_val:
            last_changed = getattr(team, changed_at_field, None)
            if last_changed:
                days_since = (now - last_changed).days
                if days_since < CHANGE_COOLDOWN_DAYS:
                    remaining = CHANGE_COOLDOWN_DAYS - days_since
                    return JsonResponse({
                        'error': f'{field_name} can only be changed once every {CHANGE_COOLDOWN_DAYS} days. '
                                 f'{remaining} day(s) remaining until next change.'
                    }, status=400)
        return None
    
    if 'name' in data:
        name_val = (data.get('name') or '').strip()
        if name_val:
            err = _check_cooldown('Team name', 'name_changed_at', team.name, name_val)
            if err:
                return err
    
    if 'tag' in data:
        tag_val = (data.get('tag') or '').strip()
        err = _check_cooldown('Team tag', 'tag_changed_at', team.tag or '', tag_val)
        if err:
            return err
    
    if 'region' in data:
        region_val = (data.get('region') or '').strip()
        if region_val:
            err = _check_cooldown('Region', 'region_changed_at', team.region, region_val)
            if err:
                return err
    # ── End Change Restrictions ──────────────────────────────────────
    
    # Update team fields - check if field is in submitted data
    if 'name' in data:
        name_val = data.get('name', '').strip() if data.get('name') else ''
        if name_val:  # Name must not be empty if provided
            if name_val != team.name:
                new_slug = slugify(name_val)
                if Team.objects.filter(slug=new_slug).exclude(id=team.id).exists():
                    return JsonResponse({'error': f'A team with the name "{name_val}" already exists'}, status=400)
                team.name = name_val
                team.slug = new_slug
                team.name_changed_at = now
    
    if 'tagline' in data:
        team.tagline = (data.get('tagline') or '').strip()
    
    if 'description' in data:
        team.description = (data.get('description') or '').strip()
    
    if 'region' in data:
        new_region = (data.get('region') or '').strip()
        if new_region and new_region != team.region:
            team.region_changed_at = now
        team.region = new_region
    
    if 'tag' in data:
        new_tag = (data.get('tag') or '').strip()
        if new_tag and new_tag != (team.tag or ''):
            team.tag_changed_at = now
        team.tag = new_tag or team.tag
    
    if 'primary_color' in data:
        pc = (data.get('primary_color') or '').strip()
        if pc:
            team.primary_color = pc
    
    if 'accent_color' in data:
        ac = (data.get('accent_color') or '').strip()
        if ac:
            team.accent_color = ac
    
    # Social links - allow empty to clear
    social_map = {
        'twitter_url': 'twitter_url', 'twitter': 'twitter_url',
        'instagram_url': 'instagram_url', 'instagram': 'instagram_url',
        'youtube_url': 'youtube_url', 'youtube': 'youtube_url',
        'twitch_url': 'twitch_url', 'twitch': 'twitch_url',
        'facebook_url': 'facebook_url', 'facebook': 'facebook_url',
        'tiktok_url': 'tiktok_url', 'tiktok': 'tiktok_url',
        'discord_webhook_url': 'discord_webhook_url', 'discord_webhook': 'discord_webhook_url',
        'website_url': 'website_url', 'website': 'website_url',
        'whatsapp_url': 'whatsapp_url', 'whatsapp': 'whatsapp_url',
        'messenger_url': 'messenger_url', 'messenger': 'messenger_url',
    }
    for key, attr in social_map.items():
        if key in data:
            setattr(team, attr, (data.get(key) or '').strip())
    
    # Tournament ops
    if 'preferred_server' in data:
        team.preferred_server = (data.get('preferred_server') or '').strip()
    if 'emergency_contact_discord' in data:
        team.emergency_contact_discord = (data.get('emergency_contact_discord') or '').strip()
    if 'emergency_contact_phone' in data:
        team.emergency_contact_phone = (data.get('emergency_contact_phone') or '').strip()
    
    # Handle file uploads
    if logo:
        team.logo = logo
    if banner:
        team.banner = banner
    
    team.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Team profile updated successfully',
        'team': {
            'name': team.name,
            'slug': team.slug,
            'tagline': team.tagline,
            'description': team.description,
            'primary_color': team.primary_color,
            'accent_color': team.accent_color,
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
    
    # Parse params — support both JSON body and form POST
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = request.POST
    
    new_status = (data.get('status') or '').strip()
    reason_text = (data.get('reason') or '').strip()
    duration_days = (data.get('duration_days') or '').strip() if isinstance(data.get('duration_days'), str) else str(data.get('duration_days', ''))
    
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


@require_http_methods(["POST"])
@login_required
def upload_roster_photo(request, slug, membership_id):
    """
    POST /api/vnext/teams/<slug>/members/<id>/roster-photo/
    
    Upload or replace a member's dedicated roster photo.
    
    Accepts multipart file upload with key 'roster_image'.
    Max 5 MB, JPEG/PNG/WebP only.
    
    Permissions:
    - Team manager can upload for any member
    - Member can upload their own photo
    """
    team = get_object_or_404(Team, slug=slug)
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Check permissions: manager OR self
    is_self = membership.user_id == request.user.id
    if not is_self:
        has_permission, reason = _check_manage_permissions(team, request.user)
        if not has_permission:
            return JsonResponse({'error': reason}, status=403)
    
    photo = request.FILES.get('roster_image')
    if not photo:
        return JsonResponse({'error': 'No roster_image file provided'}, status=400)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if photo.content_type not in allowed_types:
        return JsonResponse({'error': 'Invalid file type. Only JPEG, PNG, and WebP are allowed.'}, status=400)
    
    # Validate file size (5 MB limit)
    if photo.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'File too large. Maximum size is 5 MB.'}, status=400)
    
    # Delete old photo if exists
    if membership.roster_image:
        try:
            membership.roster_image.delete(save=False)
        except Exception:
            pass
    
    membership.roster_image = photo
    membership.save(update_fields=['roster_image'])
    
    return JsonResponse({
        'success': True,
        'roster_image_url': membership.roster_image.url,
    })


@require_http_methods(["POST"])
@login_required
def toggle_owner_privacy(request, slug):
    """
    POST /api/vnext/teams/<slug>/owner-privacy/
    
    Toggle hide_ownership flag on the current user's membership.
    Only the OWNER can toggle this setting.
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Must be OWNER (creator) or superuser
    is_owner = (
        request.user.is_superuser
        or team.created_by_id == request.user.id
    )
    if not is_owner:
        try:
            membership = team.vnext_memberships.get(user=request.user, status=MembershipStatus.ACTIVE)
            if membership.role == MembershipRole.OWNER:
                is_owner = True
        except TeamMembership.DoesNotExist:
            pass
    
    if not is_owner:
        return JsonResponse({'error': 'Only the team owner can change privacy settings'}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}
    
    hide = data.get('hide_ownership', False)
    
    # Update the owner's membership
    membership = team.vnext_memberships.filter(
        user=request.user, status=MembershipStatus.ACTIVE
    ).first()
    
    if not membership:
        return JsonResponse({'error': 'No active membership found'}, status=404)
    
    membership.hide_ownership = bool(hide)
    membership.save(update_fields=['hide_ownership'])
    
    return JsonResponse({
        'success': True,
        'hide_ownership': membership.hide_ownership,
        'message': 'Ownership status is now hidden' if membership.hide_ownership else 'Ownership status is now visible',
    })


# ────────────────────────────────────────────────────────────────
# 10. Roster Lock Toggle
# ────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
def toggle_roster_lock(request, slug):
    """
    POST /api/vnext/teams/<slug>/roster/lock/
    
    Toggle manual roster lock. When locked, no roster changes allowed.
    Only team OWNER (creator) can toggle.
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Must be owner or superuser
    is_owner = request.user.is_superuser or team.created_by_id == request.user.id
    if not is_owner:
        return JsonResponse({'error': 'Only the team owner can lock/unlock the roster'}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}
    
    locked = data.get('locked', not team.roster_locked)
    team.roster_locked = bool(locked)
    team.save(update_fields=['roster_locked'])
    
    # Log event
    TeamMembershipEvent.objects.create(
        team=team,
        user=request.user,
        actor=request.user,
        event_type=MembershipEventType.STATUS_CHANGED,
        metadata={'action': 'roster_lock', 'locked': team.roster_locked},
    )
    
    return JsonResponse({
        'success': True,
        'roster_locked': team.roster_locked,
        'message': 'Roster locked' if team.roster_locked else 'Roster unlocked',
    })


# ────────────────────────────────────────────────────────────────
# 11. Leave Team (Self-Removal)
# ────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
@transaction.atomic
def leave_team(request, slug):
    """
    POST /api/vnext/teams/<slug>/leave/
    
    Allow a member to voluntarily leave the team.
    Creator/owner cannot leave (must transfer ownership first or disband).
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Cannot leave if you are the creator
    if team.created_by_id == request.user.id:
        return JsonResponse({
            'error': 'Team creator cannot leave. Transfer ownership first or disband the team.'
        }, status=400)
    
    # Get membership
    membership = team.vnext_memberships.filter(
        user=request.user, status=MembershipStatus.ACTIVE
    ).first()
    if not membership:
        return JsonResponse({'error': 'You are not an active member of this team'}, status=404)
    
    # Update membership
    old_status = membership.status
    membership.status = MembershipStatus.INACTIVE
    membership.left_at = timezone.now()
    membership.left_reason = 'Voluntary departure'
    membership.save(update_fields=['status', 'left_at', 'left_reason'])
    
    # Log event
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=request.user,
        actor=request.user,
        event_type=MembershipEventType.LEFT,
        old_status=old_status,
        new_status=MembershipStatus.INACTIVE,
        metadata={'reason': 'voluntary_departure'},
    )
    
    invalidate_hub_cache(game_id=team.game_id)
    
    # Sync primary_team (clears it if this was user's only team)
    try:
        from apps.organizations.services.profile_sync import sync_primary_team
        sync_primary_team(request.user)
    except Exception:
        pass
    
    return JsonResponse({
        'success': True,
        'message': f'You have left {team.name}',
    })


# ────────────────────────────────────────────────────────────────
# 12. Disband / Delete Team
# ────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
@transaction.atomic
def disband_team(request, slug):
    """
    POST /api/vnext/teams/<slug>/disband/
    
    Permanently disband/delete a team. Only the creator can do this.
    Requires confirmation: body must contain {"confirm": "<team-name>"}.
    All memberships are set to INACTIVE.
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Only creator or superuser
    if not (request.user.is_superuser or team.created_by_id == request.user.id):
        return JsonResponse({'error': 'Only the team creator can disband the team'}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}
    
    confirm_name = (data.get('confirm', '') or '').strip()
    if confirm_name != team.name:
        return JsonResponse({
            'error': f'Confirmation failed. Type the team name "{team.name}" exactly to proceed.'
        }, status=400)
    
    # Deactivate all memberships
    active_memberships = team.vnext_memberships.filter(status=MembershipStatus.ACTIVE)
    for m in active_memberships:
        m.status = MembershipStatus.INACTIVE
        m.left_at = timezone.now()
        m.left_reason = 'Team disbanded'
        m.save(update_fields=['status', 'left_at', 'left_reason'])
        
        TeamMembershipEvent.objects.create(
            membership=m,
            team=team,
            user=m.user,
            actor=request.user,
            event_type=MembershipEventType.REMOVED,
            old_status=MembershipStatus.ACTIVE,
            new_status=MembershipStatus.INACTIVE,
            metadata={'reason': 'team_disbanded'},
        )
    
    # Mark team as disbanded
    team.status = TeamStatus.DISBANDED if hasattr(TeamStatus, 'DISBANDED') else 'DISBANDED'
    team.save(update_fields=['status'])
    
    invalidate_hub_cache(game_id=team.game_id)
    
    return JsonResponse({
        'success': True,
        'message': f'Team "{team.name}" has been disbanded',
        'redirect': '/',
    })


# ────────────────────────────────────────────────────────────────
# 13. Transfer Ownership
# ────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
@transaction.atomic
def transfer_ownership(request, slug):
    """
    POST /api/vnext/teams/<slug>/transfer-ownership/
    
    Transfer team ownership to another active member.
    Requires confirmation: body must contain {"member_id": <int>, "confirm": true}.
    
    - Current owner becomes MANAGER
    - Target member becomes new created_by + OWNER role
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Only creator or superuser
    if not (request.user.is_superuser or team.created_by_id == request.user.id):
        return JsonResponse({'error': 'Only the team creator can transfer ownership'}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}
    
    member_id = data.get('member_id')
    confirm = data.get('confirm', False)
    
    if not member_id:
        return JsonResponse({'error': 'member_id required'}, status=400)
    if not confirm:
        return JsonResponse({'error': 'Confirmation required (set confirm: true)'}, status=400)
    
    # Find target membership
    target = team.vnext_memberships.filter(
        id=member_id, status=MembershipStatus.ACTIVE
    ).select_related('user').first()
    if not target:
        return JsonResponse({'error': 'Target member not found or not active'}, status=404)
    
    # Cannot transfer to yourself
    if target.user_id == request.user.id:
        return JsonResponse({'error': 'Cannot transfer ownership to yourself'}, status=400)
    
    # Get current owner's membership
    owner_membership = team.vnext_memberships.filter(
        user=request.user, status=MembershipStatus.ACTIVE
    ).first()
    
    # Transfer: Update team.created_by
    old_owner = team.created_by
    team.created_by = target.user
    team.save(update_fields=['created_by'])
    
    # Update old owner's role to MANAGER
    if owner_membership:
        owner_membership.role = MembershipRole.MANAGER
        owner_membership.save(update_fields=['role'])
    
    # Update new owner's role to OWNER
    old_target_role = target.role
    target.role = MembershipRole.OWNER
    target.save(update_fields=['role'])
    
    # Log events
    TeamMembershipEvent.objects.create(
        membership=target,
        team=team,
        user=target.user,
        actor=request.user,
        event_type=MembershipEventType.ROLE_CHANGED,
        old_role=old_target_role,
        new_role=MembershipRole.OWNER,
        metadata={'action': 'ownership_transferred', 'from_user': old_owner.username if old_owner else None},
    )
    
    # Sync primary_team for both old and new owner
    try:
        from apps.organizations.services.profile_sync import sync_primary_team
        sync_primary_team(target.user)
        if old_owner:
            sync_primary_team(old_owner)
    except Exception:
        pass
    
    return JsonResponse({
        'success': True,
        'message': f'Ownership transferred to {target.user.username}',
        'new_owner': target.user.username,
    })


# ────────────────────────────────────────────────────────────────
# 14. Invite Link Generation
# ────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
def generate_invite_link(request, slug):
    """
    POST /api/vnext/teams/<slug>/invite-link/
    
    Generate or regenerate a shareable invite code.
    Managers+ can generate. Pass {"regenerate": true} to create a new code.
    """
    team = get_object_or_404(Team, slug=slug)
    
    has_permission, reason = _check_manage_permissions(team, request.user)
    if not has_permission:
        return JsonResponse({'error': reason}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}
    
    regenerate = data.get('regenerate', False)
    
    if not team.invite_code or regenerate:
        team.invite_code = uuid.uuid4().hex[:16]
        team.save(update_fields=['invite_code'])
    
    return JsonResponse({
        'success': True,
        'invite_code': team.invite_code,
        'invite_url': f'/teams/join/{team.invite_code}/',
    })


# ────────────────────────────────────────────────────────────────
# 15. Activity Timeline (History Section)
# ────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@login_required
def activity_timeline(request, slug):
    """
    GET /api/vnext/teams/<slug>/activity/
    
    Returns the team's membership event timeline (audit trail).
    Supports ?page=N (20 per page).
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Must be member
    is_member = (
        request.user.is_superuser
        or team.created_by_id == request.user.id
        or team.vnext_memberships.filter(user=request.user, status=MembershipStatus.ACTIVE).exists()
    )
    if not is_member:
        return JsonResponse({'error': 'Not a team member'}, status=403)
    
    page = int(request.GET.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    events_qs = TeamMembershipEvent.objects.filter(
        team=team
    ).select_related('user', 'actor', 'membership').order_by('-created_at')
    
    total = events_qs.count()
    events = events_qs[offset:offset + per_page]
    
    items = []
    for ev in events:
        items.append({
            'id': ev.id,
            'event_type': ev.event_type,
            'user': ev.user.username if ev.user else None,
            'actor': ev.actor.username if ev.actor else None,
            'old_role': ev.old_role or '',
            'new_role': ev.new_role or '',
            'old_status': ev.old_status or '',
            'new_status': ev.new_status or '',
            'metadata': ev.metadata or {},
            'created_at': ev.created_at.isoformat() if ev.created_at else None,
        })
    
    return JsonResponse({
        'success': True,
        'events': items,
        'page': page,
        'total': total,
        'has_more': (offset + per_page) < total,
    })


# ─── Payment Methods (owner wallet) ───────────────────────────────────
@require_http_methods(["POST"])
@login_required
def update_payment_methods(request, slug):
    """
    Owner-only: update bKash/Nagad/Rocket numbers or bank account details
    on the owner's DeltaCrownWallet.
    """
    team = get_object_or_404(Team, slug=slug)
    membership = TeamMembership.objects.filter(
        team=team, user=request.user, status='ACTIVE'
    ).first()
    if not membership or membership.role != 'OWNER':
        return JsonResponse({'error': 'Only the team owner can manage payment methods.'}, status=403)

    data = json.loads(request.body) if request.body else {}
    method = data.get('method', '')
    action = data.get('action', 'save')  # 'save' or 'remove'

    try:
        from apps.economy.models import DeltaCrownWallet
    except ImportError:
        return JsonResponse({'error': 'Economy module not available.'}, status=503)

    profile = getattr(request.user, 'profile', None)
    if not profile:
        return JsonResponse({'error': 'User profile not found.'}, status=404)

    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)

    MOBILE_METHODS = {'bkash': 'bkash_number', 'nagad': 'nagad_number', 'rocket': 'rocket_number'}

    if method in MOBILE_METHODS:
        field = MOBILE_METHODS[method]
        if action == 'remove':
            setattr(wallet, field, '')
        else:
            value = (data.get('value') or '').strip()
            # Basic BD phone validation: 11 digits starting with 01
            import re
            if value and not re.match(r'^01\d{9}$', value):
                return JsonResponse({
                    'error': f'Invalid phone number. Must be 11 digits starting with 01 (e.g. 01712345678).'
                }, status=400)
            setattr(wallet, field, value)
        wallet.save(update_fields=[field])

        display = ''
        if getattr(wallet, field):
            num = getattr(wallet, field)
            display = '*' * (len(num) - 4) + num[-4:]
        return JsonResponse({
            'success': True,
            'method': method,
            'active': bool(getattr(wallet, field)),
            'masked': display,
            'message': f'{method.title()} {"removed" if action == "remove" else "updated"} successfully.',
        })

    elif method == 'bank':
        if action == 'remove':
            wallet.bank_account_name = ''
            wallet.bank_account_number = ''
            wallet.bank_name = ''
            wallet.bank_branch = ''
            wallet.save(update_fields=['bank_account_name', 'bank_account_number', 'bank_name', 'bank_branch'])
            return JsonResponse({
                'success': True,
                'method': 'bank',
                'active': False,
                'masked': '',
                'message': 'Bank account removed.',
            })
        else:
            wallet.bank_account_name = (data.get('account_name') or '').strip()[:100]
            wallet.bank_account_number = (data.get('account_number') or '').strip()[:30]
            wallet.bank_name = (data.get('bank_name') or '').strip()[:100]
            wallet.bank_branch = (data.get('branch') or '').strip()[:100]
            wallet.save(update_fields=['bank_account_name', 'bank_account_number', 'bank_name', 'bank_branch'])

            num = wallet.bank_account_number
            masked = ('*' * (len(num) - 4) + num[-4:]) if num and len(num) >= 5 else num
            return JsonResponse({
                'success': True,
                'method': 'bank',
                'active': bool(wallet.bank_account_number),
                'masked': f'{wallet.bank_name} · {masked}' if wallet.bank_name else masked,
                'message': 'Bank account updated.',
            })

    return JsonResponse({'error': f'Unknown payment method: {method}'}, status=400)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 16. Discord Integration API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@login_required
@require_http_methods(["GET"])
def discord_config(request, slug):
    """GET /api/vnext/teams/<slug>/discord/ — current Discord config."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    return JsonResponse({
        'discord_guild_id': team.discord_guild_id,
        'discord_announcement_channel_id': team.discord_announcement_channel_id,
        'discord_chat_channel_id': team.discord_chat_channel_id,
        'discord_voice_channel_id': team.discord_voice_channel_id,
        'discord_webhook_url': team.discord_webhook_url,
        'discord_url': team.discord_url,
        'discord_bot_active': team.discord_bot_active,
    })


@login_required
@require_http_methods(["POST"])
def discord_config_save(request, slug):
    """POST /api/vnext/teams/<slug>/discord/ — save Discord config.

    Validates snowflake IDs (numeric, ≤20 chars).
    Fires validate_discord_bot_presence task if guild_id is provided.
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def _validate_snowflake(val, field_name):
        if not val:
            return ''
        val = str(val).strip()
        if not val.isdigit() or len(val) > 20:
            raise ValueError(f'{field_name} must be a numeric Discord ID (up to 20 digits)')
        return val

    try:
        guild_id = _validate_snowflake(data.get('discord_guild_id', ''), 'Guild ID')
        ann_ch = _validate_snowflake(data.get('discord_announcement_channel_id', ''), 'Announcement Channel ID')
        chat_ch = _validate_snowflake(data.get('discord_chat_channel_id', ''), 'Chat Channel ID')
        voice_ch = _validate_snowflake(data.get('discord_voice_channel_id', ''), 'Voice Channel ID')
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # Update fields
    update_fields = []
    for attr, val in [
        ('discord_guild_id', guild_id),
        ('discord_announcement_channel_id', ann_ch),
        ('discord_chat_channel_id', chat_ch),
        ('discord_voice_channel_id', voice_ch),
    ]:
        setattr(team, attr, val)
        update_fields.append(attr)

    # Also allow updating the invite link / webhook URL
    discord_url = (data.get('discord_url') or '').strip()[:300]
    webhook_url = (data.get('discord_webhook_url') or '').strip()[:300]
    if discord_url != team.discord_url:
        team.discord_url = discord_url
        update_fields.append('discord_url')
    if webhook_url != team.discord_webhook_url:
        team.discord_webhook_url = webhook_url
        update_fields.append('discord_webhook_url')

    team.save(update_fields=update_fields)

    # Fire async validation of bot presence
    if guild_id:
        from apps.organizations.tasks.discord_sync import validate_discord_bot_presence
        validate_discord_bot_presence.delay(team.pk)

    return JsonResponse({
        'success': True,
        'discord_bot_active': team.discord_bot_active,
        'message': 'Discord configuration saved. Bot presence is being verified…',
    })


@login_required
@require_http_methods(["GET"])
def discord_chat_messages(request, slug):
    """GET /api/vnext/teams/<slug>/discord/chat/ — recent chat messages.

    Query params:
      ?after=<id>  — only messages with pk > <id> (for polling)
      ?limit=50    — max messages to return (default 50, max 200)
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)

    # Any team member can read chat
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    is_member = team.vnext_memberships.filter(
        user=request.user, status='ACTIVE',
    ).exists()
    is_manager = team.created_by_id == request.user.id or request.user.is_superuser
    if not is_member and not is_manager:
        return JsonResponse({'error': 'Team members only'}, status=403)

    from apps.organizations.models.discord_sync import DiscordChatMessage

    after = request.GET.get('after')
    limit = min(int(request.GET.get('limit', 50)), 200)

    qs = DiscordChatMessage.objects.filter(team=team)
    if after:
        try:
            qs = qs.filter(pk__gt=int(after))
        except (ValueError, TypeError):
            pass

    messages = list(
        qs.order_by('-created_at')[:limit]
        .values(
            'id', 'content', 'direction',
            'author_discord_name', 'author_user__username',
            'created_at',
        )
    )
    messages.reverse()  # oldest first for display

    return JsonResponse({
        'messages': [
            {
                'id': m['id'],
                'content': m['content'],
                'direction': m['direction'],
                'author': m['author_user__username'] or m['author_discord_name'] or 'Unknown',
                'source': 'discord' if m['direction'] == 'inbound' else 'web',
                'timestamp': m['created_at'].isoformat(),
            }
            for m in messages
        ],
    })


@login_required
@require_http_methods(["POST"])
def discord_chat_send(request, slug):
    """POST /api/vnext/teams/<slug>/discord/chat/send/ — send a chat message.

    Body: { "content": "Hello team!" }

    The message is saved to DB immediately (for instant web display) and
    then a Celery task pushes it to Discord asynchronously.
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    is_member = team.vnext_memberships.filter(
        user=request.user, status='ACTIVE',
    ).exists()
    is_manager = team.created_by_id == request.user.id or request.user.is_superuser
    if not is_member and not is_manager:
        return JsonResponse({'error': 'Team members only'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Message content is required'}, status=400)
    if len(content) > 2000:
        return JsonResponse({'error': 'Message too long (max 2000 characters)'}, status=400)

    from apps.organizations.models.discord_sync import DiscordChatMessage

    msg = DiscordChatMessage.objects.create(
        team=team,
        author_user=request.user,
        content=content,
        direction='outbound',
        discord_channel_id=team.discord_chat_channel_id or '',
    )

    # Dispatch to Discord asynchronously
    if team.discord_bot_active and team.discord_chat_channel_id:
        from apps.organizations.tasks.discord_sync import send_discord_chat_message
        send_discord_chat_message.delay(team.pk, msg.pk)

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.pk,
            'content': msg.content,
            'author': request.user.username,
            'source': 'web',
            'timestamp': msg.created_at.isoformat(),
        },
    })


@login_required
@require_http_methods(["GET"])
def discord_voice_link(request, slug):
    """GET /api/vnext/teams/<slug>/discord/voice/ — voice channel deep link.

    Returns a Discord deep link that opens the voice channel directly.
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)

    if not team.discord_guild_id or not team.discord_voice_channel_id:
        return JsonResponse({
            'error': 'Voice channel not configured for this team',
        }, status=404)

    # Discord deep link format
    deep_link = f'https://discord.com/channels/{team.discord_guild_id}/{team.discord_voice_channel_id}'

    return JsonResponse({
        'voice_link': deep_link,
        'guild_id': team.discord_guild_id,
        'channel_id': team.discord_voice_channel_id,
    })


@login_required
@require_http_methods(["POST"])
def discord_test_webhook(request, slug):
    """POST /api/vnext/teams/<slug>/discord/test-webhook/

    Sends a quick test message through the team's configured webhook
    so captains can verify it works before going live.
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    webhook_url = team.discord_webhook_url
    if not webhook_url:
        return JsonResponse({'error': 'No webhook URL configured for this team.'}, status=400)

    import requests as http_requests
    try:
        payload = {
            'content': '✅ **DeltaCrown webhook test** — your Discord integration is working!',
            'username': f'{team.name} via DeltaCrown',
        }
        resp = http_requests.post(webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
        return JsonResponse({
            'success': True,
            'message': 'Test message sent to Discord! Check your channel.',
        })
    except http_requests.RequestException as exc:
        return JsonResponse({
            'error': f'Webhook test failed: {exc}',
        }, status=502)

