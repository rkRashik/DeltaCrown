#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Render Celery worker — 512 MB Starter tier
#
# Start command to use in the Render Dashboard (worker service):
#   bash bin/start_worker.sh
#
# Memory controls:
#   --max-tasks-per-child   Recycle worker process after N tasks (default 50).
#                           Prevents slow Python heap fragmentation from
#                           accumulating across many task executions.
#   --max-memory-per-child  Hard RSS ceiling in KB (default 150 MB).
#                           Worker process is restarted if it exceeds this
#                           before finishing the current task batch.
#   --concurrency=1         Single thread — single-core Starter tier only.
#
# Overridable via env:
#   CELERY_MAX_TASKS_PER_CHILD    (default: 50)
#   CELERY_MAX_MEMORY_PER_CHILD   (default: 150000  = 150 MB in KB)
#   CELERY_LOG_LEVEL              (default: info)
#
# Beat is intentionally excluded; use lifecycle_cron HTTP endpoint instead.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

MAX_TASKS="${CELERY_MAX_TASKS_PER_CHILD:-50}"
MAX_MEM="${CELERY_MAX_MEMORY_PER_CHILD:-150000}"
LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

echo "[worker] Starting Celery worker: concurrency=1 max-tasks=${MAX_TASKS} max-mem=${MAX_MEM}KB"

exec celery -A deltacrown worker \
    --loglevel="${LOG_LEVEL}" \
    --concurrency=1 \
    --max-tasks-per-child="${MAX_TASKS}" \
    --max-memory-per-child="${MAX_MEM}" \
    -Q celery
