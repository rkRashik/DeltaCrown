import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_dashboard_shows_notifications_section_empty_state(client):
    User = get_user_model()
    u = User.objects.create_user(username="notifuser", password="x", email="n@x.com")
    client.force_login(u)
    r = client.get(reverse("dashboard"))
    assert r.status_code == 200
    html = r.content.decode()
    assert "Recent notifications" in html
    assert "No notifications yet." in html
