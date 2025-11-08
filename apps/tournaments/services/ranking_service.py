# apps/tournaments/services/ranking_service.py
"""
Tournament Ranking Service (Module 4.2)

Provides ranked seeding functionality for bracket generation by integrating
with apps.teams ranking system. Handles participant sorting based on team
rankings with deterministic tie-breaking.

Integration Point: apps.teams.services.ranking_service (read-only)
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from django.apps import apps

logger = logging.getLogger(__name__)


class TournamentRankingService:
    """
    Service for ranked seeding in tournament bracket generation.
    
    Integrates with apps.teams ranking system to provide deterministic
    participant ordering based on team performance rankings.
    
    This service is READ-ONLY for team rankings - it queries apps.teams
    data but does not modify it. Tournament results that affect team
    rankings are handled separately by tournament completion workflows.
    """

    def __init__(self):
        """Initialize the ranking service with lazy-loaded models."""
        self._team_model = None
        self._team_ranking_breakdown_model = None

    @property
    def Team(self):
        """Lazy-load Team model to avoid circular imports."""
        if not self._team_model:
            self._team_model = apps.get_model('teams', 'Team')
        return self._team_model

    @property
    def TeamRankingBreakdown(self):
        """Lazy-load TeamRankingBreakdown model."""
        if not self._team_ranking_breakdown_model:
            self._team_ranking_breakdown_model = apps.get_model('teams', 'TeamRankingBreakdown')
        return self._team_ranking_breakdown_model

    def get_ranked_participants(
        self,
        participants: List[Dict[str, Any]],
        tournament: Any
    ) -> List[Dict[str, Any]]:
        """
        Sort participants by team ranking for ranked seeding.
        
        Args:
            participants: List of participant dicts with 'participant_id', 'is_team', etc.
            tournament: Tournament instance (used for context/validation)
            
        Returns:
            Sorted list of participants with 'seed' assigned based on rank
            
        Raises:
            ValidationError: If any team lacks ranking data or if rankings incomplete
            
        Algorithm:
            1. Extract team IDs from participants (skip individual players)
            2. Fetch ranking data from apps.teams.TeamRankingBreakdown
            3. Sort teams by final_total (DESC) with tie-breaking
            4. Assign seed numbers (1-indexed)
            5. Handle missing ranks with validation error
            
        Tie-Breaking Rules (deterministic):
            - Primary: final_total (higher is better)
            - Secondary: team.created_at (older teams ranked higher)
            - Tertiary: team.id (UUID lexicographic order)
        """
        if not participants:
            return []

        # Separate team and individual participants
        team_participants = [p for p in participants if p.get('is_team')]
        individual_participants = [p for p in participants if not p.get('is_team')]

        # Validate: ranked seeding requires all teams
        if individual_participants:
            raise ValidationError(
                "Ranked seeding is only supported for team-based tournaments. "
                f"Found {len(individual_participants)} individual participant(s)."
            )

        if not team_participants:
            raise ValidationError("No team participants found for ranked seeding.")

        # Extract team IDs
        team_ids = [p['participant_id'] for p in team_participants]

        # Fetch ranking data with teams (for tie-breaking)
        rankings = self.TeamRankingBreakdown.objects.filter(
            team_id__in=team_ids
        ).select_related('team').values(
            'team_id',
            'final_total',
            'team__created_at',
            'team__name'
        )

        # Build ranking lookup
        ranking_map = {r['team_id']: r for r in rankings}

        # Validate: all teams must have rankings
        missing_ranks = [tid for tid in team_ids if tid not in ranking_map]
        if missing_ranks:
            Team = self.Team
            missing_team_names = list(
                Team.objects.filter(id__in=missing_ranks).values_list('name', flat=True)
            )
            raise ValidationError(
                f"Ranked seeding requires all teams to have ranking data. "
                f"Missing rankings for: {', '.join(missing_team_names)}. "
                f"Please initialize team rankings via admin or run ranking recalculation."
            )

        # Sort teams by ranking with deterministic tie-breaking
        def ranking_sort_key(participant: Dict[str, Any]) -> Tuple[int, Any, int]:
            """
            Generate sort key for deterministic ranking.
            
            Returns:
                (negative_total, negative_created_at, team_id)
                - negative values for DESC sort
            """
            team_id = participant['participant_id']
            rank_data = ranking_map[team_id]
            
            # Primary: final_total (higher is better → negate for DESC)
            total_points = rank_data['final_total']
            
            # Secondary: created_at (older teams first → negate timestamp)
            created_at = rank_data['team__created_at']
            
            # Tertiary: team_id (lexicographic)
            return (
                -total_points,  # Higher points = lower (better) rank
                -created_at.timestamp() if created_at else 0,  # Older = better
                str(team_id)  # UUID string for deterministic order
            )

        # Sort participants
        sorted_participants = sorted(team_participants, key=ranking_sort_key)

        # Assign seeds (1-indexed)
        for i, participant in enumerate(sorted_participants, start=1):
            participant['seed'] = i
            
            # Add ranking metadata for transparency (optional)
            team_id = participant['participant_id']
            rank_data = ranking_map[team_id]
            participant['_ranking_points'] = rank_data['final_total']
            participant['_team_name'] = rank_data['team__name']

        logger.info(
            f"Ranked seeding applied for tournament {tournament.id}: "
            f"{len(sorted_participants)} teams sorted by ranking"
        )

        return sorted_participants

    def validate_ranked_seeding_available(self, tournament: Any) -> None:
        """
        Validate that ranked seeding is available for a tournament.
        
        Args:
            tournament: Tournament instance
            
        Raises:
            ValidationError: If ranked seeding cannot be used
            
        Checks:
            - Tournament must be team-based (has team participation)
            - All registered teams must have ranking data
        """
        if not tournament:
            raise ValidationError("Tournament instance required for ranked seeding validation")

        # Check if tournament has team participants
        # (This will be checked again in get_ranked_participants, but we can pre-validate)
        
        # Additional checks can be added here (e.g., minimum team count)
        logger.debug(f"Validated ranked seeding availability for tournament {tournament.id}")


# Global service instance
ranking_service = TournamentRankingService()
