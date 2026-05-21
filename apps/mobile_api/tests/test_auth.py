"""Tests for /api/mobile/v1/auth/* endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountDeletionRequest, EmailOTP, PendingSignup


User = get_user_model()


def _verified_user(**overrides):
    defaults = {
        "username": "playerone",
        "email": "playerone@example.com",
        "password": "MobilePw!12345",
    }
    defaults.update(overrides)
    user = User.objects.create_user(**defaults)
    user.is_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["is_verified", "email_verified_at"])
    return user


class LoginEndpointTests(TestCase):
    url_name = "mobile_api_v1:auth:login"

    def setUp(self):
        self.client = APIClient()
        self.url = reverse(self.url_name)
        self.user = _verified_user()

    def test_login_with_username(self):
        resp = self.client.post(
            self.url, {"identifier": "playerone", "password": "MobilePw!12345"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])
        self.assertEqual(body["data"]["user"]["id"], self.user.id)
        self.assertEqual(body["data"]["user"]["username"], "playerone")
        self.assertIn("profile", body["data"]["user"])

    def test_login_with_email(self):
        resp = self.client.post(
            self.url,
            {"identifier": "playerone@example.com", "password": "MobilePw!12345"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["user"]["email"], "playerone@example.com")

    def test_invalid_credentials_returns_envelope(self):
        resp = self.client.post(
            self.url, {"identifier": "playerone", "password": "wrong"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertFalse(body["success"])
        self.assertIsNone(body["data"])
        self.assertEqual(body["error"]["code"], "invalid_credentials")

    def test_unknown_identifier_does_not_reveal_existence(self):
        resp = self.client.post(
            self.url,
            {"identifier": "nobody@example.com", "password": "irrelevant"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "invalid_credentials")

    def test_missing_fields_returns_validation_error(self):
        resp = self.client.post(self.url, {"identifier": ""}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "invalid_request")

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        resp = self.client.post(
            self.url, {"identifier": "playerone", "password": "MobilePw!12345"}, format="json"
        )
        # ModelBackend short-circuits inactive users before our backend can
        # surface a specific reason — both 401 and 403 are acceptable as long
        # as no tokens leak.
        self.assertIn(resp.status_code, (401, 403))
        self.assertFalse(resp.json()["success"])
        self.assertNotIn("access", resp.json().get("data") or {})

    def test_scheduled_deletion_blocks_login(self):
        AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=timezone.now() + timezone.timedelta(days=14),
        )
        resp = self.client.post(
            self.url, {"identifier": "playerone", "password": "MobilePw!12345"}, format="json"
        )
        # EmailOrUsernameBackend short-circuits scheduled deletions; the
        # response is the generic invalid_credentials envelope.
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "invalid_credentials")


class RegisterEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:auth:register")

    def test_register_creates_pending_signup_and_requires_otp(self):
        resp = self.client.post(
            self.url,
            {
                "username": "newhope",
                "email": "newhope@example.com",
                "password": "StrongPw!12345",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["data"]["otp_required"])
        self.assertEqual(body["data"]["email"], "newhope@example.com")
        pending = PendingSignup.objects.get(pk=body["data"]["pending_signup_id"])
        self.assertEqual(pending.email, "newhope@example.com")
        self.assertTrue(EmailOTP.objects.filter(pending_signup=pending, is_used=False).exists())
        # No real User created yet.
        self.assertFalse(User.objects.filter(email__iexact="newhope@example.com").exists())

    def test_duplicate_email_rejected(self):
        _verified_user(username="taken", email="taken@example.com")
        resp = self.client.post(
            self.url,
            {"username": "fresh", "email": "TAKEN@example.com", "password": "StrongPw!12345"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "email_taken")

    def test_duplicate_username_rejected(self):
        _verified_user(username="taken", email="othername@example.com")
        resp = self.client.post(
            self.url,
            {"username": "Taken", "email": "fresh@example.com", "password": "StrongPw!12345"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "username_taken")

    def test_weak_password_rejected(self):
        resp = self.client.post(
            self.url,
            {"username": "weakpw", "email": "weakpw@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "weak_password")


class VerifyOtpEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("mobile_api_v1:auth:register")
        self.verify_url = reverse("mobile_api_v1:auth:verify_otp")
        self.client.post(
            self.register_url,
            {
                "username": "verifyme",
                "email": "verifyme@example.com",
                "password": "StrongPw!12345",
            },
            format="json",
        )
        self.pending = PendingSignup.objects.get(email="verifyme@example.com")
        self.otp = EmailOTP.objects.get(pending_signup=self.pending, is_used=False)

    def test_verify_creates_user_and_returns_jwt_pair(self):
        resp = self.client.post(
            self.verify_url,
            {"pending_signup_id": self.pending.id, "otp": self.otp.code},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])
        self.assertEqual(body["data"]["user"]["email"], "verifyme@example.com")
        # Real user was created and PendingSignup cleaned up.
        user = User.objects.get(email__iexact="verifyme@example.com")
        self.assertTrue(user.is_verified)
        self.assertFalse(PendingSignup.objects.filter(pk=self.pending.pk).exists())

    def test_wrong_code_returns_envelope(self):
        resp = self.client.post(
            self.verify_url,
            {"pending_signup_id": self.pending.id, "otp": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "otp_invalid")

    def test_unknown_pending_id_returns_safe_error(self):
        resp = self.client.post(
            self.verify_url,
            {"pending_signup_id": 999_999, "otp": "123456"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "pending_signup_not_found")


class ResendOtpEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:auth:resend_otp")
        self.client.post(
            reverse("mobile_api_v1:auth:register"),
            {
                "username": "resender",
                "email": "resender@example.com",
                "password": "StrongPw!12345",
            },
            format="json",
        )
        self.pending = PendingSignup.objects.get(email="resender@example.com")

    def test_resend_issues_new_code(self):
        first_otp_pk = EmailOTP.objects.get(pending_signup=self.pending, is_used=False).pk
        resp = self.client.post(self.url, {"pending_signup_id": self.pending.id}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        # New OTP row exists, distinct from the first one.
        latest = EmailOTP.objects.filter(pending_signup=self.pending).order_by("-created_at").first()
        self.assertIsNotNone(latest)
        self.assertNotEqual(latest.pk, first_otp_pk)

    def test_resend_unknown_pending_id_returns_envelope(self):
        resp = self.client.post(self.url, {"pending_signup_id": 999_999}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "pending_signup_not_found")


class RefreshEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:auth:refresh")
        self.user = _verified_user(username="refreshme", email="refreshme@example.com")
        self.refresh = RefreshToken.for_user(self.user)

    def test_refresh_returns_new_access_in_envelope(self):
        resp = self.client.post(self.url, {"refresh": str(self.refresh)}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("access", body["data"])

    def test_invalid_refresh_returns_envelope(self):
        resp = self.client.post(self.url, {"refresh": "not-a-token"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "invalid_refresh_token")


class LogoutEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("mobile_api_v1:auth:logout")
        self.user = _verified_user(username="bye", email="bye@example.com")
        self.refresh = RefreshToken.for_user(self.user)

    def test_logout_returns_envelope(self):
        resp = self.client.post(self.url, {"refresh": str(self.refresh)}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["message"], "Logged out successfully.")
        # `blacklisted` reflects whether server-side invalidation actually
        # happened. With the blacklist app not in INSTALLED_APPS this is False.
        self.assertIn("blacklisted", body["data"])

    def test_logout_invalid_token_returns_envelope(self):
        resp = self.client.post(self.url, {"refresh": "garbage"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "invalid_refresh_token")
