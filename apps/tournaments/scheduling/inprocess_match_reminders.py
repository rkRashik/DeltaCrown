"""In-process scheduler for match reminder notifications.

This replaces Celery beat timing for match reminder windows on low-memory
single-instance deployments.
"""

from __future__ import annotations

import logging
import os
import sys
import threading

from django.db import close_old_connections

logger = logging.getLogger(__name__)

_START_LOCK = threading.Lock()
_STOP_EVENT = threading.Event()
_SCHEDULER_THREAD = None


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _scheduler_interval_seconds() -> int:
    raw = os.getenv("MATCH_REMINDER_INTERVAL_SECONDS", "60")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 60
    return max(15, min(value, 600))


def _scheduler_initial_delay_seconds() -> int:
    raw = os.getenv("MATCH_REMINDER_INITIAL_DELAY_SECONDS", "8")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 8
    return max(0, min(value, 60))


def _should_start_scheduler() -> bool:
    if _env_flag("DISABLE_INPROCESS_MATCH_REMINDER", False):
        return False

    argv = [arg.lower() for arg in sys.argv]
    argv_joined = " ".join(argv)

    if "celery" in argv_joined:
        return False

    if "pytest" in argv_joined or os.getenv("PYTEST_CURRENT_TEST"):
        return False

    blocked_commands = {
        "makemigrations",
        "migrate",
        "collectstatic",
        "shell",
        "dbshell",
        "test",
        "createsuperuser",
    }
    if any(cmd in argv for cmd in blocked_commands):
        return False

    # Django autoreloader starts two runserver processes; only start in child.
    if "runserver" in argv and os.getenv("RUN_MAIN") != "true":
        return False

    return True


def _scheduler_loop(interval_seconds: int, initial_delay_seconds: int) -> None:
    if initial_delay_seconds > 0 and _STOP_EVENT.wait(initial_delay_seconds):
        return

    while not _STOP_EVENT.is_set():
        try:
            close_old_connections()
            from apps.tournaments.tasks.match_ready import run_match_ready_reminder_sweep

            result = run_match_ready_reminder_sweep()
            notified = int((result or {}).get("notified", 0) or 0)
            if notified:
                logger.info(
                    "[match_reminder.scheduler] Delivered %s reminder notification(s)",
                    notified,
                )
        except Exception:
            logger.exception("[match_reminder.scheduler] Reminder sweep failed")
        finally:
            close_old_connections()

        _STOP_EVENT.wait(interval_seconds)


def start_inprocess_match_reminder_scheduler() -> bool:
    """Start daemon scheduler thread once per process.

    Returns True if a new scheduler was started, else False.
    """
    global _SCHEDULER_THREAD

    if not _should_start_scheduler():
        return False

    with _START_LOCK:
        if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
            return False

        interval_seconds = _scheduler_interval_seconds()
        initial_delay_seconds = _scheduler_initial_delay_seconds()

        _STOP_EVENT.clear()
        _SCHEDULER_THREAD = threading.Thread(
            target=_scheduler_loop,
            name="match-reminder-scheduler",
            kwargs={
                "interval_seconds": interval_seconds,
                "initial_delay_seconds": initial_delay_seconds,
            },
            daemon=True,
        )
        _SCHEDULER_THREAD.start()

        logger.info(
            "Started in-process match reminder scheduler (interval=%ss, initial_delay=%ss)",
            interval_seconds,
            initial_delay_seconds,
        )
        return True


def stop_inprocess_match_reminder_scheduler() -> None:
    """Signal scheduler thread to stop (mainly for tests)."""
    _STOP_EVENT.set()
