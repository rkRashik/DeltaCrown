"""
User Profile Views Package

Legacy views remain in legacy_views.py (monolithic file).
New V2 views are in fe_v2.py.
"""
# Re-export all legacy views from legacy_views.py for backward compatibility
from apps.user_profile.views.legacy_views import *  # noqa

# V2 views are imported separately in urls.py
