"""
Organizer Staffing Serializers - Phase 7, Epic 7.3

DRF serializers for staff and referee management API endpoints.

Architecture:
- Maps between DTOs and JSON representations
- Request validation and response formatting
- Used by organizer-facing staffing views

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from rest_framework import serializers
from datetime import datetime


class StaffRoleSerializer(serializers.Serializer):
    """
    Serializer for staff role information.
    
    Reference: Phase 7, Epic 7.3 - Staff Roles API
    """
    
    role_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    capabilities = serializers.DictField(read_only=True)
    is_referee_role = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TournamentStaffAssignmentSerializer(serializers.Serializer):
    """
    Serializer for tournament staff assignment information.
    
    Reference: Phase 7, Epic 7.3 - Staff Assignment API
    """
    
    assignment_id = serializers.IntegerField(read_only=True)
    tournament_id = serializers.IntegerField(read_only=True)
    tournament_name = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    user_email = serializers.EmailField(read_only=True)
    role = StaffRoleSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    stage_id = serializers.IntegerField(allow_null=True, read_only=True)
    stage_name = serializers.CharField(allow_null=True, read_only=True)
    assigned_by_user_id = serializers.IntegerField(allow_null=True, read_only=True)
    assigned_by_username = serializers.CharField(allow_null=True, read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)
    notes = serializers.CharField(allow_blank=True, read_only=True)


class AssignStaffRequestSerializer(serializers.Serializer):
    """
    Serializer for staff assignment request.
    
    Reference: Phase 7, Epic 7.3 - Assign Staff Endpoint
    """
    
    user_id = serializers.IntegerField(required=True)
    role_code = serializers.CharField(required=True, max_length=50)
    stage_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    
    def validate_role_code(self, value):
        """Validate role code is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Role code cannot be empty")
        return value.strip().upper()


class MatchRefereeAssignmentSerializer(serializers.Serializer):
    """
    Serializer for match referee assignment information.
    
    Reference: Phase 7, Epic 7.3 - Referee Assignment API
    """
    
    assignment_id = serializers.IntegerField(read_only=True)
    match_id = serializers.IntegerField(read_only=True)
    tournament_id = serializers.IntegerField(read_only=True)
    stage_id = serializers.IntegerField(read_only=True)
    round_number = serializers.IntegerField(read_only=True)
    match_number = serializers.IntegerField(read_only=True)
    staff_assignment = TournamentStaffAssignmentSerializer(read_only=True)
    is_primary = serializers.BooleanField(read_only=True)
    assigned_by_user_id = serializers.IntegerField(allow_null=True, read_only=True)
    assigned_by_username = serializers.CharField(allow_null=True, read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)
    notes = serializers.CharField(allow_blank=True, read_only=True)


class AssignRefereeRequestSerializer(serializers.Serializer):
    """
    Serializer for referee assignment request.
    
    Reference: Phase 7, Epic 7.3 - Assign Referee Endpoint
    """
    
    staff_assignment_id = serializers.IntegerField(required=True)
    is_primary = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    check_load = serializers.BooleanField(required=False, default=True)
    
    def validate_staff_assignment_id(self, value):
        """Validate staff assignment ID is positive."""
        if value <= 0:
            raise serializers.ValidationError("Staff assignment ID must be positive")
        return value


class AssignRefereeResponseSerializer(serializers.Serializer):
    """
    Serializer for referee assignment response (includes warning).
    
    Reference: Phase 7, Epic 7.3 - Assign Referee Response
    """
    
    assignment = MatchRefereeAssignmentSerializer(read_only=True)
    warning = serializers.CharField(allow_null=True, read_only=True)


class StaffLoadSerializer(serializers.Serializer):
    """
    Serializer for staff workload information.
    
    Reference: Phase 7, Epic 7.3 - Staff Load API
    """
    
    staff_assignment = TournamentStaffAssignmentSerializer(read_only=True)
    total_matches_assigned = serializers.IntegerField(read_only=True)
    upcoming_matches = serializers.IntegerField(read_only=True)
    completed_matches = serializers.IntegerField(read_only=True)
    concurrent_matches = serializers.IntegerField(read_only=True)
    is_overloaded = serializers.BooleanField(read_only=True)
    load_percentage = serializers.FloatField(read_only=True)


class RemoveStaffResponseSerializer(serializers.Serializer):
    """
    Serializer for staff removal response.
    
    Reference: Phase 7, Epic 7.3 - Remove Staff Endpoint
    """
    
    assignment = TournamentStaffAssignmentSerializer(read_only=True)
    message = serializers.CharField(read_only=True)
