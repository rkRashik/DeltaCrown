#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup — Daphne only
#
# Migrations are intentionally NOT run during boot.
# Use a separate release command/manual step for schema changes.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

DAPHNE_WS_CONNECT_TIMEOUT="${DAPHNE_WEBSOCKET_CONNECT_TIMEOUT:-5}"
DAPHNE_PING_INTERVAL="${DAPHNE_PING_INTERVAL:-20}"
DAPHNE_PING_TIMEOUT="${DAPHNE_PING_TIMEOUT:-30}"
DAPHNE_APP_CLOSE_TIMEOUT="${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-5}"

echo "[render] Startup profile: daphne_only=1 access_log=${DAPHNE_ACCESS_LOG:-0}"

# ── Daphne (foreground) ────────────────────────────────────────────
# Keep websocket lifetimes bounded; allow long-lived HTTP for SSE streams.
PORT="${PORT:-8000}"
HTTP_TIMEOUT="${DAPHNE_HTTP_TIMEOUT:-86400}"
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
