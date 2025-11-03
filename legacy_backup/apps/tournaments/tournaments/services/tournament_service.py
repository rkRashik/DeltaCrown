"""
Tournament Service Layer

Business logic for tournament operations with explicit event publishing.
Replaces direct model.save() calls in views with service methods.
"""
import logging
from typing import Optional
from django.db import transaction

from apps.core.events.bus import event_bus
from apps.core.events.events import (
    TournamentCreatedEvent,
    TournamentPublishedEvent,
    TournamentStartedEvent,
    TournamentCompletedEvent,
    RegistrationCreatedEvent,
    RegistrationConfirmedEvent,
    PaymentVerifiedEvent
)

logger = logging.getLogger(__name__)


class TournamentService:
    """
    Service for tournament operations.
    
    All tournament creation/updates should go through this service
    so events are published correctly.
    """
    
    @transaction.atomic
    def create_tournament(self, **data):
        """
        Create a new tournament and publish event.
        
        Args:
            **data: Tournament fields (name, game, max_teams, etc.)
        
        Returns:
            Tournament instance
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.create(**data)
        
        # Publish event
        event = TournamentCreatedEvent(data={
            'tournament_id': tournament.id,
            'name': tournament.name,
            'game': tournament.game,
            'created_by': tournament.created_by_id if hasattr(tournament, 'created_by') else None
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Created tournament {tournament.id}: {tournament.name}")
        
        return tournament
    
    def publish_tournament(self, tournament):
        """
        Publish a tournament (make it visible to users).
        
        Args:
            tournament: Tournament instance
        """
        tournament.status = 'published'
        tournament.save(update_fields=['status'])
        
        # Publish event
        event = TournamentPublishedEvent(data={
            'tournament_id': tournament.id,
            'name': tournament.name,
            'game': tournament.game
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Published tournament {tournament.id}")
    
    def start_tournament(self, tournament):
        """
        Start a tournament (begin matches).
        
        Args:
            tournament: Tournament instance
        """
        tournament.status = 'in_progress'
        tournament.save(update_fields=['status'])
        
        # Publish event
        event = TournamentStartedEvent(data={
            'tournament_id': tournament.id,
            'name': tournament.name
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Started tournament {tournament.id}")
    
    def complete_tournament(self, tournament, winner=None):
        """
        Complete a tournament.
        
        Args:
            tournament: Tournament instance
            winner: Winning team (optional)
        """
        tournament.status = 'completed'
        if winner:
            tournament.winner = winner
        tournament.save(update_fields=['status', 'winner'] if winner else ['status'])
        
        # Publish event
        event = TournamentCompletedEvent(data={
            'tournament_id': tournament.id,
            'name': tournament.name,
            'winner_id': winner.id if winner else None
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Completed tournament {tournament.id}")


class RegistrationService:
    """
    Service for tournament registration operations.
    """
    
    @transaction.atomic
    def create_registration(self, tournament, team=None, user=None, **data):
        """
        Create a tournament registration and publish event.
        
        Args:
            tournament: Tournament instance
            team: Team instance (optional, for team tournaments)
            user: User instance (optional, for solo tournaments)
            **data: Additional registration fields
        
        Returns:
            Registration instance
        """
        from apps.tournaments.models import Registration
        
        registration = Registration.objects.create(
            tournament=tournament,
            team=team,
            user=user,
            **data
        )
        
        # Publish event
        event = RegistrationCreatedEvent(data={
            'registration_id': registration.id,
            'tournament_id': tournament.id,
            'team_id': team.id if team else None,
            'user_id': user.id if user else None,
            'game': tournament.game
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Created registration {registration.id} for tournament {tournament.id}")
        
        return registration
    
    def confirm_registration(self, registration):
        """
        Confirm a registration (after payment verified).
        
        Args:
            registration: Registration instance
        """
        registration.status = 'CONFIRMED'
        registration.save(update_fields=['status'])
        
        # Publish event
        event = RegistrationConfirmedEvent(data={
            'registration_id': registration.id,
            'tournament_id': registration.tournament_id,
            'team_id': registration.team_id,
            'user_id': registration.user_id
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Confirmed registration {registration.id}")


class PaymentService:
    """
    Service for payment verification operations.
    """
    
    def verify_payment(self, payment_verification):
        """
        Verify a payment.
        
        Args:
            payment_verification: PaymentVerification instance
        """
        payment_verification.status = 'VERIFIED'
        payment_verification.save(update_fields=['status'])
        
        # Publish event
        event = PaymentVerifiedEvent(data={
            'payment_id': payment_verification.id,
            'registration_id': payment_verification.registration_id,
            'status': 'VERIFIED',
            'amount': getattr(payment_verification, 'amount', 0)
        })
        event_bus.publish(event)
        
        logger.info(f"✅ Verified payment {payment_verification.id}")
        
        # Also confirm the registration
        registration_service = RegistrationService()
        registration_service.confirm_registration(payment_verification.registration)
