"""
Module 4.4: Result Submission & Confirmation Serializers

DRF serializers for match result operations with comprehensive validation.

Serializers:
1. ResultSubmissionSerializer - Submit match result (POST /submit-result/)
2. ResultConfirmationSerializer - Confirm match result (POST /confirm-result/)
3. DisputeReportSerializer - Report match dispute (POST /report-dispute/)
4. MatchResultSerializer - Read match result status (response serializer)

Validation:
- State guards: Enforce state machine transitions
- Field guards: Score validation, reason validation
- Permission guards: Implicit (handled by view permissions)

Planning Documents:
- PART_3.1_DATABASE_DESIGN_ERD.md#section-6.2-matchresult-model
- PART_3.1_DATABASE_DESIGN_ERD.md#section-6.3-dispute-model
"""

from rest_framework import serializers
from apps.tournaments.models.match import Match, Dispute


class ResultSubmissionSerializer(serializers.Serializer):
    """
    Serializer for match result submission.
    
    Endpoint: POST /api/tournaments/matches/{id}/submit-result/
    
    Fields:
    - participant1_score: Score for participant 1 (required, non-negative)
    - participant2_score: Score for participant 2 (required, non-negative)
    - notes: Optional notes about the result
    - evidence_url: Optional evidence URL (screenshot/video)
    
    Validation:
    - Scores must be non-negative integers
    - Scores cannot be equal (tie not allowed, enforced in MatchService)
    - Match must be in LIVE or PENDING_RESULT state (enforced in MatchService)
    - Submitter must be a participant (enforced in view permissions)
    """
    
    participant1_score = serializers.IntegerField(
        required=True,
        min_value=0,
        help_text="Score for participant 1 (non-negative)"
    )
    
    participant2_score = serializers.IntegerField(
        required=True,
        min_value=0,
        help_text="Score for participant 2 (non-negative)"
    )
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about the result"
    )
    
    evidence_url = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional evidence URL (screenshot/video)"
    )
    
    def validate(self, attrs):
        """
        Cross-field validation.
        
        Validates:
        - participant1_score and participant2_score are not equal (ties not allowed)
        
        Note: State validation (LIVE/PENDING_RESULT) is enforced in MatchService.
        """
        participant1_score = attrs.get('participant1_score')
        participant2_score = attrs.get('participant2_score')
        
        if participant1_score == participant2_score:
            raise serializers.ValidationError({
                'non_field_errors': ['Match cannot end in a tie. Implement tiebreaker rules.']
            })
        
        return attrs


class ResultConfirmationSerializer(serializers.Serializer):
    """
    Serializer for match result confirmation.
    
    Endpoint: POST /api/tournaments/matches/{id}/confirm-result/
    
    Fields: None (empty body, confirmation is implicit)
    
    Validation:
    - Match must be in PENDING_RESULT state (enforced in MatchService)
    - Match must have result set (winner_id not null, enforced in MatchService)
    - Confirmer must be opponent, organizer, or admin (enforced in view)
    """
    
    # No fields required for confirmation (empty POST body)
    pass


class DisputeReportSerializer(serializers.Serializer):
    """
    Serializer for match dispute reporting.
    
    Endpoint: POST /api/tournaments/matches/{id}/report-dispute/
    
    Fields:
    - reason: Dispute reason (required, must be valid choice)
    - description: Detailed description (required, 20-2000 chars)
    - evidence_screenshot: Optional screenshot file upload
    - evidence_video_url: Optional video URL
    
    Validation:
    - reason must be valid Dispute.REASON_CHOICES
    - description must be at least 20 characters
    - At least one evidence (screenshot or video_url) recommended but not required
    - Match must be in PENDING_RESULT or COMPLETED state (enforced in MatchService)
    - Reporter must be a participant (enforced in view permissions)
    - No active dispute must exist (enforced in MatchService)
    """
    
    reason = serializers.ChoiceField(
        choices=Dispute.REASON_CHOICES,
        required=True,
        help_text="Reason for dispute (score_mismatch, no_show, cheating, technical_issue, other)"
    )
    
    description = serializers.CharField(
        required=True,
        min_length=20,
        max_length=2000,
        help_text="Detailed description of the dispute (minimum 20 characters)"
    )
    
    evidence_screenshot = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Optional screenshot evidence"
    )
    
    evidence_video_url = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional video evidence URL (YouTube, Twitch, etc.)"
    )
    
    def validate(self, attrs):
        """
        Cross-field validation.
        
        Validates:
        - At least one evidence field is provided (recommended practice)
        """
        evidence_screenshot = attrs.get('evidence_screenshot')
        evidence_video_url = attrs.get('evidence_video_url')
        
        # Soft recommendation: Encourage evidence but don't require it
        if not evidence_screenshot and not evidence_video_url:
            # Log warning but allow (organizers may review based on description alone)
            pass
        
        return attrs


class MatchResultSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for match result status.
    
    Used for response payloads after submit/confirm/dispute operations.
    
    Fields:
    - id: Match ID
    - tournament_id: Tournament ID
    - tournament_name: Tournament name (read-only)
    - bracket_id: Bracket ID
    - round_number: Round number
    - match_number: Match number
    - state: Current match state
    - participant1_id: Participant 1 ID
    - participant1_name: Participant 1 name
    - participant1_score: Participant 1 score
    - participant2_id: Participant 2 ID
    - participant2_name: Participant 2 name
    - participant2_score: Participant 2 score
    - winner_id: Winner ID (nullable)
    - loser_id: Loser ID (nullable)
    - started_at: Match start timestamp
    - completed_at: Match completion timestamp
    - has_result: Boolean computed property
    """
    
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    has_result = serializers.SerializerMethodField()
    
    class Meta:
        model = Match
        fields = [
            'id',
            'tournament_id',
            'tournament_name',
            'bracket_id',
            'round_number',
            'match_number',
            'state',
            'participant1_id',
            'participant1_name',
            'participant1_score',
            'participant2_id',
            'participant2_name',
            'participant2_score',
            'winner_id',
            'loser_id',
            'started_at',
            'completed_at',
            'has_result'
        ]
        read_only_fields = fields  # All fields read-only
    
    def get_has_result(self, obj):
        """
        Check if match has result set.
        
        Returns True if winner_id is set (result submitted).
        """
        return obj.winner_id is not None


class DisputeSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for dispute details.
    
    Used for response payloads after dispute creation.
    
    Fields:
    - id: Dispute ID
    - match_id: Match ID
    - initiated_by_id: User ID who initiated dispute
    - reason: Dispute reason
    - description: Dispute description
    - evidence_video_url: Video evidence URL (if provided)
    - status: Dispute status
    - created_at: Creation timestamp
    """
    
    class Meta:
        model = Dispute
        fields = [
            'id',
            'match_id',
            'initiated_by_id',
            'reason',
            'description',
            'evidence_video_url',
            'status',
            'created_at'
        ]
        read_only_fields = fields  # All fields read-only
