import pytest
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.exceptions import ValidationError

User = get_user_model()
Team = apps.get_model('organizations', 'Team')
TeamMembership = apps.get_model('organizations', 'TeamMembership')
UserProfile = apps.get_model('user_profile', 'UserProfile')
Tournament = apps.get_model('tournaments', 'Tournament')
Registration = apps.get_model('tournaments', 'Registration')

def make_profile(username: str):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password='x')
    prof, _ = UserProfile.objects.get_or_create(user=user)
    return prof

@pytest.mark.django_db
def test_team_has_game_field():
    assert hasattr(Team, 'game')
    prof = make_profile('u1')
    t = Team.objects.create(name='Alpha Squad', tag='ALPHA', captain=prof, game='valorant')
    assert t.game == 'valorant'

@pytest.mark.django_db
def test_one_active_team_per_game_rule():
    prof = make_profile('u42')
    # Creating a team with a captain usually auto-creates the captain membership
    t1 = Team.objects.create(name='V-ONE', tag='V1', captain=prof, game='valorant')
    t2 = Team.objects.create(name='V-TWO', tag='V2', captain=prof, game='valorant')
    # No need to create captain membership for t1; it's auto-created by signals.
    # Attempt to create another ACTIVE membership for same game on a different team.
    m2 = TeamMembership(team=t2, profile=prof, role='PLAYER', status='ACTIVE')
    with pytest.raises(ValidationError):
        m2.full_clean()

@pytest.mark.django_db
def test_registration_sets_team_game_from_tournament():
    prof = make_profile('u7')
    # Team with blank game
    team = Team.objects.create(name='VAL Squad', tag='VSQ', captain=prof, game='')
    # Use Valorant tournament (team mode) so Registration requires team, not user
    tour = Tournament.objects.create(name='Valorant Cup', slug='valorant-cup', game='valorant')
    reg = Registration.objects.create(tournament=tour, team=team, status='PENDING')
    team.refresh_from_db()
    assert team.game == 'valorant'
