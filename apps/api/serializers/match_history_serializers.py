"""
DRF Serializers for Match History API

Phase 8, Epic 8.4: Match History Engine
Serializes match history DTOs for API responses with filtering and pagination.
"""

from rest_framework import serializers


class UserMatchHistorySerializer(serializers.Serializer):
    """
    Serializer for UserMatchHistoryDTO.
    Complete match history entry for a user with stats and opponent info.
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField(max_length=150)
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    tournament_name = serializers.CharField(max_length=255)
    game_slug = serializers.CharField(max_length=100)
    is_winner = serializers.BooleanField()
    is_draw = serializers.BooleanField()
    score_summary = serializers.CharField(max_length=100, allow_blank=True)
    opponent_user_id = serializers.IntegerField(allow_null=True)
    opponent_name = serializers.CharField(max_length=255)
    kills = serializers.IntegerField()
    deaths = serializers.IntegerField()
    assists = serializers.IntegerField()
    had_dispute = serializers.BooleanField()
    is_forfeit = serializers.BooleanField()
    completed_at = serializers.DateTimeField()


class TeamMatchHistorySerializer(serializers.Serializer):
    """
    Serializer for TeamMatchHistoryDTO.
    Complete match history entry for a team with ELO tracking.
    """
    team_id = serializers.IntegerField()
    team_name = serializers.CharField(max_length=255)
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    tournament_name = serializers.CharField(max_length=255)
    game_slug = serializers.CharField(max_length=100)
    is_winner = serializers.BooleanField()
    is_draw = serializers.BooleanField()
    score_summary = serializers.CharField(max_length=100, allow_blank=True)
    opponent_team_id = serializers.IntegerField(allow_null=True)
    opponent_team_name = serializers.CharField(max_length=255)
    elo_before = serializers.IntegerField(allow_null=True)
    elo_after = serializers.IntegerField(allow_null=True)
    elo_change = serializers.IntegerField()
    had_dispute = serializers.BooleanField()
    is_forfeit = serializers.BooleanField()
    completed_at = serializers.DateTimeField()


class MatchHistoryFilterSerializer(serializers.Serializer):
    """
    Serializer for match history query filters.
    Validates request query parameters for history endpoints.
    """
    game_slug = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Filter by game (e.g., 'valorant', 'csgo')"
    )
    tournament_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Filter by tournament ID"
    )
    from_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter by date range start (ISO 8601)"
    )
    to_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter by date range end (ISO 8601)"
    )
    only_wins = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Show only wins"
    )
    only_losses = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Show only losses"
    )
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        help_text="Results per page (1-100)"
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text="Offset for pagination"
    )
    
    def validate(self, data):
        """
        Validate filter combination.
        
        - only_wins and only_losses cannot both be True
        - from_date must be before to_date if both provided
        """
        only_wins = data.get('only_wins', False)
        only_losses = data.get('only_losses', False)
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if only_wins and only_losses:
            raise serializers.ValidationError(
                "only_wins and only_losses cannot both be True"
            )
        
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                "from_date must be before to_date"
            )
        
        return data


class MatchHistoryResponseSerializer(serializers.Serializer):
    """
    Paginated response wrapper for match history.
    Includes results, total count, and pagination metadata.
    """
    results = serializers.ListField(
        child=serializers.DictField(),  # Will be UserMatchHistorySerializer or TeamMatchHistorySerializer
        help_text="List of match history entries"
    )
    count = serializers.IntegerField(
        help_text="Total number of matching entries"
    )
    limit = serializers.IntegerField(
        help_text="Results per page"
    )
    offset = serializers.IntegerField(
        help_text="Current offset"
    )
    has_next = serializers.BooleanField(
        help_text="Whether there are more results"
    )
    has_previous = serializers.BooleanField(
        help_text="Whether there are previous results"
    )
