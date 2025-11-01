"""
Core Infrastructure - README

Welcome to DeltaCrown's Core Infrastructure!

This package provides foundational components for building loosely coupled,
event-driven architecture that scales professionally.

## 🏗️ Components

### 1. Event Bus (`apps.core.events`)
Replaces Django signals with explicit, traceable event system.

**Problem it solves:**
- "Signal Hell" - hidden business logic across signal handlers
- Unpredictable execution order
- Hard to test and debug

**Benefits:**
- ✅ Explicit event publishing (no surprises)
- ✅ Easy to trace event flow
- ✅ Enable/disable handlers at runtime
- ✅ Comprehensive logging
- ✅ Priority-based execution
- ✅ Async processing support

**Usage:**
```python
from apps.core.events.bus import event_bus, Event
from apps.core.events.events import TournamentCreatedEvent

# Subscribe to events
def handle_tournament_created(event: TournamentCreatedEvent):
    tournament_id = event.tournament_id
    # Send notifications, update rankings, etc.

event_bus.subscribe('tournament.created', handle_tournament_created)

# Publish events
event = TournamentCreatedEvent(data={'tournament_id': 123})
event_bus.publish(event)
```

### 2. Service Registry (`apps.core.registry`)
App discovery and loose coupling between apps.

**Problem it solves:**
- Direct imports between apps create tight coupling
- Changing one app breaks others
- Hard to test apps in isolation

**Benefits:**
- ✅ No direct imports between apps
- ✅ Easy to mock services for testing
- ✅ Services can be enabled/disabled at runtime
- ✅ Clear API contracts

**Usage:**
```python
from apps.core.registry.service_registry import service_registry

# Register a service (in tournaments app)
class TournamentService:
    def get_active_tournaments(self):
        return Tournament.objects.filter(status='active')

service_registry.register(
    'tournament_service',
    TournamentService(),
    app_name='tournaments'
)

# Use service (in teams app)
tournament_service = service_registry.get('tournament_service')
if tournament_service:
    tournaments = tournament_service.get_active_tournaments()
```

### 3. Plugin Framework (`apps.core.plugins`)
Extensible game system - add new games without modifying core code.

**Problem it solves:**
- Game-specific logic hardcoded throughout tournament system
- Adding new games requires changing 6+ files
- No separation between game logic and tournament logic

**Benefits:**
- ✅ Add new games by creating a plugin
- ✅ Each game is self-contained
- ✅ Clear plugin API contract
- ✅ Easy to test plugins in isolation

**Usage:**
```python
from apps.core.plugins.registry import plugin_registry, GamePlugin

# Create a game plugin (in game_valorant app)
class ValorantPlugin(GamePlugin):
    name = "valorant"
    display_name = "VALORANT"
    min_team_size = 5
    max_team_size = 5
    
    def validate_team(self, team_data):
        if team_data['size'] != 5:
            return False, "VALORANT teams must have exactly 5 players"
        return True, None
    
    def get_default_config(self):
        return {
            'map': 'Bind',
            'rounds': 25,
            'overtime': True
        }

# Register plugin
plugin_registry.register(ValorantPlugin())

# Use plugin (in tournaments app)
valorant = plugin_registry.get('valorant')
is_valid, error = valorant.validate_team(team_data)
```

### 4. API Gateway (`apps.core.api_gateway`)
Internal API for inter-app communication.

**Problem it solves:**
- Direct function calls between apps create tight coupling
- No versioning for internal APIs
- Hard to test cross-app interactions

**Benefits:**
- ✅ Versioned APIs for backward compatibility
- ✅ Request/response logging
- ✅ Easy to mock for testing
- ✅ Clear API contracts

**Usage:**
```python
from apps.core.api_gateway import api_gateway, APIRequest, APIResponse

# Register API endpoint (in tournaments app)
def get_tournament(request: APIRequest) -> APIResponse:
    tournament_id = request.data['tournament_id']
    tournament = Tournament.objects.get(id=tournament_id)
    return APIResponse(
        success=True,
        data={
            'id': tournament.id,
            'name': tournament.name,
            'status': tournament.status
        }
    )

api_gateway.register_endpoint('tournaments.get', get_tournament, version='v1')

# Call API (from teams app)
response = api_gateway.call(APIRequest(
    endpoint='tournaments.get',
    method='get',
    data={'tournament_id': 123},
    requester='teams_app'
))

if response.success:
    tournament_name = response.data['name']
```

## 📁 File Structure

```
apps/core/
├── __init__.py                 # Package initialization
├── apps.py                     # Django app config (auto-initializes systems)
├── events/
│   ├── __init__.py            # Event Bus implementation
│   └── events.py              # Common event definitions
├── registry/
│   ├── __init__.py            # Service Registry exports
│   └── service_registry.py    # Service Registry implementation
├── plugins/
│   ├── __init__.py            # Plugin Framework exports
│   └── registry.py            # Plugin Registry implementation
└── api_gateway/
    └── __init__.py            # API Gateway implementation
```

## 🚀 Getting Started

### 1. Installation

Core infrastructure is automatically initialized when Django starts.
Just add to INSTALLED_APPS (must be first):

```python
# deltacrown/settings.py
INSTALLED_APPS = [
    "apps.core",  # MUST be first!
    # ... other apps
]
```

### 2. Migration from Django Signals

**Old way (signals):**
```python
# apps/tournaments/signals.py
@receiver(post_save, sender=Tournament)
def _ensure_tournament_settings(sender, instance, created, **kwargs):
    if created:
        TournamentSettings.objects.create(tournament=instance)
```

**New way (events):**
```python
# apps/tournaments/services.py
from apps.core.events.bus import event_bus
from apps.core.events.events import TournamentCreatedEvent

def create_tournament(data):
    tournament = Tournament.objects.create(**data)
    
    # Explicitly publish event
    event = TournamentCreatedEvent(data={'tournament_id': tournament.id})
    event_bus.publish(event)
    
    return tournament

# apps/tournaments/handlers.py
from apps.core.events.bus import event_bus

def handle_tournament_created(event):
    tournament_id = event.tournament_id
    TournamentSettings.objects.create(tournament_id=tournament_id)

event_bus.subscribe('tournament.created', handle_tournament_created)
```

**Why this is better:**
- ✅ Explicit - you see exactly when events are published
- ✅ Traceable - full event log with timestamps
- ✅ Testable - can disable/enable handlers
- ✅ Controllable - set priority, async execution
- ✅ Debuggable - comprehensive logging

### 3. Migration from Direct Imports

**Old way (tight coupling):**
```python
# apps/teams/views.py
from apps.tournaments.models import Tournament  # BAD: direct import

def team_detail(request, team_id):
    team = Team.objects.get(id=team_id)
    tournaments = Tournament.objects.filter(registrations__team=team)
```

**New way (loose coupling via Service):**
```python
# apps/teams/views.py
from apps.core.registry.service_registry import service_registry

def team_detail(request, team_id):
    team = Team.objects.get(id=team_id)
    
    # Get service from registry
    tournament_service = service_registry.get('tournament_service')
    if tournament_service:
        tournaments = tournament_service.get_tournaments_for_team(team.id)
```

**New way (loose coupling via API Gateway):**
```python
# apps/teams/views.py
from apps.core.api_gateway import api_gateway, APIRequest

def team_detail(request, team_id):
    team = Team.objects.get(id=team_id)
    
    # Call internal API
    response = api_gateway.call(APIRequest(
        endpoint='tournaments.list_for_team',
        method='get',
        data={'team_id': team.id},
        requester='teams_app'
    ))
    
    if response.success:
        tournaments = response.data['tournaments']
```

## 🧪 Testing

Run tests:
```bash
pytest tests/test_core_infrastructure.py -v
```

Test coverage:
- Event Bus: Subscribe, publish, priorities, async, history
- Service Registry: Register, discover, enable/disable
- Plugin Framework: Register, validate, list plugins
- API Gateway: Register endpoints, versioning, error handling

## 📊 Monitoring

### Event Bus Statistics
```python
from apps.core.events.bus import event_bus

stats = event_bus.get_statistics()
# {
#     'total_event_types': 12,
#     'total_handlers': 45,
#     'event_history_size': 234,
#     'event_types': ['tournament.created', 'match.completed', ...]
# }

# Get recent events
recent = event_bus.get_event_history(limit=10)
```

### Service Registry Statistics
```python
from apps.core.registry.service_registry import service_registry

stats = service_registry.get_statistics()
# {
#     'total_services': 8,
#     'enabled': 7,
#     'disabled': 1,
#     'apps': ['tournaments', 'teams', 'economy', ...]
# }
```

### Plugin Registry Statistics
```python
from apps.core.plugins.registry import plugin_registry

stats = plugin_registry.get_statistics()
# {
#     'total_plugins': 3,
#     'enabled': 3,
#     'disabled': 0,
#     'plugin_names': ['valorant', 'efootball', 'csgo']
# }
```

## 🎯 Best Practices

### 1. Event Naming Convention
- Use dot notation: `{entity}.{action}`
- Examples:
  - `tournament.created`
  - `tournament.published`
  - `match.completed`
  - `team.member_joined`
  - `payment.verified`

### 2. Service Naming Convention
- Use descriptive names: `{entity}_service`
- Examples:
  - `tournament_service`
  - `team_service`
  - `notification_service`
  - `economy_service`

### 3. API Endpoint Naming
- Use dot notation: `{entity}.{action}`
- Examples:
  - `tournaments.get`
  - `tournaments.list`
  - `teams.create`
  - `payments.verify`

### 4. When to Use Each System

**Use Event Bus when:**
- One action triggers multiple reactions (tournament created → send notifications, award coins, update rankings)
- Loose coupling between publisher and subscribers
- Don't need immediate response

**Use Service Registry when:**
- Need to call methods on another app's service
- Want dependency injection for testing
- Service-oriented architecture

**Use API Gateway when:**
- Need versioned APIs
- Want request/response pattern
- Need to track API usage
- Cross-app data fetching

**Use Plugin Framework when:**
- Adding new game types
- Need extensibility without modifying core
- Clear contract/interface for plugins

## 🔧 Configuration

All systems initialize automatically in `apps.core.apps.CoreConfig.ready()`.

To customize:
```python
# apps/core/apps.py
def ready(self):
    from .events.bus import event_bus
    
    # Customize event bus
    event_bus._enable_history = True
    event_bus._max_history = 5000
    
    # Initialize
    event_bus.initialize()
```

## 📚 Further Reading

- Enterprise Integration Patterns
- Event-Driven Architecture
- Service-Oriented Architecture (SOA)
- Plugin Architecture Pattern
- Clean Architecture (Robert C. Martin)
- Domain-Driven Design (Eric Evans)

## 🆘 Troubleshooting

### Events not firing?
```python
# Check if handler is registered
handlers = event_bus.get_handlers('tournament.created')
print(f"Found {len(handlers)} handlers")

# Check event history
recent = event_bus.get_event_history(event_type='tournament.created', limit=10)
print(f"Recent events: {len(recent)}")
```

### Service not found?
```python
# List all services
services = service_registry.list_services()
print(f"Registered services: {list(services.keys())}")

# Check if service is disabled
registration = service_registry.get_registration('tournament_service')
if registration:
    print(f"Enabled: {registration.enabled}")
```

### Plugin not loading?
```python
# List all plugins
plugins = plugin_registry.list_plugins()
print(f"Registered plugins: {list(plugins.keys())}")

# Force rediscovery
plugin_registry._initialized = False
plugin_registry.discover_plugins()
```

## 📝 License

Internal DeltaCrown infrastructure - not for public distribution.
"""
