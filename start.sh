#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup — memory-optimised for Starter tier (512 MB)
#
#   1. Celery Worker   (background, capped at 150 MB)
#   2. Discord Bot     (background, only if token is set)
#   3. Daphne          (foreground, binds $PORT for Render health-check)
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Migrations ──────────────────────────────────────────────────────
echo "[render] Running migrations…"
python manage.py migrate --noinput

# ── Celery worker (background) ─────────────────────────────────────
# concurrency=1           → single worker process
# max-tasks-per-child=50  → recycle after 50 tasks (prevents leak growth)
# max-memory-per-child    → 150 MB hard cap per worker process
echo "[render] Starting Celery worker…"
celery -A deltacrown worker \
    --loglevel=warning \
    --concurrency=1 \
    --max-tasks-per-child=50 \
    --max-memory-per-child=150000 \
    --without-heartbeat \
    &
CELERY_PID=$!

# ── Discord bot (background, conditional) ──────────────────────────
DISCORD_PID=""
if [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "[render] Starting Discord bot…"
    python manage.py run_discord_bot &
    DISCORD_PID=$!
else
    echo "[render] DISCORD_BOT_TOKEN not set — skipping bot."
fi

# ── Graceful shutdown ──────────────────────────────────────────────
cleanup() {
    echo "[render] Shutting down…"
    kill "$CELERY_PID" 2>/dev/null || true
    [ -n "$DISCORD_PID" ] && kill "$DISCORD_PID" 2>/dev/null || true
    wait
    echo "[render] All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Daphne (foreground) ────────────────────────────────────────────
PORT="${PORT:-8000}"
echo "[render] Starting Daphne on port $PORT…"
exec daphne \
    -b 0.0.0.0 \
    -p "$PORT" \
    --access-log - \
    deltacrown.asgi:application
