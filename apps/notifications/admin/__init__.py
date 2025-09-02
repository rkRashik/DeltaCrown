# apps/notifications/admin/__init__.py
"""
DeltaCrown — Notifications admin (package)

We split the legacy admin.py into submodules:
  - notifications.py : ModelAdmin, registrations
  - exports.py       : CSV export action

Importing this package triggers all registrations at import-time.
Downstream code can still `import apps.notifications.admin` safely.
"""

# Import submodules to ensure ModelAdmin registration runs at import-time
from .notifications import *  # noqa: F401,F403
from .exports import *        # noqa: F401,F403
