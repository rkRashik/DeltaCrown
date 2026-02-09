# apps/organizations/tasks/legacy_bridge.py
"""
Celery task stubs that alias legacy ``apps.teams.tasks.*`` names.

These tasks are registered under the *legacy* names so that existing
Celery Beat schedules and any queued messages continue to work.
Each stub delegates to the real implementation in ``rankings.py``.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='teams.recompute_team_rankings',
    max_retries=3,
    default_retry_delay=300,
)
def recompute_team_rankings(self, tournament_id=None):
    """Legacy alias → recalculate_team_rankings."""
    from apps.organizations.tasks.rankings import recalculate_team_rankings
    return recalculate_team_rankings.apply(kwargs={}).get(timeout=600)


@shared_task(
    bind=True,
    name='teams.clean_expired_invites',
    max_retries=3,
    default_retry_delay=60,
)
def clean_expired_invites(self):
    """Clean expired team invites."""
    try:
        from apps.organizations.models import TeamInvite
        expired = TeamInvite.objects.filter(
            status='PENDING',
            expires_at__lt=timezone.now(),
        )
        count = expired.update(status='EXPIRED')
        logger.info("clean_expired_invites: expired %d invites", count)
        return {'success': True, 'expired_count': count}
    except Exception as exc:
        logger.error("clean_expired_invites failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name='teams.expire_sponsors_task',
    max_retries=3,
    default_retry_delay=60,
)
def expire_sponsors_task(self):
    """Expire sponsors — stub (no-op)."""
    return {'success': True, 'expired_count': 0}


@shared_task(
    bind=True,
    name='teams.process_scheduled_promotions_task',
    max_retries=3,
    default_retry_delay=60,
)
def process_scheduled_promotions_task(self):
    """Process scheduled promotions — stub (no-op)."""
    return {'success': True, 'processed_count': 0}
