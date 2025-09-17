import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

from apps.accounts.models import PendingSignup

User = get_user_model()


@pytest.mark.django_db
def test_login_page_renders(client):
    resp = client.get(reverse("account:login"))
    assert resp.status_code == 200
    assert "Sign in" in resp.content.decode()


@pytest.mark.django_db
def test_signup_creates_user_and_redirects(client):
    url = reverse("account:signup")
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password1": "S3curePassw0rd!",
        "password2": "S3curePassw0rd!",
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200

    # No persistent user until verification completes
    assert not User.objects.filter(username="testuser").exists()
    pending = PendingSignup.objects.get(username="testuser")
    assert pending.email == "test@example.com"

    # Verify redirect path goes through the email verification flow
    chain_urls = [u for (u, _status) in resp.redirect_chain]
    verify_url = reverse("account:verify_email_otp")
    assert any(verify_url in u for u in chain_urls)
    assert "verification" in resp.content.decode().lower()

    # Email sent with OTP
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_profile_requires_login(client):
    resp = client.get(reverse("account:profile"))
    # should redirect to login
    assert resp.status_code in (302, 301)
    assert reverse("account:login") in resp.url


@pytest.mark.django_db
def test_password_reset_sends_email(client):
    User.objects.create_user(username="alice", email="alice@example.com", password="XyZ!2345678")
    resp = client.post(reverse("account:password_reset"), {"email": "alice@example.com"}, follow=True)
    assert resp.status_code == 200
    assert len(mail.outbox) == 1
    subj = mail.outbox[0].subject or ""
    assert "reset" in subj.lower()

