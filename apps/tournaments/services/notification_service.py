"""
Tournament Notification Service

Handles all tournament-related notifications:
- Registration confirmations
- Match reminders
- Score updates
- Tournament updates
"""

from typing import Dict, List, Optional
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration
from apps.notifications.models import Notification

User = get_user_model()


class TournamentNotificationService:
    """Service for sending tournament notifications"""

    @staticmethod
    def _resolve_waitlist_promotion_recipients(registration: Registration):
        """Return unique users who should receive waitlist-promotion notifications."""
        recipients = []
        seen_ids = set()

        if getattr(registration, 'user_id', None) and getattr(registration, 'user', None):
            recipients.append(registration.user)
            seen_ids.add(registration.user_id)

        team_id = getattr(registration, 'team_id', None)
        if team_id:
            try:
                from apps.organizations.models import TeamMembership

                member_qs = TeamMembership.objects.filter(
                    team_id=team_id,
                    status=TeamMembership.Status.ACTIVE,
                ).select_related('user')

                for member in member_qs:
                    user = getattr(member, 'user', None)
                    if not user or user.id in seen_ids:
                        continue
                    recipients.append(user)
                    seen_ids.add(user.id)
            except Exception:
                # Non-blocking: if team membership resolution fails, keep direct registrant notifications.
                pass

        return recipients
    
    @staticmethod
    def notify_registration_confirmed(registration: Registration):
        """Send confirmation email when registration is approved"""
        tournament = registration.tournament
        user = registration.user
        
        # Create in-app notification
        Notification.objects.create(
            user=user,
            title=f"Registration Confirmed: {tournament.name}",
            message=f"Your registration for {tournament.name} has been confirmed! Good luck!",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/",
            icon='🎮'
        )
        
        # Send email
        subject = f"✅ Registration Confirmed - {tournament.name}"
        html_message = render_to_string('tournaments/emails/registration_confirmed.html', {
            'user': user,
            'tournament': tournament,
            'registration': registration
        })
        
        send_mass_mail([
            (subject, '', settings.DEFAULT_FROM_EMAIL, [user.email])
        ], html_message=html_message, fail_silently=True)
    
    @staticmethod
    def notify_match_scheduled(match: Match):
        """Notify participants when match is scheduled"""
        participants = match.get_participants()
        
        for user in participants:
            if not user:
                continue
                
            Notification.objects.create(
                user=user,
                title=f"Match Scheduled: {match.tournament.name}",
                message=f"Your match in {match.tournament.name} is scheduled for {match.scheduled_time.strftime('%b %d at %I:%M %p')}",
                notification_type='match',
                link=f"/tournaments/{match.tournament.slug}/matches/{match.id}/",
                icon='⚔️'
            )
    
    @staticmethod
    def notify_match_starting_soon(match: Match, minutes_before: int = 15):
        """Remind participants match is starting soon"""
        if match.state != Match.SCHEDULED:
            return
        
        if match.scheduled_time - timezone.now() > timedelta(minutes=minutes_before):
            return
        
        participants = match.get_participants()
        
        for user in participants:
            if not user:
                continue
                
            Notification.objects.create(
                user=user,
                title=f"⏰ Match Starting Soon!",
                message=f"Your match in {match.tournament.name} starts in {minutes_before} minutes!",
                notification_type='match',
                link=f"/tournaments/{match.tournament.slug}/matches/{match.id}/",
                icon='⏰',
                priority='high'
            )
    
    @staticmethod
    def notify_match_completed(match: Match):
        """Notify participants when match is completed"""
        participants = match.get_participants()
        winner = match.get_winner()
        
        for user in participants:
            if not user:
                continue
            
            is_winner = (user.id == match.winner_id)
            
            title = "🏆 Victory!" if is_winner else "Match Complete"
            message = f"You {'won' if is_winner else 'lost'} your match in {match.tournament.name}"
            
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type='match',
                link=f"/tournaments/{match.tournament.slug}/matches/{match.id}/",
                icon='🏆' if is_winner else '📊'
            )
    
    @staticmethod
    def notify_tournament_starting(tournament: Tournament):
        """Notify all participants when tournament is starting"""
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        ).select_related('user')
        
        for registration in registrations:
            user = registration.user
            
            Notification.objects.create(
                user=user,
                title=f"🎮 Tournament Starting: {tournament.name}",
                message=f"{tournament.name} is starting! Check your first match.",
                notification_type='tournament',
                link=f"/tournaments/{tournament.slug}/bracket/",
                icon='🎮',
                priority='high'
            )
    
    @staticmethod
    def notify_check_in_reminder(tournament: Tournament):
        """Remind participants to check in"""
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            checked_in=False,
            is_deleted=False
        ).select_related('user')
        
        for registration in registrations:
            user = registration.user
            
            Notification.objects.create(
                user=user,
                title=f"⚠️ Check-in Required: {tournament.name}",
                message=f"Don't forget to check in for {tournament.name}! Check-in closes soon.",
                notification_type='tournament',
                link=f"/tournaments/{tournament.slug}/lobby/",
                icon='⚠️',
                priority='high'
            )
    
    @staticmethod
    def notify_tournament_completed(
        tournament: Tournament,
        winners: Optional[List] = None,
        *,
        winner_team_ids: Optional[List[int]] = None,
    ) -> int:
        """Notify every player when a tournament concludes.

        Handles BOTH participation modes in one pass:

        * **Solo registration** (``registration.user`` is set) — notify that user.
          Mark as winner if their User.id is in ``winners``.
        * **Team registration** (``registration.team_id`` is set, ``registration.user``
          is null) — fan out one notification per player listed in the
          ``registration.lineup_snapshot`` JSON (the tournament-specific roster
          locked in at registration time, same source the Rosters TOC tab uses).
          Mark every team member as a winner when their team_id appears in
          ``winner_team_ids``.

        **Notification scope (team registrations)**:

        The ``lineup_snapshot`` contains both STARTER and SUBSTITUTE players —
        anyone who was officially rostered for THIS tournament. They all get a
        completion notification. We intentionally do NOT include:

        * Team COACH / ANALYST / MANAGER memberships (only present in the
          general ``TeamMembership`` table, not in lineup_snapshot). Staff
          monitor tournament outcomes via the dashboard, not personal notifs.
        * Players from the team's general roster who weren't on this specific
          tournament's lineup. Notifications are scoped to participation.

        If a future feature wants to notify staff, query TeamMembership for the
        winning team_ids and union the user_ids into the fan-out set.

        Args:
            tournament: The completed tournament.
            winners: List of ``User`` objects whose individual notifications
                should carry the champion copy. Used for solo events.
            winner_team_ids: List of ``Team.id`` values whose members should
                receive champion notifications. Used for team events.

        Returns:
            int: count of Notification rows created.

        Notes:
            * Duplicate user_ids (a player on multiple registered rosters, or
              both winners=[] AND winner_team_ids=[] containing their team)
              receive at most ONE notification per tournament. Winner status
              wins ties — if any registration marks them a winner, they get
              the champion copy.
            * Bulk-fetches all target users in a single ``User.objects.in_bulk``
              call regardless of bracket size.
        """
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).select_related('user').only(
            'id', 'user_id', 'team_id', 'lineup_snapshot',
        )

        winner_user_ids = {
            getattr(w, 'id', None) for w in (winners or []) if w is not None
        }
        winner_user_ids.discard(None)
        winner_team_ids_set = {int(t) for t in (winner_team_ids or []) if t}

        # Phase 1 — collect every (user_id, is_winner) tuple we need to send to.
        # We pre-dedupe by user_id so the same human gets exactly one notification
        # even if they're rostered on multiple confirmed registrations.
        targets: Dict[int, bool] = {}   # user_id -> is_winner (winner wins ties)

        def _mark(uid: int, is_winner: bool):
            if uid not in targets:
                targets[uid] = is_winner
            elif is_winner:
                # Promote to winner if any registration says so.
                targets[uid] = True

        for registration in registrations:
            user = registration.user
            if user is not None:
                # Solo path — user is the participant.
                _mark(user.id, user.id in winner_user_ids)
                continue

            team_id = registration.team_id
            if not team_id:
                # Malformed registration (no user AND no team) — skip silently.
                continue

            is_team_winner = team_id in winner_team_ids_set
            snapshot = registration.lineup_snapshot or []
            if not isinstance(snapshot, list):
                continue
            for entry in snapshot:
                if not isinstance(entry, dict):
                    continue
                uid_raw = entry.get('user_id')
                if not uid_raw:
                    continue
                try:
                    uid = int(uid_raw)
                except (TypeError, ValueError):
                    continue
                _mark(uid, is_team_winner)

        if not targets:
            return 0

        # Phase 2 — bulk-fetch users and create notifications.
        users_map = User.objects.in_bulk(list(targets.keys()))

        sent = 0
        link = f"/tournaments/{tournament.slug}/results/"
        for uid, is_winner in targets.items():
            user = users_map.get(uid)
            if user is None:
                continue
            title = (
                "🏆 Tournament Champion!" if is_winner else "Tournament Complete"
            )
            message = (
                f"{tournament.name} has concluded. "
                + (
                    "Congratulations on your victory!"
                    if is_winner
                    else "Thanks for participating!"
                )
            )
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type='tournament',
                link=link,
                icon='🏆' if is_winner else '🎮',
            )
            sent += 1
        return sent
    
    @staticmethod
    def notify_organizer_announcement(tournament: Tournament, announcement_text: str):
        """Broadcast organizer announcement to all participants"""
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        ).select_related('user')
        
        for registration in registrations:
            user = registration.user
            
            Notification.objects.create(
                user=user,
                title=f"📢 Announcement: {tournament.name}",
                message=announcement_text,
                notification_type='announcement',
                link=f"/tournaments/{tournament.slug}/",
                icon='📢'
            )
    
    @staticmethod
    def notify_waitlist_promotion(registration: Registration, payment_deadline):
        """
        Notify participant they've been promoted from waitlist.
        
        Args:
            registration: Registration that was promoted
            payment_deadline: Datetime when payment must be completed
        """
        tournament = registration.tournament
        recipients = TournamentNotificationService._resolve_waitlist_promotion_recipients(registration)
        if not recipients:
            return

        payment = getattr(registration, 'payment', None)
        payment_status = ((getattr(payment, 'status', '') if payment else '') or '').strip().lower()
        payment_required = bool(tournament.has_entry_fee and payment_status not in {'submitted', 'verified', 'waived'})

        if payment_required:
            next_step_text = (
                f"Next step: complete payment by {payment_deadline.strftime('%b %d at %I:%M %p')} to secure your slot."
            )
            action_label = 'Complete Payment'
            action_url = f"/tournaments/registration/{registration.id}/payment/complete/"
            subject = f"Waitlist Call-Up: Payment Required - {tournament.name}"
        else:
            next_step_text = "Next step: open the tournament hub to review status and check-in requirements."
            action_label = 'Open Hub'
            action_url = f"/tournaments/{tournament.slug}/hub/"
            subject = f"Waitlist Call-Up Confirmed - {tournament.name}"

        title = f"Spot Opened: {tournament.name}"
        message = (
            f"You have been promoted from the waitlist for {tournament.name}. {next_step_text}"
        )
        
        # Create in-app notification
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                event='waitlist_promoted',
                type=Notification.Type.GENERIC,
                title=title,
                body=message,
                message=message,
                url=action_url,
                action_label=action_label,
                action_url=action_url,
                category='tournament',
                tournament_id=tournament.id,
            )
        
        # Send email
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        # Calculate deadline hours
        from django.utils import timezone
        time_diff = payment_deadline - timezone.now()
        deadline_hours = int(time_diff.total_seconds() / 3600)
        
        try:
            for recipient in recipients:
                if not getattr(recipient, 'email', ''):
                    continue
                html_message = render_to_string('tournaments/emails/waitlist_promotion.html', {
                    'user': recipient,
                    'tournament': tournament,
                    'registration': registration,
                    'payment_deadline': payment_deadline,
                    'deadline_hours': deadline_hours,
                    'payment_url': f"{settings.SITE_URL}{action_url}",
                    'payment_required': payment_required,
                    'next_step_text': next_step_text,
                })
                send_mail(
                    subject=subject,
                    message=(
                        f"You have been promoted from the waitlist for {tournament.name}. "
                        f"{next_step_text}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    html_message=html_message,
                    fail_silently=True
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send waitlist promotion email: {e}")
    
    @staticmethod
    def notify_added_to_waitlist(registration: Registration):
        """
        Notify participant they've been added to the waitlist.
        
        Args:
            registration: Registration that was waitlisted
        """
        user = registration.user
        tournament = registration.tournament
        
        # Create in-app notification
        Notification.objects.create(
            user=user,
            title=f"Added to Waitlist: {tournament.name}",
            message=f"Tournament is full. You're #{registration.waitlist_position} on the waitlist. We'll notify you if a spot opens up!",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/",
            icon='⏳'
        )
        
        # Send email
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Waitlisted - {tournament.name}"
        message = f"Hi {user.username},\n\nThe tournament '{tournament.name}' is currently full. You've been added to the waitlist at position #{registration.waitlist_position}.\n\nWe'll notify you immediately if a spot becomes available!\n\nBest regards,\nThe DeltaCrown Team"
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail if email fails
    
    @staticmethod
    def notify_payment_pending(registration: Registration):
        """
        Notify participant their payment is being verified.
        
        Args:
            registration: Registration with pending payment
        """
        user = registration.user
        tournament = registration.tournament
        payment = registration.payment
        
        # Create in-app notification
        Notification.objects.create(
            user=user,
            title=f"Payment Received: {tournament.name}",
            message="Your payment proof is being reviewed. You'll be notified once verified (usually 1-6 hours).",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/",
            icon='⏱'
        )
        
        # Send email
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        subject = f"Payment Received - {tournament.name}"
        
        html_message = render_to_string('tournaments/emails/payment_pending.html', {
            'user': user,
            'tournament': tournament,
            'registration': registration,
            'payment': payment,
            'registration_url': f"{settings.SITE_URL}/tournaments/{tournament.slug}/"
        })
        
        try:
            send_mail(
                subject=subject,
                message="Your payment proof has been received and is being verified.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail if email fails
    
    @staticmethod
    def notify_payment_submitted_organizer(registration: Registration):
        """
        Notify the tournament organizer when a participant submits payment proof.

        Args:
            registration: Registration whose payment was just submitted
        """
        tournament = registration.tournament
        organizer = getattr(tournament, 'organizer', None)
        if not organizer:
            return

        participant_label = (
            registration.user.username if registration.user
            else f"Team #{registration.team_id}"
        )

        Notification.objects.create(
            user=organizer,
            title=f"💳 Payment Submitted: {tournament.name}",
            message=f"{participant_label} has submitted payment proof for {tournament.name}. Please review and verify.",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/registrations/",
            icon='💳',
        )

    @staticmethod
    def notify_payment_rejected(registration: Registration, reason: str = ''):
        """
        Notify participant that their payment proof was rejected.

        Args:
            registration: Registration whose payment was rejected
            reason: Rejection reason shown to the participant
        """
        user = registration.user
        if not user:
            return

        tournament = registration.tournament
        detail = f" Reason: {reason}" if reason else ""

        Notification.objects.create(
            user=user,
            title=f"❌ Payment Rejected: {tournament.name}",
            message=f"Your payment for {tournament.name} was rejected.{detail} Please resubmit with a valid proof.",
            notification_type='tournament',
            link=f"/tournaments/registration/{registration.id}/payment/complete/",
            icon='❌',
            priority='high',
        )

        from django.core.mail import send_mail
        try:
            send_mail(
                subject=f"Payment Rejected – {tournament.name}",
                message=(
                    f"Hi {user.username},\n\n"
                    f"Your payment for {tournament.name} was rejected.{detail}\n\n"
                    f"Please log in and resubmit your payment proof.\n\nDeltaCrown Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

    @staticmethod
    def notify_refund_processed(registration: Registration, refund_amount: str = ''):
        """
        Notify participant that their refund has been processed.

        Args:
            registration: Registration that was refunded
            refund_amount: Optional human-readable amount string (e.g. "৳500")
        """
        user = registration.user
        if not user:
            return

        tournament = registration.tournament
        amount_str = f" of {refund_amount}" if refund_amount else ""

        Notification.objects.create(
            user=user,
            title=f"💰 Refund Processed: {tournament.name}",
            message=f"Your refund{amount_str} for {tournament.name} has been processed. It may take 3-5 business days to reflect.",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/",
            icon='💰',
        )

        from django.core.mail import send_mail
        try:
            send_mail(
                subject=f"Refund Processed – {tournament.name}",
                message=(
                    f"Hi {user.username},\n\n"
                    f"Your refund{amount_str} for {tournament.name} has been processed.\n"
                    f"Please allow 3-5 business days for it to appear.\n\nDeltaCrown Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass



        """
        Notify team captains that a member has requested registration permission.
        
        Args:
            permission_request: TeamRegistrationPermissionRequest instance
        """
        from apps.notifications.models import Notification
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        team = permission_request.team
        tournament = permission_request.tournament
        requester = permission_request.requester
        captains = permission_request.get_team_captains()
        
        # Create in-app notifications for all captains
        for captain in captains:
            Notification.objects.create(
                user=captain,
                title=f"Registration Permission Request: {tournament.name}",
                message=f"{requester.username} wants to register {team.name} for {tournament.name}. Review their request.",
                notification_type='tournament',
                link=f"/teams/{team.slug}/permissions/",
                icon='🔔'
            )
        
        # Send emails to captains
        for captain in captains:
            subject = f"🔔 Registration Permission Request - {team.name}"
            html_message = render_to_string('tournaments/emails/permission_requested.html', {
                'captain': captain,
                'requester': requester,
                'team': team,
                'tournament': tournament,
                'permission_request': permission_request,
                'approve_url': f"{settings.SITE_URL}/teams/{team.slug}/permissions/{permission_request.id}/approve/",
                'reject_url': f"{settings.SITE_URL}/teams/{team.slug}/permissions/{permission_request.id}/reject/"
            })
            
            try:
                send_mail(
                    subject=subject,
                    message=f"{requester.username} has requested permission to register {team.name} for {tournament.name}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[captain.email],
                    html_message=html_message,
                    fail_silently=True
                )
            except Exception:
                pass  # Don't fail if email fails
    
    @staticmethod
    def notify_permission_approved(permission_request):
        """
        Notify requester that their permission has been approved.
        
        Args:
            permission_request: TeamRegistrationPermissionRequest instance
        """
        from apps.notifications.models import Notification
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        team = permission_request.team
        tournament = permission_request.tournament
        requester = permission_request.requester
        approved_by = permission_request.responded_by
        
        # Create in-app notification
        Notification.objects.create(
            user=requester,
            title=f"Permission Approved: {tournament.name}",
            message=f"Your request to register {team.name} for {tournament.name} has been approved! You can now complete registration.",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/register/",
            icon='✅'
        )
        
        # Send email
        subject = f"✅ Permission Approved - {team.name} for {tournament.name}"
        html_message = render_to_string('tournaments/emails/permission_approved.html', {
            'requester': requester,
            'approved_by': approved_by,
            'team': team,
            'tournament': tournament,
            'permission_request': permission_request,
            'registration_url': f"{settings.SITE_URL}/tournaments/{tournament.slug}/register/"
        })
        
        try:
            send_mail(
                subject=subject,
                message=f"Your request to register {team.name} for {tournament.name} has been approved.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[requester.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail if email fails
    
    @staticmethod
    def notify_permission_rejected(permission_request):
        """
        Notify requester that their permission has been rejected.
        
        Args:
            permission_request: TeamRegistrationPermissionRequest instance
        """
        from apps.notifications.models import Notification
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        team = permission_request.team
        tournament = permission_request.tournament
        requester = permission_request.requester
        rejected_by = permission_request.responded_by
        
        # Create in-app notification
        Notification.objects.create(
            user=requester,
            title=f"Permission Declined: {tournament.name}",
            message=f"Your request to register {team.name} for {tournament.name} was declined by {rejected_by.username}.",
            notification_type='tournament',
            link=f"/teams/{team.slug}/",
            icon='❌'
        )
        
        # Send email
        subject = f"❌ Permission Declined - {team.name} for {tournament.name}"
        html_message = render_to_string('tournaments/emails/permission_rejected.html', {
            'requester': requester,
            'rejected_by': rejected_by,
            'team': team,
            'tournament': tournament,
            'permission_request': permission_request,
            'team_url': f"{settings.SITE_URL}/teams/{team.slug}/"
        })
        
        try:
            send_mail(
                subject=subject,
                message=f"Your request to register {team.name} for {tournament.name} was declined.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[requester.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail if email fails

    @staticmethod
    def notify_disqualification(registration: "Registration", reason: str = '') -> None:
        """
        Notify participant their registration has been disqualified.

        Args:
            registration: Registration that was disqualified
            reason: Human-readable disqualification reason
        """
        user = registration.user
        tournament = registration.tournament

        # In-app notification
        Notification.objects.create(
            user=user,
            title=f"Registration Disqualified: {tournament.name}",
            message=(
                f"Your registration for {tournament.name} has been disqualified. "
                + (f"Reason: {reason}" if reason else "Please contact the organizer for details.")
            ),
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/",
            icon='🚫',
            priority='high'
        )

        # Email notification
        from django.core.mail import send_mail
        from django.conf import settings

        subject = f"Registration Disqualified — {tournament.name}"
        body = (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Your registration for {tournament.name} has been disqualified.\n"
            + (f"Reason: {reason}\n\n" if reason else "\n")
            + "Please contact the tournament organizer if you have questions."
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass


