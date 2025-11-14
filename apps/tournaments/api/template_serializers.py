"""
Tournament Template Serializers

DRF serializers for tournament template API endpoints.

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
"""

from rest_framework import serializers
from apps.tournaments.models import TournamentTemplate
from apps.tournaments.services.template_service import TemplateService


class TournamentTemplateListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for template list views.
    
    Returns essential fields for browsing templates.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True, allow_null=True)
    
    class Meta:
        model = TournamentTemplate
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'game',
            'game_name',
            'visibility',
            'is_active',
            'usage_count',
            'last_used_at',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = fields


class TournamentTemplateDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for template detail view.
    
    Includes template_config JSONB field.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True, allow_null=True)
    
    class Meta:
        model = TournamentTemplate
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'game',
            'game_name',
            'visibility',
            'organization_id',
            'template_config',
            'usage_count',
            'last_used_at',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'slug',
            'usage_count',
            'last_used_at',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]


class TournamentTemplateCreateSerializer(serializers.Serializer):
    """
    Serializer for creating templates.
    
    Validates input and delegates to TemplateService.
    """
    name = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    game_id = serializers.IntegerField(required=False, allow_null=True)
    visibility = serializers.ChoiceField(
        choices=TournamentTemplate.VISIBILITY_CHOICES,
        default=TournamentTemplate.PRIVATE
    )
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    template_config = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):
        """Validate visibility + organization_id combination."""
        visibility = attrs.get('visibility', TournamentTemplate.PRIVATE)
        organization_id = attrs.get('organization_id')
        
        if visibility == TournamentTemplate.ORG and not organization_id:
            raise serializers.ValidationError(
                "organization_id is required for ORG visibility"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create template via TemplateService."""
        user = self.context['request'].user
        
        template = TemplateService.create_template(
            name=validated_data['name'],
            created_by=user,
            game_id=validated_data.get('game_id'),
            template_config=validated_data.get('template_config', {}),
            description=validated_data.get('description', ''),
            visibility=validated_data.get('visibility', TournamentTemplate.PRIVATE),
            organization_id=validated_data.get('organization_id'),
        )
        
        return template


class TournamentTemplateUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating templates.
    
    Supports partial updates.
    """
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=TournamentTemplate.VISIBILITY_CHOICES,
        required=False
    )
    template_config = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False)
    
    def update(self, instance, validated_data):
        """Update template via TemplateService."""
        user = self.context['request'].user
        
        updated_template = TemplateService.update_template(
            template_id=instance.id,
            user=user,
            name=validated_data.get('name'),
            description=validated_data.get('description'),
            template_config=validated_data.get('template_config'),
            visibility=validated_data.get('visibility'),
            is_active=validated_data.get('is_active'),
        )
        
        return updated_template


class TournamentTemplateApplySerializer(serializers.Serializer):
    """
    Serializer for applying a template.
    
    Input: Optional tournament payload to merge with template.
    Output: Merged tournament configuration.
    """
    tournament_payload = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Optional tournament data to merge with template (overrides template values)"
    )
    
    def validate_tournament_payload(self, value):
        """Validate tournament_payload is a dict."""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("tournament_payload must be a JSON object (dict)")
        return value


class TournamentTemplateApplyResponseSerializer(serializers.Serializer):
    """
    Response serializer for template application.
    
    Returns merged tournament configuration.
    """
    merged_config = serializers.JSONField(
        help_text="Merged tournament configuration ready for TournamentService.create_tournament()"
    )
    template_id = serializers.IntegerField()
    template_name = serializers.CharField()
    applied_at = serializers.DateTimeField()
