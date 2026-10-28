"""Google OAuth redirects and state remain bound to the initiating session."""

from unittest.mock import Mock

import pytest
from django.urls import reverse


@pytest.fixture
def google_exchange(settings, monkeypatch):
    settings.GOOGLE_OAUTH_CLIENT_ID = "local-qa-client"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "local-qa-secret"
    settings.SITE_URL = "http://testserver"
    exchange = Mock(
        return_value={
            "sub": "redirect-qa",
            "email": "redirect-qa@example.com",
            "email_verified": True,
        }
    )
    monkeypatch.setattr("apps.accounts.oauth.exchange_code_for_userinfo", exchange)
    return exchange


@pytest.mark.django_db
@pytest.mark.parametrize(
    "next_url",
    [
        "https://foreign.example/",
        "//foreign.example/",
        "\\\\foreign.example/",
        "javascript:alert(1)",
    ],
)
def test_foreign_next_cannot_redirect_after_google_login(client, google_exchange, next_url):
    client.get(reverse("account:google_login"), {"next": next_url})
    state = client.session["google_oauth_state"]
    assert "google_oauth_next" not in client.session
    response = client.get(reverse("account:google_callback"), {"state": state, "code": "qa-code"})
    assert response.url == reverse("siteui:homepage")
    assert client.session.get("_auth_user_id")
    google_exchange.assert_called_once()


@pytest.mark.django_db
def test_safe_local_next_is_preserved_and_state_cannot_be_replayed(client, google_exchange):
    target = "/me/settings/?tab=passports"
    client.get(reverse("account:google_login"), {"next": target})
    state = client.session["google_oauth_state"]
    response = client.get(reverse("account:google_callback"), {"state": state, "code": "qa-code"})
    assert response.url == target
    replay = client.get(reverse("account:google_callback"), {"state": state, "code": "qa-code"})
    assert replay.url == reverse("account:login")
    google_exchange.assert_called_once()


@pytest.mark.django_db
def test_failed_exchange_consumes_state_without_authenticating(client, google_exchange):
    google_exchange.side_effect = ValueError("synthetic provider failure")
    client.get(reverse("account:google_login"))
    state = client.session["google_oauth_state"]
    for _ in range(2):
        response = client.get(
            reverse("account:google_callback"), {"state": state, "code": "qa-code"}
        )
        assert response.url == reverse("account:login")
    google_exchange.assert_called_once()
    assert not client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_stale_unsafe_session_next_is_checked_again_at_callback(client, google_exchange):
    session = client.session
    session["google_oauth_state"] = "local-qa-state"
    session["google_oauth_next"] = "https://foreign.example/"
    session.save()
    response = client.get(
        reverse("account:google_callback"), {"state": "local-qa-state", "code": "qa-code"}
    )
    assert response.url == reverse("siteui:homepage")


@pytest.mark.django_db
@pytest.mark.parametrize("has_foreign_state", [False, True])
def test_discord_missing_or_foreign_state_cannot_reach_provider(
    client, django_user_model, has_foreign_state
):
    from django.core.cache import cache
    from unittest.mock import patch

    owner = django_user_model.objects.create_user(
        "discord-state-owner", "discord-state-owner@example.com", "qa-password"
    )
    other = django_user_model.objects.create_user(
        "discord-state-other", "discord-state-other@example.com", "qa-password"
    )
    client.force_login(other)
    key = "discord_oauth_state:local-discord-state"
    cache.delete(key)
    if has_foreign_state:
        cache.set(key, {"user_id": owner.pk, "bot_state": ""}, 60)
    with patch("requests.post") as post, patch("requests.get") as get:
        response = client.get(
            reverse("account:discord_callback"), {"state": "local-discord-state", "code": "qa-code"}
        )
    assert response.status_code == 302
    post.assert_not_called()
    get.assert_not_called()
    assert cache.get(key) is None


@pytest.mark.django_db
def test_nonboolean_email_verification_cannot_link_an_existing_google_account(
    client, django_user_model, google_exchange
):
    from apps.accounts.models import GoogleIdentity

    owner = django_user_model.objects.create_user(
        "boolean-claim-owner", "boolean-claim-owner@example.com", "qa-password"
    )
    google_exchange.return_value = {
        "sub": "malformed-verification-qa",
        "email": owner.email,
        "email_verified": "false",
    }
    client.get(reverse("account:google_login"))
    state = client.session["google_oauth_state"]
    response = client.get(
        reverse("account:google_callback"), {"state": state, "code": "qa-code"}
    )
    assert response.url == reverse("account:login")
    assert not client.session.get("_auth_user_id")
    assert not GoogleIdentity.objects.filter(google_sub="malformed-verification-qa").exists()
