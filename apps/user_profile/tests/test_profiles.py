import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from apps.tournaments.models import Tournament, Registration

@pytest.mark.django_db
def test_profile_page(client):
    u = User.objects.create_user("alice", password="x")
    url = reverse("user_profile:profile", args=["alice"])
    resp = client.get(url)
    assert resp.status_code == 200
    assert "alice" in resp.content.decode()

@pytest.mark.django_db
def test_my_tournaments(client):
    u = User.objects.create_user("bob", password="x")
    client.login(username="bob", password="x")
    t = Tournament.objects.create(name="Test Cup", reg_open_at="2025-08-01T10:00Z",
                                  reg_close_at="2025-08-05T10:00Z",
                                  start_at="2025-08-06T10:00Z", end_at="2025-08-07T10:00Z",
                                  slot_size=8)
    Registration.objects.create(tournament=t, user=u.profile, status="CONFIRMED")
    url = reverse("user_profile:my_tournaments")
    resp = client.get(url)
    assert "Test Cup" in resp.content.decode()
