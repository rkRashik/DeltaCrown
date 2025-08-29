import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_public_profile_page(client):
    u = User.objects.create_user("alice", password="x")
    url = reverse("user_profile:profile", args=[u.username])
    r = client.get(url)
    assert r.status_code == 200
    assert u.username in r.content.decode()

@pytest.mark.django_db
def test_my_tournaments_requires_login(client):
    url = reverse("user_profile:my_tournaments")
    r = client.get(url)
    assert r.status_code in (302, 301)  # redirected to login
