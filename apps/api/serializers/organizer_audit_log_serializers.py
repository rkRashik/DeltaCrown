"""
Audit Log Serializers for Organizer API

Phase 7, Epic 7.5: Audit Log System
Provides DRF serializers for audit log API endpoints.

Serializers:
    - AuditLogSerializer: Single audit log entry
    - AuditLogFilterSerializer: Filter parameters for queries
    - AuditLogExportSerializer: Export format for CSV download
"""

from rest_framework import serializers
from datetime import datetime


class AuditLogSerializer(serializers.Serializer):
    """
    Serializer for audit log entries.
    
    Phase 7, Epic 7.5: Display audit trail in organizer console.
    
    Maps AuditLogDTO to JSON response.
    """
    
    log_id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(allow_null=True, read_only=True)
    username = serializers.CharField(allow_null=True, read_only=True)
    action = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    metadata = serializers.JSONField(allow_null=True, read_only=True)
    ip_address = serializers.IPAddressField(allow_null=True, read_only=True)
    user_agent = serializers.CharField(allow_null=True, read_only=True, max_length=500)
    tournament_id = serializers.IntegerField(allow_null=True, read_only=True)
    match_id = serializers.IntegerField(allow_null=True, read_only=True)
    before_state = serializers.JSONField(allow_null=True, read_only=True)
    after_state = serializers.JSONField(allow_null=True, read_only=True)
    correlation_id = serializers.CharField(allow_null=True, read_only=True, max_length=100)
    
    # Computed fields
    has_state_change = serializers.SerializerMethodField()
    changed_fields = serializers.SerializerMethodField()
    
    def get_has_state_change(self, obj):
        """Check if entry tracks state change."""
        return obj.has_state_change()
    
    def get_changed_fields(self, obj):
        """Get list of changed fields."""
        return obj.get_changed_fields()
    
    @classmethod
    def from_dto(cls, dto):
        """
        Create serializer from AuditLogDTO.
        
        Args:
            dto: AuditLogDTO instance
            
        Returns:
            Serializer instance with data from DTO
        """
        return cls(dto)


class AuditLogFilterSerializer(serializers.Serializer):
    """
    Serializer for audit log filter parameters.
    
    Phase 7, Epic 7.5: Search/filter audit logs in organizer console.
    
    Maps query parameters to AuditLogFilterDTO.
    """
    
    user_id = serializers.IntegerField(required=False, allow_null=True)
    action = serializers.CharField(required=False, allow_null=True, max_length=50)
    action_prefix = serializers.CharField(required=False, allow_null=True, max_length=50)
    tournament_id = serializers.IntegerField(required=False, allow_null=True)
    match_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    has_state_change = serializers.BooleanField(required=False, allow_null=True)
    correlation_id = serializers.CharField(required=False, allow_null=True, max_length=100)
    limit = serializers.IntegerField(required=False, default=100, min_value=1, max_value=1000)
    offset = serializers.IntegerField(required=False, default=0, min_value=0)
    order_by = serializers.ChoiceField(
        required=False,
        default='-timestamp',
        choices=['timestamp', '-timestamp', 'action', '-action', 'user_id', '-user_id']
    )
    
    def to_dto(self):
        """
        Convert validated data to AuditLogFilterDTO.
        
        Returns:
            AuditLogFilterDTO instance
        """
        from apps.tournament_ops.dtos import AuditLogFilterDTO
        
        validated_data = self.validated_data
        
        return AuditLogFilterDTO(
            user_id=validated_data.get('user_id'),
            action=validated_data.get('action'),
            action_prefix=validated_data.get('action_prefix'),
            tournament_id=validated_data.get('tournament_id'),
            match_id=validated_data.get('match_id'),
            start_date=validated_data.get('start_date'),
            end_date=validated_data.get('end_date'),
            has_state_change=validated_data.get('has_state_change'),
            correlation_id=validated_data.get('correlation_id'),
            limit=validated_data.get('limit', 100),
            offset=validated_data.get('offset', 0),
            order_by=validated_data.get('order_by', '-timestamp')
        )


class AuditLogExportSerializer(serializers.Serializer):
    """
    Serializer for audit log export (CSV format).
    
    Phase 7, Epic 7.5: Export audit logs for compliance reporting.
    
    Maps AuditLogExportDTO to CSV-friendly structure.
    """
    
    log_id = serializers.IntegerField()
    username = serializers.CharField()
    action = serializers.CharField()
    timestamp = serializers.CharField()  # ISO format string
    tournament_id = serializers.IntegerField(allow_null=True)
    match_id = serializers.IntegerField(allow_null=True)
    ip_address = serializers.CharField(allow_null=True)
    metadata_json = serializers.CharField()
    before_state_json = serializers.CharField(allow_null=True)
    after_state_json = serializers.CharField(allow_null=True)
    changed_fields = serializers.CharField(allow_null=True)
    
    @classmethod
    def from_dto(cls, dto):
        """
        Create serializer from AuditLogExportDTO.
        
        Args:
            dto: AuditLogExportDTO instance
            
        Returns:
            Serializer instance with data from DTO
        """
        return cls(dto)


class AuditLogListResponseSerializer(serializers.Serializer):
    """
    Serializer for paginated audit log list response.
    
    Phase 7, Epic 7.5: Paginated API response with metadata.
    """
    
    count = serializers.IntegerField(help_text="Total number of logs matching filters")
    results = AuditLogSerializer(many=True, help_text="Audit log entries for current page")
    
    class Meta:
        fields = ['count', 'results']


# Export serializers
__all__ = [
    'AuditLogSerializer',
    'AuditLogFilterSerializer',
    'AuditLogExportSerializer',
    'AuditLogListResponseSerializer',
]
