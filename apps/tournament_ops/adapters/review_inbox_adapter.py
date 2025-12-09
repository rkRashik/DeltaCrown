"""
Review Inbox Adapter - Phase 6, Epic 6.3

Adapter for accessing organizer results inbox data without ORM coupling.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox)
"""

from typing import Protocol, List, Tuple, Optional
from datetime import datetime, timezone

from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    DisputeDTO,
)


class ReviewInboxAdapterProtocol(Protocol):
    """
    Protocol for review inbox data access.
    
    Defines methods for fetching submissions requiring organizer attention:
    - Pending submissions (awaiting opponent response)
    - Disputed submissions (opponent disputed result)
    - Overdue auto-confirm (past deadline without confirmation)
    - Ready for finalization (confirmed but not finalized)
    
    Reference: Phase 6, Epic 6.3 - Review Inbox Adapter Protocol
    """
    
    def get_pending_submissions(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get all pending submissions (awaiting opponent response).
        
        Args:
            tournament_id: Optional tournament filter
            
        Returns:
            List of MatchResultSubmissionDTO with status='pending'
            
        Reference: Phase 6, Epic 6.3 - Pending Submissions
        """
        ...
    
    def get_disputed_submissions(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[Tuple[MatchResultSubmissionDTO, DisputeDTO]]:
        """
        Get all disputed submissions with their disputes.
        
        Args:
            tournament_id: Optional tournament filter
            
        Returns:
            List of (MatchResultSubmissionDTO, DisputeDTO) tuples
            Only includes open/under_review/escalated disputes
            
        Reference: Phase 6, Epic 6.3 - Disputed Submissions
        """
        ...
    
    def get_overdue_auto_confirm(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get submissions past auto_confirm_deadline but not confirmed.
        
        Args:
            tournament_id: Optional tournament filter
            
        Returns:
            List of MatchResultSubmissionDTO with status='pending' and
            auto_confirm_deadline < now
            
        Reference: Phase 6, Epic 6.3 - Overdue Auto-Confirm
        """
        ...
    
    def get_ready_for_finalization(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get submissions ready for finalization (confirmed but not finalized).
        
        Args:
            tournament_id: Optional tournament filter
            
        Returns:
            List of MatchResultSubmissionDTO with status='confirmed'
            (not yet finalized)
            
        Reference: Phase 6, Epic 6.3 - Ready for Finalization
        """
        ...


class ReviewInboxAdapter:
    """
    Concrete adapter for review inbox data access.
    
    Uses method-level ORM imports to avoid coupling.
    Returns DTOs only.
    
    Reference: Phase 6, Epic 6.3 - Review Inbox Adapter
    """
    
    def get_pending_submissions(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """Get pending submissions (awaiting opponent response)."""
        # Method-level import
        from apps.tournaments.models import MatchResultSubmission
        
        # Build query
        queryset = MatchResultSubmission.objects.filter(status='pending')
        
        if tournament_id is not None:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        # Order by submitted_at (oldest first)
        queryset = queryset.order_by('submitted_at')
        
        # Convert to DTOs
        return [
            MatchResultSubmissionDTO(
                id=sub.id,
                match_id=sub.match_id,
                tournament_id=sub.tournament_id,
                stage_id=sub.stage_id,
                submitted_by_user_id=sub.submitted_by_user_id,
                submitted_by_team_id=sub.submitted_by_team_id,
                raw_result_payload=sub.raw_result_payload,
                proof_screenshot_url=sub.proof_screenshot_url,
                submitter_notes=sub.submitter_notes,
                status=sub.status,
                submitted_at=sub.submitted_at,
                confirmed_at=sub.confirmed_at,
                confirmed_by_user_id=sub.confirmed_by_user_id,
                auto_confirmed=sub.auto_confirmed,
                auto_confirm_deadline=sub.auto_confirm_deadline,
            )
            for sub in queryset
        ]
    
    def get_disputed_submissions(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[Tuple[MatchResultSubmissionDTO, DisputeDTO]]:
        """Get disputed submissions with their disputes."""
        # Method-level imports
        from apps.tournaments.models import MatchResultSubmission, DisputeRecord
        
        # Build query for disputed submissions with open disputes
        # Join MatchResultSubmission with DisputeRecord
        queryset = MatchResultSubmission.objects.filter(
            status='disputed'
        ).select_related('disputerecord')
        
        if tournament_id is not None:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        # Order by dispute opened_at (oldest first)
        queryset = queryset.order_by('disputerecord__opened_at')
        
        # Convert to DTOs
        results = []
        for sub in queryset:
            # Get the open/under_review/escalated dispute
            try:
                dispute = DisputeRecord.objects.filter(
                    submission_id=sub.id,
                    status__in=['open', 'under_review', 'escalated'],
                ).first()
                
                if dispute:
                    submission_dto = MatchResultSubmissionDTO(
                        id=sub.id,
                        match_id=sub.match_id,
                        tournament_id=sub.tournament_id,
                        stage_id=sub.stage_id,
                        submitted_by_user_id=sub.submitted_by_user_id,
                        submitted_by_team_id=sub.submitted_by_team_id,
                        raw_result_payload=sub.raw_result_payload,
                        proof_screenshot_url=sub.proof_screenshot_url,
                        submitter_notes=sub.submitter_notes,
                        status=sub.status,
                        submitted_at=sub.submitted_at,
                        confirmed_at=sub.confirmed_at,
                        confirmed_by_user_id=sub.confirmed_by_user_id,
                        auto_confirmed=sub.auto_confirmed,
                        auto_confirm_deadline=sub.auto_confirm_deadline,
                    )
                    
                    dispute_dto = DisputeDTO(
                        id=dispute.id,
                        submission_id=dispute.submission_id,
                        opened_by_user_id=dispute.opened_by_user_id,
                        opened_by_team_id=dispute.opened_by_team_id,
                        reason_code=dispute.reason_code,
                        description=dispute.description,
                        status=dispute.status,
                        resolution_notes=dispute.resolution_notes,
                        opened_at=dispute.opened_at,
                        updated_at=dispute.updated_at,
                        resolved_at=dispute.resolved_at,
                        resolved_by_user_id=dispute.resolved_by_user_id,
                        escalated_at=dispute.escalated_at,
                    )
                    
                    results.append((submission_dto, dispute_dto))
            except Exception:
                # Skip submissions with no valid dispute
                pass
        
        return results
    
    def get_overdue_auto_confirm(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """Get submissions past auto_confirm_deadline but not confirmed."""
        # Method-level import
        from apps.tournaments.models import MatchResultSubmission
        
        # Current time
        now = datetime.now(timezone.utc)
        
        # Build query
        queryset = MatchResultSubmission.objects.filter(
            status='pending',
            auto_confirm_deadline__lt=now,
        )
        
        if tournament_id is not None:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        # Order by deadline (most overdue first)
        queryset = queryset.order_by('auto_confirm_deadline')
        
        # Convert to DTOs
        return [
            MatchResultSubmissionDTO(
                id=sub.id,
                match_id=sub.match_id,
                tournament_id=sub.tournament_id,
                stage_id=sub.stage_id,
                submitted_by_user_id=sub.submitted_by_user_id,
                submitted_by_team_id=sub.submitted_by_team_id,
                raw_result_payload=sub.raw_result_payload,
                proof_screenshot_url=sub.proof_screenshot_url,
                submitter_notes=sub.submitter_notes,
                status=sub.status,
                submitted_at=sub.submitted_at,
                confirmed_at=sub.confirmed_at,
                confirmed_by_user_id=sub.confirmed_by_user_id,
                auto_confirmed=sub.auto_confirmed,
                auto_confirm_deadline=sub.auto_confirm_deadline,
            )
            for sub in queryset
        ]
    
    def get_ready_for_finalization(
        self,
        tournament_id: Optional[int] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """Get submissions ready for finalization (confirmed but not finalized)."""
        # Method-level import
        from apps.tournaments.models import MatchResultSubmission
        
        # Build query
        queryset = MatchResultSubmission.objects.filter(status='confirmed')
        
        if tournament_id is not None:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        # Order by confirmed_at (oldest first)
        queryset = queryset.order_by('confirmed_at')
        
        # Convert to DTOs
        return [
            MatchResultSubmissionDTO(
                id=sub.id,
                match_id=sub.match_id,
                tournament_id=sub.tournament_id,
                stage_id=sub.stage_id,
                submitted_by_user_id=sub.submitted_by_user_id,
                submitted_by_team_id=sub.submitted_by_team_id,
                raw_result_payload=sub.raw_result_payload,
                proof_screenshot_url=sub.proof_screenshot_url,
                submitter_notes=sub.submitter_notes,
                status=sub.status,
                submitted_at=sub.submitted_at,
                confirmed_at=sub.confirmed_at,
                confirmed_by_user_id=sub.confirmed_by_user_id,
                auto_confirmed=sub.auto_confirmed,
                auto_confirm_deadline=sub.auto_confirm_deadline,
            )
            for sub in queryset
        ]
