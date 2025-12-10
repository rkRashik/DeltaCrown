"""
Team Stats API Serializers

Phase 8, Epic 8.3: Team Stats & Ranking System
DRF serializers for team stats API endpoints.
"""

from rest_framework import serializers


class TeamStatsSerializer(serializers.Serializer):
    """
    Serializer for TeamStatsDTO.
    
    Used for GET /api/stats/v1/teams/{team_id}/stats/{game_slug}/
    """
    
    team_id = serializers.IntegerField(read_only=True)
    game_slug = serializers.CharField(read_only=True)
    matches_played = serializers.IntegerField(read_only=True)
    matches_won = serializers.IntegerField(read_only=True)
    matches_lost = serializers.IntegerField(read_only=True)
    matches_drawn = serializers.IntegerField(read_only=True)
    tournaments_played = serializers.IntegerField(read_only=True)
    tournaments_won = serializers.IntegerField(read_only=True)
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    last_match_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TeamRankingSerializer(serializers.Serializer):
    """
    Serializer for TeamRankingDTO.
    
    Used for GET /api/stats/v1/teams/{team_id}/ranking/{game_slug}/
    """
    
    team_id = serializers.IntegerField(read_only=True)
    game_slug = serializers.CharField(read_only=True)
    elo_rating = serializers.IntegerField(read_only=True)
    peak_elo = serializers.IntegerField(read_only=True)
    games_played = serializers.IntegerField(read_only=True)
    wins = serializers.IntegerField(read_only=True)
    losses = serializers.IntegerField(read_only=True)
    draws = serializers.IntegerField(read_only=True)
    rank = serializers.IntegerField(read_only=True, allow_null=True)
    last_updated = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class TeamStatsSummarySerializer(serializers.Serializer):
    """
    Serializer for TeamStatsSummaryDTO.
    
    Used for GET /api/stats/v1/teams/{team_id}/summary/
    """
    
    team_id = serializers.IntegerField(read_only=True)
    game_slug = serializers.CharField(read_only=True, allow_null=True)
    total_matches = serializers.IntegerField(read_only=True)
    total_wins = serializers.IntegerField(read_only=True)
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_tournaments = serializers.IntegerField(read_only=True)
    elo_rating = serializers.IntegerField(read_only=True, allow_null=True)
    rank = serializers.IntegerField(read_only=True, allow_null=True)
    last_played = serializers.DateTimeField(read_only=True, allow_null=True)


class GameTeamLeaderboardEntrySerializer(serializers.Serializer):
    """
    Serializer for leaderboard entries.
    
    Used for GET /api/stats/v1/leaderboards/teams/{game_slug}/
    Combines TeamRankingDTO with team name for display.
    """
    
    team_id = serializers.IntegerField(read_only=True)
    team_name = serializers.CharField(read_only=True)
    elo_rating = serializers.IntegerField(read_only=True)
    peak_elo = serializers.IntegerField(read_only=True)
    games_played = serializers.IntegerField(read_only=True)
    wins = serializers.IntegerField(read_only=True)
    losses = serializers.IntegerField(read_only=True)
    draws = serializers.IntegerField(read_only=True)
    rank = serializers.IntegerField(read_only=True, allow_null=True)
    last_updated = serializers.DateTimeField(read_only=True)
