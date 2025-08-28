from django.urls import path
from . import views

app_name = "tournaments"

urlpatterns = [
    path("<slug:slug>/register/", views.register_view, name="register"),
    path("<slug:slug>/register/success/", views.register_success, name="register_success"),
]
