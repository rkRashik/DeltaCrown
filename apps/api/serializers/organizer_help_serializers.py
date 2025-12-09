"""
DRF Serializers for Help & Onboarding API

Phase 7, Epic 7.6: Guidance & Help Overlays
Serializers for help content, onboarding, and help bundle endpoints.
"""

from rest_framework import serializers
from apps.tournament_ops.dtos import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
    HelpBundleDTO,
)


class HelpContentSerializer(serializers.Serializer):
    """Serializer for HelpContentDTO."""
    
    content_id = serializers.IntegerField()
    key = serializers.CharField(max_length=100)
    scope = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    html_body = serializers.CharField(required=False, allow_null=True)
    audience = serializers.ChoiceField(
        choices=['organizer', 'referee', 'player', 'global'],
        default='global'
    )
    is_active = serializers.BooleanField(default=True)
    display_order = serializers.IntegerField(default=0)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class HelpOverlaySerializer(serializers.Serializer):
    """Serializer for HelpOverlayDTO."""
    
    overlay_id = serializers.IntegerField()
    help_content_key = serializers.CharField(max_length=100)
    help_content_title = serializers.CharField(max_length=200)
    help_content_body = serializers.CharField()
    page_id = serializers.CharField(max_length=100)
    placement = serializers.ChoiceField(
        choices=['top', 'top-right', 'right', 'bottom-right', 'bottom', 
                'bottom-left', 'left', 'top-left', 'center'],
        default='top-right'
    )
    config = serializers.JSONField(default=dict)
    is_active = serializers.BooleanField(default=True)
    display_order = serializers.IntegerField(default=0)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class OnboardingStepSerializer(serializers.Serializer):
    """Serializer for OnboardingStepDTO."""
    
    state_id = serializers.IntegerField(required=False, allow_null=True)
    user_id = serializers.IntegerField()
    tournament_id = serializers.IntegerField(required=False, allow_null=True)
    step_key = serializers.CharField(max_length=100)
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    dismissed = serializers.BooleanField(default=False)
    dismissed_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    is_complete = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)


class HelpBundleSerializer(serializers.Serializer):
    """Serializer for complete help bundle."""
    
    page_id = serializers.CharField(max_length=100)
    help_content = HelpContentSerializer(many=True)
    overlays = HelpOverlaySerializer(many=True)
    onboarding_steps = OnboardingStepSerializer(many=True)
    pending_onboarding_count = serializers.IntegerField()


class CompleteStepRequestSerializer(serializers.Serializer):
    """Request serializer for completing an onboarding step."""
    
    step_key = serializers.CharField(max_length=100, required=True)
    tournament_id = serializers.IntegerField(required=False, allow_null=True)


class DismissStepRequestSerializer(serializers.Serializer):
    """Request serializer for dismissing an onboarding step."""
    
    step_key = serializers.CharField(max_length=100, required=True)
    tournament_id = serializers.IntegerField(required=False, allow_null=True)


class OnboardingProgressSerializer(serializers.Serializer):
    """Serializer for onboarding progress summary."""
    
    total_steps = serializers.IntegerField()
    completed = serializers.IntegerField()
    dismissed = serializers.IntegerField()
    pending = serializers.IntegerField()
    completion_percentage = serializers.IntegerField()
