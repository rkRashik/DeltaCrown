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
