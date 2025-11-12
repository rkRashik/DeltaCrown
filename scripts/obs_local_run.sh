#!/bin/bash
# Observability Tests Local Runner
# Run: bash scripts/obs_local_run.sh

set -e

echo "================================================"
echo "DeltaCrown Observability Tests - Local Runner"
echo "================================================"
echo ""

# Set environment variables
export MODERATION_OBSERVABILITY_ENABLED=false  # Default OFF
export MODERATION_CACHE_ENABLED=true
export MODERATION_CACHE_TTL_SECONDS=60
export MODERATION_SAMPLING_RATE=0.10

echo "Environment Configuration:"
echo "  MODERATION_OBSERVABILITY_ENABLED=$MODERATION_OBSERVABILITY_ENABLED"
echo "  MODERATION_CACHE_ENABLED=$MODERATION_CACHE_ENABLED"
echo "  MODERATION_CACHE_TTL_SECONDS=$MODERATION_CACHE_TTL_SECONDS"
echo "  MODERATION_SAMPLING_RATE=$MODERATION_SAMPLING_RATE"
echo ""

# Run tests
echo "Running 12 observability tests..."
pytest -v -m observability tests/observability/test_sanction_cache_and_metrics.py

echo ""
echo "================================================"
echo "✅ Observability tests complete"
echo "================================================"
