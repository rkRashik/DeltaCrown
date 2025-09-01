# apps/user_profile/admin/__init__.py
# Aggregate admin registrations for user_profile.
# Django autodiscover imports "apps.user_profile.admin" → this package,
# which imports submodules that perform ModelAdmin registrations.
from .base import *  # noqa
