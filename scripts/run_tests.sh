#!/usr/bin/env bash
# Test runner script for Linux/macOS
# Loads .env.test and runs Phase 1 team creation API tests

set -e

echo ""
echo "=== DeltaCrown Phase 1 Test Runner ==="

# Load .env.test if it exists
ENV_TEST_FILE="$(dirname "$0")/../.env.test"
if [ -f "$ENV_TEST_FILE" ]; then
    echo "Loading environment from .env.test..."
    export $(grep -v '^#' "$ENV_TEST_FILE" | xargs)
    echo "  Environment loaded"
else
    echo "No .env.test file found at $ENV_TEST_FILE"
fi

# Validate DATABASE_URL_TEST is set
if [ -z "$DATABASE_URL_TEST" ]; then
    echo "ERROR: DATABASE_URL_TEST environment variable is not set"
    echo "Please create .env.test with DATABASE_URL_TEST or set it manually"
    exit 1
fi

echo "DATABASE_URL_TEST is set"

# Set Django settings module
export DJANGO_SETTINGS_MODULE="deltacrown.settings_test"
echo "Using settings module: deltacrown.settings_test"

# Run Django system check
echo ""
echo "Running Django system check..."
python manage.py check

# Run pytest
echo ""
echo "Running Phase 1 tests..."
pytest apps/organizations/tests/test_team_creation_api.py -v --tb=short --reuse-db

echo ""
echo "=== Test Run Complete ==="
