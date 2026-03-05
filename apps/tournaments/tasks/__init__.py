"""
Tournament Celery tasks package.

Auto-discovered by Celery via deltacrown/celery.py → app.autodiscover_tasks().
"""
from .lifecycle import (
    auto_advance_tournaments,
    check_tournament_wrapup,
    auto_archive_tournaments,
)
from .payment_expiry import expire_overdue_payments
from .match_ready import notify_match_ready
from .discord_tasks import dispatch_discord_webhook
from .no_show_timer import check_no_show_matches