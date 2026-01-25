"""
Legacy write enforcement mixin for Phase 5 migration.

Prevents writes to legacy teams models during migration window
while keeping reads fully functional.
"""

import logging
from contextvars import ContextVar
from contextlib import contextmanager
from django.conf import settings
from django.db import models

from apps.organizations.services.exceptions import LegacyWriteBlockedException


logger = logging.getLogger(__name__)


# ContextVar to track bypass scope (thread-safe for async)
_legacy_write_bypass_active: ContextVar[bool] = ContextVar('legacy_write_bypass_active', default=False)
_legacy_write_bypass_reason: ContextVar[str] = ContextVar('legacy_write_bypass_reason', default='')


@contextmanager
def legacy_write_bypass(reason: str = "internal_operation"):
    """
    Context manager to temporarily allow legacy writes (P5-T3 dual-write).
    
    Usage:
        with legacy_write_bypass(reason="dual_write_sync"):
            legacy_team.save()  # Allowed within context
    
    Args:
        reason: Why bypass is needed (for audit logging)
    
    Scope:
        - Automatically resets even if exceptions occur
        - Thread-safe (uses ContextVar)
        - Logged for audit trail
    
    Security:
        - Internal use only (apps.organizations.services.dual_write_service)
        - Never expose to end users or external APIs
        - Narrow scope, auto-resets
    """
    token_active = _legacy_write_bypass_active.set(True)
    token_reason = _legacy_write_bypass_reason.set(reason)
    
    logger.info(
        f"Legacy write bypass ACTIVATED: {reason}",
        extra={'bypass_reason': reason, 'bypass_active': True}
    )
    
    try:
        yield
    finally:
        _legacy_write_bypass_active.reset(token_active)
        _legacy_write_bypass_reason.reset(token_reason)
        
        logger.info(
            f"Legacy write bypass DEACTIVATED: {reason}",
            extra={'bypass_reason': reason, 'bypass_active': False}
        )


