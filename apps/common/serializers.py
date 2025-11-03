"""
Common Serializers for Decoupled Data Transfer

Industry-standard serialization layer to decouple views from models.
Views pass serialized data (dicts) to templates, not raw model objects.
This prevents tight coupling and makes the app resilient to model changes.
"""
from typing import Optional, Dict, Any


class TournamentSerializer:
    """
    Serialize tournament-related data.
    
    Since tournaments app moved to legacy, this provides backward-compatible
    data structure for templates that expect tournament information.
    """
    
    @staticmethod
    def serialize_legacy_tournament(tournament_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        Serialize a legacy tournament ID into a dict structure.
        
        Args:
            tournament_id: Integer ID of legacy tournament
            
        Returns:
            Dict with tournament data or None if no ID provided
        """
        if not tournament_id:
            return None
        
        return {
            'id': tournament_id,
            'name': f'Legacy Tournament #{tournament_id}',
            'slug': f'legacy-{tournament_id}',
            'game': 'N/A',
            'logo': None,
            'start_date': None,
            'end_date': None,
            'prize_pool': None,
            'max_teams': None,
            'status': 'archived',
        }
    
    @staticmethod
    def serialize_registration(registration_obj) -> Dict[str, Any]:
        """
        Serialize a TeamTournamentRegistration object.
        
        Args:
            registration_obj: TeamTournamentRegistration instance
            
        Returns:
            Dict with registration and tournament data
        """
        tournament_data = TournamentSerializer.serialize_legacy_tournament(
            getattr(registration_obj, 'tournament_id', None)
        )
        
        return {
            'id': registration_obj.id,
            'status': registration_obj.status,
            'registered_at': getattr(registration_obj, 'registered_at', None),
            'tournament': tournament_data,
        }
    
    @staticmethod
    def serialize_match(match_obj) -> Dict[str, Any]:
        """
        Serialize a match/MatchRecord object with tournament data.
        
        Args:
            match_obj: Match or MatchRecord instance
            
        Returns:
            Dict with match and tournament data
        """
        tournament_data = TournamentSerializer.serialize_legacy_tournament(
            getattr(match_obj, 'tournament_id', None)
        )
        
        return {
            'id': getattr(match_obj, 'id', None),
            'match_date': getattr(match_obj, 'match_date', None) or getattr(match_obj, 'scheduled_at', None),
            'opponent_name': getattr(match_obj, 'opponent_name', None),
            'result': getattr(match_obj, 'result', None),
            'score': getattr(match_obj, 'score', None),
            'team_score': getattr(match_obj, 'team_score', None),
            'opponent_score': getattr(match_obj, 'opponent_score', None),
            'tournament': tournament_data,
        }


class TransactionSerializer:
    """Serialize economy transaction data"""
    
    @staticmethod
    def serialize_transaction(transaction_obj) -> Dict[str, Any]:
        """
        Serialize a DeltaCrownTransaction with tournament data.
        
        Args:
            transaction_obj: DeltaCrownTransaction instance
            
        Returns:
            Dict with transaction data
        """
        tournament_data = TournamentSerializer.serialize_legacy_tournament(
            getattr(transaction_obj, 'tournament_id', None)
        )
        
        return {
            'id': transaction_obj.id,
            'amount': transaction_obj.amount,
            'transaction_type': getattr(transaction_obj, 'transaction_type', None),
            'created_at': transaction_obj.created_at,
            'description': getattr(transaction_obj, 'description', ''),
            'tournament': tournament_data,
        }
