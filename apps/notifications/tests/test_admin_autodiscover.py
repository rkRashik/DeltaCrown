import importlib
from django.contrib import admin
from apps.notifications.models import Notification

def test_notifications_admin_autodiscover_registers_model():
    # Should import without errors and register the model
    importlib.import_module("apps.notifications.admin")
    assert Notification in admin.site._registry
