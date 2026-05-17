from django.contrib import admin
from django.urls import path

from apps.games.views.admin_maintenance import maintenance_panel

app_name = "maintenance"

urlpatterns = [
    path("", admin.site.admin_view(maintenance_panel), name="panel"),
]
