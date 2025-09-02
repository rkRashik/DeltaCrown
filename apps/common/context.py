from __future__ import annotations
from django.conf import settings

def ui_settings(request):
    """
    Provide lightweight UI flags to templates.
    """
    return {
        "STATIC_VERSION": getattr(settings, "STATIC_VERSION", "1"),
        "USE_BUILD_ASSETS": getattr(settings, "USE_BUILD_ASSETS", False),
    }
