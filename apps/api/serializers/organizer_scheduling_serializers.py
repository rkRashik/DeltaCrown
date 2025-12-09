"""
Organizer Match Scheduling Serializers - Phase 7, Epic 7.2

DRF serializers for organizer manual scheduling API endpoints.

Architecture:
- Uses TournamentOpsService façade (no direct service access)
- Returns DTOs converted to JSON-serializable format
- Validates input data for scheduling operations

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from rest_framework import serializers
from datetime import datetime


class MatchSchedulingItemSerializer(serializers.Serializer):
    """
    Serializer for match scheduling item display.
    
    Converts MatchSchedulingItemDTO to JSON for organizer UI.
    """
    
    match_id = serializers.IntegerField(read_only=True)
    tournament_id = serializers.IntegerField(read_only=True)
    tournament_name = serializers.CharField(read_only=True)
    stage_id = serializers.IntegerField(read_only=True)
    stage_name = serializers.CharField(read_only=True)
    round_number = serializers.IntegerField(read_only=True)
    match_number = serializers.IntegerField(read_only=True)
    participant1_id = serializers.IntegerField(read_only=True, allow_null=True)
    participant1_name = serializers.CharField(read_only=True, allow_null=True)
    participant2_id = serializers.IntegerField(read_only=True, allow_null=True)
    participant2_name = serializers.CharField(read_only=True, allow_null=True)
    scheduled_time = serializers.DateTimeField(read_only=True, allow_null=True)
    estimated_duration_minutes = serializers.IntegerField(read_only=True)
    state = serializers.CharField(read_only=True)
    lobby_info = serializers.DictField(read_only=True)
    conflicts = serializers.ListField(child=serializers.CharField(), read_only=True)
    can_reschedule = serializers.BooleanField(read_only=True)
    
    def to_representation(self, instance):
        """Convert DTO to dict representation."""
        return {
            'match_id': instance.match_id,
            'tournament_id': instance.tournament_id,
            'tournament_name': instance.tournament_name,
            'stage_id': instance.stage_id,
            'stage_name': instance.stage_name,
            'round_number': instance.round_number,
            'match_number': instance.match_number,
            'participant1_id': instance.participant1_id,
            'participant1_name': instance.participant1_name,
            'participant2_id': instance.participant2_id,
            'participant2_name': instance.participant2_name,
            'scheduled_time': instance.scheduled_time.isoformat() if instance.scheduled_time else None,
            'estimated_duration_minutes': instance.estimated_duration_minutes,
            'state': instance.state,
            'lobby_info': instance.lobby_info,
            'conflicts': instance.conflicts,
            'can_reschedule': instance.can_reschedule,
        }


class ManualSchedulingRequestSerializer(serializers.Serializer):
    """
    Serializer for manual scheduling assignment request.
    
    Validates input for scheduling a match at a specific time.
    """
    
    match_id = serializers.IntegerField(required=True, min_value=1)
    scheduled_time = serializers.DateTimeField(required=True)
    skip_conflict_check = serializers.BooleanField(required=False, default=False)
    
    def validate_scheduled_time(self, value):
        """Validate scheduled time is in the future."""
        if value < datetime.utcnow():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value


class BulkShiftRequestSerializer(serializers.Serializer):
    """
    Serializer for bulk shift request.
    
    Validates input for shifting all matches in a stage.
    """
    
    stage_id = serializers.IntegerField(required=True, min_value=1)
    delta_minutes = serializers.IntegerField(required=True)
    
    def validate_delta_minutes(self, value):
        """Validate delta_minutes is reasonable."""
        if abs(value) > 10080:  # 1 week in minutes
            raise serializers.ValidationError(
                "Delta must be within ±1 week (±10080 minutes)"
            )
        return value


class SchedulingSlotSerializer(serializers.Serializer):
    """
    Serializer for scheduling slot display.
    
    Converts SchedulingSlotDTO to JSON for organizer UI.
    """
    
    slot_start = serializers.DateTimeField(read_only=True)
    slot_end = serializers.DateTimeField(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    conflicts = serializers.ListField(child=serializers.CharField(), read_only=True)
    suggested_matches = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    
    def to_representation(self, instance):
        """Convert DTO to dict representation."""
        return {
            'slot_start': instance.slot_start.isoformat(),
            'slot_end': instance.slot_end.isoformat(),
            'duration_minutes': instance.duration_minutes,
            'is_available': instance.is_available,
            'conflicts': instance.conflicts,
            'suggested_matches': instance.suggested_matches,
        }


class SchedulingConflictSerializer(serializers.Serializer):
    """
    Serializer for scheduling conflict display.
    
    Converts SchedulingConflictDTO to JSON for organizer UI.
    """
    
    conflict_type = serializers.CharField(read_only=True)
    severity = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    affected_match_ids = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    suggested_resolution = serializers.CharField(read_only=True, allow_null=True)
    
    def to_representation(self, instance):
        """Convert DTO to dict representation."""
        return {
            'conflict_type': instance.conflict_type,
            'severity': instance.severity,
            'message': instance.message,
            'affected_match_ids': instance.affected_match_ids,
            'suggested_resolution': instance.suggested_resolution,
        }


class BulkShiftResultSerializer(serializers.Serializer):
    """
    Serializer for bulk shift result display.
    
    Converts BulkShiftResultDTO to JSON for organizer UI.
    """
    
    shifted_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    conflicts_detected = SchedulingConflictSerializer(many=True, read_only=True)
    failed_match_ids = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    error_messages = serializers.DictField(read_only=True)
    
    def to_representation(self, instance):
        """Convert DTO to dict representation."""
        return {
            'shifted_count': instance.shifted_count,
            'failed_count': instance.failed_count,
            'conflicts_detected': [
                SchedulingConflictSerializer().to_representation(c)
                for c in instance.conflicts_detected
            ],
            'failed_match_ids': instance.failed_match_ids,
            'error_messages': {str(k): v for k, v in instance.error_messages.items()},
        }


class SchedulingAssignmentResponseSerializer(serializers.Serializer):
    """
    Serializer for manual scheduling assignment response.
    
    Returns result of scheduling a match with conflicts.
    """
    
    match = MatchSchedulingItemSerializer(read_only=True)
    conflicts = SchedulingConflictSerializer(many=True, read_only=True)
    was_rescheduled = serializers.BooleanField(read_only=True)
    
    def to_representation(self, instance):
        """Convert result dict to representation."""
        return {
            'match': MatchSchedulingItemSerializer().to_representation(instance['match']),
            'conflicts': [
                SchedulingConflictSerializer().to_representation(c)
                for c in instance['conflicts']
            ],
            'was_rescheduled': instance['was_rescheduled'],
        }
