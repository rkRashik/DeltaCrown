"""
BracketService - Bracket generation, seeding, and progression logic.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 5.3: BracketService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 7: Bracket Structure Models)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Bracket visualization)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in service layer
- ADR-003: Soft Delete - Brackets can be regenerated if not finalized
- ADR-007: Integration with apps.teams for ranked seeding
- ADR-007: WebSocket integration for real-time bracket updates (Module 2.3 - Phase 2)

Technical Standards:
- PEP 8 compliance with Black formatting (line length: 120)
- Type hints for all public methods
- Google-style docstrings
- Transaction safety with @transaction.atomic

Algorithms Implemented:
- Single Elimination: Standard knockout bracket with byes
- Double Elimination: Winners + Losers brackets with grand finals
- Round Robin: All participants play each other

Assumptions:
- Tournament has confirmed registrations before bracket generation
- Seeding can be slot-order (registration order), random, ranked (from apps.teams), or manual
- BracketNodes form a tree structure with parent/child navigation
- Matches are created from bracket nodes after generation
"""

import logging
import math
import random
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from apps.tournaments.models import (
    Tournament,
    Bracket,
    BracketNode,
    Match,
    Registration
)

# Module 2.3: Real-time WebSocket broadcasting
from apps.tournaments.realtime.utils import broadcast_bracket_updated
from asgiref.sync import async_to_sync  # Module 6.1: Wrap async broadcast helpers

try:
    # Module-scope import keeps backward-compatible patch targets for tests.
    from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
except Exception:  # pragma: no cover - fail-soft for partial app bootstraps
    BracketEngineService = None

logger = logging.getLogger(__name__)


def _publish_bracket_event(event_name: str, **kwargs):
    """Publish bracket lifecycle events via the core EventBus (fire-and-forget)."""
    try:
        from apps.core.events import event_bus
        from apps.core.events.bus import Event
        event_bus.publish(Event(event_type=event_name, data=kwargs, source="bracket_service"))
    except Exception as exc:
        logger.warning("Failed to publish %s event: %s", event_name, exc)


