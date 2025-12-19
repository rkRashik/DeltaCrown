"""
Dispute Service

Phase 0 Refactor: Extracted dispute management ORM mutations from organizer views.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError


class DisputeService:
    """
    Service for managing tournament match disputes.
    
    Phase 0 Scope: Extract existing ORM mutations from organizer views.
    Preserves exact behavior - does not add new notifications/webhooks.
    """
    
    @staticmethod
    @transaction.atomic
    def organizer_update_status(dispute, new_status: str):
        """
        Update dispute status (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py update_dispute_status view.
        Preserves exact behavior - updates status field only.
        
        Args:
            dispute: Dispute instance
            new_status: New status ('open', 'under_review', 'resolved')
        
        Returns:
            Updated Dispute instance
        
        Raises:
            ValidationError: If status invalid
        """
        if new_status not in ['open', 'under_review', 'resolved']:
            raise ValidationError('Invalid status')
        
        dispute.status = new_status
        dispute.save()
        
        return dispute
    
    @staticmethod
    @transaction.atomic
    def organizer_resolve(dispute, resolution_notes: str, resolved_by):
        """
        Resolve a dispute with resolution notes (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py resolve_dispute view.
        Preserves exact behavior - sets status, notes, resolved_by/at.
        
        Args:
            dispute: Dispute instance
            resolution_notes: Resolution notes text
            resolved_by: User instance (organizer)
        
        Returns:
            Updated Dispute instance
        
        Raises:
            ValidationError: If resolution_notes missing
        """
        if not resolution_notes or not resolution_notes.strip():
            raise ValidationError('Resolution notes required')
        
        dispute.status = 'resolved'
        dispute.resolution_notes = resolution_notes
        dispute.resolved_by = resolved_by
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        return dispute
