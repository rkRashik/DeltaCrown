# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#section-3.4-match-app
# Implements: Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-4.4-match-models
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-001
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-003
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-007

"""
Tournament API - Match Serializers

DRF serializers for match management endpoints.

Module: 4.3 - Match Management & Scheduling API
Phase: 4 - Tournament Live Operations

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Match App Architecture)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Match Models)
- Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md (Module 4.3 Scope)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

Architecture Decisions:
- ADR-001: Service layer pattern - Validation delegates to MatchService
- ADR-003: Soft delete support (queryset filtering)
- ADR-007: WebSocket integration for real-time updates
"""

from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.tournaments.models import Match, Tournament, Bracket


class MatchListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for match list views.
    
    Used for GET /api/matches/ with pagination.
    Optimized for performance with minimal fields.
    
    Source: PART_2.2_SERVICES_INTEGRATION.md Section 4.4
    """
    
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    bracket_name = serializers.CharField(source='bracket.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    
    class Meta:
        model = Match
        fields = [
            'id',
            'tournament',
            'tournament_name',
            'bracket',
            'bracket_name',
            'round_number',
            'match_number',
            'state',
            'state_display',
            'participant1_id',
            'participant1_name',
            'participant2_id',
            'participant2_name',
            'participant1_score',
            'participant2_score',
            'winner_id',
            'scheduled_time',
            'started_at',
            'completed_at',
        ]
        read_only_fields = fields


class MatchSerializer(serializers.ModelSerializer):
    """
    Full serializer for match detail views.
    
    Used for GET /api/matches/{id}/ with all match data.
    Includes lobby info, check-in status, and timestamps.
    
    Source: PART_2.2_SERVICES_INTEGRATION.md Section 4.4
    """
    
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    tournament_slug = serializers.CharField(source='tournament.slug', read_only=True)
    bracket_name = serializers.CharField(source='bracket.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    
    class Meta:
        model = Match
        fields = [
            # Identifiers
            'id',
            'tournament',
            'tournament_name',
            'tournament_slug',
            'bracket',
            'bracket_name',
            'round_number',
            'match_number',
            
            # State
            'state',
            'state_display',
            
            # Participants
            'participant1_id',
            'participant1_name',
            'participant2_id',
            'participant2_name',
            
            # Scores
            'participant1_score',
            'participant2_score',
            'winner_id',
            'loser_id',
            
            # Scheduling
            'scheduled_time',
            'check_in_deadline',
            
            # Check-in
            'participant1_checked_in',
            'participant2_checked_in',
            
            # Lobby
            'lobby_info',
            'stream_url',
            
            # Timestamps
            'started_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'tournament',
            'tournament_name',
            'tournament_slug',
            'bracket',
            'bracket_name',
            'round_number',
            'match_number',
            'state',
            'state_display',
            'participant1_id',
            'participant1_name',
            'participant2_id',
            'participant2_name',
            'participant1_score',
            'participant2_score',
            'winner_id',
            'loser_id',
            'check_in_deadline',
            'participant1_checked_in',
            'participant2_checked_in',
            'started_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]


class MatchUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating match fields.
    
    Used for PATCH /api/matches/{id}/
    Restricts updates to safe fields only (scheduled_time, stream_url).
    
    Permissions:
    - Organizer/Admin only
    
    Validation:
    - Cannot update completed/cancelled matches
    - scheduled_time must be in future
    
    Source: PART_2.2_SERVICES_INTEGRATION.md Section 4.4
    """
    
    class Meta:
        model = Match
        fields = [
            'scheduled_time',
            'stream_url',
        ]
    
    def validate_scheduled_time(self, value):
        """Validate scheduled_time is in future."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value
    
    def validate(self, attrs):
        """Validate match can be updated."""
        match = self.instance
        
        # Cannot update completed/cancelled matches
        if match.state in [Match.COMPLETED, Match.CANCELLED, Match.FORFEIT]:
            raise serializers.ValidationError(
                f"Cannot update match in state: {match.get_state_display()}"
            )
        
        return attrs


class LobbyInfoSerializer(serializers.Serializer):
    """
    Serializer for lobby_info JSONB field validation.
    
    Used for PATCH /api/matches/{id}/lobby/
    Validates required keys per game type.
    
    Lobby Info Schema (game-specific):
    - VALORANT: {"room_code": str, "region": str, "map": str (optional)}
    - MLBB: {"room_id": str, "room_password": str, "draft_mode": str (optional)}
    - EFOOTBALL: {"match_id": str, "lobby_code": str (optional)}
    - PUBGM: {"room_id": str, "room_password": str, "map": str, "mode": str}
    
    Source: PART_2.2_SERVICES_INTEGRATION.md Section 4.4
    """
    
    # Common fields (all games)
    room_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    room_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    room_password = serializers.CharField(max_length=50, required=False, allow_blank=True)
    lobby_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    match_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    # Game-specific fields
    region = serializers.CharField(max_length=20, required=False, allow_blank=True)
    map = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mode = serializers.CharField(max_length=50, required=False, allow_blank=True)
    draft_mode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Additional metadata
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate(self, attrs):
        """
        Validate lobby info based on game type.
        
        Validation rules:
        - At least one identifier field required (room_code, room_id, match_id)
        - Game-specific required fields validated via tournament.game_id
        """
        # Check at least one identifier provided
        identifiers = ['room_code', 'room_id', 'room_password', 'lobby_code', 'match_id']
        if not any(attrs.get(field) for field in identifiers):
            raise serializers.ValidationError(
                "At least one lobby identifier required (room_code, room_id, match_id, etc.)"
            )
        
        return attrs


class BulkScheduleSerializer(serializers.Serializer):
    """
    Serializer for bulk match scheduling.
    
    Used for POST /api/matches/bulk-schedule/
    Allows organizers to set scheduled_time for multiple matches at once.
    
    Permissions:
    - Organizer/Admin only
    
    Validation:
    - All match IDs must exist and belong to same tournament
    - scheduled_time must be in future
    - Matches must not be completed/cancelled
    
    Source: Module 4.3 Scope (bulk scheduling requirement)
    """
    
    match_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,  # Rate limit: max 100 matches per request
        help_text="List of match IDs to schedule (max 100)"
    )
    scheduled_time = serializers.DateTimeField(
        help_text="Scheduled time for all matches"
    )
    
    def validate_match_ids(self, value):
        """Validate match IDs are unique."""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate match IDs not allowed")
        return value
    
    def validate_scheduled_time(self, value):
        """Validate scheduled_time is in future."""
        if value < timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value
    
    def validate(self, attrs):
        """
        Validate all matches exist and belong to same tournament.
        
        Cross-field validation:
        - All match IDs must exist
        - All matches must belong to same tournament
        - No completed/cancelled matches
        """
        match_ids = attrs['match_ids']
        
        # Fetch matches
        matches = Match.objects.filter(
            id__in=match_ids,
            is_deleted=False
        ).select_related('tournament')
        
        # Check all IDs found
        if matches.count() != len(match_ids):
            found_ids = set(matches.values_list('id', flat=True))
            missing_ids = set(match_ids) - found_ids
            raise serializers.ValidationError({
                'match_ids': f"Matches not found: {sorted(missing_ids)}"
            })
        
        # Check all belong to same tournament
        tournament_ids = set(matches.values_list('tournament_id', flat=True))
        if len(tournament_ids) > 1:
            raise serializers.ValidationError({
                'match_ids': "All matches must belong to the same tournament"
            })
        
        # Check no completed/cancelled matches
        invalid_states = [Match.COMPLETED, Match.CANCELLED, Match.FORFEIT]
        invalid_matches = matches.filter(state__in=invalid_states)
        if invalid_matches.exists():
            invalid_ids = list(invalid_matches.values_list('id', flat=True))
            raise serializers.ValidationError({
                'match_ids': f"Cannot schedule completed/cancelled matches: {invalid_ids}"
            })
        
        # Store matches and tournament for view access
        attrs['_matches'] = matches
        attrs['_tournament'] = matches.first().tournament
        
        return attrs


class CoordinatorAssignmentSerializer(serializers.Serializer):
    """
    Serializer for coordinator assignment.
    
    Used for POST /api/matches/{id}/assign-coordinator/
    Allows organizers to assign a coordinator to oversee match execution.
    
    Permissions:
    - Organizer/Admin only
    
    Validation:
    - Coordinator user must exist
    - Match must not be completed/cancelled
    
    Source: Module 4.3 Scope (coordinator assignment requirement)
    """
    
    coordinator_id = serializers.IntegerField(
        min_value=1,
        help_text="User ID of coordinator to assign"
    )
    
    def validate_coordinator_id(self, value):
        """Validate coordinator user exists."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"User with ID {value} not found")
        
        return value
    
    def validate(self, attrs):
        """Validate match can have coordinator assigned."""
        match = self.context.get('match')
        
        if match and match.state in [Match.COMPLETED, Match.CANCELLED, Match.FORFEIT]:
            raise serializers.ValidationError(
                f"Cannot assign coordinator to match in state: {match.get_state_display()}"
            )
        
        return attrs


class MatchStartSerializer(serializers.Serializer):
    """
    Serializer for match start action.
    
    Used for POST /api/matches/{id}/start/
    Validates match can transition to LIVE state via MatchService.
    
    Permissions:
    - Organizer/Admin only
    
    Validation:
    - Match must be in READY state
    - Check-in must be complete (if enabled)
    
    Source: PART_2.1_ARCHITECTURE_FOUNDATIONS.md Section 3.4 (State Machine)
    """
    
    def validate(self, attrs):
        """
        Validate match can be started.
        
        Business rules (enforced by MatchService):
        - Match must be in READY state
        - Both participants must have checked in (if check-in enabled)
        """
        match = self.context.get('match')
        
        if not match:
            raise serializers.ValidationError("Match context not provided")
        
        # State validation
        if match.state != Match.READY:
            raise serializers.ValidationError(
                f"Cannot start match from state: {match.get_state_display()}. Must be in READY state."
            )
        
        # Check-in validation
        tournament = match.tournament
        if tournament.enable_check_in:
            if not match.participant1_checked_in or not match.participant2_checked_in:
                raise serializers.ValidationError(
                    "Cannot start match: Both participants must check in first"
                )
        
        return attrs
