"""
Review Inbox Adapter - Phase 6, Epic 6.3 & Phase 7, Epic 7.1

Adapter for accessing organizer results inbox data without ORM coupling.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox)
Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1 (Multi-Tournament Queue)
"""

from typing import Protocol, List, Tuple, Optional
from datetime import datetime, timezone

from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    DisputeDTO,
    OrganizerInboxFilterDTO,
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
        since: Optional[datetime] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get all pending submissions (awaiting opponent response).
        
        Args:
            tournament_id: Optional tournament filter
            since: Optional datetime filter (created_at >= since)
            
        Returns:
            List of MatchResultSubmissionDTO with status='pending'
            
        Reference: Phase 6, Epic 6.3 - Pending Submissions
        Reference: Phase 7, Epic 7.1 - Date Range Filtering
        """
        ...
    
    def get_disputed_submissions(
        self,
        tournament_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> List[Tuple[MatchResultSubmissionDTO, DisputeDTO]]:
        """
        Get all disputed submissions with their disputes.
        
        Args:
            tournament_id: Optional tournament filter
            since: Optional datetime filter (created_at >= since)
            
        Returns:
            List of (MatchResultSubmissionDTO, DisputeDTO) tuples
            Only includes open/under_review/escalated disputes
            
        Reference: Phase 6, Epic 6.3 - Disputed Submissions
        Reference: Phase 7, Epic 7.1 - Date Range Filtering
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
    
    def get_recent_items_for_organizer(
        self,
        organizer_user_id: int,
        since: Optional[datetime] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get recent submissions for a specific organizer.
        
        Args:
            organizer_user_id: Organizer user ID
            since: Optional datetime filter (created_at >= since)
            
        Returns:
            List of MatchResultSubmissionDTO for tournaments organized by user
            
        Reference: Phase 7, Epic 7.1 - Organizer-Specific Views
        """
        ...
    
    def get_review_items_by_filters(
        self,
        filters: OrganizerInboxFilterDTO,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get review items by filter criteria.
        
        Args:
            filters: OrganizerInboxFilterDTO with filter criteria
            
        Returns:
            List of MatchResultSubmissionDTO matching filters
            
        Reference: Phase 7, Epic 7.1 - Filter-Based Queries
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
        since: Optional[datetime] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """Get pending submissions (awaiting opponent response)."""
        # Method-level import
        from apps.tournaments.models import MatchResultSubmission
        
        # Build query
        queryset = MatchResultSubmission.objects.filter(status='pending')
        
        if tournament_id is not None:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        if since is not None:
            queryset = queryset.filter(submitted_at__gte=since)
        
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
        since: Optional[datetime] = None,
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
        
        if since is not None:
            queryset = queryset.filter(submitted_at__gte=since)
        
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
    
    def get_recent_items_for_organizer(
        self,
        organizer_user_id: int,
        since: Optional[datetime] = None,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get recent submissions for tournaments organized by user.
        
        Reference: Phase 7, Epic 7.1 - Organizer-Specific Views
        """
        # Method-level imports
        from apps.tournaments.models import MatchResultSubmission, Tournament
        
        # Get tournament IDs for this organizer
        tournament_ids = Tournament.objects.filter(
            organizer_id=organizer_user_id
        ).values_list('id', flat=True)
        
        # Build query
        queryset = MatchResultSubmission.objects.filter(
            tournament_id__in=tournament_ids,
            status__in=['pending', 'disputed', 'confirmed'],
        )
        
        if since is not None:
            queryset = queryset.filter(submitted_at__gte=since)
        
        # Order by submitted_at (newest first)
        queryset = queryset.order_by('-submitted_at')
        
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
    
    def get_review_items_by_filters(
        self,
        filters: OrganizerInboxFilterDTO,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Get review items by filter criteria.
        
        Reference: Phase 7, Epic 7.1 - Filter-Based Queries
        """
        # Method-level imports
        from apps.tournaments.models import MatchResultSubmission, DisputeRecord, Tournament
        
        # Validate filters
        filters.validate()
        
        # Build base query
        queryset = MatchResultSubmission.objects.all()
        
        # Filter by tournament_id
        if filters.tournament_id is not None:
            queryset = queryset.filter(tournament_id=filters.tournament_id)
        
        # Filter by organizer_user_id (via tournament)
        if filters.organizer_user_id is not None:
            tournament_ids = Tournament.objects.filter(
                organizer_id=filters.organizer_user_id
            ).values_list('id', flat=True)
            queryset = queryset.filter(tournament_id__in=tournament_ids)
        
        # Filter by status
        if filters.status:
            queryset = queryset.filter(status__in=filters.status)
        
        # Filter by dispute_status (requires join)
        if filters.dispute_status:
            dispute_submission_ids = DisputeRecord.objects.filter(
                status__in=filters.dispute_status
            ).values_list('submission_id', flat=True)
            queryset = queryset.filter(id__in=dispute_submission_ids)
        
        # Filter by date_from
        if filters.date_from is not None:
            queryset = queryset.filter(submitted_at__gte=filters.date_from)
        
        # Filter by date_to
        if filters.date_to is not None:
            queryset = queryset.filter(submitted_at__lte=filters.date_to)
        
        # Order by submitted_at (newest first)
        queryset = queryset.order_by('-submitted_at')
        
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
