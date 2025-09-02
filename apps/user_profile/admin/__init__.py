# apps/user_profile/admin/__init__.py
"""
DeltaCrown — User Profile admin (package)

We split the legacy admin.py into submodules:
  - users.py   : ModelAdmin registrations
  - exports.py : CSV export action

Importing this package triggers registrations at import time so that
`import apps.user_profile.admin` continues to work everywhere.
"""

# Ensure ModelAdmin registration and actions load at import-time
from .users import *    # noqa: F401,F403
from .exports import *  # noqa: F401,F403
