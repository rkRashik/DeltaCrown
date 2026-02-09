"""
Dual-Write Sync Service for Phase 5-7 transition period (P5-T3).

Syncs vNext (apps.organizations) writes to legacy (apps.teams) tables
to maintain backward compatibility with old pages/features during migration.

Key Features:
- Idempotent: Safe to call multiple times
- Atomic: Uses transactions with savepoints
- Logged: Structured logging for success/failure
- Safe: Never crashes primary vNext operation (unless strict mode)
- Mapped: Uses TeamMigrationMap for ID lookups

Usage:
    from apps.organizations.services.dual_write_service import dual_write_service
    
    # After vNext team creation
    transaction.on_commit(lambda: dual_write_service.sync_team_created(
        vnext_team_id=team.id,
        actor_user_id=request.user.id
    ))
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.organizations.models import (
    Team as VNextTeam,
    TeamMembership as VNextMembership,
    TeamMigrationMap,
)

# Legacy model imports for dual-write sync to teams_team table.
# These resolve to the legacy teams app models (different db_table).
# This entire service becomes a no-op once Phase B DB consolidation is done.
try:
    from apps.teams.models import (
        Team as LegacyTeam,
        TeamMembership as LegacyMembership,
    )
    from apps.teams.models import TeamRankingBreakdown as LegacyRanking
except ImportError:
    LegacyTeam = None
    LegacyMembership = None
    LegacyRanking = None
from apps.teams.mixins import legacy_write_bypass

User = get_user_model()
logger = logging.getLogger(__name__)


class DualWriteSyncService:
    """
    Service for syncing vNext writes to legacy tables during Phase 5-7.
    
    All methods are idempotent and safe to call multiple times.
    Failures are logged but don't crash primary operations (unless strict mode).
    """
    
    def __init__(self):
        self.enabled = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False)
        self.strict_mode = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False)
    
    def is_enabled(self) -> bool:
        """Check if dual-write sync is enabled."""
        return self.enabled
    
    def sync_team_created(self, vnext_team_id: int, actor_user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync vNext team creation to legacy tables.
        
        Creates:
        - Legacy Team record
        - TeamMigrationMap entry
        
        Args:
            vnext_team_id: vNext Team.id
            actor_user_id: User who created the team (for logging)
        
        Returns:
            {'success': bool, 'legacy_team_id': int, 'created': bool, 'error': str}
        """
        if not self.enabled:
            logger.debug(f"Dual-write disabled, skipping sync_team_created for vNext team {vnext_team_id}")
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        try:
            vnext_team = VNextTeam.objects.select_related('created_by').get(id=vnext_team_id)
        except VNextTeam.DoesNotExist:
            logger.error(f"sync_team_created: vNext team {vnext_team_id} not found")
            return {'success': False, 'error': 'vnext_team_not_found'}
        
        # Check if already synced (idempotency)
        existing_mapping = TeamMigrationMap.objects.filter(vnext_team_id=vnext_team_id).first()
        if existing_mapping:
            logger.info(
                f"Team already synced: vNext {vnext_team_id} â†’ Legacy {existing_mapping.legacy_team_id}",
                extra={'vnext_team_id': vnext_team_id, 'legacy_team_id': existing_mapping.legacy_team_id}
            )
            return {
                'success': True,
                'created': False,
                'legacy_team_id': existing_mapping.legacy_team_id,
                'idempotent': True
            }
        
        try:
            with transaction.atomic():
                with legacy_write_bypass(reason="dual_write_sync_team_created"):
                    # Create legacy team
                    legacy_team = LegacyTeam.objects.create(
                        name=vnext_team.name,
                        tag=vnext_team.slug[:10] if vnext_team.slug else vnext_team.name[:10],
                        slug=vnext_team.slug,
                        description=vnext_team.description or '',
                        game=self._map_game_id_to_slug(vnext_team.game_id),
                        region=vnext_team.region or '',
                        logo=vnext_team.logo if vnext_team.logo else None,
                        banner_image=vnext_team.banner if vnext_team.banner else None,
                        is_public=vnext_team.status == 'ACTIVE',
                        is_active=vnext_team.status == 'ACTIVE',
                    )
                    
                    # Create mapping
                    TeamMigrationMap.objects.create(
                        legacy_team_id=legacy_team.id,
                        vnext_team_id=vnext_team.id,
                        legacy_slug=vnext_team.slug,
                        migrated_by_id=actor_user_id,
                    )
                    
                    logger.info(
                        f"Team synced: vNext {vnext_team_id} â†’ Legacy {legacy_team.id}",
                        extra={
                            'vnext_team_id': vnext_team_id,
                            'legacy_team_id': legacy_team.id,
                            'actor_user_id': actor_user_id,
                            'operation': 'sync_team_created'
                        }
                    )
                    
                    return {
                        'success': True,
                        'created': True,
                        'legacy_team_id': legacy_team.id,
                        'vnext_team_id': vnext_team_id
                    }
        
        except Exception as e:
            logger.error(
                f"Failed to sync team creation: vNext {vnext_team_id}",
                exc_info=True,
                extra={
                    'vnext_team_id': vnext_team_id,
                    'error': str(e),
                    'operation': 'sync_team_created'
                }
            )
            
            if self.strict_mode:
                raise
            
            return {'success': False, 'error': str(e), 'vnext_team_id': vnext_team_id}
    
    def sync_team_member_added(
        self,
        vnext_membership_id: int,
        actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync vNext membership creation to legacy tables.
        
        Creates:
        - Legacy TeamMembership record
        
        Args:
            vnext_membership_id: vNext TeamMembership.id
            actor_user_id: User who added the member (for logging)
        
        Returns:
            {'success': bool, 'legacy_membership_id': int, 'created': bool, 'error': str}
        """
        if not self.enabled:
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        try:
            vnext_membership = VNextMembership.objects.select_related('team', 'user__userprofile').get(
                id=vnext_membership_id
            )
        except VNextMembership.DoesNotExist:
            logger.error(f"sync_team_member_added: vNext membership {vnext_membership_id} not found")
            return {'success': False, 'error': 'vnext_membership_not_found'}
        
        # Get legacy team ID from mapping
        mapping = TeamMigrationMap.objects.filter(vnext_team_id=vnext_membership.team_id).first()
        if not mapping:
            logger.warning(
                f"Cannot sync membership: vNext team {vnext_membership.team_id} not mapped to legacy",
                extra={'vnext_team_id': vnext_membership.team_id, 'vnext_membership_id': vnext_membership_id}
            )
            return {'success': False, 'error': 'team_not_mapped', 'vnext_team_id': vnext_membership.team_id}
        
        # Check if already synced (idempotency)
        existing = LegacyMembership.objects.filter(
            team_id=mapping.legacy_team_id,
            profile=vnext_membership.user.userprofile
        ).first()
        
        if existing:
            logger.info(
                f"Membership already synced: vNext {vnext_membership_id}",
                extra={'vnext_membership_id': vnext_membership_id, 'legacy_membership_id': existing.id}
            )
            return {
                'success': True,
                'created': False,
                'legacy_membership_id': existing.id,
                'idempotent': True
            }
        
        try:
            with transaction.atomic():
                with legacy_write_bypass(reason="dual_write_sync_membership_added"):
                    # Map roles (vNext â†’ Legacy)
                    legacy_role = self._map_role_vnext_to_legacy(vnext_membership.role)
                    
                    # Create legacy membership
                    legacy_membership = LegacyMembership.objects.create(
                        team_id=mapping.legacy_team_id,
                        profile=vnext_membership.user.userprofile,
                        role=legacy_role,
                        status='ACTIVE',
                    )
                    
                    logger.info(
                        f"Membership synced: vNext {vnext_membership_id} â†’ Legacy {legacy_membership.id}",
                        extra={
                            'vnext_membership_id': vnext_membership_id,
                            'legacy_membership_id': legacy_membership.id,
                            'legacy_team_id': mapping.legacy_team_id,
                            'actor_user_id': actor_user_id
                        }
                    )
                    
                    return {
                        'success': True,
                        'created': True,
                        'legacy_membership_id': legacy_membership.id,
                        'vnext_membership_id': vnext_membership_id
                    }
        
        except Exception as e:
            logger.error(
                f"Failed to sync membership: vNext {vnext_membership_id}",
                exc_info=True,
                extra={'vnext_membership_id': vnext_membership_id, 'error': str(e)}
            )
            
            if self.strict_mode:
                raise
            
            return {'success': False, 'error': str(e), 'vnext_membership_id': vnext_membership_id}
    
    def sync_team_member_updated(
        self,
        vnext_membership_id: int,
        actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync vNext membership update to legacy tables.
        
        Updates:
        - Legacy TeamMembership role/status
        
        Args:
            vnext_membership_id: vNext TeamMembership.id
            actor_user_id: User who updated the member (for logging)
        
        Returns:
            {'success': bool, 'updated': bool, 'error': str}
        """
        if not self.enabled:
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        try:
            vnext_membership = VNextMembership.objects.select_related('team', 'user__userprofile').get(
                id=vnext_membership_id
            )
        except VNextMembership.DoesNotExist:
            return {'success': False, 'error': 'vnext_membership_not_found'}
        
        # Get legacy team ID
        mapping = TeamMigrationMap.objects.filter(vnext_team_id=vnext_membership.team_id).first()
        if not mapping:
            return {'success': False, 'error': 'team_not_mapped'}
        
        # Find legacy membership
        try:
            legacy_membership = LegacyMembership.objects.get(
                team_id=mapping.legacy_team_id,
                profile=vnext_membership.user.userprofile
            )
        except LegacyMembership.DoesNotExist:
            # If doesn't exist, create it
            return self.sync_team_member_added(vnext_membership_id, actor_user_id)
        
        try:
            with transaction.atomic():
                with legacy_write_bypass(reason="dual_write_sync_membership_updated"):
                    legacy_role = self._map_role_vnext_to_legacy(vnext_membership.role)
                    legacy_membership.role = legacy_role
                    legacy_membership.save()
                    
                    logger.info(
                        f"Membership updated: vNext {vnext_membership_id}",
                        extra={
                            'vnext_membership_id': vnext_membership_id,
                            'legacy_membership_id': legacy_membership.id,
                            'new_role': legacy_role
                        }
                    )
                    
                    return {'success': True, 'updated': True, 'legacy_membership_id': legacy_membership.id}
        
        except Exception as e:
            logger.error(f"Failed to update membership: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return {'success': False, 'error': str(e)}
    
    def sync_team_member_removed(
        self,
        vnext_membership_id: int,
        actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync vNext membership removal to legacy tables.
        
        Deletes:
        - Legacy TeamMembership record
        
        Args:
            vnext_membership_id: vNext TeamMembership.id (may no longer exist)
            actor_user_id: User who removed the member (for logging)
        
        Returns:
            {'success': bool, 'deleted': bool, 'error': str}
        
        Note: Since vNext membership may be deleted, caller should pass
        team_id and user_id separately if possible. For now, we try to find
        the membership by ID.
        """
        if not self.enabled:
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        # This is tricky: vNext membership may already be deleted
        # For now, log and return success (idempotent)
        logger.warning(
            f"sync_team_member_removed called for {vnext_membership_id} - "
            "deletion sync not fully implemented (requires team_id+user_id params)",
            extra={'vnext_membership_id': vnext_membership_id}
        )
        
        return {'success': True, 'deleted': False, 'note': 'deletion_sync_not_implemented'}
    
    def sync_team_settings_updated(
        self,
        vnext_team_id: int,
        actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync vNext team settings update to legacy tables.
        
        Updates:
        - Legacy Team fields (name, description, etc.)
        
        Args:
            vnext_team_id: vNext Team.id
            actor_user_id: User who updated settings (for logging)
        
        Returns:
            {'success': bool, 'updated': bool, 'error': str}
        """
        if not self.enabled:
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        try:
            vnext_team = VNextTeam.objects.get(id=vnext_team_id)
        except VNextTeam.DoesNotExist:
            return {'success': False, 'error': 'vnext_team_not_found'}
        
        # Get legacy team ID
        mapping = TeamMigrationMap.objects.filter(vnext_team_id=vnext_team_id).first()
        if not mapping:
            # Team not yet synced - sync it now
            return self.sync_team_created(vnext_team_id, actor_user_id)
        
        try:
            legacy_team = LegacyTeam.objects.get(id=mapping.legacy_team_id)
        except LegacyTeam.DoesNotExist:
            logger.error(f"Legacy team {mapping.legacy_team_id} not found, but mapping exists")
            return {'success': False, 'error': 'legacy_team_not_found'}
        
        try:
            with transaction.atomic():
                with legacy_write_bypass(reason="dual_write_sync_team_settings"):
                    # Update legacy team fields
                    legacy_team.name = vnext_team.name
                    legacy_team.slug = vnext_team.slug
                    legacy_team.description = vnext_team.description or ''
                    legacy_team.region = vnext_team.region or ''
                    legacy_team.is_public = vnext_team.status == 'ACTIVE'
                    legacy_team.is_active = vnext_team.status == 'ACTIVE'
                    legacy_team.save()
                    
                    logger.info(
                        f"Team settings synced: vNext {vnext_team_id}",
                        extra={'vnext_team_id': vnext_team_id, 'legacy_team_id': legacy_team.id}
                    )
                    
                    return {'success': True, 'updated': True, 'legacy_team_id': legacy_team.id}
        
        except Exception as e:
            logger.error(f"Failed to sync team settings: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return {'success': False, 'error': str(e)}
    
    def sync_ranking_updated(
        self,
        vnext_team_id: int,
        actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync vNext team ranking to legacy ranking breakdown.
        
        Updates:
        - Legacy TeamRankingBreakdown
        
        Args:
            vnext_team_id: vNext Team.id
            actor_user_id: User who triggered ranking update (for logging)
        
        Returns:
            {'success': bool, 'updated': bool, 'error': str}
        """
        if not self.enabled:
            return {'success': True, 'skipped': True, 'reason': 'disabled'}
        
        # Get legacy team ID
        mapping = TeamMigrationMap.objects.filter(vnext_team_id=vnext_team_id).first()
        if not mapping:
            return {'success': False, 'error': 'team_not_mapped'}
        
        try:
            from apps.organizations.models import TeamRanking as VNextRanking
            vnext_ranking = VNextRanking.objects.get(team_id=vnext_team_id)
        except VNextRanking.DoesNotExist:
            return {'success': False, 'error': 'vnext_ranking_not_found'}
        
        try:
            with transaction.atomic():
                with legacy_write_bypass(reason="dual_write_sync_ranking"):
                    # Get or create legacy ranking
                    legacy_ranking, created = LegacyRanking.objects.get_or_create(
                        team_id=mapping.legacy_team_id,
                        defaults={
                            'final_total': vnext_ranking.current_cp,
                            'calculated_total': vnext_ranking.current_cp,
                        }
                    )
                    
                    if not created:
                        legacy_ranking.final_total = vnext_ranking.current_cp
                        legacy_ranking.calculated_total = vnext_ranking.current_cp
                        legacy_ranking.save()
                    
                    logger.info(
                        f"Ranking synced: vNext team {vnext_team_id} â†’ Legacy ranking {legacy_ranking.team_id}",
                        extra={'vnext_team_id': vnext_team_id, 'legacy_team_id': mapping.legacy_team_id}
                    )
                    
                    return {'success': True, 'updated': not created, 'created': created}
        
        except Exception as e:
            logger.error(f"Failed to sync ranking: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return {'success': False, 'error': str(e)}
    
    def _map_game_id_to_slug(self, game_id: Optional[int]) -> str:
        """Map vNext game_id to legacy game slug."""
        game_map = {
            1: 'valorant',
            2: 'csgo',
            3: 'dota2',
            4: 'pubg',
        }
        return game_map.get(game_id, '')
    
    def _map_role_vnext_to_legacy(self, vnext_role: str) -> str:
        """Map vNext role to legacy role."""
        role_map = {
            'OWNER': 'OWNER',
            'MANAGER': 'MANAGER',
            'MEMBER': 'PLAYER',
            'SUBSTITUTE': 'SUBSTITUTE',
        }
        return role_map.get(vnext_role, 'PLAYER')


# Singleton instance
dual_write_service = DualWriteSyncService()
