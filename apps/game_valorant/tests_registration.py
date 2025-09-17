# apps/game_valorant/tests_registration.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

from apps.user_profile.models import UserProfile
from apps.tournaments.models import Tournament
from apps.teams.models import Team, TeamMembership

@pytest.mark.django_db
def test_valorant_captain_only_and_roster_size(client):
    cap = User.objects.create_user(username="vcap", password="x", email="vcap@example.com")
    cap_prof = UserProfile.objects.create(user=cap, display_name="VCap", riot_id="VCap", discord_id="VCap#0001")

    not_cap = User.objects.create_user(username="notcap", password="x", email="notcap@example.com")
    UserProfile.objects.create(user=not_cap, display_name="NotCap")

    team = Team.objects.create(name="VAL5", tag="VAL5", captain=cap_prof)
    TeamMembership.objects.create(team=team, profile=cap_prof, role="CAPTAIN", status="ACTIVE")

    t = Tournament.objects.create(name="Valorant Invitational", slug="val-inv", game="valorant")

    url = reverse("tournaments:register", args=[t.slug])

    # Non-captain attempt should fail
    client.login(username="notcap", password="x")
    r = client.post(url, {
        "__team_flow": "1",
        "team": team.id,
        "agree_captain_consent": True, "agree_rules": True, "agree_no_cheat": True, "agree_enforcement": True,
        # players: fewer than 5 => fail
        "p0-full_name": "A", "p0-riot_id": "A", "p0-riot_tagline": "APAC", "p0-discord": "a#1", "p0-role": "starter",
        "p1-full_name": "B", "p1-riot_id": "B", "p1-riot_tagline": "APAC", "p1-discord": "b#1", "p1-role": "starter",
        "p2-full_name": "C", "p2-riot_id": "C", "p2-riot_tagline": "APAC", "p2-discord": "c#1", "p2-role": "starter",
        "p3-full_name": "D", "p3-riot_id": "D", "p3-riot_tagline": "APAC", "p3-discord": "d#1", "p3-role": "starter",
    })
    assert r.status_code == 200
    assert b"Only the team captain can register for Valorant" in r.content or b"You must list at least 5 starters." in r.content

    # Captain success with 5 starters
    client.logout(); client.login(username="vcap", password="x")
    payload = {
        "team": team.id,
        "agree_captain_consent": True, "agree_rules": True, "agree_no_cheat": True, "agree_enforcement": True,
        "p0-full_name": "A", "p0-riot_id": "A", "p0-riot_tagline": "APAC", "p0-discord": "a#1", "p0-role": "starter",
        "p1-full_name": "B", "p1-riot_id": "B", "p1-riot_tagline": "APAC", "p1-discord": "b#1", "p1-role": "starter",
        "p2-full_name": "C", "p2-riot_id": "C", "p2-riot_tagline": "APAC", "p2-discord": "c#1", "p2-role": "starter",
        "p3-full_name": "D", "p3-riot_id": "D", "p3-riot_tagline": "APAC", "p3-discord": "d#1", "p3-role": "starter",
        "p4-full_name": "E", "p4-riot_id": "E", "p4-riot_tagline": "APAC", "p4-discord": "e#1", "p4-role": "starter",
    }
    r = client.post(url, payload, follow=True)
    assert r.status_code == 200
    assert b"Registration submitted" in r.content

