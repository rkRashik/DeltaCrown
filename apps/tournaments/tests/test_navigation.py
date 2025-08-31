import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_home_page_renders(client):
    r = client.get(reverse("home"))
    assert r.status_code == 200
    html = r.content.decode()
    assert "Browse Tournaments" in html
    assert reverse("tournaments:list") in html

def test_my_matches_requires_login(client):
    r = client.get(reverse("tournaments:my_matches"))
    # either redirect to login or 302 to your login URL, depending on settings
    assert r.status_code in (302, 301)

def test_navbar_links_present(client):
    r = client.get(reverse("home"))
    html = r.content.decode()
    assert reverse("tournaments:list") in html
    # "My Matches" link is visible (URL printed even if user is anon)
    assert reverse("tournaments:my_matches") in html
