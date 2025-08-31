import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_dashboard_shows_upcoming_matches_section(client):
    User = get_user_model()
    u = User.objects.create_user(username="dashuser2", password="x", email="d2@x.com")
    client.force_login(u)
    r = client.get(reverse("dashboard"))
    assert r.status_code == 200
    html = r.content.decode()
    assert "Upcoming matches" in html
    # Friendly empty state is fine when the user has no matches
    assert "No upcoming matches" in html
