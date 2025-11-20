"""
LeaderboardService - BR & Series standings calculation (Milestone E)

Source Documents:
- Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Leaderboard UI specs)

Architecture Decisions:
- ADR-001: Service layer pattern - All business logic in service layer
- ADR-004: PostgreSQL JSONB for match results storage

Technical Standards:
- PEP 8 compliance with Black formatting (line length: 120)
- Type hints for all public methods
- Google-style docstrings
- Transaction safety with @transaction.atomic

Milestone E Scope:
- BR leaderboard calculation (Free Fire, PUBG Mobile)
- Series summary aggregation (Valorant, CS2, Dota2, MLBB, CODM)
- Staff placement overrides with audit trails
"""

import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from apps.tournaments.models import Tournament, Match, Registration, TournamentResult
from apps.tournaments.games.points import calc_ff_points, calc_pubgm_points

logger = logging.getLogger(__name__)


class LeaderboardService:
    """
    Service for calculating tournament standings and leaderboards.
    
    Implements game-aware leaderboard logic:
    - BR games (Free Fire, PUBG Mobile): Points-based with tiebreakers
    - Series games (Valorant, CS2, Dota2, MLBB, CODM): Best-of-X aggregation
    - Staff overrides: Manual placement adjustments with audit trail
    """
    
    @staticmethod
    def calculate_br_standings(
        tournament_id: int,
        match_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate BR leaderboard from match results.
        
        Algorithm:
        1. Fetch all completed matches for tournament (or specific matches)
        2. Parse lobby_info JSON for kills/placement per team
        3. Calculate points using calc_ff_points() or calc_pubgm_points()
        4. Aggregate by participant_id
        5. Apply 3-level tiebreaker:
           - Level 1: Total points (DESC)
           - Level 2: Total kills (DESC)
           - Level 3: Best placement (ASC - lower is better)
           - Level 4: Earliest completion timestamp (ASC)
        6. Return ranked list
        
        Args:
            tournament_id: Tournament ID to calculate standings for
            match_ids: Optional list of specific match IDs to include
        
        Returns:
            List of standings entries sorted by rank (IDs-only, no PII):
            [
                {
                    'rank': 1,
                    'participant_id': 'team-123',
                    'team_id': 456,
                    'total_points': 45,
                    'total_kills': 18,
                    'best_placement': 1,
                    'matches_played': 3,
                    'avg_placement': 2.33,
                    'tiebreaker_timestamp': '2025-11-13T15:30:00Z'
                },
                ...
            ]
            
        Note:
            Responses contain IDs only per PII discipline. Clients should resolve
            participant_id/team_id to display names via separate profile/team APIs.
        
        Raises:
            ValidationError: If tournament not found or no completed matches
        
        Example:
            >>> standings = LeaderboardService.calculate_br_standings(tournament_id=123)
            >>> print(f"Winner: {standings[0]['participant_name']} with {standings[0]['total_points']} points")
        """
        # Fetch tournament
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found")
        
        # Determine game-specific point calculator
        from apps.common.game_registry import normalize_slug
        game_slug = normalize_slug(tournament.game.slug) if hasattr(tournament, 'game') and tournament.game else ''
        if game_slug == 'free-fire':
            calc_points = calc_ff_points
        elif game_slug == 'pubg-mobile':
            calc_points = calc_pubgm_points
        else:
            raise ValidationError(
                f"Tournament game '{game_slug}' is not a BR game. "
                "Use calculate_series_summary() for series-based games."
            )
        
        # Fetch completed matches
        matches_query = Match.objects.filter(
            tournament_id=tournament_id,
            state=Match.COMPLETED
        )
        
        if match_ids:
            matches_query = matches_query.filter(id__in=match_ids)
        
        matches = matches_query.order_by('completed_at')
        
        if not matches.exists():
            logger.warning(f"No completed matches found for tournament {tournament_id}")
            return []
        
        # Aggregate results by participant
        standings_map = {}  # participant_id -> aggregated data
        
        for match in matches:
            lobby_info = match.lobby_info or {}
            
            # Parse results from lobby_info
            # Expected structure: {"team-123": {"kills": 5, "placement": 1}, ...}
            for participant_id, result_data in lobby_info.items():
                if not isinstance(result_data, dict):
                    logger.warning(f"Invalid lobby_info format in match {match.id}: {result_data}")
                    continue
                
                kills = result_data.get('kills', 0)
                placement = result_data.get('placement', 99)  # Default to worst placement
                
                # Calculate points
                points = calc_points(kills, placement)
                
                # Initialize participant entry if new
                if participant_id not in standings_map:
                    # Fetch team_id for response (IDs-only, no names per PII discipline)
                    team_id = None
                    try:
                        registration = Registration.objects.get(
                            tournament_id=tournament_id,
                            participant_id=participant_id
                        )
                        team_id = registration.team_id
                    except Registration.DoesNotExist:
                        pass
                    
                    standings_map[participant_id] = {
                        'participant_id': participant_id,
                        'team_id': team_id,
                        'total_points': 0,
                        'total_kills': 0,
                        'best_placement': 99,
                        'matches_played': 0,
                        'placements': [],  # Track all placements for avg calculation
                        'tiebreaker_timestamp': None
                    }
                
                # Aggregate data
                standings_map[participant_id]['total_points'] += points
                standings_map[participant_id]['total_kills'] += kills
                standings_map[participant_id]['best_placement'] = min(
                    standings_map[participant_id]['best_placement'],
                    placement
                )
                standings_map[participant_id]['matches_played'] += 1
                standings_map[participant_id]['placements'].append(placement)
                
                # Update tiebreaker timestamp (earliest completion)
                if standings_map[participant_id]['tiebreaker_timestamp'] is None:
                    standings_map[participant_id]['tiebreaker_timestamp'] = match.completed_at
                else:
                    standings_map[participant_id]['tiebreaker_timestamp'] = min(
                        standings_map[participant_id]['tiebreaker_timestamp'],
                        match.completed_at
                    )
        
        # Calculate average placement
        for participant_id, data in standings_map.items():
            if data['placements']:
                data['avg_placement'] = round(
                    sum(data['placements']) / len(data['placements']),
                    2
                )
            else:
                data['avg_placement'] = 99.0
            
            # Convert timestamp to ISO string
            if data['tiebreaker_timestamp']:
                data['tiebreaker_timestamp'] = data['tiebreaker_timestamp'].isoformat()
            
            # Remove temporary placements list
            del data['placements']
        
        # Sort by tiebreaker rules
        standings_list = list(standings_map.values())
        standings_list.sort(
            key=lambda x: (
                -x['total_points'],      # Level 1: More points = better (DESC)
                -x['total_kills'],       # Level 2: More kills = better (DESC)
                x['best_placement'],     # Level 3: Lower placement = better (ASC)
                x['tiebreaker_timestamp'] or ''  # Level 4: Earlier = better (ASC)
            )
        )
        
        # Assign ranks
        for idx, entry in enumerate(standings_list, start=1):
            entry['rank'] = idx
        
        logger.info(
            f"Calculated BR standings for tournament {tournament_id}: "
            f"{len(standings_list)} participants, {matches.count()} matches"
        )
        
        return standings_list
    
    @staticmethod
    def calculate_series_summary(match_ids: List[int]) -> Dict[str, Any]:
        """
        Aggregate series results (Valorant, CS2, Dota2, etc.).
        
        Algorithm:
        1. Fetch matches by IDs
        2. Count wins per participant
        3. Determine series winner (first to reach majority)
        4. Return series score + game-by-game breakdown
        
        Args:
            match_ids: List of match IDs in the series
        
        Returns:
            {
                'series_winner_id': 'team-123',
                'series_score': {'team-123': 2, 'team-456': 1},
                'total_games': 3,
                'format': 'Best-of-3',
                'games': [
                    {
                        'match_id': 1,
                        'winner_id': 'team-123',
                        'loser_id': 'team-456',
                        'score': {'team-123': 13, 'team-456': 11},
                        'completed_at': '2025-11-13T15:00:00Z'
                    },
                    ...
                ]
            }
        
        Raises:
            ValidationError: If no matches found or series incomplete
        
        Example:
            >>> summary = LeaderboardService.calculate_series_summary([1, 2, 3])
            >>> print(f"Series winner: {summary['series_winner_id']}")
            >>> print(f"Final score: {summary['series_score']}")
        """
        if not match_ids:
            raise ValidationError("match_ids cannot be empty")
        
        # Fetch matches
        matches = Match.objects.filter(
            id__in=match_ids,
            state=Match.COMPLETED
        ).order_by('completed_at')
        
        if not matches.exists():
            raise ValidationError(f"No completed matches found for IDs: {match_ids}")
        
        # Initialize series data
        series_score = {}
        games = []
        
        for match in matches:
            # Validate match has winner
            if not match.winner_id:
                logger.warning(f"Match {match.id} has no winner, skipping")
                continue
            
            # Increment series score
            series_score[match.winner_id] = series_score.get(match.winner_id, 0) + 1
            
            # Parse match score from lobby_info
            match_score = match.lobby_info.get('score', {}) if match.lobby_info else {}
            
            games.append({
                'match_id': match.id,
                'winner_id': match.winner_id,
                'loser_id': match.loser_id,
                'score': match_score,
                'completed_at': match.completed_at.isoformat() if match.completed_at else None
            })
        
        # Determine series winner (most wins)
        if not series_score:
            raise ValidationError("No valid match results found in series")
        
        series_winner_id = max(series_score, key=series_score.get)
        
        # Determine series format
        total_games = len(games)
        if total_games <= 1:
            series_format = 'Best-of-1'
        elif total_games <= 3:
            series_format = 'Best-of-3'
        elif total_games <= 5:
            series_format = 'Best-of-5'
        else:
            series_format = f'Best-of-{total_games}'
        
        logger.info(
            f"Calculated series summary: Winner {series_winner_id}, "
            f"Score {series_score}, Format {series_format}"
        )
        
        return {
            'series_winner_id': series_winner_id,
            'series_score': series_score,
            'total_games': total_games,
            'format': series_format,
            'games': games
        }
    
    @staticmethod
    @transaction.atomic
    def override_placement(
        tournament_id: int,
        registration_id: int,  # Changed from participant_id to registration_id
        new_rank: int,
        reason: str,
        actor_id: int
    ) -> Dict[str, Any]:
        """
        Staff override for final placement (with audit trail).
        
        Creates or updates TournamentResult with manual placement.
        Sets is_override=True and populates override metadata.
        
        Args:
            tournament_id: Tournament ID
            registration_id: Registration ID to override placement for
            new_rank: New rank (1=1st place, 2=2nd place, etc.)
            reason: Reason for override (required)
            actor_id: Staff user performing override
        
        Returns:
            {
                'success': True,
                'result_id': 123,
                'old_rank': 2,
                'new_rank': 1,
                'override_timestamp': '2025-11-13T15:30:00Z'
            }
        
        Raises:
            ValidationError: If tournament/participant not found, or invalid rank
        
        Example:
            >>> result = LeaderboardService.override_placement(
            ...     tournament_id=123,
            ...     registration_id=456,
            ...     new_rank=1,
            ...     reason='Manual review - technical issue during match',
            ...     actor_id=789
            ... )
        """
        # Validate inputs
        if not reason or not reason.strip():
            raise ValidationError("override reason is required")
        
        if new_rank < 1:
            raise ValidationError(f"new_rank must be >= 1, got {new_rank}")
        
        # Fetch tournament
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found")
        
        # Fetch participant registration
        try:
            registration = Registration.objects.get(
                id=registration_id,
                tournament_id=tournament_id
            )
        except Registration.DoesNotExist:
            raise ValidationError(
                f"Registration {registration_id} not found in tournament {tournament_id}"
            )
        
        # Fetch or create TournamentResult
        result, created = TournamentResult.objects.get_or_create(
            tournament_id=tournament_id,
            defaults={
                'winner_id': registration.id,
                'determination_method': 'manual',
                'rules_applied': {'method': 'staff_override', 'reason': reason},  # Add rules_applied
                'is_override': True,
                'override_reason': reason,
                'override_actor_id': actor_id,
                'override_timestamp': timezone.now()
            }
        )
        
        old_rank = None
        if not created:
            # Determine old rank based on current result
            if result.winner_id == registration.id:
                old_rank = 1
            elif result.runner_up_id == registration.id:
                old_rank = 2
            elif result.third_place_id == registration.id:
                old_rank = 3
            else:
                old_rank = None  # Not previously placed
            
            # Update result with new placement
            if new_rank == 1:
                result.winner_id = registration.id
            elif new_rank == 2:
                result.runner_up_id = registration.id
            elif new_rank == 3:
                result.third_place_id = registration.id
            
            # Update override metadata
            result.is_override = True
            result.override_reason = reason
            result.override_actor_id = actor_id
            result.override_timestamp = timezone.now()
            result.save()
        
        logger.info(
            f"Placement override: Tournament {tournament_id}, "
            f"Registration {registration_id}, Rank {old_rank} → {new_rank}, "
            f"Actor {actor_id}"
        )
        
        return {
            'success': True,
            'result_id': result.id,
            'old_rank': old_rank,
            'new_rank': new_rank,
            'override_timestamp': result.override_timestamp.isoformat()
        }
