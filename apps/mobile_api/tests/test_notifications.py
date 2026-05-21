"""Tests for mobile notification endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.mobile_api.models import MobileDeviceToken
from apps.notifications.models import Notification


User = get_user_model()


def create_notification(user, **overrides):
    defaults = {
        "recipient": user,
        "title": "Match scheduled",
        "body": "Your next match is ready.",
        "message": "Your next match is ready.",
        "category": Notification.NotificationCategory.TOURNAMENT,
        "notification_type": Notification.NotificationCategory.TOURNAMENT,
        "type": Notification.Type.MATCH_SCHEDULED,
        "priority": Notification.Priority.NORMAL,
        "action_url": "/tournaments/mobile-cup/hub/",
        "action_label": "Open",
        "action_data": {
            "deep_link": "deltacrown://matches/1",
            "match_id": 1,
            "admin_note": "hidden",
        },
        "tournament_id": 7,
        "match_id": 1,
    }
    defaults.update(overrides)
    return Notification.objects.create(**defaults)


class MobileNotificationEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("notifyuser", "notify@example.com", "testpass123!")
        self.other_user = User.objects.create_user("othernotify", "othernotify@example.com", "testpass123!")
        self.client.force_authenticate(self.user)

    def test_notifications_list_requires_auth(self):
        response = APIClient().get(reverse("mobile_api_v1:notifications:notifications"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])

    def test_notifications_list_returns_only_current_users_notifications(self):
        own = create_notification(self.user)
        create_notification(self.other_user, title="Other user notification")

        response = self.client.get(reverse("mobile_api_v1:notifications:notifications"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        notifications = body["data"]["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], own.id)

    def test_unread_count_returns_correct_count(self):
        create_notification(self.user, is_read=False)
        create_notification(self.user, is_read=True)
        create_notification(self.other_user, is_read=False)

        response = self.client.get(reverse("mobile_api_v1:notifications:unread_count"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)

    def test_mark_read_only_marks_current_users_notification(self):
        notification = create_notification(self.user, is_read=False)

        response = self.client.post(
            reverse("mobile_api_v1:notifications:mark_read", args=[notification.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_read_rejects_another_users_notification(self):
        notification = create_notification(self.other_user, is_read=False)

        response = self.client.post(
            reverse("mobile_api_v1:notifications:mark_read", args=[notification.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_read_all_marks_current_users_notifications_only(self):
        own = create_notification(self.user, is_read=False)
        other = create_notification(self.other_user, is_read=False)

        response = self.client.post(reverse("mobile_api_v1:notifications:read_all"), {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated"], 1)
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(own.is_read)
        self.assertFalse(other.is_read)

    def test_device_token_create_update_works(self):
        url = reverse("mobile_api_v1:notifications:device_token")
        response = self.client.post(
            url,
            {
                "token": "token-123",
                "platform": "android",
                "device_id": "device-a",
                "app_version": "1.0.0",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["data"]["created"])
        self.assertEqual(MobileDeviceToken.objects.count(), 1)

        response = self.client.post(
            url,
            {
                "token": "token-123",
                "platform": "ios",
                "device_id": "device-b",
                "app_version": "1.0.1",
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["created"])
        self.assertEqual(MobileDeviceToken.objects.count(), 1)
        token = MobileDeviceToken.objects.get(token="token-123")
        self.assertEqual(token.platform, "ios")
        self.assertEqual(token.device_id, "device-b")
        self.assertFalse(token.is_active)

    def test_device_token_deactivate_delete_works(self):
        MobileDeviceToken.objects.create(
            user=self.user,
            token="delete-token",
            platform=MobileDeviceToken.Platform.ANDROID,
            is_active=True,
        )

        response = self.client.delete(
            reverse("mobile_api_v1:notifications:device_token"),
            {"token": "delete-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["deactivated"], 1)
        token = MobileDeviceToken.objects.get(token="delete-token")
        self.assertFalse(token.is_active)

    def test_payload_does_not_leak_internal_admin_fields(self):
        create_notification(self.user)

        response = self.client.get(reverse("mobile_api_v1:notifications:notifications"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["notifications"][0]
        self.assertNotIn("recipient_id", payload)
        self.assertNotIn("is_delivered", payload)
        self.assertNotIn("html_text", payload)
        self.assertNotIn("event", payload)
        self.assertNotIn("admin_note", payload["action"]["data"])
