import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from apps.competition.services.challenge_service import BountyService, ChallengeService
from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import Team, TeamCompetitiveSettings, TeamMembership


pytestmark = pytest.mark.django_db

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, email=f"{username}@example.com", password="pass")


def _game(slug="valorant-settings"):
    return Game.objects.create(
        name=slug,
        display_name=slug.title(),
        slug=slug,
        short_code=slug[:3].upper(),
        category="FPS",
        game_type="TEAM_VS_TEAM",
        platforms=["PC"],
    )


def _team(name, owner, game):
    team = Team.objects.create(
        name=name,
        slug=name.lower().replace(" ", "-"),
        created_by=owner,
        game_id=game.pk,
        region="Bangladesh",
    )
    TeamMembership.objects.create(
        team=team,
        user=owner,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    return team


def _captain(team, username="captain"):
    user = _user(username)
    TeamMembership.objects.create(
        team=team,
        user=user,
        role=MembershipRole.PLAYER,
        status=MembershipStatus.ACTIVE,
        is_tournament_captain=True,
    )
    return user


def test_captain_showdown_creation_respects_team_policy():
    game = _game()
    owner = _user("owner")
    team = _team("Policy Team", owner, game)
    captain = _captain(team)
    TeamCompetitiveSettings.objects.create(
        team=team,
        showdown_create_policy=TeamCompetitiveSettings.AuthorityPolicy.OWNER_MANAGER,
    )

    with pytest.raises(PermissionDenied):
        ChallengeService.create_challenge(
            created_by=captain,
            challenger_team=team,
            game=game,
            title="Captain blocked",
        )


def test_captain_showdown_creation_allowed_when_policy_permits():
    game = _game("valorant-open")
    owner = _user("owner-open")
    team = _team("Open Policy Team", owner, game)
    captain = _captain(team, "captain-open")
    TeamCompetitiveSettings.objects.create(
        team=team,
        showdown_create_policy=TeamCompetitiveSettings.AuthorityPolicy.OWNER_MANAGER_CAPTAIN,
    )

    challenge = ChallengeService.create_challenge(
        created_by=captain,
        challenger_team=team,
        game=game,
        title="Captain allowed",
    )

    assert challenge.challenger_team == team


def test_showdown_entry_fee_cap_enforced_before_escrow():
    game = _game("cap-game")
    owner = _user("cap-owner")
    team = _team("Entry Cap Team", owner, game)
    TeamCompetitiveSettings.objects.create(team=team, max_showdown_entry_fee_dc=25)

    with pytest.raises(ValidationError):
        ChallengeService.create_challenge(
            created_by=owner,
            challenger_team=team,
            game=game,
            title="Too high",
            entry_fee_dc=50,
        )


def test_allowed_game_policy_enforced_for_showdown():
    game = _game("allowed-game")
    blocked_game = _game("blocked-game")
    owner = _user("game-owner")
    team = _team("Game Policy Team", owner, game)
    settings = TeamCompetitiveSettings.objects.create(team=team)
    settings.allowed_games.set([game])

    with pytest.raises(ValidationError):
        ChallengeService.create_challenge(
            created_by=owner,
            challenger_team=team,
            game=blocked_game,
            title="Wrong game",
        )


def test_bounty_reward_cap_enforced_before_escrow():
    game = _game("bounty-game")
    owner = _user("bounty-owner")
    team = _team("Bounty Policy Team", owner, game)
    TeamCompetitiveSettings.objects.create(team=team, max_bounty_reward_dc=100)

    with pytest.raises(ValidationError):
        BountyService.create_bounty(
            created_by=owner,
            issuer_team=team,
            game=game,
            title="Too much",
            is_hitlist=True,
            reward_amount_dc=101,
            challenger_entry_fee_dc=1,
        )
