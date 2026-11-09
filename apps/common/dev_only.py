"""Guard for development/QA pages that must not be public in production."""
from functools import wraps

from django.conf import settings
from django.http import Http404


def dev_only(view):
    """Serve the view when DEBUG is on or to signed-in staff; everyone else gets a 404."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if settings.DEBUG or (user is not None and user.is_active and user.is_staff):
            return view(request, *args, **kwargs)
        raise Http404
    return wrapper
