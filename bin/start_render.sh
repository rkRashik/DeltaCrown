#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup script — runs all 3 processes in a single container
#
#   1. Celery Worker   (background)
#   2. Discord Bot     (background)
#   3. Daphne / Gunicorn  (foreground — binds $PORT for Render health check)
#
# Render Free/Starter plans allow only 1 service, so we multiplex here.
# Set REDIS_URL (e.g. Upstash) and DISCORD_BOT_TOKEN in Render env vars.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "[render] Startup profile: migrations=${ENABLE_MIGRATIONS_ON_START:-1} celery=${ENABLE_CELERY_WORKER:-1} discord=${ENABLE_DISCORD_BOT:-1} access_log=${DAPHNE_ACCESS_LOG:-0}"

# ── Collect static files ────────────────────────────────────────────
echo "[render] Collecting static files…"
python manage.py collectstatic --noinput

# ── Run migrations ──────────────────────────────────────────────────
if [ "${ENABLE_MIGRATIONS_ON_START:-1}" = "1" ]; then
    echo "[render] Running migrations…"
    python manage.py migrate --noinput
else
    echo "[render] ENABLE_MIGRATIONS_ON_START=0 — skipping migrations."
fi

# ── Start Celery worker (background) ───────────────────────────────
# concurrency=1 + 150 MB memory cap keeps the worker inside Free-Tier limits.
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

# ── Start Discord bot (background, if token configured) ────────────
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

# ── Graceful shutdown handler ───────────────────────────────────────
cleanup() {
    echo "[render] Shutting down…"
    [ -n "$CELERY_PID" ] && kill "$CELERY_PID" 2>/dev/null || true
    [ -n "$DISCORD_PID" ] && kill "$DISCORD_PID" 2>/dev/null || true
    wait
    echo "[render] All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Start web server (foreground) ───────────────────────────────────
# Render injects $PORT; default to 8000 for local testing.
# WEB_CONCURRENCY is set in Render env vars (default 1 for Free Tier).
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
