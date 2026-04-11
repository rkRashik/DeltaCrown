"""
Group Stage Service - Business logic for group stage tournaments

Source Documents:
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 2.5)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 5: Service Layer)

Responsibilities:
- Group configuration and validation
- Participant assignment to groups (random, seeded, manual)
- Group draw execution with provability
- Standings calculation for all 9 supported games
- Tiebreaker resolution
- Advancement determination

Supported Games:
1. eFootball (goals-based)
2. FC Mobile (goals-based)
3. FIFA (goals-based)
4. Valorant (rounds-based)
5. CS2 (rounds-based)
6. PUBG Mobile (placement + kills)
7. Free Fire (placement + kills)
8. Mobile Legends (KDA-based)
9. Call of Duty Mobile (eliminations + score)
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import functools
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F, Prefetch
import random
import hashlib
import json

from apps.tournaments.models import (
    Tournament,
    Registration,
    Group,
    GroupStanding,
    Match,
)

logger = logging.getLogger(__name__)


class GroupStageService:
    """Service for group stage tournament logic."""

    @staticmethod
    def _active_groups_for_stage(stage) -> List[Group]:
        """Return the current non-deleted group set for a stage's tournament.

        Group records are currently tournament-scoped (no FK to GroupStage), so the
        active set must be resolved via soft-delete status, not stage timestamps.
        """
        groups = list(
            Group.objects.filter(
                tournament=stage.tournament,
                is_deleted=False,
            ).order_by('display_order', 'id')
        )
        if groups:
            return groups

        # Legacy safety fallback for older datasets without consistent soft-delete flags.
        return list(
            Group.objects.filter(
                tournament=stage.tournament,
                created_at__gte=stage.created_at,
            ).order_by('display_order', 'id')
        )
    
    @staticmethod
    @transaction.atomic
    def configure_groups(
        tournament_id: int,
        num_groups: int,
        points_system: Optional[Dict] = None,
        advancement_count: int = 2,
        match_format: str = 'round_robin',
        tiebreaker_rules: Optional[List[str]] = None,
    ) -> List[Group]:
        """
        Configure group stage for a tournament.
        
        Args:
            tournament_id: Tournament ID
            num_groups: Number of groups (2, 4, 8, 16)
            points_system: Points awarded {win: 3, draw: 1, loss: 0}
            advancement_count: How many from each group advance
            match_format: 'round_robin' or 'double_round_robin'
            tiebreaker_rules: List of tiebreaker criteria
        
        Returns:
            List of created Group objects
        
        Raises:
            ValidationError: If configuration is invalid
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Validate tournament format
        if tournament.format not in ['group-stage', 'group-playoff', 'group_stage', 'group_playoff']:
            raise ValidationError("Tournament must be group stage format")
        
        # Validate num_groups
        if num_groups not in [2, 4, 8, 16]:
            raise ValidationError("Number of groups must be 2, 4, 8, or 16")
        
        # Get confirmed registrations count
        total_participants = tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        ).count()
        
        if total_participants < num_groups * 2:
            raise ValidationError(f"Need at least {num_groups * 2} participants for {num_groups} groups")
        
        # Calculate participants per group
        participants_per_group = total_participants // num_groups
        remainder = total_participants % num_groups
        
        # Default points system
        if points_system is None:
            points_system = {'win': 3, 'draw': 1, 'loss': 0}
        
        # Default tiebreaker rules (game-specific logic will be applied later)
        if tiebreaker_rules is None:
            tiebreaker_rules = [
                'head_to_head',
                'goal_difference',  # or round_difference, placement_points depending on game
                'goals_for',  # or kills, score depending on game
                'random'
            ]
        
        # Delete existing groups and their standings
        _now = timezone.now()
        GroupStanding.objects.filter(
            group__tournament=tournament, is_deleted=False
        ).update(is_deleted=True, deleted_at=_now)
        Group.objects.filter(tournament=tournament).update(is_deleted=True, deleted_at=_now)
        
        # Create groups
        groups = []
        group_names = ['Group A', 'Group B', 'Group C', 'Group D', 
                       'Group E', 'Group F', 'Group G', 'Group H',
                       'Group I', 'Group J', 'Group K', 'Group L',
                       'Group M', 'Group N', 'Group O', 'Group P']
        
        for i in range(num_groups):
            # Distribute remainder (some groups get 1 extra participant)
            max_participants = participants_per_group + (1 if i < remainder else 0)
            
            group = Group.objects.create(
                tournament=tournament,
                name=group_names[i],
                display_order=i,
                max_participants=max_participants,
                advancement_count=advancement_count,
                config={
                    'points_system': points_system,
                    'match_format': match_format,
                    'tiebreaker_rules': tiebreaker_rules,
                },
                is_finalized=False
            )
            groups.append(group)
        
        return groups
    
    @staticmethod
    @transaction.atomic
    def draw_groups(
        tournament_id: int,
        draw_method: str = 'random',
        seeding_data: Optional[Dict] = None,
        manual_assignments: Optional[Dict[int, int]] = None,
    ) -> Tuple[List[GroupStanding], str]:
        """
        Assign participants to groups.
        
        Args:
            tournament_id: Tournament ID
            draw_method: 'random', 'seeded', or 'manual'
            seeding_data: For seeded draws {registration_id: seed_number}
            manual_assignments: For manual draws {registration_id: group_id}
        
        Returns:
            Tuple of (created standings, draw_seed_hash)
        
        Raises:
            ValidationError: If draw fails validation
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        groups = list(Group.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('display_order'))
        
        if not groups:
            raise ValidationError("No groups configured for this tournament")
        
        # Get confirmed registrations
        registrations = list(tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        ).order_by('created_at'))
        
        if not registrations:
            raise ValidationError("No confirmed registrations to assign")
        
        # Generate draw seed for provability
        draw_seed = f"{tournament.id}_{timezone.now().isoformat()}_{random.randint(1000, 9999)}"
        draw_seed_hash = hashlib.sha256(draw_seed.encode()).hexdigest()
        
        # Perform draw based on method
        if draw_method == 'manual' and manual_assignments:
            assignments = GroupStageService._manual_draw(
                registrations, groups, manual_assignments
            )
        elif draw_method == 'seeded' and seeding_data:
            assignments = GroupStageService._seeded_draw(
                registrations, groups, seeding_data, draw_seed
            )
        else:  # random (default)
            assignments = GroupStageService._random_draw(
                registrations, groups, draw_seed
            )
        
        # Clean up any existing (stale) standings from prior draws
        GroupStanding.objects.filter(
            group__in=groups, is_deleted=False
        ).update(is_deleted=True)

        # Create GroupStanding entries
        standings = []
        for registration, group in assignments:
            standing = GroupStanding.objects.create(
                group=group,
                user=registration.user if tournament.participation_type == 'solo' else None,
                team_id=registration.team_id if tournament.participation_type == 'team' else None,
                rank=0,  # Will be calculated after matches
                matches_played=0,
                matches_won=0,
                matches_drawn=0,
                matches_lost=0,
                points=Decimal('0.00'),
            )
            standings.append(standing)
        
        # Mark groups as finalized
        for group in groups:
            group.draw_seed = draw_seed_hash
            group.is_finalized = True
            group.save()
        
        return standings, draw_seed_hash
    
    @staticmethod
    def _random_draw(
        registrations: List[Registration],
        groups: List[Group],
        seed: str
    ) -> List[Tuple[Registration, Group]]:
        """Perform random draw."""
        # Use seed for reproducibility
        random.seed(seed)
        
        # Shuffle registrations
        shuffled = registrations.copy()
        random.shuffle(shuffled)
        
        # Assign to groups round-robin style
        assignments = []
        group_counts = [0] * len(groups)
        
        for reg in shuffled:
            # Find group with fewest participants (within capacity)
            for i, group in enumerate(groups):
                if group_counts[i] < group.max_participants:
                    assignments.append((reg, group))
                    group_counts[i] += 1
                    break
        
        return assignments
    
    @staticmethod
    def _seeded_draw(
        registrations: List[Registration],
        groups: List[Group],
        seeding_data: Dict[int, int],
        seed: str
    ) -> List[Tuple[Registration, Group]]:
        """Perform seeded draw (distributes high seeds evenly)."""
        # Sort registrations by seed
        sorted_regs = sorted(
            registrations,
            key=lambda r: seeding_data.get(r.id, 999999)
        )
        
        # Snake draft assignment (1,2,3,4 then 4,3,2,1)
        assignments = []
        group_counts = [0] * len(groups)
        forward = True
        
        for reg in sorted_regs:
            if forward:
                group_indexes = range(len(groups))
            else:
                group_indexes = range(len(groups) - 1, -1, -1)
            
            for i in group_indexes:
                if group_counts[i] < groups[i].max_participants:
                    assignments.append((reg, groups[i]))
                    group_counts[i] += 1
                    
                    # Check if round complete (toggle direction)
                    if sum(group_counts) % len(groups) == 0:
                        forward = not forward
                    break
        
        return assignments
    
    @staticmethod
    def _manual_draw(
        registrations: List[Registration],
        groups: List[Group],
        manual_assignments: Dict[int, int]
    ) -> List[Tuple[Registration, Group]]:
        """Perform manual draw (organizer assigns)."""
        group_dict = {g.id: g for g in groups}
        group_counts = {g.id: 0 for g in groups}
        
        assignments = []
        for reg in registrations:
            group_id = manual_assignments.get(reg.id)
            if not group_id or group_id not in group_dict:
                raise ValidationError(f"Invalid group assignment for registration {reg.id}")
            
            group = group_dict[group_id]
            
            # Check capacity
            if group_counts[group_id] >= group.max_participants:
                raise ValidationError(f"Group {group.name} is full")
            
            assignments.append((reg, group))
            group_counts[group_id] += 1
        
        return assignments
    
    @staticmethod
    @transaction.atomic
    def calculate_standings(
        group_id: int,
        game_slug: str
    ) -> List[GroupStanding]:
        """
        Calculate current standings for a group.

        .. deprecated::
            Prefer ``calculate_group_standings(stage_id)`` (Epic 3.2) which uses
            the correct ``state`` field, filters matches by ``lobby_info__group_id``,
            and is driven by GameRulesEngine.  This method is retained for
            backwards-compat with any callers that predate Epic 3.2.

        Aggregates match results and applies game-specific scoring.
        Handles tiebreakers and determines advancement.

        Args:
            group_id: Group ID
            game_slug: Game slug for game-specific logic

        Returns:
            List of GroupStanding objects (ordered by rank)
        """
        group = Group.objects.get(id=group_id)
        standings = list(GroupStanding.objects.filter(
            group=group,
            is_deleted=False
        ))
        
        # Get all completed matches for this group.
        # NOTE: Match uses `state` (not `status`) and stores participant IDs as
        # plain integers in `participant1_id` / `participant2_id`.
        # Group matches are identified by lobby_info__group_id (set during generation).
        # DEPRECATED: prefer calculate_group_standings(stage_id) for Epic 3.2+ paths.
        user_ids = [s.user_id for s in standings if s.user_id]
        team_ids = [s.team_id for s in standings if s.team_id]
        matches = Match.objects.filter(
            tournament=group.tournament,
            state=Match.COMPLETED,
            is_deleted=False,
        ).filter(
            Q(participant1_id__in=user_ids + team_ids) |
            Q(participant2_id__in=user_ids + team_ids)
        )
        
        # Reset all standings
        for standing in standings:
            standing.matches_played = 0
            standing.matches_won = 0
            standing.matches_drawn = 0
            standing.matches_lost = 0
            standing.points = Decimal('0.00')
            standing.goals_for = 0
            standing.goals_against = 0
            standing.goal_difference = 0
            standing.rounds_won = 0
            standing.rounds_lost = 0
            standing.round_difference = 0
            standing.total_kills = 0
            standing.total_deaths = 0
            standing.total_assists = 0
            standing.placement_points = Decimal('0.00')
            standing.total_score = 0
        
        # Aggregate match results — pre-fetch game config once
        from apps.games.services import game_service
        _cached_tournament_config = None
        if matches:
            first_match = matches[0]
            _cached_tournament_config = game_service.get_tournament_config(first_match.tournament.game)
        
        for match in matches:
            GroupStageService._update_standing_from_match(
                standings, match, game_slug, group, _cached_tournament_config
            )
        
        # Apply tiebreakers and assign ranks
        GroupStageService._apply_tiebreakers(standings, game_slug, group)
        
        # Bulk update
        GroupStanding.objects.bulk_update(
            standings,
            fields=[
                'rank', 'matches_played', 'matches_won', 'matches_drawn', 'matches_lost',
                'points', 'goals_for', 'goals_against', 'goal_difference',
                'rounds_won', 'rounds_lost', 'round_difference',
                'total_kills', 'total_deaths', 'total_assists', 'kda_ratio',
                'placement_points', 'average_placement', 'total_score',
                'is_advancing', 'is_eliminated'
            ]
        )
        
        return standings
    
    @staticmethod
    def _update_standing_from_match(
        standings: List[GroupStanding],
        match: Match,
        game_slug: str,
        group: Group,
        tournament_config=None
    ):
        """Update standings based on match result."""
        # Match.participant1_id / participant2_id are plain integers that can be
        # either a user PK or a team PK depending on the tournament type.
        # Match.winner_id is likewise a plain integer (or None for draw).
        def _pid(standing: GroupStanding) -> int | None:
            return standing.user_id if standing.user_id else standing.team_id

        standing1 = next((s for s in standings if _pid(s) == match.participant1_id), None)
        standing2 = next((s for s in standings if _pid(s) == match.participant2_id), None)
        
        if not standing1 or not standing2:
            return  # Match not in this group
        
        # Update matches played
        standing1.matches_played += 1
        standing2.matches_played += 1
        
        # Determine winner and update points
        # Match.winner_id is a plain integer (participant1_id, participant2_id, or None=draw).
        if match.winner_id == match.participant1_id:
            standing1.matches_won += 1
            standing2.matches_lost += 1
            standing1.points += Decimal(str(group.points_for_win))
            standing2.points += Decimal(str(group.points_for_loss))
        elif match.winner_id == match.participant2_id:
            standing2.matches_won += 1
            standing1.matches_lost += 1
            standing2.points += Decimal(str(group.points_for_win))
            standing1.points += Decimal(str(group.points_for_loss))
        else:  # Draw
            standing1.matches_drawn += 1
            standing2.matches_drawn += 1
            standing1.points += Decimal(str(group.points_for_draw))
            standing2.points += Decimal(str(group.points_for_draw))
        
        # Game-specific stat updates using config-driven approach.
        # Legacy callers may pass Match instances without a result_data payload;
        # use score fields as a stable fallback source of truth.
        match_data = dict(getattr(match, 'result_data', {}) or {})
        match_data.setdefault('participant1_score', match.participant1_score or 0)
        match_data.setdefault('participant2_score', match.participant2_score or 0)
        
        # Use pre-fetched game tournament config (passed from caller to avoid N+1)
        scoring_type = tournament_config.default_scoring_type if tournament_config else 'WIN_LOSS'
        
        # Delegate game-specific stat updates to the ScoringEvaluator
        from apps.games.services.scoring_evaluator import scoring_evaluator
        game_category = getattr(match.tournament.game, 'category', None) if match.tournament and match.tournament.game else None
        scoring_evaluator.update_standings(standing1, standing2, match_data, scoring_type, game_category)
    
    @staticmethod
    def _apply_tiebreakers(
        standings: List[GroupStanding],
        game_slug: str,
        group: Group
    ):
        """
        Apply tiebreaker rules and assign ranks.
        Uses GameTournamentConfig.default_tiebreakers instead of hardcoded logic.
        """
        from apps.games.services import game_service
        
        # Get game and its tournament config
        game = game_service.get_game(game_slug)
        if not game:
            # Fallback: sort by points only
            standings.sort(key=lambda s: -s.points)
            for i, standing in enumerate(standings, start=1):
                standing.rank = i
                standing.save(update_fields=['rank'])
            return
        
        tournament_config = game_service.get_tournament_config(game)
        tiebreakers = tournament_config.default_tiebreakers if tournament_config else []
        
        # Build dynamic sort key based on tiebreakers
        def build_sort_key(standing):
            """Build tuple for sorting based on configured tiebreakers."""
            key_parts = [-standing.points]  # Always sort by points first
            
            for tiebreaker in tiebreakers:
                if tiebreaker == 'goal_difference':
                    key_parts.append(-standing.goal_difference)
                elif tiebreaker == 'goals_for':
                    key_parts.append(-standing.goals_for)
                elif tiebreaker == 'matches_won':
                    key_parts.append(-standing.matches_won)
                elif tiebreaker == 'round_difference':
                    key_parts.append(-standing.round_difference)
                elif tiebreaker == 'rounds_won':
                    key_parts.append(-standing.rounds_won)
                elif tiebreaker == 'placement_points':
                    key_parts.append(-standing.placement_points)
                elif tiebreaker == 'total_kills':
                    key_parts.append(-standing.total_kills)
                elif tiebreaker == 'kda_ratio':
                    key_parts.append(-standing.kda_ratio)
                elif tiebreaker == 'total_score':
                    key_parts.append(-standing.total_score)
            
            return tuple(key_parts)
        
        standings.sort(key=build_sort_key)
        
        # Assign ranks
        for rank, standing in enumerate(standings, start=1):
            standing.update_rank(rank)
    
    @staticmethod
    def get_advancers(tournament_id: int) -> Dict[str, List[GroupStanding]]:
        """
        Get top N advancers from each group for a GROUP_PLAYOFF tournament.
        
        N is taken from group.advancement_count (e.g., top 2 from each group).
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            Dict mapping group.name -> list of GroupStanding objects
            Ordered by final position within the group.
        
        Raises:
            ValidationError: If tournament has no groups or invalid format
        
        Example:
            >>> advancers = GroupStageService.get_advancers(tournament_id=123)
            >>> for group_name, standings in advancers.items():
            ...     print(f"{group_name}: {[s.team.name for s in standings]}")
            Group A: ['Team Alpha', 'Team Beta']
            Group B: ['Team Gamma', 'Team Delta']
        """
        from apps.tournaments.models import Tournament
        
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Validate format
        if tournament.format != Tournament.GROUP_PLAYOFF:
            raise ValidationError(
                f"Tournament must be GROUP_PLAYOFF format, got {tournament.format}"
            )
        
        # Get all groups for this tournament
        groups = Group.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('display_order')
        
        if not groups.exists():
            raise ValidationError(f"Tournament {tournament.name} has no groups configured")
        
        advancers_by_group = {}
        
        for group in groups:
            # Get standings ordered by rank (position field)
            standings = GroupStanding.objects.filter(
                group=group,
                is_deleted=False
            ).order_by('rank').select_related('user')
            
            # Get top N based on advancement_count
            advancement_count = group.advancement_count
            top_standings = list(standings[:advancement_count])
            
            if len(top_standings) < advancement_count:
                raise ValidationError(
                    f"Group {group.name} has only {len(top_standings)} participants, "
                    f"but needs {advancement_count} to advance"
                )
            
            advancers_by_group[group.name] = top_standings
        
        return advancers_by_group
    
    # ========================================================================
    # Epic 3.2: Group Stage Model Methods (New GroupStage model)
    # ========================================================================
    
    @staticmethod
    @transaction.atomic
    def create_groups(
        tournament_id: int,
        num_groups: int,
        group_size: int,
        advancement_count_per_group: int = 2,
        config: Optional[Dict] = None
    ):
        """
        Create a GroupStage with N groups (Epic 3.2).
        
        Creates GroupStage model instance and associated Group instances.
        
        Args:
            tournament_id: Tournament ID
            num_groups: Number of groups to create
            group_size: Participants per group
            advancement_count_per_group: Teams advancing per group
            config: Optional configuration (points_system, tiebreakers, etc.)
        
        Returns:
            Created GroupStage instance
        """
        from apps.tournaments.models import GroupStage
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        if num_groups < 1:
            raise ValidationError("Number of groups must be at least 1")
        if group_size < 2:
            raise ValidationError("Group size must be at least 2")
        # Allow advancement_count == group_size for ADVANCEMENT_ALL scenarios
        if advancement_count_per_group > group_size:
            raise ValidationError("Advancement count must be less than group size")
        
        # Default configuration
        default_config = {
            "points_system": {"win": 3, "draw": 1, "loss": 0},
            "tiebreaker_rules": ["points", "wins", "head_to_head", "goal_difference", "goals_for"],
            "seeding_method": "snake",
        }
        if config:
            default_config.update(config)
        
        # Create GroupStage
        group_stage = GroupStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            num_groups=num_groups,
            group_size=group_size,
            format="round_robin",
            advancement_count_per_group=advancement_count_per_group,
            config=default_config,
        )
        
        # Create groups with alphabetic names (A, B, C, ...)
        for i in range(num_groups):
            group_letter = chr(65 + i)  # 65 = 'A' in ASCII
            Group.objects.create(
                tournament=tournament,
                name=f"Group {group_letter}",
                display_order=i,
                max_participants=group_size,
                advancement_count=advancement_count_per_group,
                config=default_config,
            )
        
        return group_stage
    
    @staticmethod
    @transaction.atomic
    def assign_participant(
        stage_id: int,
        participant_id: int,
        group_id: Optional[int] = None,
        is_team: bool = True
    ):
        """
        Assign a participant to a group (Epic 3.2).
        
        Args:
            stage_id: GroupStage ID
            participant_id: Team or User ID
            group_id: Optional group to assign to (auto-assigns if None)
            is_team: Whether participant is a team (True) or individual user (False)
        
        Returns:
            Created GroupStanding instance
        """
        from apps.tournaments.models import GroupStage
        
        stage = GroupStage.objects.select_related('tournament').get(id=stage_id)
        
        # Check if participant already assigned
        existing = GroupStanding.objects.filter(
            group__tournament=stage.tournament,
            **({"team_id": participant_id} if is_team else {"user_id": participant_id})
        ).first()
        
        if existing:
            raise ValidationError(
                f"Participant {participant_id} already assigned to {existing.group.name}"
            )
        
        # Find target group
        if group_id:
            target_group = Group.objects.get(id=group_id, tournament=stage.tournament)
        else:
            # Auto-assign to first group with capacity
            groups = Group.objects.filter(tournament=stage.tournament).order_by('display_order')
            target_group = None
            for group in groups:
                if not group.is_full:
                    target_group = group
                    break
            
            if not target_group:
                raise ValidationError("All groups are full")
        
        # Check capacity
        if target_group.is_full:
            raise ValidationError(f"{target_group.name} is already full")
        
        # Create standing
        standing = GroupStanding.objects.create(
            group=target_group,
            team_id=participant_id if is_team else None,
            user_id=None if is_team else participant_id,
            rank=0,
        )
        
        return standing
    
    @staticmethod
    @transaction.atomic
    def auto_balance_groups(
        stage_id: int,
        participant_ids: List[int],
        is_team: bool = True
    ) -> Dict[int, List[int]]:
        """
        Distribute participants across groups using snake/serpentine seeding (Epic 3.2).
        
        Algorithm (snake seeding):
        - Participants assumed to be ordered by seed/skill (best first)
        - Example with 8 participants, 2 groups:
          - Round 1: A gets 1, B gets 2
          - Round 2: B gets 3, A gets 4  (reverse)
          - Result: A=[1,4,5,8], B=[2,3,6,7]
        
        Args:
            stage_id: GroupStage ID
            participant_ids: List of participant IDs (ordered by seed, best first)
            is_team: Whether participants are teams (True) or users (False)
        
        Returns:
            Dict mapping group_id to list of participant_ids assigned
        """
        from apps.tournaments.models import GroupStage
        
        stage = GroupStage.objects.select_related('tournament').get(id=stage_id)

        groups = GroupStageService._active_groups_for_stage(stage)
        
        if len(groups) != stage.num_groups:
            raise ValidationError(f"Expected {stage.num_groups} groups, found {len(groups)}")
        
        # Check capacity
        total_capacity = stage.num_groups * stage.group_size
        if len(participant_ids) > total_capacity:
            raise ValidationError(
                f"Too many participants ({len(participant_ids)}) for capacity ({total_capacity})"
            )
        
        # Clear existing standings for this stage
        GroupStanding.objects.filter(group__tournament=stage.tournament).delete()
        
        # Snake seeding distribution
        assignments = {group.id: [] for group in groups}
        for idx, participant_id in enumerate(participant_ids):
            round_number = idx // stage.num_groups
            position_in_round = idx % stage.num_groups
            
            # Reverse direction on odd rounds (snake pattern)
            if round_number % 2 == 1:
                group_idx = stage.num_groups - 1 - position_in_round
            else:
                group_idx = position_in_round
            
            target_group = groups[group_idx]
            assignments[target_group.id].append(participant_id)
            
            # Create standing
            GroupStanding.objects.create(
                group=target_group,
                team_id=participant_id if is_team else None,
                user_id=None if is_team else participant_id,
                rank=0,
            )
        
        return assignments
    
    @staticmethod
    @transaction.atomic
    def generate_group_matches(stage_id: int, rounds: int = 1) -> int:
        """
        Generate round-robin matches for all groups in a stage (Epic 3.2).

        Args:
            stage_id: GroupStage ID
            rounds: Number of round-robin cycles (default 1).
                    Use ``rounds=2`` for double round-robin (home + away).
                    Each additional round re-generates all pairings with
                    participant order swapped to represent the reverse fixture.

        Returns:
            Total number of matches created

        Example:
            # Single round-robin (4 players → 6 matches per group)
            count = GroupStageService.generate_group_matches(stage.id)
            # Double round-robin (4 players → 12 matches per group)
            count = GroupStageService.generate_group_matches(stage.id, rounds=2)
        """
        from apps.tournaments.models import GroupStage

        if rounds < 1:
            raise ValidationError("rounds must be at least 1")

        stage = GroupStage.objects.select_related('tournament').get(id=stage_id)
        groups = GroupStageService._active_groups_for_stage(stage)
        total_matches = 0

        for group in groups:
            participants = list(group.standings.filter(is_deleted=False).select_related('user'))

            if len(participants) < 2:
                continue

            team_name_map = {}
            team_ids = [p.team_id for p in participants if p.team_id]
            if team_ids:
                from apps.organizations.models import Team
                team_name_map = {
                    tid: name for tid, name in Team.objects.filter(
                        id__in=team_ids,
                    ).values_list('id', 'name')
                }

            def _participant_identity(standing):
                if standing.team_id:
                    return standing.team_id, team_name_map.get(standing.team_id, f"Team #{standing.team_id}")
                if standing.user_id:
                    if standing.user:
                        return standing.user_id, (standing.user.get_full_name() or standing.user.username)
                    return standing.user_id, f"User #{standing.user_id}"
                return None, "TBD"

            # Generate all unique pairings (round-robin)
            base_pairings = []
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    base_pairings.append((participants[i], participants[j]))

            match_counter = 0
            for rnd in range(1, rounds + 1):
                for p1, p2 in base_pairings:
                    match_counter += 1
                    # In even rounds, swap home/away to represent the reverse fixture
                    if rnd % 2 == 0:
                        home, away = p2, p1
                    else:
                        home, away = p1, p2

                    home_id, home_name = _participant_identity(home)
                    away_id, away_name = _participant_identity(away)
                    if not home_id or not away_id:
                        continue

                    Match.objects.create(
                        tournament=stage.tournament,
                        participant1_id=home_id,
                        participant1_name=home_name,
                        participant2_id=away_id,
                        participant2_name=away_name,
                        round_number=rnd,
                        match_number=match_counter,
                        state=Match.SCHEDULED,
                        lobby_info={
                            "group_id": group.id,
                            "group_name": group.name,
                            "group_label": group.name,
                            "rr_round": rnd,
                        },
                    )
                    total_matches += 1

        return total_matches
    
    @staticmethod
    def calculate_group_standings(
        stage_id: int,
        group_ids: Optional[List[int]] = None,
        include_scored_data: bool = True,
    ) -> Dict[int, List[Dict]]:
        """
        Calculate standings for all groups in a stage (Epic 3.2).
        
        Integrates with GameRulesEngine for game-specific scoring logic.
        Uses GameService to retrieve scoring configuration for the tournament's game.
        
        Tiebreaker order (from GameTournamentConfig):
        1. Points
        2. Wins
        3. Head-to-head (implemented — comparator-based via functools.cmp_to_key)
        4. Goal/score difference
        5. Goals/score for
        
        Args:
            stage_id: GroupStage ID
        
        Returns:
            Dict mapping group_id to list of standing dicts with rank, points, etc.
        """
        from apps.tournaments.models import GroupStage
        from apps.games.services.rules_engine import GameRulesEngine
        from apps.games.services.game_service import GameService
        
        stage = GroupStage.objects.select_related('tournament', 'tournament__game').get(id=stage_id)
        game_slug = stage.tournament.game.slug
        
        default_points_system = {'win': 3, 'draw': 1, 'loss': 0}
        points_system = (stage.tournament.config or {}).get('points_system')

        if not points_system:
            try:
                scoring_rules = GameService.get_scoring_rules(game_slug)
                if scoring_rules:
                    scoring_rule = scoring_rules[0]  # Highest priority
                    points_system = scoring_rule.config.get('points_system')
            except ValueError:
                pass

        if not points_system:
            points_system = stage.config.get('points_system', default_points_system)

        points_system = {**default_points_system, **(points_system or {})}
        
        # Get tiebreaker rules from tournament config if available
        try:
            tournament_config = GameService.get_tournament_config_by_slug(game_slug)
            if tournament_config and getattr(tournament_config, 'default_tiebreakers', None):
                tiebreaker_rules = tournament_config.default_tiebreakers
            else:
                tiebreaker_rules = stage.config.get('tiebreaker_rules', ['points', 'wins', 'goal_difference', 'goals_for'])
        except (ValueError, AttributeError):
            # Game or config not found, use defaults
            tiebreaker_rules = stage.config.get('tiebreaker_rules', ['points', 'wins', 'goal_difference', 'goals_for'])
        
        rules_engine = GameRulesEngine()
        groups_qs = Group.objects.filter(tournament=stage.tournament, is_deleted=False)
        if group_ids:
            groups_qs = groups_qs.filter(id__in=group_ids)

        groups = list(
            groups_qs.prefetch_related(
                Prefetch(
                    'standings',
                    queryset=GroupStanding.objects.filter(is_deleted=False),
                    to_attr='_active_standings',
                )
            )
        )

        selected_group_ids = [group.id for group in groups]
        group_matches: Dict[int, List[Match]] = {group_id: [] for group_id in selected_group_ids}
        if selected_group_ids:
            matches_qs = Match.objects.filter(
                tournament=stage.tournament,
                lobby_info__group_id__in=selected_group_ids,
                state=Match.COMPLETED,
                is_deleted=False,
            ).only(
                'id',
                'lobby_info',
                'participant1_id',
                'participant2_id',
                'participant1_score',
                'participant2_score',
                'winner_id',
                'state',
            )
            for match in matches_qs:
                lobby = match.lobby_info or {}
                raw_group_id = lobby.get('group_id')
                try:
                    match_group_id = int(raw_group_id)
                except (TypeError, ValueError):
                    continue
                if match_group_id in group_matches:
                    group_matches[match_group_id].append(match)
        
        result = {}
        
        for group in groups:
            matches = group_matches.get(group.id, [])
            standings_for_group = list(getattr(group, '_active_standings', []))
            
            # If no matches exist yet, return existing GroupStanding data (for testing/manual entry)
            if not matches:
                existing_standings = []
                for standing in sorted(standings_for_group, key=lambda s: s.rank or 0):
                    participant_id = standing.team_id if standing.team_id else standing.user_id
                    existing_standings.append({
                        "participant_id": participant_id,
                        "rank": standing.rank,
                        "points": standing.points,
                        "wins": standing.matches_won,
                        "draws": standing.matches_drawn,
                        "losses": standing.matches_lost,
                        "goals_for": standing.goals_for,
                        "goals_against": standing.goals_against,
                        "goal_diff": standing.goal_difference,
                        "scored_data": {},
                    })
                result[group.id] = existing_standings
                continue
            
            # Initialize standings data
            standings_data = {}
            standing_objects_by_participant: Dict[int, GroupStanding] = {}
            for standing in standings_for_group:
                participant_id = standing.team_id if standing.team_id else standing.user_id
                if not participant_id:
                    continue
                standing_objects_by_participant[participant_id] = standing
                standings_data[participant_id] = {
                    "participant_id": participant_id,
                    "rank": 0,
                    "matches_played": 0,
                    "points": Decimal('0'),
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_diff": 0,
                    "scored_data": {},  # Game-specific scoring data
                }
            
            # Process match results using GameRulesEngine
            for match in matches:
                p1_id = match.participant1_id
                p2_id = match.participant2_id
                
                if p1_id not in standings_data or p2_id not in standings_data:
                    continue
                
                # Score match using GameRulesEngine
                # Build result_data from Match score fields
                result_data = {
                    "participant1_score": match.participant1_score,
                    "participant2_score": match.participant2_score,
                }
                match_payload = {
                    "participant1_id": p1_id,
                    "participant2_id": p2_id,
                    "result_data": result_data,
                    "winner_id": match.winner_id,
                }
                
                if include_scored_data:
                    try:
                        scoring_result = rules_engine.score_match(game_slug, match_payload)
                        # Store game-specific scoring breakdown
                        standings_data[p1_id]["scored_data"][match.id] = scoring_result.get('participant1', {})
                        standings_data[p2_id]["scored_data"][match.id] = scoring_result.get('participant2', {})
                    except Exception as e:
                        logger.warning(f"GameRulesEngine scoring failed for match {match.id}: {e}, using fallback")
                
                # Determine outcome
                if match.winner_id == p1_id:
                    standings_data[p1_id]["wins"] += 1
                    standings_data[p1_id]["points"] += Decimal(str(points_system['win']))
                    standings_data[p2_id]["losses"] += 1
                    standings_data[p2_id]["points"] += Decimal(str(points_system['loss']))
                elif match.winner_id == p2_id:
                    standings_data[p2_id]["wins"] += 1
                    standings_data[p2_id]["points"] += Decimal(str(points_system['win']))
                    standings_data[p1_id]["losses"] += 1
                    standings_data[p1_id]["points"] += Decimal(str(points_system['loss']))
                elif match.winner_id is None and match.state == Match.COMPLETED:
                    standings_data[p1_id]["draws"] += 1
                    standings_data[p1_id]["points"] += Decimal(str(points_system['draw']))
                    standings_data[p2_id]["draws"] += 1
                    standings_data[p2_id]["points"] += Decimal(str(points_system['draw']))
                
                # Goal/score tracking from Match fields
                p1_score = match.participant1_score or 0
                p2_score = match.participant2_score or 0
                standings_data[p1_id]["goals_for"] += p1_score
                standings_data[p1_id]["goals_against"] += p2_score
                standings_data[p2_id]["goals_for"] += p2_score
                standings_data[p2_id]["goals_against"] += p1_score
            
            # Calculate goal difference
            for data in standings_data.values():
                data["goal_diff"] = data["goals_for"] - data["goals_against"]
            
            # Build head-to-head results map (Epic 3.5)
            # h2h_results[(p1_id, p2_id)] = 1 if p1 won, -1 if p2 won, 0 if draw / no result
            h2h_results: Dict = {}
            for match in matches:
                p1_id = match.participant1_id
                p2_id = match.participant2_id
                if match.winner_id == p1_id:
                    h2h_results[(p1_id, p2_id)] = 1
                    h2h_results[(p2_id, p1_id)] = -1
                elif match.winner_id == p2_id:
                    h2h_results[(p1_id, p2_id)] = -1
                    h2h_results[(p2_id, p1_id)] = 1
                else:
                    h2h_results.setdefault((p1_id, p2_id), 0)
                    h2h_results.setdefault((p2_id, p1_id), 0)
            
            # Sort by tiebreakers using comparator (supports head-to-head, from config)
            def _cmp_standings(a, b):
                for rule in tiebreaker_rules:
                    if rule in ('head_to_head', 'h2h'):
                        # Positive = a is ranked higher (better)
                        h2h = h2h_results.get((a["participant_id"], b["participant_id"]))
                        if h2h is not None and h2h != 0:
                            return -h2h  # -1 means a beat b → a ranks first
                    else:
                        a_val = _tiebreaker_val(a, rule)
                        b_val = _tiebreaker_val(b, rule)
                        if a_val > b_val:
                            return -1  # a ranks higher
                        if a_val < b_val:
                            return 1   # b ranks higher
                return 0
            
            def _tiebreaker_val(data, rule):
                """Return numeric value for a tiebreaker rule (higher = better)."""
                if rule == 'points':
                    return data["points"]
                if rule == 'wins':
                    return data["wins"]
                if rule in ('goal_difference', 'score_difference'):
                    return data["goal_diff"]
                if rule in ('goals_for', 'score_for'):
                    return data["goals_for"]
                return 0
            
            sorted_standings = sorted(
                standings_data.values(),
                key=functools.cmp_to_key(_cmp_standings),
            )
            
            # Assign ranks and update database
            standings_to_update: List[GroupStanding] = []
            for rank, data in enumerate(sorted_standings, start=1):
                data["rank"] = rank
                data["matches_played"] = data["wins"] + data["draws"] + data["losses"]
                standing_obj = standing_objects_by_participant.get(data["participant_id"])
                if not standing_obj:
                    continue
                standing_obj.rank = rank
                standing_obj.matches_played = data["matches_played"]
                standing_obj.points = data["points"]
                standing_obj.matches_won = data["wins"]
                standing_obj.matches_drawn = data["draws"]
                standing_obj.matches_lost = data["losses"]
                standing_obj.goals_for = data["goals_for"]
                standing_obj.goals_against = data["goals_against"]
                standing_obj.goal_difference = data["goal_diff"]
                standings_to_update.append(standing_obj)

            if standings_to_update:
                GroupStanding.objects.bulk_update(
                    standings_to_update,
                    fields=[
                        'rank',
                        'matches_played',
                        'points',
                        'matches_won',
                        'matches_drawn',
                        'matches_lost',
                        'goals_for',
                        'goals_against',
                        'goal_difference',
                    ],
                )
            
            result[group.id] = sorted_standings
        
        logger.info(
            "Calculated standings for %s groups in stage %s using GameRulesEngine%s",
            len(result),
            stage_id,
            "" if include_scored_data else " (scored_data skipped)",
        )
        return result
    
    @staticmethod
    def export_standings(stage_id: int) -> dict:
        """
        Export group standings in structured JSON format for frontend/API consumption (Epic 3.2).
        
        Returns frontend-friendly JSON structure with groups and standings.
        
        Args:
            stage_id: GroupStage ID
        
        Returns:
            dict: {
                "groups": [
                    {
                        "group_id": int,
                        "name": str,
                        "standings": [
                            {
                                "participant_id": int,
                                "rank": int,
                                "points": float,
                                "wins": int,
                                "draws": int,
                                "losses": int,
                                "goals_for": int,
                                "goals_against": int,
                                "goal_diff": int,
                                "tiebreaker": dict
                            }
                        ]
                    }
                ]
            }
        
        Example:
            >>> json_data = GroupStageService.export_standings(stage_id=1)
            >>> json_data["groups"][0]["standings"][0]
            {'participant_id': 5, 'rank': 1, 'points': 9.0, ...}
        """
        from apps.tournaments.models import GroupStage
        
        stage = GroupStage.objects.select_related('tournament').get(id=stage_id)
        standings_by_group = GroupStageService.calculate_group_standings(stage_id)
        groups = Group.objects.filter(tournament=stage.tournament).order_by('display_order')
        
        result = {"groups": []}
        
        for group in groups:
            group_standings = standings_by_group.get(group.id, [])
            
            standings_list = []
            for standing in group_standings:
                standings_list.append({
                    "participant_id": standing["participant_id"],
                    "rank": standing["rank"],
                    "points": float(standing["points"]),  # Convert Decimal for JSON
                    "wins": standing["wins"],
                    "draws": standing["draws"],
                    "losses": standing["losses"],
                    "goals_for": standing["goals_for"],
                    "goals_against": standing["goals_against"],
                    "goal_diff": standing["goal_diff"],
                    "tiebreaker": {
                        "points": float(standing["points"]),
                        "wins": standing["wins"],
                        "goal_diff": standing["goal_diff"],
                        "goals_for": standing["goals_for"],
                    }
                })
            
            result["groups"].append({
                "group_id": group.id,
                "name": group.name,
                "standings": standings_list
            })
        
        logger.info(f"Exported standings for {len(result['groups'])} groups in stage {stage_id}")
        return result
