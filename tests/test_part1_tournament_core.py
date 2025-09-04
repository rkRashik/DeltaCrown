# tests/test_part1_tournament_core.py
import pytest
from django.urls import reverse

from apps.tournaments.models import Tournament

@pytest.mark.django_db
def test_admin_tournament_add_loads(admin_client):
    url = reverse("admin:tournaments_tournament_add")
    r = admin_client.get(url)
    assert r.status_code == 200, "Admin add page should render without FieldError"

@pytest.mark.django_db
def test_tournament_create_autocreates_settings():
    # 'valorant' and 'efootball' are the canonical choices in your model
    t = Tournament.objects.create(name="Alpha Cup", game="valorant")
    # signals should have created a settings row
    assert hasattr(t, "settings"), "Tournament.settings missing attribute"
    t.refresh_from_db()
    assert t.settings is not None, "TournamentSettings was not auto-created"

@pytest.mark.django_db
def test_admin_tournament_change_loads(admin_client):
    t = Tournament.objects.create(name="Beta Cup", game="efootball")
    url = reverse("admin:tournaments_tournament_change", args=[t.pk])
    r = admin_client.get(url)
    assert r.status_code == 200, "Admin change page should render with inlines"

@pytest.mark.django_db
def test_changelist_has_fee_filter_does_not_break(admin_client):
    # Even if HasEntryFeeFilter isn't active for your fields, passing the param should not 500
    url = reverse("admin:tournaments_tournament_changelist")
    r = admin_client.get(url, {"has_fee": "yes"})
    assert r.status_code == 200
