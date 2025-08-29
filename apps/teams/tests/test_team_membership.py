import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership

User = get_user_model()

@pytest.mark.django_db
def test_team_captain_membership_created():
    cap = User.objects.create_user(username="cap", password="x")
    cap_p, _ = UserProfile.objects.get_or_create(user=cap)
    t = Team.objects.create(name="Aces", tag="ACE", captain=cap_p)
    TeamMembership.objects.get_or_create(team=t, user=cap_p, defaults={"role": "captain"})
    assert TeamMembership.objects.filter(team=t, user=cap_p, role="captain").exists()

@pytest.mark.django_db
def test_unique_membership():
    u = User.objects.create_user(username="p1", password="x")
    p, _ = UserProfile.objects.get_or_create(user=u)
    cap = User.objects.create_user(username="cap2", password="x")
    cap_p, _ = UserProfile.objects.get_or_create(user=cap)
    t = Team.objects.create(name="Blaze", tag="BLZ", captain=cap_p)
    TeamMembership.objects.create(team=t, user=p, role="player")
    with pytest.raises(Exception):
        TeamMembership.objects.create(team=t, user=p, role="player")  # unique_together
