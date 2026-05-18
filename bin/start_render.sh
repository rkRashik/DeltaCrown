#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup script — Daphne only
#
# Migrations and other startup jobs are intentionally disabled here.
# Use release command/manual operations for schema or background workers.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

DAPHNE_WS_CONNECT_TIMEOUT="${DAPHNE_WEBSOCKET_CONNECT_TIMEOUT:-5}"
DAPHNE_PING_INTERVAL="${DAPHNE_PING_INTERVAL:-20}"
DAPHNE_PING_TIMEOUT="${DAPHNE_PING_TIMEOUT:-30}"
DAPHNE_APP_CLOSE_TIMEOUT="${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-5}"

echo "[render] Startup profile: daphne_only=1 access_log=${DAPHNE_ACCESS_LOG:-0}"

# ── Start web server (foreground) ───────────────────────────────────
# HTTP timeout: 3600 s (1 h) default — sufficient for all normal requests.
# SSE is disabled by default (NOTIFICATIONS_SSE_ENABLED=0), so 86400 is not
# needed.  Set DAPHNE_HTTP_TIMEOUT=86400 only when enabling long-lived SSE.
PORT="${PORT:-8000}"
HTTP_TIMEOUT="${DAPHNE_HTTP_TIMEOUT:-3600}"
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
