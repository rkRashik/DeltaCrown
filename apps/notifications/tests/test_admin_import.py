import importlib
from django.contrib import admin
from apps.notifications.models import Notification

def test_admin_autodiscover_imports_notifications_admin():
    importlib.import_module("apps.notifications.admin")
    assert Notification in admin.site._registry
