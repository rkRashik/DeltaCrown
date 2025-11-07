"""
Tournament Security Module

Provides role-based permissions, audit logging, and security utilities
for the tournament system.

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening

Components:
    - permissions.py: Role-based access control for REST and WebSocket
    - audit.py: Audit logging for sensitive actions
"""

from .permissions import (
    TournamentRole,
    IsSpectator,
    IsPlayer,
    IsOrganizer,
    IsAdmin,
    check_tournament_role,
    get_user_tournament_role,
    check_websocket_action_permission,
)
from .audit import audit_event, AuditAction

__all__ = [
    'TournamentRole',
    'IsSpectator',
    'IsPlayer',
    'IsOrganizer',
    'IsAdmin',
    'check_tournament_role',
    'get_user_tournament_role',
    'check_websocket_action_permission',
    'audit_event',
    'AuditAction',
]
