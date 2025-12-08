"""
Shared event infrastructure for DeltaCrown.

This package contains the event bus and event handling infrastructure used across
all domains (TournamentOps, Games, Teams, Economy, Leaderboards, etc.) to enable
loosely-coupled, event-driven communication.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2 (Event Bus Infrastructure)
"""

from .event_bus import Event, EventBus, event_handler, get_event_bus

__all__ = ["Event", "EventBus", "event_handler", "get_event_bus"]
