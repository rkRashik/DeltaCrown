#!/usr/bin/env python
"""
Quick test runner for tournament frontend tests
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings

if __name__ == '__main__':
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    # Run Sprint 2 and Sprint 4 tests
    failures = test_runner.run_tests([
        'apps.tournaments.tests.test_player_dashboard',
        'apps.tournaments.tests.test_leaderboards',
    ])
    
    sys.exit(bool(failures))
