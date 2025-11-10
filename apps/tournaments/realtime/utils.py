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

Module 6.1: Async-Native WebSocket Helpers
    - Converted all broadcast functions to async def
    - Removed async_to_sync shims for better async context handling
    - Django ORM queries wrapped with sync_to_async
    - Unblocks 4 skipped tests from Module 4.5

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
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Type hints for event types (Module 4.5: added dispute_created, Module 5.1: added tournament_completed)
EventType = Literal['match_started', 'score_updated', 'match_completed', 'bracket_updated', 'dispute_created', 'tournament_completed']

# ============================================================================
# Module 4.5: Score Micro-Batching
# Module 6.1: Event-loop-safe debouncing with asyncio.Handle
# ============================================================================

# Global state for per-match batching
# Format: {match_id: {'data': {...}, 'sequence': int, 'handle': asyncio.Handle | None}}
_score_batch_pending: Dict[int, Dict[str, Any]] = {}
_score_batch_locks: Dict[int, asyncio.Lock] = {}  # Per-match locks for safe cancellation
_score_sequence = 0  # Global sequence counter (monotonic)


async def broadcast_tournament_event(
    tournament_id: int,
    event_type: EventType,
    data: Dict[str, Any]
) -> None:
    """
    Broadcast event to all clients connected to a tournament room.
    
    This is the main utility function called by service layer (MatchService,
    BracketService) to push real-time updates to WebSocket clients.
    
    Module 6.1: Converted to async-native implementation.
    - Native async def (no async_to_sync wrapper)
    - Direct await on channel_layer.group_send
    - No Django ORM calls, so no sync_to_async needed
    
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
        >>> # From MatchService.confirm_result() (async context)
        >>> await broadcast_tournament_event(
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
        - Native async - no sync/async conversion overhead
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
        await channel_layer.group_send(
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

async def _flush_batch(match_id: int, tournament_id: int):
    """
    Flush pending score batch for a specific match.
    
    Module 4.5: Implements micro-batching for score_updated events.
    Module 6.1: Event-loop-safe flush with asyncio.Lock.
    
    Called after 100ms debounce window expires, or immediately on match completion.
    
    Args:
        match_id: Match ID to flush batch for
        tournament_id: Tournament ID for room routing
    """
    global _score_batch_pending, _score_batch_locks
    
    # Get or create lock for this match
    if match_id not in _score_batch_locks:
        _score_batch_locks[match_id] = asyncio.Lock()
    
    async with _score_batch_locks[match_id]:
        if match_id not in _score_batch_pending:
            return  # Already flushed or cancelled
        
        batch_info = _score_batch_pending.pop(match_id)
        score_data = batch_info['data'].copy()  # Copy to avoid mutations
        sequence = batch_info['sequence']
        
        # Cancel handle if still pending (safe to call even if fired)
        if batch_info.get('handle'):
            batch_info['handle'].cancel()
    
    # Add sequence number to data
    score_data['sequence'] = sequence
    
    # Broadcast to tournament room (async-native)
    try:
        await broadcast_tournament_event(tournament_id, 'score_updated', score_data)
    except Exception as e:
        logger.error(f"Failed to broadcast batched score to tournament room: {e}")
        return
    
    # Broadcast to match room
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                f'match_{match_id}',
                {
                    'type': 'score_updated',
                    'data': score_data,
                }
            )
            logger.debug(f"Broadcast batched score_updated to match_{match_id}, seq={sequence}")
    except Exception as e:
        logger.error(f"Failed to broadcast batched score to match room: {e}")


def _schedule_score_batch(match_id: int, tournament_id: int) -> Optional[asyncio.Handle]:
    """
    Schedule batched score broadcast after 100ms delay using loop.call_later.
    
    Module 4.5: Creates asyncio task to broadcast after delay.
    Module 6.1: Event-loop-safe scheduling with asyncio.Handle for cancellation.
    
    Returns asyncio.Handle that can be cancelled if new score arrives within window.
    
    Args:
        match_id: Match ID
        tournament_id: Tournament ID
        
    Returns:
        asyncio.Handle if scheduled successfully, None if no event loop
    """
    try:
        loop = asyncio.get_running_loop()
        
        # Callback that creates task to flush batch
        def flush_callback():
            try:
                # Create task in the loop to flush batch
                asyncio.create_task(_flush_batch(match_id, tournament_id))
            except Exception as e:
                logger.error(f"Failed to create flush task for match {match_id}: {e}")
        
        # Schedule callback after 100ms (0.1 seconds)
        handle = loop.call_later(0.1, flush_callback)
        logger.debug(f"Scheduled batched score flush for match {match_id} (100ms)")
        return handle
        
    except RuntimeError:
        # No running loop - fallback to thread-based scheduling
        # This should rarely happen as broadcast helpers are called from async contexts
        logger.warning(f"No event loop found for match {match_id}, using fallback thread")
        
        def sync_wrapper():
            import time
            time.sleep(0.1)
            # Create new event loop in thread
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_flush_batch(match_id, tournament_id))
                loop.close()
            except Exception as e:
                logger.error(f"Failed to flush batch in fallback thread: {e}")
        
        thread = threading.Thread(target=sync_wrapper, daemon=True)
        thread.start()
        return None  # No handle available in thread fallback


def broadcast_score_updated_batched(
    tournament_id: int, 
    match_id: int,
    score_data: Dict[str, Any]
) -> None:
    """
    Broadcast score_updated event with micro-batching (latest-wins coalescing).
    
    Module 4.5: Coalesces score updates within 100ms window per match.
    Latest score wins. Adds sequence number to payload.
    
    Module 6.1: Event-loop-safe debouncing with asyncio.Handle cancellation.
    - If new score arrives within 100ms window: Cancel old handle, schedule new one
    - Latest score overwrites pending data (sequence increments)
    - After 100ms: Broadcast single message with latest score
    
    Process:
        1. Check if batch pending for this match
        2. If yes: Cancel old handle, update pending data with latest scores
        3. If no: Create new pending batch with 100ms timer (asyncio.Handle)
        4. After 100ms: Broadcast latest score to both rooms (async)
    
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
    global _score_batch_pending, _score_sequence
    
    # Increment sequence number (monotonic)
    _score_sequence += 1
    sequence = _score_sequence
    
    if match_id in _score_batch_pending:
        # Cancel existing handle (safe even if already fired)
        old_handle = _score_batch_pending[match_id].get('handle')
        if old_handle and not old_handle.cancelled():
            old_handle.cancel()
            logger.debug(
                f"Cancelled old flush handle for match {match_id} "
                f"(coalescing to seq={sequence})"
            )
        
        # Update pending data with latest scores (latest-wins)
        _score_batch_pending[match_id]['data'] = score_data
        _score_batch_pending[match_id]['sequence'] = sequence
        
        # Schedule new flush (resets 100ms window)
        new_handle = _schedule_score_batch(match_id, tournament_id)
        _score_batch_pending[match_id]['handle'] = new_handle
        
        logger.debug(
            f"Updated batched score for match {match_id}, seq={sequence} "
            f"(latest wins, window reset)"
        )
    else:
        # Create new batch with 100ms timer
        handle = _schedule_score_batch(match_id, tournament_id)
        _score_batch_pending[match_id] = {
            'data': score_data,
            'sequence': sequence,
            'handle': handle,
        }
        logger.debug(
            f"Created batched score for match {match_id}, seq={sequence} "
            f"(100ms window started)"
        )


