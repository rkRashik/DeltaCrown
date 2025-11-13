"""
WebSocket Broadcasting Utilities for Tournament Events (Phase F).

Provides helper functions to broadcast tournament events to WebSocket rooms,
including new rank_update events for real-time leaderboard updates.

Usage:
    from apps.tournaments.realtime.broadcast import broadcast_rank_update
    
    # After leaderboard recompute:
    broadcast_rank_update(tournament_id, rank_deltas)

Event Types:
    - match_started: Match begins
    - score_updated: Match score changes
    - match_completed: Match finishes
    - bracket_updated: Bracket progression
    - rank_update: Leaderboard rank changes (NEW in Phase F)
    - dispute_created: Dispute filed

Module Integration:
    - Module 2.2: WebSocket real-time updates
    - Module 2.6: Realtime monitoring (metrics)
    - Phase F: Leaderboard ranking engine optimization
"""
import logging
from typing import List, Dict, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from . import metrics
from . import logging as ws_logging

logger = logging.getLogger(__name__)


def _get_room_group_name(tournament_id: int) -> str:
    """
    Get channel layer group name for tournament room.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        Group name string (e.g., "tournament_123")
    """
    return f"tournament_{tournament_id}"


def broadcast_match_started(
    tournament_id: int,
    match_id: int,
    round_number: int,
    participant1_id: Optional[int] = None,
    team1_id: Optional[int] = None,
    participant2_id: Optional[int] = None,
    team2_id: Optional[int] = None
) -> bool:
    """
    Broadcast match_started event to tournament room.
    
    Args:
        tournament_id: Tournament ID
        match_id: Match ID
        round_number: Round number
        participant1_id: Player 1 ID (solo tournaments)
        team1_id: Team 1 ID (team tournaments)
        participant2_id: Player 2 ID (solo tournaments)
        team2_id: Team 2 ID (team tournaments)
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "match_started",
            "tournament_id": 123,
            "match_id": 456,
            "round": 3,
            "participant1_id": 789,
            "participant2_id": 101,
        }
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": "match_started",
        "tournament_id": tournament_id,
        "match_id": match_id,
        "round": round_number,
    }
    
    if participant1_id:
        payload["participant1_id"] = participant1_id
    if team1_id:
        payload["team1_id"] = team1_id
    if participant2_id:
        payload["participant2_id"] = participant2_id
    if team2_id:
        payload["team2_id"] = team2_id
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast match_started (tournament={tournament_id}, match={match_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast match_started: {e}")
        return False


def broadcast_score_updated(
    tournament_id: int,
    match_id: int,
    participant1_id: Optional[int] = None,
    team1_id: Optional[int] = None,
    score1: int = 0,
    participant2_id: Optional[int] = None,
    team2_id: Optional[int] = None,
    score2: int = 0
) -> bool:
    """
    Broadcast score_updated event to tournament room.
    
    Args:
        tournament_id: Tournament ID
        match_id: Match ID
        participant1_id: Player 1 ID (solo tournaments)
        team1_id: Team 1 ID (team tournaments)
        score1: Player/Team 1 score
        participant2_id: Player 2 ID (solo tournaments)
        team2_id: Team 2 ID (team tournaments)
        score2: Player/Team 2 score
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "score_updated",
            "tournament_id": 123,
            "match_id": 456,
            "participant1_id": 789,
            "score1": 12,
            "participant2_id": 101,
            "score2": 8,
        }
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": "score_updated",
        "tournament_id": tournament_id,
        "match_id": match_id,
    }
    
    if participant1_id:
        payload["participant1_id"] = participant1_id
        payload["score1"] = score1
    if team1_id:
        payload["team1_id"] = team1_id
        payload["score1"] = score1
    if participant2_id:
        payload["participant2_id"] = participant2_id
        payload["score2"] = score2
    if team2_id:
        payload["team2_id"] = team2_id
        payload["score2"] = score2
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast score_updated (tournament={tournament_id}, match={match_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast score_updated: {e}")
        return False


def broadcast_match_completed(
    tournament_id: int,
    match_id: int,
    winner_participant_id: Optional[int] = None,
    winner_team_id: Optional[int] = None,
    final_score1: int = 0,
    final_score2: int = 0
) -> bool:
    """
    Broadcast match_completed event to tournament room.
    
    Args:
        tournament_id: Tournament ID
        match_id: Match ID
        winner_participant_id: Winning player ID (solo tournaments)
        winner_team_id: Winning team ID (team tournaments)
        final_score1: Final score for side 1
        final_score2: Final score for side 2
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "match_completed",
            "tournament_id": 123,
            "match_id": 456,
            "winner_participant_id": 789,
            "final_score1": 16,
            "final_score2": 12,
        }
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": "match_completed",
        "tournament_id": tournament_id,
        "match_id": match_id,
        "final_score1": final_score1,
        "final_score2": final_score2,
    }
    
    if winner_participant_id:
        payload["winner_participant_id"] = winner_participant_id
    if winner_team_id:
        payload["winner_team_id"] = winner_team_id
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast match_completed (tournament={tournament_id}, match={match_id}, winner={winner_participant_id or winner_team_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast match_completed: {e}")
        return False


def broadcast_bracket_updated(tournament_id: int) -> bool:
    """
    Broadcast bracket_updated event to tournament room.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "bracket_updated",
            "tournament_id": 123,
        }
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": "bracket_updated",
        "tournament_id": tournament_id,
    }
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast bracket_updated (tournament={tournament_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast bracket_updated: {e}")
        return False


def broadcast_dispute_created(
    tournament_id: int,
    match_id: int,
    dispute_id: int,
    filed_by_participant_id: Optional[int] = None,
    filed_by_team_id: Optional[int] = None
) -> bool:
    """
    Broadcast dispute_created event to tournament room.
    
    Args:
        tournament_id: Tournament ID
        match_id: Match ID
        dispute_id: Dispute ID
        filed_by_participant_id: Player ID who filed dispute (solo tournaments)
        filed_by_team_id: Team ID who filed dispute (team tournaments)
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "dispute_created",
            "tournament_id": 123,
            "match_id": 456,
            "dispute_id": 789,
            "filed_by_participant_id": 101,
        }
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": "dispute_created",
        "tournament_id": tournament_id,
        "match_id": match_id,
        "dispute_id": dispute_id,
    }
    
    if filed_by_participant_id:
        payload["filed_by_participant_id"] = filed_by_participant_id
    if filed_by_team_id:
        payload["filed_by_team_id"] = filed_by_team_id
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast dispute_created (tournament={tournament_id}, match={match_id}, dispute={dispute_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast dispute_created: {e}")
        return False


# ============================================================================
# Phase F: Rank Update Broadcast (NEW)
# ============================================================================

def broadcast_rank_update(
    tournament_id: int,
    rank_deltas: List[Dict[str, Any]]
) -> bool:
    """
    Broadcast rank_update event to tournament room (Phase F).
    
    Args:
        tournament_id: Tournament ID
        rank_deltas: List of rank change dicts with keys:
            - participant_id or team_id (IDs-only)
            - previous_rank (int or None)
            - current_rank (int)
            - rank_change (int, negative = moved up)
            - points (int)
            
    Returns:
        True if broadcast succeeded, False otherwise
        
    Payload (IDs-only):
        {
            "type": "rank_update",
            "tournament_id": 123,
            "changes": [
                {
                    "participant_id": 91,
                    "previous_rank": 5,
                    "current_rank": 3,
                    "rank_change": -2,
                    "points": 1250
                },
                {
                    "participant_id": 44,
                    "previous_rank": 11,
                    "current_rank": 14,
                    "rank_change": 3,
                    "points": 890
                }
            ]
        }
        
    Usage:
        from apps.leaderboards.engine import RankingEngine
        from apps.tournaments.realtime.broadcast import broadcast_rank_update
        
        # After match completion:
        engine = RankingEngine()
        response = engine.compute_partial_update(
            tournament_id,
            affected_participant_ids={456, 789},
            affected_team_ids=set()
        )
        
        # Broadcast deltas to spectators:
        deltas_json = [d.to_dict() for d in response.deltas]
        broadcast_rank_update(tournament_id, deltas_json)
        
    Observability:
        Uses Module 2.6 metrics:
        - ws_messages_total{type="rank_update"}
        - ws_message_latency_seconds
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    # Filter to only rank changes (exclude new entries with no previous rank)
    significant_changes = [
        delta for delta in rank_deltas
        if delta.get("previous_rank") is not None and delta.get("rank_change") != 0
    ]
    
    if not significant_changes:
        logger.debug(f"No significant rank changes for tournament {tournament_id}, skipping broadcast")
        return True
    
    payload = {
        "type": "tournament_event",
        "event_type": "rank_update",
        "tournament_id": tournament_id,
        "changes": significant_changes,
    }
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        
        # Module 2.6 observability: Record message metric
        metrics.record_message(
            user_id=None,  # System-initiated broadcast
            tournament_id=tournament_id,
            message_type="rank_update",
            direction="outbound"
        )
        
        logger.info(f"Broadcast rank_update (tournament={tournament_id}, {len(significant_changes)} changes)")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast rank_update: {e}")
        return False


def broadcast_event(
    tournament_id: int,
    event_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    Generic event broadcaster for custom events.
    
    Args:
        tournament_id: Tournament ID
        event_type: Event type string (e.g., "custom_event")
        data: Event payload dict (must be JSON-serializable, IDs-only)
        
    Returns:
        True if broadcast succeeded, False otherwise
        
    Usage:
        broadcast_event(
            tournament_id=123,
            event_type="prize_distribution",
            data={"participant_id": 456, "prize_amount": 5000}
        )
    """
    channel_layer = get_channel_layer()
    room_group = _get_room_group_name(tournament_id)
    
    payload = {
        "type": "tournament_event",
        "event_type": event_type,
        "tournament_id": tournament_id,
        **data,
    }
    
    try:
        async_to_sync(channel_layer.group_send)(room_group, payload)
        logger.info(f"Broadcast {event_type} (tournament={tournament_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast {event_type}: {e}")
        return False
