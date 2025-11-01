"""
Plugin Framework - Extensible Game System

Industry-standard plugin architecture for adding new games without modifying core code.

Benefits:
- Add new games without touching core tournament system
- Each game is self-contained
- Plugins can be enabled/disabled at runtime
- Clear plugin API contract
- Easy to test plugins in isolation
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, Type
from dataclasses import dataclass
from abc import ABC, abstractmethod
from django.apps import apps


logger = logging.getLogger(__name__)


class GamePlugin(ABC):
    """
    Base class for all game plugins.
    
    Each game (Valorant, eFootball, etc.) implements this interface.
    """
    
    # Plugin metadata
    name: str = ""
    display_name: str = ""
    version: str = "1.0.0"
    description: str = ""
    
    # Game-specific settings
    min_team_size: int = 1
    max_team_size: int = 5
    supports_solo: bool = False
    requires_roster: bool = True
    
    @abstractmethod
    def validate_team(self, team_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate team composition for this game.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def validate_match_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate match configuration.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this game"""
        pass
    
    @abstractmethod
    def format_match_result(self, result_data: Dict[str, Any]) -> str:
        """Format match result for display"""
        pass
    
    def get_rules_template(self) -> str:
        """Get default rules template for this game"""
        return ""
    
    def calculate_player_stats(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate player statistics from match data"""
        return {}
    
    def __str__(self):
        return f"{self.display_name} Plugin v{self.version}"


@dataclass
class PluginRegistration:
    """Plugin registration entry"""
    name: str
    plugin: GamePlugin
    enabled: bool = True


class PluginRegistry:
    """
    Central registry for game plugins.
    
    Usage:
        # Register a plugin
        plugin_registry.register(ValorantPlugin())
        
        # Get a plugin
        valorant = plugin_registry.get('valorant')
        is_valid, error = valorant.validate_team(team_data)
        
        # List all plugins
        plugins = plugin_registry.list_plugins()
    """
    
    def __init__(self):
        self._plugins: Dict[str, PluginRegistration] = {}
        self._initialized = False
    
    def discover_plugins(self):
        """
        Auto-discover plugins from installed Django apps.
        
        Looks for 'plugin.py' in game_* apps and registers them automatically.
        """
        if self._initialized:
            return
        
        logger.info("🔍 Discovering game plugins...")
        
        # Look for game_* apps
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('apps.game_'):
                try:
                    # Try to import plugin module
                    plugin_module = __import__(
                        f'{app_config.name}.plugin',
                        fromlist=['plugin']
                    )
                    
                    # Look for GamePlugin subclass
                    for attr_name in dir(plugin_module):
                        attr = getattr(plugin_module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, GamePlugin) and 
                            attr is not GamePlugin):
                            
                            # Instantiate and register
                            plugin_instance = attr()
                            self.register(plugin_instance)
                            logger.info(f"✅ Discovered plugin: {plugin_instance.name}")
                
                except ImportError:
                    logger.debug(f"No plugin found in {app_config.name}")
                except Exception as e:
                    logger.error(f"❌ Error loading plugin from {app_config.name}: {e}")
        
        self._initialized = True
        logger.info(f"🎮 Plugin discovery complete: {len(self._plugins)} plugins loaded")
    
    def register(self, plugin: GamePlugin):
        """Register a game plugin"""
        if not plugin.name:
            raise ValueError("Plugin must have a name")
        
        if plugin.name in self._plugins:
            logger.warning(f"⚠️ Plugin already registered: {plugin.name}, replacing...")
        
        registration = PluginRegistration(
            name=plugin.name,
            plugin=plugin
        )
        
        self._plugins[plugin.name] = registration
        logger.info(f"📝 Registered plugin: {plugin.display_name} ({plugin.name})")
    
    def unregister(self, name: str):
        """Unregister a plugin"""
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"❌ Unregistered plugin: {name}")
    
    def get(self, name: str) -> Optional[GamePlugin]:
        """
        Get a plugin by name.
        
        Returns:
            Plugin instance or None if not found/disabled
        """
        registration = self._plugins.get(name)
        
        if not registration:
            logger.warning(f"⚠️ Plugin not found: {name}")
            return None
        
        if not registration.enabled:
            logger.warning(f"⚠️ Plugin disabled: {name}")
            return None
        
        return registration.plugin
    
    def enable_plugin(self, name: str):
        """Enable a plugin"""
        if name in self._plugins:
            self._plugins[name].enabled = True
            logger.info(f"✅ Enabled plugin: {name}")
    
    def disable_plugin(self, name: str):
        """Disable a plugin"""
        if name in self._plugins:
            self._plugins[name].enabled = False
            logger.info(f"⏸️ Disabled plugin: {name}")
    
    def list_plugins(self, enabled_only: bool = False) -> Dict[str, GamePlugin]:
        """
        List all registered plugins.
        
        Args:
            enabled_only: Only return enabled plugins
        """
        plugins = {}
        for name, reg in self._plugins.items():
            if not enabled_only or reg.enabled:
                plugins[name] = reg.plugin
        return plugins
    
    def get_plugin_choices(self) -> List[tuple[str, str]]:
        """Get plugin choices for Django model field"""
        return [
            (name, plugin.display_name)
            for name, plugin in self.list_plugins(enabled_only=True).items()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        enabled = sum(1 for reg in self._plugins.values() if reg.enabled)
        disabled = len(self._plugins) - enabled
        
        return {
            'total_plugins': len(self._plugins),
            'enabled': enabled,
            'disabled': disabled,
            'plugin_names': list(self._plugins.keys()),
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (
            f"PluginRegistry(plugins={stats['total_plugins']}, "
            f"enabled={stats['enabled']})"
        )


# Global plugin registry instance
plugin_registry = PluginRegistry()
