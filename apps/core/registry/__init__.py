"""
Service Registry - App Discovery and Access

Industry-standard service registry for loosely coupled architecture.
Apps register their services, and other apps discover them through the registry.

Benefits:
- No direct imports between apps
- Easy to mock services for testing
- Services can be enabled/disabled at runtime
- Clear API contracts between apps
"""

import logging
from typing import Any, Callable, Dict, Optional, Protocol, Type
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class Service(Protocol):
    """Protocol defining what a service looks like"""
    name: str
    version: str
    
    def health_check(self) -> bool:
        """Check if service is healthy"""
        ...


@dataclass
class ServiceRegistration:
    """Service registration entry"""
    name: str
    service: Any
    version: str = "1.0.0"
    app_name: str = ""
    enabled: bool = True
    description: str = ""


class ServiceRegistry:
    """
    Central registry for application services.
    
    Usage:
        # Register a service
        service_registry.register(
            'tournament_service',
            TournamentService(),
            app_name='tournaments'
        )
        
        # Get a service
        tournament_service = service_registry.get('tournament_service')
        if tournament_service:
            tournaments = tournament_service.list_active_tournaments()
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceRegistration] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize service registry"""
        if self._initialized:
            return
        
        logger.info("🚀 Initializing Service Registry")
        self._initialized = True
    
    def register(
        self,
        name: str,
        service: Any,
        version: str = "1.0.0",
        app_name: str = "",
        description: str = ""
    ):
        """
        Register a service.
        
        Args:
            name: Unique service name
            service: Service instance
            version: Service version
            app_name: App that owns this service
            description: Human-readable description
        """
        if name in self._services:
            logger.warning(f"⚠️ Service already registered: {name}, replacing...")
        
        registration = ServiceRegistration(
            name=name,
            service=service,
            version=version,
            app_name=app_name,
            description=description
        )
        
        self._services[name] = registration
        logger.info(f"📝 Registered service: {name} v{version} ({app_name})")
    
    def unregister(self, name: str):
        """Unregister a service"""
        if name in self._services:
            del self._services[name]
            logger.info(f"❌ Unregistered service: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Returns:
            Service instance or None if not found/disabled
        """
        registration = self._services.get(name)
        
        if not registration:
            logger.warning(f"⚠️ Service not found: {name}")
            return None
        
        if not registration.enabled:
            logger.warning(f"⚠️ Service disabled: {name}")
            return None
        
        return registration.service
    
    def get_registration(self, name: str) -> Optional[ServiceRegistration]:
        """Get full service registration"""
        return self._services.get(name)
    
    def enable_service(self, name: str):
        """Enable a service"""
        if name in self._services:
            self._services[name].enabled = True
            logger.info(f"✅ Enabled service: {name}")
    
    def disable_service(self, name: str):
        """Disable a service"""
        if name in self._services:
            self._services[name].enabled = False
            logger.info(f"⏸️ Disabled service: {name}")
    
    def list_services(self, app_name: Optional[str] = None) -> Dict[str, ServiceRegistration]:
        """
        List all registered services.
        
        Args:
            app_name: Filter by app name
        """
        if app_name:
            return {
                name: reg for name, reg in self._services.items()
                if reg.app_name == app_name
            }
        return self._services.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        enabled = sum(1 for reg in self._services.values() if reg.enabled)
        disabled = len(self._services) - enabled
        
        return {
            'total_services': len(self._services),
            'enabled': enabled,
            'disabled': disabled,
            'apps': list(set(reg.app_name for reg in self._services.values())),
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (
            f"ServiceRegistry(services={stats['total_services']}, "
            f"enabled={stats['enabled']}, apps={len(stats['apps'])})"
        )


# Global service registry instance
service_registry = ServiceRegistry()
