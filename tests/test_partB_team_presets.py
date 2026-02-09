
import pytest
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Team = apps.get_model('organizations', 'Team')
UserProfile = apps.get_model('user_profile', 'UserProfile')
EfootballTeamPreset = apps.get_model('organizations', 'EfootballTeamPreset')
ValorantTeamPreset = apps.get_model('organizations', 'ValorantTeamPreset')
ValorantPlayerPreset = apps.get_model('organizations', 'ValorantPlayerPreset')

def make_profile(username: str):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password='x')
    prof, _ = UserProfile.objects.get_or_create(user=user)
    return prof

@pytest.mark.django_db
def test_team_media_fields_exist_and_slug_unique():
    prof = make_profile("media1")
    t1 = Team.objects.create(name="Phantom Squad", tag="PHAN", captain=prof, game="valorant", slug="phantom")
    # Same slug allowed for different game
    t2 = Team.objects.create(name="Phantom Squad 2", tag="PH2", captain=prof, game="efootball", slug="phantom")
    assert t1.slug == "phantom"
    assert t2.slug == "phantom"

@pytest.mark.django_db
def test_create_efootball_preset_and_list():
    prof = make_profile("ef1")
    p = EfootballTeamPreset.objects.create(profile=prof, name="Duo Default", team_name="EF Duo")
    assert EfootballTeamPreset.objects.filter(profile=prof).count() == 1
    assert p.team_name == "EF Duo"

@pytest.mark.django_db
def test_create_valorant_preset_with_players():
    prof = make_profile("va1")
    p = ValorantTeamPreset.objects.create(profile=prof, name="VAL Base", team_name="V-Team", team_tag="VTM")
    ValorantPlayerPreset.objects.create(preset=p, in_game_name="Cap", role="CAPTAIN")
    ValorantPlayerPreset.objects.create(preset=p, in_game_name="P1", role="PLAYER")
    assert p.players.count() == 2
