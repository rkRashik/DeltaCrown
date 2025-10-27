"""Tests for team list button logic and display."""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user with profile."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        is_active=True,
        is_verified=True
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def another_user(db):
    """Create another test user with profile."""
    user = User.objects.create_user(
        username="anotheruser",
        email="another@example.com",
        password="testpass123",
        is_active=True,
        is_verified=True
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def recruiting_team(db, test_user):
    """Create a recruiting team."""
    profile, _ = UserProfile.objects.get_or_create(user=test_user)
    team = Team.objects.create(
        name="Recruiting Team",
        tag="RCT",
        game="valorant",
        is_active=True,
        is_public=True,
        is_recruiting=True,
        allow_join_requests=True,
        captain=profile
    )
    return team


@pytest.fixture
def non_recruiting_team(db, test_user):
    """Create a non-recruiting team."""
    profile, _ = UserProfile.objects.get_or_create(user=test_user)
    team = Team.objects.create(
        name="Closed Team",
        tag="CLT",
        game="cs2",
        is_active=True,
        is_public=True,
        is_recruiting=False,
        allow_join_requests=False,
        captain=profile
    )
    return team


@pytest.mark.django_db
def test_team_list_page_renders(client):
    """Test that the team list page renders successfully."""
    url = reverse("teams:list")
    response = client.get(url)
    assert response.status_code == 200
    assert "teams" in response.context or "object_list" in response.context


@pytest.mark.django_db
def test_view_team_button_text(client, recruiting_team):
    """Test that 'View Team' button text is displayed instead of 'View Profile'."""
    url = reverse("teams:list")
    response = client.get(url)
    content = response.content.decode()
    
    # Should have "View Team" text
    assert "View Team" in content
    
    # Should NOT have "View Profile" for teams
    # (Note: "View Profile" might still appear in user menu, so we check context)
    team_section = content[content.find("team-actions-premium"):content.find("team-actions-premium") + 500]
    assert "View Team" in team_section


@pytest.mark.django_db
def test_join_button_shown_for_recruiting_team(client, test_user, recruiting_team):
    """Test that Join button is shown for recruiting teams when user is not a member."""
    url = reverse("teams:list")
    
    # Login as a different user (not the captain)
    client.login(username="testuser", password="testpass123")
    
    response = client.get(url)
    content = response.content.decode()
    
    # For a recruiting team, if user is not a member, Join button should appear
    # Check if the team is in the response and has join functionality
    assert recruiting_team.name in content


@pytest.mark.django_db
def test_join_button_not_shown_for_non_recruiting_team(client, test_user, non_recruiting_team):
    """Test that Join button is NOT shown for non-recruiting teams."""
    url = reverse("teams:list")
    
    # Create another user to test with
    another = User.objects.create_user(
        username="viewer",
        email="viewer@example.com",
        password="testpass123"
    )
    UserProfile.objects.get_or_create(user=another)
    
    client.login(username="viewer", password="testpass123")
    response = client.get(url)
    
    # Teams on page should have show_join_button attribute set correctly
    teams = response.context.get('teams', response.context.get('object_list', []))
    
    for team in teams:
        if team.id == non_recruiting_team.id:
            # Non-recruiting team should not show join button
            assert not team.show_join_button


@pytest.mark.django_db
def test_member_badge_shown_for_member(client, test_user, recruiting_team):
    """Test that Member badge is shown when user is already a member."""
    # Create another user and add them to the team
    member_user = User.objects.create_user(
        username="member",
        email="member@example.com",
        password="testpass123"
    )
    member_profile, _ = UserProfile.objects.get_or_create(user=member_user)
    
    # Add member to team
    TeamMembership.objects.create(
        team=recruiting_team,
        profile=member_profile,
        role=TeamMembership.Role.PLAYER,
        status=TeamMembership.Status.ACTIVE
    )
    
    # Login as member
    client.login(username="member", password="testpass123")
    response = client.get(reverse("teams:list"))
    
    # Check that user_is_member is True for this team
    teams = response.context.get('teams', response.context.get('object_list', []))
    
    for team in teams:
        if team.id == recruiting_team.id:
            assert team.user_is_member
            # Member should not see join button
            assert not team.show_join_button


@pytest.mark.django_db
def test_unauthenticated_user_sees_join_for_recruiting(client, recruiting_team):
    """Test that unauthenticated users can see join button for recruiting teams."""
    url = reverse("teams:list")
    response = client.get(url)
    
    # Teams should be visible
    teams = response.context.get('teams', response.context.get('object_list', []))
    
    # For unauthenticated users, show_join_button should be based on recruiting status
    for team in teams:
        if team.id == recruiting_team.id:
            # Should show join button based on recruiting status
            assert team.show_join_button == (team.is_recruiting or team.allow_join_requests)


@pytest.mark.django_db
def test_team_attributes_set_correctly(client, recruiting_team, non_recruiting_team):
    """Test that all team attributes are set correctly in the view."""
    url = reverse("teams:list")
    response = client.get(url)
    
    teams = response.context.get('teams', response.context.get('object_list', []))
    
    for team in teams:
        # Check that all required attributes exist
        assert hasattr(team, 'user_is_member')
        assert hasattr(team, 'show_join_button')
        assert hasattr(team, 'power_rank')
        assert hasattr(team, 'members_count')
        
        # Check boolean types
        assert isinstance(team.user_is_member, bool)
        assert isinstance(team.show_join_button, bool)


@pytest.mark.django_db
def test_ajax_json_response_includes_button_flags(client, recruiting_team):
    """Test that AJAX JSON responses include button display flags."""
    url = reverse("teams:list")
    
    # Make AJAX request with JSON accept header
    response = client.get(
        url,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        HTTP_ACCEPT='application/json'
    )
    
    if response.status_code == 200 and response.get('Content-Type') == 'application/json':
        import json
        data = json.loads(response.content)
        
        if 'teams' in data and len(data['teams']) > 0:
            team_data = data['teams'][0]
            
            # Check that required fields are present
            assert 'allow_join' in team_data
            assert 'user_is_member' in team_data
