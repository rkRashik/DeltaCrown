"""
Celery configuration for DeltaCrown

Memory-optimised for Render Starter (512 MB single-container).
Heavy / high-frequency tasks are gated behind ENABLE_CELERY_BEAT env-var
so staging or free-tier deploys can disable them entirely.
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

# ---------------------------------------------------------------------------
# Feature flag: set ENABLE_CELERY_BEAT=1 in Render env vars to activate the
# periodic schedule.  When disabled (default on free tier) the worker still
# processes tasks dispatched on-demand, but no cron-like jobs fire.
# ---------------------------------------------------------------------------
_beat_enabled = os.getenv('ENABLE_CELERY_BEAT', '0') == '1'

# ---------------------------------------------------------------------------
# Lightweight tasks — always scheduled (cheap, infrequent)
# ---------------------------------------------------------------------------
_base_schedule = {
    # Daily ranking recalculation at 2 AM
    'recompute-rankings-daily': {
        'task': 'teams.recompute_team_rankings',
        'schedule': crontab(hour=2, minute=0),
    },
    # Daily digest emails at 8 AM
    'send-digest-emails-daily': {
        'task': 'apps.notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    # Clean expired invites every 6 hours
    'clean-expired-invites': {
        'task': 'teams.clean_expired_invites',
        'schedule': crontab(hour='*/6', minute=0),
    },
    # Expire sponsors daily at 3 AM
    'expire-sponsors-daily': {
        'task': 'teams.expire_sponsors_task',
        'schedule': crontab(hour=3, minute=0),
    },
}

# ---------------------------------------------------------------------------
# Heavy / high-frequency tasks — only when ENABLE_CELERY_BEAT=1
# ---------------------------------------------------------------------------
_heavy_schedule = {
    # Process scheduled promotions hourly
    'process-scheduled-promotions': {
        'task': 'teams.process_scheduled_promotions_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Tournament wrap-up check every hour
    'check-tournament-wrapup': {
        'task': 'apps.tournaments.tasks.check_tournament_wrapup',
        'schedule': crontab(minute=15),  # Every hour at :15
    },

    # Auto-advance tournament statuses every 5 minutes
    'auto-advance-tournaments': {
        'task': 'apps.tournaments.tasks.auto_advance_tournaments',
        'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 300,
        },
    },

    # Auto-archive completed/cancelled tournaments daily at 4 AM
    'auto-archive-tournaments': {
        'task': 'apps.tournaments.tasks.auto_archive_tournaments',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'expires': 3600,
        },
    },

    # P4-T02: Expire overdue (unpaid) payments every 15 minutes
    'expire-overdue-payments': {
        'task': 'apps.tournaments.tasks.expire_overdue_payments',
        'schedule': crontab(minute='*/15'),
        'options': {
            'expires': 900,
        },
    },

    # Match-ready reminders every 5 minutes
    'notify-match-ready': {
        'task': 'apps.tournaments.tasks.notify_match_ready',
        'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 300,
        },
    },

    # No-show auto-DQ every 2 minutes
    'check-no-show-matches': {
        'task': 'apps.tournaments.tasks.check_no_show_matches',
        'schedule': crontab(minute='*/2'),
        'options': {
            'expires': 120,
        },
    },

    # ========================================================================
    # vNext Team & Organization Ranking Tasks (Phase 4 - P4-T2)
    # ========================================================================

    # Recalculate vNext team rankings nightly at 3:00 AM
    'vnext-recalculate-team-rankings': {
        'task': 'apps.organizations.tasks.recalculate_team_rankings',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'expires': 3600,
        }
    },

    # Apply inactivity decay nightly at 3:30 AM
    'vnext-apply-inactivity-decay': {
        'task': 'apps.organizations.tasks.apply_inactivity_decay',
        'schedule': crontab(hour=3, minute=30),
        'kwargs': {
            'cutoff_days': 7
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

    # ========================================================================
    # TournamentOps Periodic Tasks (Phase 1 - Foundation Wiring)
    # ========================================================================

    # Auto-confirm unresponded result submissions every 30 minutes
    'tournament-ops-auto-confirm-stale': {
        'task': 'apps.tournament_ops.tasks_result_submission.auto_confirm_submission_task',
        'schedule': crontab(minute='*/30'),
        'options': {
            'expires': 1800,
        },
    },

    # Send opponent response reminders every hour
    'tournament-ops-opponent-reminder': {
        'task': 'tournament_ops.opponent_response_reminder_task',
        'schedule': crontab(minute=20),
        'options': {
            'expires': 3600,
        },
    },

    # Auto-escalate overdue disputes every 6 hours
    'tournament-ops-dispute-escalation': {
        'task': 'tournament_ops.dispute_escalation_task',
        'schedule': crontab(hour='*/6', minute=45),
        'options': {
            'expires': 3600,
        },
    },
}

# Assemble the final beat schedule
if _beat_enabled:
    app.conf.beat_schedule = {**_base_schedule, **_heavy_schedule}
else:
    app.conf.beat_schedule = _base_schedule

# Celery configuration — memory-optimised for 512 MB
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,       # 30 minutes hard kill
    task_soft_time_limit=25 * 60,  # 25 minutes soft timeout

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result backend
    result_expires=3600,  # 1 hour

    # Worker settings — keep memory tight on Render Starter (512 MB)
    worker_prefetch_multiplier=1,      # fetch 1 task at a time (was 4)
    worker_max_tasks_per_child=50,     # recycle after 50 tasks (was 1000)
    worker_max_memory_per_child=150_000,  # 150 MB hard cap per worker
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working"""
    print(f'Request: {self.request!r}')
