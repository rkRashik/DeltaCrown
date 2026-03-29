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


def _normalize_celery_env_url(name: str) -> None:
    """Remove blank broker/backend env values before Celery reads them."""
    value = os.getenv(name)
    if value is None:
        return

    normalized = value.strip()
    if normalized.startswith(('"', "'")) and normalized.endswith(('"', "'")):
        normalized = normalized[1:-1].strip()

    if normalized:
        os.environ[name] = normalized
    else:
        os.environ.pop(name, None)


_normalize_celery_env_url('CELERY_BROKER_URL')
_normalize_celery_env_url('CELERY_RESULT_BACKEND')

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
#
# Daily tasks staggered with 30-min gaps to avoid worker contention
# on single-concurrency Render Starter deployment:
#   1:00 AM  team rankings recalculation (base; heavy schedule duplicates at 1:30 AM)
#   1:30 AM  vnext team rankings (heavy schedule)
#   2:00 AM  (reserved for inactivity decay in heavy schedule)
#   2:30 AM  (reserved for org rankings in heavy schedule)
#   3:00 AM  (reserved for auto-archive in heavy schedule)
#   8:00 AM  digest emails
# ---------------------------------------------------------------------------
_base_schedule = {
    # Daily ranking recalculation at 1:00 AM (staggered from 2 AM)
    'recompute-rankings-daily': {
        'task': 'apps.organizations.tasks.recalculate_team_rankings',
        'schedule': crontab(hour=1, minute=0),
    },
    # Daily digest emails at 8 AM
    'send-digest-emails-daily': {
        'task': 'apps.notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    # Clean expired invites every 6 hours
    'clean-expired-invites': {
        'task': 'apps.organizations.tasks.clean_expired_invites',
        'schedule': crontab(hour='*/6', minute=0),
    },
    # Critical participant reminders (1h/20m/5m windows) every 5 minutes.
    # Kept in base schedule so reminder automation is not disabled by heavy beat flag.
    'notify-match-ready': {
        'task': 'apps.tournaments.tasks.notify_match_ready',
        'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 300,
        },
    },
}

