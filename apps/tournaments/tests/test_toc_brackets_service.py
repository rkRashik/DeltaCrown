import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.organizations.models import Team
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Bracket, BracketNode, Game, Group, GroupStage, GroupStanding, Match, Registration, Tournament
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
def test_generate_group_matches_uses_active_groups_not_stage_created_at_cutoff(
    tournament,
    organizer,
    drawn_group_stage,
):
    # Reproduce real TOC configure flow where GroupStage.created_at can be newer than groups.
    GroupStage.objects.filter(id=drawn_group_stage.id).update(
        created_at=timezone.now() + timedelta(minutes=5)
    )
    drawn_group_stage.refresh_from_db()
    drawn_group_stage.state = "pending"
    drawn_group_stage.save(update_fields=["state"])

    result = TOCBracketsService.generate_group_matches(tournament, {}, organizer)

    assert result["generated_matches"] == 6


@pytest.mark.django_db
def test_generate_group_matches_returns_specific_reason_for_underpopulated_group(
    tournament,
    organizer,
    drawn_group_stage,
):
    standings_qs = GroupStanding.objects.filter(
        group__tournament=tournament,
        is_deleted=False,
    ).order_by("id")
    keeper = standings_qs.first()
    assert keeper is not None
    standings_qs.exclude(id=keeper.id).update(is_deleted=True)

    with pytest.raises(ValueError, match="Group A has only 1 active participant"):
        TOCBracketsService.generate_group_matches(tournament, {}, organizer)


@pytest.mark.django_db
def test_group_generate_matches_api_returns_structured_validation_payload(
    tournament,
    organizer,
    drawn_group_stage,
):
    standings_qs = GroupStanding.objects.filter(
        group__tournament=tournament,
        is_deleted=False,
    ).order_by("id")
    keeper = standings_qs.first()
    assert keeper is not None
    standings_qs.exclude(id=keeper.id).update(is_deleted=True)

    client = APIClient()
    client.force_login(organizer)
    url = reverse("toc_api:groups-generate-matches", kwargs={"slug": tournament.slug})

    response = client.post(url, data={}, format="json")

    assert response.status_code == 400
    payload = response.json()
    assert "active participant" in payload.get("error", "")
    assert payload.get("code") in {
        "group_generation_blocked",
        "group_generation_zero_output",
    }
    details = payload.get("details") or {}
    blocked = details.get("blocked_groups") or []
    assert blocked and blocked[0].get("group_name") == "Group A"


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


@pytest.mark.django_db
def test_auto_schedule_avoids_concurrent_participant_overlap(tournament, organizer):
    base_start = timezone.now().replace(minute=0, second=0, microsecond=0)

    m1 = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=11,
        participant1_name="Player 11",
        participant2_id=12,
        participant2_name="Player 12",
        state=Match.SCHEDULED,
    )
    m2 = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=2,
        participant1_id=11,
        participant1_name="Player 11",
        participant2_id=13,
        participant2_name="Player 13",
        state=Match.SCHEDULED,
    )
    m3 = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=3,
        participant1_id=14,
        participant1_name="Player 14",
        participant2_id=15,
        participant2_name="Player 15",
        state=Match.SCHEDULED,
    )

    result = TOCBracketsService.auto_schedule(
        tournament,
        {
            "start_time": base_start.isoformat(),
            "match_duration_minutes": 60,
            "break_minutes": 0,
            "max_concurrent": 2,
            "round_break_minutes": 0,
        },
        organizer,
    )

    assert result["scheduled"] == 3

    m1.refresh_from_db()
    m2.refresh_from_db()
    m3.refresh_from_db()

    # Player 11 appears in m1 and m2, so these cannot share a slot.
    assert m1.scheduled_time != m2.scheduled_time

    # Parallelism should still happen for disjoint participants.
    unique_slots = {m1.scheduled_time, m2.scheduled_time, m3.scheduled_time}
    assert len(unique_slots) == 2

    conflicts = TOCBracketsService._detect_schedule_conflicts([m1, m2, m3])
    assert conflicts == []


@pytest.mark.django_db
def test_generate_bracket_group_playoff_blocks_before_group_matches_exist(
    tournament,
    organizer,
    drawn_group_stage,
):
    with pytest.raises(ValueError, match="group-stage matches are generated"):
        TOCBracketsService.generate_bracket(
            tournament,
            organizer,
            {"seeding_method": "group_standings"},
        )


