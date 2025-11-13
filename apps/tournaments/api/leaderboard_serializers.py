"""
Milestone E: Leaderboard & Standings Serializers

DRF serializers for leaderboard operations with comprehensive validation.

Serializers:
1. LeaderboardEntrySerializer - Individual leaderboard entry (BR/series)
2. BRLeaderboardSerializer - Full BR leaderboard response
3. SeriesSummarySerializer - Series summary response (Best-of-X)
4. PlacementOverrideSerializer - Staff placement override request

Endpoints:
- GET /api/tournaments/{id}/leaderboard/ - BR standings
- GET /api/tournaments/{id}/series/{match_id}/ - Series summary
- POST /api/tournaments/{id}/override-placement/ - Staff override

Planning Documents:
- Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md
- Documents/ExecutionPlan/MILESTONES_E_F_STATUS.md
"""

from rest_framework import serializers
from apps.tournaments.models import Tournament, Registration, TournamentResult


class LeaderboardEntrySerializer(serializers.Serializer):
    """
    Individual leaderboard entry (BR or series-based).
    
    Used in both BR leaderboards and series summaries.
    
    PII Discipline: IDs-only responses (no display names, emails, usernames).
    Clients should resolve participant_id to display names via separate profile API.
    """
    
    rank = serializers.IntegerField(
        help_text="Placement rank (1=1st place, 2=2nd place, etc.)"
    )
    
    participant_id = serializers.IntegerField(
        help_text="Registration ID (resolve to display name via profile API)"
    )
    
    team_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Team ID if team registration (resolve via team API)"
    )
    
    # BR-specific fields
    total_points = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Total points across all matches (BR)"
    )
    
    total_kills = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Total kills across all matches (BR)"
    )
    
    best_placement = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Best placement achieved (1=winner, lower is better)"
    )
    
    avg_placement = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Average placement across matches"
    )
    
    matches_played = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Number of matches played"
    )
    
    # Series-specific fields
    wins = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Number of wins in series"
    )
    
    losses = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Number of losses in series"
    )
    
    series_score = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Series score string (e.g., '2-1', '3-0')"
    )
    
    # Override metadata
    is_override = serializers.BooleanField(
        default=False,
        help_text="Whether placement was manually overridden by staff"
    )


class BRLeaderboardSerializer(serializers.Serializer):
    """
    BR leaderboard response (Free Fire, PUBG Mobile).
    
    Endpoint: GET /api/tournaments/{id}/leaderboard/?match_ids=1,2,3
    
    PII Discipline: IDs-only responses. No tournament names or participant names.
    Clients resolve IDs to human-readable labels via metadata APIs.
    """
    
    tournament_id = serializers.IntegerField(
        help_text="Tournament ID (resolve to name via tournament metadata API)"
    )
    
    game_slug = serializers.CharField(
        help_text="Game slug (e.g., 'free-fire', 'pubg-mobile')"
    )
    
    match_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Match IDs included in this leaderboard"
    )
    
    standings = LeaderboardEntrySerializer(
        many=True,
        help_text="Ranked participants with BR stats"
    )
    
    total_participants = serializers.IntegerField(
        help_text="Total number of participants"
    )
    
    generated_at = serializers.DateTimeField(
        help_text="Timestamp when leaderboard was generated"
    )


class SeriesSummarySerializer(serializers.Serializer):
    """
    Series summary response (Valorant, CS2, Dota2, MLBB, CODM).
    
    Endpoint: GET /api/tournaments/{id}/series/{match_id}/
    
    Aggregates Best-of-1/3/5/7 series results.
    """
    
    series_id = serializers.CharField(
        help_text="Series identifier (match ID or series UUID)"
    )
    
    format = serializers.CharField(
        help_text="Series format (e.g., 'Best of 3', 'Best of 5')"
    )
    
    series_winner_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Winner registration ID (null if incomplete)"
    )
    
    series_score = serializers.DictField(
        help_text="Series score by participant ID (e.g., {123: 2, 456: 1})"
    )
    
    total_games = serializers.IntegerField(
        help_text="Total games played in series"
    )
    
    games = serializers.ListField(
        child=serializers.DictField(),
        help_text="Game-by-game results"
    )
    
    participants = LeaderboardEntrySerializer(
        many=True,
        help_text="Participant standings with win/loss records"
    )


class PlacementOverrideSerializer(serializers.Serializer):
    """
    Staff placement override request.
    
    Endpoint: POST /api/tournaments/{id}/override-placement/
    
    Requires IsStaffOrAdmin permission.
    """
    
    registration_id = serializers.IntegerField(
        required=True,
        help_text="Registration ID to override placement for"
    )
    
    new_rank = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="New placement rank (1=1st place, 2=2nd place, etc.)"
    )
    
    reason = serializers.CharField(
        required=True,
        min_length=10,
        max_length=500,
        help_text="Reason for override (required, min 10 characters)"
    )
    
    def validate_reason(self, value):
        """Validate reason is non-empty and meaningful."""
        if not value or not value.strip():
            raise serializers.ValidationError("Override reason cannot be empty")
        
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Override reason must be at least 10 characters (currently {})".format(len(value.strip()))
            )
        
        return value.strip()
    
    def validate_new_rank(self, value):
        """Validate rank is positive."""
        if value < 1:
            raise serializers.ValidationError("Rank must be 1 or higher")
        
        return value


class PlacementOverrideResponseSerializer(serializers.Serializer):
    """
    Placement override response.
    
    Returns audit trail of the override operation.
    """
    
    success = serializers.BooleanField(
        help_text="Whether override succeeded"
    )
    
    result_id = serializers.IntegerField(
        help_text="TournamentResult ID"
    )
    
    old_rank = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Previous rank (null if no prior placement)"
    )
    
    new_rank = serializers.IntegerField(
        help_text="New rank after override"
    )
    
    override_timestamp = serializers.DateTimeField(
        help_text="When override was applied"
    )
    
    override_actor_id = serializers.IntegerField(
        help_text="User ID of staff member who performed override"
    )
    
    override_reason = serializers.CharField(
        help_text="Reason for override"
    )
