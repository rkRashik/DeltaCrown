import importlib
from django.contrib import admin
from apps.user_profile.models import UserProfile

def test_admin_autodiscover_imports_user_profile_admin():
    importlib.import_module("apps.user_profile.admin")
    assert UserProfile in admin.site._registry
