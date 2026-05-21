"""Tests for the /api/mobile/v1/ chassis (health + me)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


User = get_user_model()


class HealthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:health")

    def test_health_returns_envelope(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["success"], True)
        self.assertIsNone(body["error"])

        data = body["data"]
        self.assertEqual(data["service"], "DeltaCrown Mobile API")
        self.assertEqual(data["version"], "v1")
        self.assertEqual(data["status"], "ok")

    def test_health_does_not_require_authentication(self):
        # No credentials supplied — must still succeed.
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, 200)


class MeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:me")
        self.user = User.objects.create_user(
            username="ranger",
            email="ranger@example.com",
            password="testpass123!",
        )

    def test_me_unauthenticated_returns_401_envelope(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertEqual(body["success"], False)
        self.assertIsNone(body["data"])
        self.assertEqual(body["error"]["code"], "not_authenticated")
        self.assertIn("message", body["error"])
        self.assertIsInstance(body["error"]["details"], dict)

    def test_me_authenticated_returns_compact_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["success"], True)
        self.assertIsNone(body["error"])

        data = body["data"]
        self.assertEqual(data["id"], self.user.id)
        self.assertEqual(data["username"], "ranger")
        self.assertEqual(data["email"], "ranger@example.com")

        profile = data["profile"]
        self.assertIn("display_name", profile)
        self.assertIn("public_id", profile)
        self.assertIn("country", profile)
        self.assertIn("region", profile)
        self.assertIn("profile_completed", profile)
        self.assertIn("completion_percentage", profile)
        self.assertIsInstance(profile["profile_completed"], bool)
        self.assertIsInstance(profile["completion_percentage"], int)

    def test_me_serializer_tolerates_missing_userprofile(self):
        # A post_save signal in user_profile auto-recreates UserProfile rows on
        # any User.save, so we can't reliably exercise a profileless user via
        # the full request path. Verify the serializer itself emits safe
        # null/default values when the profile relation is absent.
        from apps.mobile_api.serializers import serialize_mobile_profile

        data = serialize_mobile_profile(None)
        self.assertIsNone(data["display_name"])
        self.assertIsNone(data["public_id"])
        self.assertIsNone(data["country"])
        self.assertIsNone(data["region"])
        self.assertEqual(data["profile_completed"], False)
        self.assertEqual(data["completion_percentage"], 0)
