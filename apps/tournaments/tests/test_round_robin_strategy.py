"""
Round Robin Strategy — acceptance tests (Phase 2).

Acceptance criteria from the audit:
  1. 3-player Round Robin creates exactly 3 Match rows.
  2. No TBA / empty names in generated match participants.
  3. Standings update (via calculate_group_standings) after a match result is entered.
  4. Champion can be identified from points / tiebreaker after all matches complete.
  5. Calling generate_fixtures twice raises ValidationError (idempotency guard).
  6. Reset clears all data; generate_fixtures works again afterward.
  7. TOCBracketsService.generate_bracket() routes round_robin to the strategy.
  8. TOCBracketsService.reset_bracket() routes round_robin to the strategy.
  9. _build_lifecycle_stepper uses 'Generate Fixtures' label for round_robin.
 10. RoundRobinStrategy.can_finalize() reflects pending vs completed state.

Manual checklist after deployment:
  /toc/<slug>/#overview  → stepper shows "Generate Fixtures" not "Generate Bracket"
  /toc/<slug>/#matches   → 3 rows for 3-player solo RR
  /toc/<slug>/#schedule  → 3 fixtures
  /toc/<slug>/#standings → league table
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration, Match
from apps.tournaments.models.group import Group, GroupStage, GroupStanding
from apps.tournaments.services.format_strategy import (
    RoundRobinStrategy,
    get_strategy,
    format_has_strategy,
)

User = get_user_model()


# ─── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def game(db):
    from apps.tournaments.models import Game
    return Game.objects.create(
        name="Test Game",
        slug="test-game-rr",
        is_active=True,
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username="rr_organizer",
        email="rr_organizer@test.com",
        password="pass123",
    )


@pytest.fixture
def rr_tournament(db, game, organizer):
    """Solo Round Robin tournament in registration_closed state."""
    return Tournament.objects.create(
        name="RR Test Cup",
        slug="rr-test-cup",
        description="Round robin acceptance test",
        game=game,
        organizer=organizer,
        format=Tournament.ROUND_ROBIN,
        participation_type=Tournament.SOLO,
        min_participants=2,
        max_participants=8,
        status=Tournament.REGISTRATION_CLOSED,
        registration_start=timezone.now() - timezone.timedelta(days=5),
        registration_end=timezone.now() - timezone.timedelta(days=1),
        tournament_start=timezone.now() + timezone.timedelta(days=2),
    )


def _make_confirmed_player(db_fixture, *, username, tournament):
    """Create a user + confirmed Registration and return both."""
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass123",
    )
    reg = Registration.objects.create(
        tournament=tournament,
        user=user,
        status=Registration.CONFIRMED,
    )
    return user, reg


@pytest.fixture
def three_players(db, rr_tournament):
    """Three confirmed solo registrations for the RR tournament."""
    pa, _ = _make_confirmed_player(db, username="player_alice", tournament=rr_tournament)
    pb, _ = _make_confirmed_player(db, username="player_bob",   tournament=rr_tournament)
    pc, _ = _make_confirmed_player(db, username="player_carol", tournament=rr_tournament)
    return pa, pb, pc


@pytest.fixture
def strategy():
    return RoundRobinStrategy()


# ─── Registry smoke tests ──────────────────────────────────────────────────────

def test_registry_round_robin_registered():
    assert format_has_strategy("round_robin")


def test_registry_get_strategy_returns_correct_type():
    s = get_strategy("round_robin")
    assert isinstance(s, RoundRobinStrategy)


def test_registry_all_formats_registered():
    for fmt in ("single_elimination", "double_elimination", "round_robin", "swiss", "group_playoff"):
        assert format_has_strategy(fmt), f"'{fmt}' not in registry"


# ─── Core: fixture generation ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_generate_fixtures_creates_exactly_3_matches(rr_tournament, three_players, strategy):
    """3 confirmed players → exactly 3 Match rows."""
    result = strategy.generate_fixtures(rr_tournament, {})

    matches = Match.objects.filter(
        tournament=rr_tournament,
        bracket__isnull=True,
        is_deleted=False,
    )
    assert matches.count() == 3, (
        f"Expected 3 matches, got {matches.count()}. Result: {result}"
    )
    assert result["fixtures"] == 3
    assert result["participants"] == 3
    assert result["expected_fixtures"] == 3


@pytest.mark.django_db
def test_generate_fixtures_creates_group_stage_and_group(rr_tournament, three_players, strategy):
    """GroupStage + Group should be created with correct metadata."""
    result = strategy.generate_fixtures(rr_tournament, {})

    stages = GroupStage.objects.filter(tournament=rr_tournament)
    assert stages.count() == 1
    stage = stages.first()
    assert stage.num_groups == 1
    assert stage.format == "round_robin"
    assert stage.state == "active"

    groups = Group.objects.filter(tournament=rr_tournament)
    assert groups.count() == 1
    group = groups.first()
    assert group.max_participants == 3

    standings = GroupStanding.objects.filter(group=group)
    assert standings.count() == 3

    # All 3 players should have user FK set (solo tournament)
    user_ids = set(standings.values_list("user_id", flat=True))
    assert len(user_ids) == 3
    assert None not in user_ids


@pytest.mark.django_db
def test_generate_fixtures_no_tba_names(rr_tournament, three_players, strategy):
    """No match should have TBA / empty participant names."""
    strategy.generate_fixtures(rr_tournament, {})

    matches = Match.objects.filter(
        tournament=rr_tournament,
        bracket__isnull=True,
        is_deleted=False,
    )
    tba_values = {"tba", "tbd", "pending", "to be decided", "to be announced", ""}

    for match in matches:
        p1 = (match.participant1_name or "").strip().lower()
        p2 = (match.participant2_name or "").strip().lower()
        assert p1 not in tba_values, f"Match {match.id} has TBA participant1: '{match.participant1_name}'"
        assert p2 not in tba_values, f"Match {match.id} has TBA participant2: '{match.participant2_name}'"
        assert match.participant1_id is not None, f"Match {match.id} missing participant1_id"
        assert match.participant2_id is not None, f"Match {match.id} missing participant2_id"


@pytest.mark.django_db
def test_generate_fixtures_all_matches_scheduled_state(rr_tournament, three_players, strategy):
    """Newly generated matches must be in SCHEDULED state, ready for play."""
    strategy.generate_fixtures(rr_tournament, {})

    non_scheduled = Match.objects.filter(
        tournament=rr_tournament,
        bracket__isnull=True,
        is_deleted=False,
    ).exclude(state=Match.SCHEDULED)

    assert non_scheduled.count() == 0, (
        f"Some matches are not SCHEDULED: "
        f"{list(non_scheduled.values_list('id', 'state'))}"
    )


@pytest.mark.django_db
def test_generate_fixtures_every_pair_plays_once(rr_tournament, three_players, strategy):
    """Each unique (participant1_id, participant2_id) pair appears exactly once."""
    strategy.generate_fixtures(rr_tournament, {})

    matches = list(
        Match.objects.filter(
            tournament=rr_tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).values_list("participant1_id", "participant2_id")
    )

    # Normalise pairs so order doesn't matter
    canonical = {frozenset([p1, p2]) for p1, p2 in matches}
    assert len(canonical) == 3, f"Expected 3 unique pairings, got {len(canonical)}: {canonical}"


# ─── Idempotency + reset ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_generate_fixtures_idempotency_guard(rr_tournament, three_players, strategy):
    """Calling generate_fixtures twice raises ValidationError."""
    strategy.generate_fixtures(rr_tournament, {})

    with pytest.raises(ValidationError, match="already been generated"):
        strategy.generate_fixtures(rr_tournament, {})


@pytest.mark.django_db
def test_reset_clears_all_data(rr_tournament, three_players, strategy):
    """After reset, no Matches, Groups, GroupStandings, or GroupStages remain."""
    strategy.generate_fixtures(rr_tournament, {})

    strategy.reset_fixtures(rr_tournament)

    assert Match.objects.filter(tournament=rr_tournament, bracket__isnull=True).count() == 0
    assert Group.objects.filter(tournament=rr_tournament).count() == 0
    assert GroupStage.objects.filter(tournament=rr_tournament).count() == 0


@pytest.mark.django_db
def test_reset_then_regenerate_works(rr_tournament, three_players, strategy):
    """Generate → Reset → Generate must produce 3 matches again."""
    strategy.generate_fixtures(rr_tournament, {})
    strategy.reset_fixtures(rr_tournament)
    result = strategy.generate_fixtures(rr_tournament, {})

    assert result["fixtures"] == 3
    assert Match.objects.filter(tournament=rr_tournament, bracket__isnull=True, is_deleted=False).count() == 3


# ─── Standings after result ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_standings_update_after_match_result(rr_tournament, three_players, strategy):
    """
    After one match is marked completed, calculate_group_standings() must
    reflect the winner's 3 points and the loser's 0 points.
    """
    from apps.tournaments.services.group_stage_service import GroupStageService

    strategy.generate_fixtures(rr_tournament, {})

    stage = GroupStage.objects.get(tournament=rr_tournament)
    alice, bob, carol = three_players

    # Find the Alice vs Bob match
    match = Match.objects.filter(
        tournament=rr_tournament,
        bracket__isnull=True,
        is_deleted=False,
    ).filter(
        participant1_id__in=[alice.id, bob.id],
        participant2_id__in=[alice.id, bob.id],
    ).first()
    assert match is not None, "Expected a match between alice and bob"

    # Alice wins
    match.state = Match.COMPLETED
    match.winner_id = alice.id
    match.participant1_score = 2
    match.participant2_score = 0
    match.completed_at = timezone.now()
    match.save()

    # Recalculate standings from match data
    standings_data = GroupStageService.calculate_group_standings(stage.id)
    group = Group.objects.get(tournament=rr_tournament)
    group_standings = standings_data.get(group.id, [])

    # Map by participant id
    by_id = {s["participant_id"]: s for s in group_standings}

    assert by_id[alice.id]["points"] == 3, f"Alice should have 3 pts, got {by_id[alice.id]['points']}"
    assert by_id[bob.id]["points"] == 0,   f"Bob should have 0 pts, got {by_id[bob.id]['points']}"
    assert by_id[alice.id]["wins"] == 1,   f"Alice should have 1 win"
    assert by_id[bob.id]["losses"] == 1,   f"Bob should have 1 loss"


# ─── can_finalize ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_can_finalize_false_when_matches_pending(rr_tournament, three_players, strategy):
    """can_finalize() must return False while any match is SCHEDULED."""
    strategy.generate_fixtures(rr_tournament, {})

    ok, reason = strategy.can_finalize(rr_tournament)
    assert ok is False
    assert "pending" in reason.lower() or "match" in reason.lower()


@pytest.mark.django_db
def test_can_finalize_true_after_all_matches_complete(rr_tournament, three_players, strategy):
    """can_finalize() must return True when all matches are COMPLETED."""
    strategy.generate_fixtures(rr_tournament, {})

    alice, bob, carol = three_players
    matches = Match.objects.filter(
        tournament=rr_tournament, bracket__isnull=True, is_deleted=False
    )
    for match in matches:
        match.state = Match.COMPLETED
        match.winner_id = match.participant1_id
        match.completed_at = timezone.now()
        match.save()

    ok, reason = strategy.can_finalize(rr_tournament)
    assert ok is True, f"Expected finalize=True but got: ({ok}, '{reason}')"
    assert reason == ""


@pytest.mark.django_db
def test_champion_identified_by_points(rr_tournament, three_players, strategy):
    """
    After Alice wins all 2 matches (A beats B, A beats C), she has the
    highest points in calculate_group_standings() and should be ranked 1st.
    """
    from apps.tournaments.services.group_stage_service import GroupStageService

    strategy.generate_fixtures(rr_tournament, {})
    stage = GroupStage.objects.get(tournament=rr_tournament)
    group = Group.objects.get(tournament=rr_tournament)
    alice, bob, carol = three_players

    # Alice beats Bob and Carol; Bob beats Carol
    alice_matches = Match.objects.filter(
        tournament=rr_tournament,
        bracket__isnull=True,
        is_deleted=False,
    ).filter(
        participant1_id__in=[alice.id, bob.id, carol.id],
        participant2_id__in=[alice.id, bob.id, carol.id],
    )

    for match in alice_matches:
        # If Alice is a participant, she wins; otherwise Bob beats Carol
        if alice.id in (match.participant1_id, match.participant2_id):
            winner = alice.id
        else:
            winner = match.participant1_id  # Bob
        match.state = Match.COMPLETED
        match.winner_id = winner
        match.completed_at = timezone.now()
        match.save()

    standings_data = GroupStageService.calculate_group_standings(stage.id)
    group_rows = standings_data.get(group.id, [])
    assert group_rows, "No standings rows returned"

    # Rank 1 should be Alice (most wins, most points)
    top = group_rows[0]
    assert top["participant_id"] == alice.id, (
        f"Expected Alice (id={alice.id}) as #1, got participant_id={top['participant_id']}"
    )
    assert top["rank"] == 1


# ─── TOCBracketsService routing ────────────────────────────────────────────────

@pytest.mark.django_db
def test_toc_generate_bracket_routes_to_strategy(rr_tournament, three_players):
    """TOCBracketsService.generate_bracket() must use the strategy for round_robin."""
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService

    organizer = rr_tournament.organizer
    result = TOCBracketsService.generate_bracket(rr_tournament, organizer)

    assert result.get("status") == "fixtures_generated"
    assert result.get("fixtures") == 3
    assert Match.objects.filter(
        tournament=rr_tournament, bracket__isnull=True, is_deleted=False
    ).count() == 3


@pytest.mark.django_db
def test_toc_reset_bracket_routes_to_strategy(rr_tournament, three_players):
    """TOCBracketsService.reset_bracket() must clear the RR fixtures."""
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService

    organizer = rr_tournament.organizer
    TOCBracketsService.generate_bracket(rr_tournament, organizer)
    result = TOCBracketsService.reset_bracket(rr_tournament, organizer)

    assert result.get("status") == "reset"
    assert Match.objects.filter(
        tournament=rr_tournament, bracket__isnull=True, is_deleted=False
    ).count() == 0
    assert GroupStage.objects.filter(tournament=rr_tournament).count() == 0


# ─── Lifecycle stepper ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_lifecycle_stepper_uses_generate_fixtures_label(rr_tournament, three_players):
    """The stepper for a round_robin tournament must say 'Generate Fixtures'."""
    from apps.tournaments.api.toc.service import TOCService

    # Inject minimal stubs so _build_lifecycle_stepper() doesn't fail
    reg_stats = {"confirmed": 3, "total": 3, "pending": 0, "checked_in": 0}
    match_stats = {"total": 0, "completed": 0, "scheduled": 0, "live": 0}

    stepper = TOCService._build_lifecycle_stepper(
        tournament=rr_tournament,
        reg_stats=reg_stats,
        match_stats=match_stats,
        group_progress=None,
        completion_payload={},
    )

    step_keys   = [s["key"]   for s in stepper["steps"]]
    step_labels = [s["label"] for s in stepper["steps"]]

    assert "generate_fixtures" in step_keys, f"Missing 'generate_fixtures' step. Keys: {step_keys}"
    assert "Generate Fixtures" in step_labels, f"Missing 'Generate Fixtures' label. Labels: {step_labels}"
    assert "generate_bracket" not in step_keys, (
        f"Round Robin should NOT show 'generate_bracket'. Keys: {step_keys}"
    )
    assert stepper["format"] == "round_robin"


@pytest.mark.django_db
def test_lifecycle_stepper_generate_fixtures_done_after_generation(rr_tournament, three_players):
    """After generating fixtures, the 'generate_fixtures' step must be 'done'."""
    from apps.tournaments.api.toc.service import TOCService

    strategy = RoundRobinStrategy()
    strategy.generate_fixtures(rr_tournament, {})

    total_matches = Match.objects.filter(
        tournament=rr_tournament, is_deleted=False
    ).count()

    match_stats = {"total": total_matches, "completed": 0, "scheduled": total_matches, "live": 0}
    reg_stats = {"confirmed": 3, "total": 3, "pending": 0, "checked_in": 0}

    stepper = TOCService._build_lifecycle_stepper(
        tournament=rr_tournament,
        reg_stats=reg_stats,
        match_stats=match_stats,
        group_progress=None,
        completion_payload={},
    )

    steps_by_key = {s["key"]: s for s in stepper["steps"]}
    assert steps_by_key["generate_fixtures"]["status"] == "done", (
        f"Expected 'generate_fixtures' to be 'done', "
        f"got '{steps_by_key['generate_fixtures']['status']}'"
    )


# ─── Minimum players validation ────────────────────────────────────────────────

@pytest.mark.django_db
def test_generate_fixtures_requires_at_least_2_players(rr_tournament, strategy):
    """Generating with 0 confirmed registrations must raise ValidationError."""
    with pytest.raises(ValidationError, match="at least 2"):
        strategy.generate_fixtures(rr_tournament, {})


@pytest.mark.django_db
def test_generate_fixtures_with_2_players_creates_1_match(rr_tournament, strategy):
    """2 players → exactly 1 match."""
    ua = User.objects.create_user(username="p2a", email="p2a@t.com", password="x")
    ub = User.objects.create_user(username="p2b", email="p2b@t.com", password="x")
    Registration.objects.create(tournament=rr_tournament, user=ua, status=Registration.CONFIRMED)
    Registration.objects.create(tournament=rr_tournament, user=ub, status=Registration.CONFIRMED)

    result = strategy.generate_fixtures(rr_tournament, {})
    assert result["fixtures"] == 1
    assert result["expected_fixtures"] == 1
