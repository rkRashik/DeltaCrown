"""
Result Submission Adapter - Phase 6, Epic 6.1

Adapter for accessing MatchResultSubmission domain from tournament_ops.

Architecture:
- Protocol-based interface (runtime_checkable)
- Concrete implementation uses method-level ORM imports
- Returns DTOs only (never ORM models)
- Raises tournament_ops exceptions
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from apps.tournament_ops.dtos import MatchResultSubmissionDTO
from apps.tournament_ops.exceptions import (
    ResultSubmissionNotFoundError,
    ResultSubmissionError,
)


@runtime_checkable
class ResultSubmissionAdapterProtocol(Protocol):
    """
    Protocol for result submission domain access.
    
    All methods return DTOs (no ORM models exposed).
    """
    
    def create_submission(
        self,
        match_id: int,
        submitted_by_user_id: int,
        submitted_by_team_id: Optional[int],
        raw_result_payload: dict,
        proof_screenshot_url: Optional[str],
        submitter_notes: str = "",
    ) -> MatchResultSubmissionDTO:
        """
        Create new result submission.
        
        Args:
            match_id: Match ID
            submitted_by_user_id: User ID of submitter
            submitted_by_team_id: Team ID if team tournament
            raw_result_payload: Game-specific result data
            proof_screenshot_url: URL to proof screenshot
            submitter_notes: Optional notes from submitter
            
        Returns:
            MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionError: If creation fails
        """
        ...
    
    def get_submission(self, submission_id: int) -> MatchResultSubmissionDTO:
        """
        Fetch submission by ID.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: If submission doesn't exist
        """
        ...
    
    def get_submissions_for_match(self, match_id: int) -> List[MatchResultSubmissionDTO]:
        """
        Fetch all submissions for a match.
        
        Args:
            match_id: Match ID
            
        Returns:
            List of MatchResultSubmissionDTO
        """
        ...
    
    def update_submission_status(
        self,
        submission_id: int,
        status: str,
        confirmed_by_user_id: Optional[int] = None,
        organizer_notes: Optional[str] = None,
    ) -> MatchResultSubmissionDTO:
        """
        Update submission status.
        
        Args:
            submission_id: Submission ID
            status: New status
            confirmed_by_user_id: User ID who confirmed (if applicable)
            organizer_notes: Notes from organizer (if applicable)
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: If submission doesn't exist
            ResultSubmissionError: If update fails
        """
        ...
    
    def get_pending_submissions_before(
        self,
        deadline: datetime,
    ) -> List[MatchResultSubmissionDTO]:
        """
        Fetch pending submissions with deadline before given time.
        
        Used for auto-confirm Celery task.
        
        Args:
            deadline: Deadline cutoff
            
        Returns:
            List of MatchResultSubmissionDTO
        """
        ...
    
    def update_submission_payload(
        self,
        submission_id: int,
        raw_result_payload: dict,
    ) -> MatchResultSubmissionDTO:
        """
        Update submission's raw_result_payload.
        
        Used in Epic 6.5 when organizer resolves dispute by approving disputed result
        or applying custom result.
        
        Args:
            submission_id: Submission ID
            raw_result_payload: New payload to store
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: If submission doesn't exist
            ResultSubmissionError: If update fails
            
        Reference: Phase 6, Epic 6.5 - Dispute Resolution (approve_dispute, custom_result)
        """
        ...
    
    def update_auto_confirm_deadline(
        self,
        submission_id: int,
        auto_confirm_deadline: datetime,
    ) -> MatchResultSubmissionDTO:
        """
        Update submission's auto_confirm_deadline.
        
        Used in Epic 6.5 when organizer dismisses dispute, restarting 24-hour timer.
        
        Args:
            submission_id: Submission ID
            auto_confirm_deadline: New deadline (typically now + 24 hours)
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: If submission doesn't exist
            ResultSubmissionError: If update fails
            
        Reference: Phase 6, Epic 6.5 - Dispute Resolution (dismiss_dispute)
        """
        ...


class ResultSubmissionAdapter:
    """
    Concrete implementation of ResultSubmissionAdapterProtocol.
    
    Uses method-level ORM imports to avoid cross-domain coupling.
    """
    
    def create_submission(
        self,
        match_id: int,
        submitted_by_user_id: int,
        submitted_by_team_id: Optional[int],
        raw_result_payload: dict,
        proof_screenshot_url: Optional[str],
        submitter_notes: str = "",
    ) -> MatchResultSubmissionDTO:
        """Create new result submission."""
        from apps.tournaments.models import MatchResultSubmission
        from django.utils import timezone
        
        try:
            submission = MatchResultSubmission.objects.create(
                match_id=match_id,
                submitted_by_user_id=submitted_by_user_id,
                submitted_by_team_id=submitted_by_team_id,
                raw_result_payload=raw_result_payload,
                proof_screenshot_url=proof_screenshot_url or "",
                submitter_notes=submitter_notes,
                status=MatchResultSubmission.STATUS_PENDING,
                auto_confirm_deadline=timezone.now() + timedelta(hours=24),
            )
            return MatchResultSubmissionDTO.from_model(submission)
        except Exception as e:
            raise ResultSubmissionError(f"Failed to create submission: {str(e)}")
    
    def get_submission(self, submission_id: int) -> MatchResultSubmissionDTO:
        """Fetch submission by ID."""
        from apps.tournaments.models import MatchResultSubmission
        
        try:
            submission = MatchResultSubmission.objects.get(id=submission_id)
            return MatchResultSubmissionDTO.from_model(submission)
        except MatchResultSubmission.DoesNotExist:
            raise ResultSubmissionNotFoundError(f"Submission {submission_id} not found")
    
    def get_submissions_for_match(self, match_id: int) -> List[MatchResultSubmissionDTO]:
        """Fetch all submissions for a match."""
        from apps.tournaments.models import MatchResultSubmission
        
        submissions = MatchResultSubmission.objects.filter(match_id=match_id).order_by('-submitted_at')
        return [MatchResultSubmissionDTO.from_model(s) for s in submissions]
    
    def update_submission_status(
        self,
        submission_id: int,
        status: str,
        confirmed_by_user_id: Optional[int] = None,
        organizer_notes: Optional[str] = None,
    ) -> MatchResultSubmissionDTO:
        """Update submission status."""
        from apps.tournaments.models import MatchResultSubmission
        from django.utils import timezone
        
        try:
            submission = MatchResultSubmission.objects.get(id=submission_id)
            
            submission.status = status
            
            # Set timestamps based on status
            if status == MatchResultSubmission.STATUS_CONFIRMED and not submission.confirmed_at:
                submission.confirmed_at = timezone.now()
            
            if status == MatchResultSubmission.STATUS_AUTO_CONFIRMED and not submission.confirmed_at:
                submission.confirmed_at = timezone.now()
            
            if status == MatchResultSubmission.STATUS_FINALIZED and not submission.finalized_at:
                submission.finalized_at = timezone.now()
            
            # Set confirmed_by if provided
            if confirmed_by_user_id:
                submission.confirmed_by_user_id = confirmed_by_user_id
            
            # Update organizer notes if provided
            if organizer_notes is not None:
                submission.organizer_notes = organizer_notes
            
            submission.save()
            
            return MatchResultSubmissionDTO.from_model(submission)
        except MatchResultSubmission.DoesNotExist:
            raise ResultSubmissionNotFoundError(f"Submission {submission_id} not found")
        except Exception as e:
            raise ResultSubmissionError(f"Failed to update submission: {str(e)}")
    
    def get_pending_submissions_before(
        self,
        deadline: datetime,
    ) -> List[MatchResultSubmissionDTO]:
        """Fetch pending submissions with deadline before given time."""
        from apps.tournaments.models import MatchResultSubmission
        
        submissions = MatchResultSubmission.objects.filter(
            status=MatchResultSubmission.STATUS_PENDING,
            auto_confirm_deadline__lte=deadline,
        ).order_by('auto_confirm_deadline')
        
        return [MatchResultSubmissionDTO.from_model(s) for s in submissions]
    
    def update_submission_payload(
        self,
        submission_id: int,
        raw_result_payload: Dict[str, Any],
    ) -> MatchResultSubmissionDTO:
        """
        Update submission's raw_result_payload.
        
        Used in Epic 6.5 when organizer resolves dispute by approving disputed result
        or applying custom result.
        
        Args:
            submission_id: Submission ID
            raw_result_payload: New payload to store
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: Submission not found
            ResultSubmissionError: Update failed
            
        Reference: Phase 6, Epic 6.5 - Dispute Resolution (approve_dispute, custom_result)
        """
        from apps.tournaments.models import MatchResultSubmission
        
        try:
            submission = MatchResultSubmission.objects.get(id=submission_id)
            submission.raw_result_payload = raw_result_payload
            submission.save()
            
            return MatchResultSubmissionDTO.from_model(submission)
        except MatchResultSubmission.DoesNotExist:
            raise ResultSubmissionNotFoundError(f"Submission {submission_id} not found")
        except Exception as e:
            raise ResultSubmissionError(f"Failed to update submission payload: {str(e)}")
    
    def update_auto_confirm_deadline(
        self,
        submission_id: int,
        auto_confirm_deadline: datetime,
    ) -> MatchResultSubmissionDTO:
        """
        Update submission's auto_confirm_deadline.
        
        Used in Epic 6.5 when organizer dismisses dispute, restarting 24-hour timer.
        
        Args:
            submission_id: Submission ID
            auto_confirm_deadline: New deadline (typically now + 24 hours)
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            ResultSubmissionNotFoundError: Submission not found
            ResultSubmissionError: Update failed
            
        Reference: Phase 6, Epic 6.5 - Dispute Resolution (dismiss_dispute)
        """
        from apps.tournaments.models import MatchResultSubmission
        
        try:
            submission = MatchResultSubmission.objects.get(id=submission_id)
            submission.auto_confirm_deadline = auto_confirm_deadline
            submission.save()
            
            return MatchResultSubmissionDTO.from_model(submission)
        except MatchResultSubmission.DoesNotExist:
            raise ResultSubmissionNotFoundError(f"Submission {submission_id} not found")
        except Exception as e:
            raise ResultSubmissionError(f"Failed to update auto_confirm_deadline: {str(e)}")
