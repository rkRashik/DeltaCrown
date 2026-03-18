#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup — memory-optimised for Starter tier (512 MB)
#
#   1. Celery Worker   (background, solo pool — no subprocess fork)
#   2. Celery Beat     (background, if ENABLE_CELERY_BEAT=1)
#   3. Discord Bot     (background, only if token is set)
#   4. Daphne          (foreground, binds $PORT for Render health-check)
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

CELERY_POOL="${CELERY_POOL:-solo}"
CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-1}"
CELERY_PREFETCH_MULTIPLIER="${CELERY_PREFETCH_MULTIPLIER:-1}"
DAPHNE_WS_CONNECT_TIMEOUT="${DAPHNE_WEBSOCKET_CONNECT_TIMEOUT:-5}"
DAPHNE_PING_INTERVAL="${DAPHNE_PING_INTERVAL:-20}"
DAPHNE_PING_TIMEOUT="${DAPHNE_PING_TIMEOUT:-30}"
DAPHNE_APP_CLOSE_TIMEOUT="${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-5}"

echo "[render] Startup profile: migrations=${ENABLE_MIGRATIONS_ON_START:-1} celery=${ENABLE_CELERY_WORKER:-1} beat=${ENABLE_CELERY_BEAT:-0} discord=${ENABLE_DISCORD_BOT:-0} access_log=${DAPHNE_ACCESS_LOG:-0} celery_pool=${CELERY_POOL} celery_concurrency=${CELERY_CONCURRENCY} prefetch=${CELERY_PREFETCH_MULTIPLIER}"

# ── Migrations ──────────────────────────────────────────────────────
if [ "${ENABLE_MIGRATIONS_ON_START:-1}" = "1" ]; then
    echo "[render] Running migrations…"
    python manage.py migrate --noinput
else
    echo "[render] ENABLE_MIGRATIONS_ON_START=0 — skipping migrations."
fi

# ── Celery worker (background) ─────────────────────────────────────
# --pool=solo avoids prefork child-process overhead on small Render plans.
# --optimization=fair + prefetch=1 keep queue reservation pressure low.
# gossip/mingle/heartbeat are disabled to cut broker chatter and idle memory.
CELERY_PID=""
if [ "${ENABLE_CELERY_WORKER:-1}" = "1" ]; then
    echo "[render] Starting Celery worker (pool=${CELERY_POOL}, concurrency=${CELERY_CONCURRENCY})…"
    celery -A deltacrown worker \
        --loglevel=warning \
        --pool="${CELERY_POOL}" \
        --concurrency="${CELERY_CONCURRENCY}" \
        --optimization=fair \
        --prefetch-multiplier="${CELERY_PREFETCH_MULTIPLIER}" \
        --without-gossip \
        --without-mingle \
        --without-heartbeat \
        --max-memory-per-child=150000 \
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
if [ "${ENABLE_DISCORD_BOT:-0}" = "1" ] && [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "[render] Starting Discord bot…"
    python manage.py run_discord_bot &
    DISCORD_PID=$!
elif [ "${ENABLE_DISCORD_BOT:-0}" != "1" ]; then
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
# Keep connection lifetimes bounded so abandoned websocket/app state does not
# linger forever on memory-constrained plans.
PORT="${PORT:-8000}"
HTTP_TIMEOUT="${DAPHNE_HTTP_TIMEOUT:-60}"
DAPHNE_ARGS=(
    -b 0.0.0.0
    -p "$PORT"
    --http-timeout "$HTTP_TIMEOUT"
    --proxy-headers
    --websocket_connect_timeout "$DAPHNE_WS_CONNECT_TIMEOUT"
    --ping-interval "$DAPHNE_PING_INTERVAL"
    --ping-timeout "$DAPHNE_PING_TIMEOUT"
    --application-close-timeout "$DAPHNE_APP_CLOSE_TIMEOUT"
)

if [ -n "${DAPHNE_WEBSOCKET_TIMEOUT:-}" ]; then
    DAPHNE_ARGS+=(--websocket_timeout "${DAPHNE_WEBSOCKET_TIMEOUT}")
fi

echo "[render] Starting Daphne on port $PORT (http-timeout=${HTTP_TIMEOUT}s, ws_connect_timeout=${DAPHNE_WS_CONNECT_TIMEOUT}s, ping=${DAPHNE_PING_INTERVAL}/${DAPHNE_PING_TIMEOUT}s)…"
if [ "${DAPHNE_ACCESS_LOG:-0}" = "1" ]; then
    DAPHNE_ARGS+=(--access-log -)
fi

exec daphne "${DAPHNE_ARGS[@]}" deltacrown.asgi:application