# ---------------------------------------------------------------------------
# Heavy / high-frequency tasks — only when ENABLE_CELERY_BEAT=1
# ---------------------------------------------------------------------------
_heavy_schedule = {
    # NOTE: 'process-scheduled-promotions' removed — was a no-op stub
    # (teams.process_scheduled_promotions_task always returns processed_count=0).
    # Task function preserved in legacy_bridge.py for backward compat.

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

    # Auto-archive completed/cancelled tournaments daily at 3:00 AM (moved from 4 AM)
    'auto-archive-tournaments': {
        'task': 'apps.tournaments.tasks.auto_archive_tournaments',
        'schedule': crontab(hour=3, minute=0),
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

    # No-show auto-DQ every 2 minutes
    'check-no-show-matches': {
        'task': 'apps.tournaments.tasks.check_no_show_matches',
        'schedule': crontab(minute='*/2'),
        'options': {
            'expires': 120,
        },
    },

    # Phase 10: Sync Riot-backed Valorant passport stats
    'sync-all-active-riot-passports': {
        'task': 'user_profile.sync_all_active_riot_passports',
        'schedule': crontab(minute=os.getenv('RIOT_SYNC_SCHEDULE_MINUTE', '*/20')),
        'options': {
            # Prevent overlaps when queues are congested.
            'expires': int(os.getenv('RIOT_SYNC_TASK_EXPIRES_SECONDS', '900')),
        },
    },

    # Steam persona name / avatar refresh every 4 hours (conservative — Steam API rate limits)
    'sync-all-active-steam-passports': {
        'task': 'user_profile.sync_all_active_steam_passports',
        'schedule': crontab(hour='*/4', minute=10),
        'options': {'expires': 3600},
    },

    # Epic OAuth token proactive refresh every hour (tokens expire every 4h, 30-min window)
    'sync-all-active-epic-passports': {
        'task': 'user_profile.sync_all_active_epic_passports',
        'schedule': crontab(minute=50),
        'options': {'expires': 3600},
    },

    # ========================================================================
    # vNext Team & Organization Ranking Tasks (Phase 4 - P4-T2)
    # ========================================================================

    # Recalculate vNext team rankings nightly at 1:30 AM (staggered from 3 AM)
    'vnext-recalculate-team-rankings': {
        'task': 'apps.organizations.tasks.recalculate_team_rankings',
        'schedule': crontab(hour=1, minute=30),
        'options': {
            'expires': 3600,
        }
    },

    # Apply inactivity decay nightly at 2:00 AM (staggered from 3:30 AM)
    'vnext-apply-inactivity-decay': {
        'task': 'apps.organizations.tasks.apply_inactivity_decay',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {
            'cutoff_days': 7
        },
        'options': {
            'expires': 3600,
        }
    },

    # Recalculate organization rankings nightly at 2:30 AM (staggered from 4 AM)
    'vnext-recalculate-org-rankings': {
        'task': 'apps.organizations.tasks.recalculate_organization_rankings',
        'schedule': crontab(hour=2, minute=30),
        'options': {
            'expires': 3600,
        }
    },

    # Phase 18: Reset daily match counters at midnight UTC
    'reset-daily-match-counters': {
        'task': 'apps.organizations.tasks.reset_daily_match_counters',
        'schedule': crontab(hour=0, minute=0),
        'options': {'expires': 3600},
    },

    # Phase 18: Activity score decay at 00:15 UTC
    'apply-activity-decay': {
        'task': 'apps.organizations.tasks.apply_activity_decay',
        'schedule': crontab(hour=0, minute=15),
        'options': {'expires': 3600},
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

    # ========================================================================
    # Leaderboard Snapshot & Analytics Tasks (Phase F / Phase 8)
    # Night window stagger (single-concurrency Render Starter):
    #   03:30  all-time snapshot
    #   04:00  mark inactive players
    #   04:30  cold storage compaction (Sundays only)
    #   05:00  nightly user analytics
    #   05:30  nightly team analytics
    # ========================================================================

    # Tournament ranking snapshots every 30 min (no-op unless ENGINE_V2_ENABLED=1)
    'snapshot-active-tournaments': {
        'task': 'apps.leaderboards.tasks.snapshot_active_tournaments',
        'schedule': crontab(minute='*/30'),
        'options': {'expires': 1800},
    },

    # All-time cross-game ranking snapshot daily at 03:30 UTC
    'snapshot-all-time-global': {
        'task': 'apps.leaderboards.tasks.snapshot_all_time',
        'schedule': crontab(hour=3, minute=30),
        'args': [None],
        'options': {'expires': 3600},
    },

    # Hourly leaderboard cache refresh at :45 each hour
    'hourly-leaderboard-refresh': {
        'task': 'apps.leaderboards.tasks.hourly_leaderboard_refresh',
        'schedule': crontab(minute=45),
        'options': {'expires': 3600},
    },

    # Mark inactive players (>30 days) daily at 04:00 UTC
    'mark-inactive-players': {
        'task': 'apps.leaderboards.tasks.mark_inactive_players',
        'schedule': crontab(hour=4, minute=0),
        'options': {'expires': 3600},
    },

    # Weekly cold storage compaction — Sundays at 04:30 UTC, 90-day threshold
    'compact-old-snapshots': {
        'task': 'apps.leaderboards.tasks.compact_old_snapshots',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
        'args': [90],
        'options': {'expires': 3600},
    },

    # Nightly user analytics refresh at 05:00 UTC
    'nightly-user-analytics-refresh': {
        'task': 'apps.leaderboards.tasks.nightly_user_analytics_refresh',
        'schedule': crontab(hour=5, minute=0),
        'options': {'expires': 7200},
    },

    # Nightly team analytics refresh at 05:30 UTC (staggered)
    'nightly-team-analytics-refresh': {
        'task': 'apps.leaderboards.tasks.nightly_team_analytics_refresh',
        'schedule': crontab(hour=5, minute=30),
        'options': {'expires': 7200},
    },

    # Seasonal rollover — first of each month at 00:00 UTC
    'seasonal-rollover': {
        'task': 'apps.leaderboards.tasks.seasonal_rollover',
        'schedule': crontab(hour=0, minute=0, day_of_month=1),
        'options': {'expires': 3600},
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
