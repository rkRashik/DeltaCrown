"""
Tournament Provider Interface

Abstract interface for tournament operations. This allows multiple implementations
of tournament systems to coexist, enabling safe replacement of tournament apps
without breaking dependencies.

Usage:
    from apps.core.registry import registry
    provider = registry.get('tournament_provider')
    tournament = provider.get_tournament(123)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class ITournamentProvider(ABC):
    """
    Abstract base class for tournament operations.
    
    Any tournament system (v1, v2, external API, etc.) must implement this interface.
    Other apps use this interface instead of importing Tournament models directly.
    """
    
    @abstractmethod
    def get_tournament(self, tournament_id: int) -> Any:
        """
        Get a tournament by ID.
        
        Args:
            tournament_id: Tournament ID
            
        Returns:
            Tournament object (implementation-specific)
            
        Raises:
            DoesNotExist: If tournament not found
        """
        pass
    
    @abstractmethod
    def get_tournament_by_slug(self, slug: str) -> Any:
        """
        Get a tournament by slug.
        
        Args:
            slug: Tournament slug
            
        Returns:
            Tournament object
            
        Raises:
            DoesNotExist: If tournament not found
        """
        pass
    
    @abstractmethod
    def list_tournaments(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Any]:
        """
        List tournaments with optional filters.
        
        Args:
            filters: Dict of filter criteria (status, game, featured, etc.)
            limit: Maximum number of results
            
        Returns:
            List of tournament objects
        """
        pass
    
    @abstractmethod
    def create_tournament(self, **data) -> Any:
        """
        Create a new tournament.
        
        Args:
            **data: Tournament data (name, game, status, etc.)
            
        Returns:
            Created tournament object
        """
        pass
    
    @abstractmethod
    def update_tournament(self, tournament_id: int, **data) -> Any:
        """
        Update a tournament.
        
        Args:
            tournament_id: Tournament ID
            **data: Fields to update
            
        Returns:
            Updated tournament object
        """
        pass
    
    @abstractmethod
    def delete_tournament(self, tournament_id: int) -> None:
        """
        Delete a tournament.
        
        Args:
            tournament_id: Tournament ID
        """
        pass
    
    # Registration Operations
    
    @abstractmethod
    def get_registration(self, registration_id: int) -> Any:
        """Get a registration by ID"""
        pass
    
    @abstractmethod
    def get_tournament_registrations(self, tournament_id: int, status: Optional[str] = None) -> List[Any]:
        """
        Get registrations for a tournament.
        
        Args:
            tournament_id: Tournament ID
            status: Optional status filter (PENDING, CONFIRMED, etc.)
            
        Returns:
            List of registration objects
        """
        pass
    
    @abstractmethod
    def create_registration(self, tournament_id: int, team_id: Optional[int] = None, 
                          user_id: Optional[int] = None, **data) -> Any:
        """
        Create a registration.
        
        Args:
            tournament_id: Tournament ID
            team_id: Optional team ID (for team tournaments)
            user_id: Optional user ID (for solo tournaments)
            **data: Additional registration data
            
        Returns:
            Created registration object
        """
        pass
    
    @abstractmethod
    def update_registration_status(self, registration_id: int, status: str) -> Any:
        """
        Update registration status.
        
        Args:
            registration_id: Registration ID
            status: New status (PENDING, CONFIRMED, REJECTED, etc.)
            
        Returns:
            Updated registration object
        """
        pass
    
    @abstractmethod
    def delete_registration(self, registration_id: int) -> None:
        """Delete a registration"""
        pass
    
    # Match Operations
    
    @abstractmethod
    def get_match(self, match_id: int) -> Any:
        """Get a match by ID"""
        pass
    
    @abstractmethod
    def get_tournament_matches(self, tournament_id: int, round_no: Optional[int] = None) -> List[Any]:
        """
        Get matches for a tournament.
        
        Args:
            tournament_id: Tournament ID
            round_no: Optional round number filter
            
        Returns:
            List of match objects
        """
        pass
    
    @abstractmethod
    def create_match(self, tournament_id: int, **data) -> Any:
        """Create a match"""
        pass
    
    @abstractmethod
    def update_match(self, match_id: int, **data) -> Any:
        """Update a match"""
        pass
    
    # Payment Operations
    
    @abstractmethod
    def get_payment_verification(self, registration_id: int) -> Any:
        """Get payment verification for a registration"""
        pass
    
    @abstractmethod
    def verify_payment(self, registration_id: int, **data) -> Any:
        """
        Verify payment for a registration.
        
        Args:
            registration_id: Registration ID
            **data: Payment verification data
            
        Returns:
            Payment verification object
        """
        pass
    
    # Stats & Analytics
    
    @abstractmethod
    def get_tournament_stats(self, tournament_id: int) -> Dict[str, Any]:
        """
        Get tournament statistics.
        
        Returns:
            Dict with stats: total_registrations, confirmed_count, prize_pool, etc.
        """
        pass
    
    @abstractmethod
    def get_participant_count(self, tournament_id: int) -> int:
        """Get number of confirmed participants in tournament"""
        pass
    
    # Tournament Settings
    
    @abstractmethod
    def get_tournament_settings(self, tournament_id: int) -> Any:
        """Get tournament settings object"""
        pass
    
    @abstractmethod
    def update_tournament_settings(self, tournament_id: int, **data) -> Any:
        """Update tournament settings"""
        pass


class IGameConfigProvider(ABC):
    """
    Abstract base class for game-specific configurations.
    
    Handles game-specific rules, validations, and configurations for tournaments.
    """
    
    @abstractmethod
    def get_config(self, game: str, tournament_id: int) -> Any:
        """
        Get game configuration for a tournament.
        
        Args:
            game: Game identifier (valorant, efootball, etc.)
            tournament_id: Tournament ID
            
        Returns:
            Game config object
            
        Raises:
            DoesNotExist: If config not found
        """
        pass
    
    @abstractmethod
    def create_config(self, game: str, tournament_id: int, **data) -> Any:
        """
        Create game configuration for a tournament.
        
        Args:
            game: Game identifier
            tournament_id: Tournament ID
            **data: Game-specific configuration data
            
        Returns:
            Created config object
        """
        pass
    
    @abstractmethod
    def update_config(self, game: str, tournament_id: int, **data) -> Any:
        """Update game configuration"""
        pass
    
    @abstractmethod
    def validate_config(self, game: str, config_data: Dict[str, Any]) -> bool:
        """
        Validate game configuration data.
        
        Args:
            game: Game identifier
            config_data: Configuration to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If invalid
        """
        pass
    
    @abstractmethod
    def get_game_rules(self, game: str) -> Dict[str, Any]:
        """
        Get default rules/constraints for a game.
        
        Returns:
            Dict with rules: min_team_size, max_team_size, allowed_modes, etc.
        """
        pass
    
    @abstractmethod
    def get_supported_games(self) -> List[str]:
        """Get list of supported game identifiers"""
        pass


__all__ = ['ITournamentProvider', 'IGameConfigProvider']
