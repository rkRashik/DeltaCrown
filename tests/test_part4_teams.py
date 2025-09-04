# tests/test_part4_teams.py
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.teams.models import Team, TeamMembership, TeamInvite


def _profile_for(user):
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@pytest.mark.django_db
def test_team_creation_captain_membership(django_user_model):
    u = django_user_model.objects.create_user("cap", "cap@example.com", "pass")
    p = _profile_for(u)
    t = Team.objects.create(name="My Squad", tag="MSQ", captain=p)
    assert t.members_count >= 1
    cap_mem = TeamMembership.objects.get(team=t, profile=p)
    assert cap_mem.role == TeamMembership.Role.CAPTAIN
    assert cap_mem.status == TeamMembership.Status.ACTIVE


@pytest.mark.django_db
def test_unique_membership_constraint(django_user_model):
    cap_u = django_user_model.objects.create_user("cap2", "cap2@example.com", "pass")
    cap_p = _profile_for(cap_u)
    t = Team.objects.create(name="Unique", tag="UNQ", captain=cap_p)

    u = django_user_model.objects.create_user("x", "x@example.com", "pass")
    p = _profile_for(u)
    TeamMembership.objects.create(team=t, profile=p, role=TeamMembership.Role.PLAYER)

    with pytest.raises(IntegrityError):
        TeamMembership.objects.create(team=t, profile=p, role=TeamMembership.Role.SUB)


@pytest.mark.django_db
def test_promote_to_captain_switches_team_captain(django_user_model):
    u0 = django_user_model.objects.create_user("cap3", "cap3@example.com", "pass")
    p0 = _profile_for(u0)
    t = Team.objects.create(name="Promos", tag="PRM", captain=p0)

    u1 = django_user_model.objects.create_user("u1", "u1@example.com", "pass")
    p1 = _profile_for(u1)
    m = TeamMembership.objects.create(team=t, profile=p1, role=TeamMembership.Role.PLAYER)
    m.promote_to_captain()
    t.refresh_from_db()
    assert t.captain == p1
    m.refresh_from_db()
    assert m.role == TeamMembership.Role.CAPTAIN
    assert m.status == TeamMembership.Status.ACTIVE


@pytest.mark.django_db
def test_invite_accept_sets_membership_active(django_user_model):
    cap_u = django_user_model.objects.create_user("cap4", "cap4@example.com", "pass")
    cap_p = _profile_for(cap_u)
    t = Team.objects.create(name="Invites", tag="INV", captain=cap_p)

    u = django_user_model.objects.create_user("player", "p@example.com", "pass")
    p = _profile_for(u)
    inv = TeamInvite.objects.create(team=t, inviter=cap_p, invited_user=p, role=TeamMembership.Role.MANAGER)
    inv.accept()
    inv.refresh_from_db()
    assert inv.status == "ACCEPTED"
    mem = TeamMembership.objects.get(team=t, profile=p)
    assert mem.role == TeamMembership.Role.MANAGER
    assert mem.status == TeamMembership.Status.ACTIVE


@pytest.mark.django_db
def test_invite_respects_roster_limit(django_user_model, settings):
    # Seed team with roster up to TEAM_MAX_ROSTER and ensure new invite fails validation
    from apps.teams.models import TEAM_MAX_ROSTER
    cap_u = django_user_model.objects.create_user("cap5", "cap5@example.com", "pass")
    cap_p = _profile_for(cap_u)
    t = Team.objects.create(name="Roster", tag="RST", captain=cap_p)

    # Fill up to limit - 1 (captain already counted as ACTIVE)
    current = t.members_count
    to_add = max(0, TEAM_MAX_ROSTER - current - 1)
    for i in range(to_add):
        u = django_user_model.objects.create_user(f"u{i}", f"u{i}@example.com", "pass")
        p = _profile_for(u)
        TeamMembership.objects.create(team=t, profile=p, role=TeamMembership.Role.PLAYER)

    # Now new pending invite should fail clean()
    inv = TeamInvite(team=t, inviter=cap_p, invited_email="full@example.com")
    with pytest.raises(ValidationError):
        inv.full_clean()
