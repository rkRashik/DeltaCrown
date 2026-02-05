"""
User Team History API

Provides player career history from append-only membership event ledger.
Used for Profile user journey, fair play enforcement, and audits.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db.models import Prefetch

from apps.organizations.models import TeamMembership, TeamMembershipEvent
from apps.organizations.choices import MembershipEventType

User = get_user_model()


@require_http_methods(["GET"])
@login_required
def user_team_history(request, user_id):
    """
    GET /api/vnext/users/<user_id>/team-history/
    
    Returns user's complete team membership history with event timeline.
    
    Query Parameters:
    - limit: Number of memberships to return (default: 50, max: 100)
    - cursor: ISO timestamp to fetch memberships before this date
    
    Permissions:
    - Users can view their own history
    - Staff/admin can view any user's history (including sensitive metadata)
    - Others: 403
    
    Response structure:
    {
        "user_id": 123,
        "username": "player_name",
        "pagination": {
            "limit": 50,
            "next_cursor": "2025-12-01T00:00:00Z" or null
        },
        "history": [
            {
                "team_id": 1,
                "team_slug": "alpha",
                "team_name": "Team Alpha",
                "organization_slug": "org-x",
                "joined_at": "2026-01-15T10:00:00Z",
                "left_at": null,
                "current_status": "ACTIVE",
                "current_role": "PLAYER",
                "summary": {
                    "total_events": 3,
                    "roles_held": ["PLAYER", "COACH"],
                    "is_active": true
                },
                "role_timeline": [
                    {"at": "2026-01-15T10:00:00Z", "role": "PLAYER"},
                    {"at": "2026-02-01T14:30:00Z", "role": "COACH"}
                ],
                "events": [...]
            }
        ]
    }
    """
    # Get target user
    user = get_object_or_404(User, id=user_id)
    
    # Check permissions
    is_self = request.user.id == user.id
    is_staff = request.user.is_staff
    
    if not is_self and not is_staff:
        return JsonResponse({'error': 'You do not have permission to view this user\'s history'}, status=403)
    
    # Parse pagination parameters
    limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100
    cursor = request.GET.get('cursor')  # ISO timestamp
    
    # Build query
    memberships_query = TeamMembership.objects.filter(
        user=user
    ).select_related(
        'team',
        'team__organization'
    ).prefetch_related(
        Prefetch(
            'events',
            queryset=TeamMembershipEvent.objects.select_related('actor').order_by('created_at')
        )
    ).order_by('-joined_at')
    
    # Apply cursor pagination
    if cursor:
        from django.utils.dateparse import parse_datetime
        cursor_dt = parse_datetime(cursor)
        if cursor_dt:
            memberships_query = memberships_query.filter(joined_at__lt=cursor_dt)
    
    # Fetch limit + 1 to determine if there's more data
    memberships = list(memberships_query[:limit + 1])
    has_more = len(memberships) > limit
    if has_more:
        memberships = memberships[:limit]
    
    # Determine next cursor
    next_cursor = None
    if has_more and memberships:
        last_membership = memberships[-1]
        next_cursor = last_membership.joined_at.isoformat() if last_membership.joined_at else None
    
    # Build history
    history = []
    for membership in memberships:
        # Extract events for this membership
        events_data = []
        role_timeline = []
        roles_held = set()
        
        for event in membership.events.all():
            # Redact sensitive metadata unless staff
            metadata = event.metadata or {}
            if not is_staff:
                # Remove admin-only fields
                metadata = {k: v for k, v in metadata.items() 
                           if k not in ['reason', 'duration_days', 'moderator_notes']}
            
            event_dict = {
                'at': event.created_at.isoformat() if event.created_at else None,
                'type': event.event_type,
                'actor_username': event.actor.username if event.actor else 'system',
                'metadata': metadata,
            }
            
            # Add role/status changes
            if event.old_role:
                event_dict['old_role'] = event.old_role
                roles_held.add(event.old_role)
            if event.new_role:
                event_dict['new_role'] = event.new_role
                roles_held.add(event.new_role)
            if event.old_status:
                event_dict['old_status'] = event.old_status
            if event.new_status:
                event_dict['new_status'] = event.new_status
            
            events_data.append(event_dict)
            
            # Build role timeline from JOINED and ROLE_CHANGED events
            if event.event_type in (MembershipEventType.JOINED, MembershipEventType.ROLE_CHANGED):
                if event.new_role:
                    role_timeline.append({
                        'at': event.created_at.isoformat() if event.created_at else None,
                        'role': event.new_role,
                    })
        
        # Build membership history entry with summary
        history_entry = {
            'team_id': membership.team.id,
            'team_slug': membership.team.slug,
            'team_name': membership.team.name,
            'organization_slug': membership.team.organization.slug if membership.team.organization else None,
            'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
            'left_at': membership.left_at.isoformat() if membership.left_at else None,
            'current_status': membership.status,
            'current_role': membership.role,
            'summary': {
                'total_events': len(events_data),
                'roles_held': sorted(list(roles_held)) if roles_held else [membership.role],
                'is_active': membership.status == 'ACTIVE',
            },
            'role_timeline': role_timeline,
            'events': events_data,
        }
        
        history.append(history_entry)
    
    return JsonResponse({
        'user_id': user.id,
        'username': user.username,
        'pagination': {
            'limit': limit,
            'next_cursor': next_cursor,
        },
        'history': history,
    })
