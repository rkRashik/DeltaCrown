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

logger = logging.getLogger(__name__)


class BracketService:
    """
    Service for bracket generation, seeding, and progression.
    
    Implements algorithms for single elimination, double elimination, and round robin
    bracket generation with support for multiple seeding strategies.
    """
    
    # Participant data structure: {"id": str, "name": str, "seed": int}
    
    @staticmethod
    @transaction.atomic
    def generate_bracket(
        tournament_id: int,
        bracket_format: Optional[str] = None,
        seeding_method: Optional[str] = None,
        participants: Optional[List[Dict]] = None
    ) -> Bracket:
        """
        Main entry point for bracket generation.
        
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
                # Delete old bracket nodes and bracket
                BracketNode.objects.filter(bracket=old_bracket).delete()
                old_bracket.delete()
        
        # Generate bracket based on format
        if bracket_format == Bracket.SINGLE_ELIMINATION:
            bracket = BracketService._generate_single_elimination(tournament, seeded_participants, seeding_method)
        elif bracket_format == Bracket.DOUBLE_ELIMINATION:
            bracket = BracketService._generate_double_elimination(tournament, seeded_participants, seeding_method)
        elif bracket_format == Bracket.ROUND_ROBIN:
            bracket = BracketService._generate_round_robin(tournament, seeded_participants, seeding_method)
        else:
            raise ValidationError(
                f"Bracket format '{bracket_format}' not yet implemented. "
                f"Supported formats: single-elimination, double-elimination, round-robin"
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
        
        participants = []
        for reg in registrations:
            # Determine participant ID and name
            if reg.team_id:
                # Team-based tournament
                participant_id = reg.team_id  # Store as integer
                # Fetch team name from apps.teams (to be implemented)
                # For now, use generic name
                participant_name = f"Team #{reg.team_id}"
            else:
                # Solo tournament
                participant_id = reg.user_id  # Store as integer
                participant_name = reg.user.username if reg.user else f"User #{reg.user_id}"
            
            participants.append({
                'id': participant_id,
                'name': participant_name,
                'seed': reg.seed if reg.seed else len(participants) + 1,
                'registration_id': reg.id
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
                participant1_name=participant1['name'] if participant1 else None,
                participant2_id=participant2['id'] if participant2 else None,
                participant2_name=participant2['name'] if participant2 else None,
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
        
        Algorithm:
        1. Create winners bracket (same as single elimination)
        2. Create losers bracket (losers from winners bracket)
        3. Create grand finals node
        4. Link brackets with proper progression
        
        Args:
            tournament: Tournament instance
            participants: Seeded participant list
            seeding_method: Seeding method used
        
        Returns:
            Created Bracket instance with winners and losers brackets
        
        Note:
            This is a simplified implementation. Full double elimination requires
            complex loser bracket pairing logic.
        """
        # TODO: Implement full double elimination logic
        # For now, raise NotImplementedError
        raise NotImplementedError(
            "Double elimination bracket generation will be implemented in next iteration. "
            "Current implementation supports single-elimination and round-robin formats."
        )
    
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
                status=Match.SCHEDULED,
                bracket_node=node  # Link to bracket node
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
        if match.status != Match.COMPLETED:
            raise ValidationError(
                f"Cannot update bracket for match {match.id}: "
                f"Match status is '{match.status}', expected 'completed'"
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
        
        parent_node.save(update_fields=['participant1_id', 'participant1_name', 
                                       'participant2_id', 'participant2_name'])
        updated_node_ids.append(parent_node.id)
        
        # Check if parent node is ready for match creation
        if parent_node.has_both_participants and not parent_node.match:
            # Create match for parent node
            parent_match = Match.objects.create(
                tournament=parent_node.bracket.tournament,
                round_number=parent_node.round_number,
                match_number=parent_node.match_number_in_round,
                participant1_id=parent_node.participant1_id,
                participant2_id=parent_node.participant2_id,
                status=Match.SCHEDULED,
                bracket_node=parent_node
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
            # Delete all matches linked to bracket nodes
            Match.objects.filter(bracket_node__bracket=bracket).delete()
            
            # Delete all bracket nodes
            BracketNode.objects.filter(bracket=bracket).delete()
            
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
