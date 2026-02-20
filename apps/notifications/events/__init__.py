"""
Notification Event Handlers

Replaces signal-based notification triggers with event-driven notifications.
Listens to events from other apps and sends notifications accordingly.

P4-T06: Extended to cover all registration/payment lifecycle events.
"""
import logging
from django.apps import apps

from apps.core.events import event_bus
from apps.notifications.services import notify

logger = logging.getLogger(__name__)


def _profile_from_team(team):
    """Helper to get captain UserProfile from Team"""
    return getattr(team, "captain", None)


def _safe_get_registration(registration_id):
    """Safely fetch a Registration with related objects."""
    Registration = apps.get_model("tournaments", "Registration")
    return Registration.objects.select_related('tournament', 'user').get(id=registration_id)


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


def notify_registration_submitted(event):
    """Send notification when a registration is submitted (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.TOURNAMENT_REGISTERED,
                title=f"Registration submitted · {registration.tournament.name}",
                body="Your registration has been submitted and is under review.",
                url=f"/tournaments/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Registration received – {registration.tournament.name}",
                email_template="registration_confirmed",
                email_ctx={"t": registration.tournament, "r": registration},
            )

        # Organizer aggregated notification
        _notify_organizer_aggregate(
            registration.tournament,
            f"New registration: {registration.user.username if registration.user else 'Team'}",
        )
    except Exception as e:
        logger.error("❌ notify_registration_submitted failed: %s", e, exc_info=True)


def notify_registration_rejected(event):
    """Send notification when a registration is rejected (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.GENERIC,
                title=f"Registration declined · {registration.tournament.name}",
                body=event.data.get('reason', 'Your registration was not approved.'),
                url=f"/tournaments/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Registration update – {registration.tournament.name}",
                email_template="registration_rejected",
                email_ctx={"t": registration.tournament, "r": registration,
                           "reason": event.data.get('reason', '')},
            )
    except Exception as e:
        logger.error("❌ notify_registration_rejected failed: %s", e, exc_info=True)


def notify_payment_submitted(event):
    """Send notification when payment proof is submitted (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.GENERIC,
                title=f"Payment received · {registration.tournament.name}",
                body="Your payment is being reviewed. You'll be notified once verified.",
                url=f"/tournaments/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Payment received – {registration.tournament.name}",
                email_template="payment_pending",
                email_ctx={"t": registration.tournament, "r": registration},
            )
    except Exception as e:
        logger.error("❌ notify_payment_submitted failed: %s", e, exc_info=True)


def notify_payment_verified(event):
    """Send notification when payment is verified (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.PAYMENT_VERIFIED,
                title=f"Payment verified · {registration.tournament.name}",
                body="Your payment has been confirmed. You're all set!",
                url=f"/tournaments/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Payment confirmed – {registration.tournament.name}",
                email_template="payment_verified",
                email_ctx={"t": registration.tournament, "r": registration},
            )
    except Exception as e:
        logger.error("❌ notify_payment_verified failed: %s", e, exc_info=True)


