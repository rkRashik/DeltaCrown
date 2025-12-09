"""
Notification Adapter - Phase 6, Epic 6.5

Protocol and implementation for notification system integration.

Phase 6: No-op implementation (notifications mocked in tests)
Phase 10: Full integration with email, Discord, in-app notifications

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Notification System Integration)
"""

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tournament_ops.dtos import (
        MatchResultSubmissionDTO,
        DisputeDTO,
        DisputeResolutionDTO,
    )


class NotificationAdapterProtocol(Protocol):
    """
    Protocol for notification system integration.
    
    Phase 6: Methods defined, implementations are no-ops with TODOs
    Phase 10: Full implementation with email/Discord/in-app notifications
    
    All methods are fire-and-forget (no return value).
    Failures should be logged but not block the calling workflow.
    
    Reference: Phase 6, Epic 6.5 - Notification Integration
              Phase 10, Epic 10.3 - Email Notifications
              Phase 10, Epic 10.4 - Discord Webhooks
    """
    
    def notify_submission_created(
        self,
        submission_dto: "MatchResultSubmissionDTO",
        opponent_user_id: int,
    ) -> None:
        """
        Notify opponent when result submission created.
        
        Notification should include:
        - Match details (tournament, teams, round)
        - Submission deadline (24-hour timer)
        - Call-to-action: Review and confirm/dispute
        
        Channels (Phase 10):
        - Email to opponent
        - In-app notification
        - Optional: Discord DM if configured
        
        Args:
            submission_dto: Submission details
            opponent_user_id: Opponent user to notify
            
        Reference: Epic 6.1 - Result Submission Notifications
        """
        ...
    
    def notify_dispute_created(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        Notify submitter and organizer when dispute created.
        
        Notification should include:
        - Dispute reason
        - Disputer user
        - Match details
        - Call-to-action: Review dispute in organizer inbox
        
        Channels (Phase 10):
        - Email to submitter + organizer
        - In-app notification
        - Optional: Discord webhook to organizer channel
        
        Args:
            dispute_dto: Dispute details
            submission_dto: Related submission
            
        Reference: Epic 6.2 - Dispute Created Notifications
        """
        ...
    
    def notify_evidence_added(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        Notify both parties and organizer when evidence added to dispute.
        
        Notification should include:
        - Evidence type (screenshot, video, etc.)
        - Uploader user
        - Match/dispute details
        
        Channels (Phase 10):
        - Email to all parties
        - In-app notification
        
        Args:
            dispute_dto: Dispute details (includes evidence)
            submission_dto: Related submission
            
        Reference: Epic 6.2 - Evidence Added Notifications
        """
        ...
    
    def notify_dispute_resolved(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
        resolution_dto: "DisputeResolutionDTO",
    ) -> None:
        """
        Notify both parties when organizer resolves dispute.
        
        Notification should include:
        - Resolution type (approve original, approve dispute, custom, dismiss)
        - Resolution notes
        - Final match result
        - Next steps (if dismiss: 24-hour timer restarted)
        
        Channels (Phase 10):
        - Email to both parties
        - In-app notification
        - Optional: Discord DM if configured
        
        Args:
            dispute_dto: Dispute details
            submission_dto: Related submission
            resolution_dto: Resolution decision details
            
        Reference: Epic 6.5 - Dispute Resolution Notifications
        """
        ...
    
    def notify_auto_confirmed(
        self,
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        Notify submitter when result auto-confirmed after 24-hour deadline.
        
        Notification should include:
        - Match details
        - Final result
        - Next steps (bracket progression)
        
        Channels (Phase 10):
        - Email to submitter
        - In-app notification
        
        Args:
            submission_dto: Auto-confirmed submission
            
        Reference: Epic 6.1 - Auto-Confirm Notifications
        """
        ...


class NotificationAdapter:
    """
    No-op notification adapter for Phase 6.
    
    All methods are stubs with TODO comments for Phase 10 implementation.
    Tests will mock this adapter to verify notification calls.
    
    Phase 10 Implementation Plan:
    - Epic 10.3: Email notifications via SendGrid/AWS SES
    - Epic 10.4: Discord webhooks for organizer notifications
    - Epic 10.5: In-app notification system
    
    Reference: Phase 6, Epic 6.5 - Notification Adapter (No-op)
              Phase 10 - Full Notification System
    """
    
    def notify_submission_created(
        self,
        submission_dto: "MatchResultSubmissionDTO",
        opponent_user_id: int,
    ) -> None:
        """
        TODO (Phase 10): Send notification to opponent about new submission.
        
        Implementation Plan:
        - Fetch opponent user email/Discord from UserAdapter
        - Render email template with submission details
        - Send via email service (SendGrid/AWS SES)
        - Create in-app notification record
        - Optional: Send Discord DM if user configured
        
        Reference: Phase 10, Epic 10.3 - Email Notifications
        """
        # No-op for Phase 6
        pass
    
    def notify_dispute_created(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        TODO (Phase 10): Send notification about new dispute.
        
        Implementation Plan:
        - Fetch submitter + organizer contacts
        - Render dispute notification template
        - Send emails to both parties
        - Create in-app notifications
        - Send Discord webhook to organizer channel
        
        Reference: Phase 10, Epic 10.3 - Email Notifications
                  Phase 10, Epic 10.4 - Discord Webhooks
        """
        # No-op for Phase 6
        pass
    
    def notify_evidence_added(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        TODO (Phase 10): Send notification about new evidence.
        
        Implementation Plan:
        - Fetch all dispute parties + organizer
        - Render evidence notification template
        - Send emails
        - Create in-app notifications
        
        Reference: Phase 10, Epic 10.3 - Email Notifications
        """
        # No-op for Phase 6
        pass
    
    def notify_dispute_resolved(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
        resolution_dto: "DisputeResolutionDTO",
    ) -> None:
        """
        TODO (Phase 10): Send notification about dispute resolution.
        
        Implementation Plan:
        - Fetch both parties (submitter + disputer)
        - Render resolution notification template with:
          - Resolution type
          - Resolution notes
          - Final match result
          - Next steps
        - Send emails to both parties
        - Create in-app notifications
        - Optional: Discord DM to both parties
        
        Reference: Phase 10, Epic 10.3 - Email Notifications
                  Phase 10, Epic 10.4 - Discord Webhooks
        """
        # No-op for Phase 6
        pass
    
    def notify_auto_confirmed(
        self,
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """
        TODO (Phase 10): Send notification about auto-confirmation.
        
        Implementation Plan:
        - Fetch submitter contact
        - Render auto-confirm notification template
        - Send email
        - Create in-app notification
        
        Reference: Phase 10, Epic 10.3 - Email Notifications
        """
        # No-op for Phase 6
        pass
