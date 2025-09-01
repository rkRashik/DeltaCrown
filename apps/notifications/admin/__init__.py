# apps/notifications/admin/__init__.py
# Aggregates all admin registrations for notifications.
# Django’s autodiscover will import "apps.notifications.admin" -> this package,
# which immediately imports submodules that register ModelAdmins.
from .base import *  # noqa
