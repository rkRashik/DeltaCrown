import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.teams.models import Team, TeamMembership, TeamInvite
from apps.user_profile.models import UserProfile


def _profile(user):
    p, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username})
    return p


@pytest.mark.django_db
def test_invite_accept_via_token(client, django_user_model):
    # captain + team
    u_cap = django_user_model.objects.create_user(username="cap", password="x")
    cap = _profile(u_cap)
    team = Team.objects.create(name="Alpha", tag="ALP", captain=cap)
    TeamMembership.objects.get_or_create(team=team, profile=cap, defaults={"role": "CAPTAIN", "status": "ACTIVE"})

    # target user + invite
    u_bob = django_user_model.objects.create_user(username="bob", password="x")
    bob = _profile(u_bob)
    inv = TeamInvite.objects.create(team=team, inviter=cap, invited_user=bob, status="PENDING")

    client.force_login(u_bob)
    url = reverse("teams:accept_invite", kwargs={"token": inv.token})
    resp = client.get(url)
    # accept may redirect to team page
    assert resp.status_code in (302, 301)

    # membership created
    assert TeamMembership.objects.filter(team=team, profile=bob, status="ACTIVE").exists()
    inv.refresh_from_db()
    assert inv.status == "ACCEPTED"


@pytest.mark.django_db
def test_invite_accept_expired_token(client, django_user_model):
    u_cap = django_user_model.objects.create_user(username="cap2", password="x")
    cap = _profile(u_cap)
    team = Team.objects.create(name="Beta", tag="BET", captain=cap)
    TeamMembership.objects.get_or_create(team=team, profile=cap, defaults={"role": "CAPTAIN", "status": "ACTIVE"})

    u_eve = django_user_model.objects.create_user(username="eve", password="x")
    eve = _profile(u_eve)
    inv = TeamInvite.objects.create(
        team=team, inviter=cap, invited_user=eve, status="PENDING",
        expires_at=timezone.now() - dt.timedelta(days=1),
    )

    client.force_login(u_eve)
    url = reverse("teams:accept_invite", kwargs={"token": inv.token})
    resp = client.get(url)
    assert resp.status_code in (410, 400, 404)  # friendly error page
    inv.refresh_from_db()
    assert inv.status in ("EXPIRED", "PENDING")  # allowed: view may mark expired

    # and no membership granted
    assert not TeamMembership.objects.filter(team=team, profile=eve, status="ACTIVE").exists()


@pytest.mark.django_db
def test_captain_switch_persists(django_user_model):
    u_cap = django_user_model.objects.create_user(username="c1", password="x")
    cap = _profile(u_cap)
    team = Team.objects.create(name="Gamma", tag="GAM", captain=cap)
    TeamMembership.objects.get_or_create(team=team, profile=cap, defaults={"role": "CAPTAIN", "status": "ACTIVE"})

    u_new = django_user_model.objects.create_user(username="n1", password="x")
    new = _profile(u_new)
    mem_new, _ = TeamMembership.objects.get_or_create(team=team, profile=new, defaults={"role": "PLAYER", "status": "ACTIVE"})

    # Use the model method (ensures demotion+promotion atomically)
    mem_new.promote_to_captain()
    team.refresh_from_db()
    mem_new.refresh_from_db()
    assert team.captain_id == new.id
    assert mem_new.role == "CAPTAIN"


@pytest.mark.django_db
def test_profile_page_loads(client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer", password="x")
    _ = _profile(user)
    resp = client.get(reverse("user_profile:profile", kwargs={"username": user.username}))
    assert resp.status_code == 200
    body = resp.content.decode()
    # wallet link present
    assert "/wallet/" in body
