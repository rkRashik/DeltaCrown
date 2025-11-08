# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-structure

"""
Tournament API Package

REST API for tournament management, registration, and real-time updates.

Modules:
- serializers: DRF serializers for API request/response
- views: DRF viewsets for API endpoints  
- permissions: Custom permission classes
- urls: API URL routing
"""

from apps.tournaments.api.views import RegistrationViewSet
from apps.tournaments.api.bracket_views import BracketViewSet
from apps.tournaments.api.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationCancelSerializer,
    BracketGenerationSerializer,
    BracketSerializer,
    BracketDetailSerializer
)
from apps.tournaments.api.permissions import (
    IsOrganizerOrReadOnly,
    IsOwnerOrOrganizer,
    IsPlayerOrSpectator,
    IsOrganizerOrAdmin
)

__all__ = [
    # ViewSets
    'RegistrationViewSet',
    'BracketViewSet',
    
    # Serializers
    'RegistrationSerializer',
    'RegistrationDetailSerializer',
    'RegistrationCancelSerializer',
    'BracketGenerationSerializer',
    'BracketSerializer',
    'BracketDetailSerializer',
    
    # Permissions
    'IsOrganizerOrReadOnly',
    'IsOwnerOrOrganizer',
    'IsPlayerOrSpectator',
    'IsOrganizerOrAdmin',
]
