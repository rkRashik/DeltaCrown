"""
DRF Serializers for User Stats API

Phase 8, Epic 8.2: User Stats Service
Serializes UserStatsDTO for API responses.
"""

from rest_framework import serializers
from decimal import Decimal


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for UserStatsDTO.
    Full user statistics for a specific game.
    """
    user_id = serializers.IntegerField()
    game_slug = serializers.CharField(max_length=100)
    matches_played = serializers.IntegerField()
    matches_won = serializers.IntegerField()
    matches_lost = serializers.IntegerField()
    matches_drawn = serializers.IntegerField()
    tournaments_played = serializers.IntegerField()
    tournaments_won = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_kills = serializers.IntegerField()
    total_deaths = serializers.IntegerField()
    kd_ratio = serializers.DecimalField(max_digits=6, decimal_places=2)
    last_match_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class UserStatsSummarySerializer(serializers.Serializer):
    """
    Serializer for lightweight user stats summary.
    Used in list views and cards.
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField(max_length=150)
    game_slug = serializers.CharField(max_length=100)
    matches_played = serializers.IntegerField()
    matches_won = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    kd_ratio = serializers.DecimalField(max_digits=6, decimal_places=2)
    last_match_at = serializers.DateTimeField(allow_null=True)


class UserStatsListSerializer(serializers.Serializer):
    """
    Serializer for list of user stats across multiple games.
    """
    user_id = serializers.IntegerField()
    games = serializers.ListField(
        child=UserStatsSerializer(),
        help_text="User stats for each game"
    )
    total_matches = serializers.IntegerField()
    total_wins = serializers.IntegerField()
    overall_win_rate = serializers.FloatField()
