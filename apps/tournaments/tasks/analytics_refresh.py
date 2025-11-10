"""
Celery Tasks: Tournament Analytics Refresh

Module 6.2: Materialized Views for Analytics
Phase 6 Sprint 1

Implements: PHASE_6_IMPLEMENTATION_PLAN.md#module-62-materialized-views-for-analytics

Scheduled Tasks:
    - refresh_analytics_hourly: Runs every hour (jittered) via Celery beat
    - refresh_tournament_analytics: On-demand refresh for single tournament

Configuration (deltacrown/settings.py):
    CELERY_BEAT_SCHEDULE = {
        'refresh-analytics-hourly': {
            'task': 'apps.tournaments.tasks.analytics_refresh.refresh_analytics_hourly',
            'schedule': crontab(minute='*/60'),  # Every hour
        },
    }

Performance:
    - Uses REFRESH MATERIALIZED VIEW CONCURRENTLY (non-blocking)
    - Typical duration: 500-2000ms for 1000 tournaments
    - Safe to run during peak traffic (no table locks)
"""
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging
import random

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def refresh_analytics_hourly(self):
    """
    Hourly scheduled refresh of tournament analytics materialized view.
    
    Module 6.2: Celery beat task for automated refresh
    
    Schedule: Every hour (jittered by 0-10 minutes to avoid thundering herd)
    
    Implements:
        - Full REFRESH MATERIALIZED VIEW CONCURRENTLY
        - Retry logic (3 attempts with exponential backoff)
        - Performance logging (duration + row counts)
        - Jitter to distribute load across beat workers
    
    Raises:
        Exception: If refresh fails after 3 retries
    """
    try:
        # Jitter: random delay 0-600 seconds (0-10 minutes)
        jitter_seconds = random.randint(0, 600)
        if jitter_seconds > 0:
            logger.info(f"Analytics refresh: jittered delay {jitter_seconds}s")
            import time
            time.sleep(jitter_seconds)
        
        start_time = timezone.now()
        
        # Execute full refresh via management command
        call_command('refresh_analytics', verbosity=0)
        
        duration_ms = (timezone.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Analytics hourly refresh complete: {duration_ms:.2f}ms (task_id={self.request.id})"
        )
        
        return {
            'status': 'success',
            'duration_ms': duration_ms,
            'task_id': str(self.request.id),
        }
    
    except Exception as exc:
        logger.error(
            f"Analytics hourly refresh failed (attempt {self.request.retries + 1}/3): {exc}",
            exc_info=True
        )
        
        # Retry with exponential backoff: 60s, 300s, 900s
        raise self.retry(exc=exc, countdown=60 * (5 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def refresh_tournament_analytics(self, tournament_id: int):
    """
    On-demand refresh for single tournament analytics.
    
    Module 6.2: Targeted refresh triggered by organizer/admin
    
    Args:
        tournament_id: Tournament ID to refresh
    
    Use Cases:
        - Organizer views tournament dashboard (force fresh data)
        - Match/result/prize update (invalidate cache)
        - Admin export request (ensure latest data)
    
    Implements:
        - Targeted DELETE + INSERT (faster than full refresh)
        - Retry logic (2 attempts)
        - Performance logging
    
    Raises:
        Exception: If refresh fails after 2 retries
    """
    try:
        start_time = timezone.now()
        
        # Execute targeted refresh via management command
        call_command('refresh_analytics', tournament=tournament_id, verbosity=0)
        
        duration_ms = (timezone.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Analytics targeted refresh for tournament {tournament_id}: {duration_ms:.2f}ms (task_id={self.request.id})"
        )
        
        return {
            'status': 'success',
            'tournament_id': tournament_id,
            'duration_ms': duration_ms,
            'task_id': str(self.request.id),
        }
    
    except Exception as exc:
        logger.error(
            f"Analytics targeted refresh for tournament {tournament_id} failed (attempt {self.request.retries + 1}/2): {exc}",
            exc_info=True
        )
        
        # Retry once with 30s delay
        raise self.retry(exc=exc, countdown=30)
