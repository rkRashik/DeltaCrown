from django.urls import include, path

from apps.user_profile.views.oauth_epic_api import EpicCallbackView, EpicLoginRedirectView
from apps.user_profile.views.oauth_riot_api import RiotCallbackView, RiotLoginRedirectView
from apps.user_profile.views.oauth_steam_api import SteamCallbackView, SteamLoginRedirectView


user_profile_patterns = (
    [
        path("profile/api/oauth/riot/login/", RiotLoginRedirectView.as_view(), name="riot_oauth_login"),
        path("profile/api/oauth/riot/callback/", RiotCallbackView.as_view(), name="riot_oauth_callback"),
        path("profile/api/oauth/steam/login/", SteamLoginRedirectView.as_view(), name="steam_openid_login"),
        path("profile/api/oauth/steam/callback/", SteamCallbackView.as_view(), name="steam_openid_callback"),
        path("profile/api/oauth/epic/login/", EpicLoginRedirectView.as_view(), name="epic_oauth_login"),
        path("profile/api/oauth/epic/callback/", EpicCallbackView.as_view(), name="epic_oauth_callback"),
    ],
    "user_profile",
)


urlpatterns = [
    path("", include(user_profile_patterns, namespace="user_profile")),
]