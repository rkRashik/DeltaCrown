from django.urls import path
from .views import home, ui_showcase

urlpatterns = [
    path("", home, name="homepage"),
    path("ui/", ui_showcase, name="ui_showcase"),
]