class LegacyWriteEnforcementMixin:
    """
    Mixin to block write operations on legacy team models during migration.
    
    Usage:
        class Team(LegacyWriteEnforcementMixin, models.Model):
            ...
    
    Settings:
        TEAM_LEGACY_WRITE_BLOCKED (bool): If True, blocks all writes. Default: True
        TEAM_LEGACY_WRITE_BYPASS_ENABLED (bool): If True, allows writes. Default: False
        TEAM_LEGACY_WRITE_BYPASS_TOKEN (str): Optional token for controlled bypass
    
    Behavior:
        - If TEAM_LEGACY_WRITE_BLOCKED=True and BYPASS_ENABLED=False: Raises LegacyWriteBlockedException
        - If TEAM_LEGACY_WRITE_BLOCKED=False: No enforcement (normal operation)
        - If TEAM_LEGACY_WRITE_BYPASS_ENABLED=True: Allows writes (emergency killswitch)
        - Logs all blocked write attempts with structured data
    
    Phase 5 Timeline:
        - Phase 5 start: BLOCKED=True, BYPASS=False (writes blocked)
        - Emergency: BYPASS=True (temporary re-enable)
        - Phase 8 completion: Remove mixin (legacy system archived)
    """
    
    def _check_legacy_write_allowed(self, operation: str) -> None:
        """
        Check if write operation is allowed on legacy model.
        
        Args:
            operation: Operation type (save, delete, bulk_update, etc.)
        
        Raises:
            LegacyWriteBlockedException: If write is blocked and bypass is not enabled
        """
        # Check if in bypass context (P5-T3 dual-write)
        if _legacy_write_bypass_active.get():
            bypass_reason = _legacy_write_bypass_reason.get()
            logger.info(
                f"Legacy write ALLOWED via context bypass: {operation} on {self.__class__.__name__}",
                extra={
                    'model': self.__class__.__name__,
                    'operation': operation,
                    'bypass_active': True,
                    'bypass_reason': bypass_reason,
                    'instance_id': getattr(self, 'id', None),
                }
            )
            return
        
        # Check if blocking is enabled
        blocked = getattr(settings, 'TEAM_LEGACY_WRITE_BLOCKED', True)
        
        if not blocked:
            # Blocking disabled - allow all writes
            return
        
        # Check bypass killswitch (emergency override)
        bypass_enabled = getattr(settings, 'TEAM_LEGACY_WRITE_BYPASS_ENABLED', False)
        
        if bypass_enabled:
            # Bypass enabled - allow write but log
            logger.warning(
                f"Legacy write ALLOWED via bypass: {operation} on {self.__class__.__name__}",
                extra={
                    'model': self.__class__.__name__,
                    'operation': operation,
                    'bypass_active': True,
                    'instance_id': getattr(self, 'id', None),
                }
            )
            return
        
        # Write is blocked - log and raise exception
        logger.error(
            f"Legacy write BLOCKED: {operation} on {self.__class__.__name__}",
            extra={
                'model': self.__class__.__name__,
                'operation': operation,
                'blocked': True,
                'instance_id': getattr(self, 'id', None),
                'table': self._meta.db_table if hasattr(self, '_meta') else None,
            }
        )
        
        raise LegacyWriteBlockedException(
            model=self.__class__.__name__,
            operation=operation,
            table=self._meta.db_table if hasattr(self, '_meta') else None,
        )
    
    def save(self, *args, **kwargs):
        """Override save to enforce write blocking."""
        self._check_legacy_write_allowed('save')
        return super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to enforce write blocking."""
        self._check_legacy_write_allowed('delete')
        return super().delete(*args, **kwargs)
    
    @classmethod
    def _check_bulk_write_allowed(cls, operation: str) -> None:
        """
        Check if bulk write operation is allowed.
        
        Args:
            operation: Bulk operation type (bulk_create, bulk_update, etc.)
        
        Raises:
            LegacyWriteBlockedException: If write is blocked and bypass is not enabled
        """
        # Check if in bypass context (P5-T3 dual-write)
        if _legacy_write_bypass_active.get():
            bypass_reason = _legacy_write_bypass_reason.get()
            logger.info(
                f"Legacy bulk write ALLOWED via context bypass: {operation} on {cls.__name__}",
                extra={
                    'model': cls.__name__,
                    'operation': operation,
                    'bypass_active': True,
                    'bypass_reason': bypass_reason,
                }
            )
            return
        
        blocked = getattr(settings, 'TEAM_LEGACY_WRITE_BLOCKED', True)
        
        if not blocked:
            return
        
        bypass_enabled = getattr(settings, 'TEAM_LEGACY_WRITE_BYPASS_ENABLED', False)
        
        if bypass_enabled:
            logger.warning(
                f"Legacy bulk write ALLOWED via bypass: {operation} on {cls.__name__}",
                extra={
                    'model': cls.__name__,
                    'operation': operation,
                    'bypass_active': True,
                }
            )
            return
        
        logger.error(
            f"Legacy bulk write BLOCKED: {operation} on {cls.__name__}",
            extra={
                'model': cls.__name__,
                'operation': operation,
                'blocked': True,
                'table': cls._meta.db_table if hasattr(cls, '_meta') else None,
            }
        )
        
        raise LegacyWriteBlockedException(
            model=cls.__name__,
            operation=operation,
            table=cls._meta.db_table if hasattr(cls, '_meta') else None,
        )


class LegacyQuerySetMixin:
    """
    QuerySet mixin to block bulk write operations on legacy models.
    
    Usage:
        class TeamQuerySet(LegacyQuerySetMixin, models.QuerySet):
            pass
        
        class Team(LegacyWriteEnforcementMixin, models.Model):
            objects = TeamQuerySet.as_manager()
    """
    
    def bulk_create(self, objs, *args, **kwargs):
        """Override bulk_create to enforce write blocking."""
        if objs and len(objs) > 0:
            model_class = objs[0].__class__
            if hasattr(model_class, '_check_bulk_write_allowed'):
                model_class._check_bulk_write_allowed('bulk_create')
        return super().bulk_create(objs, *args, **kwargs)
    
    def bulk_update(self, objs, fields, *args, **kwargs):
        """Override bulk_update to enforce write blocking."""
        if objs and len(objs) > 0:
            model_class = objs[0].__class__
            if hasattr(model_class, '_check_bulk_write_allowed'):
                model_class._check_bulk_write_allowed('bulk_update')
        return super().bulk_update(objs, fields, *args, **kwargs)
    
    def update(self, **kwargs):
        """Override update to enforce write blocking."""
        if hasattr(self.model, '_check_bulk_write_allowed'):
            self.model._check_bulk_write_allowed('queryset_update')
        return super().update(**kwargs)
    
    def delete(self):
        """Override delete to enforce write blocking."""
        if hasattr(self.model, '_check_bulk_write_allowed'):
            self.model._check_bulk_write_allowed('queryset_delete')
        return super().delete()
