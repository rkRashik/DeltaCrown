import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import Team
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Game, GroupStanding, Match, Tournament
from apps.tournaments.services.group_stage_service import GroupStageService

User = get_user_model()


@pytest.fixture
def game(db):
    return Game.objects.create(
        name="TOC Test Game",
        slug="toc-test-game",
        is_active=True,
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username="toc-organizer",
        email="toc-organizer@test.com",
        password="pass123",
    )


@pytest.fixture
def tournament(db, game, organizer):
    return Tournament.objects.create(
        name="TOC Group Lifecycle",
        game=game,
        organizer=organizer,
        format=Tournament.GROUP_PLAYOFF,
        max_participants=16,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=8),
        tournament_end=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def drawn_group_stage(db, tournament):
    teams = [
        Team.objects.create(
            name=f"Team {i}",
            tag=f"T{i}",
            slug=f"toc-team-{i}",
            game=tournament.game.slug,
        )
        for i in range(1, 5)
    ]

    stage = GroupStageService.create_groups(
        tournament_id=tournament.id,
        num_groups=1,
        group_size=4,
        advancement_count_per_group=2,
    )

    GroupStageService.auto_balance_groups(
        stage_id=stage.id,
        participant_ids=[team.id for team in teams],
        is_team=True,
    )

    stage.state = "active"
    stage.save(update_fields=["state"])
    return stage


@pytest.mark.django_db
def test_generate_group_matches_requires_drawn_stage(tournament, organizer):
    stage = GroupStageService.create_groups(
        tournament_id=tournament.id,
        num_groups=1,
        group_size=4,
        advancement_count_per_group=2,
    )

    stage.state = "pending"
    stage.save(update_fields=["state"])

    with pytest.raises(ValueError, match="Draw groups first"):
        TOCBracketsService.generate_group_matches(tournament, {}, organizer)


@pytest.mark.django_db
def test_get_groups_infers_drawn_state_from_existing_standings(tournament, drawn_group_stage):
    drawn_group_stage.state = "pending"
    drawn_group_stage.save(update_fields=["state"])

    snapshot = TOCBracketsService.get_groups(tournament)

    assert snapshot["exists"] is True
    assert snapshot["stage"]["state"] == "active"


@pytest.mark.django_db
def test_generate_group_matches_allows_stale_pending_state_when_assignments_exist(
    tournament,
    organizer,
    drawn_group_stage,
):
    drawn_group_stage.state = "pending"
    drawn_group_stage.save(update_fields=["state"])

    result = TOCBracketsService.generate_group_matches(tournament, {}, organizer)

    assert result["generated_matches"] == 6
    drawn_group_stage.refresh_from_db()
    assert drawn_group_stage.state == "active"


@pytest.mark.django_db
def test_generate_group_matches_guard_prevents_duplicates(tournament, organizer, drawn_group_stage):
    first = TOCBracketsService.generate_group_matches(tournament, {}, organizer)
    assert first["generated_matches"] == 6
    assert Match.objects.filter(tournament=tournament).count() == 6

    with pytest.raises(ValueError, match="already exist"):
        TOCBracketsService.generate_group_matches(tournament, {}, organizer)


@pytest.mark.django_db
def test_generate_group_matches_ignores_unscoped_bracketless_matches(tournament, organizer, drawn_group_stage):
    group_team_ids = list(
        GroupStanding.objects.filter(
            group__tournament=tournament,
            is_deleted=False,
            team_id__isnull=False,
        ).values_list("team_id", flat=True)
    )
    assert len(group_team_ids) >= 2

    # Legacy/unscoped bracket-less match (missing lobby_info.group_id) should not block generation.
    Match.objects.create(
        tournament=tournament,
        participant1_id=group_team_ids[0],
        participant1_name="Legacy Team A",
        participant2_id=group_team_ids[1],
        participant2_name="Legacy Team B",
        round_number=1,
        match_number=99,
        state=Match.SCHEDULED,
        lobby_info={},
    )

    result = TOCBracketsService.generate_group_matches(tournament, {}, organizer)
    assert result["generated_matches"] == 6
    assert Match.objects.filter(tournament=tournament).count() == 7
