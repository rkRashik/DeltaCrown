import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.teams.models import Team, TeamMembership

User = get_user_model()


@pytest.mark.django_db
def test_teams_list_renders(client):
    Team.objects.create(name="Team Alpha", slug="team-alpha", game="valorant")
    url = reverse("teams:list")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Teams" in resp.content


@pytest.mark.django_db
def test_my_teams_row_shows_user_teams_per_game(client):
    user = User.objects.create_user(username="rashik", password="x")
    t = Team.objects.create(name="Phoenix", slug="phoenix", game="valorant")
    TeamMembership.objects.create(user=user, team=t)
    client.login(username="rashik", password="x")
    resp = client.get(reverse("teams:list"))
    assert resp.status_code == 200
    assert b"My Teams" in resp.content
    assert b"Phoenix" in resp.content


@pytest.mark.django_db
def test_team_detail_join_guard_when_already_in_game_team(client):
    user = User.objects.create_user(username="p1", password="x")
    t1 = Team.objects.create(name="A", slug="a", game="valorant")
    t2 = Team.objects.create(name="B", slug="b", game="valorant")
    TeamMembership.objects.create(user=user, team=t1)
    client.login(username="p1", password="x")
    resp = client.get(reverse("teams:detail", args=[t2.slug]))
    assert resp.status_code == 200
    assert b"Already in a Valorant team" in resp.content or b"Already in a" in resp.content
