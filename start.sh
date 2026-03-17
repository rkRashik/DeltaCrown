#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup — memory-optimised for Starter tier (512 MB)
#
#   1. Celery Worker   (background, capped at 150 MB)
#   2. Celery Beat     (background, if ENABLE_CELERY_BEAT=1)
#   3. Discord Bot     (background, only if token is set)
#   4. Daphne          (foreground, binds $PORT for Render health-check)
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "[render] Startup profile: migrations=${ENABLE_MIGRATIONS_ON_START:-1} celery=${ENABLE_CELERY_WORKER:-1} beat=${ENABLE_CELERY_BEAT:-0} discord=${ENABLE_DISCORD_BOT:-1} access_log=${DAPHNE_ACCESS_LOG:-0}"

# ── Migrations ──────────────────────────────────────────────────────
if [ "${ENABLE_MIGRATIONS_ON_START:-1}" = "1" ]; then
    echo "[render] Running migrations…"
    python manage.py migrate --noinput
else
    echo "[render] ENABLE_MIGRATIONS_ON_START=0 — skipping migrations."
fi

# ── Celery worker (background) ─────────────────────────────────────
# concurrency=1           → single worker process
# max-tasks-per-child=50  → recycle after 50 tasks (prevents leak growth)
# max-memory-per-child    → 150 MB hard cap per worker process
CELERY_PID=""
if [ "${ENABLE_CELERY_WORKER:-1}" = "1" ]; then
    echo "[render] Starting Celery worker…"
    celery -A deltacrown worker \
        --loglevel=warning \
        --concurrency=1 \
        --max-tasks-per-child=50 \
        --max-memory-per-child=150000 \
        --without-heartbeat \
        &
    CELERY_PID=$!
else
    echo "[render] ENABLE_CELERY_WORKER=0 — skipping worker."
fi

# ── Celery Beat scheduler (background, opt-in) ──────────────────
# Drives periodic tasks defined in deltacrown/celery.py beat_schedule.
# Only start when ENABLE_CELERY_BEAT=1 (set in Render env vars).
BEAT_PID=""
if [ "${ENABLE_CELERY_BEAT:-0}" = "1" ]; then
    echo "[render] Starting Celery Beat…"
    celery -A deltacrown beat \
        --loglevel=warning \
        &
    BEAT_PID=$!
else
    echo "[render] ENABLE_CELERY_BEAT=0 — skipping beat scheduler."
fi

# ── Discord bot (background, conditional) ──────────────────────────
DISCORD_PID=""
if [ "${ENABLE_DISCORD_BOT:-1}" = "1" ] && [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "[render] Starting Discord bot…"
    python manage.py run_discord_bot &
    DISCORD_PID=$!
elif [ "${ENABLE_DISCORD_BOT:-1}" != "1" ]; then
    echo "[render] ENABLE_DISCORD_BOT=0 — skipping bot."
else
    echo "[render] DISCORD_BOT_TOKEN not set — skipping bot."
fi

# ── Graceful shutdown ──────────────────────────────────────────────
cleanup() {
    echo "[render] Shutting down…"
    [ -n "$CELERY_PID" ] && kill "$CELERY_PID" 2>/dev/null || true
    [ -n "$BEAT_PID" ] && kill "$BEAT_PID" 2>/dev/null || true
    [ -n "$DISCORD_PID" ] && kill "$DISCORD_PID" 2>/dev/null || true
    wait
    echo "[render] All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Daphne (foreground) ────────────────────────────────────────────
PORT="${PORT:-8000}"
HTTP_TIMEOUT="${DAPHNE_HTTP_TIMEOUT:-60}"
echo "[render] Starting Daphne on port $PORT (http-timeout=${HTTP_TIMEOUT}s)…"
if [ "${DAPHNE_ACCESS_LOG:-0}" = "1" ]; then
    exec daphne \
        -b 0.0.0.0 \
        -p "$PORT" \
        --http-timeout "$HTTP_TIMEOUT" \
        --access-log - \
        deltacrown.asgi:application
else
    exec daphne \
        -b 0.0.0.0 \
        -p "$PORT" \
        --http-timeout "$HTTP_TIMEOUT" \
        deltacrown.asgi:application
fi
