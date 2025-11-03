"""
Tournament Event Handlers

Replaces signal handlers from tournaments/signals.py with explicit event handlers.
Registered with Event Bus for loose coupling.
"""
import logging
from django.apps import apps
from django.core.exceptions import ValidationError

from apps.core.events.bus import event_bus

logger = logging.getLogger(__name__)


# ============================================================================
# Tournament Created Handlers
# ============================================================================

def create_tournament_settings(event):
    """
    Create TournamentSettings when tournament is created.
    
    Replaces: _ensure_tournament_settings signal
    """
    try:
        tournament_id = event.data['tournament_id']
        Settings = apps.get_model("tournaments", "TournamentSettings")
        
        # Use get_or_create - all fields are nullable so no defaults needed
        settings, created = Settings.objects.get_or_create(
            tournament_id=tournament_id
        )
        
        if created:
            logger.info(f"✅ Created TournamentSettings for tournament {tournament_id}")
        else:
            logger.debug(f"TournamentSettings already exists for tournament {tournament_id}")
            
    except Exception as e:
        logger.error(f"❌ Failed to create TournamentSettings: {e}", exc_info=True)


def create_game_config(event):
    """
    Create game-specific config when tournament is created.
    
    Replaces: _ensure_game_config_for_tournament signal
    """
    try:
        tournament_id = event.data['tournament_id']
        game = event.data.get('game')
        
        if not game:
            logger.debug(f"No game specified for tournament {tournament_id}")
            return
        
        if game == "valorant":
            try:
                ValorantConfig = apps.get_model("game_valorant", "ValorantConfig")
                config, created = ValorantConfig.objects.get_or_create(tournament_id=tournament_id)
                
                if created:
                    logger.info(f"✅ Created ValorantConfig for tournament {tournament_id}")
                    
            except LookupError:
                logger.debug("game_valorant app not installed")
                
        elif game == "efootball":
            try:
                EfootballConfig = apps.get_model("game_efootball", "EfootballConfig")
                config, created = EfootballConfig.objects.get_or_create(tournament_id=tournament_id)
                
                if created:
                    logger.info(f"✅ Created EfootballConfig for tournament {tournament_id}")
                    
            except LookupError:
                logger.debug("game_efootball app not installed")
        
    except Exception as e:
        logger.error(f"❌ Failed to create game config: {e}")


# ============================================================================
# Registration Created Handlers
# ============================================================================

def create_payment_verification(event):
    """
    Create PaymentVerification when registration is created.
    
    Replaces: _ensure_payment_verification signal
    """
    try:
        registration_id = event.data['registration_id']
        PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
        
        pv, created = PaymentVerification.objects.get_or_create(registration_id=registration_id)
        
        if created:
            logger.info(f"✅ Created PaymentVerification for registration {registration_id}")
        else:
            logger.debug(f"PaymentVerification already exists for registration {registration_id}")
            
    except Exception as e:
        logger.error(f"❌ Failed to create PaymentVerification: {e}")


def set_team_game_from_registration(event):
    """
    Set team's game field when team registers for tournament.
    
    Replaces: _set_team_game_from_registration signal
    """
    try:
        team_id = event.data.get('team_id')
        game = event.data.get('game')
        
        if not team_id or not game:
            logger.debug("No team or game in registration event")
            return
        
        Team = apps.get_model("teams", "Team")
        team = Team.objects.get(id=team_id)
        
        # Only set if team doesn't have a game yet
        if not team.game:
            team.game = game
            team.save(update_fields=['game'])
            logger.info(f"✅ Set team {team_id} game to {game}")
        else:
            logger.debug(f"Team {team_id} already has game: {team.game}")
            
    except Exception as e:
        logger.error(f"❌ Failed to set team game: {e}")


# ============================================================================
# Payment Verified Handlers
# ============================================================================

def award_coins_on_payment_verified(event):
    """
    Award participation coins when payment is verified.
    
    Replaces: _maybe_award_coins_on_verification signal
    """
    try:
        status = event.data.get('status')
        registration_id = event.data.get('registration_id')
        
        if status not in ("VERIFIED", "APPROVED", "CONFIRMED"):
            logger.debug(f"Payment not verified yet: {status}")
            return
        
        # Import economy service
        from apps.economy.services.participation import award_participation_for_registration
        from apps.tournaments.models import Registration
        
        registration = Registration.objects.get(id=registration_id)
        award_participation_for_registration(registration)
        
        logger.info(f"✅ Awarded coins for registration {registration_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to award coins: {e}")


# ============================================================================
# Registration Handlers
# ============================================================================

def register_tournament_event_handlers():
    """
    Register all tournament event handlers with the Event Bus.
    
    Call this in TournamentsConfig.ready() method.
    """
    # Tournament created
    event_bus.subscribe(
        'tournament.created',
        create_tournament_settings,
        name='create_tournament_settings',
        priority=10  # Run early
    )
    
    event_bus.subscribe(
        'tournament.created',
        create_game_config,
        name='create_game_config',
        priority=20  # Run after settings
    )
    
    # Registration created
    event_bus.subscribe(
        'registration.created',
        create_payment_verification,
        name='create_payment_verification',
        priority=10
    )
    
    event_bus.subscribe(
        'registration.created',
        set_team_game_from_registration,
        name='set_team_game_from_registration',
        priority=20
    )
    
    # Payment verified
    event_bus.subscribe(
        'payment.verified',
        award_coins_on_payment_verified,
        name='award_coins_on_payment_verified',
        priority=30  # Run after other payment handlers
    )
    
    logger.info("✅ Registered tournament event handlers")


# Auto-register when module is imported
try:
    register_tournament_event_handlers()
except Exception as e:
    logger.error(f"❌ Failed to register tournament event handlers: {e}")
