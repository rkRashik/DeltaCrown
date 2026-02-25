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

# ── Collect static files ────────────────────────────────────────────
echo "[render] Collecting static files…"
python manage.py collectstatic --noinput

# ── Run migrations ──────────────────────────────────────────────────
echo "[render] Running migrations…"
python manage.py migrate --noinput

# ── Start Celery worker (background) ───────────────────────────────
# concurrency=1 + 150 MB memory cap keeps the worker inside Free-Tier limits.
echo "[render] Starting Celery worker…"
celery -A deltacrown worker \
    --loglevel=info \
    --concurrency=1 \
    --max-tasks-per-child=50 \
    --max-memory-per-child=150000 \
    &
CELERY_PID=$!

# ── Start Discord bot (background, if token configured) ────────────
DISCORD_PID=""
if [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "[render] Starting Discord bot…"
    python manage.py run_discord_bot &
    DISCORD_PID=$!
else
    echo "[render] DISCORD_BOT_TOKEN not set — skipping bot."
fi

# ── Graceful shutdown handler ───────────────────────────────────────
cleanup() {
    echo "[render] Shutting down…"
    kill "$CELERY_PID" 2>/dev/null || true
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
WORKERS="${WEB_CONCURRENCY:-1}"
echo "[render] Starting Daphne on port $PORT (workers: $WORKERS)…"
exec daphne \
    -b 0.0.0.0 \
    -p "$PORT" \
    --access-log - \
    deltacrown.asgi:application
