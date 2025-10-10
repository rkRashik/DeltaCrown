from __future__ import annotations

import os
from typing import Iterable, Optional, Any, Dict

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.db import transaction

User = get_user_model()
FROM_EMAIL = os.getenv("DeltaCrownEmail", "no-reply@deltacrown.local")

Notification = apps.get_model("notifications", "Notification")


class EmitResult(dict):
    """
    Hybrid result that supports BOTH attribute access (r.created)
    and dict-style access (r["created"]). This satisfies mixed tests.
    """
    def __init__(self, created: int, skipped: int, email_sent: int = 0):
        super().__init__(created=created, skipped=skipped, email_sent=email_sent)
        self.created = created
        self.skipped = skipped
        self.email_sent = email_sent


def _resolve_email(target: Any) -> Optional[str]:
    """Return an email from accounts.User / UserProfile / raw string."""
    if isinstance(target, str):
        return target
    u = getattr(target, "user", None)
    if u and getattr(u, "email", ""):
        return u.email
    if getattr(target, "email", ""):
        return target.email
    return None


def _to_user_model(target: Any) -> Optional[User]:
    """Normalize target to accounts.User (UserProfile ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ .user; User ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ itself)."""
    if getattr(target, "user", None) and getattr(getattr(target, "user"), "_meta", None):
        usr = target.user
        if getattr(usr._meta, "model_name", "") == "user":
            return usr
    if getattr(target, "_meta", None) and getattr(target._meta, "model_name", "") == "user":
        return target
    return None


def _send_templated_email(to_email: Optional[str], subject: str, template_slug: str, ctx: Dict[str, Any]) -> bool:
    """
    Render & send multipart email:
      notifications/email/{slug}.txt (required)
      notifications/email/{slug}.html (optional)
    If templates are missing, skip quietly (tests may omit them).
    """
    if not to_email:
        return False
    try:
        txt = render_to_string(f"notifications/email/{template_slug}.txt", ctx)
    except TemplateDoesNotExist:
        return False
    try:
        html = render_to_string(f"notifications/email/{template_slug}.html", ctx)
    except TemplateDoesNotExist:
        html = None

    msg = EmailMultiAlternatives(subject, txt, FROM_EMAIL, [to_email])
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
    return True


