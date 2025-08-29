import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

pytestmark = pytest.mark.django_db

def test_notifications_requires_login(client):
    resp = client.get(reverse("notifications:list"))
    # should redirect to login page
    assert resp.status_code in (302, 301)

def test_notifications_list_ok(client):
    U = get_user_model()
    u = U.objects.create_user("bob", password="x")
    UserProfile.objects.get_or_create(user=u, defaults={"display_name": "Bob"})
    client.login(username="bob", password="x")
    resp = client.get(reverse("notifications:list"))
    assert resp.status_code == 200
