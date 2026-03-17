"""
Core Infrastructure Tests

Test suite for Event Bus, Service Registry, and Plugin Framework.
"""

import pytest
from apps.core.events.bus import event_bus, Event, event_handler
from apps.core.events.events import TournamentCreatedEvent, RegistrationConfirmedEvent
from apps.core.registry.service_registry import service_registry
from apps.core.plugins.registry import plugin_registry, GamePlugin


# ============================================================================
# Event Bus Tests
# ============================================================================

class TestEventBus:
    """Test Event Bus functionality"""
    
    def setup_method(self):
        """Clear event bus before each test"""
        event_bus.clear_handlers()
        event_bus.initialize()
    
    def test_subscribe_and_publish(self):
        """Test basic event subscription and publishing"""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe('test.event', handler)
        
        event = Event(event_type='test.event', data={'test': 'data'})
        event_bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0].data['test'] == 'data'
    
    def test_multiple_handlers(self):
        """Test multiple handlers for same event"""
        calls = []
        
        def handler1(event: Event):
            calls.append('handler1')
        
        def handler2(event: Event):
            calls.append('handler2')
        
        event_bus.subscribe('test.event', handler1)
        event_bus.subscribe('test.event', handler2)
        
        event = Event(event_type='test.event')
        event_bus.publish(event)
        
        assert len(calls) == 2
        assert 'handler1' in calls
        assert 'handler2' in calls
    
    def test_handler_priority(self):
        """Test handlers execute in priority order"""
        calls = []
        
        def low_priority(event: Event):
            calls.append('low')
        
        def high_priority(event: Event):
            calls.append('high')
        
        event_bus.subscribe('test.event', low_priority, priority=100)
        event_bus.subscribe('test.event', high_priority, priority=10)
        
        event = Event(event_type='test.event')
        event_bus.publish(event)
        
        assert calls == ['high', 'low']
    
    def test_disable_handler(self):
        """Test disabling event handlers"""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe('test.event', handler, name='test_handler')
        event_bus.disable_handler('test.event', 'test_handler')
        
        event = Event(event_type='test.event')
        event_bus.publish(event)
        
        assert len(received_events) == 0
    
    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe('test.event', handler, name='test_handler')
        event_bus.unsubscribe('test.event', 'test_handler')
        
        event = Event(event_type='test.event')
        event_bus.publish(event)
        
        assert len(received_events) == 0
    
    def test_event_history(self):
        """Test event history tracking"""
        event_bus._enable_history = True
        
        event1 = Event(event_type='test.event1')
        event2 = Event(event_type='test.event2')
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        
        history = event_bus.get_event_history()
        assert len(history) >= 2
        assert any(e.event_type == 'test.event1' for e in history)
        assert any(e.event_type == 'test.event2' for e in history)
    
    def test_typed_events(self):
        """Test using typed event classes"""
        received_events = []
        
        def handler(event: TournamentCreatedEvent):
            received_events.append(event)
        
        event_bus.subscribe('tournament.created', handler)
        
        event = TournamentCreatedEvent(data={'tournament_id': 123})
        event_bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0].tournament_id == 123


# ============================================================================
# Service Registry Tests
# ============================================================================

class DummyService:
    """Dummy service for testing"""
    name = "dummy_service"
    version = "1.0.0"
    
    def health_check(self):
        return True
    
    def get_data(self):
        return "test_data"


