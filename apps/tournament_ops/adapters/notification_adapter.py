"""
Notification Adapter — wired to apps.notifications.services.notify().

Protocol and implementation for notification system integration.
All methods fire-and-forget; failures are logged but never block callers.
"""

import logging
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tournament_ops.dtos import (
        MatchResultSubmissionDTO,
        DisputeDTO,
        DisputeResolutionDTO,
    )

logger = logging.getLogger(__name__)


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
    Notification adapter wired to apps.notifications.services.notify().
    
    All methods are fire-and-forget: failures are logged but never propagated.
    Tests should mock this adapter to verify notification calls.
    """
    
    def _get_user(self, user_id: int):
        """Resolve user_id → User model instance for notify() recipients."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning("NotificationAdapter: user %d not found", user_id)
            return None
    
    def _notify(self, recipients, *, event: str, title: str, body: str = "",
                url: str = "", tournament_id=None, match_id=None, **kwargs):
        """Central dispatcher — wraps notifications.services.notify()."""
        try:
            from apps.notifications.services import notify
            notify(
                recipients=[r for r in recipients if r is not None],
                event=event,
                title=title,
                body=body,
                url=url,
                tournament_id=tournament_id,
                match_id=match_id,
            )
        except Exception as e:
            logger.error("NotificationAdapter._notify failed (event=%s): %s", event, e)
    
    def notify_submission_created(
        self,
        submission_dto: "MatchResultSubmissionDTO",
        opponent_user_id: int,
    ) -> None:
        """Notify opponent when a result submission is created."""
        user = self._get_user(opponent_user_id)
        if not user:
            return
        self._notify(
            [user],
            event="match.result_submitted",
            title="Match Result Submitted",
            body=f"Your opponent submitted a result for match #{getattr(submission_dto, 'match_id', '?')}. "
                 f"Please review and confirm or dispute within 24 hours.",
            match_id=getattr(submission_dto, 'match_id', None),
            tournament_id=getattr(submission_dto, 'tournament_id', None),
        )
    
    def notify_dispute_created(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """Notify submitter and organizer when a dispute is created."""
        recipients = []
        submitter_id = getattr(submission_dto, 'submitted_by_user_id', None)
        if submitter_id:
            user = self._get_user(submitter_id)
            if user:
                recipients.append(user)
        # TODO: Resolve organizer from tournament when organizer service available
        
        if recipients:
            self._notify(
                recipients,
                event="match.result_disputed",
                title="Match Result Disputed",
                body=f"A dispute has been filed for match #{getattr(submission_dto, 'match_id', '?')}. "
                     f"Reason: {getattr(dispute_dto, 'reason', 'Not specified')}",
                match_id=getattr(submission_dto, 'match_id', None),
                tournament_id=getattr(submission_dto, 'tournament_id', None),
            )
    
    def notify_evidence_added(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """Notify parties when evidence is added to a dispute."""
        # Collect unique user IDs from dispute parties
        user_ids = set()
        for attr in ('submitted_by_user_id', 'disputed_by_user_id'):
            uid = getattr(dispute_dto, attr, None) or getattr(submission_dto, attr, None)
            if uid:
                user_ids.add(uid)
        
        recipients = [u for u in (self._get_user(uid) for uid in user_ids) if u]
        if recipients:
            self._notify(
                recipients,
                event="dispute.evidence_added",
                title="New Evidence Added",
                body=f"New evidence was added to the dispute for match #{getattr(submission_dto, 'match_id', '?')}.",
                match_id=getattr(submission_dto, 'match_id', None),
                tournament_id=getattr(submission_dto, 'tournament_id', None),
            )
    
    def notify_dispute_resolved(
        self,
        dispute_dto: "DisputeDTO",
        submission_dto: "MatchResultSubmissionDTO",
        resolution_dto: "DisputeResolutionDTO",
    ) -> None:
        """Notify both parties when organizer resolves a dispute."""
        user_ids = set()
        for attr in ('submitted_by_user_id', 'disputed_by_user_id'):
            uid = getattr(dispute_dto, attr, None) or getattr(submission_dto, attr, None)
            if uid:
                user_ids.add(uid)
        
        recipients = [u for u in (self._get_user(uid) for uid in user_ids) if u]
        resolution_type = getattr(resolution_dto, 'resolution_type', 'resolved')
        
        if recipients:
            self._notify(
                recipients,
                event="dispute.resolved",
                title="Dispute Resolved",
                body=f"The dispute for match #{getattr(submission_dto, 'match_id', '?')} "
                     f"has been resolved ({resolution_type}).",
                match_id=getattr(submission_dto, 'match_id', None),
                tournament_id=getattr(submission_dto, 'tournament_id', None),
            )
    
    def notify_auto_confirmed(
        self,
        submission_dto: "MatchResultSubmissionDTO",
    ) -> None:
        """Notify submitter when result is auto-confirmed after 24h timeout."""
        submitter_id = getattr(submission_dto, 'submitted_by_user_id', None)
        if not submitter_id:
            return
        user = self._get_user(submitter_id)
        if not user:
            return
        self._notify(
            [user],
            event="match.result_auto_confirmed",
            title="Result Auto-Confirmed",
            body=f"Your result submission for match #{getattr(submission_dto, 'match_id', '?')} "
                 f"was automatically confirmed (no response within 24 hours).",
            match_id=getattr(submission_dto, 'match_id', None),
            tournament_id=getattr(submission_dto, 'tournament_id', None),
        )
