import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_login_url_resolves_and_renders(client):
    url = reverse("login")
    r = client.get(url)
    # For anonymous users this should render the login page
    assert r.status_code == 200

def test_home_shows_login_link_for_anonymous(client):
    r = client.get(reverse("home"))
    assert r.status_code == 200
    html = r.content.decode()
    assert reverse("login") in html
