"""
User Profile Signals

Imports all signal handlers.
"""

# Legacy signals
from apps.user_profile.signals.legacy_signals import *  # noqa

# UP-M2 activity signals
from apps.user_profile.signals.activity_signals import *  # noqa

# Follow notification signals (PHASE 9: Follow System Completion)
from apps.user_profile.signals.follow_signals import *  # noqa
