"""
Audit Logging for Tournament System

Provides audit trail for sensitive operations to ensure accountability
and enable security monitoring.

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening

Audit Actions:
    - Payment operations (verify, reject, refund)
    - Bracket operations (regenerate, finalize, unfinalize)
    - Dispute operations (resolve, escalate)
    - Administrative actions (ban, force refund)

Usage:
    from apps.tournaments.security.audit import audit_event, AuditAction
    
    # In service layer
    def verify_payment(payment_id, verified_by):
        payment = Payment.objects.get(id=payment_id)
        payment.status = 'verified'
        payment.save()
        
        audit_event(
            user=verified_by,
            action=AuditAction.PAYMENT_VERIFY,
            meta={
                'payment_id': payment_id,
                'tournament_id': payment.tournament_id,
                'amount': payment.amount
            }
        )
"""

import logging
from enum import Enum
from typing import Dict, Optional, Any, TYPE_CHECKING
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import QuerySet

logger = logging.getLogger(__name__)
User = get_user_model()

# Import AuditLog model from models package (Module 2.4)
from apps.tournaments.models import AuditLog


class AuditAction(str, Enum):
    """
    Enumeration of auditable actions.
    
    Categories:
        - PAYMENT_*: Payment-related operations
        - BRACKET_*: Bracket management operations
        - DISPUTE_*: Dispute resolution operations
        - ADMIN_*: Administrative actions
        - MATCH_*: Match management operations
    """
    # Payment operations
    PAYMENT_VERIFY = 'payment_verify'
    PAYMENT_REJECT = 'payment_reject'
    PAYMENT_REFUND = 'payment_refund'
    PAYMENT_FORCE_REFUND = 'payment_force_refund'
    FEE_WAIVED = 'fee_waived'
    
    # Bracket operations
    BRACKET_GENERATE = 'bracket_generate'
    BRACKET_REGENERATE = 'bracket_regenerate'
    BRACKET_FINALIZE = 'bracket_finalize'
    BRACKET_UNFINALIZE = 'bracket_unfinalize'
    
    # Dispute operations
    DISPUTE_CREATE = 'dispute_create'
    DISPUTE_RESOLVE = 'dispute_resolve'
    DISPUTE_ESCALATE = 'dispute_escalate'
    DISPUTE_CLOSE = 'dispute_close'
    
    # Match operations
    MATCH_SCORE_UPDATE = 'match_score_update'
    MATCH_FORCE_WIN = 'match_force_win'
    MATCH_RESET = 'match_reset'
    MATCH_START = 'match_start'  # Module 4.3: Match start
    MATCH_SCHEDULE = 'match_schedule'  # Module 4.3: Schedule update
    MATCH_BULK_SCHEDULE = 'match_bulk_schedule'  # Module 4.3: Bulk scheduling
    MATCH_COORDINATOR_ASSIGN = 'match_coordinator_assign'  # Module 4.3: Coordinator assignment
    MATCH_LOBBY_UPDATE = 'match_lobby_update'  # Module 4.3: Lobby info update
    
    # Result submission operations (Module 4.4)
    RESULT_SUBMIT = 'result_submit'  # Module 4.4: Result submission
    RESULT_CONFIRM = 'result_confirm'  # Module 4.4: Result confirmation
    # Note: DISPUTE_CREATE already defined in "Dispute operations" section above
    
    # Administrative actions
    ADMIN_BAN_PARTICIPANT = 'admin_ban_participant'
    ADMIN_UNBAN_PARTICIPANT = 'admin_unban_participant'
    ADMIN_CANCEL_TOURNAMENT = 'admin_cancel_tournament'
    ADMIN_EMERGENCY_STOP = 'admin_emergency_stop'
    
    # Registration operations
    REGISTRATION_OVERRIDE = 'registration_override'
    REGISTRATION_FORCE_CHECKIN = 'registration_force_checkin'
    REGISTRATION_CHECKIN = 'registration_checkin'
    REGISTRATION_CHECKIN_REVERT = 'registration_checkin_revert'


# AuditLog model is defined in apps/tournaments/models/security.py
# and imported at the top of this file


def audit_event(
    user,  # User who performed the action (or None)
    action: AuditAction,
    meta: Optional[Dict[str, Any]] = None,
    request=None
) -> AuditLog:
    """
    Create an audit log entry for a sensitive action.
    
    Args:
        user: User who performed the action (None for system actions)
        action: AuditAction enum value
        meta: Dictionary of action-specific metadata
        request: Optional Django request object (for IP/user agent)
        
    Returns:
        Created AuditLog instance
        
    Example:
        # Payment verification
        audit_event(
            user=request.user,
            action=AuditAction.PAYMENT_VERIFY,
            meta={
                'payment_id': payment.id,
                'tournament_id': payment.tournament.id,
                'amount': payment.amount,
                'method': payment.payment_method
            },
            request=request
        )
        
        # Bracket regeneration
        audit_event(
            user=request.user,
            action=AuditAction.BRACKET_REGENERATE,
            meta={
                'tournament_id': tournament.id,
                'old_bracket_id': old_bracket.id,
                'new_bracket_id': new_bracket.id,
                'reason': 'Participant withdrew'
            }
        )
    """
    metadata = meta or {}
    
    # Extract IP and user agent from request if provided
    ip_address = None
    user_agent = None
    
    if request:
        # Get client IP (handle proxy headers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT')
    
    # Create audit log entry
    try:
        audit_log = AuditLog.objects.create(
            user=user,
            action=action.value if isinstance(action, AuditAction) else action,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Audit: {action.value if isinstance(action, AuditAction) else action} by "
            f"{user.username if user else 'SYSTEM'} - {metadata}"
        )
        
        return audit_log
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        # Re-raise to ensure audit failures don't go unnoticed
        raise


