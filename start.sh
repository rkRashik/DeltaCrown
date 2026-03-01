#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Celery Worker (Memory Optimized) in the background..."
# --concurrency=1 forces Celery to use only 1 process to prevent RAM exhaustion
celery -A deltacrown worker -l info --concurrency=1 &

echo "Starting Discord Bot in the background..."
python manage.py run_discord_bot &

echo "Starting Django ASGI/Web Server..."
exec daphne deltacrown.asgi:application -b 0.0.0.0 -p "${PORT:-8000}"
