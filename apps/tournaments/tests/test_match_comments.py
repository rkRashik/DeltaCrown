import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.apps import apps

from apps.tournaments.models import Tournament, Match

pytestmark = pytest.mark.django_db

def ensure_profile(user):
    p = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if p:
        return p
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username.title()})
    return p

def mk_user(username):
    u, _ = User.objects.get_or_create(username=username)
    if not u.has_usable_password():
        u.set_password("pw"); u.save(update_fields=["password"])
    ensure_profile(u); return u

def mk_tournament():
    now = timezone.now()
    return Tournament.objects.create(
        name="Comment Cup", slug=f"comment-cup-{int(now.timestamp())}",
        reg_open_at=now - timedelta(days=1), reg_close_at=now + timedelta(days=1),
        start_at=now + timedelta(days=2), end_at=now + timedelta(days=3), slot_size=4
    )

def mk_match(t):
    a = mk_user("alice"); b = mk_user("bob")
    m = Match.objects.create(tournament=t, round_no=1, position=1,
                             user_a=ensure_profile(a), user_b=ensure_profile(b), best_of=1)
    return a, b, m

def test_add_comment_as_participant(client):
    t = mk_tournament()
    a, b, m = mk_match(t)
    client.force_login(a)
    r = client.post(reverse("tournaments:match_comment", args=[m.id]), {"body": "gg wp"})
    assert r.status_code in (302, 200)
    MatchComment = apps.get_model("tournaments", "MatchComment")
    assert MatchComment.objects.filter(match=m, body="gg wp").exists()

def test_comment_permission_denied_for_non_participant(client):
    t = mk_tournament()
    a, b, m = mk_match(t)
    outsider = mk_user("mallory")
    client.force_login(outsider)
    r = client.post(reverse("tournaments:match_comment", args=[m.id]), {"body": "hi"})
    # redirect to review or 403 depending on template handling
    assert r.status_code in (302, 403)
    MatchComment = apps.get_model("tournaments", "MatchComment")
    assert not MatchComment.objects.filter(match=m, body="hi").exists()