@pytest.mark.django_db
def test_generate_bracket_group_playoff_uses_cross_group_seeding(tournament, organizer):
    teams = [
        Team.objects.create(
            name=f"Playoff Team {i}",
            tag=f"P{i}",
            slug=f"playoff-team-{i}",
            game=tournament.game.slug,
        )
        for i in range(1, 5)
    ]

    stage = GroupStageService.create_groups(
        tournament_id=tournament.id,
        num_groups=2,
        group_size=2,
        advancement_count_per_group=2,
    )
    GroupStageService.auto_balance_groups(
        stage_id=stage.id,
        participant_ids=[team.id for team in teams],
        is_team=True,
    )
    GroupStageService.generate_group_matches(stage.id, rounds=1)

    groups = list(Group.objects.filter(tournament=tournament, is_deleted=False).order_by("display_order"))
    assert len(groups) == 2

    group_a_match = Match.objects.get(
        tournament=tournament,
        bracket__isnull=True,
        lobby_info__group_id=groups[0].id,
    )
    group_b_match = Match.objects.get(
        tournament=tournament,
        bracket__isnull=True,
        lobby_info__group_id=groups[1].id,
    )

    # Force deterministic final tables: participant1 wins in each group.
    for match in (group_a_match, group_b_match):
        match.participant1_score = 2
        match.participant2_score = 0
        match.winner_id = match.participant1_id
        match.loser_id = match.participant2_id
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save(
            update_fields=[
                "participant1_score",
                "participant2_score",
                "winner_id",
                "loser_id",
                "state",
                "completed_at",
            ]
        )

    TOCBracketsService.generate_bracket(
        tournament,
        organizer,
        {"seeding_method": "group_standings"},
    )

    bracket = Bracket.objects.get(tournament=tournament)
    round_one_nodes = list(
        BracketNode.objects.filter(bracket=bracket, round_number=1).order_by("match_number_in_round")
    )
    assert len(round_one_nodes) == 2

    expected_pair_a = frozenset({group_a_match.participant1_id, group_b_match.participant2_id})
    expected_pair_b = frozenset({group_b_match.participant1_id, group_a_match.participant2_id})
    actual_pairs = {
        frozenset({node.participant1_id, node.participant2_id})
        for node in round_one_nodes
    }
    assert actual_pairs == {expected_pair_a, expected_pair_b}


@pytest.mark.django_db
def test_draw_groups_respects_notify_toggle(tournament, organizer, monkeypatch):
    GroupStageService.create_groups(
        tournament_id=tournament.id,
        num_groups=2,
        group_size=2,
        advancement_count_per_group=1,
    )

    fired_events = []

    def _fake_draw_groups(*args, **kwargs):
        return None

    def _fake_fire_auto_event(_tournament, event, context=None):
        fired_events.append((event, context or {}))

    monkeypatch.setattr(GroupStageService, "draw_groups", staticmethod(_fake_draw_groups))

    monkeypatch.setattr(
        "apps.tournaments.api.toc.notifications_service.TOCNotificationsService.fire_auto_event",
        _fake_fire_auto_event,
    )

    TOCBracketsService.draw_groups(
        tournament,
        {"method": "random", "notify_participants": False},
        organizer,
    )
    assert fired_events == []

    stage = GroupStage.objects.get(tournament=tournament)
    stage.state = "pending"
    stage.save(update_fields=["state"])

    TOCBracketsService.draw_groups(
        tournament,
        {"method": "random", "notify_participants": True, "force_email": True},
        organizer,
    )
    assert len(fired_events) == 1
    assert fired_events[0][0] == "group_draw_completed"
    assert fired_events[0][1].get("force_email") is True


@pytest.mark.django_db
def test_auto_schedule_fires_schedule_generated_event_when_enabled(tournament, organizer, monkeypatch):
    Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=101,
        participant1_name="Alpha",
        participant2_id=102,
        participant2_name="Bravo",
        state=Match.SCHEDULED,
    )

    fired_events = []

    def _fake_fire_auto_event(_tournament, event, context=None):
        fired_events.append((event, context or {}))

    monkeypatch.setattr(
        "apps.tournaments.api.toc.notifications_service.TOCNotificationsService.fire_auto_event",
        _fake_fire_auto_event,
    )

    result = TOCBracketsService.auto_schedule(
        tournament,
        {
            "start_time": timezone.now().isoformat(),
            "match_duration_minutes": 30,
            "break_minutes": 5,
            "max_concurrent": 1,
            "round_break_minutes": 0,
            "notify_participants": True,
            "force_email": True,
        },
        organizer,
    )

    assert result["scheduled"] == 1
    assert result["notified_participants"] is True
    assert len(fired_events) == 1
    assert fired_events[0][0] == "schedule_generated"
    assert fired_events[0][1].get("force_email") is True


@pytest.mark.django_db
def test_send_match_reminders_targets_upcoming_registered_participants(
    tournament,
    organizer,
    monkeypatch,
):
    player_one = User.objects.create_user(
        username="reminder-player-1",
        email="reminder-player-1@test.com",
        password="pass123",
    )
    player_two = User.objects.create_user(
        username="reminder-player-2",
        email="reminder-player-2@test.com",
        password="pass123",
    )

    Registration.objects.create(
        tournament=tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )
    Registration.objects.create(
        tournament=tournament,
        user=player_two,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name=player_one.username,
        participant2_id=player_two.id,
        participant2_name=player_two.username,
        state=Match.SCHEDULED,
        scheduled_time=timezone.now() + timedelta(minutes=20),
    )

    fired_events = []

    def _fake_fire_auto_event(_tournament, event, context=None):
        fired_events.append((event, context or {}))

    monkeypatch.setattr(
        "apps.tournaments.api.toc.notifications_service.TOCNotificationsService.fire_auto_event",
        _fake_fire_auto_event,
    )

    result = TOCBracketsService.send_match_reminders(
        tournament,
        {"minutes_ahead": 30, "force_email": True},
        organizer,
    )

    assert result["reminders_sent"] == 1
    assert result["recipients_notified"] == 2
    assert len(fired_events) == 1
    assert fired_events[0][0] == "match_ready"
    assert sorted(fired_events[0][1].get("target_user_ids", [])) == sorted([player_one.id, player_two.id])

