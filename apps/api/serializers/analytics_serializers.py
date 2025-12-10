"""
Analytics API Serializers for Epic 8.5 - Advanced Analytics & Leaderboards.

Serializers for user/team analytics, leaderboards, and seasons.
"""

from rest_framework import serializers
from decimal import Decimal


class UserAnalyticsSerializer(serializers.Serializer):
    """Serializer for user analytics snapshots."""
    
    user_id = serializers.IntegerField()
    game_slug = serializers.CharField()
    mmr_snapshot = serializers.IntegerField()
    elo_snapshot = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    kda_ratio = serializers.DecimalField(max_digits=6, decimal_places=2)
    matches_last_7d = serializers.IntegerField()
    matches_last_30d = serializers.IntegerField()
    win_rate_7d = serializers.DecimalField(max_digits=5, decimal_places=2)
    win_rate_30d = serializers.DecimalField(max_digits=5, decimal_places=2)
    current_streak = serializers.IntegerField()
    longest_win_streak = serializers.IntegerField()
    tier = serializers.ChoiceField(choices=['bronze', 'silver', 'gold', 'diamond', 'crown'])
    percentile_rank = serializers.DecimalField(max_digits=5, decimal_places=2)
    recalculated_at = serializers.DateTimeField()


class TeamAnalyticsSerializer(serializers.Serializer):
    """Serializer for team analytics snapshots."""
    
    team_id = serializers.IntegerField()
    game_slug = serializers.CharField()
    elo_snapshot = serializers.IntegerField()
    elo_volatility = serializers.DecimalField(max_digits=6, decimal_places=2)
    avg_member_skill = serializers.DecimalField(max_digits=8, decimal_places=2)
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    win_rate_7d = serializers.DecimalField(max_digits=5, decimal_places=2)
    win_rate_30d = serializers.DecimalField(max_digits=5, decimal_places=2)
    synergy_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    activity_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    matches_last_7d = serializers.IntegerField()
    matches_last_30d = serializers.IntegerField()
    tier = serializers.ChoiceField(choices=['bronze', 'silver', 'gold', 'diamond', 'crown'])
    percentile_rank = serializers.DecimalField(max_digits=5, decimal_places=2)
    recalculated_at = serializers.DateTimeField()


class LeaderboardEntrySerializer(serializers.Serializer):
    """Serializer for leaderboard entries."""
    
    leaderboard_type = serializers.CharField()
    rank = serializers.IntegerField()
    reference_id = serializers.IntegerField()
    game_slug = serializers.CharField(required=False, allow_null=True)
    season_id = serializers.CharField(required=False, allow_null=True)
    score = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    payload = serializers.JSONField()
    computed_at = serializers.DateTimeField(required=False, allow_null=True)


class SeasonSerializer(serializers.Serializer):
    """Serializer for seasons."""
    
    season_id = serializers.CharField()
    name = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    is_active = serializers.BooleanField()
    decay_rules = serializers.JSONField()


class LeaderboardRefreshRequestSerializer(serializers.Serializer):
    """Serializer for leaderboard refresh requests."""
    
    leaderboard_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Optional list of specific leaderboard types to refresh"
    )
    force = serializers.BooleanField(
        default=False,
        help_text="Force immediate refresh even if recently updated"
    )