class BracketService:
    """
    Service for bracket generation, seeding, and progression.
    
    Implements algorithms for single elimination, double elimination, and round robin
    bracket generation with support for multiple seeding strategies.
    
    Phase 3, Epic 3.1: Universal Bracket Engine Integration
    - Legacy methods preserved for backwards compatibility and rollback safety
    - New universal engine path via generate_bracket_universal_safe()
    - Feature flag: BRACKETS_USE_UNIVERSAL_ENGINE controls which path is used
    - Reference: CLEANUP_AND_TESTING_PART_6.md §4.5 (Safe Rollback)
    """
    
    # Participant data structure: {"id": str, "name": str, "seed": int}
    
    @staticmethod
    @transaction.atomic
    def generate_bracket_universal_safe(
        tournament_id: int,
        bracket_format: Optional[str] = None,
        seeding_method: Optional[str] = None,
        participants: Optional[List[Dict]] = None
    ) -> Bracket:
        """
        Feature-flagged bracket generation entry point.
        
        Routes to either legacy bracket generation or new universal engine based on
        BRACKETS_USE_UNIVERSAL_ENGINE setting.
        
        Args:
            tournament_id: Tournament ID to generate bracket for
            bracket_format: Bracket format (single-elimination, double-elimination, round-robin).
                           If None, uses tournament.format
            seeding_method: Seeding method (slot-order, random, ranked, manual).
                           If None, uses default slot-order
            participants: List of participant dicts with keys: id, name, seed (optional).
                         If None, fetches from confirmed registrations
        
        Returns:
            Generated Bracket instance
        
        Raises:
            ValidationError: If tournament not found, insufficient participants, or bracket finalized
        
        Feature Flag Behavior:
        - BRACKETS_USE_UNIVERSAL_ENGINE=False (default): Uses legacy generate_bracket()
        - BRACKETS_USE_UNIVERSAL_ENGINE=True: Uses new BracketEngineService
        
        Rollback Safety:
        - Set flag to False to immediately revert to legacy implementation
        - No data migration required - flag controls runtime behavior only
        - Both paths produce compatible Bracket/BracketNode structures
        
        TODO (Epic 3.4): Replace direct service calls with TournamentAdapter once available
        TODO (Epic 3.3): Wire StageTransitionService for match advancement after generation
        
        Example:
            >>> from django.conf import settings
            >>> # Test with universal engine
            >>> with override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=True):
            ...     bracket = BracketService.generate_bracket_universal_safe(
            ...         tournament_id=123,
            ...         bracket_format='single-elimination'
            ...     )
            >>> # Rollback to legacy
            >>> with override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=False):
            ...     bracket = BracketService.generate_bracket_universal_safe(
            ...         tournament_id=123,
            ...         bracket_format='single-elimination'
            ...     )
        """
        from django.conf import settings
        
        use_universal_engine = getattr(settings, 'BRACKETS_USE_UNIVERSAL_ENGINE', False)
        
        logger.info(
            f"Bracket generation for tournament {tournament_id}: "
            f"using {'universal engine' if use_universal_engine else 'legacy implementation'}"
        )
        
        if use_universal_engine:
            # Use new universal bracket engine (Phase 3, Epic 3.1)
            return BracketService._generate_bracket_using_universal_engine(
                tournament_id=tournament_id,
                bracket_format=bracket_format,
                seeding_method=seeding_method,
                participants=participants
            )
        else:
            # Use legacy bracket generation (preserves existing behavior)
            return BracketService.generate_bracket(
                tournament_id=tournament_id,
                bracket_format=bracket_format,
                seeding_method=seeding_method,
                participants=participants
            )
    
    @staticmethod
    @transaction.atomic
    def _generate_bracket_using_universal_engine(
        tournament_id: int,
        bracket_format: Optional[str] = None,
        seeding_method: Optional[str] = None,
        participants: Optional[List[Dict]] = None
    ) -> Bracket:
        """
        Generate bracket using universal BracketEngineService (Phase 3, Epic 3.1).
        
        This method:
        1. Fetches tournament data (remains in tournaments domain)
        2. Converts to DTOs for TournamentOps
        3. Calls BracketEngineService to generate matches
        4. Persists results back to Bracket/BracketNode models
        
        Args:
            tournament_id: Tournament ID
            bracket_format: Bracket format override
            seeding_method: Seeding method
            participants: Participant list override
        
        Returns:
            Generated Bracket instance
        
        Architecture Notes:
        - This method bridges tournaments domain and TournamentOps
        - All ORM usage stays in tournaments app
        - BracketEngineService is DTO-only (no model imports)
        - TODO (Epic 3.4): Replace with TournamentAdapter.generate_bracket() when available
        
        Implementation Status:
        - Basic integration complete for Epic 3.1
        - Match advancement wiring: TODO Epic 3.3 (StageTransitionService)
        - Bracket editing support: TODO Epic 3.4 (BracketEditorService)
        """
        from apps.tournament_ops.dtos.tournament import TournamentDTO
        from apps.tournament_ops.dtos.stage import StageDTO
        from apps.tournament_ops.dtos.team import TeamDTO

        if BracketEngineService is None:
            raise ValidationError("BracketEngineService is unavailable")
        
        # TODO (Epic 3.4): Replace with TournamentAdapter.get_tournament() when available
        # For now, fetch directly (ORM usage acceptable in tournaments domain)
        try:
            tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Determine bracket format
        if bracket_format is None:
            bracket_format = tournament.format or Bracket.SINGLE_ELIMINATION
        
        # Determine seeding method
        if seeding_method is None:
            seeding_method = Bracket.SLOT_ORDER
        
        # Get participants
        if participants is None:
            participants = BracketService._get_confirmed_participants(tournament)
        
        # Apply seeding
        seeded_participants = BracketService.apply_seeding(participants, seeding_method, tournament)
        
        # Convert to DTOs for TournamentOps
        tournament_dto = TournamentDTO(
            id=tournament.id,
            name=tournament.name,
            game_slug=tournament.game.slug if tournament.game else "",
            stage="bracket",
            team_size=int(getattr(tournament, 'team_size', 0) or 1),
            max_teams=int(getattr(tournament, 'max_teams', 0) or getattr(tournament, 'max_participants', 0) or len(seeded_participants)),
            status=tournament.status or Tournament.DRAFT,
            start_time=getattr(tournament, 'tournament_start', None) or timezone.now(),
            ruleset={
                "seeding_method": seeding_method,
                "original_format": tournament.format,
                "format": bracket_format,
            },
        )
        
        # Create stage DTO (represents single-stage tournament for now)
        # TODO (Epic 3.3): Support multi-stage tournaments via StageTransitionService
        stage_dto = StageDTO(
            id=1,  # Placeholder: actual stage model doesn't exist yet
            name="Main Stage",
            type=bracket_format,
            order=1,
            config={
                "third_place_match": (tournament.config or {}).get('bracket_settings', {}).get('third_place_match', False),
            },
            metadata={
                "is_single_stage": True,
            }
        )
        
        # Convert participants to TeamDTOs
        team_dtos = [
            TeamDTO(
                id=int(p["id"]),
                name=p["name"],
                captain_id=int(p["id"]),
                captain_name=p["name"],
                member_ids=[int(p["id"])],
                member_names=[p["name"]],
                game=tournament.game.slug if tournament.game else "",
                is_verified=True,
                logo_url=None,
            )
            for idx, p in enumerate(seeded_participants)
        ]
        
        # Generate bracket using universal engine
        engine = BracketEngineService()
        match_dtos = engine.generate_bracket_for_stage(
            tournament=tournament_dto,
            stage=stage_dto,
            participants=team_dtos
        )
        
        logger.info(
            f"Universal engine generated {len(match_dtos)} matches for "
            f"tournament {tournament_id}, format '{bracket_format}'"
        )

        total_rounds = max((m.round_number for m in match_dtos), default=0)
        
        # Create Bracket model
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=bracket_format,
            total_rounds=total_rounds,
            total_matches=len(match_dtos),
            bracket_structure={
                "generated_by": "universal_engine",
                "participant_count": len(seeded_participants),
            },
            seeding_method=seeding_method,
            is_finalized=False,
        )
        
        # Convert MatchDTOs to BracketNode models
        created_nodes = []
        for idx, match_dto in enumerate(match_dtos, start=1):
            node = BracketNode.objects.create(
                bracket=bracket,
                position=idx,
                round_number=match_dto.round_number,
                match_number_in_round=match_dto.match_number or 1,
                participant1_id=match_dto.team_a_id,
                participant2_id=match_dto.team_b_id,
                bracket_type=match_dto.stage_type or BracketNode.MAIN,
            )
            created_nodes.append(node)
        
        # Wire parent_node advancement links
        # In single-elimination: match M in round R advances winner to
        # match ceil(M/2) in round R+1, occupying slot 1 (odd M) or 2 (even M)
        import math
        node_lookup = {}
        for node in created_nodes:
            rn = node.round_number
            mn = getattr(node, 'match_number_in_round', None) or getattr(node, 'match_number', None)
            if rn is not None and mn is not None:
                node_lookup[(rn, mn)] = node
        
        max_round = max((n.round_number for n in created_nodes), default=0)
        nodes_to_update = []
        for node in created_nodes:
            rn = node.round_number
            mn = getattr(node, 'match_number_in_round', None) or getattr(node, 'match_number', None)
            if rn is None or mn is None or rn >= max_round:
                continue  # Final round has no parent
            parent_round = rn + 1
            parent_match = math.ceil(mn / 2)
            parent_slot = 1 if (mn % 2 == 1) else 2
            parent_node = node_lookup.get((parent_round, parent_match))
            if parent_node:
                node.parent_node = parent_node
                node.parent_slot = parent_slot
                nodes_to_update.append(node)
        
        if nodes_to_update:
            BracketNode.objects.bulk_update(nodes_to_update, ['parent_node', 'parent_slot'])
        
        logger.info(
            f"Created {len(match_dtos)} BracketNode instances for bracket {bracket.id}"
        )
        
        # TODO (Epic 3.3): Create Match instances with advancement wiring
        # For now, bracket structure is complete but matches not yet created
        
        return bracket
    
    @staticmethod
    @transaction.atomic
    def generate_bracket(
        tournament_id: int,
        bracket_format: Optional[str] = None,
        seeding_method: Optional[str] = None,
        participants: Optional[List[Dict]] = None
    ) -> Bracket:
        """
        LEGACY: Main entry point for bracket generation.
        
        This is the original implementation, preserved for backwards compatibility
        and rollback safety. New code should use generate_bracket_universal_safe()
        which routes to either this method or the universal engine based on feature flag.
        
        Args:
            tournament_id: Tournament ID to generate bracket for
            bracket_format: Bracket format (single-elimination, double-elimination, round-robin).
                           If None, uses tournament.format
            seeding_method: Seeding method (slot-order, random, ranked, manual).
                           If None, uses default slot-order
            participants: List of participant dicts with keys: id, name, seed (optional).
                         If None, fetches from confirmed registrations
        
        Returns:
            Generated Bracket instance
        
        Raises:
            ValidationError: If tournament not found, insufficient participants, or bracket finalized
        
        Example:
            >>> bracket = BracketService.generate_bracket(
            ...     tournament_id=123,
            ...     bracket_format='single-elimination',
            ...     seeding_method='ranked'
            ... )
        """
        # Fetch tournament
        try:
            tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Check if bracket already exists and is finalized
        if hasattr(tournament, 'bracket') and tournament.bracket.is_finalized:
            raise ValidationError(
                f"Bracket for tournament '{tournament.name}' is finalized and cannot be regenerated. "
                "Use recalculate_bracket() to update an existing bracket."
            )
        
        # Determine bracket format
        if bracket_format is None:
            bracket_format = tournament.format or Bracket.SINGLE_ELIMINATION
        
        # Normalize format: Tournament uses underscores, Bracket uses hyphens
        bracket_format = bracket_format.replace('_', '-')
        # GROUP_PLAYOFF tournaments must transition from group results into a
        # knockout bracket, not attempt direct "group-stage" bracket creation.
        if bracket_format == 'group-playoff':
            from apps.tournaments.services.tournament_service import TournamentService

            return TournamentService.transition_to_knockout_stage(tournament_id)
        
        # Validate bracket format
        valid_formats = [choice[0] for choice in Bracket.FORMAT_CHOICES]
        if bracket_format not in valid_formats:
            raise ValidationError(
                f"Invalid bracket format '{bracket_format}'. "
                f"Valid formats: {', '.join(valid_formats)}"
            )
        
        # Determine seeding method
        if seeding_method is None:
            seeding_method = Bracket.SLOT_ORDER
        
        # Validate seeding method
        valid_seeding = [choice[0] for choice in Bracket.SEEDING_METHOD_CHOICES]
        if seeding_method not in valid_seeding:
            raise ValidationError(
                f"Invalid seeding method '{seeding_method}'. "
                f"Valid methods: {', '.join(valid_seeding)}"
            )
        
        # Get participants
        if participants is None:
            participants = BracketService._get_confirmed_participants(tournament)
        
        # Validate participant count
        if len(participants) < 2:
            raise ValidationError(
                f"At least 2 participants required for bracket generation. "
                f"Current count: {len(participants)}"
            )
        
        # Apply seeding
        seeded_participants = BracketService.apply_seeding(participants, seeding_method, tournament)
        
        # Delete existing bracket if not finalized (regeneration)
        if hasattr(tournament, 'bracket'):
            old_bracket = tournament.bracket
            if not old_bracket.is_finalized:
                # Delete old bracket nodes and bracket (use all_objects to include soft-deleted)
                BracketNode.all_objects.filter(bracket=old_bracket).delete()
                old_bracket.delete()
        
        # Generate bracket based on format
        if bracket_format == Bracket.SINGLE_ELIMINATION:
            bracket = BracketService._generate_single_elimination(tournament, seeded_participants, seeding_method)
        elif bracket_format == Bracket.DOUBLE_ELIMINATION:
            bracket = BracketService._generate_double_elimination(tournament, seeded_participants, seeding_method)
        elif bracket_format == Bracket.ROUND_ROBIN:
            bracket = BracketService._generate_round_robin(tournament, seeded_participants, seeding_method)
        elif bracket_format == Bracket.SWISS:
            from apps.tournaments.services.swiss_service import SwissService
            bracket = SwissService.generate_round1(tournament, seeded_participants, seeding_method)
        else:
            raise ValidationError(
                f"Bracket format '{bracket_format}' not yet implemented. "
                f"Supported formats: single-elimination, double-elimination, round-robin, swiss"
            )
        
        return bracket
    
    @staticmethod
    @transaction.atomic
    def generate_knockout_from_groups(
        tournament_id: int,
        bracket_format: Optional[str] = None,
        seeding_method: str = "group_standings",
    ) -> Bracket:
        """
        Generate a knockout bracket using group stage results as input.
        
        Collects all advancers from all groups, orders them based on group position,
        points, and game-specific stats, then passes them into generate_bracket().
        
        Args:
            tournament_id: Tournament ID
            bracket_format: Bracket format (single-elimination, double-elimination).
                          If None, defaults to 'single-elimination'
            seeding_method: Seeding method (default: "ranked" by group results)
        
        Returns:
            Generated Bracket instance for knockout stage
        
        Raises:
            ValidationError: If tournament not GROUP_PLAYOFF, no groups, or insufficient advancers
        
        Example:
            >>> # After group stage completes, generate knockout bracket
            >>> bracket = BracketService.generate_knockout_from_groups(
            ...     tournament_id=123,
            ...     bracket_format='single-elimination',
            ...     seeding_method='ranked'
            ... )
            >>> print(f"Knockout bracket created with {bracket.participant_count} participants")
        """
        from apps.games.services import game_service
        from apps.tournaments.services.group_stage_service import GroupStageService
        
        # Load tournament
        try:
            tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Validate format
        if tournament.format != Tournament.GROUP_PLAYOFF:
            raise ValidationError(
                f"Tournament must be GROUP_PLAYOFF format to generate knockout from groups. "
                f"Current format: {tournament.format}"
            )
        
        # Get advancers from all groups
        try:
            advancers_by_group = GroupStageService.get_advancers(tournament_id)
        except ValidationError as e:
            raise ValidationError(f"Failed to get group advancers: {str(e)}")
        
        if not advancers_by_group:
            raise ValidationError("No advancers found from group stage")
        
        # Flatten advancers into a list with seeding info.
        ordered_groups = list(advancers_by_group.items())
        group_order = {
            group_name: index
            for index, (group_name, _) in enumerate(ordered_groups)
        }
        advancers = []
        advancers_by_group_name: Dict[str, List[Dict]] = {}
        for group_name, standings in ordered_groups:
            for standing in standings:
                advancer = {
                    "group": group_name,
                    "group_index": group_order[group_name],
                    "group_position": standing.rank,  # Position within group (1, 2, 3...)
                    "points": float(standing.points),
                    "team_id": standing.team_id,
                    "user_id": standing.user_id,
                    "name": "",
                }
                
                # Get participant name
                if standing.team:
                    advancer["name"] = standing.team.name
                elif standing.user:
                    advancer["name"] = (
                        standing.user.profile.display_name 
                        if hasattr(standing.user, 'profile') and standing.user.profile.display_name
                        else standing.user.username
                    )
                else:
                    advancer["name"] = "Unknown Participant"
                
                # Add game-specific tie-breaking stats from GameTournamentConfig
                game_slug = tournament.game.slug
                tournament_config = game_service.get_tournament_config(tournament.game)
                
                # Get tiebreakers from config (all 9 supported games now have configs)
                if tournament_config and tournament_config.scoring_rules:
                    tiebreaker_fields = tournament_config.scoring_rules.get('tiebreaker_fields', [])
                    for field_config in tiebreaker_fields:
                        field_name = field_config.get('field')
                        if hasattr(standing, field_name):
                            advancer[field_name] = getattr(standing, field_name)
                elif tournament_config:
                    # Fallback to scoring type detection for games without full scoring_rules
                    scoring_type = tournament_config.default_scoring_type
                    if scoring_type == 'GOALS':
                        advancer["goal_difference"] = getattr(standing, 'goal_difference', 0)
                        advancer["goals_for"] = getattr(standing, 'goals_for', 0)
                    elif scoring_type == 'ROUNDS':
                        advancer["round_difference"] = getattr(standing, 'round_difference', 0)
                        advancer["rounds_won"] = getattr(standing, 'rounds_won', 0)
                    elif scoring_type in ['PLACEMENT', 'KILLS']:
                        advancer["placement_points"] = float(getattr(standing, 'placement_points', 0) or 0)
                        advancer["total_kills"] = getattr(standing, 'total_kills', 0)
                
                advancers.append(advancer)
                advancers_by_group_name.setdefault(group_name, []).append(advancer)

        for group_name in advancers_by_group_name:
            advancers_by_group_name[group_name].sort(
                key=lambda item: (
                    item.get("group_position", 999),
                    -item.get("points", 0),
                )
            )
        
        # Sort advancers by group position first, then by points and game-specific stats
        # Uses game_service.get_tiebreakers() which reads from GameTournamentConfig.
        try:
            tiebreakers = game_service.get_tiebreakers(tournament.game) or []
        except Exception:
            tiebreakers = []
        
        # Build sort key from tiebreakers config
        def sort_key(advancer):
            # Primary sort: group position, then points (descending)
            key = [advancer["group_position"], -advancer["points"]]
            
            # Add tiebreaker fields if available
            for tiebreaker in tiebreakers:
                value = advancer.get(tiebreaker, 0)
                # Negative for descending order (higher is better)
                if tiebreaker not in ['total_deaths']:  # Deaths: lower is better
                    key.append(-float(value) if value else 0)
                else:
                    key.append(float(value) if value else 999)
            
            # Deterministic tie-break across groups.
            key.append(advancer.get("group_index", 0))

            return tuple(key)

        seeding_mode = str(seeding_method or "").replace('-', '_').lower()
        use_cross_match_seeding = (
            seeding_mode in {"group_standings", "cross_match", "cross_group"}
            and len(ordered_groups) >= 2
            and len(ordered_groups) % 2 == 0
            and all(len(advancers_by_group_name.get(group_name, [])) == 2 for group_name, _ in ordered_groups)
        )

        if use_cross_match_seeding:
            # Pair adjacent groups for projected cross-match seeding:
            # A1 vs B2, B1 vs A2, C1 vs D2, D1 vs C2, ...
            next_low_seed = 1
            next_high_seed = len(advancers)

            for idx in range(0, len(ordered_groups), 2):
                group_a_name, _ = ordered_groups[idx]
                group_b_name, _ = ordered_groups[idx + 1]
                group_a_advancers = advancers_by_group_name.get(group_a_name, [])
                group_b_advancers = advancers_by_group_name.get(group_b_name, [])

                if len(group_a_advancers) != 2 or len(group_b_advancers) != 2:
                    use_cross_match_seeding = False
                    break

                # Sorted index 0 = winner, 1 = runner-up.
                group_a_advancers[0]["seed"] = next_low_seed
                group_b_advancers[0]["seed"] = next_low_seed + 1
                group_a_advancers[1]["seed"] = next_high_seed - 1
                group_b_advancers[1]["seed"] = next_high_seed

                next_low_seed += 2
                next_high_seed -= 2

        if not use_cross_match_seeding:
            advancers.sort(key=sort_key)

            # Assign seeds based on sorted order.
            for i, advancer in enumerate(advancers, start=1):
                advancer["seed"] = i
        
        # Build participants list for generate_bracket()
        participants = []
        for adv in sorted(advancers, key=lambda item: item.get("seed", 9999)):
            # Participant ID is either team_id or user_id
            pid = adv["team_id"] or adv["user_id"]
            if pid is None:
                logger.warning(f"Advancer from {adv['group']} has no team_id or user_id, skipping")
                continue
            
            participants.append({
                "id": pid,
                "name": adv["name"],
                "seed": adv["seed"],
            })
        
        # Validate sufficient participants
        if len(participants) < 2:
            raise ValidationError(
                f"Insufficient participants for knockout bracket. Need at least 2, got {len(participants)}"
            )
        
        # Determine bracket format
        if bracket_format is None:
            # Default to single elimination
            bracket_format = Bracket.SINGLE_ELIMINATION

        bracket_format = str(bracket_format).replace('_', '-')
        if bracket_format == 'single-elim':
            bracket_format = Bracket.SINGLE_ELIMINATION
        elif bracket_format == 'double-elim':
            bracket_format = Bracket.DOUBLE_ELIMINATION
        
        # Validate bracket format
        if bracket_format not in [Bracket.SINGLE_ELIMINATION, Bracket.DOUBLE_ELIMINATION]:
            raise ValidationError(
                f"Invalid bracket format '{bracket_format}'. "
                f"For GROUP_PLAYOFF knockout stage, use 'single-elimination' or 'double-elimination'"
            )
        
        logger.info(
            f"Generating {bracket_format} knockout bracket for tournament {tournament.name} "
            f"with {len(participants)} advancers from {len(advancers_by_group)} groups"
        )
        
        # Generate the bracket using existing generate_bracket logic
        # Use seeding_method="manual" since we've already assigned seeds
        bracket = BracketService.generate_bracket(
            tournament_id=tournament_id,
            bracket_format=bracket_format,
            seeding_method="manual",  # Seeds already assigned
            participants=participants
        )
        
        return bracket
    
    @staticmethod
    def apply_seeding(
        participants: List[Dict],
        seeding_method: str,
        tournament: Optional[Tournament] = None
    ) -> List[Dict]:
        """
        Apply seeding strategy to participants.
        
        Args:
            participants: List of participant dicts with keys: id, name, seed (optional)
            seeding_method: Seeding method (slot-order, random, ranked, manual)
            tournament: Tournament instance (required for ranked seeding)
        
        Returns:
            Seeded participant list (sorted by seed)
        
        Example:
            >>> participants = [
            ...     {"id": "team-1", "name": "Team Alpha"},
            ...     {"id": "team-2", "name": "Team Beta"}
            ... ]
            >>> seeded = BracketService.apply_seeding(participants, 'random')
        """
        if seeding_method == Bracket.SLOT_ORDER:
            # Slot order - use registration order (already sorted by registered_at)
            for i, participant in enumerate(participants, start=1):
                participant['seed'] = i
            return participants
        
        elif seeding_method == Bracket.RANDOM:
            # Random seeding
            shuffled = participants.copy()
            random.shuffle(shuffled)
            for i, participant in enumerate(shuffled, start=1):
                participant['seed'] = i
            return shuffled
        
        elif seeding_method == Bracket.RANKED:
            # Module 4.2: Ranked seeding from apps.teams
            if tournament is None:
                raise ValidationError("Tournament required for ranked seeding")
            
            # Import ranking service (lazy to avoid circular imports)
            from apps.tournaments.services.ranking_service import ranking_service
            
            # Get ranked participants (sorted by team ranking)
            # ranking_service validates all teams have rankings and raises
            # ValidationError (400-level) if data is incomplete
            try:
                ranked_participants = ranking_service.get_ranked_participants(
                    participants=participants,
                    tournament=tournament
                )
                return ranked_participants
            except ValidationError:
                # Re-raise validation errors as-is (400 Bad Request)
                raise
            except Exception as e:
                # Catch unexpected errors and wrap with context
                raise ValidationError(
                    f"Failed to apply ranked seeding: {str(e)}"
                )
        
        elif seeding_method == Bracket.MANUAL:
            # Manual seeding - use provided seed values
            # Validate all participants have seeds
            for participant in participants:
                if 'seed' not in participant:
                    raise ValidationError(
                        f"Manual seeding requires all participants to have 'seed' value. "
                        f"Missing for participant: {participant.get('name', participant.get('id'))}"
                    )
            
            # Sort by seed (lower is better)
            return sorted(participants, key=lambda p: p['seed'])
        
        else:
            raise ValidationError(f"Unknown seeding method: {seeding_method}")
    
    @staticmethod
    def _get_confirmed_participants(tournament: Tournament) -> List[Dict]:
        """
        Fetch confirmed registrations for tournament.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            List of participant dicts with keys: id, name, seed
        
        Note:
            Participants are ordered by registered_at (slot order) by default
        """
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED
        ).select_related('user').order_by('registered_at')

        # Pre-fetch team names for team tournaments
        team_ids = [r.team_id for r in registrations if r.team_id]
        team_name_map = {}
        if team_ids:
            try:
                from apps.organizations.models.team import Team as OrgTeam
                team_name_map = dict(
                    OrgTeam.objects.filter(id__in=team_ids)
                    .values_list('id', 'name')
                )
            except Exception:
                pass
        
        participants = []
        for reg in registrations:
            # Determine participant ID and name
            if reg.team_id:
                # Team-based tournament — resolve real name
                participant_id = reg.team_id
                participant_name = team_name_map.get(reg.team_id) or f"Team {reg.team_id}"
                is_team = True
            else:
                # Solo tournament
                participant_id = reg.user_id  # Store as integer
                participant_name = reg.user.username if reg.user else f"User {reg.user_id}"
                is_team = False
            
            participants.append({
                'id': participant_id,
                'participant_id': participant_id,  # Module 4.2: ranking_service expects this
                'name': participant_name,
                'seed': reg.seed if reg.seed else len(participants) + 1,
                'registration_id': reg.id,
                'is_team': is_team  # Module 4.2: ranking_service uses this to validate team tournaments
            })
        
        return participants
    
    @staticmethod
    @transaction.atomic
    def _generate_single_elimination(
        tournament: Tournament,
        participants: List[Dict],
        seeding_method: str
    ) -> Bracket:
        """
        Generate single elimination bracket.
        
        Algorithm:
        1. Calculate rounds needed: ceil(log2(participant_count))
        2. Calculate next power of 2 for bracket size
        3. Create bracket nodes in tree structure (bottom-up)
        4. Assign participants with standard seeding (1 vs lowest, 2 vs 2nd lowest, etc.)
        5. Add byes for missing slots
        6. Link parent/child nodes for progression
        
        Args:
            tournament: Tournament instance
            participants: Seeded participant list
            seeding_method: Seeding method used
        
        Returns:
            Created Bracket instance with all nodes
        
        Example:
            4 participants → 2 rounds (semifinals → finals)
            8 participants → 3 rounds (quarterfinals → semifinals → finals)
            16 participants → 4 rounds
        """
        participant_count = len(participants)
        
        # Calculate bracket size (next power of 2)
        total_rounds = math.ceil(math.log2(participant_count)) if participant_count > 1 else 1
        bracket_size = 2 ** total_rounds
        
        # Calculate total matches (bracket_size - 1 for single elimination)
        total_matches = bracket_size - 1
        
        # Create bracket structure metadata for JSONB
        bracket_structure = {
            'format': 'single-elimination',
            'total_participants': participant_count,
            'bracket_size': bracket_size,
            'rounds': []
        }
        
        # Build rounds metadata
        for round_num in range(1, total_rounds + 1):
            matches_in_round = bracket_size // (2 ** round_num)
            round_name = BracketService._get_round_name(round_num, total_rounds)
            
            bracket_structure['rounds'].append({
                'round_number': round_num,
                'round_name': round_name,
                'matches': matches_in_round
            })
        
        # Create Bracket instance
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=total_rounds,
            total_matches=total_matches,
            bracket_structure=bracket_structure,
            seeding_method=seeding_method,
            is_finalized=False
        )
        
        # Create bracket nodes (bottom-up approach)
        nodes_by_position = {}  # position -> BracketNode
        current_position = 1
        
        # Round 1: Create leaf nodes with participants
        matches_in_round_1 = bracket_size // 2
        participants_with_byes = participants + [None] * (bracket_size - participant_count)
        
        # Standard single elimination seeding: 1 vs n, 2 vs n-1, etc.
        seeded_slots = []
        for i in range(matches_in_round_1):
            top_seed_idx = i
            bottom_seed_idx = bracket_size - 1 - i
            seeded_slots.append((
                participants_with_byes[top_seed_idx],
                participants_with_byes[bottom_seed_idx]
            ))
        
        # Create Round 1 nodes
        for match_number, (participant1, participant2) in enumerate(seeded_slots, start=1):
            # Check for byes
            is_bye = (participant1 is None or participant2 is None)
            
            node = BracketNode.objects.create(
                bracket=bracket,
                position=current_position,
                round_number=1,
                match_number_in_round=match_number,
                participant1_id=participant1['id'] if participant1 else None,
                participant1_name=participant1['name'] if participant1 else '',
                participant2_id=participant2['id'] if participant2 else None,
                participant2_name=participant2['name'] if participant2 else '',
                is_bye=is_bye,
                bracket_type=BracketNode.MAIN
            )
            
            nodes_by_position[current_position] = node
            current_position += 1
        
        # Create subsequent rounds (empty nodes that will be filled by winners)
        for round_num in range(2, total_rounds + 1):
            matches_in_round = bracket_size // (2 ** round_num)
            
            for match_number in range(1, matches_in_round + 1):
                node = BracketNode.objects.create(
                    bracket=bracket,
                    position=current_position,
                    round_number=round_num,
                    match_number_in_round=match_number,
                    bracket_type=BracketNode.MAIN
                )
                
                nodes_by_position[current_position] = node
                current_position += 1
        
        # Link parent/child relationships
        BracketService._link_single_elimination_nodes(nodes_by_position, bracket_size, total_rounds)
        
        return bracket
    
    @staticmethod
    def _link_single_elimination_nodes(
        nodes_by_position: Dict[int, BracketNode],
        bracket_size: int,
        total_rounds: int
    ) -> None:
        """
        Link parent/child relationships for single elimination bracket.
        
        Pattern:
        - Positions 1-2 (Round 1, Match 1) → Position n (Round 2, Match 1)
        - Positions 3-4 (Round 1, Match 2) → Position n+1 (Round 2, Match 2)
        
        Args:
            nodes_by_position: Dict mapping position to BracketNode
            bracket_size: Total bracket size (power of 2)
            total_rounds: Number of rounds
        """
        position = 1
        
        for round_num in range(1, total_rounds):
            matches_in_current_round = bracket_size // (2 ** round_num)
            matches_in_next_round = bracket_size // (2 ** (round_num + 1))
            
            # Calculate starting position for next round
            next_round_start_position = position + matches_in_current_round
            
            for match_number in range(matches_in_current_round):
                current_node = nodes_by_position[position + match_number]
                
                # Determine parent node (every 2 matches go to 1 parent)
                parent_match_number = (match_number // 2) + 1
                parent_position = next_round_start_position + (match_number // 2)
                parent_node = nodes_by_position[parent_position]
                
                # Link current node to parent
                current_node.parent_node = parent_node
                current_node.parent_slot = 1 if match_number % 2 == 0 else 2
                current_node.save()
                
                # Link parent to children
                if match_number % 2 == 0:
                    parent_node.child1_node = current_node
                else:
                    parent_node.child2_node = current_node
                    parent_node.save()  # Save after both children assigned
            
            position += matches_in_current_round
    
    @staticmethod
    def _generate_double_elimination(
        tournament: Tournament,
        participants: List[Dict],
        seeding_method: str
    ) -> Bracket:
        """
        Generate double elimination bracket.

        Structure:
        - Winners Bracket (WB): Standard single-elimination.
        - Losers Bracket (LB): Losers from WB drop in; only eliminated after 2 losses.
          * LB round 1: WB round 1 losers (n/2 teams → n/4 matches)
          * LB round 2: LB round 1 winners (survivors only)  
          * WB round k losers drop into LB at corresponding level.
        - Grand Finals (GF): WB winner vs LB winner.
        - Grand Finals Reset (GFR): If LB winner beats WB winner in GF,
          they play a reset match (LB side had 0 prior losses, WB side had 1).

        Args:
            tournament: Tournament instance
            participants: Seeded participant list
            seeding_method: Seeding method used

        Returns:
            Created Bracket instance with WB, LB, GF, and GFR nodes.
        """
        import math

        n = len(participants)
        if n < 2:
            raise ValidationError("Double elimination requires at least 2 participants.")

        # WB structure (same as single elimination)
        wb_rounds = math.ceil(math.log2(n)) if n > 1 else 1
        wb_size = 2 ** wb_rounds  # virtual bracket size (power-of-2)

        # LB structure: WB round k losers feed to LB round (2k-2 or 2k-1).
        # For n participants: LB has 2*(wb_rounds-1) rounds.
        lb_rounds = 2 * (wb_rounds - 1)

        # Total rounds: WB rounds + LB rounds + GF + GFR
        # We label them all as sequential numbers in their respective bracket_type.
        total_wb_matches = wb_size - 1
        total_lb_matches = (wb_size // 2) - 1  # LB is half the WB size minus grand final entry
        gf_matches = 2  # Grand Finals + potential Reset

        bracket_structure = {
            "format": "double-elimination",
            "total_participants": n,
            "wb_rounds": wb_rounds,
            "lb_rounds": lb_rounds,
            "wb_size": wb_size,
            "rounds": [],
        }

        # Summarise rounds for metadata
        for r in range(1, wb_rounds + 1):
            bracket_structure["rounds"].append({
                "bracket_type": "main",
                "round_number": r,
                "round_name": f"WB Round {r}",
                "matches": wb_size // (2 ** r),
            })
        for r in range(1, lb_rounds + 1):
            bracket_structure["rounds"].append({
                "bracket_type": "losers",
                "round_number": r,
                "round_name": f"LB Round {r}",
                "matches": max(1, (wb_size // 4) // (((r + 1) // 2))),
            })
        bracket_structure["rounds"].append({"bracket_type": "main", "round_number": wb_rounds + 1, "round_name": "Grand Finals", "matches": 1})
        bracket_structure["rounds"].append({"bracket_type": "main", "round_number": wb_rounds + 2, "round_name": "Grand Finals Reset", "matches": 1})

        # ── WB→LB loser-drop routing table ───────────────────────────
        # Maps "main_Rk_Mm" → {lb_round, lb_match, lb_slot} so that
        # update_bracket_after_match() can route WB losers to the right LB node
        # without any hard-coded round arithmetic at result time.
        loser_drops: Dict[str, dict] = {}
        if lb_rounds > 0:
            wb_r1_mc = wb_size // 2  # WB round-1 match count
            # WB-R1 losers pair up in LB-R1 (adjacent WB matches share one LB node)
            for m in range(1, wb_r1_mc + 1):
                loser_drops[f"main_R1_M{m}"] = {
                    "lb_round": 1,
                    "lb_match": (m + 1) // 2,
                    "lb_slot": 1 if m % 2 == 1 else 2,
                }
            # WB-Rk (k ≥ 2) losers drop to LB feed round (2k-2), slot 2
            # Slot 1 is reserved for the LB survivor advancing from the prior LB round.
            for k in range(2, wb_rounds + 1):
                lb_feed_round = 2 * k - 2
                wb_mk = wb_size // (2 ** k)
                for m in range(1, wb_mk + 1):
                    loser_drops[f"main_R{k}_M{m}"] = {
                        "lb_round": lb_feed_round,
                        "lb_match": m,
                        "lb_slot": 2,
                    }
        bracket_structure["loser_drops"] = loser_drops

        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.DOUBLE_ELIMINATION,
            total_rounds=wb_rounds + lb_rounds + 2,  # +GF +GFR
            total_matches=total_wb_matches + max(1, lb_rounds) + gf_matches,
            bracket_structure=bracket_structure,
            seeding_method=seeding_method,
            is_finalized=False,
        )

        # ── Winners Bracket Nodes ──────────────────────────────────────
        # Mirror single-elimination logic but bracket_type='main'
        participants_with_byes = participants + [None] * (wb_size - n)
        wb_nodes: Dict[str, BracketNode] = {}  # key: "wbR{r}_M{m}"

        position = 1
        wb_r1_matches = wb_size // 2

        # Create WB round 1 nodes
        seeded_slots = []
        for i in range(wb_r1_matches):
            seeded_slots.append((participants_with_byes[i], participants_with_byes[wb_size - 1 - i]))

        for match_num, (p1, p2) in enumerate(seeded_slots, start=1):
            is_bye = p1 is None or p2 is None
            node = BracketNode.objects.create(
                bracket=bracket, position=position, round_number=1,
                match_number_in_round=match_num,
                participant1_id=p1["id"] if p1 else None,
                participant1_name=p1["name"] if p1 else "",
                participant2_id=p2["id"] if p2 else None,
                participant2_name=p2["name"] if p2 else "",
                is_bye=is_bye,
                bracket_type=BracketNode.MAIN,
            )
            wb_nodes[f"wb_R1_M{match_num}"] = node
            position += 1

        # Create WB rounds 2 → wb_rounds
        for r in range(2, wb_rounds + 1):
            matches = wb_size // (2 ** r)
            for m in range(1, matches + 1):
                node = BracketNode.objects.create(
                    bracket=bracket, position=position, round_number=r,
                    match_number_in_round=m, bracket_type=BracketNode.MAIN,
                )
                wb_nodes[f"wb_R{r}_M{m}"] = node
                position += 1

        # Link WB parent/child
        for r in range(1, wb_rounds):
            matches_curr = wb_size // (2 ** r)
            for m in range(1, matches_curr + 1):
                curr_node = wb_nodes[f"wb_R{r}_M{m}"]
                parent_m = (m + 1) // 2
                parent_node = wb_nodes[f"wb_R{r + 1}_M{parent_m}"]
                curr_node.parent_node = parent_node
                curr_node.parent_slot = 1 if m % 2 == 1 else 2
                curr_node.save()
                if m % 2 == 1:
                    parent_node.child1_node = curr_node
                else:
                    parent_node.child2_node = curr_node
                    parent_node.save()

        # ── Losers Bracket Nodes ─────────────────────────────────────
        # LB round structure:
        # LB-R1 (n/4 matches): WB-R1 losers vs WB-R1 losers
        # LB-R2 (n/4 matches): LB-R1 winners vs WB-R2 losers (if same count)
        # … alternating between "feed" rounds and "play" rounds
        lb_nodes: Dict[str, BracketNode] = {}
        lb_r1_matches = wb_r1_matches // 2  # n/4

        for r in range(1, lb_rounds + 1):
            # LB match count halves every 2 rounds
            lb_matches_this_round = max(1, lb_r1_matches // (2 ** ((r - 1) // 2)))
            for m in range(1, lb_matches_this_round + 1):
                node = BracketNode.objects.create(
                    bracket=bracket, position=position,
                    round_number=r, match_number_in_round=m,
                    bracket_type=BracketNode.LOSERS,
                )
                lb_nodes[f"lb_R{r}_M{m}"] = node
                position += 1

        # ── Grand Finals & Reset ──────────────────────────────────────
        gf_node = BracketNode.objects.create(
            bracket=bracket, position=position,
            round_number=wb_rounds + 1, match_number_in_round=1,
            bracket_type=BracketNode.MAIN,
        )
        position += 1

        gf_reset_node = BracketNode.objects.create(
            bracket=bracket, position=position,
            round_number=wb_rounds + 2, match_number_in_round=1,
            bracket_type=BracketNode.MAIN,
            is_bye=True,  # Reset only played if LB winner wins GF
        )

        # Link WB finals → Grand Finals
        wb_finals = wb_nodes.get(f"wb_R{wb_rounds}_M1")
        if wb_finals:
            wb_finals.parent_node = gf_node
            wb_finals.parent_slot = 1
            wb_finals.save()
            gf_node.child1_node = wb_finals
            gf_node.save()

        # Link GF → GFR
        gf_node.parent_node = gf_reset_node
        gf_node.parent_slot = 1
        gf_node.save()
        gf_reset_node.child1_node = gf_node
        gf_reset_node.save()

        # ── Wire Losers Bracket parent/child links ────────────────────
        # Two transition types alternate through LB rounds:
        #   Odd LB round  → Even LB round (feed):  same match number, slot 1
        #   Even LB round → Odd LB round (consol.): pair-up like SE, slot per parity
        # Last LB round (LB Finals) winner advances to GF slot 2.
        if lb_rounds > 0 and lb_nodes:
            for r in range(1, lb_rounds + 1):
                lb_m_count = max(1, lb_r1_matches // (2 ** ((r - 1) // 2)))
                for m in range(1, lb_m_count + 1):
                    curr_lb = lb_nodes[f"lb_R{r}_M{m}"]

                    if r == lb_rounds:
                        # LB Finals → GF slot 2
                        curr_lb.parent_node = gf_node
                        curr_lb.parent_slot = 2
                        curr_lb.save()
                        gf_node.child2_node = curr_lb
                        gf_node.save()
                    else:
                        if r % 2 == 1:
                            # Odd → even (feed round): 1:1, LB winner fills slot 1
                            parent_m = m
                            parent_slot = 1
                        else:
                            # Even → odd (consolidation): pairs fold like SE
                            parent_m = (m + 1) // 2
                            parent_slot = 1 if m % 2 == 1 else 2
                        parent_lb = lb_nodes[f"lb_R{r + 1}_M{parent_m}"]
                        curr_lb.parent_node = parent_lb
                        curr_lb.parent_slot = parent_slot
                        curr_lb.save()
                        if parent_slot == 1:
                            parent_lb.child1_node = curr_lb
                        else:
                            parent_lb.child2_node = curr_lb
                        parent_lb.save()

        return bracket

    @staticmethod
    def _generate_round_robin(
        tournament: Tournament,
        participants: List[Dict],
        seeding_method: str
    ) -> Bracket:
        """
        Generate round robin bracket (all participants play each other).
        
        Algorithm:
        1. Total matches = n * (n-1) / 2 where n = participant count
        2. Create one round with all matchups
        3. Each participant plays every other participant once
        
        Args:
            tournament: Tournament instance
            participants: Seeded participant list
            seeding_method: Seeding method used
        
        Returns:
            Created Bracket instance with all round robin matches
        
        Note:
            Round robin uses bracket_type='main' and single round structure
        """
        participant_count = len(participants)
        
        # Calculate total matches: n choose 2 = n * (n-1) / 2
        total_matches = (participant_count * (participant_count - 1)) // 2
        
        # Create bracket structure metadata
        bracket_structure = {
            'format': 'round-robin',
            'total_participants': participant_count,
            'rounds': [
                {
                    'round_number': 1,
                    'round_name': 'Round Robin',
                    'matches': total_matches
                }
            ]
        }
        
        # Create Bracket instance
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.ROUND_ROBIN,
            total_rounds=1,
            total_matches=total_matches,
            bracket_structure=bracket_structure,
            seeding_method=seeding_method,
            is_finalized=False
        )
        
        # Create bracket nodes for all matchups
        match_number = 1
        position = 1
        
        for i in range(participant_count):
            for j in range(i + 1, participant_count):
                participant1 = participants[i]
                participant2 = participants[j]
                
                BracketNode.objects.create(
                    bracket=bracket,
                    position=position,
                    round_number=1,
                    match_number_in_round=match_number,
                    participant1_id=participant1['id'],
                    participant1_name=participant1['name'],
                    participant2_id=participant2['id'],
                    participant2_name=participant2['name'],
                    is_bye=False,
                    bracket_type=BracketNode.MAIN
                )
                
                match_number += 1
                position += 1
        
        return bracket
    
    @staticmethod
    def _get_round_name(round_number: int, total_rounds: int) -> str:
        """
        Get human-readable round name based on position.
        
        Args:
            round_number: Current round number (1-indexed)
            total_rounds: Total number of rounds in bracket
        
        Returns:
            Round name (e.g., "Finals", "Semi Finals", "Quarter Finals", "Round 1")
        
        Example:
            >>> BracketService._get_round_name(3, 3)
            "Finals"
            >>> BracketService._get_round_name(2, 3)
            "Semi Finals"
        """
        rounds_from_end = total_rounds - round_number
        
        if rounds_from_end == 0:
            return "Finals"
        elif rounds_from_end == 1:
            return "Semi Finals"
        elif rounds_from_end == 2:
            return "Quarter Finals"
        elif rounds_from_end == 3:
            return "Round of 16"
        elif rounds_from_end == 4:
            return f"Round of 32"
        else:
            return f"Round {round_number}"
    
    @staticmethod
    @transaction.atomic
    def create_matches_from_bracket(bracket: Bracket) -> List[Match]:
        """
        Create Match records from BracketNodes.
        
        Generates Match instances for all bracket nodes that have both participants
        assigned. Skips bye matches and empty nodes waiting for winners.
        
        Args:
            bracket: Bracket instance to create matches for
        
        Returns:
            List of created Match instances
        
        Raises:
            ValidationError: If bracket is invalid or matches already exist
        
        Example:
            >>> bracket = BracketService.generate_bracket(tournament_id=123)
            >>> matches = BracketService.create_matches_from_bracket(bracket)
            >>> print(f"Created {len(matches)} matches")
        """
        # Fetch all nodes with both participants (ready for match creation)
        ready_nodes = BracketNode.objects.filter(
            bracket=bracket,
            participant1_id__isnull=False,
            participant2_id__isnull=False,
            match__isnull=True  # No match created yet
        ).exclude(is_bye=True)
        
        created_matches = []
        
        for node in ready_nodes:
            # Create Match instance
            match = Match.objects.create(
                tournament=bracket.tournament,
                round_number=node.round_number,
                match_number=node.match_number_in_round,
                participant1_id=node.participant1_id,
                participant2_id=node.participant2_id,
                state=Match.SCHEDULED,
            )
            
            # Link match to node
            node.match = match
            node.save(update_fields=['match'])
            
            created_matches.append(match)
        
        return created_matches
    
    @staticmethod
    @transaction.atomic
    def update_bracket_after_match(match: Match) -> Optional[BracketNode]:
        """
        Update bracket structure after match completion.
        
        Advances the winner to the next round by updating parent node participants.
        Handles bye advancement and losers bracket progression for double elimination.
        
        Args:
            match: Completed Match instance with winner determined
        
        Returns:
            Parent BracketNode if winner was advanced, None if finals or error
        
        Raises:
            ValidationError: If match is not completed or has no winner
            
        Side Effects:
            - Broadcasts bracket_updated event via WebSocket (Module 2.3)
            - May create new match for parent node if both participants ready
        
        Example:
            >>> match.winner_id = "team-1"
            >>> match.status = Match.COMPLETED
            >>> match.save()
            >>> parent_node = BracketService.update_bracket_after_match(match)
        """
        # Validate match is completed
        if match.state not in (Match.COMPLETED, Match.FORFEIT):
            raise ValidationError(
                f"Cannot update bracket for match {match.id}: "
                f"Match state is '{match.state}', expected one of: completed, forfeit"
            )
        
        if not match.winner_id:
            raise ValidationError(
                f"Cannot update bracket for match {match.id}: No winner determined"
            )
        
        # Get bracket node for this match
        try:
            node = BracketNode.objects.select_related('parent_node', 'bracket').get(match=match)
        except BracketNode.DoesNotExist:
            # Match not linked to bracket (might be manual match)
            logger.info(f"Match {match.id} not linked to bracket - skipping bracket update")
            return None
        
        # Track updated nodes for broadcast
        updated_node_ids = [node.id]
        created_matches = []
        
        # Update node winner
        node.winner_id = match.winner_id
        node.save(update_fields=['winner_id'])
        
        # Get parent node
        parent_node = node.parent_node
        if not parent_node:
            # This is the finals node - no parent to advance to
            logger.info(f"Match {match.id} is finals - bracket complete")
            
            # Broadcast bracket_updated (tournament complete)
            # Module 6.1: Wrap async broadcast with async_to_sync
            try:
                async_to_sync(broadcast_bracket_updated)(
                    tournament_id=match.tournament_id,
                    bracket_data={
                        'bracket_id': node.bracket.id,
                        'tournament_id': match.tournament_id,
                        'updated_nodes': updated_node_ids,
                        'next_matches': [],
                        'bracket_status': 'completed',
                        'finals_winner_id': match.winner_id,
                        'updated_at': timezone.now().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Failed to broadcast bracket_updated for completed bracket {node.bracket.id}: {e}",
                    exc_info=True
                )
            
            return None
        
        # Determine winner name from node participants
        winner_name = node.get_winner_name()
        
        # Advance winner to parent node based on parent_slot
        if node.parent_slot == 1:
            parent_node.participant1_id = match.winner_id
            parent_node.participant1_name = winner_name
        elif node.parent_slot == 2:
            parent_node.participant2_id = match.winner_id
            parent_node.participant2_name = winner_name
        else:
            raise ValidationError(
                f"Invalid parent_slot {node.parent_slot} for node {node.id}. "
                "Must be 1 or 2."
            )

        # ── GF Reset activation (Double Elimination) ─────────────────────
        # If the parent node is flagged as a conditional bye match (is_bye=True),
        # this is the Grand Finals → GF Reset transition.  The GF loser must be
        # seeded into the opposite slot so the reset match can be scheduled.
        gfr_activated = False
        if parent_node.is_bye:
            loser_id = (
                node.participant2_id
                if match.winner_id == node.participant1_id
                else node.participant1_id
            )
            loser_name = (
                node.participant2_name
                if match.winner_id == node.participant1_id
                else node.participant1_name
            ) or ""
            # Place loser in the slot NOT already taken by the winner
            if node.parent_slot == 1:
                parent_node.participant2_id = loser_id
                parent_node.participant2_name = loser_name
            else:
                parent_node.participant1_id = loser_id
                parent_node.participant1_name = loser_name
            parent_node.is_bye = False
            gfr_activated = True
            logger.info(
                "GFR activated for bracket node %s: GF winner=%s, GFR loser=%s",
                parent_node.id, match.winner_id, loser_id,
            )

        save_fields = ['participant1_id', 'participant1_name',
                       'participant2_id', 'participant2_name']
        if gfr_activated:
            save_fields.append('is_bye')
        parent_node.save(update_fields=save_fields)
        updated_node_ids.append(parent_node.id)

        # ── WB Loser Drop (Double Elimination) ───────────────────────
        # When a WB (bracket_type=MAIN) match completes and the bracket is DE,
        # route the loser to the appropriate LB node as stored in loser_drops.
        # Skip byes (no real loser) and skip GF/GFR nodes (handled separately).
        if (
            not gfr_activated
            and node.bracket_type == BracketNode.MAIN
            and node.bracket.format == Bracket.DOUBLE_ELIMINATION
            and not node.is_bye
        ):
            bstruct = node.bracket.bracket_structure or {}
            loser_drops = bstruct.get("loser_drops", {})
            drop_key = f"main_R{node.round_number}_M{node.match_number_in_round}"
            drop_info = loser_drops.get(drop_key)
            if drop_info:
                loser_id = (
                    node.participant2_id
                    if match.winner_id == node.participant1_id
                    else node.participant1_id
                )
                loser_name = (
                    (node.participant2_name if match.winner_id == node.participant1_id
                     else node.participant1_name) or ""
                )
                try:
                    lb_node = BracketNode.objects.select_related('bracket').get(
                        bracket=node.bracket,
                        bracket_type=BracketNode.LOSERS,
                        round_number=drop_info["lb_round"],
                        match_number_in_round=drop_info["lb_match"],
                    )
                    lb_slot = drop_info["lb_slot"]
                    lb_save = []
                    if lb_slot == 1:
                        lb_node.participant1_id = loser_id
                        lb_node.participant1_name = loser_name
                        lb_save = ['participant1_id', 'participant1_name']
                    else:
                        lb_node.participant2_id = loser_id
                        lb_node.participant2_name = loser_name
                        lb_save = ['participant2_id', 'participant2_name']
                    lb_node.save(update_fields=lb_save)
                    updated_node_ids.append(lb_node.id)
                    logger.info(
                        "DE loser drop: match %s loser %s → LB-R%s-M%s slot %s",
                        match.id, loser_id,
                        drop_info["lb_round"], drop_info["lb_match"], lb_slot,
                    )
                    # Create LB match if both participants are now ready
                    if lb_node.has_both_participants and not lb_node.match_id:
                        lb_match = Match.objects.create(
                            tournament=lb_node.bracket.tournament,
                            round_number=lb_node.round_number,
                            match_number=lb_node.match_number_in_round,
                            participant1_id=lb_node.participant1_id,
                            participant2_id=lb_node.participant2_id,
                            state=Match.SCHEDULED,
                        )
                        lb_node.match = lb_match
                        lb_node.save(update_fields=['match'])
                        created_matches.append({
                            'match_id': lb_match.id,
                            'round': lb_match.round_number,
                            'match_number': lb_match.match_number,
                            'participant1_id': lb_match.participant1_id,
                            'participant2_id': lb_match.participant2_id,
                        })
                except BracketNode.DoesNotExist:
                    logger.warning(
                        "DE loser drop: LB node not found for drop_key=%s (bracket %s)",
                        drop_key, node.bracket_id,
                    )

        # Check if parent node is ready for match creation
        if parent_node.has_both_participants and not parent_node.match:
            # Create match for parent node
            parent_match = Match.objects.create(
                tournament=parent_node.bracket.tournament,
                round_number=parent_node.round_number,
                match_number=parent_node.match_number_in_round,
                participant1_id=parent_node.participant1_id,
                participant2_id=parent_node.participant2_id,
                state=Match.SCHEDULED,
            )
            
            parent_node.match = parent_match
            parent_node.save(update_fields=['match'])
            
            created_matches.append({
                'match_id': parent_match.id,
                'round': parent_match.round_number,
                'match_number': parent_match.match_number,
                'participant1_id': parent_match.participant1_id,
                'participant2_id': parent_match.participant2_id,
            })
        
        # Module 2.3: Broadcast bracket_updated event to WebSocket clients
        # Module 6.1: Wrap async broadcast with async_to_sync
        try:
            async_to_sync(broadcast_bracket_updated)(
                tournament_id=match.tournament_id,
                bracket_data={
                    'bracket_id': node.bracket.id,
                    'tournament_id': match.tournament_id,
                    'updated_nodes': updated_node_ids,
                    'next_matches': created_matches,
                    'bracket_status': node.bracket.status,
                    'parent_node_ready': parent_node.has_both_participants,
                    'updated_at': timezone.now().isoformat(),
                }
            )
        except Exception as e:
            # Log error but don't fail transaction - broadcasting is non-critical
            logger.warning(
                f"Failed to broadcast bracket_updated for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'tournament_id': match.tournament_id}
            )
        
        return parent_node
    
    @staticmethod
    @transaction.atomic
    def recalculate_bracket(tournament_id: int, force: bool = False) -> Bracket:
        """
        Recalculate/regenerate bracket for tournament.
        
        Updates existing bracket or creates new one based on current registrations.
        Preserves completed matches and their results if force=False.
        
        Args:
            tournament_id: Tournament ID to recalculate bracket for
            force: If True, completely regenerate bracket (deletes all nodes and matches).
                  If False, update bracket preserving completed matches (default)
        
        Returns:
            Updated or regenerated Bracket instance
        
        Raises:
            ValidationError: If tournament not found or bracket is finalized
        
        Example:
            >>> # Soft recalculation (preserves results)
            >>> bracket = BracketService.recalculate_bracket(tournament_id=123)
            >>> 
            >>> # Force regeneration (deletes everything)
            >>> bracket = BracketService.recalculate_bracket(tournament_id=123, force=True)
        """
        # Fetch tournament
        try:
            tournament = Tournament.objects.select_related('bracket').get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Check if bracket exists
        if not hasattr(tournament, 'bracket'):
            # No bracket exists - generate new one
            return BracketService.generate_bracket(tournament_id)
        
        bracket = tournament.bracket
        
        # Check if bracket is finalized
        if bracket.is_finalized and not force:
            raise ValidationError(
                f"Bracket for tournament '{tournament.name}' is finalized and cannot be recalculated. "
                "Use force=True to regenerate (WARNING: deletes all matches and results)."
            )
        
        if force:
            # Force regeneration - delete everything and start fresh
            # Delete all matches linked to bracket nodes (use all_objects to include soft-deleted)
            Match.objects.filter(bracket_node__bracket=bracket).delete()
            
            # Delete all bracket nodes (use all_objects to include soft-deleted)
            BracketNode.all_objects.filter(bracket=bracket).delete()
            
            # Delete bracket
            bracket.delete()
            
            # Generate new bracket
            return BracketService.generate_bracket(tournament_id)
        
        else:
            # Soft recalculation - preserve completed matches
            # This is complex and requires:
            # 1. Identify completed nodes
            # 2. Update pending nodes with new participants
            # 3. Regenerate empty portions of bracket
            
            # For initial implementation, raise NotImplementedError
            # Full implementation would require sophisticated merge logic
            raise NotImplementedError(
                "Soft bracket recalculation (preserving results) not yet implemented. "
                "Use force=True to completely regenerate bracket, or manually adjust nodes."
            )
    
    @staticmethod
    @transaction.atomic
    def finalize_bracket(bracket_id: int, finalized_by=None) -> Bracket:
        """
        Finalize bracket to prevent further modifications.
        
        Locks the bracket structure so no regeneration or modification is allowed.
        This is typically done after the tournament starts.
        
        Module 2.4: Security Hardening - Audit logging added
        
        Args:
            bracket_id: Bracket ID to finalize
            finalized_by: User finalizing the bracket (admin/organizer)
        
        Returns:
            Finalized Bracket instance
        
        Raises:
            ValidationError: If bracket not found or already finalized
        
        Example:
            >>> bracket = BracketService.finalize_bracket(
            ...     bracket_id=456,
            ...     finalized_by=request.user
            ... )
            >>> assert bracket.is_finalized == True
        """
        try:
            bracket = Bracket.objects.get(id=bracket_id)
        except Bracket.DoesNotExist:
            raise ValidationError(f"Bracket with ID {bracket_id} not found")
        
        if bracket.is_finalized:
            raise ValidationError(f"Bracket {bracket_id} is already finalized")
        
        bracket.is_finalized = True
        bracket.save(update_fields=['is_finalized'])
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        if finalized_by:
            from apps.tournaments.security.audit import audit_event, AuditAction
            
            audit_event(
                user=finalized_by,
                action=AuditAction.BRACKET_FINALIZE,
                meta={
                    'bracket_id': bracket_id,
                    'tournament_id': bracket.tournament_id,
                    'bracket_type': bracket.bracket_type,
                    'total_nodes': bracket.nodes.count(),
                }
            )
        
        # Publish bracket.finalized event
        _bracket_id = bracket.id
        _tourney_id = bracket.tournament_id
        def _emit_finalized():
            _publish_bracket_event(
                "bracket.finalized",
                bracket_id=_bracket_id,
                tournament_id=_tourney_id,
            )
        transaction.on_commit(_emit_finalized)
        
        return bracket
    
    @staticmethod
    def get_bracket_visualization_data(bracket_id: int) -> Dict:
        """
        Get bracket data formatted for frontend visualization.
        
        Returns structured data with rounds, matches, and progression for UI rendering.
        
        Args:
            bracket_id: Bracket ID to visualize
        
        Returns:
            Dict with structure:
            {
                'bracket': {...},  # Bracket model data
                'rounds': [  # List of rounds
                    {
                        'round_number': 1,
                        'round_name': 'Quarter Finals',
                        'matches': [  # List of bracket nodes
                            {
                                'position': 1,
                                'participant1': {...},
                                'participant2': {...},
                                'winner': {...},
                                'match_id': 123,
                                'is_bye': False
                            }
                        ]
                    }
                ]
            }
        
        Example:
            >>> data = BracketService.get_bracket_visualization_data(bracket_id=456)
            >>> for round_data in data['rounds']:
            >>>     print(f"{round_data['round_name']}: {len(round_data['matches'])} matches")
        """
        try:
            bracket = Bracket.objects.get(id=bracket_id)
        except Bracket.DoesNotExist:
            raise ValidationError(f"Bracket with ID {bracket_id} not found")
        
        # Fetch all nodes ordered by round and position
        nodes = BracketNode.objects.filter(bracket=bracket).select_related('match').order_by(
            'round_number', 'position'
        )
        
        # Group nodes by round
        rounds_data = {}
        for node in nodes:
            if node.round_number not in rounds_data:
                round_name = bracket.get_round_name(node.round_number)
                rounds_data[node.round_number] = {
                    'round_number': node.round_number,
                    'round_name': round_name,
                    'matches': []
                }
            
            # Format node data for visualization
            match_data = {
                'position': node.position,
                'participant1': {
                    'id': node.participant1_id,
                    'name': node.participant1_name
                } if node.participant1_id else None,
                'participant2': {
                    'id': node.participant2_id,
                    'name': node.participant2_name
                } if node.participant2_id else None,
                'winner': {
                    'id': node.winner_id,
                    'name': node.get_winner_name()
                } if node.winner_id else None,
                'match_id': node.match_id,
                'is_bye': node.is_bye,
                'bracket_type': node.bracket_type,
                'parent_position': node.parent_node.position if node.parent_node else None
            }
            
            rounds_data[node.round_number]['matches'].append(match_data)
        
        # Convert to sorted list
        rounds_list = sorted(rounds_data.values(), key=lambda r: r['round_number'])
        
        return {
            'bracket': {
                'id': bracket.id,
                'tournament_id': bracket.tournament_id,
                'format': bracket.format,
                'seeding_method': bracket.seeding_method,
                'total_rounds': bracket.total_rounds,
                'total_matches': bracket.total_matches,
                'is_finalized': bracket.is_finalized,
                'bracket_structure': bracket.bracket_structure
            },
            'rounds': rounds_list
        }
