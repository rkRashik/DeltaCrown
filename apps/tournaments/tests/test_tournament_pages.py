import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, Registration

User = get_user_model()


@pytest.mark.django_db
def test_hub_renders(client):
    Tournament.objects.create(name="Delta Clash", slug="delta-clash", game="valorant")
    resp = client.get(reverse("tournaments:hub"))
    assert resp.status_code == 200
    assert b"Tournaments" in resp.content


@pytest.mark.django_db
def test_detail_cta_states(client):
    user = User.objects.create_user(username="p1", email="p1@example.com", password="x")
    t = Tournament.objects.create(name="V Cup", slug="v-cup", game="valorant")
    client.login(username="p1", password="x")
    resp = client.get(reverse("tournaments:detail", args=[t.slug]))
    assert resp.status_code == 200
    assert b"Register" in resp.content or b"Registration" in resp.content


@pytest.mark.django_db
def test_by_game_uses_hub(client):
    Tournament.objects.create(name="eF Open", slug="ef-open", game="efootball")
    resp = client.get(reverse("tournaments:by_game", args=["efootball"]))
    assert resp.status_code == 200
    assert b"Tournaments" in resp.content
