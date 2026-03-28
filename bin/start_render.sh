#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render.com startup script — runs all processes in a single container
#
#   1. Celery Worker   (background, solo pool — no subprocess fork)
#   2. Celery Beat     (background, if ENABLE_CELERY_BEAT=1)
#   3. Discord Bot     (background, only if token is set)
#   4. Daphne          (foreground — binds $PORT for Render health check)
#
# Render Free/Starter plans allow only 1 service, so we multiplex here.
# Set REDIS_URL (e.g. Upstash) and DISCORD_BOT_TOKEN in Render env vars.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

CELERY_POOL="${CELERY_POOL:-solo}"
CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-1}"
CELERY_PREFETCH_MULTIPLIER="${CELERY_PREFETCH_MULTIPLIER:-1}"
DAPHNE_WS_CONNECT_TIMEOUT="${DAPHNE_WEBSOCKET_CONNECT_TIMEOUT:-5}"
DAPHNE_PING_INTERVAL="${DAPHNE_PING_INTERVAL:-20}"
DAPHNE_PING_TIMEOUT="${DAPHNE_PING_TIMEOUT:-30}"
DAPHNE_APP_CLOSE_TIMEOUT="${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-5}"

echo "[render] Startup profile: migrations=${ENABLE_MIGRATIONS_ON_START:-1} celery=${ENABLE_CELERY_WORKER:-1} beat=${ENABLE_CELERY_BEAT:-0} discord=${ENABLE_DISCORD_BOT:-1} access_log=${DAPHNE_ACCESS_LOG:-0} celery_pool=${CELERY_POOL} celery_concurrency=${CELERY_CONCURRENCY} prefetch=${CELERY_PREFETCH_MULTIPLIER}"

probe_database_url() {
    local target_url="$1"
    DATABASE_URL_PROBE="$target_url" python - <<'PY'
import os
import sys

import psycopg2

url = os.environ.get("DATABASE_URL_PROBE", "")
try:
    conn = psycopg2.connect(url, connect_timeout=5)
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    conn.close()
except Exception as exc:
    print(f"[render] DB probe failed: {exc}", file=sys.stderr)
    sys.exit(1)
PY
}

is_supabase_pooler_6543_url() {
    local target_url="$1"
    case "$target_url" in
        *".pooler.supabase.com:6543/"*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

derive_supabase_direct_url_from_pooler() {
    local current_url="$1"
    DATABASE_URL_PROBE="$current_url" python - <<'PY'
import os
from urllib.parse import quote, unquote, urlsplit, urlunsplit

url = os.environ.get("DATABASE_URL_PROBE", "")
try:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    username = parsed.username or ""
    if not host.endswith(".pooler.supabase.com") or not username.startswith("postgres."):
        print("")
        raise SystemExit(0)

    project_ref = username.split(".", 1)[1]
    password = parsed.password or ""
    auth = "postgres"
    if password:
        auth += ":" + quote(unquote(password), safe="")

    direct_host = f"db.{project_ref}.supabase.co"
    netloc = f"{auth}@{direct_host}:5432"
    print(urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)))
except Exception:
    print("")
PY
}

build_supabase_fallback_url() {
    local current_url="$1"
    local fallback_url="${SUPABASE_DIRECT_DATABASE_URL:-}"
    if [ -z "$fallback_url" ]; then
        fallback_url="$(derive_supabase_direct_url_from_pooler "$current_url")"
    fi
    if [ -z "$fallback_url" ]; then
        fallback_url="$(printf '%s' "$current_url" | sed 's/:6543\//:5432\//')"
    fi
    if [ "$fallback_url" = "$current_url" ]; then
        printf ''
        return
    fi
    printf '%s' "$fallback_url"
}

select_database_url_for_startup() {
    local current_url="${DATABASE_URL:-}"
    if [ -z "$current_url" ]; then
        return
    fi
    if [ "${SUPABASE_POOLER_PORT_FALLBACK:-1}" != "1" ]; then
        return
    fi
    if ! is_supabase_pooler_6543_url "$current_url"; then
        return
    fi

    local fallback_url
    fallback_url="$(build_supabase_fallback_url "$current_url")"

    local prefer_direct="${SUPABASE_PREFER_DIRECT_CONNECTION:-1}"
    local primary_candidate="$current_url"
    local secondary_candidate="$fallback_url"
    if [ "$prefer_direct" = "1" ] && [ -n "$fallback_url" ]; then
        primary_candidate="$fallback_url"
        secondary_candidate="$current_url"
    fi

    for candidate in "$primary_candidate" "$secondary_candidate"; do
        if [ -z "$candidate" ]; then
            continue
        fi
        echo "[render] Probing candidate DATABASE_URL endpoint…"
        if probe_database_url "$candidate"; then
            if [ "$candidate" != "$current_url" ]; then
                export DATABASE_URL="$candidate"
                echo "[render] Switched DATABASE_URL endpoint for startup readiness."
            else
                echo "[render] Keeping current DATABASE_URL endpoint."
            fi
            return
        fi
    done

    echo "[render] No database candidate passed startup probe; keeping existing DATABASE_URL."
}

run_migrations_with_retry() {
    local max_attempts="${DB_MIGRATION_MAX_ATTEMPTS:-3}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        echo "[render] Running migrations (attempt ${attempt}/${max_attempts})…"
        if python manage.py migrate --noinput; then
            echo "[render] Migrations completed successfully."
            return 0
        fi

        echo "[render] Migration attempt ${attempt} failed."
        local current_url="${DATABASE_URL:-}"
        if is_supabase_pooler_6543_url "$current_url"; then
            local fallback_url
            fallback_url="$(build_supabase_fallback_url "$current_url")"
            if [ -n "$fallback_url" ] && [ "$fallback_url" != "$current_url" ]; then
                echo "[render] Trying migration fallback endpoint…"
                if probe_database_url "$fallback_url"; then
                    export DATABASE_URL="$fallback_url"
                    echo "[render] Switched DATABASE_URL for migration retry."
                else
                    echo "[render] Migration fallback endpoint probe failed."
                fi
            fi
        fi

        if [ "$attempt" -lt "$max_attempts" ]; then
            sleep 2
        fi
        attempt=$((attempt + 1))
    done

    return 1
}

select_database_url_for_startup

# ── Collect static files ────────────────────────────────────────────
echo "[render] Collecting static files…"
python manage.py collectstatic --noinput

# ── Run migrations ──────────────────────────────────────────────────
if [ "${ENABLE_MIGRATIONS_ON_START:-1}" = "1" ]; then
    if ! run_migrations_with_retry; then
        echo "[render] Migrations failed after all retry attempts."
        exit 1
    fi
else
    echo "[render] ENABLE_MIGRATIONS_ON_START=0 — skipping migrations."
fi

# ── Start Celery worker (background) ───────────────────────────────
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
    [ -n "$BEAT_PID" ] && kill "$BEAT_PID" 2>/dev/null || true
    [ -n "$DISCORD_PID" ] && kill "$DISCORD_PID" 2>/dev/null || true
    wait
    echo "[render] All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Start web server (foreground) ───────────────────────────────────
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
