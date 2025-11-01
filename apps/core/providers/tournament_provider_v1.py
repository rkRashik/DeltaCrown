"""
Tournament Provider V1

Concrete implementation of ITournamentProvider using the current tournament system.
This wraps the existing Tournament, Registration, and Match models.
"""

import logging
from typing import List, Optional, Dict, Any
from django.apps import apps
from django.db import transaction

from apps.core.interfaces import ITournamentProvider, IGameConfigProvider
from apps.core.events import event_bus
from apps.core.events.events import (
    TournamentCreatedEvent,
    TournamentUpdatedEvent,
    RegistrationCreatedEvent,
    MatchScheduledEvent,
)

logger = logging.getLogger(__name__)


class TournamentProviderV1(ITournamentProvider):
    """
    Version 1 implementation using current tournament models.
    
    This provider wraps apps.tournaments.models and provides a clean interface
    that other apps can depend on without importing Tournament models directly.
    """
    
    def __init__(self):
        # Lazy load models to avoid circular imports
        self._tournament_model = None
        self._registration_model = None
        self._match_model = None
        self._payment_model = None
        self._settings_model = None
    
    @property
    def Tournament(self):
        if self._tournament_model is None:
            self._tournament_model = apps.get_model('tournaments', 'Tournament')
        return self._tournament_model
    
    @property
    def Registration(self):
        if self._registration_model is None:
            self._registration_model = apps.get_model('tournaments', 'Registration')
        return self._registration_model
    
    @property
    def Match(self):
        if self._match_model is None:
            self._match_model = apps.get_model('tournaments', 'Match')
        return self._match_model
    
    @property
    def PaymentVerification(self):
        if self._payment_model is None:
            self._payment_model = apps.get_model('tournaments', 'PaymentVerification')
        return self._payment_model
    
    @property
    def TournamentSettings(self):
        if self._settings_model is None:
            self._settings_model = apps.get_model('tournaments', 'TournamentSettings')
        return self._settings_model
    
    # Tournament Operations
    
    def get_tournament(self, tournament_id: int) -> Any:
        """Get tournament by ID"""
        try:
            return self.Tournament.objects.select_related('settings').get(id=tournament_id)
        except self.Tournament.DoesNotExist:
            return None
    
    def get_tournament_by_slug(self, slug: str) -> Any:
        """Get tournament by slug"""
        return self.Tournament.objects.select_related('settings').get(slug=slug)
    
    def list_tournaments(self, status: Optional[str] = None, game: Optional[str] = None, 
                        filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Any]:
        """List tournaments with filters"""
        queryset = self.Tournament.objects.select_related('settings')
        
        # Support both direct parameters and filters dict for backward compatibility
        if status:
            queryset = queryset.filter(status=status)
        if game:
            queryset = queryset.filter(game=game)
            
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'game' in filters:
                queryset = queryset.filter(game=filters['game'])
            if 'featured' in filters:
                queryset = queryset.filter(featured=filters['featured'])
            if 'published' in filters and filters['published']:
                queryset = queryset.filter(status='PUBLISHED')
        
        return list(queryset[:limit])
    
    @transaction.atomic
    def create_tournament(self, **data) -> Any:
        """Create tournament and publish event"""
        tournament = self.Tournament.objects.create(**data)
        
        # Publish event
        event = TournamentCreatedEvent(data={
            'tournament_id': tournament.id,
            'game': tournament.game,
            'status': tournament.status,
        })
        event_bus.publish(event)
        
        logger.info(f"Created tournament: {tournament.name} (ID: {tournament.id})")
        return tournament
    
    @transaction.atomic
    def update_tournament(self, tournament_id: int, **data) -> Any:
        """Update tournament and publish event"""
        tournament = self.get_tournament(tournament_id)
        
        for key, value in data.items():
            setattr(tournament, key, value)
        
        tournament.save()
        
        # Publish event
        event = TournamentUpdatedEvent(data={
            'tournament_id': tournament.id,
            'updated_fields': list(data.keys()),
        })
        event_bus.publish(event)
        
        logger.info(f"Updated tournament: {tournament.name} (ID: {tournament.id})")
        return tournament
    
    def delete_tournament(self, tournament_id: int) -> None:
        """Delete tournament"""
        tournament = self.get_tournament(tournament_id)
        name = tournament.name
        tournament.delete()
        logger.info(f"Deleted tournament: {name} (ID: {tournament_id})")
    
    # Registration Operations
    
    def get_registration(self, registration_id: int) -> Any:
        """Get registration by ID"""
        return self.Registration.objects.select_related(
            'tournament', 'team', 'user'
        ).get(id=registration_id)
    
    def get_tournament_registrations(self, tournament_id: int, status: Optional[str] = None) -> List[Any]:
        """Get registrations for tournament"""
        queryset = self.Registration.objects.filter(
            tournament_id=tournament_id
        ).select_related('team', 'user')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset)
    
    def get_registrations(self, tournament_id: int, status: Optional[str] = None) -> List[Any]:
        """Alias for get_tournament_registrations"""
        return self.get_tournament_registrations(tournament_id, status)
    
    @transaction.atomic
    def create_registration(self, tournament_id: int, team_id: Optional[int] = None,
                          user_id: Optional[int] = None, **data) -> Any:
        """Create registration and publish event"""
        registration = self.Registration.objects.create(
            tournament_id=tournament_id,
            team_id=team_id,
            user_id=user_id,
            **data
        )
        
        # Publish event
        event = RegistrationCreatedEvent(data={
            'registration_id': registration.id,
            'tournament_id': tournament_id,
            'team_id': team_id,
            'user_id': user_id,
        })
        event_bus.publish(event)
        
        logger.info(f"Created registration: {registration.id} for tournament {tournament_id}")
        return registration
    
    @transaction.atomic
    def update_registration_status(self, registration_id: int, status: str) -> Any:
        """Update registration status"""
        registration = self.get_registration(registration_id)
        registration.status = status
        registration.save(update_fields=['status'])
        
        logger.info(f"Updated registration {registration_id} status to: {status}")
        return registration
    
    def delete_registration(self, registration_id: int) -> None:
        """Delete registration"""
        registration = self.get_registration(registration_id)
        registration.delete()
        logger.info(f"Deleted registration: {registration_id}")
    
    # Match Operations
    
    def get_match(self, match_id: int) -> Any:
        """Get match by ID"""
        return self.Match.objects.select_related(
            'tournament', 'team_a', 'team_b', 'user_a', 'user_b'
        ).get(id=match_id)
    
    def get_tournament_matches(self, tournament_id: int, round_no: Optional[int] = None) -> List[Any]:
        """Get matches for tournament"""
        queryset = self.Match.objects.filter(
            tournament_id=tournament_id
        ).select_related('team_a', 'team_b', 'user_a', 'user_b')
        
        if round_no is not None:
            queryset = queryset.filter(round_no=round_no)
        
        return list(queryset.order_by('round_no', 'position'))
    
    @transaction.atomic
    def create_match(self, tournament_id: int, **data) -> Any:
        """Create match"""
        match = self.Match.objects.create(
            tournament_id=tournament_id,
            **data
        )
        
        # Publish event if match has start time
        if data.get('start_at'):
            event = MatchScheduledEvent(data={
                'match_id': match.id,
                'tournament_id': tournament_id,
            })
            event_bus.publish(event)
        
        logger.info(f"Created match: {match.id} for tournament {tournament_id}")
        return match
    
    @transaction.atomic
    def update_match(self, match_id: int, **data) -> Any:
        """Update match"""
        match = self.get_match(match_id)
        
        for key, value in data.items():
            setattr(match, key, value)
        
        match.save()
        
        # Publish event if start time was updated
        if 'start_at' in data and data['start_at']:
            event = MatchScheduledEvent(data={
                'match_id': match.id,
                'tournament_id': match.tournament_id,
            })
            event_bus.publish(event)
        
        logger.info(f"Updated match: {match_id}")
        return match
    
    # Payment Operations
    
    def get_payment_verification(self, registration_id: int) -> Any:
        """Get payment verification"""
        return self.PaymentVerification.objects.get(registration_id=registration_id)
    
    @transaction.atomic
    def verify_payment(self, registration_id: int, **data) -> Any:
        """Verify payment"""
        payment = self.get_payment_verification(registration_id)
        payment.status = 'verified'
        
        for key, value in data.items():
            if hasattr(payment, key):
                setattr(payment, key, value)
        
        payment.save()
        
        logger.info(f"Verified payment for registration: {registration_id}")
        return payment
    
    # Stats & Analytics
    
    def get_tournament_stats(self, tournament_id: int) -> Dict[str, Any]:
        """Get tournament statistics"""
        tournament = self.get_tournament(tournament_id)
        registrations = self.Registration.objects.filter(tournament_id=tournament_id)
        
        return {
            'total_registrations': registrations.count(),
            'confirmed_count': registrations.filter(status='CONFIRMED').count(),
            'pending_count': registrations.filter(status='PENDING').count(),
            'prize_pool': getattr(tournament, 'prize_pool', 0),
            'match_count': self.Match.objects.filter(tournament_id=tournament_id).count(),
        }
    
    def get_participant_count(self, tournament_id: int) -> int:
        """Get confirmed participant count"""
        return self.Registration.objects.filter(
            tournament_id=tournament_id,
            status='CONFIRMED'
        ).count()
    
    # Tournament Settings
    
    def get_tournament_settings(self, tournament_id: int) -> Any:
        """Get tournament settings"""
        return self.TournamentSettings.objects.get(tournament_id=tournament_id)
    
    @transaction.atomic
    def update_tournament_settings(self, tournament_id: int, **data) -> Any:
        """Update tournament settings"""
        settings = self.get_tournament_settings(tournament_id)
        
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.save()
        
        logger.info(f"Updated settings for tournament: {tournament_id}")
        return settings


