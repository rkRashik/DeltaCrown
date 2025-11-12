#!/bin/bash
# Smoke Tests Local Runner
# Run: bash scripts/smoke_local_run.sh

set -e

echo "==============================================="
echo "DeltaCrown Smoke Tests - Local Runner"
echo "==============================================="
echo ""

# Set environment variables (all enforcement OFF by default)
export MODERATION_OBSERVABILITY_ENABLED=false
export PURCHASE_ENFORCEMENT_ENABLED=false

echo "Environment Configuration:"
echo "  MODERATION_OBSERVABILITY_ENABLED=$MODERATION_OBSERVABILITY_ENABLED"
echo "  PURCHASE_ENFORCEMENT_ENABLED=$PURCHASE_ENFORCEMENT_ENABLED"
echo ""

# Run smoke tests
echo "Running 12 smoke tests..."
pytest -v -m smoke tests/smoke/test_end_to_end_paths.py

echo ""
echo "==============================================="
echo "✅ Smoke tests complete"
echo "==============================================="
