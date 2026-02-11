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

from django.conf import settings
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
    - Team COACH role
    - Organization CEO
    - Organization staff (CEO/MANAGER) via OrganizationMembership
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
    
    # Check organization staff (CEO, MANAGER) via OrganizationMembership
    if team.organization:
        if team.organization.ceo_id == user.id:
            return True, None
        from apps.organizations.models import OrganizationMembership
        if OrganizationMembership.objects.filter(
            organization=team.organization,
            user=user,
            role__in=['CEO', 'MANAGER'],
        ).exists():
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
    
    # Platform rule: OWNER role cannot be *assigned* to someone who isn't already OWNER
    # But if the member already IS the owner, allow edits to go through (role stays the same)
    if new_role == MembershipRole.OWNER and membership.role != MembershipRole.OWNER:
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
    
    # Parse params — support both JSON body (toggles) and form data (profile form)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}
    
    # Only update fields that are explicitly present in the request payload.
    # This prevents a single-field AJAX save from wiping out unrelated fields.
    updated_fields = []
    
    # String fields: only touch if the key is present in data
    FIELD_MAP = {
        'tagline': ('tagline', 140),
        'description': ('description', 500),
        'twitter': ('twitter_url', None),
        'discord': ('discord_url', None),
        'website': ('website_url', None),
        'playstyle': ('playstyle', 50),
        'playpace': ('playpace', 50),
        'playfocus': ('playfocus', 50),
    }
    
    for param_key, (model_field, max_len) in FIELD_MAP.items():
        if param_key in data:
            val = str(data[param_key]).strip() if data[param_key] is not None else ''
            if max_len and len(val) > max_len:
                return JsonResponse({'error': f'{param_key} must be {max_len} characters or less'}, status=400)
            if hasattr(team, model_field):
                setattr(team, model_field, val)
                updated_fields.append(model_field)
    
    # Platform (validated)
    if 'platform' in data:
        platform = str(data['platform']).strip()
        VALID_PLATFORMS = ('PC', 'Mobile', 'Console', 'Cross-Platform')
        if platform and platform not in VALID_PLATFORMS:
            return JsonResponse({'error': f'Invalid platform. Must be one of: {", ".join(VALID_PLATFORMS)}'}, status=400)
        if platform and hasattr(team, 'platform'):
            team.platform = platform
            updated_fields.append('platform')
    
    # Boolean toggle fields (sent as JSON from ManageHQ.toggleSetting)
    if 'is_recruiting' in data:
        team.is_recruiting = bool(data['is_recruiting'])
        updated_fields.append('is_recruiting')
    if 'visibility' in data and data['visibility'] in ('PUBLIC', 'PRIVATE', 'UNLISTED'):
        team.visibility = data['visibility']
        updated_fields.append('visibility')
    if 'is_temporary' in data:
        team.is_temporary = bool(data['is_temporary'])
        updated_fields.append('is_temporary')
    
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
    
    Returns the team's combined activity timeline (audit trail + activity log).
    Supports ?page=N (20 per page) and ?filter=TYPE.
    Includes is_pinned for admin pin/unpin controls.
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
    filter_type = request.GET.get('filter', '')
    per_page = 20
    offset = (page - 1) * per_page
    
    # Merge membership events + activity logs into unified timeline
    combined = []
    
    # Membership events
    events_qs = TeamMembershipEvent.objects.filter(
        team=team
    ).select_related('user', 'actor', 'membership').order_by('-created_at')
    
    if filter_type == 'roster':
        events_qs = events_qs.filter(event_type__in=['JOINED', 'REMOVED', 'ROLE_CHANGED', 'LEFT'])
    elif filter_type == 'settings' or filter_type == 'profile':
        events_qs = events_qs.none()

    for ev in events_qs[:50]:
        combined.append({
            'id': f'me-{ev.id}',
            'source': 'membership',
            'event_type': ev.event_type,
            'description': f'{ev.user.username if ev.user else "?"} — {ev.get_event_type_display() if hasattr(ev, "get_event_type_display") else ev.event_type}',
            'user': ev.user.username if ev.user else None,
            'actor': ev.actor.username if ev.actor else None,
            'old_role': ev.old_role or '',
            'new_role': ev.new_role or '',
            'old_status': ev.old_status or '',
            'new_status': ev.new_status or '',
            'metadata': ev.metadata or {},
            'timestamp': ev.created_at.isoformat() if ev.created_at else None,
            'is_pinned': False,
            'can_pin': False,
        })
    
    # Activity log entries
    from apps.organizations.models import TeamActivityLog
    activity_qs = TeamActivityLog.objects.filter(team=team).order_by('-timestamp')
    
    if filter_type == 'roster':
        activity_qs = activity_qs.filter(action_type__in=['ROSTER_ADD', 'ROSTER_REMOVE', 'ROSTER_UPDATE'])
    elif filter_type == 'tournament':
        activity_qs = activity_qs.filter(action_type='TOURNAMENT_REGISTER')
    elif filter_type == 'settings':
        activity_qs = activity_qs.filter(action_type='UPDATE')
    elif filter_type == 'profile':
        activity_qs = activity_qs.filter(action_type='UPDATE')
    
    for act in activity_qs[:50]:
        combined.append({
            'id': f'al-{act.pk}',
            'activity_id': act.pk,
            'source': 'activity_log',
            'event_type': act.action_type,
            'description': act.description,
            'user': act.actor_username,
            'actor': act.actor_username,
            'metadata': act.metadata or {},
            'timestamp': act.timestamp.isoformat() if act.timestamp else None,
            'is_pinned': act.is_pinned,
            'is_milestone': act.is_milestone,
            'can_pin': True,
        })
    
    # Sort by timestamp descending
    combined.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
    total = len(combined)
    page_items = combined[offset:offset + per_page]
    
    return JsonResponse({
        'success': True,
        'events': page_items,
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

    # Check Redis cache first for instant bot status (set by bot on_ready)
    bot_active = team.discord_bot_active
    if team.discord_guild_id and not bot_active:
        try:
            from django.core.cache import cache
            cached = cache.get(f'discord_bot_online:{team.discord_guild_id}')
            if cached:
                bot_active = True
                # Update DB in background so future loads are fast
                Team.objects.filter(pk=team.pk).update(discord_bot_active=True)
        except Exception:
            pass

    return JsonResponse({
        'discord_guild_id': team.discord_guild_id,
        'discord_announcement_channel_id': team.discord_announcement_channel_id,
        'discord_chat_channel_id': team.discord_chat_channel_id,
        'discord_voice_channel_id': team.discord_voice_channel_id,
        'discord_webhook_url_masked': '••••••••' if team.discord_webhook_url else '',
        'discord_url': team.discord_url,
        'discord_bot_active': bot_active,
        'discord_bot_invite_url': (
            f'https://discord.com/api/oauth2/authorize?client_id={settings.DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands'
            if settings.DISCORD_CLIENT_ID else ''
        ),
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
        captain_role = _validate_snowflake(data.get('discord_captain_role_id', ''), 'Captain Role ID')
        manager_role = _validate_snowflake(data.get('discord_manager_role_id', ''), 'Manager Role ID')
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # Update fields
    update_fields = []
    for attr, val in [
        ('discord_guild_id', guild_id),
        ('discord_announcement_channel_id', ann_ch),
        ('discord_chat_channel_id', chat_ch),
        ('discord_voice_channel_id', voice_ch),
        ('discord_captain_role_id', captain_role),
        ('discord_manager_role_id', manager_role),
    ]:
        setattr(team, attr, val)
        update_fields.append(attr)

    # Also allow updating the invite link / webhook URL
    discord_url = (data.get('discord_url') or '').strip()[:300]
    webhook_url = (data.get('discord_webhook_url') or '').strip()[:300]

    # Validate Community Invite URL (must be discord.gg/ or discord.com/invite/)
    if discord_url and not re.match(
        r'^https://(discord\.gg|discord\.com/invite)/[a-zA-Z0-9\-]+', discord_url
    ):
        return JsonResponse(
            {'error': 'Community Invite URL must be a discord.gg/ or discord.com/invite/ link'},
            status=400,
        )

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
            'author_user_id',
            'author_user__profile__display_name',
            'author_user__profile__avatar',
            'author_discord_id',
            'created_at',
        )
    )
    messages.reverse()  # oldest first for display

    def _build_msg(m):
        # Resolve best display name
        display = (
            m['author_user__profile__display_name']
            or m['author_user__username']
            or m['author_discord_name']
            or 'Unknown'
        )
        # Resolve avatar
        avatar = None
        if m.get('author_user__profile__avatar'):
            avatar = settings.MEDIA_URL + m['author_user__profile__avatar']
        elif m.get('author_discord_id'):
            # No linked profile — could build Discord CDN avatar later
            pass
        return {
            'id': m['id'],
            'content': m['content'],
            'direction': m['direction'],
            'author': display,
            'author_id': m.get('author_user_id'),
            'avatar_url': avatar,
            'source': 'discord' if m['direction'] == 'inbound' else 'web',
            'timestamp': m['created_at'].isoformat(),
        }

    return JsonResponse({
        'messages': [_build_msg(m) for m in messages],
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

    # Dispatch to Discord asynchronously (webhook OR bot — task decides)
    if team.discord_webhook_url or (team.discord_bot_active and team.discord_chat_channel_id):
        from apps.organizations.tasks.discord_sync import send_discord_chat_message
        send_discord_chat_message.delay(team.pk, msg.pk)

    # Resolve avatar + display_name for the sender
    avatar_url = None
    display_name = request.user.username
    try:
        profile = request.user.profile
        if profile.avatar:
            avatar_url = settings.MEDIA_URL + str(profile.avatar)
        if profile.display_name:
            display_name = profile.display_name
    except Exception:
        pass

    msg_payload = {
        'id': msg.pk,
        'content': msg.content,
        'author': display_name,
        'author_id': request.user.id,
        'avatar_url': avatar_url,
        'source': 'web',
        'timestamp': msg.created_at.isoformat(),
    }

    # Push to WebSocket group so other connected clients see it instantly
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(
                f'team_{team.pk}',
                {'type': 'chat.message', 'payload': msg_payload},
            )
    except Exception:
        pass  # WebSocket push is best-effort

    return JsonResponse({
        'success': True,
        'message': msg_payload,
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


# ═══════════════════════════════════════════════════════════════════════
# COMMUNITY & MEDIA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@login_required
@require_http_methods(["GET"])
def community_data(request, slug):
    """GET /api/vnext/teams/<slug>/community/ — aggregated feed data."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    is_member = team.vnext_memberships.filter(
        user=request.user, status='ACTIVE',
    ).exists()
    is_manager = team.created_by_id == request.user.id or request.user.is_superuser
    if not is_member and not is_manager:
        return JsonResponse({'error': 'Team members only'}, status=403)

    from apps.organizations.models import TeamAnnouncement, TeamMedia, TeamHighlight
    from django.utils.timesince import timesince

    posts = list(
        TeamAnnouncement.objects.filter(team=team)
        .select_related('author')
        .order_by('-pinned', '-created_at')[:30]
        .values('id', 'content', 'announcement_type', 'pinned',
                'author__username', 'created_at')
    )
    gallery = list(
        TeamMedia.objects.filter(team=team)
        .order_by('-created_at')[:50]
        .values('id', 'title', 'category', 'file', 'file_url', 'created_at')
    )
    highlights = list(
        TeamHighlight.objects.filter(team=team)
        .order_by('-created_at')[:20]
        .values('id', 'title', 'url', 'description', 'thumbnail_url', 'created_at')
    )

    now = timezone.now()
    return JsonResponse({
        'posts': [{
            'id': p['id'],
            'content': p['content'],
            'type': p['announcement_type'],
            'pinned': p['pinned'],
            'author': p['author__username'] or 'Team',
            'time_ago': timesince(p['created_at'], now) + ' ago' if p['created_at'] else '',
        } for p in posts],
        'gallery': [{
            'id': g['id'],
            'title': g['title'],
            'category': g['category'],
            'url': (settings.MEDIA_URL + g['file']) if g['file'] else (g['file_url'] or ''),
        } for g in gallery],
        'highlights': [{
            'id': h['id'],
            'title': h['title'],
            'url': h['url'],
            'description': h['description'],
            'thumbnail_url': h['thumbnail_url'],
        } for h in highlights],
    })


@login_required
@require_http_methods(["POST"])
def community_create_post(request, slug):
    """POST /api/vnext/teams/<slug>/community/posts/ — create a team post/announcement."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Content is required'}, status=400)
    if len(content) > 2000:
        return JsonResponse({'error': 'Content too long (max 2000 characters)'}, status=400)

    post_type = data.get('type', 'update')
    valid_types = [c[0] for c in [
        ('general', ''), ('announcement', ''), ('update', ''),
        ('alert', ''), ('match_result', ''), ('roster_change', ''),
        ('matchday', ''),
    ]]
    if post_type == 'matchday':
        post_type = 'match_result'
    if post_type not in valid_types:
        post_type = 'update'

    from apps.organizations.models import TeamAnnouncement
    post = TeamAnnouncement.objects.create(
        team=team,
        author=request.user,
        content=content,
        announcement_type=post_type,
        pinned=bool(data.get('pinned', False)),
    )
    # post_save signal will fire Discord sync if announcement type

    return JsonResponse({
        'success': True,
        'message': 'Post published!',
        'post': {
            'id': post.pk,
            'content': post.content,
            'type': post.announcement_type,
            'pinned': post.pinned,
            'author': request.user.username,
        },
    })


@login_required
@require_http_methods(["POST"])
def community_upload_media(request, slug):
    """POST /api/vnext/teams/<slug>/community/media/ — upload gallery media."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    title = (request.POST.get('title') or '').strip() or 'Untitled'
    category = request.POST.get('category', 'general')
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    # Limit to 10MB
    if file.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (max 10MB)'}, status=400)

    from apps.organizations.models import TeamMedia
    media = TeamMedia.objects.create(
        team=team,
        uploaded_by=request.user,
        title=title[:200],
        category=category,
        file=file,
        file_size=file.size,
        file_type='image' if file.content_type.startswith('image') else 'video',
    )

    return JsonResponse({
        'success': True,
        'message': 'Media uploaded!',
        'media': {
            'id': media.pk,
            'title': media.title,
            'url': media.url,
            'category': media.category,
        },
    })


@login_required
@require_http_methods(["POST"])
def community_add_highlight(request, slug):
    """POST /api/vnext/teams/<slug>/community/highlights/ — add a highlight reel."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = (data.get('title') or '').strip()
    url = (data.get('url') or '').strip()
    if not title or not url:
        return JsonResponse({'error': 'Title and URL are required'}, status=400)

    from apps.organizations.models import TeamHighlight
    highlight = TeamHighlight.objects.create(
        team=team,
        added_by=request.user,
        title=title[:200],
        url=url[:500],
        description=(data.get('description') or '')[:500],
    )

    return JsonResponse({
        'success': True,
        'message': 'Highlight added!',
        'highlight': {
            'id': highlight.pk,
            'title': highlight.title,
            'url': highlight.url,
        },
    })


# ============================================================================
# JOIN REQUESTS — User-initiated team applications
# ============================================================================

@login_required
@require_http_methods(["POST"])
def apply_to_team(request, slug):
    """POST /api/vnext/teams/<slug>/apply/ — submit a join request.

    Body: { "message": "optional intro message" }
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    # Can't apply if already a member
    if team.vnext_memberships.filter(user=request.user, status='ACTIVE').exists():
        return JsonResponse({'error': 'You are already a member of this team'}, status=400)

    # Team must be recruiting
    if not getattr(team, 'is_recruiting', True):
        return JsonResponse({'error': 'This team is not currently recruiting'}, status=400)

    # Roster must not be locked
    if team.roster_locked:
        return JsonResponse({'error': 'Team roster is currently locked'}, status=400)

    from apps.organizations.models.join_request import TeamJoinRequest

    # Check for existing pending request
    if TeamJoinRequest.objects.filter(team=team, user=request.user, status='PENDING').exists():
        return JsonResponse({'error': 'You already have a pending application'}, status=400)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    msg = (data.get('message') or '').strip()[:500]

    jr = TeamJoinRequest.objects.create(
        team=team,
        user=request.user,
        message=msg,
    )

    return JsonResponse({
        'success': True,
        'message': 'Application submitted! The team will review it shortly.',
        'request_id': jr.pk,
    })


@login_required
@require_http_methods(["POST"])
def withdraw_application(request, slug):
    """POST /api/vnext/teams/<slug>/apply/withdraw/ — withdraw own pending request."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    from apps.organizations.models.join_request import TeamJoinRequest

    jr = TeamJoinRequest.objects.filter(
        team=team, user=request.user, status='PENDING',
    ).first()
    if not jr:
        return JsonResponse({'error': 'No pending application found'}, status=404)

    jr.status = 'WITHDRAWN'
    jr.save(update_fields=['status', 'updated_at'])

    return JsonResponse({'success': True, 'message': 'Application withdrawn.'})


@login_required
@require_http_methods(["GET"])
def list_join_requests(request, slug):
    """GET /api/vnext/teams/<slug>/join-requests/ — list pending join requests (admin only)."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.join_request import TeamJoinRequest

    requests_qs = TeamJoinRequest.objects.filter(
        team=team, status__in=['PENDING', 'TRYOUT_SCHEDULED', 'TRYOUT_COMPLETED', 'OFFER_SENT'],
    ).select_related('user', 'user__profile').order_by('-created_at')

    items = []
    for jr in requests_qs:
        avatar = None
        display_name = jr.user.username
        try:
            if jr.user.profile.avatar:
                avatar = settings.MEDIA_URL + str(jr.user.profile.avatar)
            if jr.user.profile.display_name:
                display_name = jr.user.profile.display_name
        except Exception:
            pass
        items.append({
            'id': jr.pk,
            'user_id': jr.user_id,
            'username': jr.user.username,
            'display_name': display_name,
            'avatar_url': avatar,
            'message': jr.message,
            'status': jr.status,
            'applied_position': jr.applied_position,
            'tryout_date': jr.tryout_date.isoformat() if jr.tryout_date else None,
            'tryout_notes': jr.tryout_notes,
            'created_at': jr.created_at.isoformat(),
        })

    return JsonResponse({
        'requests': items,
        'count': len(items),
        'total_count': TeamJoinRequest.objects.filter(team=team).count(),
        'accepted_count': TeamJoinRequest.objects.filter(team=team, status='ACCEPTED').count(),
    })


@login_required
@require_http_methods(["POST"])
def review_join_request(request, slug, request_id):
    """POST /api/vnext/teams/<slug>/join-requests/<id>/<action>/ — accept or decline.

    Body: { "action": "accept" | "decline" }
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.join_request import TeamJoinRequest
    from django.utils import timezone

    jr = get_object_or_404(TeamJoinRequest, pk=request_id, team=team, status='PENDING')

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    action = (data.get('action') or '').lower()
    if action not in ('accept', 'decline'):
        return JsonResponse({'error': 'action must be "accept" or "decline"'}, status=400)

    if action == 'accept':
        # Create membership
        from apps.organizations.models import TeamMembership
        from apps.organizations.choices import MembershipRole

        if team.vnext_memberships.filter(user=jr.user, status='ACTIVE').exists():
            jr.status = 'ACCEPTED'
            jr.reviewed_by = request.user
            jr.reviewed_at = timezone.now()
            jr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
            return JsonResponse({'success': True, 'message': 'User is already a member.'})

        TeamMembership.objects.create(
            team=team,
            user=jr.user,
            role=MembershipRole.PLAYER,
            status='ACTIVE',
            invited_by=request.user,
        )
        jr.status = 'ACCEPTED'
        jr.reviewed_by = request.user
        jr.reviewed_at = timezone.now()
        jr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
        return JsonResponse({'success': True, 'message': f'{jr.user.username} has been added to the team!'})

    else:  # decline
        jr.status = 'DECLINED'
        jr.reviewed_by = request.user
        jr.reviewed_at = timezone.now()
        jr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Application declined.'})


# ============================================================================
# RECRUITMENT SETTINGS — Job Post Builder (Point 1A)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def recruitment_positions(request, slug):
    """GET /api/vnext/teams/<slug>/recruitment/positions/ — list open positions."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentPosition
    positions = RecruitmentPosition.objects.filter(team=team).order_by('sort_order', '-created_at')

    return JsonResponse({
        'positions': [
            {
                'id': p.pk,
                'title': p.title,
                'role_category': getattr(p, 'role_category', ''),
                'rank_requirement': getattr(p, 'rank_requirement', ''),
                'region': getattr(p, 'region', ''),
                'platform': getattr(p, 'platform', ''),
                'short_pitch': getattr(p, 'short_pitch', ''),
                'cross_post_community': getattr(p, 'cross_post_community', False),
                'description': p.description,
                'is_active': p.is_active,
                'sort_order': p.sort_order,
            }
            for p in positions
        ],
        'team_defaults': {
            'region': team.region or '',
            'platform': team.platform or '',
        },
        'role_choices': [
            {'value': c[0], 'label': c[1]}
            for c in RecruitmentPosition.RoleCategory.choices
        ],
    })


@login_required
@require_http_methods(["POST"])
def recruitment_position_save(request, slug):
    """POST /api/vnext/teams/<slug>/recruitment/positions/save/ — create or update position."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentPosition

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = (data.get('title') or '').strip()
    if not title or len(title) > 60:
        return JsonResponse({'error': 'Title is required (max 60 chars)'}, status=400)

    description = (data.get('description') or '').strip()[:200]
    role_category = (data.get('role_category') or '').strip()[:20]
    rank_requirement = (data.get('rank_requirement') or '').strip()[:60]
    region = (data.get('region') or '').strip()[:30]
    platform = (data.get('platform') or '').strip()[:30]
    short_pitch = (data.get('short_pitch') or '').strip()[:140]
    cross_post = bool(data.get('cross_post_community', False))
    position_id = data.get('id')

    save_fields = {
        'title': title,
        'description': description,
        'role_category': role_category,
        'rank_requirement': rank_requirement,
        'region': region,
        'platform': platform,
        'short_pitch': short_pitch,
        'cross_post_community': cross_post,
        'is_active': data.get('is_active', True),
    }

    if position_id:
        pos = get_object_or_404(RecruitmentPosition, pk=position_id, team=team)
        for k, v in save_fields.items():
            setattr(pos, k, v)
        pos.save(update_fields=list(save_fields.keys()))
        return JsonResponse({'success': True, 'id': pos.pk, 'message': 'Position updated.'})

    # Check limit (max 10 active positions)
    active_count = RecruitmentPosition.objects.filter(team=team, is_active=True).count()
    if active_count >= 10:
        return JsonResponse({'error': 'Maximum 10 active positions allowed.'}, status=400)

    pos = RecruitmentPosition.objects.create(
        team=team,
        sort_order=active_count,
        **save_fields,
    )
    return JsonResponse({'success': True, 'id': pos.pk, 'message': 'Position added.'})


@login_required
@require_http_methods(["POST"])
def recruitment_position_delete(request, slug, position_id):
    """POST /api/vnext/teams/<slug>/recruitment/positions/<id>/delete/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentPosition
    pos = get_object_or_404(RecruitmentPosition, pk=position_id, team=team)
    pos.delete()
    return JsonResponse({'success': True, 'message': 'Position removed.'})


@login_required
@require_http_methods(["GET"])
def recruitment_requirements(request, slug):
    """GET /api/vnext/teams/<slug>/recruitment/requirements/ — list requirements."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentRequirement
    reqs = RecruitmentRequirement.objects.filter(team=team).order_by('sort_order', '-created_at')

    return JsonResponse({
        'requirements': [
            {'id': r.pk, 'label': r.label, 'value': r.value, 'sort_order': r.sort_order}
            for r in reqs
        ],
    })


@login_required
@require_http_methods(["POST"])
def recruitment_requirement_save(request, slug):
    """POST /api/vnext/teams/<slug>/recruitment/requirements/save/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentRequirement

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    label = (data.get('label') or '').strip()
    value = (data.get('value') or '').strip()
    if not label or not value:
        return JsonResponse({'error': 'Both label and value are required.'}, status=400)

    req_id = data.get('id')
    if req_id:
        req = get_object_or_404(RecruitmentRequirement, pk=req_id, team=team)
        req.label = label[:40]
        req.value = value[:100]
        req.save(update_fields=['label', 'value'])
        return JsonResponse({'success': True, 'id': req.pk, 'message': 'Requirement updated.'})

    count = RecruitmentRequirement.objects.filter(team=team).count()
    if count >= 15:
        return JsonResponse({'error': 'Maximum 15 requirements allowed.'}, status=400)

    req = RecruitmentRequirement.objects.create(
        team=team, label=label[:40], value=value[:100], sort_order=count,
    )
    return JsonResponse({'success': True, 'id': req.pk, 'message': 'Requirement added.'})


@login_required
@require_http_methods(["POST"])
def recruitment_requirement_delete(request, slug, requirement_id):
    """POST /api/vnext/teams/<slug>/recruitment/requirements/<id>/delete/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.recruitment import RecruitmentRequirement
    req = get_object_or_404(RecruitmentRequirement, pk=requirement_id, team=team)
    req.delete()
    return JsonResponse({'success': True, 'message': 'Requirement removed.'})


# ============================================================================
# TRYOUT WORKFLOW — Schedule / Complete / Offer (Point 1B)
# ============================================================================

@login_required
@require_http_methods(["POST"])
def schedule_tryout(request, slug, request_id):
    """POST /api/vnext/teams/<slug>/join-requests/<id>/tryout/schedule/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.join_request import TeamJoinRequest
    from datetime import datetime

    jr = get_object_or_404(TeamJoinRequest, pk=request_id, team=team, status='PENDING')

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    tryout_date_str = data.get('tryout_date')
    if not tryout_date_str:
        return JsonResponse({'error': 'tryout_date is required (ISO format)'}, status=400)

    try:
        tryout_date = datetime.fromisoformat(tryout_date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format. Use ISO 8601.'}, status=400)

    position = (data.get('position') or '').strip()[:60]
    notes = (data.get('notes') or '').strip()[:1000]

    jr.status = 'TRYOUT_SCHEDULED'
    jr.tryout_date = tryout_date
    jr.tryout_notes = notes
    if position:
        jr.applied_position = position
    jr.reviewed_by = request.user
    jr.save(update_fields=['status', 'tryout_date', 'tryout_notes', 'applied_position', 'reviewed_by', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': f'Tryout scheduled for {jr.user.username}.',
        'tryout_date': jr.tryout_date.isoformat(),
    })


@login_required
@require_http_methods(["POST"])
def advance_tryout(request, slug, request_id):
    """POST /api/vnext/teams/<slug>/join-requests/<id>/tryout/advance/

    Advance through tryout lifecycle:
      TRYOUT_SCHEDULED → TRYOUT_COMPLETED
      TRYOUT_COMPLETED → OFFER_SENT
      OFFER_SENT → ACCEPTED (creates membership)
    """
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.join_request import TeamJoinRequest

    jr = get_object_or_404(TeamJoinRequest, pk=request_id, team=team)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    notes = (data.get('notes') or '').strip()
    if notes:
        jr.tryout_notes = notes[:1000]

    TRANSITIONS = {
        'TRYOUT_SCHEDULED': ('TRYOUT_COMPLETED', 'Tryout completed.'),
        'TRYOUT_COMPLETED': ('OFFER_SENT', 'Offer sent.'),
    }

    if jr.status == 'OFFER_SENT':
        # Final step — sign the player (create membership)
        from apps.organizations.models import TeamMembership
        if not team.vnext_memberships.filter(user=jr.user, status='ACTIVE').exists():
            TeamMembership.objects.create(
                team=team,
                user=jr.user,
                role=MembershipRole.PLAYER,
                status='ACTIVE',
                invited_by=request.user,
            )
        jr.status = 'ACCEPTED'
        jr.reviewed_by = request.user
        jr.reviewed_at = timezone.now()
        jr.save(update_fields=['status', 'tryout_notes', 'reviewed_by', 'reviewed_at', 'updated_at'])
        return JsonResponse({'success': True, 'status': 'ACCEPTED', 'message': f'{jr.user.username} signed!'})

    if jr.status not in TRANSITIONS:
        return JsonResponse({'error': f'Cannot advance from status {jr.status}'}, status=400)

    next_status, msg = TRANSITIONS[jr.status]
    jr.status = next_status
    jr.reviewed_by = request.user
    jr.save(update_fields=['status', 'tryout_notes', 'reviewed_by', 'updated_at'])

    return JsonResponse({'success': True, 'status': next_status, 'message': msg})


# ============================================================================
# ACTIVITY PIN / UNPIN — Journey filtering (Point 2)
# ============================================================================

@login_required
@require_http_methods(["POST"])
def toggle_activity_pin(request, slug, activity_id):
    """POST /api/vnext/teams/<slug>/activity/<id>/pin/ — toggle pin on activity log entry."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models import TeamActivityLog
    entry = get_object_or_404(TeamActivityLog, pk=activity_id, team=team)

    entry.is_pinned = not entry.is_pinned
    entry.save(update_fields=['is_pinned'])

    return JsonResponse({
        'success': True,
        'is_pinned': entry.is_pinned,
        'message': 'Pinned!' if entry.is_pinned else 'Unpinned.',
    })


# ============================================================================
# TROPHY MANAGEMENT — Dashboard module (Point 4)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_trophies(request, slug):
    """GET /api/vnext/teams/<slug>/trophies/ — list team trophies from metadata."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    # Public endpoint — no perm check
    meta = team.metadata or {}
    trophies = meta.get('trophies', [])
    return JsonResponse({'trophies': trophies})


@login_required
@require_http_methods(["POST"])
def save_trophy(request, slug):
    """POST /api/vnext/teams/<slug>/trophies/save/ — add or edit trophy entry."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'error': 'Trophy title is required.'}, status=400)

    meta = team.metadata or {}
    trophies = meta.get('trophies', [])

    entry = {
        'id': data.get('id') or str(uuid.uuid4())[:8],
        'title': title[:80],
        'event': (data.get('event') or '').strip()[:100],
        'date': (data.get('date') or '').strip()[:20],
        'placement': (data.get('placement') or '').strip()[:30],
    }

    # Update existing or append
    existing_idx = next((i for i, t in enumerate(trophies) if t.get('id') == entry['id']), None)
    if existing_idx is not None:
        trophies[existing_idx] = entry
    else:
        if len(trophies) >= 50:
            return JsonResponse({'error': 'Maximum 50 trophies.'}, status=400)
        trophies.append(entry)

    meta['trophies'] = trophies
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'trophy': entry, 'message': 'Trophy saved.'})


@login_required
@require_http_methods(["POST"])
def delete_trophy(request, slug, trophy_id):
    """POST /api/vnext/teams/<slug>/trophies/<id>/delete/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    meta = team.metadata or {}
    trophies = meta.get('trophies', [])
    meta['trophies'] = [t for t in trophies if t.get('id') != trophy_id]
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'message': 'Trophy deleted.'})


# ============================================================================
# MERCH MANAGEMENT — Dashboard module (Point 4)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_merch(request, slug):
    """GET /api/vnext/teams/<slug>/merch/ — list merch items from metadata."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    meta = team.metadata or {}
    return JsonResponse({'merch': meta.get('merch_items', [])})


@login_required
@require_http_methods(["POST"])
def save_merch(request, slug):
    """POST /api/vnext/teams/<slug>/merch/save/ — add or edit merch item."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'error': 'Item name is required.'}, status=400)

    meta = team.metadata or {}
    merch = meta.get('merch_items', [])

    item = {
        'id': data.get('id') or str(uuid.uuid4())[:8],
        'name': name[:80],
        'price': (data.get('price') or '').strip()[:20],
        'url': (data.get('url') or '').strip()[:300],
        'image_url': (data.get('image_url') or '').strip()[:300],
    }

    existing_idx = next((i for i, m in enumerate(merch) if m.get('id') == item['id']), None)
    if existing_idx is not None:
        merch[existing_idx] = item
    else:
        if len(merch) >= 20:
            return JsonResponse({'error': 'Maximum 20 merch items.'}, status=400)
        merch.append(item)

    meta['merch_items'] = merch
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'item': item, 'message': 'Merch item saved.'})


@login_required
@require_http_methods(["POST"])
def delete_merch(request, slug, merch_id):
    """POST /api/vnext/teams/<slug>/merch/<id>/delete/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    meta = team.metadata or {}
    merch = meta.get('merch_items', [])
    meta['merch_items'] = [m for m in merch if m.get('id') != merch_id]
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'message': 'Merch item deleted.'})


# ============================================================================
# MANUAL MILESTONES
# ============================================================================

@login_required
@require_http_methods(["POST"])
def add_manual_milestone(request, slug):
    """POST /api/vnext/teams/<slug>/milestones/add/ — add a custom milestone entry."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    description = (data.get('description') or '').strip()
    if not description or len(description) > 300:
        return JsonResponse({'error': 'Description is required (max 300 chars)'}, status=400)

    milestone_date = data.get('date', '')

    from apps.organizations.models import TeamActivityLog
    from django.utils import timezone
    import datetime

    ts = timezone.now()
    if milestone_date:
        try:
            ts = datetime.datetime.fromisoformat(milestone_date).replace(tzinfo=datetime.timezone.utc)
        except (ValueError, TypeError):
            pass

    entry = TeamActivityLog.objects.create(
        team=team,
        action_type='UPDATE',
        actor_id=request.user.pk,
        actor_username=request.user.username,
        description=description,
        is_milestone=True,
        is_pinned=True,
        timestamp=ts,
    )

    return JsonResponse({'success': True, 'id': entry.pk, 'message': 'Milestone added.'})


# ============================================================================
# SPONSORS / PARTNERS  (stored in team.metadata['sponsors'])
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_sponsors(request, slug):
    """GET /api/vnext/teams/<slug>/sponsors/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    meta = team.metadata or {}
    return JsonResponse({'sponsors': meta.get('sponsors', [])})


@login_required
@require_http_methods(["POST"])
def save_sponsor(request, slug):
    """POST /api/vnext/teams/<slug>/sponsors/save/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = (data.get('name') or '').strip()
    if not name or len(name) > 80:
        return JsonResponse({'error': 'Name is required (max 80 chars)'}, status=400)

    meta = team.metadata or {}
    sponsors = meta.get('sponsors', [])
    sponsor_id = data.get('id')

    import uuid
    entry = {
        'id': sponsor_id or str(uuid.uuid4())[:8],
        'name': name,
        'logo_url': (data.get('logo_url') or '').strip()[:500],
        'url': (data.get('url') or '').strip()[:300],
        'tier': (data.get('tier') or 'partner').strip()[:20],
    }

    if sponsor_id:
        sponsors = [entry if s.get('id') == sponsor_id else s for s in sponsors]
    else:
        if len(sponsors) >= 10:
            return JsonResponse({'error': 'Maximum 10 sponsors.'}, status=400)
        sponsors.append(entry)

    meta['sponsors'] = sponsors
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'sponsor': entry})


@login_required
@require_http_methods(["POST"])
def delete_sponsor(request, slug, sponsor_id):
    """POST /api/vnext/teams/<slug>/sponsors/<id>/delete/"""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    meta = team.metadata or {}
    sponsors = meta.get('sponsors', [])
    meta['sponsors'] = [s for s in sponsors if s.get('id') != sponsor_id]
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'message': 'Sponsor removed.'})


# ============================================================================
# JOURNEY MILESTONES — Curated Public Timeline
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_journey_milestones(request, slug):
    """GET /api/vnext/teams/<slug>/journey/ — list all curated journey milestones."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.journey import TeamJourneyMilestone
    milestones = TeamJourneyMilestone.objects.filter(team=team).order_by('-milestone_date')
    items = [
        {
            'id': m.pk,
            'title': m.title,
            'description': m.description,
            'milestone_date': m.milestone_date.isoformat(),
            'milestone_type': getattr(m, 'milestone_type', 'CUSTOM'),
            'is_visible': m.is_visible,
            'is_system_generated': getattr(m, 'is_system_generated', False),
            'sort_order': m.sort_order,
        }
        for m in milestones
    ]
    return JsonResponse({'success': True, 'milestones': items, 'count': len(items)})


@login_required
@require_http_methods(["POST"])
def save_journey_milestone(request, slug):
    """POST /api/vnext/teams/<slug>/journey/save/ — create or update a journey milestone."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    milestone_date_str = (data.get('milestone_date') or '').strip()
    milestone_type = (data.get('milestone_type') or 'CUSTOM').strip()
    is_visible = data.get('is_visible', True)
    milestone_id = data.get('id')

    # Validate milestone_type
    from apps.organizations.models.journey import MilestoneType
    valid_types = [c[0] for c in MilestoneType.choices]
    if milestone_type not in valid_types:
        milestone_type = 'CUSTOM'

    if not title or len(title) > 120:
        return JsonResponse({'error': 'Title is required (max 120 chars)'}, status=400)
    if len(description) > 500:
        return JsonResponse({'error': 'Description must be 500 characters or less'}, status=400)
    if not milestone_date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)

    import datetime
    try:
        milestone_date = datetime.date.fromisoformat(milestone_date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format (use YYYY-MM-DD)'}, status=400)

    from apps.organizations.models.journey import TeamJourneyMilestone

    # Max 10 milestones per team
    if not milestone_id:
        existing_count = TeamJourneyMilestone.objects.filter(team=team).count()
        if existing_count >= 10:
            return JsonResponse({'error': 'Maximum 10 journey milestones allowed'}, status=400)

    if milestone_id:
        try:
            milestone = TeamJourneyMilestone.objects.get(pk=milestone_id, team=team)
            milestone.title = title
            milestone.description = description
            milestone.milestone_date = milestone_date
            milestone.milestone_type = milestone_type
            milestone.is_visible = bool(is_visible)
            milestone.save()
            msg = 'Milestone updated.'
        except TeamJourneyMilestone.DoesNotExist:
            return JsonResponse({'error': 'Milestone not found'}, status=404)
    else:
        milestone = TeamJourneyMilestone.objects.create(
            team=team,
            title=title,
            description=description,
            milestone_date=milestone_date,
            milestone_type=milestone_type,
            is_visible=bool(is_visible),
            created_by=request.user,
        )
        msg = 'Milestone created.'

    return JsonResponse({
        'success': True,
        'message': msg,
        'milestone': {
            'id': milestone.pk,
            'title': milestone.title,
            'description': milestone.description,
            'milestone_date': milestone.milestone_date.isoformat(),
            'milestone_type': milestone.milestone_type,
            'is_visible': milestone.is_visible,
            'is_system_generated': milestone.is_system_generated,
        },
    })


@login_required
@require_http_methods(["POST"])
def delete_journey_milestone(request, slug, milestone_id):
    """POST /api/vnext/teams/<slug>/journey/<id>/delete/ — delete a journey milestone."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.journey import TeamJourneyMilestone
    try:
        milestone = TeamJourneyMilestone.objects.get(pk=milestone_id, team=team)
        milestone.delete()
        return JsonResponse({'success': True, 'message': 'Milestone deleted.'})
    except TeamJourneyMilestone.DoesNotExist:
        return JsonResponse({'error': 'Milestone not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def toggle_journey_visibility(request, slug, milestone_id):
    """POST /api/vnext/teams/<slug>/journey/<id>/toggle/ — toggle milestone visibility."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.models.journey import TeamJourneyMilestone
    try:
        milestone = TeamJourneyMilestone.objects.get(pk=milestone_id, team=team)
        milestone.is_visible = not milestone.is_visible
        milestone.save(update_fields=['is_visible'])
        return JsonResponse({
            'success': True,
            'is_visible': milestone.is_visible,
            'message': f'Milestone {"shown" if milestone.is_visible else "hidden"}.',
        })
    except TeamJourneyMilestone.DoesNotExist:
        return JsonResponse({'error': 'Milestone not found'}, status=404)


# ── Milestone Suggestions ──────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def journey_suggestions(request, slug):
    """GET /api/vnext/teams/<slug>/journey/suggestions/ — auto-detected milestone suggestions."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    from apps.organizations.services.milestone_suggestions import get_milestone_suggestions
    suggestions = get_milestone_suggestions(team)
    return JsonResponse({'success': True, 'suggestions': suggestions})


@login_required
@require_http_methods(["POST"])
def dismiss_journey_suggestion(request, slug):
    """POST /api/vnext/teams/<slug>/journey/suggestions/dismiss/ — dismiss a suggested milestone."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    has_perm, reason = _check_manage_permissions(team, request.user)
    if not has_perm:
        return JsonResponse({'error': reason}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    key = (data.get('key') or '').strip()
    if not key:
        return JsonResponse({'error': 'Suggestion key is required'}, status=400)

    # Store dismissed key in team metadata
    meta = team.metadata or {}
    dismissed = meta.get('dismissed_milestone_suggestions', [])
    if key not in dismissed:
        dismissed.append(key)
    meta['dismissed_milestone_suggestions'] = dismissed
    team.metadata = meta
    team.save(update_fields=['metadata'])

    return JsonResponse({'success': True, 'message': 'Suggestion dismissed.'})