def notify_payment_rejected(event):
    """Send notification when payment is rejected (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.GENERIC,
                title=f"Payment issue · {registration.tournament.name}",
                body=event.data.get('reason', 'Your payment could not be verified. Please resubmit.'),
                url=f"/tournaments/{registration.tournament.slug}/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Payment update – {registration.tournament.name}",
                email_template="payment_verified",
                email_ctx={"t": registration.tournament, "r": registration,
                           "reason": event.data.get('reason', '')},
            )
    except Exception as e:
        logger.error("❌ notify_payment_rejected failed: %s", e, exc_info=True)


def notify_waitlist_promoted(event):
    """Send notification when a participant is promoted from the waitlist (P4-T06)."""
    try:
        registration = _safe_get_registration(event.data.get('registration_id'))
        Notification = apps.get_model("notifications", "Notification")

        if registration.user:
            notify(
                [registration.user],
                Notification.Type.GENERIC,
                title=f"Promoted from waitlist · {registration.tournament.name}",
                body="A spot opened up! Complete your registration to secure it.",
                url=f"/tournaments/{registration.tournament.slug}/register/",
                tournament=registration.tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Spot available – {registration.tournament.name}",
                email_template="waitlist_promotion",
                email_ctx={"t": registration.tournament, "r": registration},
            )
    except Exception as e:
        logger.error("❌ notify_waitlist_promoted failed: %s", e, exc_info=True)


def notify_checkin_open(event):
    """Send notification when check-in opens for a tournament (P4-T06)."""
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        Registration = apps.get_model("tournaments", "Registration")
        Notification = apps.get_model("notifications", "Notification")

        tournament = Tournament.objects.get(id=event.data.get('tournament_id'))
        confirmed_users = Registration.objects.filter(
            tournament=tournament,
            status='confirmed',
            is_deleted=False,
            user__isnull=False,
        ).values_list('user', flat=True)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipients = list(User.objects.filter(id__in=confirmed_users))

        if recipients:
            notify(
                recipients,
                Notification.Type.CHECKIN_OPEN,
                title=f"Check-in is open · {tournament.name}",
                body="Check in now to confirm your participation.",
                url=f"/tournaments/{tournament.slug}/",
                tournament=tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Check-in open – {tournament.name}",
                email_template="custom_notification",
                email_ctx={"t": tournament, "message": "Check-in is now open."},
            )
    except Exception as e:
        logger.error("❌ notify_checkin_open failed: %s", e, exc_info=True)


def notify_tournament_cancelled(event):
    """Send notification when a tournament is cancelled (P4-T06)."""
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        Registration = apps.get_model("tournaments", "Registration")
        Notification = apps.get_model("notifications", "Notification")

        tournament = Tournament.objects.get(id=event.data.get('tournament_id'))
        registered_users = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            user__isnull=False,
        ).exclude(
            status__in=['cancelled', 'rejected']
        ).values_list('user', flat=True)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipients = list(User.objects.filter(id__in=registered_users))

        if recipients:
            notify(
                recipients,
                Notification.Type.GENERIC,
                title=f"Tournament cancelled · {tournament.name}",
                body="This tournament has been cancelled. Check your email for refund details.",
                url=f"/tournaments/{tournament.slug}/",
                tournament=tournament,
                dedupe=True,
                email_subject=f"[DeltaCrown] Tournament cancelled – {tournament.name}",
                email_template="custom_notification",
                email_ctx={"t": tournament, "message": "This tournament has been cancelled."},
            )
    except Exception as e:
        logger.error("❌ notify_tournament_cancelled failed: %s", e, exc_info=True)


# ============================================================================
# Organizer Aggregated Notifications
# ============================================================================

def _notify_organizer_aggregate(tournament, summary_text: str):
    """
    Send an aggregated notification to the tournament organizer.
    Uses dedupe to avoid per-registration spam.
    """
    try:
        Notification = apps.get_model("notifications", "Notification")
        organizer = getattr(tournament, 'organizer', None)
        if not organizer:
            return

        notify(
            [organizer],
            Notification.Type.GENERIC,
            title=f"Activity · {tournament.name}",
            body=summary_text,
            url=f"/tournaments/{tournament.slug}/manage/participants/",
            tournament=tournament,
            dedupe=False,  # Organizer gets each one, but they're concise
        )
    except Exception as e:
        logger.error("❌ Organizer notification failed: %s", e, exc_info=True)


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
        priority=50
    )
    
    event_bus.subscribe(
        'registration.created',
        notify_registration_submitted,
        name='notify_registration_submitted',
        priority=50
    )

    event_bus.subscribe(
        'registration.rejected',
        notify_registration_rejected,
        name='notify_registration_rejected',
        priority=50
    )

    # Payment events
    event_bus.subscribe(
        'payment.submitted',
        notify_payment_submitted,
        name='notify_payment_submitted',
        priority=50
    )

    event_bus.subscribe(
        'payment.verified',
        notify_payment_verified,
        name='notify_payment_verified',
        priority=50
    )

    event_bus.subscribe(
        'payment.rejected',
        notify_payment_rejected,
        name='notify_payment_rejected',
        priority=50
    )

    # Waitlist
    event_bus.subscribe(
        'registration.waitlist_promoted',
        notify_waitlist_promoted,
        name='notify_waitlist_promoted',
        priority=50
    )

    # Tournament lifecycle
    event_bus.subscribe(
        'tournament.checkin_open',
        notify_checkin_open,
        name='notify_checkin_open',
        priority=50
    )

    event_bus.subscribe(
        'tournament.cancelled',
        notify_tournament_cancelled,
        name='notify_tournament_cancelled',
        priority=50
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
    'notify_registration_submitted',
    'notify_registration_rejected',
    'notify_payment_submitted',
    'notify_payment_verified',
    'notify_payment_rejected',
    'notify_waitlist_promoted',
    'notify_checkin_open',
    'notify_tournament_cancelled',
    'notify_match_scheduled',
    'notify_result_verified',
    'register_notification_event_handlers',
]
