"""Crown Contracts API serializers."""
from __future__ import annotations

from rest_framework import serializers


class ContractTemplateSerializer(serializers.Serializer):
    """Public catalog row for a Crown Contract mission."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)

    # Game
    game_id = serializers.IntegerField(source='game.id', read_only=True)
    game_name = serializers.CharField(source='game.display_name', read_only=True)
    game_short_code = serializers.CharField(source='game.short_code', read_only=True)

    # Economy
    entry_fee_dc = serializers.IntegerField(read_only=True)
    reward_dc = serializers.IntegerField(read_only=True)

    # Goal
    goal_type = serializers.CharField(read_only=True)
    goal_type_display = serializers.CharField(
        source='get_goal_type_display', read_only=True
    )
    goal_spec = serializers.JSONField(read_only=True)

    # Reward extras
    badge_slug = serializers.CharField(read_only=True, allow_blank=True)

    # Time-window
    duration_hours = serializers.IntegerField(read_only=True)

    # Availability
    is_active = serializers.BooleanField(read_only=True)
    is_currently_available = serializers.BooleanField(read_only=True)
    valid_from = serializers.DateTimeField(read_only=True, allow_null=True)
    valid_until = serializers.DateTimeField(read_only=True, allow_null=True)

    created_at = serializers.DateTimeField(read_only=True)


class ContractEnrollmentSerializer(serializers.Serializer):
    """A player's attempt at a contract.

    Always includes ``closure_reason`` + ``closure_note`` so the UI can
    render specific terminal-state messaging instead of a bare countdown.
    """

    id = serializers.UUIDField(read_only=True)
    reference_code = serializers.CharField(read_only=True)

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    # Embedded template snapshot
    template_id = serializers.UUIDField(source='template.id', read_only=True)
    template_title = serializers.CharField(source='template.title', read_only=True)
    template_entry_fee_dc = serializers.IntegerField(
        source='template.entry_fee_dc', read_only=True
    )
    template_reward_dc = serializers.IntegerField(
        source='template.reward_dc', read_only=True
    )
    template_badge_slug = serializers.CharField(
        source='template.badge_slug', read_only=True, allow_blank=True
    )

    # State
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress = serializers.JSONField(read_only=True)

    # Time-window
    enrolled_at = serializers.DateTimeField(read_only=True)
    deadline_at = serializers.DateTimeField(read_only=True)
    resolved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True)

    # Closure (REQUIRED on every match/lobby state response)
    closure_reason = serializers.CharField(read_only=True, allow_blank=True)
    closure_reason_display = serializers.CharField(
        source='get_closure_reason_display', read_only=True, allow_blank=True
    )
    closure_note = serializers.CharField(read_only=True, allow_blank=True)
