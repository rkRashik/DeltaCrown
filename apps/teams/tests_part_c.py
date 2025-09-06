import pytest
from django.urls import reverse
from django.apps import apps
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

def create_user(username="alice"):
    User = get_user_model()
    return User.objects.create_user(username=username, password="pw12345", email=f"{username}@x.test")

def ensure_profile(user):
    Profile = apps.get_model("user_profile", "UserProfile")
    p, _ = Profile.objects.get_or_create(user=user, defaults={"display_name": user.username})
    return p

def create_team(game="valorant", name="Alpha", tag="ALP", slug="alpha"):
    Team = apps.get_model("teams", "Team")
    User = get_user_model()
    cap = create_user("cap" + tag.lower())
    cap_p = ensure_profile(cap)
    team = Team.objects.create(name=name, tag=tag, slug=slug, game=game, captain_id=cap_p.id)
    # make captain membership active
    TeamMembership = apps.get_model("teams", "TeamMembership")
    TeamMembership.objects.create(team=team, profile=cap_p, role="CAPTAIN", status="ACTIVE")
    return team, cap, cap_p

def test_public_team_page_by_slug(client):
    team, cap, _ = create_team(game="valorant", name="VKings", tag="VK", slug="vkings")
    url = f"/teams/valorant/{team.slug}/"
    res = client.get(url)
    assert res.status_code == 200
    assert b"VKings" in res.content

def test_manage_requires_captain(client):
    team, cap, cap_p = create_team(game="efootball", name="Eagles", tag="EGL", slug="eagles")
    # non-captain
    bob = create_user("bob")
    client.login(username="bob", password="pw12345")
    assert client.get("/profile/teams/efootball/manage/").status_code in (302, 403)

    # captain can open
    client.logout()
    client.login(username=cap.username, password="pw12345")
    r = client.get("/profile/teams/efootball/manage/")
    assert r.status_code == 200
    assert b"Manage Team" in r.content

def test_rebuild_stats_flow(client):
    team, cap, cap_p = create_team(game="valorant", name="StatsTeam", tag="ST", slug="statsteam")
    # create another team and a verified match
    enemy, _, _ = create_team(game="valorant", name="Enemy", tag="EN", slug="enemy")
    Match = apps.get_model("tournaments", "Match")
    Tournament = apps.get_model("tournaments", "Tournament")
    t = Tournament.objects.create(name="Test Cup", slug="test-cup", game="valorant")
    m = Match.objects.create(tournament=t, round_no=1, position=1, best_of=1,
                             team_a=team, team_b=enemy, score_a=1, score_b=0,
                             winner_team=team, state="VERIFIED")
    client.login(username=cap.username, password="pw12345")
    r = client.post("/profile/teams/valorant/manage/", {"rebuild_stats": "1"})
    assert r.status_code in (302, 200)
    TeamStats = apps.get_model("teams", "TeamStats")
    snap = TeamStats.objects.filter(team=team).order_by("-updated_at").first()
    assert snap and snap.wins == 1 and snap.matches_played == 1