class TestServiceRegistry:
    """Test Service Registry functionality"""
    
    def setup_method(self):
        """Clear registry before each test"""
        service_registry._services.clear()
        service_registry.initialize()
    
    def test_register_and_get_service(self):
        """Test registering and retrieving services"""
        service = DummyService()
        service_registry.register('dummy', service, app_name='test_app')
        
        retrieved = service_registry.get('dummy')
        assert retrieved is service
        assert retrieved.get_data() == 'test_data'
    
    def test_service_not_found(self):
        """Test getting non-existent service"""
        service = service_registry.get('nonexistent')
        assert service is None
    
    def test_disable_service(self):
        """Test disabling services"""
        service = DummyService()
        service_registry.register('dummy', service)
        service_registry.disable_service('dummy')
        
        retrieved = service_registry.get('dummy')
        assert retrieved is None
    
    def test_enable_service(self):
        """Test enabling disabled services"""
        service = DummyService()
        service_registry.register('dummy', service)
        service_registry.disable_service('dummy')
        service_registry.enable_service('dummy')
        
        retrieved = service_registry.get('dummy')
        assert retrieved is service
    
    def test_list_services(self):
        """Test listing all services"""
        service1 = DummyService()
        service2 = DummyService()
        
        service_registry.register('service1', service1, app_name='app1')
        service_registry.register('service2', service2, app_name='app2')
        
        all_services = service_registry.list_services()
        assert len(all_services) == 2
        
        app1_services = service_registry.list_services(app_name='app1')
        assert len(app1_services) == 1
    
    def test_statistics(self):
        """Test registry statistics"""
        service1 = DummyService()
        service2 = DummyService()
        
        service_registry.register('service1', service1, app_name='app1')
        service_registry.register('service2', service2, app_name='app2')
        service_registry.disable_service('service2')
        
        stats = service_registry.get_statistics()
        assert stats['total_services'] == 2
        assert stats['enabled'] == 1
        assert stats['disabled'] == 1


# ============================================================================
# Plugin Registry Tests
# ============================================================================

class DummyGamePlugin(GamePlugin):
    """Dummy game plugin for testing"""
    name = "test_game"
    display_name = "Test Game"
    version = "1.0.0"
    description = "Test game plugin"
    
    min_team_size = 1
    max_team_size = 5
    
    def validate_team(self, team_data):
        team_size = team_data.get('size', 0)
        if team_size < self.min_team_size or team_size > self.max_team_size:
            return False, f"Team size must be between {self.min_team_size} and {self.max_team_size}"
        return True, None
    
    def validate_match_config(self, config):
        if 'map' not in config:
            return False, "Map is required"
        return True, None
    
    def get_default_config(self):
        return {'map': 'default_map', 'rounds': 10}
    
    def format_match_result(self, result_data):
        return f"Winner: {result_data.get('winner')}"


class TestPluginRegistry:
    """Test Plugin Registry functionality"""
    
    def setup_method(self):
        """Clear registry before each test"""
        plugin_registry._plugins.clear()
        plugin_registry._initialized = False
    
    def test_register_and_get_plugin(self):
        """Test registering and retrieving plugins"""
        plugin = DummyGamePlugin()
        plugin_registry.register(plugin)
        
        retrieved = plugin_registry.get('test_game')
        assert retrieved is plugin
        assert retrieved.display_name == "Test Game"
    
    def test_validate_team(self):
        """Test plugin team validation"""
        plugin = DummyGamePlugin()
        plugin_registry.register(plugin)
        
        plugin = plugin_registry.get('test_game')
        
        # Valid team
        is_valid, error = plugin.validate_team({'size': 3})
        assert is_valid
        assert error is None
        
        # Invalid team
        is_valid, error = plugin.validate_team({'size': 10})
        assert not is_valid
        assert 'Team size' in error
    
    def test_disable_plugin(self):
        """Test disabling plugins"""
        plugin = DummyGamePlugin()
        plugin_registry.register(plugin)
        plugin_registry.disable_plugin('test_game')
        
        retrieved = plugin_registry.get('test_game')
        assert retrieved is None
    
    def test_list_plugins(self):
        """Test listing all plugins"""
        plugin1 = DummyGamePlugin()
        plugin1.name = 'game1'
        plugin2 = DummyGamePlugin()
        plugin2.name = 'game2'
        
        plugin_registry.register(plugin1)
        plugin_registry.register(plugin2)
        
        all_plugins = plugin_registry.list_plugins()
        assert len(all_plugins) == 2
        
        plugin_registry.disable_plugin('game2')
        enabled_plugins = plugin_registry.list_plugins(enabled_only=True)
        assert len(enabled_plugins) == 1
    
    def test_get_plugin_choices(self):
        """Test getting Django model field choices"""
        plugin1 = DummyGamePlugin()
        plugin1.name = 'game1'
        plugin1.display_name = 'Game One'
        
        plugin_registry.register(plugin1)
        
        choices = plugin_registry.get_plugin_choices()
        assert len(choices) == 1
        assert choices[0] == ('game1', 'Game One')
