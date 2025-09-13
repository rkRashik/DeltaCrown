from django.urls import path
from .views import home, ui_showcase
from . import views

urlpatterns = [
    path("", home, name="homepage"),
    path("ui/", ui_showcase, name="ui_showcase"),
    path("about/", views.about, name="about"),
    path("community/", views.community, name="community"),
    path("watch/", views.watch, name="watch"),
]
