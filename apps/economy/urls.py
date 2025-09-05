# apps/economy/urls.py
from django.urls import path
from .views.wallet import wallet_view

app_name = "economy"

urlpatterns = [
    path("wallet/", wallet_view, name="wallet"),
]
