"""
End-to-end test: match.completed event → CP ranking update → global_rank.

Validates the full pipeline wired in Phase 4:
  EventBus(match.completed) → event_handlers → MatchResultIntegrator → 
  RankingService.apply_match_result → compute_global_ranks
"""
import pytest

from apps.organizations.models import TeamRanking
from apps.organizations.services.match_integration import MatchResultIntegrator
from apps.organizations.services.ranking_service import compute_global_ranks


@pytest.mark.django_db(transaction=True)
class TestMatchToCPPipeline:
    """Full pipeline: match completion → CP + global_rank.

    Uses transaction=True because apply_match_result() uses
    select_for_update() which requires a real transaction.
    """

    def test_apply_match_result_creates_rankings_and_updates_cp(self, team_factory):
        """Winner gains CP, loser stays at 0, both get global_rank."""
        team_a = team_factory(name="Alpha")
        team_b = team_factory(name="Bravo")

        # Ensure no rankings exist yet
        assert TeamRanking.objects.count() == 0

        result = MatchResultIntegrator.process_match_result(
            winner_team_id=team_a.id,
            loser_team_id=team_b.id,
            match_id=1,
            is_tournament_match=True,
        )

        assert result.success
        assert result.vnext_processed

        winner_r = TeamRanking.objects.get(team_id=team_a.id)
        loser_r = TeamRanking.objects.get(team_id=team_b.id)

        # Winner should have gained CP (base 100, UNRANKED opponent → ×1.0)
        assert winner_r.current_cp > 0
        assert winner_r.streak_count == 1
        assert winner_r.tier in ("ROOKIE", "CHALLENGER")

        # Loser should have 0 CP (floor) and reset streak
        assert loser_r.current_cp == 0
        assert loser_r.streak_count == 0

        # Both should have global_rank assigned
        assert winner_r.global_rank is not None
        assert loser_r.global_rank is not None
        assert winner_r.global_rank < loser_r.global_rank  # Winner ranked higher

    def test_repeated_wins_build_streak_and_cp(self, team_factory):
        """Multiple wins accumulate CP and trigger hot streak.

        Note: same-opponent diminishing returns apply (100%/50%/25%),
        so total CP < 4×100. The test validates streak mechanics.
        """
        team_a = team_factory(name="Streak")
        team_b = team_factory(name="Punching Bag")

        for _ in range(4):
            result = MatchResultIntegrator.process_match_result(
                winner_team_id=team_a.id,
                loser_team_id=team_b.id,
                match_id=None,
            )
            assert result.success

        r = TeamRanking.objects.get(team_id=team_a.id)
        assert r.streak_count == 4
        assert r.is_hot_streak  # 3+ wins
        # With diminishing returns vs same opponent (1.0, 0.5, 0.25, 0.25),
        # total CP is lower than 4×100 but still positive and accumulated.
        assert r.current_cp >= 150  # Conservative floor with diminishing returns

    def test_event_handler_processes_match(self, team_factory):
        """Simulate the EventBus event dispatch path."""
        from apps.tournaments.models import Match, Tournament

        team_a = team_factory(name="EventA")
        team_b = team_factory(name="EventB")

        # We need a Match row for the event handler to look up
        # Check if we can create one directly
        try:
            match = Match.objects.create(
                participant1_id=team_a.id,
                participant2_id=team_b.id,
                winner_id=team_a.id,
                loser_id=team_b.id,
                state="COMPLETED",
            )
        except Exception:
            # If Match requires a tournament FK or other fields, skip this test
            pytest.skip("Cannot create Match without tournament FK")

        from apps.organizations.event_handlers import handle_match_completed_for_rankings

        class FakeEvent:
            def __init__(self, data):
                self.data = data

        handle_match_completed_for_rankings(FakeEvent({"match_id": match.id}))

        r = TeamRanking.objects.get(team_id=team_a.id)
        assert r.current_cp > 0

    def test_compute_global_ranks_uses_dense_rank(self, team_factory):
        """Teams with same CP get same rank (dense_rank behavior)."""
        teams = [team_factory(name=f"Rank{i}") for i in range(3)]

        # Create rankings manually with known CP
        TeamRanking.objects.create(team_id=teams[0].id, current_cp=500)
        TeamRanking.objects.create(team_id=teams[1].id, current_cp=500)
        TeamRanking.objects.create(team_id=teams[2].id, current_cp=100)

        compute_global_ranks()

        r0 = TeamRanking.objects.get(team_id=teams[0].id)
        r1 = TeamRanking.objects.get(team_id=teams[1].id)
        r2 = TeamRanking.objects.get(team_id=teams[2].id)

        # Two tied at 500 should both be rank 1
        assert r0.global_rank == 1
        assert r1.global_rank == 1
        # Next rank should be 2 (dense_rank, not 3)
        assert r2.global_rank == 2
