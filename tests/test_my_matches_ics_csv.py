# tests/test_my_matches_ics_csv.py
import pytest
from django.urls import reverse
from apps.tournaments.models.userprefs import CalendarFeedToken

@pytest.mark.django_db
def test_csv_download(client, django_user_model):
    user = django_user_model.objects.create_user(username="p1", password="x")
    client.login(username="p1", password="x")
    url = reverse("tournaments:my_matches_csv")
    r = client.get(url)
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/csv")

@pytest.mark.django_db
def test_ics_link_and_download(client, django_user_model):
    user = django_user_model.objects.create_user(username="p1", password="x")
    client.login(username="p1", password="x")
    help_url = reverse("tournaments:my_matches_ics_link")
    r = client.get(help_url)
    assert r.status_code == 200
    tok = CalendarFeedToken.objects.get(user=user).token
    ics_url = reverse("tournaments:my_matches_ics", args=[tok])
    r2 = client.get(ics_url)
    assert r2.status_code == 200
    assert r2["Content-Type"].startswith("text/calendar")
