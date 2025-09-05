# tests/test_part8_polish_admin.py
import pytest
from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse

from apps.tournaments.models import Tournament, Match, Registration
from apps.user_profile.models import UserProfile
from apps.tournaments.admin.tournaments import TournamentAdmin
from apps.corelib.brackets import generate_bracket, admin_set_winner


def make_admin_request(user, method="get", path="/"):
    rf = RequestFactory()
    req = getattr(rf, method.lower())(path)
    req.user = user
    # messages framework requires a session + _messages
    setattr(req, "session", {})
    storage = FallbackStorage(req)
    setattr(req, "_messages", storage)
    return req


@pytest.mark.django_db
def test_safe_vs_force_regeneration(django_user_model):
    admin_user = django_user_model.objects.create_superuser("admin", "a@e.com", "x")
    req = make_admin_request(admin_user)

    t = Tournament.objects.create(name="SafeGuard", slug="safe-guard", game="efootball", status="PUBLISHED")
    u1 = django_user_model.objects.create_user("p1", "p1@e.com", "x")
    u2 = django_user_model.objects.create_user("p2", "p2@e.com", "x")
    p1, _ = UserProfile.objects.get_or_create(user=u1)
    p2, _ = UserProfile.objects.get_or_create(user=u2)
    Registration.objects.create(tournament=t, user=p1, status="CONFIRMED")
    Registration.objects.create(tournament=t, user=p2, status="CONFIRMED")

    generate_bracket(t)
    m = Match.objects.get(tournament=t)
    admin_set_winner(m, who="a")

    ma = TournamentAdmin(Tournament, AdminSite())

    # SAFE generate should skip (results exist)
    ma.action_generate_bracket_safe(req, Tournament.objects.filter(pk=t.pk))
    assert Match.objects.filter(tournament=t).count() == 1  # unchanged

    # FORCE generate proceeds (subject to core lock rules)
    ma.action_force_regenerate_bracket(req, Tournament.objects.filter(pk=t.pk))
    assert Match.objects.filter(tournament=t).count() == 1


@pytest.mark.django_db
def test_export_bracket_json(client, django_user_model):
    # Must be logged in as staff, admin views require auth
    admin_user = django_user_model.objects.create_superuser("admin", "a@e.com", "x")
    client.force_login(admin_user)

    t = Tournament.objects.create(name="ExportMe", slug="export-me", game="efootball", status="PUBLISHED")
    u1 = django_user_model.objects.create_user("p1", "p1@e.com", "x")
    u2 = django_user_model.objects.create_user("p2", "p2@e.com", "x")
    p1, _ = UserProfile.objects.get_or_create(user=u1)
    p2, _ = UserProfile.objects.get_or_create(user=u2)
    Registration.objects.create(tournament=t, user=p1, status="CONFIRMED")
    Registration.objects.create(tournament=t, user=p2, status="CONFIRMED")

    generate_bracket(t)

    url = reverse("admin:tournaments_export_bracket", kwargs={"pk": t.pk})
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tournament"]["id"] == t.pk
    assert len(data["matches"]) >= 1
    assert "round" in data["matches"][0]
