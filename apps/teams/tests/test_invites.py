import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership, TeamInvite, TEAM_MAX_ROSTER

@pytest.mark.django_db
def test_captain_can_invite_and_user_accepts(client):
    cap_u = User.objects.create_user("cap", password="pw")
    cap_p = cap_u.profile
    t = Team.objects.create(name="Alpha Squad", tag="ALP", captain=cap_p)
    TeamMembership.objects.create(team=t, user=cap_p, role="captain")

    target_u = User.objects.create_user("neo", password="pw")
    client.login(username="cap", password="pw")
    url = reverse("teams:invite_member", kwargs={"team_id": t.id})
    resp = client.post(url, {"username": "neo", "message": "Join us!"})
    assert resp.status_code in (302, 200)
    inv = TeamInvite.objects.get(team=t, invited_user=target_u.profile)
    assert inv.status == "PENDING"

    # Accept
    client.logout()
    client.login(username="neo", password="pw")
    acc = client.get(reverse("teams:accept_invite", kwargs={"token": inv.token}))
    assert acc.status_code in (302, 200)
    assert TeamMembership.objects.filter(team=t, user=target_u.profile).exists()
    inv.refresh_from_db()
    assert inv.status == "ACCEPTED"

@pytest.mark.django_db
def test_roster_cap_enforced_on_invite():
    cap_u = User.objects.create_user("cap", password="pw")
    cap_p = cap_u.profile
    t = Team.objects.create(name="Beta", tag="BTA", captain=cap_p)
    TeamMembership.objects.create(team=t, user=cap_p, role="captain")

    # Fill up to max
    for i in range(TEAM_MAX_ROSTER - 1):
        u = User.objects.create_user(f"p{i}", password="pw")
        TeamMembership.objects.create(team=t, user=u.profile, role="player")

    # Next invite should fail cleanly at model.clean()
    neo = User.objects.create_user("neo", password="pw")
    inv = TeamInvite(team=t, invited_user=neo.profile, invited_by=cap_p, token="x")
    with pytest.raises(Exception):
        inv.clean()

@pytest.mark.django_db
def test_captain_must_transfer_before_leaving(client):
    cap_u = User.objects.create_user("cap", password="pw")
    cap_p = cap_u.profile
    t = Team.objects.create(name="Gamma", tag="GMA", captain=cap_p)
    TeamMembership.objects.create(team=t, user=cap_p, role="captain")
    client.login(username="cap", password="pw")
    resp = client.get(reverse("teams:leave_team", kwargs={"team_id": t.id}))
    # should not allow; redirect back with error
    assert resp.status_code in (302, 200)
    assert TeamMembership.objects.filter(team=t, user=cap_p).exists()
