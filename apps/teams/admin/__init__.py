# apps/teams/admin/__init__.py
"""
DeltaCrown — Teams admin (package)

We split the legacy admin.py into submodules:
  - teams.py   : ModelAdmin registrations
  - exports.py : CSV export action
  - inlines.py : Inline classes attached to TeamAdmin
"""

# Ensure ModelAdmin registration and actions load at import-time
from .teams import *    # noqa: F401,F403
from .exports import *  # noqa: F401,F403
from .inlines import *  # noqa: F401,F403
