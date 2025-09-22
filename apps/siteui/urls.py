from django.urls import path
from .views import home, ui_showcase
from . import views

app_name = 'siteui'

urlpatterns = [
    path("", home, name="homepage"),
    path("ui/", ui_showcase, name="ui_showcase"),
    path("about/", views.about, name="about"),
    path("community/", views.community, name="community"),
    path("community/create-post/", views.handle_community_post_creation, name="create_community_post"),
    path("watch/", views.watch, name="watch"),
]
