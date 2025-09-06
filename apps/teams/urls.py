from django.urls import path

# Import modules in a defensive way to avoid import-time AttributeError
from . import views as _views
try:
    from .views.public import team_list as _team_list
except Exception:
    _team_list = None
try:
    from .views.public import leave_team_view as _leave_team_by_id
except Exception:
    _leave_team_by_id = None
try:
    from .views import manage as _manage_views
except Exception:
    _manage_views = None
try:
    from .views import token as _token_views
except Exception:
    _token_views = None
try:
    from .views import presets as _presets_views
except Exception:
    _presets_views = None

# New public-by-slug page
try:
    from .views.public_team import team_public_by_slug as _team_public_by_slug
except Exception:
    _team_public_by_slug = None

app_name = "teams"
urlpatterns = []

def _add(view, route, name):
    if callable(view):
        urlpatterns.append(path(route, view, name=name))

# New: public page by (game, slug)
_add(_team_public_by_slug, "<str:game>/<slug:slug>/", "public_by_slug")

# Index
_add(_team_list, "", "index")

# Invites (token-based accept/decline)
if _token_views:
    _add(getattr(_token_views, "accept_invite_view", None), "invites/<str:token>/accept/", "accept_invite")
_add(getattr(_views, "my_invites", None), "invites/", "my_invites")
_add(getattr(_views, "decline_invite_view", None), "invites/<str:token>/decline/", "decline_invite")

# Quick create & detail
_add(getattr(_views, "create_team_quick", None), "create-quick/", "create_quick")
_add(getattr(_views, "team_detail", None), "<int:team_id>/", "detail")

# Member management by team_id
_add(getattr(_views, "invite_member_view", None), "<int:team_id>/invite/", "invite_member")
_add(_leave_team_by_id, "<int:team_id>/leave/", "leave_team")

# Optional tag-based routes (leave/transfer) — add only if they exist
if _manage_views:
    _add(getattr(_manage_views, "leave_team_view", None), "<str:tag>/leave/", "leave")
    _add(getattr(_manage_views, "transfer_captain_view", None), "<str:tag>/transfer/", "transfer")

# Presets (optional)
if _presets_views:
    _add(getattr(_presets_views, "my_presets", None), "presets/", "my_presets")
    _add(getattr(_presets_views, "delete_preset", None), "presets/<str:kind>/<int:preset_id>/delete/", "delete_preset")
