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
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F
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
        
        # Delete existing groups if any
        Group.objects.filter(tournament=tournament).update(is_deleted=True)
        
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
        
        # Get all completed matches for this group
        matches = Match.objects.filter(
            tournament=group.tournament,
            status='completed',
            is_deleted=False
        ).filter(
            Q(participant1_user__in=[s.user for s in standings if s.user]) |
            Q(participant1_team__in=[s.team for s in standings if s.team]) |
            Q(participant2_user__in=[s.user for s in standings if s.user]) |
            Q(participant2_team__in=[s.team for s in standings if s.team])
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
        
        # Aggregate match results
        for match in matches:
            GroupStageService._update_standing_from_match(
                standings, match, game_slug, group
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
        group: Group
    ):
        """Update standings based on match result."""
        # Find standings for both participants
        standing1 = next((s for s in standings if 
                         (s.user == match.participant1_user) or 
                         (s.team == match.participant1_team)), None)
        standing2 = next((s for s in standings if 
                         (s.user == match.participant2_user) or 
                         (s.team == match.participant2_team)), None)
        
        if not standing1 or not standing2:
            return  # Match not in this group
        
        # Update matches played
        standing1.matches_played += 1
        standing2.matches_played += 1
        
        # Determine winner and update points
        if match.winner_participant == 1:
            standing1.matches_won += 1
            standing2.matches_lost += 1
            standing1.points += Decimal(str(group.points_for_win))
            standing2.points += Decimal(str(group.points_for_loss))
        elif match.winner_participant == 2:
            standing2.matches_won += 1
            standing1.matches_lost += 1
            standing2.points += Decimal(str(group.points_for_win))
            standing1.points += Decimal(str(group.points_for_loss))
        else:  # Draw
            standing1.matches_drawn += 1
            standing2.matches_drawn += 1
            standing1.points += Decimal(str(group.points_for_draw))
            standing2.points += Decimal(str(group.points_for_draw))
        
        # Game-specific stat updates using config-driven approach
        from apps.games.services import game_service
        match_data = match.result_data or {}
        
        # Get game tournament config for stat field mapping
        tournament_config = game_service.get_tournament_config(match.tournament.game)
        scoring_type = tournament_config.default_scoring_type if tournament_config else 'WIN_LOSS'
        
        # Update stats based on scoring type
        if scoring_type == 'GOALS':
            # Goals-based games (eFootball, FC Mobile, FIFA)
            standing1.goals_for += match_data.get('participant1_score', 0)
            standing1.goals_against += match_data.get('participant2_score', 0)
            standing1.goal_difference = standing1.goals_for - standing1.goals_against
            
            standing2.goals_for += match_data.get('participant2_score', 0)
            standing2.goals_against += match_data.get('participant1_score', 0)
            standing2.goal_difference = standing2.goals_for - standing2.goals_against
        
        elif scoring_type == 'ROUNDS':
            # Rounds-based games (Valorant, CS2, COD Mobile)
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
        
        elif scoring_type in ['PLACEMENT', 'KILLS']:
            # Battle Royale games (PUBG Mobile, Free Fire)
            standing1.total_kills += match_data.get('participant1_kills', 0)
            standing1.placement_points += Decimal(str(match_data.get('participant1_placement_points', 0)))
            
            standing2.total_kills += match_data.get('participant2_kills', 0)
            standing2.placement_points += Decimal(str(match_data.get('participant2_placement_points', 0)))
        
        elif scoring_type == 'WIN_LOSS' and match.tournament.game.category == 'MOBA':
            # MOBA games (Mobile Legends)
            standing1.total_kills += match_data.get('participant1_kills', 0)
            standing1.total_deaths += match_data.get('participant1_deaths', 0)
            standing1.total_assists += match_data.get('participant1_assists', 0)
            standing1.kda_ratio = standing1.calculate_kda()
            
            standing2.total_kills += match_data.get('participant2_kills', 0)
            standing2.total_deaths += match_data.get('participant2_deaths', 0)
            standing2.total_assists += match_data.get('participant2_assists', 0)
            standing2.kda_ratio = standing2.calculate_kda()
            standing1.total_score += match_data.get('participant1_score', 0)
            
            standing2.total_kills += match_data.get('participant2_eliminations', 0)
            standing2.total_deaths += match_data.get('participant2_deaths', 0)
            standing2.total_score += match_data.get('participant2_score', 0)
    
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
            ).order_by('rank').select_related('team', 'user')
            
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
        
        # Get groups for this specific GroupStage (created after the GroupStage itself)
        # NOTE: Groups don't have FK to GroupStage, so we infer by created_at timestamps
        groups = list(Group.objects.filter(
            tournament=stage.tournament,
            created_at__gte=stage.created_at
        ).order_by('display_order'))
        
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
    def generate_group_matches(stage_id: int) -> int:
        """
        Generate round-robin matches for all groups in a stage (Epic 3.2).
        
        Each pair of participants in a group plays exactly once.
        
        Args:
            stage_id: GroupStage ID
        
        Returns:
            Total number of matches created
        
        TODO (Epic 3.5): Integrate with BracketEngineService for round-robin generation.
        """
        from apps.tournaments.models import GroupStage
        
        stage = GroupStage.objects.select_related('tournament').get(id=stage_id)
        # Get groups for this specific GroupStage (created after the GroupStage itself)
        groups = Group.objects.filter(
            tournament=stage.tournament,
            created_at__gte=stage.created_at
        ).prefetch_related('standings')
        total_matches = 0
        
        for group in groups:
            participants = list(group.standings.filter(is_deleted=False))
            
            if len(participants) < 2:
                continue
            
            # Generate all unique pairings (round-robin)
            pairings = []
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    pairings.append((participants[i], participants[j]))
            
            # Create Match instances
            for idx, (p1, p2) in enumerate(pairings, start=1):
                Match.objects.create(
                    tournament=stage.tournament,
                    participant1_id=p1.team_id if p1.team_id else p1.user_id,
                    participant2_id=p2.team_id if p2.team_id else p2.user_id,
                    round_number=1,
                    match_number=idx,
                    state=Match.SCHEDULED,
                    lobby_info={"group_id": group.id, "group_name": group.name},
                )
                total_matches += 1
        
        return total_matches
    
    @staticmethod
    def calculate_group_standings(stage_id: int) -> Dict[int, List[Dict]]:
        """
        Calculate standings for all groups in a stage (Epic 3.2).
        
        Integrates with GameRulesEngine for game-specific scoring logic.
        Uses GameService to retrieve scoring configuration for the tournament's game.
        
        Tiebreaker order (from GameTournamentConfig):
        1. Points
        2. Wins
        3. Head-to-head (TODO: Epic 3.5)
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
        
        # Get scoring rules from GameService
        try:
            scoring_rules = GameService.get_scoring_rules(game_slug)
            if scoring_rules:
                scoring_rule = scoring_rules[0]  # Highest priority
                points_system = scoring_rule.config.get('points_system', {'win': 3, 'draw': 1, 'loss': 0})
            else:
                # Fallback to config or default
                points_system = stage.config.get('points_system', {'win': 3, 'draw': 1, 'loss': 0})
        except ValueError:
            points_system = stage.config.get('points_system', {'win': 3, 'draw': 1, 'loss': 0})
        
        # Get tiebreaker rules from tournament config if available
        try:
            tournament_config = GameService.get_tournament_config_by_slug(game_slug)
            if tournament_config and tournament_config.config.get('tiebreaker_rules'):
                tiebreaker_rules = tournament_config.config['tiebreaker_rules']
            else:
                tiebreaker_rules = stage.config.get('tiebreaker_rules', ['points', 'wins', 'goal_difference', 'goals_for'])
        except ValueError:
            # Game or config not found, use defaults
            tiebreaker_rules = stage.config.get('tiebreaker_rules', ['points', 'wins', 'goal_difference', 'goals_for'])
        
        rules_engine = GameRulesEngine()
        groups = Group.objects.filter(tournament=stage.tournament).prefetch_related('standings')
        
        result = {}
        
        for group in groups:
            # Get all matches for this group
            matches = Match.objects.filter(
                tournament=stage.tournament,
                lobby_info__group_id=group.id,
                state=Match.COMPLETED
            )
            
            # If no matches exist yet, return existing GroupStanding data (for testing/manual entry)
            if not matches.exists():
                existing_standings = []
                for standing in group.standings.filter(is_deleted=False).order_by('rank'):
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
            for standing in group.standings.filter(is_deleted=False):
                participant_id = standing.team_id if standing.team_id else standing.user_id
                standings_data[participant_id] = {
                    "participant_id": participant_id,
                    "rank": 0,
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
                elif match.winner_id is None and match.state == Match.STATE_COMPLETED:
                    standings_data[p1_id]["draws"] += 1
                    standings_data[p1_id]["points"] += Decimal(str(points_system['draw']))
                    standings_data[p2_id]["draws"] += 1
                    standings_data[p2_id]["points"] += Decimal(str(points_system['draw']))
                
                # Goal/score tracking from Match fields
                p1_score = match.participant1_score
                p2_score = match.participant2_score
                standings_data[p1_id]["goals_for"] += p1_score
                standings_data[p1_id]["goals_against"] += p2_score
                standings_data[p2_id]["goals_for"] += p2_score
                standings_data[p2_id]["goals_against"] += p1_score
            
            # Calculate goal difference
            for data in standings_data.values():
                data["goal_diff"] = data["goals_for"] - data["goals_against"]
            
            # Sort by tiebreakers (from config)
            def build_sort_key(standing_data):
                key = []
                for rule in tiebreaker_rules:
                    if rule == 'points':
                        key.append(-standing_data["points"])
                    elif rule == 'wins':
                        key.append(-standing_data["wins"])
                    elif rule == 'goal_difference' or rule == 'score_difference':
                        key.append(-standing_data["goal_diff"])
                    elif rule == 'goals_for' or rule == 'score_for':
                        key.append(-standing_data["goals_for"])
                return tuple(key)
            
            sorted_standings = sorted(standings_data.values(), key=build_sort_key)
            
            # Assign ranks and update database
            for rank, data in enumerate(sorted_standings, start=1):
                data["rank"] = rank
                
                GroupStanding.objects.filter(
                    group=group,
                    **({"team_id": data["participant_id"]} if group.standings.filter(team_id=data["participant_id"]).exists()
                       else {"user_id": data["participant_id"]})
                ).update(
                    rank=rank,
                    points=data["points"],
                    matches_won=data["wins"],
                    matches_drawn=data["draws"],
                    matches_lost=data["losses"],
                    goals_for=data["goals_for"],
                    goals_against=data["goals_against"],
                    goal_difference=data["goal_diff"],
                )
            
            result[group.id] = sorted_standings
        
        logger.info(f"Calculated standings for {len(result)} groups in stage {stage_id} using GameRulesEngine")
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
