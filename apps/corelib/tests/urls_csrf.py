from django.urls import path, include
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse

@csrf_protect
def needs_csrf(request):
    if request.method == "POST":
        return HttpResponse("OK")
    return HttpResponse("GET OK")

# CSRF failures use templates/403_csrf.html automatically
handler403 = "deltacrown.views.permission_denied_view"

urlpatterns = [
    # Test-only path that requires CSRF on POST
    path("needs-csrf/", needs_csrf),

    # IMPORTANT: include the real project URLs so navbar reverses work
    path("", include("deltacrown.urls")),
]
