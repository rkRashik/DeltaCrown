# tests/test_my_matches_dashboard.py
import pytest
from django.urls import reverse
from django.utils import timezone
from apps.tournaments.models.userprefs import SavedMatchFilter, CalendarFeedToken

@pytest.mark.django_db
def test_my_matches_smoke(client, django_user_model):
    user = django_user_model.objects.create_user(username="p1", password="x")
    client.login(username="p1", password="x")
    url = reverse("tournaments:my_matches")
    r = client.get(url)
    assert r.status_code == 200
    assert b"My Matches" in r.content

@pytest.mark.django_db
def test_saving_default_filter(client, django_user_model):
    user = django_user_model.objects.create_user(username="p1", password="x")
    client.login(username="p1", password="x")
    url = reverse("tournaments:my_matches_save_default")
    r = client.post(url, {"game":"valorant","state":"scheduled"})
    assert r.status_code in (302, 303)
    sf = SavedMatchFilter.objects.get(user=user, name="Default")
    assert sf.is_default is True
    assert sf.game == "valorant"
    assert sf.state == "scheduled"

@pytest.mark.django_db
def test_calendar_token_issued(client, django_user_model):
    user = django_user_model.objects.create_user(username="p1", password="x")
    client.login(username="p1", password="x")
    url = reverse("tournaments:my_matches")
    client.get(url)
    assert CalendarFeedToken.objects.filter(user=user).exists()
