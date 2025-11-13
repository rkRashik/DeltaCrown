"""
URL Configuration for Admin Read-Only API.

Maps admin API endpoints. All require staff authentication.
"""

from django.urls import path
from apps.admin.api import webhooks, leaderboards, tournament_ops

app_name = "admin_api"

urlpatterns = [
    # Webhook inspection endpoints
    path(
        "webhooks/deliveries",
        webhooks.webhook_deliveries_list,
        name="webhook_deliveries_list"
    ),
    path(
        "webhooks/deliveries/<uuid:webhook_id>",
        webhooks.webhook_delivery_detail,
        name="webhook_delivery_detail"
    ),
    path(
        "webhooks/statistics",
        webhooks.webhook_statistics,
        name="webhook_statistics"
    ),
    path(
        "webhooks/circuit-breaker",
        webhooks.circuit_breaker_status,
        name="circuit_breaker_status"
    ),
    
    # Leaderboards inspection endpoints (Phase E)
    path(
        "leaderboards/tournaments/<int:tournament_id>/",
        leaderboards.tournament_leaderboard_debug,
        name="tournament_leaderboard_debug"
    ),
    path(
        "leaderboards/snapshots/<int:snapshot_id>/",
        leaderboards.snapshot_detail,
        name="snapshot_detail"
    ),
    path(
        "leaderboards/scoped/<str:scope>/",
        leaderboards.scoped_leaderboard_debug,
        name="scoped_leaderboard_debug"
    ),
    
    # Tournament Operations inspection endpoints (Phase E Section 9)
    path(
        "tournaments/<int:tournament_id>/payments/",
        tournament_ops.tournament_payments,
        name="tournament_payments"
    ),
    path(
        "tournaments/<int:tournament_id>/matches/",
        tournament_ops.tournament_matches,
        name="tournament_matches"
    ),
    path(
        "tournaments/<int:tournament_id>/disputes/",
        tournament_ops.tournament_disputes,
        name="tournament_disputes"
    ),
]
