"""
Audit Service

Provides query API for append-only moderation audit trail.

API:
- list_audit_events(): Query audit events with filters and pagination
"""
from django.db.models import Q

from apps.moderation.models import ModerationAudit


def list_audit_events(
    *,
    ref_type=None,
    ref_id=None,
    actor_id=None,
    since=None,
    until=None,
    limit=100,
    offset=0,
):
    """
    List audit events with filters and pagination.
    
    Args:
        ref_type: Filter by reference type (e.g., 'sanction', 'report')
        ref_id: Filter by reference ID
        actor_id: Filter by actor (user who performed action)
        since: Filter events created >= this datetime
        until: Filter events created < this datetime
        limit: Max results to return (default: 100)
        offset: Pagination offset (default: 0)
    
    Returns:
        dict: {
            'count': int,  # Total matching events
            'limit': int,
            'offset': int,
            'events': [
                {
                    'id': int,
                    'event': str,
                    'actor_id': int or None,
                    'subject_profile_id': int or None,
                    'ref_type': str,
                    'ref_id': int,
                    'meta': dict,
                    'created_at': str (ISO),
                },
                ...
            ]
        }
    """
    # Build query
    q = Q()
    
    if ref_type:
        q &= Q(ref_type=ref_type)
    if ref_id is not None:
        q &= Q(ref_id=ref_id)
    if actor_id is not None:
        q &= Q(actor_id=actor_id)
    if since:
        q &= Q(created_at__gte=since)
    if until:
        q &= Q(created_at__lt=until)
    
    # Query with pagination
    queryset = ModerationAudit.objects.filter(q).order_by('-created_at')
    total_count = queryset.count()
    
    events = queryset[offset:offset + limit]
    
    return {
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'events': [
            {
                'id': e.id,
                'event': e.event,
                'actor_id': e.actor_id,
                'subject_profile_id': e.subject_profile_id,
                'ref_type': e.ref_type,
                'ref_id': e.ref_id,
                'meta': e.meta,
                'created_at': e.created_at.isoformat(),
            }
            for e in events
        ]
    }
