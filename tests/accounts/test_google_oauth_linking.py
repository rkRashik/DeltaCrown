"""Google OAuth linking behavior — safety + same-email linking.

Covers:
- existing email/password user + verified Google email → links, no duplicate
- existing GoogleIdentity → reuses the linked user
- no existing user → creates a new user as before
- unverified Google email matching an existing user → blocked, no duplicate
- multiple users with same email → fails safely
- scheduled-deletion + inactive accounts → blocked safely
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts import oauth
from apps.accounts.models import AccountDeletionRequest, GoogleIdentity


User = get_user_model()


@pytest.fixture
def google_settings(settings):
    settings.SITE_URL = "http://testserver"
    settings.GOOGLE_OAUTH_CLIENT_ID = "id"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "secret"
    return settings


def _start_state(client):
    sess = client.session
    sess["google_oauth_state"] = "state-abc"
    sess.save()


def _patch_exchange(monkeypatch, **payload):
    payload.setdefault("sub", "google-sub-default")
    payload.setdefault("email", "default@example.com")
    payload.setdefault("email_verified", True)
    payload.setdefault("name", "Default User")

    def fake_exchange(**_):
        return payload
    monkeypatch.setattr(oauth, "exchange_code_for_userinfo", fake_exchange)


def _hit_callback(client):
    return client.get(reverse("account:google_callback"), {"state": "state-abc", "code": "x"})


@pytest.mark.django_db
def test_links_to_existing_user_when_verified_email_matches(client, google_settings, monkeypatch):
    existing = User.objects.create_user(
        username="ranger", email="ranger@example.com", password="Pw!12345"
    )
    existing.is_verified = True
    existing.email_verified_at = timezone.now()
    existing.save(update_fields=["is_verified", "email_verified_at"])

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-ranger",
        email="ranger@example.com",
        email_verified=True,
        name="Ranger",
    )

    resp = _hit_callback(client)

    assert resp.status_code in (301, 302)
    # No duplicate: still exactly one user with that email.
    assert User.objects.filter(email__iexact="ranger@example.com").count() == 1
    same = User.objects.get(email__iexact="ranger@example.com")
    assert same.id == existing.id
    # And the Google identity was attached to *that* user.
    identity = GoogleIdentity.objects.get(google_sub="sub-ranger")
    assert identity.user_id == existing.id
    # Session reflects an authenticated login.
    assert client.session.get("_auth_user_id") == str(existing.id)


@pytest.mark.django_db
def test_existing_google_identity_reuses_linked_user(client, google_settings, monkeypatch):
    existing = User.objects.create_user(
        username="repeat", email="repeat@example.com", password="Pw!12345"
    )
    GoogleIdentity.objects.create(user=existing, google_sub="sub-repeat", email="repeat@example.com")

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-repeat",
        # Note: email returned by Google differs in case; sub wins.
        email="REPEAT@example.com",
        email_verified=True,
        name="Repeat",
    )

    resp = _hit_callback(client)

    assert resp.status_code in (301, 302)
    assert User.objects.filter(email__iexact="repeat@example.com").count() == 1
    assert GoogleIdentity.objects.filter(google_sub="sub-repeat").count() == 1
    assert client.session.get("_auth_user_id") == str(existing.id)


@pytest.mark.django_db
def test_no_existing_email_creates_new_google_user(client, google_settings, monkeypatch):
    assert not User.objects.filter(email__iexact="fresh@example.com").exists()

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-fresh",
        email="fresh@example.com",
        email_verified=True,
        name="Fresh User",
    )

    resp = _hit_callback(client)

    assert resp.status_code in (301, 302)
    created = User.objects.get(email__iexact="fresh@example.com")
    assert created.is_verified is True
    identity = GoogleIdentity.objects.get(google_sub="sub-fresh")
    assert identity.user_id == created.id
    assert client.session.get("_auth_user_id") == str(created.id)


@pytest.mark.django_db
def test_unverified_email_does_not_auto_link_to_existing_user(client, google_settings, monkeypatch):
    existing = User.objects.create_user(
        username="legit", email="legit@example.com", password="Pw!12345"
    )
    existing.is_verified = True
    existing.save(update_fields=["is_verified"])

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-attacker",
        email="legit@example.com",
        email_verified=False,  # Google says NOT verified
        name="Attacker",
    )

    resp = _hit_callback(client)

    # Bounced back to the login page; no link created, no duplicate.
    assert resp.status_code in (301, 302)
    assert resp.url.endswith(reverse("account:login"))
    assert User.objects.filter(email__iexact="legit@example.com").count() == 1
    assert not GoogleIdentity.objects.filter(google_sub="sub-attacker").exists()
    # The attacker is not logged in as the legit user.
    assert client.session.get("_auth_user_id") != str(existing.id)


@pytest.mark.django_db
def test_unverified_email_with_no_existing_user_still_creates_account(client, google_settings, monkeypatch):
    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-newunv",
        email="newunv@example.com",
        email_verified=False,
        name="New Unverified",
    )

    resp = _hit_callback(client)

    assert resp.status_code in (301, 302)
    user = User.objects.get(email__iexact="newunv@example.com")
    # is_verified stays False because Google didn't confirm the email.
    assert user.is_verified is False
    assert GoogleIdentity.objects.filter(google_sub="sub-newunv", user=user).exists()


@pytest.mark.django_db
def test_multiple_users_with_same_email_fails_safely(client, google_settings, monkeypatch):
    # `User.email` is unique, so we can't insert two rows with the literal
    # same email — but case-differing emails can co-exist. Force the
    # ambiguous state and confirm the view refuses to guess.
    u1 = User.objects.create_user(username="amb1", email="amb@example.com", password="Pw!12345")
    u2 = User.objects.create_user(username="amb2", email="AMB@example.com", password="Pw!12345")
    assert User.objects.filter(email__iexact="amb@example.com").count() == 2

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-amb",
        email="amb@example.com",
        email_verified=True,
        name="Ambiguous",
    )

    resp = _hit_callback(client)

    assert resp.status_code in (301, 302)
    assert resp.url.endswith(reverse("account:login"))
    # No identity, no new user.
    assert not GoogleIdentity.objects.filter(google_sub="sub-amb").exists()
    assert User.objects.filter(email__iexact="amb@example.com").count() == 2
    assert client.session.get("_auth_user_id") not in {str(u1.id), str(u2.id)}


@pytest.mark.django_db
def test_scheduled_deletion_user_cannot_link(client, google_settings, monkeypatch):
    existing = User.objects.create_user(
        username="deleter", email="deleter@example.com", password="Pw!12345"
    )
    existing.is_verified = True
    existing.save(update_fields=["is_verified"])
    AccountDeletionRequest.objects.create(
        user=existing,
        scheduled_for=timezone.now() + timezone.timedelta(days=14),
    )

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-deleter",
        email="deleter@example.com",
        email_verified=True,
        name="Deleter",
    )

    resp = _hit_callback(client)

    assert resp.url.endswith(reverse("account:login"))
    assert not GoogleIdentity.objects.filter(google_sub="sub-deleter").exists()
    assert client.session.get("_auth_user_id") != str(existing.id)


@pytest.mark.django_db
def test_inactive_user_cannot_link(client, google_settings, monkeypatch):
    existing = User.objects.create_user(
        username="ghost", email="ghost@example.com", password="Pw!12345"
    )
    existing.is_active = False
    existing.is_verified = True
    existing.save(update_fields=["is_active", "is_verified"])

    _start_state(client)
    _patch_exchange(
        monkeypatch,
        sub="sub-ghost",
        email="ghost@example.com",
        email_verified=True,
        name="Ghost",
    )

    resp = _hit_callback(client)

    assert resp.url.endswith(reverse("account:login"))
    assert not GoogleIdentity.objects.filter(google_sub="sub-ghost").exists()
    assert client.session.get("_auth_user_id") != str(existing.id)
