"""Crown Royale API serializers."""
from __future__ import annotations

from rest_framework import serializers


class RoyaleLobbyListSerializer(serializers.Serializer):
    """Public lobby card for the schedule view.

    Includes ``closure_reason`` + ``closure_note`` so cancelled lobbies
    can render a specific reason instead of a bare countdown.
    """

    id = serializers.UUIDField(read_only=True)
    reference_code = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)

    # Game
    game_id = serializers.IntegerField(source='game.id', read_only=True)
    game_name = serializers.CharField(source='game.display_name', read_only=True)
    game_short_code = serializers.CharField(source='game.short_code', read_only=True)

    # Capacity & economy
    max_slots = serializers.IntegerField(source='slot_capacity', read_only=True)
    reserved_slots = serializers.IntegerField(source='reserved_count', read_only=True)
    remaining_slots = serializers.IntegerField(read_only=True)
    entry_fee_per_slot_dc = serializers.IntegerField(
        source='entry_fee_dc', read_only=True
    )
    total_pot_dc = serializers.IntegerField(read_only=True)
    prize_distribution = serializers.JSONField(read_only=True)

    # Schedule
    scheduled_at = serializers.DateTimeField(read_only=True)
    registration_opens_at = serializers.DateTimeField(read_only=True, allow_null=True)
    registration_closes_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # State
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Closure (REQUIRED on every match/lobby state response)
    closure_reason = serializers.CharField(read_only=True, allow_blank=True)
    closure_reason_display = serializers.CharField(
        source='get_closure_reason_display', read_only=True, allow_blank=True
    )
    closure_note = serializers.CharField(read_only=True, allow_blank=True)

    # Visibility
    is_public = serializers.BooleanField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)


class RoyaleLobbyDetailSerializer(RoyaleLobbyListSerializer):
    """Detail view: same as list, plus room credentials and timestamps.

    NOTE: ``room_id`` and ``room_password`` are blank until ``scheduled_at``
    has passed; the calling view is responsible for redaction logic.
    """

    room_id = serializers.CharField(read_only=True, allow_blank=True)
    room_password = serializers.CharField(read_only=True, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class RoyaleEntrySerializer(serializers.Serializer):
    """A single player's reservation."""

    id = serializers.UUIDField(read_only=True)
    lobby_id = serializers.UUIDField(source='lobby.id', read_only=True)
    lobby_reference_code = serializers.CharField(
        source='lobby.reference_code', read_only=True
    )

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    placement = serializers.IntegerField(read_only=True, allow_null=True)
    kills = serializers.IntegerField(read_only=True, allow_null=True)

    reserved_at = serializers.DateTimeField(read_only=True)
    scored_at = serializers.DateTimeField(read_only=True, allow_null=True)
    resolved_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # Closure (REQUIRED on every match/lobby state response)
    closure_reason = serializers.CharField(read_only=True, allow_blank=True)
    closure_reason_display = serializers.CharField(
        source='get_closure_reason_display', read_only=True, allow_blank=True
    )
    closure_note = serializers.CharField(read_only=True, allow_blank=True)
