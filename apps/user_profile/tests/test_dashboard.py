import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_dashboard_redirects_when_anonymous(client):
    r = client.get("/dashboard/")
    # Django's LoginRequired should redirect to login
    assert r.status_code in (302, 301)
    # Should point at the login URL name "login"
    assert reverse("login") in r.headers.get("Location", "")

def test_dashboard_ok_when_authenticated(client):
    User = get_user_model()
    u = User.objects.create_user(username="dashuser", password="x", email="d@x.com")
    client.force_login(u)
    r = client.get(reverse("dashboard"))
    assert r.status_code == 200
    html = r.content.decode()
    assert "Dashboard" in html
    assert u.username in html
