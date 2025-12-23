"""
Stats Update Service

Updates UserProfileStats from UserActivity events.

Design:
- Stats are DERIVED from events (never manually updated)
- Recomputation is idempotent (safe to run multiple times)
- Uses select_for_update() for concurrency safety
- Syncs profile cache fields after stats update

Usage:
    from apps.user_profile.services.stats_service import StatsUpdateService
    
    # Recompute stats for single user
    stats = StatsUpdateService.update_stats_for_user(user_id=123)
    
    # Recompute stats for multiple users (batch)
    StatsUpdateService.update_stats_for_users([123, 124, 125])
    
    # Update profile cache after stats change
    StatsUpdateService.sync_profile_cache(user_id=123)
"""

from django.db import transaction
from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.models import UserProfile
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class StatsUpdateService:
    """Service for updating UserProfileStats from events."""
    
    @classmethod
    def update_stats_for_user(cls, user_id: int) -> UserProfileStats:
        """
        Recompute stats for a single user from UserActivity events.
        
        This is the primary way to update stats - always derives from
        immutable event log to ensure accuracy.
        
        Args:
            user_id: User ID to update stats for
            
        Returns:
            UserProfileStats: Updated stats instance
            
        Raises:
            UserProfile.DoesNotExist: If profile doesn't exist
        """
        try:
            with transaction.atomic():
                # Recompute from events (ensures accuracy)
                stats = UserProfileStats.recompute_from_events(user_id)
                
                # Sync profile cache
                cls.sync_profile_cache(user_id)
                
                logger.info(f"Updated stats for user {user_id}")
                return stats
        except UserProfile.DoesNotExist:
            logger.error(f"Cannot update stats: User {user_id} profile not found")
            raise
        except Exception as e:
            logger.error(f"Failed to update stats for user {user_id}: {e}", exc_info=True)
            raise
    
    @classmethod
    def update_stats_for_users(cls, user_ids: List[int]) -> dict:
        """
        Batch update stats for multiple users.
        
        Args:
            user_ids: List of user IDs
            
        Returns:
            dict: {'success': [...], 'failed': [...]}
        """
        success = []
        failed = []
        
        for user_id in user_ids:
            try:
                cls.update_stats_for_user(user_id)
                success.append(user_id)
            except Exception as e:
                logger.error(f"Failed to update stats for user {user_id}: {e}")
                failed.append(user_id)
        
        logger.info(
            f"Batch stats update: {len(success)} success, {len(failed)} failed"
        )
        return {'success': success, 'failed': failed}
    
    @classmethod
    def sync_profile_cache(cls, user_id: int) -> None:
        """
        Sync UserProfile cache fields from UserProfileStats.
        
        Profile fields synced:
        - tournaments_played
        - matches_played
        - (Add more as needed)
        
        Args:
            user_id: User ID to sync cache for
        """
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            
            # Get stats (create if missing)
            try:
                stats = profile.stats
            except UserProfileStats.DoesNotExist:
                stats = UserProfileStats.recompute_from_events(user_id)
            
            # Update profile cache fields (if they exist)
            updated = False
            
            if hasattr(profile, 'tournaments_played'):
                profile.tournaments_played = stats.tournaments_played
                updated = True
            
            if hasattr(profile, 'matches_played'):
                profile.matches_played = stats.matches_played
                updated = True
            
            if updated:
                profile.save(update_fields=['tournaments_played', 'matches_played'])
                logger.debug(f"Synced profile cache for user {user_id}")
        
        except UserProfile.DoesNotExist:
            logger.warning(f"Cannot sync cache: User {user_id} profile not found")
        except Exception as e:
            logger.error(f"Failed to sync profile cache for user {user_id}: {e}")
            # Don't raise - cache sync is non-critical
    
    @classmethod
    def get_stats(cls, user_id: int) -> Optional[UserProfileStats]:
        """
        Get stats for user, creating if missing.
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfileStats or None if profile doesn't exist
        """
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            
            # Get or create stats
            try:
                stats = profile.stats
            except UserProfileStats.DoesNotExist:
                stats = UserProfileStats.recompute_from_events(user_id)
            
            return stats
        except UserProfile.DoesNotExist:
            logger.warning(f"Cannot get stats: User {user_id} profile not found")
            return None
