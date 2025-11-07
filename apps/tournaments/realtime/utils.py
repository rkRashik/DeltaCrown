"""
Broadcasting Utilities for Real-Time Tournament Events

Provides helper functions for broadcasting events to WebSocket clients
connected to tournament rooms.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates

Event Types:
    - match_started: New match begins
    - score_updated: Match score changes
    - match_completed: Match finishes with confirmed result
    - bracket_updated: Bracket progression after match completion
"""

import logging
from typing import Dict, Any, Literal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Type hints for event types
EventType = Literal['match_started', 'score_updated', 'match_completed', 'bracket_updated']


def broadcast_tournament_event(
    tournament_id: int,
    event_type: EventType,
    data: Dict[str, Any]
) -> None:
    """
    Broadcast event to all clients connected to a tournament room.
    
    This is the main utility function called by service layer (MatchService,
    BracketService) to push real-time updates to WebSocket clients.
    
    Args:
        tournament_id: ID of tournament to broadcast to
        event_type: Type of event (match_started, score_updated, 
                    match_completed, bracket_updated)
        data: Event payload (dict containing event-specific data)
        
    Returns:
        None
        
    Raises:
        No exceptions - failures are logged but don't propagate to caller
        
    Side Effects:
        - Sends message to all WebSocket clients in tournament_{tournament_id} group
        - Logs broadcast attempts and failures
        
    Example:
        >>> # From MatchService.confirm_result()
        >>> broadcast_tournament_event(
        ...     tournament_id=1,
        ...     event_type='match_completed',
        ...     data={
        ...         'match_id': 123,
        ...         'winner_id': 45,
        ...         'participant1_score': 2,
        ...         'participant2_score': 1,
        ...     }
        ... )
        
    Implementation Notes:
        - Uses Django Channels group_send to broadcast to room
        - Room name format: 'tournament_{tournament_id}'
        - Consumer method name derived from event_type (e.g., 'match_started')
        - Synchronous wrapper around async channel layer
    """
    try:
        channel_layer = get_channel_layer()
        
        if not channel_layer:
            logger.error("Channel layer not configured - cannot broadcast events")
            return
        
        room_group_name = f'tournament_{tournament_id}'
        
        logger.info(
            f"Broadcasting {event_type} to {room_group_name}",
            extra={
                'tournament_id': tournament_id,
                'event_type': event_type,
                'data_keys': list(data.keys())
            }
        )
        
        # Send to all clients in tournament room
        # The 'type' field maps to consumer method name (e.g., match_started)
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': event_type,  # Maps to consumer method
                'data': data,
            }
        )
        
        logger.debug(f"Successfully broadcast {event_type} to {room_group_name}")
        
    except Exception as e:
        # Log error but don't raise - broadcasting failures shouldn't break app logic
        logger.error(
            f"Failed to broadcast {event_type} for tournament {tournament_id}: {str(e)}",
            exc_info=True,
            extra={
                'tournament_id': tournament_id,
                'event_type': event_type,
            }
        )


def broadcast_match_started(tournament_id: int, match_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting match_started events.
    
    Args:
        tournament_id: Tournament ID
        match_data: Match details (id, participants, scheduled_time, etc.)
    """
    broadcast_tournament_event(tournament_id, 'match_started', match_data)


def broadcast_score_updated(tournament_id: int, score_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting score_updated events.
    
    Args:
        tournament_id: Tournament ID
        score_data: Score details (match_id, participant1_score, participant2_score, etc.)
    """
    broadcast_tournament_event(tournament_id, 'score_updated', score_data)


def broadcast_match_completed(tournament_id: int, result_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting match_completed events.
    
    Args:
        tournament_id: Tournament ID
        result_data: Match result (match_id, winner_id, final_scores, etc.)
    """
    broadcast_tournament_event(tournament_id, 'match_completed', result_data)


def broadcast_bracket_updated(tournament_id: int, bracket_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting bracket_updated events.
    
    Args:
        tournament_id: Tournament ID
        bracket_data: Bracket update (bracket_id, updated_nodes, next_matches, etc.)
    """
    broadcast_tournament_event(tournament_id, 'bracket_updated', bracket_data)
