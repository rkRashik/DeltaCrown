"""
Challenge & Bounty API serializers.

Phase 10: Challenge & Bounty competitive system.
"""
from rest_framework import serializers


class ChallengeListSerializer(serializers.Serializer):
    """Compact challenge representation for lists and sidebar widgets."""
    id = serializers.UUIDField(read_only=True)
    reference_code = serializers.CharField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    challenge_type = serializers.CharField()
    best_of = serializers.IntegerField()
    
    # Teams
    challenger_team_id = serializers.IntegerField(source='challenger_team.id', read_only=True)
    challenger_team_name = serializers.CharField(source='challenger_team.name', read_only=True)
    challenger_team_slug = serializers.CharField(source='challenger_team.slug', read_only=True)
    challenger_team_tag = serializers.CharField(source='challenger_team.tag', read_only=True, allow_null=True)
    
    challenged_team_id = serializers.IntegerField(source='challenged_team.id', read_only=True, allow_null=True)
    challenged_team_name = serializers.CharField(source='challenged_team.name', read_only=True, allow_null=True)
    challenged_team_slug = serializers.CharField(source='challenged_team.slug', read_only=True, allow_null=True)
    challenged_team_tag = serializers.CharField(source='challenged_team.tag', read_only=True, allow_null=True)

    # Game
    game_id = serializers.IntegerField(source='game.id', read_only=True)
    game_name = serializers.CharField(source='game.display_name', read_only=True)
    game_short_code = serializers.CharField(source='game.short_code', read_only=True)
    game_category = serializers.CharField(source='game.category', read_only=True)

    # Prize
    prize_type = serializers.CharField()
    prize_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    prize_description = serializers.CharField(allow_blank=True, required=False)

    # Result
    result = serializers.CharField(read_only=True)

    # Timing
    created_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    scheduled_at = serializers.DateTimeField(allow_null=True, required=False)

    # Flags
    is_expired = serializers.BooleanField(read_only=True)
    is_open_challenge = serializers.BooleanField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)


class ChallengeDetailSerializer(ChallengeListSerializer):
    """Full challenge detail including game config and scores."""
    game_config = serializers.JSONField(required=False)
    platform = serializers.CharField(allow_blank=True, required=False)
    server_region = serializers.CharField(allow_blank=True, required=False)
    score_details = serializers.JSONField(read_only=True)
    evidence_url = serializers.URLField(allow_blank=True, required=False)
    accepted_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    settled_at = serializers.DateTimeField(read_only=True)


class ChallengeCreateSerializer(serializers.Serializer):
    """Input for challenge creation."""
    challenger_team_id = serializers.IntegerField()
    challenged_team_id = serializers.IntegerField(required=False, allow_null=True)
    game_id = serializers.IntegerField(help_text="Game PK (from games.Game)")
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    challenge_type = serializers.ChoiceField(
        choices=['DIRECT', 'OPEN', 'RANKED', 'WAGER', 'SCRIM'],
        default='DIRECT',
    )
    best_of = serializers.ChoiceField(choices=[1, 3, 5, 7], default=1)
    game_config = serializers.JSONField(required=False, default=dict)
    platform = serializers.CharField(required=False, allow_blank=True, default='')
    server_region = serializers.CharField(required=False, allow_blank=True, default='')
    prize_type = serializers.ChoiceField(
        choices=['NONE', 'CP', 'USD', 'GLORY'],
        default='NONE',
    )
    prize_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_description = serializers.CharField(required=False, allow_blank=True, default='')
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    is_public = serializers.BooleanField(default=True)


class ChallengeAcceptSerializer(serializers.Serializer):
    """Input for accepting a challenge."""
    accepting_team_id = serializers.IntegerField(
        required=False,
        help_text="Required for open challenges; ignored for direct challenges."
    )


class ChallengeResultSerializer(serializers.Serializer):
    """Input for submitting a challenge result."""
    result = serializers.ChoiceField(
        choices=['CHALLENGER_WIN', 'CHALLENGED_WIN', 'DRAW'],
    )
    score_details = serializers.JSONField(required=False, default=dict)
    evidence_url = serializers.URLField(required=False, allow_blank=True, default='')


class ChallengeScheduleSerializer(serializers.Serializer):
    """Input for scheduling a challenge match."""
    scheduled_at = serializers.DateTimeField()


class ChallengeStatsSerializer(serializers.Serializer):
    """Challenge stats for a team."""
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    draws = serializers.IntegerField()
    total = serializers.IntegerField()
    win_rate = serializers.FloatField()
    total_earned = serializers.DecimalField(max_digits=10, decimal_places=2)


# ═══════════════════════════════════════════════════════════════════════════
#  Bounty Serializers
# ═══════════════════════════════════════════════════════════════════════════

class BountyListSerializer(serializers.Serializer):
    """Compact bounty for list displays."""
    id = serializers.UUIDField(read_only=True)
    reference_code = serializers.CharField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bounty_type = serializers.CharField()
    
    issuer_team_id = serializers.IntegerField(source='issuer_team.id', read_only=True)
    issuer_team_name = serializers.CharField(source='issuer_team.name', read_only=True)
    issuer_team_slug = serializers.CharField(source='issuer_team.slug', read_only=True)
    
    game_name = serializers.CharField(source='game.display_name', read_only=True)
    game_short_code = serializers.CharField(source='game.short_code', read_only=True)
    
    reward_type = serializers.CharField()
    reward_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reward_description = serializers.CharField(allow_blank=True, required=False)
    
    max_claims = serializers.IntegerField()
    claim_count = serializers.IntegerField(read_only=True)
    is_claimable = serializers.BooleanField(read_only=True)
    
    expires_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)


class BountyCreateSerializer(serializers.Serializer):
    """Input for bounty creation."""
    issuer_team_id = serializers.IntegerField()
    game_id = serializers.IntegerField()
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    bounty_type = serializers.ChoiceField(
        choices=['BEAT_US', 'WIN_STREAK', 'FIRST_BLOOD', 'TOURNAMENT_WIN', 'CUSTOM'],
        default='BEAT_US',
    )
    criteria = serializers.JSONField(required=False, default=dict)
    reward_type = serializers.ChoiceField(
        choices=['CP', 'USD', 'BADGE', 'GLORY'],
        default='CP',
    )
    reward_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    reward_description = serializers.CharField(required=False, allow_blank=True, default='')
    max_claims = serializers.IntegerField(default=1, min_value=1)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    is_public = serializers.BooleanField(default=True)


class BountyClaimSerializer(serializers.Serializer):
    """Input for submitting a bounty claim."""
    claiming_team_id = serializers.IntegerField()
    evidence_url = serializers.URLField(required=False, allow_blank=True, default='')
    evidence_notes = serializers.CharField(required=False, allow_blank=True, default='')
    challenge_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    match_report_id = serializers.IntegerField(required=False, allow_null=True, default=None)
