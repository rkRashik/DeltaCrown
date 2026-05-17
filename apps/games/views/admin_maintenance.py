"""System Operations Center — admin maintenance view.

All operations:
  - Work without ENABLE_CELERY_BEAT.
  - Create a MaintenanceRunLog row on completion.
  - Never expose secret keys in responses.
  - Destructive ops require typed confirmation.
  - Protected paths (evidence, payments, kyc) can never be deleted.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------

def _has_maintenance_permission(user) -> bool:
    return user.is_superuser or user.has_perm("games.can_run_maintenance_tasks")


# ---------------------------------------------------------------------------
# Run logger
# ---------------------------------------------------------------------------

def _log_run(user, task_name: str, status: str, started_at, summary: dict, error: str = "") -> None:
    try:
        from apps.games.models.maintenance_log import MaintenanceRunLog
        finished = timezone.now()
        ms = int((finished - started_at).total_seconds() * 1000)
        MaintenanceRunLog.objects.create(
            user=user,
            task_name=task_name,
            status=status,
            started_at=started_at,
            finished_at=finished,
            duration_ms=ms,
            summary=summary,
            error_message=error,
        )
    except Exception:
        logger.exception("Could not write MaintenanceRunLog for task=%s", task_name)


# ---------------------------------------------------------------------------
# Environment status
# ---------------------------------------------------------------------------

def _get_env_status() -> dict:
    from django.core.files.storage import default_storage

    try:
        backend_cls = type(default_storage).__name__
        is_cloudinary = "Cloudinary" in backend_cls
    except Exception:
        backend_cls = "unknown"
        is_cloudinary = False

    cloudinary_configured = bool(os.getenv("CLOUDINARY_URL"))
    beat_enabled = os.getenv("ENABLE_CELERY_BEAT", "0") == "1"
    media_cleanup_enabled = os.getenv("ENABLE_MEDIA_CLEANUP_BEAT", "0") == "1"
    django_env = os.getenv("DJANGO_ENV", "development")
    is_production = (not settings.DEBUG) or (django_env == "production")

    redis_ok = False
    try:
        from django.core.cache import cache
        cache.set("_maint_ping", 1, timeout=5)
        redis_ok = cache.get("_maint_ping") == 1
        cache.delete("_maint_ping")
    except Exception:
        pass

    db_ok = False
    try:
        from django.db import connection
        connection.ensure_connection()
        db_ok = True
    except Exception:
        pass

    riot_key_set = bool(os.getenv("RIOT_API_KEY"))

    return {
        "backend_cls": backend_cls,
        "is_cloudinary": is_cloudinary,
        "cloudinary_configured": cloudinary_configured,
        "beat_enabled": beat_enabled,
        "media_cleanup_enabled": media_cleanup_enabled,
        "django_env": django_env,
        "is_production": is_production,
        "redis_ok": redis_ok,
        "db_ok": db_ok,
        "riot_key_set": riot_key_set,
        "local_storage_in_prod": (not is_cloudinary) and is_production,
    }


# ---------------------------------------------------------------------------
# Group 1 — Media & Storage handlers
# ---------------------------------------------------------------------------

def _run_game_media_audit() -> dict:
    from apps.common.media_urls import storage_file_exists
    from apps.games.models.game import Game
    IMAGE_FIELDS = ("icon", "logo", "banner", "card_image")
    ok = missing = empty = 0
    missing_detail = []
    for game in Game.objects.filter(is_active=True).order_by("slug"):
        for f in IMAGE_FIELDS:
            field = getattr(game, f, None)
            name = getattr(field, "name", "") or ""
            if not name:
                empty += 1
                continue
            if storage_file_exists(field):
                ok += 1
            else:
                missing += 1
                missing_detail.append({"game": game.name, "field": f, "path": name})
    return {"ok": ok, "empty": empty, "missing": missing, "missing_detail": missing_detail[:50]}


def _run_map_image_audit() -> dict:
    from apps.common.media_urls import storage_file_exists
    from apps.games.models.map_pool import GameMapPool
    ok = missing = empty = no_image_active = 0
    missing_detail = []
    for mp in GameMapPool.objects.select_related("game").filter(game__is_active=True).order_by("game__slug", "map_name"):
        name = getattr(mp.image, "name", "") or ""
        if not name:
            empty += 1
            if mp.is_active and mp.is_competitive:
                no_image_active += 1
            continue
        if storage_file_exists(mp.image):
            ok += 1
        else:
            missing += 1
            missing_detail.append({"game": mp.game.name, "map": mp.map_name, "path": name})
    return {"ok": ok, "empty": empty, "missing": missing, "no_image_active": no_image_active, "missing_detail": missing_detail[:30]}


def _run_storage_backend_check() -> dict:
    from django.core.files.storage import default_storage
    backend_cls = type(default_storage).__name__
    is_cloudinary = "Cloudinary" in backend_cls
    cloudinary_url = os.getenv("CLOUDINARY_URL", "")
    result = {
        "backend": backend_cls,
        "is_cloudinary": is_cloudinary,
        "cloudinary_env_set": bool(cloudinary_url),
    }
    if is_cloudinary:
        try:
            from apps.games.management.commands.audit_cloudinary_orphans import _cloudinary_available
            result["cloudinary_api_ok"] = _cloudinary_available()
        except Exception as exc:
            result["cloudinary_api_ok"] = False
            result["cloudinary_error"] = str(exc)
    return result


def _run_cloudinary_orphan_scan() -> dict:
    from apps.games.management.commands.audit_cloudinary_orphans import (
        ALL_APPROVED_FOLDERS, _cloudinary_available, _cloudinary_media_prefix,
        _collect_db_references, _is_blocked, _is_recent, _list_cloudinary_folder,
        DEFAULT_MIN_AGE_HOURS,
    )
    if not _cloudinary_available():
        return {"error": "Cloudinary is not configured. Set CLOUDINARY_URL."}
    db_refs = _collect_db_references()
    prefix = _cloudinary_media_prefix()
    orphans, recent_protected, scanned = [], 0, 0
    for folder in ALL_APPROVED_FOLDERS:
        for res in _list_cloudinary_folder(prefix + folder):
            scanned += 1
            pid = res.get("public_id", "")
            if _is_blocked(pid) or pid in db_refs:
                continue
            if _is_recent(res, DEFAULT_MIN_AGE_HOURS):
                recent_protected += 1
                continue
            orphans.append({"public_id": pid, "created_at": res.get("created_at"), "bytes": res.get("bytes", 0)})
    return {
        "scanned": scanned, "orphan_count": len(orphans),
        "recent_protected": recent_protected, "folders": len(ALL_APPROVED_FOLDERS),
        "orphans_preview": orphans[:20],
    }


def _run_delete_eligible_media() -> dict:
    from apps.games.services.media_cleanup_service import MediaCleanupService
    return dict(MediaCleanupService().process_eligible(dry_run=False))


# ---------------------------------------------------------------------------
# Group 2 — Riot / Passport handlers
# ---------------------------------------------------------------------------

def _run_riot_retry() -> dict:
    try:
        from apps.games.tasks.riot_verification_tasks import retry_pending_riot_passports_task
        retry_pending_riot_passports_task.delay()
        return {"queued": True, "method": "celery"}
    except Exception:
        try:
            from apps.user_profile.models_main import GameProfile
            from apps.games.tasks.riot_verification_tasks import verify_game_passport_task
            pending_ids = list(
                GameProfile.objects.filter(game__slug="valorant")
                .exclude(verification_status="VERIFIED")
                .values_list("id", flat=True)[:30]
            )
            for pid in pending_ids:
                try:
                    verify_game_passport_task.apply(args=[pid])
                except Exception:
                    pass
            return {"queued": True, "enqueued": len(pending_ids), "method": "inline"}
        except Exception as exc:
            return {"queued": False, "error": str(exc)}


def _run_riot_verify_one(passport_id: str) -> dict:
    if not passport_id or not str(passport_id).strip().isdigit():
        return {"error": "Provide a valid numeric passport (GameProfile) ID."}
    pid = int(passport_id)
    try:
        from apps.games.tasks.riot_verification_tasks import verify_game_passport_task
        verify_game_passport_task.apply(args=[pid], kwargs={"force": True})
        return {"passport_id": pid, "dispatched": True, "message": f"Verification run for passport #{pid}."}
    except Exception as exc:
        return {"passport_id": pid, "error": str(exc)}


def _run_riot_api_test(riot_id: str) -> dict:
    raw = (riot_id or "").strip()
    if "#" not in raw:
        return {"error": "Format must be 'GameName#TAG' (e.g. PlayerOne#1234)."}
    game_name, tag_line = raw.rsplit("#", 1)
    game_name, tag_line = game_name.strip(), tag_line.strip()
    if not game_name or not tag_line:
        return {"error": "Both game name and tag are required."}
    try:
        from apps.games.services.riot_verification_service import verify_riot_id, _key_diagnostic
        key_info = _key_diagnostic()
        result = verify_riot_id(game_name, tag_line)
        return {
            "riot_id_tested": raw,
            "api_key_status": key_info,
            "verified": result.get("verified", False),
            "puuid_found": bool(result.get("puuid")),
            "error": result.get("error"),
            "status": result.get("status"),
        }
    except Exception as exc:
        return {"riot_id_tested": raw, "error": str(exc)}


# ---------------------------------------------------------------------------
# Group 3 — Tournament & Match handlers (reuse lifecycle_cron runners)
# ---------------------------------------------------------------------------

def _run_sweep_no_show() -> dict:
    from deltacrown.lifecycle_cron import _run_no_show
    return _run_no_show()


def _run_sweep_veto() -> dict:
    try:
        from apps.tournaments.tasks.veto_timeout import sweep_veto_timeouts
        result = sweep_veto_timeouts.apply().result
        return result if isinstance(result, dict) else {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_auto_advance() -> dict:
    from deltacrown.lifecycle_cron import _run_auto_advance
    return _run_auto_advance()


def _run_tournament_wrapup() -> dict:
    from deltacrown.lifecycle_cron import _run_wrapup
    return _run_wrapup()


def _run_expire_payments() -> dict:
    from deltacrown.lifecycle_cron import _run_payment_expiry
    return _run_payment_expiry()


def _run_auto_confirm_submissions() -> dict:
    from deltacrown.lifecycle_cron import _run_auto_confirm_submissions
    return _run_auto_confirm_submissions()


# ---------------------------------------------------------------------------
# Group 4 — Evidence handlers
# ---------------------------------------------------------------------------

def _run_evidence_audit() -> dict:
    try:
        from apps.tournaments.models import Match
        try:
            from apps.tournaments.tasks.evidence_cleanup import sweep_eligible_evidence_task
            retention_days = 30
        except Exception:
            retention_days = 30
        cutoff = timezone.now() - timedelta(days=retention_days)
        total = Match.objects.filter(state="completed", updated_at__lt=cutoff).count()
        return {"total_completed_old": total, "retention_days": retention_days, "dry_run": True}
    except Exception as exc:
        return {"error": str(exc), "dry_run": True}


def _run_evidence_sweep() -> dict:
    try:
        from apps.tournaments.tasks.evidence_cleanup import sweep_eligible_evidence_task
        result = sweep_eligible_evidence_task.apply().result
        return result if isinstance(result, dict) else {"ok": True, "swept": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Group 5 — Cache & Health handlers
# ---------------------------------------------------------------------------

def _run_clear_game_cache() -> dict:
    from django.core.cache import cache
    keys_cleared = []
    for key in ["context_active_games", "active_games_list", "games_registry"]:
        if cache.delete(key):
            keys_cleared.append(key)
    return {"cleared_keys": keys_cleared, "total": len(keys_cleared)}


def _run_leaderboard_refresh() -> dict:
    try:
        from apps.leaderboards.tasks import hourly_leaderboard_refresh
        result = hourly_leaderboard_refresh.apply().result
        return result if isinstance(result, dict) else {"ok": True, "refreshed": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_health_check() -> dict:
    from django.core.cache import cache
    from django.core.files.storage import default_storage

    checks = {}

    # DB
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    # Redis/Cache
    try:
        cache.set("_health_check", 1, timeout=5)
        val = cache.get("_health_check")
        cache.delete("_health_check")
        checks["cache"] = "ok" if val == 1 else "read_failed"
    except Exception as exc:
        checks["cache"] = f"error: {exc}"

    # Storage
    checks["storage_backend"] = type(default_storage).__name__
    checks["cloudinary_env"] = "set" if os.getenv("CLOUDINARY_URL") else "not_set"
    checks["riot_api_key"] = "set" if os.getenv("RIOT_API_KEY") else "not_set"
    checks["beat_enabled"] = os.getenv("ENABLE_CELERY_BEAT", "0")
    checks["django_env"] = os.getenv("DJANGO_ENV", "development")
    checks["debug"] = str(settings.DEBUG)

    overall = "ok" if all(v == "ok" or "set" in str(v) or v in ("ok", "True", "False", "development", "production", "0", "1") for v in checks.values()) else "warning"
    return {"status": overall, **checks}


# ---------------------------------------------------------------------------
# Recommended actions — context-aware cards shown near the top of the page
# ---------------------------------------------------------------------------

def _compute_recommended_actions(env: dict, eligible_count: int, pending_count: int) -> list[dict]:
    actions = []
    if env.get("local_storage_in_prod"):
        actions.append({
            "type": "danger",
            "icon": "cloud_off",
            "title": "Local storage active in production",
            "desc": "Files uploaded here exist only on this server. Use deltacrown.xyz admin to upload production images.",
            "cta_label": "Open Games",
            "cta_href": "/admin/games/game/",
            "cta_tab": None,
        })
    if eligible_count > 0:
        actions.append({
            "type": "warning",
            "icon": "delete_sweep",
            "title": f"{eligible_count} file(s) eligible for cleanup",
            "desc": "Old replaced game media has passed the 48 h retention window and can be safely deleted.",
            "cta_label": "Delete Eligible Media",
            "cta_href": None,
            "cta_tab": "t-media",
        })
    elif pending_count > 0:
        actions.append({
            "type": "info",
            "icon": "hourglass_top",
            "title": f"{pending_count} candidate(s) in retention window",
            "desc": "Old replaced game media is waiting for the 48 h window before becoming eligible.",
            "cta_label": "View Candidates",
            "cta_href": "/admin/games/mediacleanupcandidate/",
            "cta_tab": None,
        })
    if not env.get("riot_key_set"):
        actions.append({
            "type": "warning",
            "icon": "key_off",
            "title": "Riot API key not configured",
            "desc": "Valorant passport verification will fail. Set RIOT_API_KEY in Render environment variables.",
            "cta_label": "Test Riot API",
            "cta_href": None,
            "cta_tab": "t-riot",
        })
    if not env.get("redis_ok"):
        actions.append({
            "type": "danger",
            "icon": "error",
            "title": "Redis unavailable",
            "desc": "Cache and Celery messaging are not working. Some operations may fail silently.",
            "cta_label": "Run Health Check",
            "cta_href": None,
            "cta_tab": "t-cache",
        })
    if not actions:
        actions.append({
            "type": "success",
            "icon": "check_circle",
            "title": "System looks healthy",
            "desc": "No critical issues detected. Run any operation below as needed.",
            "cta_label": None,
            "cta_href": None,
            "cta_tab": None,
        })
    return actions[:5]


# ---------------------------------------------------------------------------
# Action dispatch table
# format: label, handler, is_destructive, confirm_word_required
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, tuple] = {
    # Group 1 — Media
    "game_media_audit":      ("Game Media Audit",          _run_game_media_audit,      False, None),
    "map_image_audit":       ("Map Image Audit",            _run_map_image_audit,       False, None),
    "storage_backend_check": ("Storage Backend Check",      _run_storage_backend_check, False, None),
    "orphan_scan":           ("Cloudinary Orphan Scan",     _run_cloudinary_orphan_scan,False, None),
    "delete_eligible_media": ("Delete Eligible Media",      _run_delete_eligible_media, True,  "CLEANUP"),
    # Group 2 — Riot
    "riot_retry":            ("Riot Passport Retry",        _run_riot_retry,            False, None),
    # Group 3 — Tournament
    "sweep_no_show":         ("No-Show / Forfeit Sweep",    _run_sweep_no_show,         False, None),
    "sweep_veto":            ("Veto Timeout Sweep",         _run_sweep_veto,            False, None),
    "auto_advance":          ("Auto-Advance Tournaments",   _run_auto_advance,          False, None),
    "tournament_wrapup":     ("Tournament Wrapup",          _run_tournament_wrapup,     False, None),
    "expire_payments":       ("Expire Overdue Payments",    _run_expire_payments,       False, None),
    "auto_confirm_submissions": ("Auto-Confirm Submissions",_run_auto_confirm_submissions,False,None),
    # Group 4 — Evidence
    "evidence_audit":        ("Evidence Cleanup Audit",     _run_evidence_audit,        False, None),
    "evidence_sweep":        ("Run Evidence Sweep",         _run_evidence_sweep,        True,  "RUN"),
    # Group 5 — Cache/Health
    "clear_game_cache":      ("Clear Game Cache",           _run_clear_game_cache,      False, None),
    "leaderboard_refresh":   ("Leaderboard Cache Refresh",  _run_leaderboard_refresh,   False, None),
    "health_check":          ("System Health Check",        _run_health_check,          False, None),
}

# Input-based actions handled separately in the view
_INPUT_ACTIONS = {"riot_verify_one", "riot_api_test"}


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

@staff_member_required
@require_http_methods(["GET", "POST"])
def maintenance_panel(request):
    if not _has_maintenance_permission(request.user):
        return HttpResponseForbidden("You do not have permission to access the maintenance panel.")

    result = None
    action_label = None
    action_status = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        # ── Input-based special actions ──────────────────────────────
        if action == "riot_verify_one":
            label = "Verify Riot Passport by ID"
            started = timezone.now()
            passport_id = request.POST.get("passport_id", "").strip()
            try:
                result = _run_riot_verify_one(passport_id)
                log_status = "failed" if result.get("error") else "success"
            except Exception as exc:
                result = {"error": str(exc)}
                log_status = "failed"
            _log_run(request.user, label, log_status, started, result or {})
            action_label, action_status = label, log_status

        elif action == "riot_api_test":
            label = "Riot API Test"
            started = timezone.now()
            riot_id = request.POST.get("riot_id", "").strip()
            try:
                result = _run_riot_api_test(riot_id)
                log_status = "failed" if result.get("error") else "success"
            except Exception as exc:
                result = {"error": str(exc)}
                log_status = "failed"
            _log_run(request.user, label, log_status, started, result or {})
            action_label, action_status = label, log_status

        # ── Standard mapped actions ──────────────────────────────────
        elif action in _ACTION_MAP:
            label, handler, is_destructive, confirm_word = _ACTION_MAP[action]

            if is_destructive and confirm_word:
                confirm = request.POST.get("confirm_word", "").strip()
                if confirm != confirm_word:
                    from django.contrib import messages
                    messages.error(request, f"Type '{confirm_word}' exactly to confirm.")
                    return redirect(request.path)

            started = timezone.now()
            error_msg = ""
            try:
                result = handler()
                has_error = isinstance(result, dict) and bool(result.get("error"))
                log_status = "failed" if has_error else "success"
            except Exception as exc:
                logger.exception("Maintenance panel: %s raised", action)
                result = {"error": str(exc)}
                log_status = "failed"
                error_msg = str(exc)

            _log_run(request.user, label, log_status, started, result or {}, error_msg)
            action_label, action_status = label, log_status

        else:
            from django.contrib import messages
            messages.error(request, "Unknown maintenance action.")

    # ── Context ──────────────────────────────────────────────────────
    from apps.games.models.cleanup_candidate import MediaCleanupCandidate
    from apps.games.models.maintenance_log import MaintenanceRunLog

    eligible_count = MediaCleanupCandidate.objects.filter(
        status="pending", eligible_after__lte=timezone.now(),
    ).count()
    pending_count = MediaCleanupCandidate.objects.filter(status="pending").count()
    recent_logs = MaintenanceRunLog.objects.select_related("user").order_by("-created_at")[:12]

    env = _get_env_status()

    ctx = {
        "title": "System Operations Center",
        "site_header": "DeltaCrown Admin",
        "env": env,
        "eligible_count": eligible_count,
        "pending_count": pending_count,
        "recent_logs": recent_logs,
        "result": result,
        "action_label": action_label,
        "action_status": action_status,
        "recommended_actions": _compute_recommended_actions(env, eligible_count, pending_count),
        "cleanup_admin_url": "/admin/games/mediacleanupcandidate/",
        "games_admin_url": "/admin/games/game/",
        "logs_admin_url": "/admin/games/maintenancerunlog/",
    }
    return render(request, "admin/games/maintenance.html", ctx)
