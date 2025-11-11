"""
Reports Service

Provides idempotent, atomic operations for abuse reports.

API:
- file_report(): Create abuse report with idempotency
- triage_report(): Transition report state with validation
"""
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from apps.moderation.models import AbuseReport, ModerationAudit


def file_report(
    reporter_id,
    *,
    category,
    ref_type,
    ref_id,
    priority=3,
    idempotency_key=None,
    meta=None,
):
    """
    Create an abuse report with idempotency.
    
    Args:
        reporter_id: User profile ID filing the report
        category: Report category (e.g., 'harassment', 'cheating')
        ref_type: Type of entity being reported (e.g., 'chat_message', 'profile')
        ref_id: ID of entity being reported
        priority: Priority 0-5 (default: 3)
        idempotency_key: Unique key for replay protection
        meta: Dict of additional metadata
    
    Returns:
        dict: {
            'report_id': int,
            'created': bool,  # False if replayed
            'reporter_profile_id': int,
            'category': str,
            'ref_type': str,
            'ref_id': int,
            'state': str,
            'priority': int,
        }
    
    Raises:
        ValueError: Invalid parameters
    """
    # Validate required fields
    if not reporter_id:
        raise ValueError("reporter_id is required")
    if not category:
        raise ValueError("category is required")
    if not ref_type:
        raise ValueError("ref_type is required")
    if ref_id is None:
        raise ValueError("ref_id is required")
    if not (0 <= priority <= 5):
        raise ValueError("priority must be between 0 and 5")
    
    # Idempotency: check for existing report with same key
    if idempotency_key:
        existing = AbuseReport.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return {
                'report_id': existing.id,
                'created': False,
                'reporter_profile_id': existing.reporter_profile_id,
                'category': existing.category,
                'ref_type': existing.ref_type,
                'ref_id': existing.ref_id,
                'state': existing.state,
                'priority': existing.priority,
            }
    
    # Create report atomically
    with transaction.atomic():
        report = AbuseReport.objects.create(
            reporter_profile_id=reporter_id,
            category=category,
            ref_type=ref_type,
            ref_id=ref_id,
            priority=priority,
            idempotency_key=idempotency_key,
            meta=meta or {},
        )
        
        # Write audit trail
        ModerationAudit.objects.create(
            event='report_filed',
            actor_id=reporter_id,
            subject_profile_id=None,  # Will be set when triaged
            ref_type='report',
            ref_id=report.id,
            meta={
                'category': category,
                'ref_type': ref_type,
                'ref_id': ref_id,
                'priority': priority,
            }
        )
    
    return {
        'report_id': report.id,
        'created': True,
        'reporter_profile_id': report.reporter_profile_id,
        'category': report.category,
        'ref_type': report.ref_type,
        'ref_id': report.ref_id,
        'state': report.state,
        'priority': report.priority,
    }


def triage_report(
    report_id,
    *,
    new_state,
    actor_id,
    meta=None,
):
    """
    Transition report to new state with validation.
    
    Valid transitions:
    - open → triaged
    - triaged → resolved
    - triaged → rejected
    
    Args:
        report_id: ID of report to triage
        new_state: Target state ('triaged', 'resolved', 'rejected')
        actor_id: User profile ID performing triage
        meta: Dict of additional metadata
    
    Returns:
        dict: {
            'report_id': int,
            'transitioned': bool,  # False if invalid transition
            'old_state': str,
            'new_state': str,
        }
    
    Raises:
        ValueError: Report not found or invalid transition
    """
    with transaction.atomic():
        # Lock row for update
        try:
            report = AbuseReport.objects.select_for_update().get(id=report_id)
        except AbuseReport.DoesNotExist:
            raise ValueError(f"Report {report_id} not found")
        
        old_state = report.state
        
        # Validate transition
        if not report.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition: {old_state} → {new_state}. "
                f"Valid transitions: {', '.join(AbuseReport.VALID_TRANSITIONS.get(old_state, []))}"
            )
        
        # Transition state
        report.state = new_state
        report.save(update_fields=['state', 'updated_at'])
        
        # Write audit trail
        ModerationAudit.objects.create(
            event='report_triaged',
            actor_id=actor_id,
            subject_profile_id=report.subject_profile_id,
            ref_type='report',
            ref_id=report.id,
            meta={
                'old_state': old_state,
                'new_state': new_state,
                'triage_meta': meta or {},
            }
        )
    
    return {
        'report_id': report.id,
        'transitioned': True,
        'old_state': old_state,
        'new_state': new_state,
    }
