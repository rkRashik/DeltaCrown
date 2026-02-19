from django.urls import path
from .views import home, ui_showcase
from . import views

app_name = 'siteui'

urlpatterns = [
    path("", home, name="homepage"),
    path("", home, name="home"),  # Add alias for 'home' name
    path("ui/", ui_showcase, name="ui_showcase"),
    path("about/", views.about, name="about"),
    path("community/", views.community, name="community"),
    path("community/create-post/", views.handle_community_post_creation, name="create_community_post"),

    # Community JSON API (SPA feeds)
    path("community/api/feed/", views.community_api_feed, name="community_api_feed"),
    path("community/api/posts/create/", views.community_api_create_post, name="community_api_create_post"),
    path("community/api/posts/<int:post_id>/like/", views.community_api_like, name="community_api_like"),
    path("community/api/posts/<int:post_id>/comments/", views.community_api_comments, name="community_api_comments"),
    path("community/api/posts/<int:post_id>/delete/", views.community_api_delete_post, name="community_api_delete_post"),
    path("community/api/sidebar/", views.community_api_sidebar, name="community_api_sidebar"),
    path("community/api/user-teams/", views.community_api_user_teams, name="community_api_user_teams"),

    path("arena/", views.watch, name="arena"),
    path("watch/", views.watch, name="watch"),  # Backward compat redirect
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]