async def broadcast_match_started(tournament_id: int, match_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting match_started events.
    
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        match_data: Match details (id, participants, scheduled_time, etc.)
    """
    await broadcast_tournament_event(tournament_id, 'match_started', match_data)


async def broadcast_score_updated(tournament_id: int, score_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting score_updated events (non-batched).
    
    Module 4.5: For single-shot score updates. For rapid updates, use 
    broadcast_score_updated_batched() instead to enable micro-batching.
    
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        score_data: Score details (match_id, participant1_score, participant2_score, etc.)
    """
    await broadcast_tournament_event(tournament_id, 'score_updated', score_data)


async def broadcast_match_completed(tournament_id: int, result_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting match_completed events.
    
    Module 6.1: Converted to async-native implementation.
    - Flushes any pending score batch for this match first (immediate flush)
    - Then broadcasts match_completed with no debounce
    - Sends to both tournament and match channels (Module 4.5 spec)
    
    This ensures score updates are sent before completion event.
    
    Args:
        tournament_id: Tournament ID
        result_data: Match result (match_id, winner_id, final_scores, etc.)
    """
    # Module 6.1: Flush any pending score batch immediately before completion
    match_id = result_data.get('match_id')
    if match_id and match_id in _score_batch_pending:
        logger.debug(f"Flushing pending score batch for match {match_id} before completion")
        await _flush_batch(match_id, tournament_id)
    
    # Broadcast completion immediately (no batching) to tournament room
    await broadcast_tournament_event(tournament_id, 'match_completed', result_data)
    
    # Module 4.5: Also broadcast to match-specific room
    if match_id:
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                await channel_layer.group_send(
                    f'match_{match_id}',
                    {
                        'type': 'match_completed',
                        'data': result_data,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to broadcast match_completed to match room: {e}")


async def broadcast_bracket_updated(tournament_id: int, bracket_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting bracket_updated events.
    
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        bracket_data: Bracket update (bracket_id, updated_nodes, next_matches, etc.)
    """
    await broadcast_tournament_event(tournament_id, 'bracket_updated', bracket_data)


async def broadcast_bracket_generated(tournament_id: int, bracket_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting bracket_generated events.
    
    Sent when a new bracket is generated or regenerated for a tournament.
    Clients can use this to refresh bracket visualization.
    
    Module: 4.1 - Bracket Generation API
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        bracket_data: Bracket details (bracket_id, format, total_matches, seeding_method, etc.)
    
    Example:
        >>> await broadcast_bracket_generated(
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
    await broadcast_tournament_event(tournament_id, 'bracket_generated', bracket_data)


async def broadcast_dispute_created(tournament_id: int, dispute_data: Dict[str, Any]) -> None:
    """
    Convenience wrapper for broadcasting dispute_created events.
    
    Sent when a new dispute is reported for a match.
    Alerts organizers and participants of dispute status.
    
    Module: 4.5 - WebSocket Enhancement
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        dispute_data: Dispute details (dispute_id, match_id, reason, status, timestamp, etc.)
    
    Example:
        >>> await broadcast_dispute_created(
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
    await broadcast_tournament_event(tournament_id, 'dispute_created', dispute_data)


async def broadcast_tournament_completed(
    tournament_id: int,
    winner_registration_id: int,
    runner_up_registration_id: Optional[int],
    third_place_registration_id: Optional[int],
    determination_method: str,
    requires_review: bool,
    rules_applied_summary: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> None:
    """
    Broadcast tournament_completed event with validated schema.
    
    Sent when tournament winner is determined and tournament status transitions
    to COMPLETED. Notifies all connected clients of final results.
    
    **PRIVACY**: Only registration IDs are broadcast. No PII (emails, phone numbers,
    addresses) should ever be included in WebSocket payloads. Clients must fetch
    user details via separate authenticated API calls.
    
    Module: 5.1 - Winner Determination & Verification
    Module 6.1: Converted to async-native implementation.
    
    Args:
        tournament_id: Tournament ID
        winner_registration_id: Registration ID of winner (required)
        runner_up_registration_id: Registration ID of runner-up (optional, finals loser)
        third_place_registration_id: Registration ID of 3rd place (optional, from 3rd place match or semi-final)
        determination_method: Method used ('normal', 'tiebreaker', 'forfeit_chain', etc.)
        requires_review: Whether organizer review is needed (forfeit chains)
        rules_applied_summary: Optional summary of tie-breaker rules applied (condensed for WS)
        timestamp: ISO8601 timestamp of determination (auto-generated if None)
    
    Schema (guaranteed fields):
        {
            'type': 'tournament_completed',
            'tournament_id': int,
            'winner_registration_id': int,
            'runner_up_registration_id': int | null,
            'third_place_registration_id': int | null,
            'determination_method': str,
            'requires_review': bool,
            'rules_applied_summary': dict | null,
            'timestamp': str (ISO8601)
        }
    
    Example:
        >>> from django.utils import timezone
        >>> await broadcast_tournament_completed(
        ...     tournament_id=1,
        ...     winner_registration_id=42,
        ...     runner_up_registration_id=43,
        ...     third_place_registration_id=44,
        ...     determination_method='normal',
        ...     requires_review=False,
        ...     rules_applied_summary=None,
        ...     timestamp=timezone.now().isoformat()
        ... )
        
        >>> # Tie-breaker scenario with review required
        >>> await broadcast_tournament_completed(
        ...     tournament_id=2,
        ...     winner_registration_id=100,
        ...     runner_up_registration_id=101,
        ...     third_place_registration_id=None,
        ...     determination_method='tiebreaker',
        ...     requires_review=False,
        ...     rules_applied_summary={
        ...         'rules': ['head_to_head', 'score_differential'],
        ...         'outcome': 'decided_by_score_differential'
        ...     }
        ... )
    """
    from django.utils import timezone
    
    # Auto-generate timestamp if not provided
    if timestamp is None:
        timestamp = timezone.now().isoformat()
    
    # Construct validated payload
    # PRIVACY NOTE: Only IDs, no user PII
    payload = {
        'type': 'tournament_completed',  # Explicit type field for client routing
        'tournament_id': tournament_id,
        'winner_registration_id': winner_registration_id,
        'runner_up_registration_id': runner_up_registration_id,
        'third_place_registration_id': third_place_registration_id,
        'determination_method': determination_method,
        'requires_review': requires_review,
        'rules_applied_summary': rules_applied_summary,
        'timestamp': timestamp,
    }
    
    logger.info(
        f"Broadcasting tournament_completed for tournament {tournament_id}, "
        f"winner={winner_registration_id}, method={determination_method}",
        extra={
            'tournament_id': tournament_id,
            'winner_registration_id': winner_registration_id,
            'determination_method': determination_method,
            'requires_review': requires_review,
        }
    )
    
    # Broadcast to tournament room only (no match room needed)
    await broadcast_tournament_event(tournament_id, 'tournament_completed', payload)


# ============================================================================
# Module 6.1: Test Helpers (TESTING mode only)
# ============================================================================

async def flush_all_batches() -> None:
    """
    Flush all pending score batches immediately (test helper).
    
    Module 6.1: Test-only helper to avoid race conditions in WebSocket tests.
    
    Iterates all pending batches, cancels their handles, and flushes immediately.
    Should be called in tests before final assertions to ensure all batches are sent.
    
    Example:
        >>> # In test after burst of score updates
        >>> await asyncio.sleep(0.05)  # Let batches queue
        >>> await flush_all_batches()  # Flush before assertions
        >>> response = await communicator.receive_json_from(timeout=1)
    """
    global _score_batch_pending
    
    # Get snapshot of pending matches (avoid iteration mutation)
    pending_matches = list(_score_batch_pending.keys())
    
    for match_id in pending_matches:
        if match_id in _score_batch_pending:
            batch_info = _score_batch_pending[match_id]
            tournament_id = batch_info['data'].get('tournament_id')
            
            if tournament_id:
                logger.debug(f"Test helper: flushing batch for match {match_id}")
                await _flush_batch(match_id, tournament_id)

