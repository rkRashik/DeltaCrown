"""
Event Bus System - Replaces Django Signals

Industry-standard event-driven architecture with explicit event publishing,
subscription management, and comprehensive logging.

Benefits over Django Signals:
- Explicit event publishing (no hidden side effects)
- Easy to trace event flow
- Can enable/disable handlers
- Async processing support
- Comprehensive logging
- Event versioning support
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event class - all events inherit from this"""
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"


@dataclass
class EventHandler:
    """Event handler registration"""
    name: str
    handler: Callable
    event_type: str
    enabled: bool = True
    async_processing: bool = False
    priority: int = 100  # Lower = higher priority


class EventBus:
    """
    Central event bus for application-wide events.
    
    Usage:
        # Subscribe to events
        event_bus.subscribe('tournament.created', handle_tournament_created)
        
        # Publish events
        event_bus.publish(Event(
            event_type='tournament.created',
            data={'tournament_id': 123}
        ))
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._initialized = False
        self._enable_history = True
        self._max_history = 1000
    
    def initialize(self):
        """Initialize event bus"""
        if self._initialized:
            return
        
        logger.info("🚀 Initializing Event Bus")
        self._initialized = True
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        name: Optional[str] = None,
        async_processing: bool = False,
        priority: int = 100
    ):
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to (e.g., 'tournament.created')
            handler: Callable that handles the event
            name: Optional handler name for logging
            async_processing: If True, handler runs in background thread
            priority: Handler priority (lower = runs first)
        """
        handler_name = name or handler.__name__
        
        event_handler = EventHandler(
            name=handler_name,
            handler=handler,
            event_type=event_type,
            async_processing=async_processing,
            priority=priority
        )
        
        self._handlers[event_type].append(event_handler)
        
        # Sort by priority
        self._handlers[event_type].sort(key=lambda h: h.priority)
        
        logger.info(f"📝 Subscribed: {handler_name} → {event_type} (priority: {priority})")
    
    def unsubscribe(self, event_type: str, handler_name: str):
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type]
                if h.name != handler_name
            ]
            logger.info(f"❌ Unsubscribed: {handler_name} from {event_type}")
    
    def publish(self, event: Event, sync: bool = False):
        """
        Publish an event to all subscribed handlers.
        
        Args:
            event: Event to publish
            sync: If True, wait for all handlers to complete
        """
        if not self._initialized:
            logger.warning("⚠️ Event bus not initialized, initializing now")
            self.initialize()
        
        # Store in history
        if self._enable_history:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        # Get handlers for this event type
        handlers = self._handlers.get(event.event_type, [])
        
        if not handlers:
            logger.debug(f"📭 No handlers for event: {event.event_type}")
            return
        
        logger.info(f"📢 Publishing event: {event.event_type} ({len(handlers)} handlers)")
        
        # Execute handlers
        for handler in handlers:
            if not handler.enabled:
                logger.debug(f"⏭️ Skipped (disabled): {handler.name}")
                continue
            
            try:
                if handler.async_processing and not sync:
                    # Run in background thread
                    self._executor.submit(self._execute_handler, handler, event)
                    logger.debug(f"🔄 Async: {handler.name}")
                else:
                    # Run synchronously
                    self._execute_handler(handler, event)
                    logger.debug(f"✅ Executed: {handler.name}")
            
            except Exception as e:
                logger.error(
                    f"❌ Handler failed: {handler.name} for {event.event_type}",
                    exc_info=True
                )
                # Continue with other handlers even if one fails
    
    def _execute_handler(self, handler: EventHandler, event: Event):
        """Execute a single handler"""
        try:
            handler.handler(event)
        except Exception as e:
            logger.error(
                f"❌ Error in handler {handler.name}: {str(e)}",
                exc_info=True
            )
            raise
    
    def enable_handler(self, event_type: str, handler_name: str):
        """Enable a specific handler"""
        for handler in self._handlers.get(event_type, []):
            if handler.name == handler_name:
                handler.enabled = True
                logger.info(f"✅ Enabled handler: {handler_name} for {event_type}")
    
    def disable_handler(self, event_type: str, handler_name: str):
        """Disable a specific handler"""
        for handler in self._handlers.get(event_type, []):
            if handler.name == handler_name:
                handler.enabled = False
                logger.info(f"⏸️ Disabled handler: {handler_name} for {event_type}")
    
    def get_handlers(self, event_type: str) -> List[EventHandler]:
        """Get all handlers for an event type"""
        return self._handlers.get(event_type, [])
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Get recent event history"""
        if event_type:
            events = [e for e in self._event_history if e.event_type == event_type]
        else:
            events = self._event_history
        
        return events[-limit:]
    
    def clear_handlers(self, event_type: Optional[str] = None):
        """Clear all handlers (use with caution!)"""
        if event_type:
            self._handlers[event_type] = []
            logger.warning(f"🗑️ Cleared handlers for: {event_type}")
        else:
            self._handlers.clear()
            logger.warning("🗑️ Cleared ALL event handlers")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'total_event_types': len(self._handlers),
            'total_handlers': sum(len(handlers) for handlers in self._handlers.values()),
            'event_history_size': len(self._event_history),
            'event_types': list(self._handlers.keys()),
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (
            f"EventBus(event_types={stats['total_event_types']}, "
            f"handlers={stats['total_handlers']}, "
            f"history={stats['event_history_size']})"
        )


# Global event bus instance
event_bus = EventBus()


# Convenience decorator for subscribing handlers
def event_handler(event_type: str, **kwargs):
    """
    Decorator to register event handlers.
    
    Usage:
        @event_handler('tournament.created', priority=10)
        def handle_tournament_created(event: Event):
            tournament_id = event.data['tournament_id']
            # Handle event
    """
    def decorator(func):
        event_bus.subscribe(event_type, func, name=func.__name__, **kwargs)
        return func
    return decorator
