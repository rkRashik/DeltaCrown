"""
Celery configuration for DeltaCrown
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

app = Celery('deltacrown')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Daily ranking recalculation at 2 AM
    'recompute-rankings-daily': {
        'task': 'apps.teams.tasks.recompute_team_rankings',
        'schedule': crontab(hour=2, minute=0),
    },
    # Daily digest emails at 8 AM
    'send-digest-emails-daily': {
        'task': 'apps.notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    # Clean expired invites every 6 hours
    'clean-expired-invites': {
        'task': 'apps.teams.tasks.clean_expired_invites',
        'schedule': crontab(hour='*/6', minute=0),
    },
    # Expire sponsors daily at 3 AM
    'expire-sponsors-daily': {
        'task': 'apps.teams.tasks.expire_sponsors_task',
        'schedule': crontab(hour=3, minute=0),
    },
    # Process scheduled promotions hourly
    'process-scheduled-promotions': {
        'task': 'apps.teams.tasks.process_scheduled_promotions_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Tournament wrap-up check every hour
    'check-tournament-wrapup': {
        'task': 'apps.tournaments.tasks.check_tournament_wrapup',
        'schedule': crontab(minute=15),  # Every hour at :15
    },
    
    # ========================================================================
    # vNext Team & Organization Ranking Tasks (Phase 4 - P4-T2)
    # ========================================================================
    
    # Recalculate vNext team rankings nightly at 3:00 AM
    'vnext-recalculate-team-rankings': {
        'task': 'apps.organizations.tasks.recalculate_team_rankings',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'expires': 3600,  # Task expires after 1 hour
        }
    },
    
    # Apply inactivity decay nightly at 3:30 AM
    'vnext-apply-inactivity-decay': {
        'task': 'apps.organizations.tasks.apply_inactivity_decay',
        'schedule': crontab(hour=3, minute=30),
        'kwargs': {
            'cutoff_days': 7  # Default: 7 days inactivity
        },
        'options': {
            'expires': 3600,
        }
    },
    
    # Recalculate organization rankings nightly at 4:00 AM
    'vnext-recalculate-org-rankings': {
        'task': 'apps.organizations.tasks.recalculate_organization_rankings',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'expires': 3600,
        }
    },
}

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working"""
    print(f'Request: {self.request!r}')
