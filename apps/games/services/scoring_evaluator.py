"""
ScoringEvaluator — data-driven scoring for group-stage standings.

Replaces the hardcoded if/elif chain in GroupStageService._update_standing_from_match
with a dispatch-table approach driven by GameTournamentConfig.default_scoring_type.

Usage:
    from apps.games.services.scoring_evaluator import ScoringEvaluator

    evaluator = ScoringEvaluator()
    evaluator.update_standings(standing1, standing2, match_data, scoring_type, game_category)
"""

from decimal import Decimal
from typing import Any, Dict, Optional


class ScoringEvaluator:
    """Config-driven scoring dispatcher for group-stage standing updates."""

    # Map scoring_type → handler method name
    _HANDLERS = {
        'GOALS': '_apply_goals',
        'ROUNDS': '_apply_rounds',
        'PLACEMENT': '_apply_br',
        'KILLS': '_apply_br',
        'WIN_LOSS': '_apply_win_loss',
        'POINTS': '_apply_win_loss',
        'CUSTOM': '_apply_win_loss',
    }

    def update_standings(
        self,
        standing1,
        standing2,
        match_data: Dict[str, Any],
        scoring_type: str,
        game_category: Optional[str] = None,
        max_score: Optional[int] = None,
    ) -> None:
        """Apply game-specific stat updates to both standings.

        Args:
            standing1: GroupStanding for participant1
            standing2: GroupStanding for participant2
            match_data: Dict with participant1_*/participant2_* stat keys
            scoring_type: GameTournamentConfig.default_scoring_type value
            game_category: Game.category (e.g. 'MOBA', 'FPS', 'BR')
            max_score: Optional cap from GameTournamentConfig.max_score
        """
        # Validate score range if max_score is configured
        if max_score is not None:
            for key in ('participant1_score', 'participant2_score'):
                val = match_data.get(key)
                if val is not None:
                    try:
                        if int(val) > max_score:
                            raise ValueError(
                                f"Score {val} exceeds maximum allowed ({max_score}) "
                                f"for key '{key}'"
                            )
                    except (TypeError, ValueError) as exc:
                        if 'exceeds maximum' in str(exc):
                            raise
                        # Non-numeric values pass though — let handler deal with it

        # Special case: WIN_LOSS + MOBA category → use MOBA handler
        if scoring_type == 'WIN_LOSS' and game_category == 'MOBA':
            self._apply_moba(standing1, standing2, match_data)
            return

        handler_name = self._HANDLERS.get(scoring_type, '_apply_win_loss')
        handler = getattr(self, handler_name)
        handler(standing1, standing2, match_data)

    @staticmethod
    def _apply_goals(standing1, standing2, match_data: Dict[str, Any]) -> None:
        """Goals-based games (eFootball, FC Mobile, FIFA)."""
        standing1.goals_for += match_data.get('participant1_score', 0)
        standing1.goals_against += match_data.get('participant2_score', 0)
        standing1.goal_difference = standing1.goals_for - standing1.goals_against

        standing2.goals_for += match_data.get('participant2_score', 0)
        standing2.goals_against += match_data.get('participant1_score', 0)
        standing2.goal_difference = standing2.goals_for - standing2.goals_against

    @staticmethod
    def _apply_rounds(standing1, standing2, match_data: Dict[str, Any]) -> None:
        """Rounds-based games (Valorant, CS2, COD Mobile)."""
        standing1.rounds_won += match_data.get('participant1_rounds', 0)
        standing1.rounds_lost += match_data.get('participant2_rounds', 0)
        standing1.round_difference = standing1.rounds_won - standing1.rounds_lost

        standing2.rounds_won += match_data.get('participant2_rounds', 0)
        standing2.rounds_lost += match_data.get('participant1_rounds', 0)
        standing2.round_difference = standing2.rounds_won - standing2.rounds_lost

        # Also track kills/deaths for FPS games
        standing1.total_kills += match_data.get('participant1_kills', 0)
        standing1.total_deaths += match_data.get('participant1_deaths', 0)
        standing2.total_kills += match_data.get('participant2_kills', 0)
        standing2.total_deaths += match_data.get('participant2_deaths', 0)

    @staticmethod
    def _apply_br(standing1, standing2, match_data: Dict[str, Any]) -> None:
        """Battle Royale games (PUBG Mobile, Free Fire)."""
        standing1.total_kills += match_data.get('participant1_kills', 0)
        standing1.placement_points += Decimal(
            str(match_data.get('participant1_placement_points', 0))
        )

        standing2.total_kills += match_data.get('participant2_kills', 0)
        standing2.placement_points += Decimal(
            str(match_data.get('participant2_placement_points', 0))
        )

    @staticmethod
    def _apply_moba(standing1, standing2, match_data: Dict[str, Any]) -> None:
        """MOBA games (Mobile Legends) — KDA + assists tracking."""
        standing1.total_kills += match_data.get('participant1_kills', 0)
        standing1.total_deaths += match_data.get('participant1_deaths', 0)
        standing1.total_assists += match_data.get('participant1_assists', 0)
        standing1.kda_ratio = standing1.calculate_kda()

        standing2.total_kills += match_data.get('participant2_kills', 0)
        standing2.total_deaths += match_data.get('participant2_deaths', 0)
        standing2.total_assists += match_data.get('participant2_assists', 0)
        standing2.kda_ratio = standing2.calculate_kda()

        standing1.total_score += match_data.get('participant1_score', 0)
        standing2.total_score += match_data.get('participant2_score', 0)

    @staticmethod
    def _apply_win_loss(standing1, standing2, match_data: Dict[str, Any]) -> None:
        """Default win/loss — no extra stats to track."""
        pass


# Module-level singleton
scoring_evaluator = ScoringEvaluator()
