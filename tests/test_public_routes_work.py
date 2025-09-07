import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_public_pages_anonymous(client):
    # exact URLs requested
    urls = [
        "/tournaments/",
        "/teams/",
        "/user/",              # will redirect to homepage when anon
        "/about/",
        "/community/",
        "/notifications/",     # anon should redirect to login
    ]
    for url in urls:
        res = client.get(url, follow=True)
        assert res.status_code in (200, 302)

def test_logout_route(client, django_user_model):
    u = django_user_model.objects.create_user(username="x", password="pw", email="x@x.com")
    client.login(username="x", password="pw")
    res = client.get("/accounts/logout/", follow=True)
    assert res.status_code in (200, 302)
    # after logout we should be able to hit homepage
    res2 = client.get(reverse("homepage"))
    assert res2.status_code == 200

def test_tournaments_list_shows_created_tournament(client, django_user_model):
    # Create a tournament and assert it appears on /tournaments/
    from django.apps import apps
    Tournament = apps.get_model("tournaments", "Tournament")
    t = Tournament.objects.create(name="Spring Cup", slug="spring-cup")
    res = client.get("/tournaments/")
    assert res.status_code == 200
    html = res.content.decode()
    assert "Spring Cup" in html
    # and detail page by slug
    res2 = client.get(f"/tournaments/{t.slug}/")
    assert res2.status_code == 200
