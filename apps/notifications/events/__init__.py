"""
Notification Event Handlers

Replaces signal-based notification triggers with event-driven notifications.
Listens to events from other apps and sends notifications accordingly.
"""
import logging
from django.apps import apps

from apps.core.events import event_bus
from apps.notifications.services import notify

logger = logging.getLogger(__name__)


def _profile_from_team(team):
    """Helper to get captain UserProfile from Team"""
    return getattr(team, "captain", None)


# ============================================================================
# Registration Event Handlers
# ============================================================================

def notify_registration_confirmed(event):
    """
    Send notification when registration is confirmed.
    
    Replaces: registration_confirmed signal handler
    Triggered by: RegistrationConfirmedEvent
    """
    try:
        registration_id = event.data.get('registration_id')
        Registration = apps.get_model("tournaments", "Registration")
        Notification = apps.get_model("notifications", "Notification")
        
        registration = Registration.objects.select_related(
            'tournament', 'user', 'team', 'team__captain'
        ).get(id=registration_id)
        
        recipients = []
        
        # Solo registration
        if registration.user:
            recipients.append(registration.user)
        
        # Team registration
        if registration.team:
            captain = _profile_from_team(registration.team)
            if captain:
                recipients.append(captain)
        
        if recipients:
            notify(
                recipients,
                Notification.Type.REG_CONFIRMED,
                title=f"Registration confirmed · {registration.tournament.name}",
                body="You're in! Watch for scheduling updates.",
                url=f"/t/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Registration confirmed – {registration.tournament.name}",
                email_template="reg_confirmed",
                email_ctx={"t": registration.tournament, "r": registration},
            )
            
            logger.info(
                f"✅ Sent registration confirmation notification: "
                f"Tournament={registration.tournament.name}, Recipients={len(recipients)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to send registration notification: {e}", exc_info=True)


# ============================================================================
# Match Event Handlers  
# ============================================================================

def notify_match_scheduled(event):
    """
    Send notification when match is scheduled.
    
    Replaces: match_events signal handler (scheduling part)
    Triggered by: MatchScheduledEvent
    """
    try:
        match_id = event.data.get('match_id')
        Match = apps.get_model("tournaments", "Match")
        Notification = apps.get_model("notifications", "Notification")
        
        match = Match.objects.select_related(
            'tournament', 
            'user_a', 'user_b',
            'team_a', 'team_a__captain',
            'team_b', 'team_b__captain'
        ).get(id=match_id)
        
        tournament = match.tournament
        recipients = []
        
        # Get participants
        participant_a = match.user_a or _profile_from_team(match.team_a)
        participant_b = match.user_b or _profile_from_team(match.team_b)
        
        if participant_a:
            recipients.append(participant_a)
        if participant_b:
            recipients.append(participant_b)
        
        if recipients:
            notify(
                recipients,
                Notification.Type.MATCH_SCHEDULED,
                title=f"Match scheduled · {tournament.name}",
                body=f"Round {match.round_no}, Position {match.position}.",
                url=f"/t/{tournament.slug}/",
                tournament=tournament,
                match=match,
                dedupe=True,
                email_subject=f"[DeltaCrown] Match scheduled – {tournament.name}",
                email_template="match_scheduled",
                email_ctx={"t": tournament, "m": match},
            )
            
            logger.info(
                f"✅ Sent match scheduled notification: "
                f"Match={match.id}, Recipients={len(recipients)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to send match scheduled notification: {e}", exc_info=True)


def notify_result_verified(event):
    """
    Send notification when match result is verified.
    
    Replaces: match_events signal handler (result verified part)
    Triggered by: MatchResultVerifiedEvent
    """
    try:
        match_id = event.data.get('match_id')
        Match = apps.get_model("tournaments", "Match")
        Notification = apps.get_model("notifications", "Notification")
        
        match = Match.objects.select_related(
            'tournament',
            'winner_user',
            'winner_team', 'winner_team__captain'
        ).get(id=match_id)
        
        tournament = match.tournament
        winner = match.winner_user or _profile_from_team(match.winner_team)
        
        if winner:
            notify(
                [winner],
                Notification.Type.RESULT_VERIFIED,
                title="Result verified — you advance to next round",
                url=f"/t/{tournament.slug}/",
                tournament=tournament,
                match=match,
                dedupe=True,
                email_subject=f"[DeltaCrown] Result verified – {tournament.name}",
                email_template="result_verified",
                email_ctx={"t": tournament, "m": match},
            )
            
            logger.info(
                f"✅ Sent result verified notification: "
                f"Match={match.id}, Winner={winner}"
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to send result verified notification: {e}", exc_info=True)


# ============================================================================
# Registration Function
# ============================================================================

def register_notification_event_handlers():
    """Register all notification event handlers with the event bus"""
    
    # Registration events
    event_bus.subscribe(
        'registration.confirmed',
        notify_registration_confirmed,
        name='notify_registration_confirmed',
        priority=50  # Notifications are not critical, run after core handlers
    )
    
    # Match events
    event_bus.subscribe(
        'match.scheduled',
        notify_match_scheduled,
        name='notify_match_scheduled',
        priority=50
    )
    
    event_bus.subscribe(
        'match.result_verified',
        notify_result_verified,
        name='notify_result_verified',
        priority=50
    )
    
    logger.info("📢 Registered notification event handlers")


# Export handlers for testing
__all__ = [
    'notify_registration_confirmed',
    'notify_match_scheduled',
    'notify_result_verified',
    'register_notification_event_handlers',
]
