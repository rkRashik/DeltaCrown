"""Mobile notification endpoints."""
from __future__ import annotations

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from apps.notifications.models import Notification

from ..base import MobileApiView
from ..models import MobileDeviceToken
from ..responses import error_response, success_response
from ..tournaments.serializers import paginate_queryset
from .serializers import MobileDeviceTokenSerializer, serialize_device_token, serialize_notification


class MobileNotificationListView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).order_by("-created_at", "-id")

        unread_only = request.query_params.get("unread_only")
        if unread_only is not None and unread_only.lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(is_read=False)

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=str(category).upper())

        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), 20)
        page_obj, pagination = paginate_queryset(queryset, page, page_size)
        return success_response(
            {
                "notifications": [serialize_notification(item) for item in page_obj.object_list],
                "pagination": pagination,
            }
        )


class MobileNotificationUnreadCountView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return success_response({"count": count})


class MobileNotificationReadView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        notification = Notification.objects.filter(id=notification_id, recipient=request.user).first()
        if notification is None:
            return error_response("not_found", "Notification not found.", status=http_status.HTTP_404_NOT_FOUND)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return success_response({"notification": serialize_notification(notification)})


class MobileNotificationReadAllView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True, read_at=now)
        return success_response({"updated": updated})


class MobileDeviceTokenView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MobileDeviceTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                "validation_error",
                "Validation failed.",
                details=serializer.errors,
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        device_token, created = MobileDeviceToken.objects.update_or_create(
            token=data["token"],
            defaults={
                "user": request.user,
                "platform": data["platform"],
                "device_id": data.get("device_id", ""),
                "app_version": data.get("app_version", ""),
                "is_active": data.get("is_active", True),
            },
        )
        return success_response(
            {"device_token": serialize_device_token(device_token), "created": created},
            status=http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK,
        )

    def delete(self, request):
        token = (request.data.get("token") or "").strip()
        queryset = MobileDeviceToken.objects.filter(user=request.user)
        if token:
            queryset = queryset.filter(token=token)
        updated = queryset.update(is_active=False, updated_at=timezone.now())
        return success_response({"deactivated": updated})


def _positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default
