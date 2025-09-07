import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_homepage_connects_core_routes_anonymous(client):
    res = client.get(reverse("homepage"))
    assert res.status_code == 200
    html = res.content.decode()

    # Always-visible links
    assert reverse("tournaments:my_matches") in html
    assert reverse("tournaments:my_matches_csv") in html
    assert reverse("tournaments:my_matches_ics_link") in html
    assert reverse("healthz") in html

    # Auth-only links should not 500 even if absent for anon users
    # (We don't assert presence for anon.)

def test_homepage_connects_core_routes_authenticated(client, django_user_model):
    u = django_user_model.objects.create_user(username="home", password="pw", email="h@example.com")
    client.login(username="home", password="pw")
    res = client.get(reverse("homepage"))
    assert res.status_code == 200
    html = res.content.decode()

    # Links visible to authenticated users
    assert reverse("user_profile:edit") in html
    assert reverse("user_profile:public_profile", args=["home"]) in html
