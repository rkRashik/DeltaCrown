import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.apps import apps

from apps.tournaments.models import Tournament, Match

pytestmark = pytest.mark.django_db


def ensure_profile(user):
    """Return the attached profile, regardless of OneToOne field name; create if missing."""
    p = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if p:
        return p
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": user.username.title()}
    )
    return p


def mk_user(username: str) -> User:
    u, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
    # Set a password to allow force_login in client
    if not u.has_usable_password():
        u.set_password("pw")
        u.save(update_fields=["password"])
    ensure_profile(u)
    return u


def mk_tournament():
    now = timezone.now()
    return Tournament.objects.create(
        name="Test Cup",
        slug=f"test-cup-{int(now.timestamp())}",
        reg_open_at=now - timedelta(days=1),
        reg_close_at=now + timedelta(days=1),
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=3),
        slot_size=4,
    )


def mk_match_solo(t):
    a = mk_user("alice")
    b = mk_user("bob")
    m = Match.objects.create(
        tournament=t,
        round_no=1,
        position=1,
        user_a=ensure_profile(a),
        user_b=ensure_profile(b),
        best_of=1,
    )
    return a, b, m


def test_report_then_confirm(client):
    t = mk_tournament()
    u1, u2, m = mk_match_solo(t)

    # reporter submits 2-1
    client.force_login(u1)
    url = reverse("tournaments:match_report", args=[m.id])
    r = client.post(url, {"score_a": "2", "score_b": "1"})
    assert r.status_code in (302, 200)

    m.refresh_from_db()
    assert m.state == "REPORTED"
    assert m.score_a == 2 and m.score_b == 1

    # opponent confirms
    client.logout()
    client.force_login(u2)
    r = client.post(reverse("tournaments:match_confirm", args=[m.id]))
    assert r.status_code in (302, 200)

    m.refresh_from_db()
    assert m.state == "VERIFIED"
    assert m.winner_user == m.user_a


def test_report_then_dispute(client):
    t = mk_tournament()
    u1, u2, m = mk_match_solo(t)

    client.force_login(u1)
    client.post(
        reverse("tournaments:match_report", args=[m.id]),
        {"score_a": "1", "score_b": "0"},
    )
    m.refresh_from_db()
    assert m.state == "REPORTED"

    client.logout()
    client.force_login(u2)
    r = client.get(reverse("tournaments:match_dispute", args=[m.id]))
    assert r.status_code == 200
    r = client.post(
        reverse("tournaments:match_dispute", args=[m.id]),
        {"reason": "Screenshot shows 0-1"},
    )
    assert r.status_code in (302, 200)

    m.refresh_from_db()
    assert m.state == "REPORTED"  # remains pending
    MatchDispute = apps.get_model("tournaments", "MatchDispute")
    assert MatchDispute.objects.filter(match=m, is_open=True).exists()
