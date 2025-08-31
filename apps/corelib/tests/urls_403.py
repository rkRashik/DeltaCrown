from django.urls import path, include
from django.core.exceptions import PermissionDenied

def forbidden(_request):
    raise PermissionDenied("nope")

# Use the project's custom 403 handler
handler403 = "deltacrown.views.permission_denied_view"

urlpatterns = [
    # Test-only path that raises PermissionDenied
    path("forbidden/", forbidden),

    # IMPORTANT: include the real project URLs so navbar reverses work
    path("", include("deltacrown.urls")),
]