def get_user_audit_trail(user, limit: int = 100) -> QuerySet:
    """
    Get audit trail for a specific user.
    
    Args:
        user: User to get audit trail for
        limit: Maximum number of entries to return
        
    Returns:
        QuerySet of AuditLog entries
        
    Example:
        # Get recent activity for user
        audit_trail = get_user_audit_trail(user, limit=50)
        for entry in audit_trail:
            print(f"{entry.timestamp}: {entry.action} - {entry.metadata}")
    """
    # Don't slice - allows further filtering. Apply limit when materializing results.
    qs = AuditLog.objects.filter(user=user).order_by('-timestamp')
    return qs[:limit] if limit else qs


def get_tournament_audit_trail(tournament_id: int, limit: int = 100) -> QuerySet:
    """
    Get audit trail for a specific tournament.
    
    Args:
        tournament_id: Tournament ID to filter by
        limit: Maximum number of entries to return
        
    Returns:
        QuerySet of AuditLog entries where metadata contains tournament_id
        
    Example:
        # Get all payment actions for tournament
        payment_actions = get_tournament_audit_trail(tournament_id).filter(
            action__startswith='payment_'
        )
    """
    # Don't slice - allows further filtering as shown in docstring example
    qs = AuditLog.objects.filter(
        metadata__tournament_id=tournament_id
    ).order_by('-timestamp')
    return qs[:limit] if limit else qs


def get_action_audit_trail(action: AuditAction, limit: int = 100) -> QuerySet:
    """
    Get audit trail for a specific action type.
    
    Args:
        action: AuditAction enum value
        limit: Maximum number of entries to return
        
    Returns:
        QuerySet of AuditLog entries for the action
        
    Example:
        # Get all payment verifications in last 24 hours
        from django.utils import timezone
        from datetime import timedelta
        
        recent_verifications = get_action_audit_trail(AuditAction.PAYMENT_VERIFY).filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        )
    """
    action_value = action.value if isinstance(action, AuditAction) else action
    # Don't slice - allows further filtering as shown in docstring example
    qs = AuditLog.objects.filter(action=action_value).order_by('-timestamp')
    return qs[:limit] if limit else qs


def get_audit_summary(start_date=None, end_date=None) -> Dict[str, int]:
    """
    Get summary of audit actions within date range.
    
    Args:
        start_date: Start of date range (default: 30 days ago)
        end_date: End of date range (default: now)
        
    Returns:
        Dictionary mapping action types to counts
        
    Example:
        # Get last 7 days audit summary
        from datetime import timedelta
        summary = get_audit_summary(
            start_date=timezone.now() - timedelta(days=7)
        )
        print(f"Payment verifications: {summary.get('payment_verify', 0)}")
    """
    from datetime import timedelta
    
    if not start_date:
        start_date = timezone.now() - timedelta(days=30)
    if not end_date:
        end_date = timezone.now()
    
    queryset = AuditLog.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    # Group by action and count
    from django.db.models import Count
    summary = queryset.values('action').annotate(count=Count('id'))
    
    return {item['action']: item['count'] for item in summary}


# -----------------------------------------------------------------------------
# Django Admin Integration
# -----------------------------------------------------------------------------

from django.contrib import admin


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing audit logs.
    
    Features:
        - Read-only (audit logs should not be modified)
        - Filter by action, user, timestamp
        - Search by user, action, metadata
        - JSON metadata display
    """
    
    list_display = ('timestamp', 'user', 'action', 'get_metadata_preview', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action', 'metadata')
    readonly_fields = ('user', 'action', 'timestamp', 'metadata', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Disable manual creation of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion of individual audit logs"""
        # Only allow bulk deletion through admin actions (with confirmation)
        return request.user.is_superuser
    
    def get_metadata_preview(self, obj):
        """Display preview of metadata JSON"""
        import json
        try:
            preview = json.dumps(obj.metadata, indent=2)
            if len(preview) > 100:
                return preview[:100] + '...'
            return preview
        except Exception:
            return str(obj.metadata)
    
    get_metadata_preview.short_description = 'Metadata'
    
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        """Export selected audit logs as CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'User', 'Action', 'Metadata', 'IP Address'])
        
        for log in queryset:
            writer.writerow([
                log.timestamp.isoformat(),
                log.user.username if log.user else 'SYSTEM',
                log.action,
                str(log.metadata),
                log.ip_address or ''
            ])
        
        return response
    
    export_as_csv.short_description = "Export selected logs as CSV"
