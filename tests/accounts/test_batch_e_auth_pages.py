"""Batch E: account pages keep their contracts and render the new accessible markup.

Contracts under test: CSRF + field names + safe `next` handling on login, no account enumeration on the reset
request page, reset-link invalid state, authenticated password-change pages render (they raised NoReverseMatch
before), and the OTP page exposes the one-time-code input attributes.
"""
import re
import secrets

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

User = get_user_model()
# Synthetic fixture credentials: generated per run, valid only for throwaway users in the test database.
def _synthetic_password():
    return "Tst-" + secrets.token_urlsafe(18)


PW = _synthetic_password()
NEW_PW = _synthetic_password()


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Login and reset views rate-limit per IP in the shared cache; keep this file's many requests from leaking into other suites."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="batche", email="batche@example.test", password=PW)


def _html(resp):
    return resp.content.decode()


@pytest.mark.django_db
def test_login_page_contract_and_markup(client):
    resp = client.get(reverse("account:login") + "?next=/tournaments/")
    html = _html(resp)
    assert resp.status_code == 200
    assert 'name="csrfmiddlewaretoken"' in html
    assert 'name="username"' in html and 'id="id_username"' in html and 'autocomplete="username"' in html
    assert 'name="password"' in html and 'autocomplete="current-password"' in html
    assert re.search(r'<input[^>]+name="next"[^>]+value="/tournaments/"', html)
    # labels point at real ids; no decorative orbs; one h1
    assert 'for="id_username"' in html and 'for="id_password"' in html
    assert "auth-orb" not in html and "auth-bg-pattern" not in html
    assert html.count("<h1") == html.count("</h1>") and 'class="auth-title"' in html


@pytest.mark.django_db
def test_login_failure_is_generic_and_announced(client, user):
    resp = client.post(reverse("account:login"), {"username": "batche", "password": "wrong"})
    html = _html(resp)
    assert resp.status_code == 200
    assert 'role="alert"' in html
    # same message whether or not the account exists (no enumeration)
    other = client.post(reverse("account:login"), {"username": "ghost-user", "password": "wrong"})
    assert re.search(r"correct username/email and password", _html(other))
    assert re.search(r"correct username/email and password", html)


@pytest.mark.django_db
def test_login_next_survives_and_redirects_safely(client, user):
    ok = client.post(reverse("account:login"), {"username": "batche", "password": PW, "next": "/tournaments/"})
    assert ok.status_code == 302 and ok.url == "/tournaments/"
    client.logout()
    evil = client.post(reverse("account:login"), {"username": "batche", "password": PW, "next": "https://evil.example/x"})
    assert evil.status_code == 302 and "evil.example" not in evil.url


@pytest.mark.django_db
def test_signup_page_has_mobile_friendly_inputs(client):
    html = _html(client.get(reverse("account:signup")))
    for name, ac in (("username", "username"), ("email", "email"), ("password1", "new-password"), ("password2", "new-password")):
        m = re.search(r'<input[^>]+name="%s"[^>]*>' % name, html)
        assert m, name
        assert 'autocomplete="%s"' % ac in m.group(0), (name, m.group(0))
    assert 'inputmode="email"' in html
    assert html.count("auth-pw__toggle") >= 2


@pytest.mark.django_db
def test_signup_errors_are_rendered_next_to_fields(client):
    resp = client.post(reverse("account:signup"), {"username": "x", "email": "bad", "password1": "a", "password2": "b"})
    html = _html(resp)
    assert resp.status_code == 200
    assert 'class="form-error"' in html
    assert 'aria-invalid="true"' in html


@pytest.mark.django_db
def test_otp_page_exposes_one_time_code_input(client):
    client.post(reverse("account:signup"), {"username": "otpuser", "email": "otp@example.test", "password1": PW, "password2": PW})
    assert len(mail.outbox) == 1
    resp = client.get(reverse("account:verify_email_otp"))
    html = _html(resp)
    code = re.search(r'<input[^>]+name="code"[^>]*>', html).group(0)
    assert 'inputmode="numeric"' in code and 'autocomplete="one-time-code"' in code and 'maxlength="6"' in code
    # the pending address is shown so people can spot a typo, and plain info messages are not rendered as errors
    assert "otp@example.test" in html
    assert "auth-alert--error" not in html


@pytest.mark.django_db
def test_wrong_otp_shows_alert_and_keeps_pending(client):
    client.post(reverse("account:signup"), {"username": "otpuser2", "email": "otp2@example.test", "password1": PW, "password2": PW})
    resp = client.post(reverse("account:verify_email_otp"), {"code": "000000"})
    assert resp.status_code == 200
    assert 'role="alert"' in _html(resp)
    assert not User.objects.filter(username="otpuser2").exists()


