"""
Stage Transition Service

Epic 3.4: Stage Transitions System

Provides business logic for advancing tournaments through multiple stages:
- calculate_advancement: Determine which participants advance based on group standings
- generate_next_stage: Create next stage (bracket or groups) using universal bracket engine

Architecture:
- Lives in tournaments app (ORM access allowed)
- Uses GroupStageService for group standings calculations
- Bridges to tournament_ops.BracketEngineService via DTOs for bracket generation
- No TournamentOps imports in models, only in this service layer

Stage Transition Flow:
1. Group Stage completes → calculate which teams advance
2. generate_next_stage creates next stage (single-elim, double-elim, or another group stage)
3. If bracket stage: converts participants to TeamDTOs, calls BracketEngineService
4. If group stage: creates new GroupStage via GroupStageService
5. Updates state: current stage → completed, next stage → active
"""

import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import (
    Tournament,
    TournamentStage,
    GroupStage,
    Group,
    GroupStanding,
    Match,
    Registration,
)
from apps.tournaments.services.group_stage_service import GroupStageService

logger = logging.getLogger(__name__)


class StageTransitionService:
    """
    Service for managing transitions between tournament stages.
    
    Epic 3.4: Stage Transitions System
    """
    
    @staticmethod
    def calculate_advancement(stage_id: int) -> Dict[str, List[int]]:
        """
        Calculate which participants advance from a stage.
        
        Supports:
        - Group stages (round_robin with GroupStage)
        - Swiss system tournaments
        - Single/Double elimination (TODO: Epic 3.5+)
        
        For group stages:
        - Uses GroupStageService.calculate_group_standings()
        - Extracts top N per group or top N overall based on advancement_criteria
        
        For Swiss stages:
        - Sorts by points → tiebreakers from GameRulesEngine
        - Takes top N overall
        
        Args:
            stage_id: TournamentStage ID
        
        Returns:
            Dict with keys:
            - "advanced": List of participant IDs (ordered by seed/rank)
            - "eliminated": List of participant IDs
        
        Raises:
            ValidationError: If stage not found or invalid configuration
        """
        from apps.games.services.game_service import GameService
        
        try:
            stage = TournamentStage.objects.select_related('tournament', 'group_stage', 'tournament__game').get(id=stage_id)
        except TournamentStage.DoesNotExist:
            raise ValidationError(f"TournamentStage with ID {stage_id} not found")
        
        if stage.state != TournamentStage.STATE_COMPLETED:
            raise ValidationError(f"Stage '{stage.name}' is not completed yet")
        
        advanced = []
        eliminated = []
        
        # Get advancement rules from GameTournamentConfig if available
        game_slug = stage.tournament.game.slug
        try:
            tournament_config = GameService.get_tournament_config_by_slug(game_slug)
        except (ValueError, AttributeError):
            # Game not found in games app or no config - use default rules
            tournament_config = None
        
        if tournament_config and tournament_config.config.get('group_advancement_rules'):
            advancement_rules = tournament_config.config['group_advancement_rules']
            logger.info(f"Using advancement rules from GameTournamentConfig for {game_slug}")
        else:
            advancement_rules = None
        
        if stage.is_group_stage and stage.group_stage:
            # Group stage advancement
            group_standings = GroupStageService.calculate_group_standings(stage.group_stage.id)
            
            # Apply advancement rules from config if available
            if advancement_rules:
                criteria = advancement_rules.get('criteria', stage.advancement_criteria)
            else:
                criteria = stage.advancement_criteria
            
            if criteria == TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP:
                # Take top N from each group, preserving group winner priority
                advancement_count = stage.group_stage.advancement_count_per_group
                by_rank_position = {}  # {rank: [participant_ids]}
                
                for group_id, standings in group_standings.items():
                    for standing in standings:
                        rank = standing["rank"]
                        if rank <= advancement_count:
                            if rank not in by_rank_position:
                                by_rank_position[rank] = []
                            by_rank_position[rank].append(standing["participant_id"])
                        else:
                            eliminated.append(standing["participant_id"])
                
                # Build advanced list: group winners first, then runners-up, etc.
                for rank in sorted(by_rank_position.keys()):
                    advanced.extend(by_rank_position[rank])
            
            elif criteria == TournamentStage.ADVANCEMENT_TOP_N:
                # Take top N overall across all groups
                all_standings = []
                for group_id, standings in group_standings.items():
                    all_standings.extend(standings)
                
                # Sort globally by points, wins, goal_diff
                all_standings.sort(
                    key=lambda x: (
                        -x["points"],
                        -x["wins"],
                        -x["goal_diff"],
                        -x["goals_for"],
                    )
                )
                
                # Use stage.advancement_count for overall top N
                advancement_count_total = stage.advancement_count if stage.advancement_count else len(all_standings)
                advanced = [s["participant_id"] for s in all_standings[:advancement_count_total]]
                eliminated = [s["participant_id"] for s in all_standings[advancement_count_total:]]
            
            elif criteria == TournamentStage.ADVANCEMENT_ALL:
                # All participants advance
                for group_id, standings in group_standings.items():
                    advanced.extend([s["participant_id"] for s in standings])
            
            else:
                raise ValidationError(f"Unknown advancement criteria: {criteria}")
        
        elif stage.format == TournamentStage.FORMAT_SWISS:
            # Swiss system advancement
            from apps.games.services.rules_engine import GameRulesEngine
            
            # Get all completed matches for this stage
            matches = Match.objects.filter(
                tournament=stage.tournament,
                lobby_info__stage_id=stage.id,
                state=Match.COMPLETED
            )
            
            # Calculate Swiss standings
            participant_scores = {}
            for match in matches:
                p1_id = match.participant1_id
                p2_id = match.participant2_id
                
                if p1_id not in participant_scores:
                    participant_scores[p1_id] = {"points": 0, "wins": 0, "score_for": 0, "score_against": 0}
                if p2_id not in participant_scores:
                    participant_scores[p2_id] = {"points": 0, "wins": 0, "score_for": 0, "score_against": 0}
                
                # Assign points based on winner
                if match.winner_id == p1_id:
                    participant_scores[p1_id]["points"] += 1
                    participant_scores[p1_id]["wins"] += 1
                elif match.winner_id == p2_id:
                    participant_scores[p2_id]["points"] += 1
                    participant_scores[p2_id]["wins"] += 1
                else:
                    # Draw - half point each
                    participant_scores[p1_id]["points"] += 0.5
                    participant_scores[p2_id]["points"] += 0.5
                
                # Track scores using actual Match fields
                p1_score = match.participant1_score or 0
                p2_score = match.participant2_score or 0
                participant_scores[p1_id]["score_for"] += p1_score
                participant_scores[p1_id]["score_against"] += p2_score
                participant_scores[p2_id]["score_for"] += p2_score
                participant_scores[p2_id]["score_against"] += p1_score
            
            # Sort by Swiss standings (points → wins → score_diff)
            sorted_participants = sorted(
                participant_scores.items(),
                key=lambda x: (
                    -x[1]["points"],
                    -x[1]["wins"],
                    -(x[1]["score_for"] - x[1]["score_against"]),
                    -x[1]["score_for"],
                )
            )
            
            advancement_count = stage.advancement_count or len(sorted_participants)
            advanced = [p_id for p_id, _ in sorted_participants[:advancement_count]]
            eliminated = [p_id for p_id, _ in sorted_participants[advancement_count:]]
            
            logger.info(f"Swiss stage advancement: {len(advanced)} advanced, {len(eliminated)} eliminated")
        
        else:
            # TODO (Epic 3.5+): Support other formats (single-elim, double-elim)
            raise NotImplementedError(f"Advancement calculation not yet implemented for format '{stage.format}'")
        
        logger.info(
            f"Calculated advancement for stage {stage_id} ('{stage.name}'): "
            f"{len(advanced)} advanced, {len(eliminated)} eliminated"
        )
        
        return {
            "advanced": advanced,
            "eliminated": eliminated,
        }
    
    @staticmethod
    @transaction.atomic
    def generate_next_stage(current_stage_id: int) -> Optional[TournamentStage]:
        """
        Generate the next tournament stage based on current stage completion.
        
        Workflow:
        1. Find next stage (order + 1)
        2. Get advancing participants from calculate_advancement()
        3. If next stage is bracket (single-elim, double-elim):
           - Convert participants to TeamDTOs
           - Call BracketEngineService.generate_bracket_for_stage()
           - Persist MatchDTOs as Match objects
        4. If next stage is group stage:
           - Call GroupStageService.create_groups() and auto_balance_groups()
        5. Update states: current → completed, next → active
        
        Args:
            current_stage_id: Current TournamentStage ID
        
        Returns:
            Next TournamentStage instance, or None if no next stage
        
        Raises:
            ValidationError: If current stage not completed or next stage misconfigured
        
        Example:
            >>> next_stage = StageTransitionService.generate_next_stage(current_stage_id=1)
            >>> next_stage.format
            'single_elim'
            >>> next_stage.state
            'active'
        
        TODO (Epic 3.4+): Integrate with TournamentAdapter for proper DTO conversion
        TODO (Epic 3.5+): Use BracketEngineService for bracket generation
        """
        try:
            current_stage = TournamentStage.objects.select_related('tournament').get(id=current_stage_id)
        except TournamentStage.DoesNotExist:
            raise ValidationError(f"TournamentStage with ID {current_stage_id} not found")
        
        if current_stage.state != TournamentStage.STATE_COMPLETED:
            raise ValidationError(f"Stage '{current_stage.name}' must be completed before generating next stage")
        
        # Find next stage
        next_stage = current_stage.next_stage
        if not next_stage:
            logger.info(f"No next stage after '{current_stage.name}' (stage {current_stage_id})")
            return None
        
        if next_stage.state != TournamentStage.STATE_PENDING:
            raise ValidationError(f"Next stage '{next_stage.name}' is already {next_stage.state}")
        
        # Get advancing participants
        advancement_result = StageTransitionService.calculate_advancement(current_stage_id)
        advanced_participant_ids = advancement_result["advanced"]
        
        if len(advanced_participant_ids) == 0:
            raise ValidationError(f"No participants advanced from stage '{current_stage.name}'")
        
        logger.info(
            f"Generating next stage '{next_stage.name}' with {len(advanced_participant_ids)} participants"
        )
        
        # Generate stage content based on format
        if next_stage.format == TournamentStage.FORMAT_ROUND_ROBIN:
            # Create group stage
            StageTransitionService._generate_group_stage(
                next_stage,
                advanced_participant_ids,
            )
        
        elif next_stage.format in [TournamentStage.FORMAT_SINGLE_ELIM, TournamentStage.FORMAT_DOUBLE_ELIM]:
            # Create bracket stage
            StageTransitionService._generate_bracket_stage(
                next_stage,
                advanced_participant_ids,
            )
        
        else:
            raise NotImplementedError(f"Stage generation not yet implemented for format '{next_stage.format}'")
        
        # Update states
        next_stage.state = TournamentStage.STATE_ACTIVE
        next_stage.start_date = timezone.now()
        next_stage.save()
        
        logger.info(f"Generated next stage '{next_stage.name}' (ID {next_stage.id}), state set to active")
        
        return next_stage
    
    @staticmethod
    def _generate_group_stage(stage: TournamentStage, participant_ids: List[int]):
        """
        Generate a group stage with participants.
        
        Creates GroupStage model and distributes participants across groups.
        
        Args:
            stage: TournamentStage instance
            participant_ids: List of participant IDs to assign
        """
        # Determine group configuration
        num_participants = len(participant_ids)
        
        # Default: 4 groups for 16+ participants, 2 groups for 8+, 1 group otherwise
        if num_participants >= 16:
            num_groups = 4
        elif num_participants >= 8:
            num_groups = 2
        else:
            num_groups = 1
        
        group_size = (num_participants + num_groups - 1) // num_groups  # Round up
        advancement_count_per_group = max(1, group_size // 2)  # Top half advances
        
        # Create GroupStage
        group_stage_instance = GroupStageService.create_groups(
            tournament_id=stage.tournament.id,
            num_groups=num_groups,
            group_size=group_size,
            advancement_count_per_group=advancement_count_per_group,
            config=stage.config or {},
        )
        
        # Link to TournamentStage
        stage.group_stage = group_stage_instance
        stage.save()
        
        # Distribute participants
        GroupStageService.auto_balance_groups(
            stage_id=group_stage_instance.id,
            participant_ids=participant_ids,
            is_team=True,  # TODO: Detect from Tournament.team_based
        )
        
        # Generate matches
        GroupStageService.generate_group_matches(group_stage_instance.id)
        
        logger.info(
            f"Generated group stage for '{stage.name}': {num_groups} groups, "
            f"{group_size} participants per group"
        )
    
    @staticmethod
    def _generate_bracket_stage(stage: TournamentStage, participant_ids: List[int]):
        """
        Generate a bracket stage (single-elim or double-elim) with participants.
        
        Uses BracketEngineService for bracket generation (Epic 3.4).
        Converts participants → TeamDTO before calling bracket engine.
        
        Args:
            stage: TournamentStage instance
            participant_ids: List of participant IDs to assign
        
        Integration:
        - Calls BracketEngineService.generate_bracket_for_stage()
        - Persists MatchDTO results as Match objects in tournaments app
        - Respects architecture boundaries (DTO-based communication)
        """
        from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
        from apps.tournament_ops.dtos import TeamDTO, TournamentDTO, StageDTO
        
        # Convert tournament to TournamentDTO
        tournament_dto = TournamentDTO(
            id=stage.tournament.id,
            name=stage.tournament.name,
            game_slug=stage.tournament.game.slug,
            stage=stage.name,
            team_size=stage.tournament.team_size if hasattr(stage.tournament, 'team_size') else 1,
            max_teams=stage.tournament.max_participants,
            status=stage.tournament.status,
            start_time=stage.tournament.tournament_start,
            ruleset=stage.config or {},
        )
        
        # Convert stage to StageDTO
        stage_dto = StageDTO(
            id=stage.id,
            name=stage.name,
            type=stage.format,
            order=stage.order,
            config=stage.config or {},
        )
        
        # Convert participants to TeamDTOs
        team_dtos = []
        for idx, participant_id in enumerate(participant_ids):
            team_dtos.append(TeamDTO(
                id=participant_id,
                name=f"Team {participant_id}",  # TODO: Fetch actual team name from teams app
                captain_id=0,  # Placeholder
                captain_name="",
                member_ids=[],
                member_names=[],
                game=stage.tournament.game.slug if hasattr(stage.tournament, 'game') else "",
                is_verified=True,
                logo_url=None
            ))
        
        # Call BracketEngineService
        bracket_engine = BracketEngineService()
        try:
            match_dtos = bracket_engine.generate_bracket_for_stage(
                tournament=tournament_dto,
                stage=stage_dto,
                participants=team_dtos
            )
            
            logger.info(
                f"BracketEngineService generated {len(match_dtos)} matches for stage '{stage.name}' "
                f"(format: {stage.format})"
            )
        except Exception as e:
            logger.error(f"BracketEngineService failed for stage {stage.id}: {e}")
            raise ValidationError(f"Bracket generation failed: {e}")
        
        # Persist MatchDTOs as Match objects
        for idx, match_dto in enumerate(match_dtos, start=1):
            Match.objects.create(
                tournament=stage.tournament,
                participant1_id=match_dto.team_a_id if match_dto.team_a_id else None,
                participant2_id=match_dto.team_b_id if match_dto.team_b_id else None,
                round_number=match_dto.round_number,
                match_number=idx,
                state=Match.SCHEDULED,
                lobby_info={
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "stage": match_dto.stage,
                },
            )
        
        logger.info(
            f"Persisted {len(match_dtos)} bracket matches from BracketEngineService for stage '{stage.name}'"
        )
