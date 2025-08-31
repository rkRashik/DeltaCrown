import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.apps import apps

pytestmark = pytest.mark.django_db

def prof(u):
    p = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    if p: return p
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(user=u, defaults={"display_name": u.username})
    return p

def mk_team(tag="WLV"):
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    a = User.objects.create_user("alice", password="pw")
    b = User.objects.create_user("bob", password="pw")
    pa, pb = prof(a), prof(b)
    t = Team.objects.create(name="Wolves", tag=tag, captain=pa)
    TeamMembership.objects.create(team=t, user=pa, role="captain")
    TeamMembership.objects.create(team=t, user=pb, role="player")
    return t, a, b

def test_player_can_leave_team(client):
    t, a, b = mk_team()
    client.force_login(b)
    url = reverse("teams:leave", args=[t.tag])
    r = client.get(url)
    assert r.status_code == 200
    r = client.post(url)
    assert r.status_code in (302, 200)

    TeamMembership = apps.get_model("teams", "TeamMembership")
    assert not TeamMembership.objects.filter(team=t, user=prof(b)).exists()

def test_captain_must_transfer_before_leaving(client):
    t, a, b = mk_team()
    client.force_login(a)  # captain
    url = reverse("teams:leave", args=[t.tag])
    r = client.post(url)
    assert r.status_code in (302, 200)

    TeamMembership = apps.get_model("teams", "TeamMembership")
    # captain still present because there was another member
    assert TeamMembership.objects.filter(team=t, user=prof(a), role="captain").exists()

def test_transfer_captain(client):
    t, a, b = mk_team()
    client.force_login(a)  # captain

    # load form
    r = client.get(reverse("teams:transfer", args=[t.tag]))
    assert r.status_code == 200

    # pick bob's membership
    TeamMembership = apps.get_model("teams", "TeamMembership")
    bob_mem = TeamMembership.objects.get(team=t, user=prof(b))

    r = client.post(reverse("teams:transfer", args=[t.tag]), {"new_captain_id": bob_mem.id})
    assert r.status_code in (302, 200)

    t.refresh_from_db()
    assert t.captain == prof(b)
    assert TeamMembership.objects.get(team=t, user=prof(a)).role == "player"
    assert TeamMembership.objects.get(team=t, user=prof(b)).role == "captain"

def test_captain_solo_leaving_deletes_team(client):
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    # make team with single captain
    u = User.objects.create_user("solo", password="pw")
    p = prof(u)
    t = Team.objects.create(name="SoloTeam", tag="SOLO", captain=p)
    TeamMembership.objects.create(team=t, user=p, role="captain")

    client.force_login(u)
    url = reverse("teams:leave", args=["SOLO"])
    r = client.post(url)
    assert r.status_code in (302, 200)
    assert not Team.objects.filter(tag="SOLO").exists()
