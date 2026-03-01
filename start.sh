#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Celery Worker in the background..."
celery -A deltacrown worker -l info &

echo "Starting Discord Bot in the background..."
python manage.py run_discord_bot &

echo "Starting Django ASGI/Web Server..."
exec daphne deltacrown.asgi:application -b 0.0.0.0 -p "${PORT:-8000}"
