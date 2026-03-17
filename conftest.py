# Root conftest.py — ensures proper test collection and filtering.
# Place at project root so pytest discovers it before any test directories.

import os
import sys

# Import Redis fixtures for Module 6.8 rate limit tests
pytest_plugins = ['tests.redis_fixtures']

# ── Apply model compatibility shims GLOBALLY ──
# Must run before ANY test module imports so patches cover apps/ AND tests/.
from tests._model_shims import apply_all_patches
apply_all_patches()

# ── Collection exclusions ──
collect_ignore_glob = [
    "backups/*",
    "scripts/_archive/*",
    "test_results*.txt",
]
