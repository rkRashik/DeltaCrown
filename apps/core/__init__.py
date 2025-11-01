"""
DeltaCrown Core Infrastructure

This app provides foundational infrastructure for the entire DeltaCrown platform,
enabling loosely coupled, event-driven architecture.

Components:
- Event Bus: Replace Django signals with explicit event system
- Service Registry: Discover and access app services
- Plugin Framework: Extensible game plugin system
- API Gateway: Internal API communication between apps
- Interfaces: Shared contracts and protocols
"""

default_app_config = 'apps.core.apps.CoreConfig'
