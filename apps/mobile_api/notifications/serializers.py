"""Mobile-safe notification serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification

from ..models import MobileDeviceToken


SAFE_ACTION_DATA_KEYS = {
    "action",
    "url",
    "path",
    "deep_link",
    "screen",
    "params",
    "tournament_id",
    "match_id",
    "team_id",
    "request_id",
}


class MobileDeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512, allow_blank=False)
    platform = serializers.ChoiceField(choices=MobileDeviceToken.Platform.choices)
    device_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)


def serialize_notification(notification: Notification) -> dict:
    message = notification.message or notification.body or ""
    action_data = notification.action_data if isinstance(notification.action_data, dict) else {}
    safe_action_data = {key: value for key, value in action_data.items() if key in SAFE_ACTION_DATA_KEYS}

    action = None
    action_url = notification.action_url or notification.url
    if action_url or notification.action_label or safe_action_data:
        action = {
            "label": notification.action_label or "",
            "url": action_url or "",
            "deep_link": safe_action_data.get("deep_link") or safe_action_data.get("path") or action_url or "",
            "data": safe_action_data,
        }

    related = {}
    if notification.tournament_id:
        related["tournament_id"] = notification.tournament_id
    if notification.match_id:
        related["match_id"] = notification.match_id
    if notification.action_object_id and notification.action_type:
        related["action_object"] = {
            "id": notification.action_object_id,
            "type": notification.action_type,
        }

    return {
        "id": notification.id,
        "title": notification.title,
        "message": message,
        "body": notification.body,
        "category": notification.category,
        "type": notification.type,
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "action": action,
        "related": related,
        "image_url": notification.image_url or None,
        "avatar_url": notification.avatar_url or None,
    }


def serialize_device_token(device_token: MobileDeviceToken) -> dict:
    return {
        "id": device_token.id,
        "platform": device_token.platform,
        "device_id": device_token.device_id or None,
        "app_version": device_token.app_version or None,
        "is_active": device_token.is_active,
        "updated_at": device_token.updated_at.isoformat() if device_token.updated_at else None,
    }
