# apps/tournaments/api/serializers_matches.py
from rest_framework import serializers
from ..models import Match, Dispute


class MatchSerializer(serializers.ModelSerializer):
    """Read-only serializer for match responses (no PII)."""
    
    tournament_id = serializers.IntegerField(source='tournament.id', read_only=True)
    sides = serializers.SerializerMethodField()
    
    class Meta:
        model = Match
        fields = [
            'id',
            'tournament_id',
            'round_number',
            'state',
            'sides',
            'scheduled_time',
            'started_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def get_sides(self, obj):
        """Return participant info as sides A/B (no PII - IDs only)."""
        return {
            'A': {
                'participant_id': obj.participant1_id,
                'score': obj.participant1_score,
                'checked_in': obj.participant1_checked_in,
            },
            'B': {
                'participant_id': obj.participant2_id,
                'score': obj.participant2_score,
                'checked_in': obj.participant2_checked_in,
            }
        }


class MatchSubmitResultSerializer(serializers.Serializer):
    """Serializer for participants submitting match results."""
    
    score = serializers.IntegerField(min_value=0, required=True)
    opponent_score = serializers.IntegerField(min_value=0, required=True)
    evidence = serializers.URLField(required=False, allow_blank=True)
    notes = serializers.JSONField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate scores are different (no ties unless allowed)."""
        if data['score'] == data.get('opponent_score'):
            # For now, allow ties - game rules will determine validity
            pass
        return data


class MatchStartSerializer(serializers.Serializer):
    """Serializer for staff starting matches (empty - idempotency only)."""
    pass


class MatchConfirmResultSerializer(serializers.Serializer):
    """Serializer for staff confirming results."""
    decision = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MatchDisputeSerializer(serializers.Serializer):
    """Serializer for participants filing disputes."""
    
    REASON_CODES = [
        'SCORE_MISMATCH',
        'NO_SHOW',
        'CHEATING',
        'TECHNICAL_ISSUE',
        'OTHER'
    ]
    
    reason_code = serializers.ChoiceField(choices=REASON_CODES, required=True)
    notes = serializers.JSONField(required=False, allow_null=True)
    evidence = serializers.URLField(required=False, allow_blank=True)
    
    def validate_reason_code(self, value):
        """Ensure reason code is uppercase."""
        return value.upper()


class MatchResolveDisputeSerializer(serializers.Serializer):
    """Serializer for staff resolving disputes."""
    
    DECISIONS = ['ACCEPT_REPORTED', 'OVERRIDE', 'REMATCH', 'DISQUALIFY']
    
    decision = serializers.ChoiceField(choices=DECISIONS, required=True)
    final_score_a = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    final_score_b = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.JSONField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate that OVERRIDE decision includes final scores."""
        if data['decision'] == 'OVERRIDE':
            if data.get('final_score_a') is None or data.get('final_score_b') is None:
                raise serializers.ValidationError(
                    "OVERRIDE decision requires final_score_a and final_score_b"
                )
        return data


class MatchCancelSerializer(serializers.Serializer):
    """Serializer for staff cancelling matches."""
    
    REASON_CODES = [
        'TOURNAMENT_CANCELLED',
        'INSUFFICIENT_PARTICIPANTS',
        'TECHNICAL_ISSUES',
        'ORGANIZER_REQUEST',
        'OTHER'
    ]
    
    reason_code = serializers.ChoiceField(choices=REASON_CODES, required=True)
    notes = serializers.JSONField(required=False, allow_null=True)
