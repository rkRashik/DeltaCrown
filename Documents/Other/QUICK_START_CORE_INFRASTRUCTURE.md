# Core Infrastructure Quick Start

**Get started with DeltaCrown's event-driven, loosely coupled architecture in 5 minutes!**

## 📦 What's Installed

You now have 4 powerful systems:
1. **Event Bus** - Replace Django signals
2. **Service Registry** - Loose coupling between apps
3. **Plugin Framework** - Extensible game system
4. **API Gateway** - Internal APIs with versioning

## 🚀 Quick Examples

### 1. Publishing Events

```python
# In your service layer (e.g., apps/tournaments/services.py)
from apps.core.events.bus import event_bus
from apps.core.events.events import TournamentCreatedEvent

def create_tournament(name, game):
    tournament = Tournament.objects.create(name=name, game=game)
    
    # Publish event - other apps can react to this
    event = TournamentCreatedEvent(data={
        'tournament_id': tournament.id,
        'name': tournament.name,
        'game': game
    })
    event_bus.publish(event)
    
    return tournament
```

### 2. Subscribing to Events

```python
# In your app (e.g., apps/notifications/handlers.py)
from apps.core.events.bus import event_bus

def send_tournament_notification(event):
    """Send notification when tournament is created"""
    tournament_id = event.tournament_id
    # Send notification logic here
    print(f"Tournament {tournament_id} created!")

# Register handler
event_bus.subscribe('tournament.created', send_tournament_notification)
```

### 3. Using Services

```python
# Register a service (in apps/tournaments/services.py)
from apps.core.registry.service_registry import service_registry

class TournamentService:
    def get_active_tournaments(self):
        return Tournament.objects.filter(status='active')
    
    def get_tournament(self, tournament_id):
        return Tournament.objects.get(id=tournament_id)

# Register the service
tournament_service = TournamentService()
service_registry.register('tournament_service', tournament_service, app_name='tournaments')
```

```python
# Use the service (in apps/teams/views.py)
from apps.core.registry.service_registry import service_registry

def my_view(request):
    # Get service (no direct import from tournaments!)
    tournament_service = service_registry.get('tournament_service')
    
    if tournament_service:
        tournaments = tournament_service.get_active_tournaments()
    
    return render(request, 'template.html', {'tournaments': tournaments})
```

### 4. Creating Game Plugins

```python
# Create apps/game_valorant/plugin.py
from apps.core.plugins.registry import GamePlugin, plugin_registry

class ValorantPlugin(GamePlugin):
    name = "valorant"
    display_name = "VALORANT"
    version = "1.0.0"
    
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
    
    def format_match_result(self, result_data):
        winner = result_data.get('winner')
        score = result_data.get('score', '')
        return f"Winner: {winner} ({score})"

# Register plugin (auto-discovered, but can register manually)
plugin_registry.register(ValorantPlugin())
```

```python
# Use plugin (in tournament creation)
from apps.core.plugins.registry import plugin_registry

def create_tournament(name, game):
    # Get game plugin
    plugin = plugin_registry.get(game)
    
    if not plugin:
        raise ValueError(f"Game plugin not found: {game}")
    
    # Use plugin to get default config
    default_config = plugin.get_default_config()
    
    tournament = Tournament.objects.create(
        name=name,
        game=game,
        config=default_config
    )
    return tournament
```

### 5. Creating Internal APIs

```python
# Register API endpoint (in apps/tournaments/api.py)
from apps.core.api_gateway import api_gateway, APIRequest, APIResponse

def get_tournament_handler(request: APIRequest) -> APIResponse:
    """API endpoint to get tournament details"""
    tournament_id = request.data['tournament_id']
    
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        return APIResponse(
            success=True,
            data={
                'id': tournament.id,
                'name': tournament.name,
                'status': tournament.status,
                'game': tournament.game
            }
        )
    except Tournament.DoesNotExist:
        return APIResponse(
            success=False,
            error='Tournament not found',
            status_code=404
        )

# Register endpoint
api_gateway.register_endpoint('tournaments.get', get_tournament_handler, version='v1')
```

```python
# Call API endpoint (from another app)
from apps.core.api_gateway import api_gateway, APIRequest

def my_function():
    # Call internal API
    response = api_gateway.call(APIRequest(
        endpoint='tournaments.get',
        method='get',
        data={'tournament_id': 123},
        requester='teams_app'
    ))
    
    if response.success:
        tournament_name = response.data['name']
        print(f"Tournament: {tournament_name}")
    else:
        print(f"Error: {response.error}")
```

## 📊 Monitoring

### Check Event Bus Stats
```python
from apps.core.events.bus import event_bus

stats = event_bus.get_statistics()
print(f"Event types: {stats['total_event_types']}")
print(f"Handlers: {stats['total_handlers']}")
print(f"History: {stats['event_history_size']}")
```

