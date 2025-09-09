import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_google_oauth_creates_user_and_logs_in(client, settings, monkeypatch):
    # Fake settings
    settings.SITE_URL = "http://testserver"
    settings.GOOGLE_OAUTH_CLIENT_ID = "id"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "secret"

    # Simulate login start sets state in session
    sess = client.session
    sess["google_oauth_state"] = "abc123"
    sess.save()

    # Monkeypatch exchange to avoid network
    from apps.accounts import oauth
    def fake_exchange(**kwargs):
        return {"sub": "sub123", "email": "guser@example.com", "email_verified": True, "name": "G User"}
    monkeypatch.setattr(oauth, "exchange_code_for_userinfo", fake_exchange)

    # Call callback with state + code
    resp = client.get(reverse("accounts:google_callback"), {"state": "abc123", "code": "dummy"})
    assert resp.status_code in (302, 301)
    assert resp.url.endswith("/accounts/profile/")
    assert User.objects.filter(email="guser@example.com").exists()
