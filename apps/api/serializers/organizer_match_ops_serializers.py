"""
Match Operations API Serializers - Phase 7, Epic 7.4

DRF serializers for Match Operations Command Center (MOCC) endpoints.

Reference: Phase 7, Epic 7.4 - Match Operations API
"""

from rest_framework import serializers


class MatchOperationLogSerializer(serializers.Serializer):
    """Serializer for match operation log entries."""
    
    log_id = serializers.IntegerField()
    match_id = serializers.IntegerField()
    operator_user_id = serializers.IntegerField()
    operator_username = serializers.CharField()
    operation_type = serializers.CharField()
    payload = serializers.JSONField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()


class MatchModeratorNoteSerializer(serializers.Serializer):
    """Serializer for moderator notes."""
    
    note_id = serializers.IntegerField()
    match_id = serializers.IntegerField()
    author_user_id = serializers.IntegerField()
    author_username = serializers.CharField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField()


class MatchOpsActionResultSerializer(serializers.Serializer):
    """Serializer for operation action results."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    match_id = serializers.IntegerField()
    new_state = serializers.CharField(required=False, allow_null=True)
    operation_log = MatchOperationLogSerializer(required=False, allow_null=True)
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )


class MatchOpsPermissionSerializer(serializers.Serializer):
    """Serializer for match operations permissions."""
    
    user_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    match_id = serializers.IntegerField(required=False, allow_null=True)
    can_mark_live = serializers.BooleanField()
    can_pause = serializers.BooleanField()
    can_resume = serializers.BooleanField()
    can_force_complete = serializers.BooleanField()
    can_override_result = serializers.BooleanField()
    can_add_note = serializers.BooleanField()
    can_assign_referee = serializers.BooleanField()
    is_referee = serializers.BooleanField()
    is_admin = serializers.BooleanField()


class MatchTimelineEventSerializer(serializers.Serializer):
    """Serializer for match timeline events."""
    
    event_id = serializers.CharField()
    event_type = serializers.CharField()
    match_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    actor_user_id = serializers.IntegerField(required=False, allow_null=True)
    actor_username = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField()
    metadata = serializers.JSONField(required=False, allow_null=True)


class MatchOpsDashboardItemSerializer(serializers.Serializer):
    """Serializer for dashboard match items."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    tournament_name = serializers.CharField()
    stage_id = serializers.IntegerField()
    stage_name = serializers.CharField()
    round_number = serializers.IntegerField()
    match_number = serializers.IntegerField()
    status = serializers.CharField()
    scheduled_time = serializers.DateTimeField(required=False, allow_null=True)
    team1_name = serializers.CharField(required=False, allow_null=True)
    team2_name = serializers.CharField(required=False, allow_null=True)
    primary_referee_username = serializers.CharField(required=False, allow_null=True)
    has_pending_result = serializers.BooleanField()
    has_unresolved_dispute = serializers.BooleanField()
    last_operation_type = serializers.CharField(required=False, allow_null=True)
    last_operation_time = serializers.DateTimeField(required=False, allow_null=True)
    moderator_notes_count = serializers.IntegerField()


# Request Serializers

class MarkMatchLiveRequestSerializer(serializers.Serializer):
    """Request serializer for mark match live."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()


class PauseMatchRequestSerializer(serializers.Serializer):
    """Request serializer for pause match."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ResumeMatchRequestSerializer(serializers.Serializer):
    """Request serializer for resume match."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()


class ForceCompleteMatchRequestSerializer(serializers.Serializer):
    """Request serializer for force complete match."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    reason = serializers.CharField()
    result_data = serializers.JSONField(required=False, allow_null=True)


class AddMatchNoteRequestSerializer(serializers.Serializer):
    """Request serializer for add moderator note."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    content = serializers.CharField()


class OverrideMatchResultRequestSerializer(serializers.Serializer):
    """Request serializer for override match result."""
    
    match_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField()
    new_result_data = serializers.JSONField()
    reason = serializers.CharField()
