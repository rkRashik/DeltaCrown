"""
User Profile Views Package

Legacy views remain in legacy_views.py (monolithic file).
New V2 views are in fe_v2.py.
"""
import os

# Re-export all legacy views from legacy_views.py for backward compatibility.
# Minimal OAuth test mode loads targeted view modules directly and skips the
# broader legacy dependency graph.
if os.environ.get("DELTA_MINIMAL_TEST_APPS") != "1":
	from apps.user_profile.views.legacy_views import *  # noqa

# V2 views are imported separately in urls.py
