import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()

@pytest.mark.django_db
def test_email_signup_and_verify_flow(client):
    # Sign up (creates inactive user + sends code)
    resp = client.post(reverse("account:signup"), {
        "username": "otpuser",
        "email": "otp@example.com",
        "password1": "S3curePassw0rd!",
        "password2": "S3curePassw0rd!",
    }, follow=True)
    assert resp.status_code == 200
    u = User.objects.get(username="otpuser")
    assert not u.is_active
    # Email sent
    assert len(mail.outbox) == 1
    # Get last OTP from DB
    from apps.accounts.models import EmailOTP
    otp = EmailOTP.objects.filter(user=u).order_by("-created_at").first()
    assert otp is not None

    # Verify
    resp2 = client.post(reverse("account:verify_email"), {"code": otp.code}, follow=True)
    assert resp2.status_code == 200
    u.refresh_from_db()
    assert u.is_active
    # Landed on profile
    assert "Profile" in resp2.content.decode()