@pytest.mark.django_db
def test_password_reset_request_does_not_enumerate(client, user):
    known = client.post(reverse("account:password_reset"), {"email": "batche@example.test"})
    unknown = client.post(reverse("account:password_reset"), {"email": "nobody@example.test"})
    assert known.status_code == unknown.status_code == 302
    assert known.url == unknown.url == reverse("account:password_reset_done")
    page = _html(client.get(reverse("account:password_reset_done")))
    assert "If an account exists" in page


@pytest.mark.django_db
def test_password_reset_invalid_link_is_clear(client):
    resp = client.get(reverse("account:password_reset_confirm", args=["bad", "token"]))
    html = _html(resp)
    assert resp.status_code == 200
    assert "expired" in html and reverse("account:password_reset") in html
    assert 'name="new_password1"' not in html


@pytest.mark.django_db
def test_password_reset_full_flow(client, user):
    client.post(reverse("account:password_reset"), {"email": "batche@example.test"})
    body = mail.outbox[0].body
    link = re.search(r"https?://[^/\s]+(/account/reset/[^\s]+)", body).group(1)
    first = client.get(link, follow=True)
    html = _html(first)
    assert 'name="new_password1"' in html and 'for="id_new_password1"' in html and 'for="id_new_password2"' in html
    done = client.post(first.redirect_chain[-1][0] if first.redirect_chain else link, {"new_password1": NEW_PW, "new_password2": NEW_PW})
    assert done.status_code == 302 and done.url == reverse("account:password_reset_complete")
    user.refresh_from_db()
    assert user.check_password(NEW_PW)


@pytest.mark.django_db
def test_password_change_pages_render_for_signed_in_user(client, user):
    """Regression: both pages linked to the non-existent `user_profile:settings_v3` and returned HTTP 500."""
    client.force_login(user)
    form = client.get(reverse("account:password_change"))
    assert form.status_code == 200
    html = _html(form)
    assert 'autocomplete="current-password"' in html and html.count('autocomplete="new-password"') == 2
    assert reverse("user_profile:profile_settings") in html
    done = client.post(reverse("account:password_change"), {"old_password": PW, "new_password1": NEW_PW, "new_password2": NEW_PW})
    assert done.status_code == 302 and done.url == reverse("account:password_change_done")
    assert client.get(done.url).status_code == 200


@pytest.mark.django_db
def test_password_change_requires_login(client):
    resp = client.get(reverse("account:password_change"))
    assert resp.status_code == 302 and "login" in resp.url


@pytest.mark.django_db
@pytest.mark.parametrize("target", ["//evil.example/x", "https://evil.example/x", "http://evil.example", "javascript:alert(1)", "///evil.example"])
def test_login_blocks_external_and_protocol_relative_next(client, user, target):
    resp = client.post(reverse("account:login"), {"username": "batche", "password": PW, "next": target})
    assert resp.status_code == 302 and "evil" not in resp.url and not resp.url.startswith("//") and "javascript" not in resp.url


@pytest.mark.django_db
def test_login_next_via_get_and_authenticated_redirect(client, user):
    assert client.post(reverse("account:login") + "?next=/teams/", {"username": "batche", "password": PW}).url == "/teams/"
    # already signed in: GET with a hostile next must not bounce off-site, a local one still works
    bad = client.get(reverse("account:login") + "?next=//evil.example/x")
    assert bad.status_code == 302 and "evil" not in bad.url
    assert client.get(reverse("account:login") + "?next=/teams/").url == "/teams/"


@pytest.mark.django_db
def test_login_requires_csrf(user):
    from django.test import Client
    strict = Client(enforce_csrf_checks=True)
    assert strict.post(reverse("account:login"), {"username": "batche", "password": PW}).status_code == 403
    assert strict.post(reverse("account:password_reset"), {"email": "batche@example.test"}).status_code == 403


@pytest.mark.django_db
def test_google_entry_keeps_next_and_view_contract(client, settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "synthetic-client-id"
    html = _html(client.get(reverse("account:login") + "?next=/teams/"))
    assert reverse("account:google_login") + "?next=/teams/" in html


@pytest.mark.django_db
def test_reset_token_cannot_be_replayed(client, user):
    client.post(reverse("account:password_reset"), {"email": "batche@example.test"})
    link = re.search(r"https?://[^/\s]+(/account/reset/[^\s]+)", mail.outbox[0].body).group(1)
    page = client.get(link, follow=True)
    post_url = page.redirect_chain[-1][0] if page.redirect_chain else link
    assert client.post(post_url, {"new_password1": NEW_PW, "new_password2": NEW_PW}).status_code == 302
    replay = client.post(post_url, {"new_password1": PW, "new_password2": PW}, follow=True)
    assert 'name="new_password1"' not in _html(replay)
    user.refresh_from_db()
    assert user.check_password(NEW_PW) and not user.check_password(PW)
