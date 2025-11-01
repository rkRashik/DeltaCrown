# Migration Guide: From Signals to Events

## Overview

This guide shows how to migrate from Django signals to the new Event Bus system.

## Why Migrate?

### Problems with Django Signals:
- ❌ Hidden side effects (business logic obscured)
- ❌ Unpredictable execution order
- ❌ Hard to test (can't easily disable signals)
- ❌ Hard to debug (no visibility into what's happening)
- ❌ Circular dependencies (signals can trigger more signals)

### Benefits of Event Bus:
- ✅ Explicit event publishing (clear intent)
- ✅ Priority-based execution order
- ✅ Easy to test (can disable handlers)
- ✅ Easy to debug (comprehensive logging + event history)
- ✅ No circular dependencies (events don't automatically trigger more events)

## Migration Strategy

### Step 1: Identify Signal Handlers

Find all signal handlers in your app:
```bash
grep -r "@receiver" apps/tournaments/
grep -r "post_save.connect" apps/tournaments/
```

### Step 2: Convert to Event Handlers

For each signal handler, create an equivalent event handler.

### Step 3: Publish Events Explicitly

Update code to publish events when actions occur.

### Step 4: Test Thoroughly

Run tests to ensure new system works correctly.

### Step 5: Remove Old Signals

Once tested, remove old signal handlers.

## Common Migrations

### Example 1: Auto-Create Related Object

**Old (Signal):**
```python
# apps/tournaments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Tournament)
def _ensure_tournament_settings(sender, instance, created, **kwargs):
    """Auto-create TournamentSettings when Tournament is created"""
    if created:
        TournamentSettings.objects.create(tournament=instance)
```

**New (Event):**
```python
# apps/tournaments/events/handlers.py
from apps.core.events.bus import event_bus
from apps.tournaments.models import TournamentSettings

def create_tournament_settings(event):
    """Create TournamentSettings when tournament is created"""
    tournament_id = event.tournament_id
    TournamentSettings.objects.get_or_create(tournament_id=tournament_id)

# Register handler
event_bus.subscribe(
    'tournament.created',
    create_tournament_settings,
    name='create_tournament_settings',
    priority=10  # Run early
)
```

**Publisher (in service layer):**
```python
# apps/tournaments/services/tournament_service.py
from apps.core.events.bus import event_bus
from apps.core.events.events import TournamentCreatedEvent

def create_tournament(user, **data):
    """Create a new tournament"""
    tournament = Tournament.objects.create(**data)
    
    # Explicitly publish event
    event = TournamentCreatedEvent(data={
        'tournament_id': tournament.id,
        'created_by': user.id
    })
    event_bus.publish(event)
    
    return tournament
```

### Example 2: Cross-App Integration

**Old (Signal):**
```python
# apps/tournaments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.economy.models import CoinTransaction

@receiver(post_save, sender=PaymentVerification)
def _maybe_award_coins_on_verification(sender, instance, created, **kwargs):
    """Award coins when payment is verified"""
    if instance.verified:
        registration = instance.registration
        CoinTransaction.objects.create(
            user=registration.user,
            amount=50,
            reason='tournament_registration'
        )
```

**New (Event):**
```python
# apps/economy/events/handlers.py
from apps.core.events.bus import event_bus
from apps.economy.models import CoinTransaction

def award_registration_coins(event):
    """Award coins when registration is confirmed"""
    user_id = event.data.get('user_id')
    tournament_id = event.data.get('tournament_id')
    
    if user_id:
        CoinTransaction.objects.create(
            user_id=user_id,
            amount=50,
            reason=f'tournament_registration_{tournament_id}'
        )

# Register in economy app
event_bus.subscribe(
    'registration.confirmed',
    award_registration_coins,
    name='award_registration_coins'
)
```

**Publisher:**
```python
# apps/tournaments/services/payment_service.py
from apps.core.events.bus import event_bus
from apps.core.events.events import RegistrationConfirmedEvent

def verify_payment(payment_verification):
    """Verify a payment"""
    payment_verification.verified = True
    payment_verification.save()
    
    # Publish event for other apps to react
    event = RegistrationConfirmedEvent(data={
        'registration_id': payment_verification.registration.id,
        'tournament_id': payment_verification.registration.tournament.id,
        'team_id': payment_verification.registration.team_id,
        'user_id': payment_verification.registration.user_id
    })
    event_bus.publish(event)
```

### Example 3: Notification Sending

**Old (Signal):**
```python
# apps/tournaments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.models import Notification

@receiver(post_save, sender=Match)
def _notify_match_scheduled(sender, instance, created, **kwargs):
    """Notify teams when match is scheduled"""
    if created:
        for team in [instance.team1, instance.team2]:
            Notification.objects.create(
                user=team.captain,
                message=f"Match scheduled: {instance}"
            )
```

**New (Event):**
```python
# apps/notifications/events/handlers.py
from apps.core.events.bus import event_bus
from apps.notifications.services import NotificationService

def notify_match_scheduled(event):
    """Send notifications when match is scheduled"""
    match_id = event.match_id
    
    # Use service layer
    notification_service = NotificationService()
    notification_service.send_match_scheduled_notification(match_id)

# Register handler
event_bus.subscribe(
    'match.scheduled',
    notify_match_scheduled,
    name='notify_match_scheduled',
    async_processing=True  # Run in background
)
```

**Publisher:**
```python
# apps/tournaments/services/match_service.py
from apps.core.events.bus import event_bus
from apps.core.events.events import MatchScheduledEvent

def schedule_match(tournament, team1, team2, scheduled_time):
    """Schedule a new match"""
    match = Match.objects.create(
        tournament=tournament,
        team1=team1,
        team2=team2,
        scheduled_time=scheduled_time
    )
    
    # Publish event
    event = MatchScheduledEvent(data={
        'match_id': match.id,
        'tournament_id': tournament.id,
        'team1_id': team1.id,
        'team2_id': team2.id
    })
    event_bus.publish(event)
    
    return match
```

## Testing Strategy

### Old Way (Hard to Test):
```python
# tests/test_tournaments.py
def test_tournament_creation():
    """Test creating tournament"""
    tournament = Tournament.objects.create(name="Test Tournament")
    
    # Signal automatically created settings, but hard to verify
    # and can't disable for isolated testing
    assert TournamentSettings.objects.filter(tournament=tournament).exists()
```

### New Way (Easy to Test):
```python
# tests/test_tournaments.py
from apps.core.events.bus import event_bus

def test_tournament_creation_without_side_effects():
    """Test tournament creation in isolation"""
    # Disable event handlers for this test
    event_bus.disable_handler('tournament.created', 'create_tournament_settings')
    
    tournament = Tournament.objects.create(name="Test Tournament")
    
    # No settings created because handler is disabled
    assert not TournamentSettings.objects.filter(tournament=tournament).exists()
    
    # Re-enable handler
    event_bus.enable_handler('tournament.created', 'create_tournament_settings')

def test_tournament_creation_with_events():
    """Test tournament creation with events"""
    from apps.tournaments.services.tournament_service import create_tournament
    
    tournament = create_tournament(user=user, name="Test Tournament")
    
    # Event was published, handlers ran
    assert TournamentSettings.objects.filter(tournament=tournament).exists()

def test_event_handler_directly():
    """Test event handler in isolation"""
    from apps.tournaments.events.handlers import create_tournament_settings
    from apps.core.events.events import TournamentCreatedEvent
    
    tournament = Tournament.objects.create(name="Test Tournament")
    
    # Create event manually
    event = TournamentCreatedEvent(data={'tournament_id': tournament.id})
    
    # Call handler directly
    create_tournament_settings(event)
    
    # Verify settings created
    assert TournamentSettings.objects.filter(tournament=tournament).exists()
```

## Debugging Events

### View Event History:
```python
from apps.core.events.bus import event_bus

# Get recent events
recent = event_bus.get_event_history(limit=20)
for event in recent:
    print(f"{event.timestamp}: {event.event_type}")
    print(f"  Data: {event.data}")
    print(f"  Source: {event.source}")

# Get specific event type
tournament_events = event_bus.get_event_history(
    event_type='tournament.created',
    limit=10
)
```

### View Registered Handlers:
```python
from apps.core.events.bus import event_bus

# See what handlers are registered
handlers = event_bus.get_handlers('tournament.created')
for handler in handlers:
    print(f"Handler: {handler.name}")
    print(f"  Enabled: {handler.enabled}")
    print(f"  Priority: {handler.priority}")
    print(f"  Async: {handler.async_processing}")
```

### Enable Detailed Logging:
```python
# deltacrown/settings.py
LOGGING = {
    # ... existing config
    'loggers': {
        'apps.core.events': {
            'level': 'DEBUG',  # See all event activity
            'handlers': ['console'],
        },
    }
}
```

## Migration Checklist

For each signal handler:

- [ ] Create event type (if not exists) in `apps/core/events/events.py`
- [ ] Create event handler function
- [ ] Register handler with `event_bus.subscribe()`
- [ ] Update service layer to publish event
- [ ] Write tests for handler
- [ ] Test integration end-to-end
- [ ] Remove old signal handler
- [ ] Update documentation

## Common Pitfalls

### 1. Forgetting to Publish Events
**Problem:** Handler registered but event never published
**Solution:** Always publish events in service layer after action

### 2. Circular Event Publishing
**Problem:** Handler publishes event that triggers itself
**Solution:** Use different event types or check event source

### 3. Forgetting to Register Handlers
**Problem:** Handler function exists but never subscribed
**Solution:** Register in app's `ready()` method or at module level

### 4. Async Handler Blocking
**Problem:** Async handler takes too long and blocks
**Solution:** Use `async_processing=True` for non-critical handlers

## Where to Register Handlers

### Option 1: In App's ready() Method
```python
# apps/tournaments/apps.py
class TournamentsConfig(AppConfig):
    def ready(self):
        from .events import handlers  # Import registers handlers
```

### Option 2: At Module Level
```python
# apps/tournaments/events/handlers.py
from apps.core.events.bus import event_bus

def my_handler(event):
    # Handle event
    pass

# Register immediately when module is imported
event_bus.subscribe('tournament.created', my_handler)
```

### Option 3: Manual Registration
```python
# Somewhere in your code
from apps.core.events.bus import event_bus
from apps.tournaments.events.handlers import my_handler

event_bus.subscribe('tournament.created', my_handler)
```

## Next Steps

After migrating from signals:
1. ✅ All signal handlers converted to event handlers
2. ✅ Service layer publishes events explicitly
3. ✅ Tests updated to use new system
4. ✅ Old signal handlers removed
5. → Move on to implementing game plugins
6. → Register services in Service Registry
7. → Create API Gateway endpoints

The new system is more explicit, easier to test, and gives you full control! 🚀
