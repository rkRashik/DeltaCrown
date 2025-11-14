"""
Custom Field API Serializers

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (CustomField Model)

Description:
DRF serializers for tournament custom fields CRUD operations via REST API.
Provides lightweight list views and detailed CRUD operations with validation.

Architecture Decisions:
- ADR-001: Service Layer Pattern - Delegates to CustomFieldService
- ADR-004: PostgreSQL JSONB - Serializes field_config and field_value
"""

from rest_framework import serializers
from apps.tournaments.models.tournament import CustomField
from apps.tournaments.services.custom_field_service import CustomFieldService


class CustomFieldListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for custom field list views.
    
    Returns essential fields for quick display.
    
    Example response:
    {
        "id": 1,
        "field_name": "Discord Server",
        "field_key": "discord-server",
        "field_type": "url",
        "is_required": true,
        "order": 0
    }
    """
    class Meta:
        model = CustomField
        fields = ['id', 'field_name', 'field_key', 'field_type', 'is_required', 'order']
        read_only_fields = ['id', 'field_key']


class CustomFieldDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for custom field retrieval.
    
    Returns all fields including configuration and values.
    
    Example response:
    {
        "id": 1,
        "tournament": 1,
        "field_name": "Discord Server",
        "field_key": "discord-server",
        "field_type": "url",
        "field_config": {
            "pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"
        },
        "field_value": {},
        "is_required": true,
        "help_text": "Tournament Discord server link",
        "order": 0
    }
    """
    class Meta:
        model = CustomField
        fields = [
            'id', 'tournament', 'field_name', 'field_key', 'field_type',
            'field_config', 'field_value', 'is_required', 'help_text', 'order'
        ]
        read_only_fields = ['id', 'field_key']


class CustomFieldCreateSerializer(serializers.Serializer):
    """
    Write-only serializer for creating custom fields.
    
    Delegates to CustomFieldService for validation and creation.
    
    Example request body:
    {
        "field_name": "Discord Server",
        "field_type": "url",
        "field_config": {
            "pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"
        },
        "is_required": true,
        "help_text": "Tournament Discord server link",
        "order": 0
    }
    """
    field_name = serializers.CharField(max_length=100)
    field_type = serializers.ChoiceField(
        choices=['text', 'number', 'media', 'toggle', 'date', 'url', 'dropdown']
    )
    field_config = serializers.JSONField(required=False, default=dict)
    is_required = serializers.BooleanField(default=False)
    help_text = serializers.CharField(required=False, allow_blank=True, default='')
    order = serializers.IntegerField(default=0)
    
    def create(self, validated_data):
        """
        Create custom field via service layer.
        
        Args:
            validated_data: Validated field data
        
        Returns:
            CustomField: Created field instance
        """
        tournament_id = self.context['tournament_id']
        user = self.context['request'].user
        
        return CustomFieldService.create_field(
            tournament_id=tournament_id,
            user=user,
            field_data=validated_data
        )


class CustomFieldUpdateSerializer(serializers.Serializer):
    """
    Write-only serializer for updating custom fields.
    
    Accepts partial updates. Delegates to CustomFieldService.
    
    Example request body:
    {
        "is_required": false,
        "help_text": "Optional Discord link"
    }
    """
    field_name = serializers.CharField(max_length=100, required=False)
    field_type = serializers.ChoiceField(
        choices=['text', 'number', 'media', 'toggle', 'date', 'url', 'dropdown'],
        required=False
    )
    field_config = serializers.JSONField(required=False)
    is_required = serializers.BooleanField(required=False)
    help_text = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False)
    
    def update(self, instance, validated_data):
        """
        Update custom field via service layer.
        
        Args:
            instance: CustomField instance
            validated_data: Validated update data
        
        Returns:
            CustomField: Updated field instance
        """
        user = self.context['request'].user
        
        return CustomFieldService.update_field(
            field_id=instance.id,
            user=user,
            update_data=validated_data
        )