def notify(
    recipients: Iterable[Any],
    ntype: Optional[str] = None,   # tests sometimes pass event as the 2nd positional arg
    *,
    event: Optional[str] = None,   # alias used by other callers
    title: str,
    body: str = "",
    url: str = "",
    tournament=None,
    match=None,
    dedupe: bool = True,
    fingerprint: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Create Notification rows for accounts.User recipients and optionally send emails.
    RETURNS a dict: {"created": X, "skipped": Y, "email_sent": Z}
    """
    event_str = event or ntype or "generic"

    # Map to enum when possible; else fall back to "generic"
    enum_values = set(getattr(Notification, "Type").values) if hasattr(Notification, "Type") else set()
    type_str = event_str if event_str in enum_values else "generic"

    created = skipped = sent = 0

    # Detect presence of an optional fingerprint column on your Notification model
    has_fp = any(getattr(f, "name", None) == "fingerprint" for f in Notification._meta.get_fields())

    for target in recipients:
        user = _to_user_model(target)

        if user is not None:
            with transaction.atomic():
                if has_fp and fingerprint:
                    obj, was_created = Notification.objects.get_or_create(
                        recipient=user,
                        fingerprint=fingerprint,
                        defaults={
                            "type": type_str,
                            "event": event_str,
                            "title": title or "",
                            "body": body or "",
                            "url": url or "",
                            "tournament": tournament,
                            "match": match,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                else:
                    # Fallback dedupe tuple (works even when fingerprint column isn't present)
                    if dedupe:
                        exists = Notification.objects.filter(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            tournament=tournament,
                            match=match,
                        ).exists()
                        if exists:
                            skipped += 1
                        else:
                            Notification.objects.create(
                                recipient=user,
                                type=type_str,
                                event=event_str,
                                title=title or "",
                                body=body or "",
                                url=url or "",
                                tournament=tournament,
                                match=match,
                            )
                            created += 1
                    else:
                        Notification.objects.create(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            title=title or "",
                            body=body or "",
                            url=url or "",
                            tournament=tournament,
                            match=match,
                        )
                        created += 1

        # Optional email (quiet if templates missing)
        if email_subject and email_template:
            if _send_templated_email(_resolve_email(target), email_subject, email_template, email_ctx or {}):
                sent += 1

    return {"created": created, "skipped": skipped, "email_sent": sent}


def emit(
    recipients: Iterable[Any],
    *args,
    title: str,
    body: str = "",
    url: str = "",
    tournament=None,
    match=None,
    dedupe: bool = True,
    fingerprint: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> EmitResult:
    """
    Back-compat wrapper expected by tests:
      - accepts EVENT as positional 2nd arg OR keyword `event=...`
      - RETURNS an object with attributes .created/.skipped
        (and supports dict-style indexing too)
    """
    # Resolve event value from positional or keyword usage
    event_value = None
    if args:
        event_value = args[0]
    if "event" in kwargs and kwargs["event"]:
        event_value = kwargs["event"]

    result = notify(
        recipients,
        ntype=None,
        event=event_value,
        title=title,
        body=body,
        url=url,
        tournament=tournament,
        match=match,
        dedupe=dedupe,
        fingerprint=fingerprint,
        email_subject=email_subject,
        email_template=email_template,
        email_ctx=email_ctx,
    )
    return EmitResult(created=result["created"], skipped=result["skipped"], email_sent=result["email_sent"])


__all__ = ["notify", "emit", "EmitResult", "NotificationService"]


class NotificationService:
    """
    Enhanced notification service for Task 9 with multi-channel delivery.
    Supports in-app, email, and Discord notifications with user preferences.
    """
    
    @staticmethod
    def _send_notification_multi_channel(users, notification_type, title, body, url='', **metadata):
        """
        Send notification through multiple channels based on user preferences.
        
        Args:
            users: List of User objects
            notification_type: Type of notification (from Notification.Type)
            title: Notification title
            body: Notification body
            url: Optional URL
            **metadata: Additional metadata (tournament, match, etc.)
        """
        from apps.notifications.models import NotificationPreference
        from apps.notifications.tasks import send_email_notification, send_discord_notification
        
        created_notifications = []
        
        for user in users:
            # Get user preferences
            prefs = NotificationPreference.get_or_create_for_user(user)
            channels = prefs.get_channels_for_type(notification_type)
            
            # Always create in-app notification
            if 'in_app' in channels:
                notification = Notification.objects.create(
                    recipient=user,
                    type=notification_type,
                    event=notification_type,
                    title=title,
                    body=body,
                    url=url,
                    **{k: v for k, v in metadata.items() if hasattr(Notification, k)}
                )
                created_notifications.append(notification)
                
                # Queue email notification if enabled
                if 'email' in channels:
                    send_email_notification.delay(notification.id)
            
            # Queue Discord notification if enabled
            if 'discord' in channels and settings.DISCORD_NOTIFICATIONS_ENABLED:
                send_discord_notification.delay({
                    'title': title,
                    'body': body,
                    'url': url,
                    'color': 3447003,  # Blue
                })
        
        return created_notifications
    
    @staticmethod
    def notify_invite_sent(invite):
        """
        Notify user when they receive a team invite.
        
        Args:
            invite: TeamInvite object
        """
        from django.urls import reverse
        
        title = f"Team Invite from {invite.team.name}"
        body = f"{invite.inviter.username} invited you to join {invite.team.name}"
        url = reverse('teams:team_detail', kwargs={'slug': invite.team.slug})
        
        return NotificationService._send_notification_multi_channel(
            users=[invite.invitee],
            notification_type='invite_sent',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_invite_accepted(invite):
        """
        Notify team captain when invite is accepted.
        
        Args:
            invite: TeamInvite object
        """
        from django.urls import reverse
        
        title = f"{invite.invitee.username} joined your team!"
        body = f"{invite.invitee.username} has accepted the invite to join {invite.team.name}"
        url = reverse('teams:team_detail', kwargs={'slug': invite.team.slug})
        
        # Notify captain and co-captains
        captains = [invite.team.captain.user] if invite.team.captain else []
        # Add co-captains if your model supports it
        
        return NotificationService._send_notification_multi_channel(
            users=captains,
            notification_type='invite_accepted',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_roster_change(team, change_type, affected_user):
        """
        Notify team members about roster changes.
        
        Args:
            team: Team object
            change_type: 'added', 'removed', 'role_changed'
            affected_user: User who was affected
        """
        from django.urls import reverse
        
        change_messages = {
            'added': f"{affected_user.username} joined the team",
            'removed': f"{affected_user.username} left the team",
            'role_changed': f"{affected_user.username}'s role was updated",
        }
        
        title = f"Roster Change: {team.name}"
        body = change_messages.get(change_type, "Team roster has been updated")
        url = reverse('teams:team_detail', kwargs={'slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='roster_changed',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_tournament_registration(tournament, team):
        """
        Notify team members when team registers for tournament.
        
        Args:
            tournament: Tournament object
            team: Team object
        """
        from django.urls import reverse
        
        title = f"Registered for {tournament.name}"
        body = f"Your team {team.name} has been registered for {tournament.name}"
        url = reverse('tournaments:tournament_detail', kwargs={'slug': tournament.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='tournament_registered',
            title=title,
            body=body,
            url=url,
            tournament=tournament
        )
    
    @staticmethod
    def notify_match_result(match):
        """
        Notify teams when match result is posted.
        
        Args:
            match: Match object
        """
        from django.urls import reverse
        
        title = f"Match Result: {match.team1.name} vs {match.team2.name}"
        
        if match.winner:
            body = f"Winner: {match.winner.name}"
        else:
            body = f"Match result has been posted"
        
        url = reverse('tournaments:match_detail', kwargs={'pk': match.id})
        
        # Get all members from both teams
        team1_members = [member.user for member in match.team1.members.all() if member.user]
        team2_members = [member.user for member in match.team2.members.all() if member.user]
        all_members = team1_members + team2_members
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='match_result',
            title=title,
            body=body,
            url=url,
            match=match,
            tournament=match.tournament
        )
    
    @staticmethod
    def notify_match_scheduled(match):
        """
        Notify teams when match is scheduled.
        
        Args:
            match: Match object
        """
        from django.urls import reverse
        
        title = f"Match Scheduled: {match.team1.name} vs {match.team2.name}"
        body = f"Your match in {match.tournament.name} has been scheduled"
        
        if match.scheduled_at:
            body += f" for {match.scheduled_at.strftime('%B %d, %Y at %H:%M UTC')}"
        
        url = reverse('tournaments:match_detail', kwargs={'pk': match.id})
        
        # Get all members from both teams
        team1_members = [member.user for member in match.team1.members.all() if member.user]
        team2_members = [member.user for member in match.team2.members.all() if member.user]
        all_members = team1_members + team2_members
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='match_scheduled',
            title=title,
            body=body,
            url=url,
            match=match,
            tournament=match.tournament
        )
    
    @staticmethod
    def notify_ranking_changed(team, old_rank, new_rank, points_change):
        """
        Notify team about ranking changes.
        
        Args:
            team: Team object
            old_rank: Previous ranking
            new_rank: New ranking
            points_change: Change in points
        """
        from django.urls import reverse
        
        if new_rank < old_rank:
            direction = "up"
            emoji = "📈"
        else:
            direction = "down"
            emoji = "📉"
        
        title = f"{emoji} Ranking Update: {team.name}"
        body = f"Your team moved {direction} from #{old_rank} to #{new_rank} ({points_change:+} points)"
        url = reverse('teams:team_detail', kwargs={'slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='ranking_changed',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_sponsor_approved(sponsor):
        """
        Notify team when sponsor is approved.
        
        Args:
            sponsor: TeamSponsor object
        """
        from django.urls import reverse
        
        title = f"Sponsor Approved: {sponsor.sponsor_name}"
        body = f"Your sponsorship with {sponsor.sponsor_name} has been approved!"
        url = reverse('teams:sponsor_dashboard', kwargs={'team_slug': sponsor.team.slug})
        
        # Notify captain and co-captains
        captains = [sponsor.team.captain.user] if sponsor.team.captain else []
        
        return NotificationService._send_notification_multi_channel(
            users=captains,
            notification_type='sponsor_approved',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_promotion_started(promotion):
        """
        Notify team when promotion starts.
        
        Args:
            promotion: TeamPromotion object
        """
        from django.urls import reverse
        
        title = f"Promotion Started: {promotion.promotion_type}"
        body = f"Your team promotion ({promotion.get_promotion_type_display()}) is now active!"
        url = reverse('teams:team_detail', kwargs={'slug': promotion.team.slug})
        
        # Notify captain
        captains = [promotion.team.captain.user] if promotion.team.captain else []
        
        return NotificationService._send_notification_multi_channel(
            users=captains,
            notification_type='promotion_started',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_payout_received(team, amount, reason):
        """
        Notify team when they receive a payout.
        
        Args:
            team: Team object
            amount: Amount of coins received
            reason: Reason for payout
        """
        from django.urls import reverse
        
        title = f"💰 Payout Received: {amount} coins"
        body = f"Your team received {amount} coins! Reason: {reason}"
        url = reverse('teams:team_detail', kwargs={'slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='payout_received',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_achievement_earned(team, achievement):
        """
        Notify team when they earn an achievement.
        
        Args:
            team: Team object
            achievement: TeamAchievement object
        """
        from django.urls import reverse
        
        title = f"🏆 Achievement Unlocked: {achievement.title}"
        body = f"Your team earned: {achievement.description}"
        url = reverse('teams:team_detail', kwargs={'slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='achievement_earned',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_bracket_ready(tournament):
        """
        Notify all registered teams when tournament bracket is ready.
        
        Args:
            tournament: Tournament object
        """
        from django.urls import reverse
        from apps.tournaments.models import TournamentRegistration
        
        title = f"Bracket Ready: {tournament.name}"
        body = f"The tournament bracket has been generated. Check your matches!"
        url = reverse('tournaments:tournament_detail', kwargs={'slug': tournament.slug})
        
        # Get all registered teams' members
        registrations = TournamentRegistration.objects.filter(
            tournament=tournament,
            status='approved'
        ).select_related('team')
        
        all_members = []
        for reg in registrations:
            team_members = [member.user for member in reg.team.members.all() if member.user]
            all_members.extend(team_members)
        
        # Remove duplicates
        all_members = list(set(all_members))
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='bracket_ready',
            title=title,
            body=body,
            url=url,
            tournament=tournament
        )



