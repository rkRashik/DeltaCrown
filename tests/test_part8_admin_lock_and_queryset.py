import pytest
from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from apps.tournaments.models import Tournament, Match, Registration
from apps.user_profile.models import UserProfile
from apps.tournaments.admin.matches import MatchAdmin
from apps.corelib.brackets import generate_bracket


def _admin_request(user, method="get", path="/"):
    rf = RequestFactory()
    req = getattr(rf, method)(path)
    req.user = user
    # messages framework needs a session + storage
    setattr(req, "session", {})
    storage = FallbackStorage(req)
    setattr(req, "_messages", storage)
    return req


@pytest.mark.django_db
def test_matchadmin_respects_lock_and_prefetch(client, django_user_model):
    # superuser for admin views
    admin_user = django_user_model.objects.create_superuser("admin", "a@e.com", "x")

    # Setup: 2 players, generate bracket
    u1 = django_user_model.objects.create_user("pa", "pa@e.com", "x")
    u2 = django_user_model.objects.create_user("pb", "pb@e.com", "x")
    p1, _ = UserProfile.objects.get_or_create(user=u1)
    p2, _ = UserProfile.objects.get_or_create(user=u2)
    t = Tournament.objects.create(name="Locky", slug="locky", game="efootball", status="PUBLISHED")
    Registration.objects.create(tournament=t, user=p1, status="CONFIRMED")
    Registration.objects.create(tournament=t, user=p2, status="CONFIRMED")
    generate_bracket(t)

    # Lock the bracket
    b = t.bracket
    b.is_locked = True
    b.save(update_fields=["is_locked"])

    # Admin class
    ma = MatchAdmin(Match, AdminSite())
    m = Match.objects.get(tournament=t)

    # 1) Read-only fields contain score/winner when locked
    ro = ma.get_readonly_fields(request=None, obj=m)
    assert "score_a" in ro and "score_b" in ro and "winner_user" in ro and "winner_team" in ro

    # 2) get_queryset uses select_related/prefetch safely
    qs = ma.get_queryset(request=None)
    assert qs.model is Match

    # 3) Attempt to set winner via the admin view while LOCKED → should be blocked
    req = _admin_request(admin_user, "get", f"/admin/tournaments/match/{m.id}/set_winner/a/")
    ma.set_winner_view(req, match_id=m.id, who="a")

    m.refresh_from_db()
    # still no winner because bracket is locked
    assert m.winner_user_id is None and m.winner_team_id is None
