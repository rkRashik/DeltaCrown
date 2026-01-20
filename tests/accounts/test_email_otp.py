import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

from apps.accounts.models import EmailOTP, PendingSignup

User = get_user_model()


@pytest.mark.django_db
def test_email_signup_and_verify_flow(client):
    # Sign up (creates pending signup + sends code)
    resp = client.post(reverse("account:signup"), {
        "username": "otpuser",
        "email": "otp@example.com",
        "password1": "S3curePassw0rd!",
        "password2": "S3curePassw0rd!",
    }, follow=True)
    assert resp.status_code == 200
    assert not User.objects.filter(username="otpuser").exists()
    pending = PendingSignup.objects.get(username="otpuser")

    # Email sent
    assert len(mail.outbox) == 1

    # Get last OTP from DB
    otp = EmailOTP.objects.filter(pending_signup=pending).order_by("-created_at").first()
    assert otp is not None

    # Verify (creates actual user)
    resp2 = client.post(reverse("account:verify_email"), {"code": otp.code}, follow=True)
    assert resp2.status_code == 200

    user = User.objects.get(username="otpuser")
    assert user.is_active
    assert user.is_verified
    assert not PendingSignup.objects.filter(pk=pending.pk).exists()

    # Landed on homepage after signup verification
    assert "DeltaCrown - Bangladesh" in resp2.content.decode()
