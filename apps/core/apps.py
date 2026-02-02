"""
Core App Configuration with Database Migration Guards
"""
import logging
import os
import sys
from django.apps import AppConfig
from django.conf import settings
from django.db import ProgrammingError, OperationalError

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core Infrastructure'
    
    def ready(self):
        """Initialize core infrastructure when Django starts"""
        # Skip initialization during migrations
        if 'migrate' in sys.argv:
            logger.info("⏭️  Skipping core initialization during migrations")
            return
        
        # Skip initialization during makemigrations
        if 'makemigrations' in sys.argv:
            logger.info("⏭️  Skipping core initialization during makemigrations")
            return
        
        # Import here to avoid AppRegistryNotReady
        from .events.bus import event_bus
        from .registry import service_registry
        from .plugins.registry import plugin_registry
        
        # Initialize systems
        event_bus.initialize()
        service_registry.initialize()
        plugin_registry.discover_plugins()
        
        # Register providers (Phase 3)
        # Guard: Skip provider registration if DB tables don't exist yet (e.g., during test setup)
        # This is safe because providers use lazy loading via @property decorators
        try:
            from .providers import tournament_provider_v1, game_config_provider_v1
            
            service_registry.register(
                'tournament_provider',
                tournament_provider_v1,
                version='1.0',
                description='Tournament operations provider (current system)'
            )
            
            service_registry.register(
                'game_config_provider',
                game_config_provider_v1,
                version='1.0',
                description='Game configuration provider (current system)'
            )
            
            logger.info("✅ Registered tournament and game config providers")
        except (ProgrammingError, OperationalError) as e:
            # DB tables don't exist yet (e.g., during test database setup)
            # This is expected and safe - providers will work once tables are created
            logger.debug(f"Skipping provider registration - DB tables not ready: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to register providers: {e}", exc_info=True)
        
        logger.info("DeltaCrown Core Infrastructure initialized")
