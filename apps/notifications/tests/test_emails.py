import types
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings

from apps.notifications import email as email_utils

pytestmark = pytest.mark.django_db


def _dummy_match(**overrides):
    # Build a lightweight object with the attrs our helpers read.
    m = types.SimpleNamespace(
        id=42,
        round_no=1,
        score_a=2,
        score_b=1,
        tournament=types.SimpleNamespace(name="Test Cup"),
        user_a=types.SimpleNamespace(display_name="Alice"),
        user_b=types.SimpleNamespace(display_name="Bob"),
        team_a=None,
        team_b=None,
    )
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _dummy_dispute(**overrides):
    d = types.SimpleNamespace(
        id=5,
        status="resolved",
        reason="Invalid score",
        match=_dummy_match(),
    )
    for k, v in overrides.items():
        setattr(d, k, v)
    return d


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_match_scheduled_with_user():
    User = get_user_model()
    u = User.objects.create_user(username="alice", email="alice@example.com", password="x")

    ok = email_utils.send_match_scheduled(u, _dummy_match())
    assert ok is True
    assert len(mail.outbox) == 1
    assert "Match scheduled" in mail.outbox[0].subject
    assert "Test Cup" in mail.outbox[0].body


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_match_verified_with_raw_email():
    ok = email_utils.send_match_verified("bob@example.com", _dummy_match(score_a=3, score_b=2))
    assert ok is True
    assert len(mail.outbox) == 1
    assert "Match verified" in mail.outbox[0].subject
    assert "3 – 2" in mail.outbox[0].body


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_dispute_opened_and_resolved():
    d = _dummy_dispute()
    ok1 = email_utils.send_dispute_opened("cap@example.com", d)
    ok2 = email_utils.send_dispute_resolved("cap@example.com", d)

    assert ok1 is True and ok2 is True
    assert len(mail.outbox) == 2
    assert "Dispute opened" in mail.outbox[0].subject
    assert "Dispute resolved" in mail.outbox[1].subject
