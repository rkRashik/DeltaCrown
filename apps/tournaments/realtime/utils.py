"""
Broadcasting Utilities for Real-Time Tournament Events

Provides helper functions for broadcasting events to WebSocket clients
connected to tournament rooms.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates

Module 4.5: WebSocket Enhancement
    - Micro-batching for score_updated events (100ms window)
    - dispute_created event broadcasting

Module 5.1: Winner Determination & Verification
    - tournament_completed event broadcasting

Event Types:
    - match_started: New match begins
    - score_updated: Match score changes (micro-batched)
    - match_completed: Match finishes with confirmed result
    - bracket_updated: Bracket progression after match completion
    - dispute_created: Dispute reported for match (Module 4.5)
    - tournament_completed: Tournament winner determined (Module 5.1)
"""

import logging
import asyncio
import threading
from typing import Dict, Any, Literal, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Type hints for event types (Module 4.5: added dispute_created, Module 5.1: added tournament_completed)
EventType = Literal['match_started', 'score_updated', 'match_completed', 'bracket_updated', 'dispute_created', 'tournament_completed']

# ============================================================================
# Module 4.5: Score Micro-Batching
# ============================================================================

# Global dict to track pending score updates per match
# Format: {match_id: {'data': {...}, 'sequence': int, 'task': asyncio.Task}}
_score_batch_pending: Dict[int, Dict[str, Any]] = {}
_score_batch_lock = threading.Lock()
_score_sequence = 0  # Global sequence counter


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


# ============================================================================
# Module 4.5: Score Micro-Batching Implementation
# ============================================================================

def _broadcast_batched_score(match_id: int, tournament_id: int):
    """
    Internal function to broadcast batched score update after 100ms window.
    
    Module 4.5: Implements micro-batching for score_updated events.
    
    Args:
        match_id: Match ID to broadcast score for
        tournament_id: Tournament ID for room routing
    """
    global _score_batch_pending, _score_batch_lock
    
    with _score_batch_lock:
        if match_id not in _score_batch_pending:
            return  # Already sent or cancelled
        
        batch_info = _score_batch_pending.pop(match_id)
        score_data = batch_info['data']
        sequence = batch_info['sequence']
    
    # Add sequence number to data
    score_data['sequence'] = sequence
    
    # Broadcast to tournament room
    broadcast_tournament_event(tournament_id, 'score_updated', score_data)
    
    # Broadcast to match room
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'match_{match_id}',
                {
                    'type': 'score_updated',
                    'data': score_data,
                }
            )
            logger.debug(f"Broadcast batched score_updated to match_{match_id}, seq={sequence}")
    except Exception as e:
        logger.error(f"Failed to broadcast batched score to match room: {e}")


def _schedule_score_batch(match_id: int, tournament_id: int):
    """
    Schedule batched score broadcast after 100ms delay.
    
    Module 4.5: Creates asyncio task to broadcast after delay.
    
    Args:
        match_id: Match ID
        tournament_id: Tournament ID
    """
    import threading
    
    def delayed_broadcast():
        import time
        time.sleep(0.1)  # 100ms window
        _broadcast_batched_score(match_id, tournament_id)
    
    # Run in background thread (synchronous context)
    thread = threading.Timer(0.1, _broadcast_batched_score, args=(match_id, tournament_id))
    thread.daemon = True
    thread.start()


def broadcast_score_updated_batched(
    tournament_id: int, 
    match_id: int,
    score_data: Dict[str, Any]
) -> None:
    """
    Broadcast score_updated event with micro-batching.
    
    Module 4.5: Coalesces score updates within 100ms window per match.
    Latest score wins. Adds sequence number to payload.
    
    Process:
        1. Check if batch pending for this match
        2. If yes: Update pending data with latest scores
        3. If no: Create new pending batch with 100ms timer
        4. After 100ms: Broadcast latest score to both rooms
    
    Args:
        tournament_id: Tournament ID
        match_id: Match ID (required for batching key)
        score_data: Score details (match_id, participant1_score, participant2_score, etc.)
    
    Example:
        >>> # Rapid score updates (burst)
        >>> broadcast_score_updated_batched(1, 123, {'participant1_score': 10, ...})
        >>> broadcast_score_updated_batched(1, 123, {'participant1_score': 11, ...})
        >>> broadcast_score_updated_batched(1, 123, {'participant1_score': 12, ...})
        >>> # Only final score (12) is broadcast after 100ms
    """
    global _score_batch_pending, _score_batch_lock, _score_sequence
    
    with _score_batch_lock:
        # Increment sequence number
        _score_sequence += 1
        sequence = _score_sequence
        
        if match_id in _score_batch_pending:
            # Update existing pending batch with latest scores
            _score_batch_pending[match_id]['data'] = score_data
            _score_batch_pending[match_id]['sequence'] = sequence
            logger.debug(
                f"Updated batched score for match {match_id}, seq={sequence} "
                f"(latest wins)"
            )
        else:
            # Create new batch with 100ms timer
            _score_batch_pending[match_id] = {
                'data': score_data,
                'sequence': sequence,
            }
            logger.debug(
                f"Created batched score for match {match_id}, seq={sequence} "
                f"(100ms window)"
            )
            
            # Schedule broadcast after 100ms
            _schedule_score_batch(match_id, tournament_id)


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
    Convenience wrapper for broadcasting score_updated events (non-batched).
    
    Module 4.5: For single-shot score updates. For rapid updates, use 
    broadcast_score_updated_batched() instead to enable micro-batching.
    
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


def broadcast_bracket_generated(tournament_id: int, bracket_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting bracket_generated events.
    
    Sent when a new bracket is generated or regenerated for a tournament.
    Clients can use this to refresh bracket visualization.
    
    Module: 4.1 - Bracket Generation API
    
    Args:
        tournament_id: Tournament ID
        bracket_data: Bracket details (bracket_id, format, total_matches, seeding_method, etc.)
    
    Example:
        >>> broadcast_bracket_generated(
        ...     tournament_id=1,
        ...     bracket_data={
        ...         'bracket_id': 456,
        ...         'format': 'single-elimination',
        ...         'seeding_method': 'random',
        ...         'total_rounds': 3,
        ...         'total_matches': 7,
        ...         'generated_at': '2025-01-08T10:30:00Z',
        ...         'generated_by': 42,
        ...     }
        ... )
    """
    broadcast_tournament_event(tournament_id, 'bracket_generated', bracket_data)


def broadcast_dispute_created(tournament_id: int, dispute_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting dispute_created events.
    
    Sent when a new dispute is reported for a match.
    Alerts organizers and participants of dispute status.
    
    Module: 4.5 - WebSocket Enhancement
    
    Args:
        tournament_id: Tournament ID
        dispute_data: Dispute details (dispute_id, match_id, reason, status, timestamp, etc.)
    
    Example:
        >>> broadcast_dispute_created(
        ...     tournament_id=1,
        ...     dispute_data={
        ...         'dispute_id': 789,
        ...         'match_id': 123,
        ...         'initiated_by': 45,
        ...         'reason': 'score_mismatch',
        ...         'status': 'open',
        ...         'timestamp': '2025-11-09T15:30:00Z',
        ...     }
        ... )
    """
    broadcast_tournament_event(tournament_id, 'dispute_created', dispute_data)