class GameConfigProviderV1(IGameConfigProvider):
    """
    Version 1 implementation for game configs using current models.
    """
    
    def __init__(self):
        self._valorant_config_model = None
        self._efootball_config_model = None
    
    @property
    def ValorantConfig(self):
        if self._valorant_config_model is None:
            self._valorant_config_model = apps.get_model('game_valorant', 'ValorantConfig')
        return self._valorant_config_model
    
    @property
    def EfootballConfig(self):
        if self._efootball_config_model is None:
            self._efootball_config_model = apps.get_model('game_efootball', 'EfootballConfig')
        return self._efootball_config_model
    
    def _get_config_model(self, game: str):
        """Get config model for game"""
        game_map = {
            'valorant': self.ValorantConfig,
            'efootball': self.EfootballConfig,
        }
        
        if game not in game_map:
            raise ValueError(f"Unsupported game: {game}")
        
        return game_map[game]
    
    def get_config(self, game: str, tournament_id: int) -> Any:
        """Get game config"""
        try:
            model = self._get_config_model(game)
            return model.objects.get(tournament_id=tournament_id)
        except Exception:
            # Tournament doesn't have this game config, return None
            return None
    
    @transaction.atomic
    def create_config(self, game: str, tournament_id: int, **data) -> Any:
        """Create game config"""
        model = self._get_config_model(game)
        config = model.objects.create(tournament_id=tournament_id, **data)
        
        logger.info(f"Created {game} config for tournament {tournament_id}")
        return config
    
    @transaction.atomic
    def update_config(self, game: str, tournament_id: int, **data) -> Any:
        """Update game config"""
        config = self.get_config(game, tournament_id)
        
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.save()
        
        logger.info(f"Updated {game} config for tournament {tournament_id}")
        return config
    
    def validate_config(self, game: str, config_data: Dict[str, Any]) -> bool:
        """Validate game config"""
        # Basic validation - extend as needed
        model = self._get_config_model(game)
        
        # Check required fields exist
        required_fields = ['tournament']
        for field in required_fields:
            if field not in config_data:
                raise ValueError(f"Missing required field: {field}")
        
        return True
    
    def get_game_rules(self, game: str) -> Dict[str, Any]:
        """Get default rules for game"""
        rules = {
            'valorant': {
                'min_team_size': 5,
                'max_team_size': 7,
                'default_mode': '5v5',
                'allowed_modes': ['5v5', 'custom'],
            },
            'efootball': {
                'min_team_size': 1,
                'max_team_size': 1,
                'default_mode': '1v1',
                'allowed_modes': ['1v1', '2v2'],
            },
        }
        
        return rules.get(game, {})
    
    def get_supported_games(self) -> List[str]:
        """Get supported games"""
        return ['valorant', 'efootball']


# Singleton instances
tournament_provider_v1 = TournamentProviderV1()
game_config_provider_v1 = GameConfigProviderV1()


__all__ = [
    'TournamentProviderV1',
    'GameConfigProviderV1',
    'tournament_provider_v1',
    'game_config_provider_v1',
]
