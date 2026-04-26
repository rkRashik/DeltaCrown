"""Recovery-flow guarantees for signup, verify, and resend.

These tests cover behavior the prior implementation got wrong:
* A stale ``PendingSignup`` (older than retention) must NOT block a new
  signup attempt with the same email or username.
* An active pending signup with the same email must be resumed cleanly:
  the form succeeds, the prior pending row is replaced, and a fresh OTP
  is delivered.
* A fully verified user with the same email must keep blocking signup.
* The verify and resend views must work even when the session has been
  lost (closed browser, new device) by accepting the email and looking
  the pending up.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EmailOTP, PendingSignup


User = get_user_model()


SIGNUP_PAYLOAD = {
    "username": "newcomer",
    "email": "newcomer@example.com",
    "password1": "S3curePassw0rd!",
    "password2": "S3curePassw0rd!",
}


def _force_pending_age(pending, *, days):
    """Backdate the pending so it falls outside STALE_ACCOUNT_RETENTION."""
    PendingSignup.objects.filter(pk=pending.pk).update(
        created_at=timezone.now() - timedelta(days=days),
    )


@pytest.mark.django_db
class TestSignupStaleRecovery:
    def test_stale_pending_with_same_username_does_not_block(self, client):
        stale = PendingSignup.objects.create(
            username=SIGNUP_PAYLOAD["username"],
            email="someone-else@example.com",
            password_hash=make_password("OldPass123!"),
        )
        _force_pending_age(stale, days=2)

        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        assert resp.status_code == 200
        assert PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ).exists()
        assert not PendingSignup.objects.filter(pk=stale.pk).exists()

    def test_stale_pending_with_same_email_is_replaced(self, client):
        stale = PendingSignup.objects.create(
            username="oldname",
            email=SIGNUP_PAYLOAD["email"],
            password_hash=make_password("OldPass123!"),
        )
        _force_pending_age(stale, days=2)

        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        assert resp.status_code == 200
        # Only one pending exists now, with the new username.
        rows = list(PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ))
        assert len(rows) == 1
        assert rows[0].username == SIGNUP_PAYLOAD["username"]

    def test_active_pending_same_email_is_resumed_with_fresh_otp(self, client):
        prior = PendingSignup.objects.create(
            username="oldname",
            email=SIGNUP_PAYLOAD["email"],
            password_hash=make_password("OldPass123!"),
        )
        EmailOTP.issue(pending_signup=prior)
        # Active pending — within retention.
        assert (timezone.now() - prior.created_at) < EmailOTP.STALE_ACCOUNT_RETENTION

        before_count = mail.outbox.__len__()
        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        assert resp.status_code == 200

        rows = list(PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ))
        assert len(rows) == 1
        assert rows[0].username == SIGNUP_PAYLOAD["username"]
        # Existing pending signup is reused idempotently, old OTPs are removed,
        # and a fresh OTP is issued for the same pending row.
        assert rows[0].pk == prior.pk
        assert EmailOTP.objects.filter(pending_signup=rows[0]).count() == 1
        assert len(mail.outbox) == before_count + 1

    def test_active_pending_same_email_and_username_is_resumed(self, client):
        prior = PendingSignup.objects.create(
            username=SIGNUP_PAYLOAD["username"],
            email=SIGNUP_PAYLOAD["email"],
            password_hash=make_password("OldPass123!"),
        )

        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        assert resp.status_code == 200
        rows = list(PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ))
        assert len(rows) == 1
        assert rows[0].pk == prior.pk

    def test_active_pending_username_collision_different_email_still_blocks(
        self, client,
    ):
        PendingSignup.objects.create(
            username=SIGNUP_PAYLOAD["username"],
            email="someone-else@example.com",
            password_hash=make_password("OldPass123!"),
        )

        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD)
        assert resp.status_code == 200
        body = resp.content.decode()
        # Form re-rendered with the friendly recovery hint
        assert "pending verification" in body.lower()
        assert not PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ).exists()

    def test_verified_user_with_same_email_blocks_signup(self, client):
        User.objects.create_user(
            username="exists",
            email=SIGNUP_PAYLOAD["email"],
            password="ExistingPass123!",
        )

        resp = client.post(reverse("account:signup"), SIGNUP_PAYLOAD)
        assert resp.status_code == 200
        assert "already in use" in resp.content.decode().lower()
        assert not PendingSignup.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
        ).exists()


@pytest.mark.django_db
class TestVerifyRecovery:
    def _signup(self, client):
        client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        return PendingSignup.objects.get(email__iexact=SIGNUP_PAYLOAD["email"])

    def test_verify_recovers_when_session_is_lost(self, client):
        pending = self._signup(client)
        otp = EmailOTP.objects.filter(pending_signup=pending).latest("created_at")
        # Drop session entirely — simulate new browser/device.
        client.cookies.clear()
        client.session.flush()

        resp = client.post(
            reverse("account:verify_email_otp"),
            {"code": otp.code, "email": SIGNUP_PAYLOAD["email"]},
            follow=True,
        )
        assert resp.status_code == 200
        assert User.objects.filter(
            email__iexact=SIGNUP_PAYLOAD["email"],
            is_verified=True,
        ).exists()

    def test_verify_get_without_session_still_renders_recovery_form(self, client):
        resp = client.get(reverse("account:verify_email_otp"))
        assert resp.status_code == 200
        body = resp.content.decode()
        assert "verification code" in body.lower()
        assert 'name="email"' in body

    def test_verify_post_without_session_or_email_redirects_to_signup(self, client):
        resp = client.post(
            reverse("account:verify_email_otp"),
            {"code": "000000"},
            follow=False,
        )
        assert resp.status_code == 302
        assert reverse("account:signup") in resp["Location"]


@pytest.mark.django_db
class TestResendRecovery:
    def _signup(self, client):
        client.post(reverse("account:signup"), SIGNUP_PAYLOAD, follow=True)
        return PendingSignup.objects.get(email__iexact=SIGNUP_PAYLOAD["email"])

    def test_resend_recovers_via_email_when_session_is_lost(self, client):
        self._signup(client)
        before = len(mail.outbox)
        client.cookies.clear()
        client.session.flush()

        resp = client.post(
            reverse("account:resend_otp"),
            {"email": SIGNUP_PAYLOAD["email"]},
            follow=False,
        )
        assert resp.status_code == 302
        assert reverse("account:verify_email_otp") in resp["Location"]
        assert len(mail.outbox) == before + 1

    def test_resend_without_session_or_email_bounces_to_signup(self, client):
        resp = client.post(reverse("account:resend_otp"), follow=False)
        assert resp.status_code == 302
        assert reverse("account:signup") in resp["Location"]
