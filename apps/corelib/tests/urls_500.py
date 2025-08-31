from django.urls import path, include

def boom(request):
    # Deliberately raise to exercise the 500 handler
    raise Exception("boom")

# Use the project's custom 500 handler for this test
handler500 = "deltacrown.views.server_error_view"

urlpatterns = [
    path("boom/", boom),

    # IMPORTANT: include the real project URLs so navbar reverses work
    # (tournaments, teams, profiles, notifications, etc.)
    path("", include("deltacrown.urls")),
]
