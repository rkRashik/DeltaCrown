"""
Serializers for Check-in API

Handles serialization/deserialization for:
- Single check-in requests
- Undo check-in requests
- Bulk check-in requests
- Check-in status responses

Author: DeltaCrown Development Team
Date: November 8, 2025
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.tournaments.models import Registration

User = get_user_model()


class CheckinRequestSerializer(serializers.Serializer):
    """
    Serializer for single check-in request.
    Empty body - registration_id comes from URL, actor from context.
    """
    pass


class UndoCheckinRequestSerializer(serializers.Serializer):
    """Serializer for undo check-in request"""
    
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for undoing check-in"
    )
    
    organizer_override = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Flag indicating organizer override (set automatically)"
    )


class BulkCheckinSerializer(serializers.Serializer):
    """Serializer for bulk check-in request"""
    
    registration_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=200,
        help_text="List of registration IDs to check in (max 200)"
    )
    
    def validate_registration_ids(self, value):
        """Ensure no duplicate IDs"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate registration IDs are not allowed")
        return value


class BulkCheckinResultSerializer(serializers.Serializer):
    """Serializer for bulk check-in operation result"""
    
    id = serializers.IntegerField()
    reason = serializers.CharField(required=False)


class BulkCheckinResponseSerializer(serializers.Serializer):
    """Serializer for bulk check-in response"""
    
    success = BulkCheckinResultSerializer(many=True)
    skipped = BulkCheckinResultSerializer(many=True)
    errors = BulkCheckinResultSerializer(many=True)
    
    summary = serializers.SerializerMethodField()
    
    def get_summary(self, obj):
        """Generate summary statistics"""
        return {
            'total_requested': len(obj['success']) + len(obj['skipped']) + len(obj['errors']),
            'successful': len(obj['success']),
            'skipped': len(obj['skipped']),
            'failed': len(obj['errors'])
        }


class CheckedInBySerializer(serializers.ModelSerializer):
    """Serializer for user who performed check-in"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class CheckinStatusSerializer(serializers.ModelSerializer):
    """Serializer for check-in status response"""
    
    # Note: checked_in_by field not yet added to Registration model (future enhancement)
    # checked_in_by_details = CheckedInBySerializer(
    #     source='checked_in_by',
    #     read_only=True
    # )
    
    tournament_id = serializers.IntegerField(source='tournament.id', read_only=True)
    tournament_title = serializers.CharField(source='tournament.name', read_only=True)
    
    registration_type = serializers.SerializerMethodField()
    
    can_undo = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = [
            'id',
            'tournament_id',
            'tournament_title',
            'registration_type',
            'status',
            'checked_in',
            'checked_in_at',
            # 'checked_in_by',
            # 'checked_in_by_details',
            'can_undo',
        ]
        read_only_fields = fields
    
    def get_registration_type(self, obj):
        """Return 'solo' or 'team'"""
        return 'solo' if obj.user_id else 'team'
    
    def get_can_undo(self, obj):
        """
        Check if current user can undo check-in.
        Requires request context with user.
        """
        if not obj.checked_in:
            return False
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # Import here to avoid circular imports
        from apps.tournaments.services.checkin_service import CheckinService
        
        # Organizer can always undo
        if CheckinService._is_organizer_or_admin(user, obj.tournament):
            return True
        
        # Owner can undo within window
        if CheckinService._is_registration_owner(user, obj):
            return CheckinService._is_within_undo_window(obj)
        
        return False


class CheckinResponseSerializer(serializers.Serializer):
    """Generic response serializer for check-in operations"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    registration = CheckinStatusSerializer()