### Check Service Registry
```python
from apps.core.registry.service_registry import service_registry

stats = service_registry.get_statistics()
print(f"Services: {stats['total_services']}")
print(f"Enabled: {stats['enabled']}")

# List all services
services = service_registry.list_services()
for name, registration in services.items():
    print(f"  {name}: {registration.app_name} (v{registration.version})")
```

### Check Plugin Registry
```python
from apps.core.plugins.registry import plugin_registry

stats = plugin_registry.get_statistics()
print(f"Plugins: {stats['total_plugins']}")

# List all plugins
plugins = plugin_registry.list_plugins()
for name, plugin in plugins.items():
    print(f"  {name}: {plugin.display_name} (v{plugin.version})")
```

### View Event History
```python
from apps.core.events.bus import event_bus

# Get recent events
recent = event_bus.get_event_history(limit=10)
for event in recent:
    print(f"{event.timestamp}: {event.event_type} - {event.data}")
```

## 🧪 Testing

### Test with Events Disabled
```python
# tests/test_my_feature.py
from apps.core.events.bus import event_bus

def test_without_side_effects():
    """Test in isolation without event handlers"""
    # Disable handler for this test
    event_bus.disable_handler('tournament.created', 'send_notification')
    
    # Your test code here
    tournament = create_tournament("Test Tournament", "valorant")
    
    # Re-enable handler
    event_bus.enable_handler('tournament.created', 'send_notification')
```

### Test Event Handlers Directly
```python
def test_event_handler():
    """Test event handler in isolation"""
    from apps.notifications.handlers import send_tournament_notification
    from apps.core.events.events import TournamentCreatedEvent
    
    # Create event
    event = TournamentCreatedEvent(data={'tournament_id': 123})
    
    # Call handler directly
    send_tournament_notification(event)
    
    # Assert notification was sent
    # ... assertions here
```

## 🎯 Best Practices

### 1. Event Naming
Use dot notation: `{entity}.{action}`
- ✅ `tournament.created`
- ✅ `match.completed`
- ✅ `team.member_joined`
- ❌ `tournament_created`
- ❌ `TournamentCreated`

### 2. Service Naming
Use descriptive names: `{entity}_service`
- ✅ `tournament_service`
- ✅ `team_service`
- ✅ `notification_service`
- ❌ `TournamentSvc`
- ❌ `tourney_service`

### 3. When to Use Each System

**Event Bus:**
- One action → multiple reactions
- Loose coupling
- Don't need immediate response
- Example: Tournament created → send notifications, award coins, update rankings

**Service Registry:**
- Need to call methods on another app
- Want dependency injection for testing
- Service-oriented architecture
- Example: Team service needs tournament service

**API Gateway:**
- Need versioned APIs
- Request/response pattern
- Want to track API usage
- Example: Get tournament details from another app

**Plugin Framework:**
- Adding new game types
- Need extensibility without modifying core
- Clear contract/interface
- Example: Add new game without changing tournament system

## 🔗 Full Documentation

- **Comprehensive Guide:** `apps/core/README.md`
- **Migration Guide:** `MIGRATION_GUIDE_SIGNALS_TO_EVENTS.md`
- **Phase 1 Summary:** `PHASE_1_COMPLETE.md`
- **Architecture Plan:** `ENTERPRISE_ARCHITECTURE_PLAN.md`

## ✅ Quick Checklist

To adopt the new infrastructure:

1. [ ] Read `apps/core/README.md` for full documentation
2. [ ] Identify signal handlers to migrate
3. [ ] Convert one signal handler to event handler
4. [ ] Test the conversion
5. [ ] Gradually migrate remaining signal handlers
6. [ ] Create game plugins for Valorant and eFootball
7. [ ] Register services for your apps
8. [ ] Create internal API endpoints

## 🆘 Need Help?

**Event not firing?**
```python
# Check registered handlers
handlers = event_bus.get_handlers('your.event')
print(f"Handlers: {len(handlers)}")

# Check event history
events = event_bus.get_event_history(event_type='your.event', limit=5)
print(f"Recent events: {len(events)}")
```

**Service not found?**
```python
# List all services
services = service_registry.list_services()
print(f"Available services: {list(services.keys())}")
```

**Plugin not loading?**
```python
# List all plugins
plugins = plugin_registry.list_plugins()
print(f"Available plugins: {list(plugins.keys())}")

# Force rediscovery
plugin_registry._initialized = False
plugin_registry.discover_plugins()
```

## 🚀 You're Ready!

The core infrastructure is in place. Start using it in your code and enjoy:
- ✅ Loose coupling between apps
- ✅ Explicit, traceable event flow
- ✅ Easy testing and debugging
- ✅ Extensible architecture
- ✅ Industry-standard patterns

Happy coding! 🎉
