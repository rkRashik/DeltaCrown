"""
Tournament Notification Service

Handles all tournament-related notifications:
- Registration confirmations
- Match reminders
- Score updates
- Tournament updates
"""

from typing import List, Optional
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration
from apps.notifications.models import Notification


class TournamentNotificationService:
    """Service for sending tournament notifications"""
    
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
    def notify_tournament_completed(tournament: Tournament, winners: List):
        """Notify all participants when tournament is complete"""
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        ).select_related('user')
        
        for registration in registrations:
            user = registration.user
            
            # Check if user is a winner
            is_winner = any(w.id == user.id for w in winners if w)
            
            title = "🏆 Tournament Champion!" if is_winner else "Tournament Complete"
            message = f"{tournament.name} has concluded. {'Congratulations on your victory!' if is_winner else 'Thanks for participating!'}"
            
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type='tournament',
                link=f"/tournaments/{tournament.slug}/results/",
                icon='🏆' if is_winner else '🎮'
            )
    
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
        user = registration.user
        tournament = registration.tournament
        
        # Create in-app notification
        Notification.objects.create(
            user=user,
            title=f"🎉 Promoted from Waitlist: {tournament.name}",
            message=f"A spot opened up! Complete your payment by {payment_deadline.strftime('%b %d at %I:%M %p')} to secure your spot.",
            notification_type='tournament',
            link=f"/tournaments/{tournament.slug}/register/payment/",
            icon='🎉',
            priority='high'
        )
        
        # Send email
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        subject = f"🎉 You've Been Promoted - {tournament.name}"
        
        # Calculate deadline hours
        from django.utils import timezone
        time_diff = payment_deadline - timezone.now()
        deadline_hours = int(time_diff.total_seconds() / 3600)
        
        html_message = render_to_string('tournaments/emails/waitlist_promotion.html', {
            'user': user,
            'tournament': tournament,
            'registration': registration,
            'payment_deadline': payment_deadline,
            'deadline_hours': deadline_hours,
            'payment_url': f"{settings.SITE_URL}/tournaments/{tournament.slug}/register/payment/"
        })
        
        try:
            send_mail(
                subject=subject,
                message=f"You've been promoted from the waitlist for {tournament.name}! Complete your payment within {deadline_hours} hours.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
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
    def notify_permission_requested(permission_request):
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


