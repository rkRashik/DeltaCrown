"""
WinnerDeterminationService - Business logic for tournament winner determination (Module 5.1)

Source Documents:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md (Module 5.1: Winner Determination)
- Documents/ExecutionPlan/Modules/MODULE_5.1_EXECUTION_CHECKLIST.md (14-section implementation guide)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: BracketService winner progression)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 3: Tournament status COMPLETED → CONCLUDED)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer Pattern, ADR-007: WebSocket)

Architecture Decisions:
- ADR-001: Service layer pattern - All business logic in services
- ADR-007: WebSocket integration for tournament_completed event

Winner Determination Flow:
1. Verify all matches COMPLETED (no pending/disputed)
2. Traverse bracket tree to identify winner
3. Apply tie-breaking rules if needed (head-to-head → score diff → seed → time)
4. Detect forfeit chains and flag for review
5. Create TournamentResult with audit trail
6. Update Tournament.status → COMPLETED (atomic)
7. Broadcast tournament_completed via WebSocket (on_commit)

Service Responsibilities:
- Tournament completion verification
- Winner/runner-up/third-place determination
- Tie-breaking rule application (strict order)
- Forfeit chain detection and review flagging
- Audit trail generation (rules_applied JSONB)
- Atomic transaction management
- WebSocket event broadcasting
- Idempotency (single TournamentResult per tournament)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet, F, Count, Prefetch, Max

from apps.tournaments.models import (
    Tournament,
    Match,
    Bracket,
    Registration,
    TournamentResult,
)

# Module 5.1: WebSocket broadcasting for tournament_completed event
from apps.tournaments.realtime.utils import broadcast_tournament_event

logger = logging.getLogger(__name__)


class WinnerDeterminationService:
    """
    Service for determining tournament winners and creating audit records.
    
    Implements automated winner determination with:
    - Completion verification (all matches resolved)
    - Dispute guards (block if any active disputes)
    - Tie-breaking rules (head-to-head → score diff → seed → time)
    - Forfeit chain detection (requires_review flag)
    - Audit trail generation (rules_applied JSONB)
    - Atomic transactions (status update + result creation)
    - WebSocket broadcasting (tournament_completed event)
    - Idempotency (return existing result if present)
    
    User Decisions (locked in):
    1. Status transition: Automatic COMPLETED within transaction
    2. Tie-breaker order: Head-to-head → Score diff → Seed → Time → ValidationError
    3. Runner-up/3rd place: Finals loser / 3rd place match winner (or tie-breaker)
    4. Forfeit chain: Valid win, determination_method="forfeit_chain", requires_review=True
    """
    
    def __init__(self, tournament: Tournament, created_by: Optional[Any] = None):
        """
        Initialize service for a specific tournament.
        
        Args:
            tournament: Tournament instance to determine winner for
            created_by: User who triggered determination (nullable)
        """
        self.tournament = tournament
        self.created_by = created_by
        self.audit_steps: List[Dict[str, Any]] = []
    
    # ============================================================================
    # ID Normalization Helpers (private)
    # ============================================================================
    #
    # These helpers provide consistent FK/ID handling throughout the service.
    # Django models use IntegerFields for FK IDs (e.g., Match.winner_id) but
    # tests often work with Registration objects. These helpers normalize both.
    #
    # **Usage in Service Code:**
    #   - Use _rid(x) when x MUST be an ID (raises ValueError if None)
    #   - Use _opt_rid(x) when x CAN be None (returns None if None)
    #   - Always use for winner/runner_up/third_place comparisons
    #   - Always use when querying Match.winner_id, participant1_id, etc.
    #
    # **Usage in Tests/Fixtures:**
    #   - When creating Match objects: always use .id explicitly
    #     ✅ Match.objects.create(winner_id=reg.id, ...)
    #     ❌ Match.objects.create(winner=reg, ...)  # No FK field
    #   - When comparing placements: use _rid() in assertions
    #     ✅ assert service._rid(result.winner) == reg_a.id
    #     ❌ assert result.winner == reg_a  # FK comparison fails
    #
    # **Why Needed:**
    #   Match model uses IntegerFields (winner_id, participant1_id, etc.) for
    #   performance and to avoid N+1 queries. Tests create Registration objects
    #   but service must work with IDs. These helpers bridge the gap.
    #
    # **Examples:**
    #   >>> reg = Registration.objects.create(...)
    #   >>> service._rid(reg)         # Returns: 42 (reg.pk)
    #   >>> service._rid(42)          # Returns: 42 (already int)
    #   >>> service._opt_rid(None)    # Returns: None (allows None)
    #   >>> service._rid(None)        # Raises: ValueError
    #
    
    def _rid(self, x) -> int:
        """
        Normalize registration/entity to ID (int). Raises if None.
        
        Args:
            x: Registration object, int ID, or object with .pk attribute
            
        Returns:
            int: Registration ID
            
        Raises:
            ValueError: If x is None (use _opt_rid for nullable fields)
            
        Usage:
            winner_id = self._rid(winner)  # winner can be Registration or int
            Match.objects.filter(winner_id=winner_id)  # Always int query
        """
        if x is None:
            raise ValueError("Cannot normalize None to registration ID")
        return x.pk if hasattr(x, 'pk') else int(x)
    
    def _opt_rid(self, x) -> Optional[int]:
        """
        Normalize registration/entity to ID (int), allowing None.
        
        Args:
            x: Registration object, int ID, object with .pk, or None
            
        Returns:
            int | None: Registration ID or None
            
        Usage:
            third_place_id = self._opt_rid(third_place)  # Can be None
            result = TournamentResult.objects.create(
                third_place_id=third_place_id  # None is OK
            )
        """
        if x is None:
            return None
        return x.pk if hasattr(x, 'pk') else int(x)
        
    def determine_winner(self) -> TournamentResult:
        """
        Determine tournament winner and create result record.
        
        This is the main entry point for winner determination. It performs:
        1. Idempotency check (return existing result if present)
        2. Completion verification (all matches resolved, no disputes)
        3. Winner/runner-up/third-place identification
        4. Tie-breaking if needed
        5. Forfeit chain detection
        6. Result creation with audit trail
        7. Tournament status update (→ COMPLETED)
        8. WebSocket broadcast (tournament_completed event)
        
        Returns:
            TournamentResult: Created or existing result record
            
        Raises:
            ValidationError: If tournament incomplete, has disputes, or tie-breaker fails
            
        Example:
            >>> service = WinnerDeterminationService(tournament, user)
            >>> result = service.determine_winner()
            >>> print(result.winner.team.name)
            'Champions United'
        """
        # Idempotency: Return existing result if already determined
        existing_result = TournamentResult.objects.filter(
            tournament=self.tournament,
            is_deleted=False
        ).first()
        
        if existing_result:
            logger.info(
                f"Tournament {self.tournament.id} already has result "
                f"(winner: {existing_result.winner_id})"
            )
            return existing_result
        
        # Verify tournament completion (all matches resolved, no disputes)
        self.verify_tournament_completion()
        
        # Use atomic transaction for status update + result creation
        with transaction.atomic():
            # Determine winner, runner-up, third place
            winner_reg, runner_up_reg, third_place_reg, determination_method = (
                self._determine_placements()
            )
            
            # Detect forfeit chains
            requires_review = self._detect_forfeit_chain(winner_reg)
            if requires_review:
                determination_method = 'forfeit_chain'
                self.audit_steps.append({
                    'rule': 'forfeit_chain_detection',
                    'data': {
                        'winner_id': winner_reg.id,
                        'chain_summary': 'Winner advanced via forfeit chain'
                    },
                    'outcome': 'requires_review_flagged'
                })
            
            # Create TournamentResult with audit trail
            result = TournamentResult.objects.create(
                tournament=self.tournament,
                winner=winner_reg,
                runner_up=runner_up_reg,
                third_place=third_place_reg,
                final_bracket=self._get_final_bracket(),
                determination_method=determination_method,
                rules_applied=self.create_audit_log(),
                requires_review=requires_review,
                created_by=self.created_by
            )
            
            # Update tournament status to COMPLETED
            self.tournament.status = Tournament.COMPLETED
            self.tournament.save(update_fields=['status', 'updated_at'])
            
            logger.info(
                f"Tournament {self.tournament.id} winner determined: "
                f"{winner_reg.id} (method: {determination_method}, "
                f"requires_review: {requires_review})"
            )
            
            # Broadcast tournament_completed event (after commit)
            transaction.on_commit(lambda: self._broadcast_completion(result))
            
            return result
    
    def verify_tournament_completion(self) -> None:
        """
        Verify tournament is ready for winner determination.
        
        Checks:
        1. All bracket matches are COMPLETED (or resolved/forfeit)
        2. No matches are in DISPUTED or PENDING_RESULT state
        3. At least one match exists (sanity check)
        
        Raises:
            ValidationError: If tournament incomplete or has pending disputes
            
        Side Effects:
            Adds verification steps to audit trail
        """
        # Get all matches for this tournament
        matches = Match.objects.filter(
            bracket__tournament=self.tournament,
            is_deleted=False
        ).select_related('bracket')
        
        if not matches.exists():
            self.audit_steps.append({
                'rule': 'completion_verification',
                'data': {'match_count': 0},
                'outcome': 'no_matches_found'
            })
            raise ValidationError(
                f"Tournament {self.tournament.id} has no matches - cannot determine winner"
            )
        
        # Check for active disputes FIRST (including semi-final disputes)
        # DISPUTED matches should be caught here, not as "incomplete"
        disputed_matches = matches.filter(state=Match.DISPUTED)
        
        if disputed_matches.exists():
            disputed_ids = list(disputed_matches.values_list('id', flat=True))
            self.audit_steps.append({
                'rule': 'dispute_guard',
                'data': {
                    'disputed_matches': disputed_ids,
                    'disputed_count': len(disputed_ids)
                },
                'outcome': 'blocked_by_dispute'
            })
            raise ValidationError(
                f"Tournament {self.tournament.id} has {len(disputed_ids)} disputed matches - "
                f"cannot determine winner until disputes resolved"
            )
        
        # Check for incomplete matches (excluding DISPUTED, which was checked above)
        incomplete_matches = matches.exclude(
            state__in=[Match.COMPLETED, Match.FORFEIT, Match.DISPUTED]
        )
        
        if incomplete_matches.exists():
            incomplete_ids = list(incomplete_matches.values_list('id', flat=True))
            self.audit_steps.append({
                'rule': 'completion_verification',
                'data': {
                    'total_matches': matches.count(),
                    'incomplete_matches': incomplete_ids,
                    'incomplete_count': len(incomplete_ids)
                },
                'outcome': 'incomplete_matches_found'
            })
            raise ValidationError(
                f"Tournament {self.tournament.id} has {len(incomplete_ids)} incomplete matches - "
                f"cannot determine winner"
            )
        
        # Verification passed
        self.audit_steps.append({
            'rule': 'completion_verification',
            'data': {
                'total_matches': matches.count(),
                'completed_matches': matches.filter(state=Match.COMPLETED).count(),
                'forfeit_matches': matches.filter(state=Match.FORFEIT).count()
            },
            'outcome': 'verified_complete'
        })
    
    def apply_tiebreaker_rules(
        self,
        tied_registrations: List[Registration]
    ) -> Registration:
        """
        Apply tie-breaking rules to determine winner among tied participants.
        
        Tie-breaker order (strict):
        1. Head-to-head record (if direct match exists)
        2. Score differential (exclude forfeits)
        3. Seed ranking (lower seed wins)
        4. Earliest valid completion time
        5. ValidationError (manual resolution required)
        
        Args:
            tied_registrations: List of Registration instances tied for placement
            
        Returns:
            Registration: Winner after tie-breaking
            
        Raises:
            ValidationError: If all tie-breakers fail (unresolved tie)
            
        Side Effects:
            Adds tie-breaker steps to audit trail
        """
        if len(tied_registrations) < 2:
            return tied_registrations[0]
        
        self.audit_steps.append({
            'rule': 'tiebreaker_initiated',
            'data': {
                'tied_count': len(tied_registrations),
                'registration_ids': [r.id for r in tied_registrations]
            },
            'outcome': 'applying_tiebreaker_rules'
        })
        
        # Rule 1: Head-to-head record
        winner = self._apply_head_to_head(tied_registrations)
        if winner:
            return winner
        
        # Rule 2: Score differential (exclude forfeits)
        winner = self._apply_score_differential(tied_registrations)
        if winner:
            return winner
        
        # Rule 3: Seed ranking (lower seed wins)
        winner = self._apply_seed_ranking(tied_registrations)
        if winner:
            return winner
        
        # Rule 4: Earliest completion time
        winner = self._apply_completion_time(tied_registrations)
        if winner:
            return winner
        
        # Rule 5: No tie-breaker resolved - raise error
        self.audit_steps.append({
            'rule': 'tiebreaker_unresolved',
            'data': {
                'tied_registrations': [r.id for r in tied_registrations],
                'all_rules_failed': True
            },
            'outcome': 'manual_resolution_required'
        })
        raise ValidationError(
            f"Tie-breaker unresolved for tournament {self.tournament.id} - "
            f"manual resolution required"
        )
    
    def create_audit_log(self) -> Dict[str, Any]:
        """
        Create structured audit log from accumulated steps.
        
        Returns:
            Dict with audit trail data:
            - timestamp: When determination occurred
            - tournament_id: Tournament ID
            - steps: Ordered list of determination steps
            - total_steps: Count of steps
            
        Example:
            {
                'timestamp': '2025-11-09T10:30:45Z',
                'tournament_id': 123,
                'steps': [
                    {
                        'rule': 'completion_verification',
                        'data': {'total_matches': 15, 'completed_matches': 15},
                        'outcome': 'verified_complete'
                    },
                    {
                        'rule': 'winner_identification',
                        'data': {'winner_id': 45, 'method': 'normal'},
                        'outcome': 'winner_identified'
                    }
                ],
                'total_steps': 2
            }
        """
        return {
            'timestamp': timezone.now().isoformat(),
            'tournament_id': self.tournament.id,
            'steps': self.audit_steps,
            'total_steps': len(self.audit_steps)
        }
    
    # ============================================================================
    # Private Helper Methods
    # ============================================================================
    
    def _determine_placements(self) -> Tuple[Registration, Optional[Registration], Optional[Registration], str]:
        """
        Determine winner, runner-up, and third place.
        
        Returns:
            Tuple of (winner, runner_up, third_place, determination_method)
        """
        # Get final bracket (highest round)
        final_bracket = self._get_final_bracket()
        
        if not final_bracket:
            raise ValidationError(
                f"Tournament {self.tournament.id} has no brackets - cannot determine winner"
            )
        
        # Get finals match (highest round, match 1)
        finals_match = Match.objects.filter(
            bracket=final_bracket,
            is_deleted=False
        ).order_by('-round_number', 'match_number').first()
        
        if not finals_match:
            raise ValidationError(
                f"Tournament {self.tournament.id} has no finals match - cannot determine winner"
            )
        
        # Winner is the finals winner (winner_id is a Registration ID)
        if not finals_match.winner_id:
            raise ValidationError(
                f"Finals match {finals_match.id} has no winner - cannot determine tournament winner"
            )
        
        # Fetch winner Registration object
        winner_reg = Registration.objects.filter(
            id=finals_match.winner_id,
            tournament=self.tournament
        ).first()
        
        if not winner_reg:
            raise ValidationError(
                f"Winner registration {finals_match.winner_id} not found for tournament {self.tournament.id}"
            )
        
        self.audit_steps.append({
            'rule': 'winner_identification',
            'data': {
                'winner_id': winner_reg.id,
                'finals_match_id': finals_match.id,
                'bracket_id': final_bracket.id
            },
            'outcome': 'winner_identified'
        })
        
        # Runner-up is the finals loser (determine from participant IDs)
        loser_id = finals_match.loser_id or (
            finals_match.participant2_id if finals_match.winner_id == finals_match.participant1_id
            else finals_match.participant1_id
        )
        
        runner_up_reg = Registration.objects.filter(
            id=loser_id,
            tournament=self.tournament
        ).first() if loser_id else None
        
        # Third place: look for 3rd place match, or use semi-final losers with tie-breaker
        third_place_reg = self._determine_third_place(final_bracket, winner_reg, runner_up_reg)
        
        determination_method = 'normal'
        
        return winner_reg, runner_up_reg, third_place_reg, determination_method
    
    def _get_final_bracket(self) -> Optional[Bracket]:
        """Get the bracket for this tournament (OneToOne relationship)."""
        try:
            return self.tournament.bracket
        except Bracket.DoesNotExist:
            return None
    
    def _determine_third_place(
        self,
        final_bracket: Bracket,
        winner: Registration,
        runner_up: Registration
    ) -> Optional[Registration]:
        """
        Determine third place finisher.
        
        Strategy:
        1. Look for explicit 3rd place match
        2. If not found, identify semi-final losers
        3. Apply tie-breaker if multiple semi-final losers
        """
        # Get the highest round number (finals)
        highest_round = Match.objects.filter(
            bracket=final_bracket,
            is_deleted=False
        ).aggregate(Max('round_number'))['round_number__max']
        
        if not highest_round:
            return None
        
        # Check for 3rd place match (one round before finals)
        third_place_match = Match.objects.filter(
            bracket=final_bracket,
            is_deleted=False,
            round_number=highest_round - 1
        ).exclude(
            Q(winner_id=winner.id) | Q(winner_id=runner_up.id)
        ).order_by('-round_number').first()
        
        if third_place_match and third_place_match.winner_id:
            # Find which registration this winner_id belongs to
            third_place = Registration.objects.filter(
                tournament=self.tournament,
                id=third_place_match.winner_id
            ).first()
            
            if third_place:
                self.audit_steps.append({
                    'rule': 'third_place_identification',
                    'data': {
                        'third_place_id': third_place.id,
                        'match_id': third_place_match.id,
                        'method': '3rd_place_match'
                    },
                    'outcome': 'third_place_identified'
                })
                return third_place
        
        # Find semi-final losers (participants who lost to finalists)
        # Use IDs for all comparisons
        winner_id = self._rid(winner)
        runner_up_id = self._rid(runner_up)
        
        semi_final_losers = []
        semi_finals = Match.objects.filter(
            bracket=final_bracket,
            is_deleted=False,
            winner_id__in=[winner_id, runner_up_id]
        )
        
        for match in semi_finals:
            # Determine loser ID from participant IDs
            loser_id = match.loser_id or (
                match.participant2_id if match.winner_id == match.participant1_id
                else match.participant1_id
            )
            
            # Exclude winner and runner_up from losers list
            if loser_id and loser_id not in [winner_id, runner_up_id]:
                loser_reg = Registration.objects.filter(
                    id=loser_id,
                    tournament=self.tournament
                ).first()
                if loser_reg:
                    semi_final_losers.append(loser_reg)
        
        if not semi_final_losers:
            self.audit_steps.append({
                'rule': 'third_place_identification',
                'data': {'method': 'no_semi_finals_found'},
                'outcome': 'third_place_null'
            })
            return None
        
        if len(semi_final_losers) == 1:
            self.audit_steps.append({
                'rule': 'third_place_identification',
                'data': {
                    'third_place_id': semi_final_losers[0].id,
                    'method': 'single_semi_final_loser'
                },
                'outcome': 'third_place_identified'
            })
            return semi_final_losers[0]
        
        # Multiple semi-final losers: apply tie-breaker
        try:
            third_place = self.apply_tiebreaker_rules(semi_final_losers)
            self.audit_steps.append({
                'rule': 'third_place_identification',
                'data': {
                    'third_place_id': third_place.id,
                    'method': 'tiebreaker_applied',
                    'tied_count': len(semi_final_losers)
                },
                'outcome': 'third_place_identified'
            })
            return third_place
        except ValidationError:
            # Tie-breaker failed - return None
            self.audit_steps.append({
                'rule': 'third_place_identification',
                'data': {'method': 'tiebreaker_failed'},
                'outcome': 'third_place_null'
            })
            return None
    
    def _detect_forfeit_chain(self, winner: Registration) -> bool:
        """
        Detect if winner advanced via forfeit chain.
        
        Returns:
            True if winner won via forfeit chain (requires review)
        """
        # Get all matches where winner participated
        winner_matches = Match.objects.filter(
            Q(participant1_id=winner.id) | Q(participant2_id=winner.id),
            bracket__tournament=self.tournament,
            is_deleted=False,
            winner_id=winner.id
        )
        
        # Check if any wins were via forfeit
        forfeit_wins = winner_matches.filter(state=Match.FORFEIT).count()
        total_wins = winner_matches.count()
        
        # If 50% or more wins via forfeit, flag for review
        if total_wins > 0 and forfeit_wins >= (total_wins * 0.5):
            return True
        
        return False
    
    def _apply_head_to_head(self, registrations: List[Registration]) -> Optional[Registration]:
        """Apply head-to-head tie-breaker rule."""
        if len(registrations) != 2:
            # Head-to-head only works for 2 participants
            return None
        
        reg1, reg2 = registrations
        
        # Find direct match between these two
        head_to_head = Match.objects.filter(
            Q(participant1_id=reg1.id, participant2_id=reg2.id) | Q(participant1_id=reg2.id, participant2_id=reg1.id),
            bracket__tournament=self.tournament,
            is_deleted=False,
            state=Match.COMPLETED
        ).first()
        
        if head_to_head and head_to_head.winner_id:
            # winner_id is either reg1.id or reg2.id
            winner_reg = reg1 if head_to_head.winner_id == reg1.id else reg2
            self.audit_steps.append({
                'rule': 'tiebreaker_head_to_head',
                'data': {
                    'winner_id': head_to_head.winner_id,
                    'match_id': head_to_head.id
                },
                'outcome': 'resolved'
            })
            return winner_reg
        
        self.audit_steps.append({
            'rule': 'tiebreaker_head_to_head',
            'data': {'direct_match_found': False},
            'outcome': 'not_applicable'
        })
        return None
    
    def _apply_score_differential(self, registrations: List[Registration]) -> Optional[Registration]:
        """Apply score differential tie-breaker rule (exclude forfeits)."""
        differentials = {}
        
        for reg in registrations:
            # Get all completed matches (exclude forfeits)
            matches = Match.objects.filter(
                Q(participant1_id=reg.id) | Q(participant2_id=reg.id),
                bracket__tournament=self.tournament,
                is_deleted=False,
                state=Match.COMPLETED
            ).exclude(state=Match.FORFEIT)
            
            total_diff = 0
            for match in matches:
                if match.participant1_id == reg.id:
                    total_diff += (match.participant1_score or 0) - (match.participant2_score or 0)
                else:
                    total_diff += (match.participant2_score or 0) - (match.participant1_score or 0)
            
            differentials[reg.id] = total_diff
        
        # Find max differential
        if not differentials:
            return None
        
        max_diff = max(differentials.values())
        winners = [reg for reg in registrations if differentials[reg.id] == max_diff]
        
        if len(winners) == 1:
            self.audit_steps.append({
                'rule': 'tiebreaker_score_differential',
                'data': {
                    'winner_id': winners[0].id,
                    'differentials': differentials,
                    'winning_differential': max_diff
                },
                'outcome': 'resolved'
            })
            return winners[0]
        
        self.audit_steps.append({
            'rule': 'tiebreaker_score_differential',
            'data': {'differentials': differentials, 'still_tied': len(winners)},
            'outcome': 'not_resolved'
        })
        return None
    
    def _apply_seed_ranking(self, registrations: List[Registration]) -> Optional[Registration]:
        """Apply seed ranking tie-breaker rule (lower seed wins)."""
        # Get registrations with seed values
        seeded = [(reg, reg.seed) for reg in registrations if reg.seed is not None]
        
        if not seeded:
            self.audit_steps.append({
                'rule': 'tiebreaker_seed_ranking',
                'data': {'seeded_count': 0},
                'outcome': 'not_applicable'
            })
            return None
        
        # Sort by seed (ascending - lower is better)
        seeded.sort(key=lambda x: x[1])
        
        # Check if there's a unique lowest seed
        if len(seeded) > 1 and seeded[0][1] == seeded[1][1]:
            self.audit_steps.append({
                'rule': 'tiebreaker_seed_ranking',
                'data': {
                    'seeds': {reg.id: seed for reg, seed in seeded},
                    'still_tied': True
                },
                'outcome': 'not_resolved'
            })
            return None
        
        winner = seeded[0][0]
        self.audit_steps.append({
            'rule': 'tiebreaker_seed_ranking',
            'data': {
                'winner_id': winner.id,
                'winning_seed': seeded[0][1],
                'seeds': {reg.id: seed for reg, seed in seeded}
            },
            'outcome': 'resolved'
        })
        return winner
    
    def _apply_completion_time(self, registrations: List[Registration]) -> Optional[Registration]:
        """Apply completion time tie-breaker rule (earliest wins)."""
        completion_times = {}
        
        for reg in registrations:
            # Get earliest match completion time
            earliest_match = Match.objects.filter(
                Q(participant1_id=reg.id) | Q(participant2_id=reg.id),
                bracket__tournament=self.tournament,
                is_deleted=False,
                state=Match.COMPLETED,
                updated_at__isnull=False
            ).order_by('updated_at').first()
            
            if earliest_match:
                completion_times[reg.id] = earliest_match.updated_at
        
        if not completion_times:
            self.audit_steps.append({
                'rule': 'tiebreaker_completion_time',
                'data': {'completion_times_found': 0},
                'outcome': 'not_applicable'
            })
            return None
        
        # Find earliest completion
        earliest_reg_id = min(completion_times, key=completion_times.get)
        winner = next(reg for reg in registrations if reg.id == earliest_reg_id)
        
        # Check if tied
        earliest_time = completion_times[earliest_reg_id]
        tied_count = sum(1 for t in completion_times.values() if t == earliest_time)
        
        if tied_count > 1:
            self.audit_steps.append({
                'rule': 'tiebreaker_completion_time',
                'data': {
                    'completion_times': {k: v.isoformat() for k, v in completion_times.items()},
                    'still_tied': True
                },
                'outcome': 'not_resolved'
            })
            return None
        
        self.audit_steps.append({
            'rule': 'tiebreaker_completion_time',
            'data': {
                'winner_id': winner.id,
                'earliest_time': earliest_time.isoformat(),
                'completion_times': {k: v.isoformat() for k, v in completion_times.items()}
            },
            'outcome': 'resolved'
        })
        return winner
    
    def _broadcast_completion(self, result: TournamentResult) -> None:
        """
        Broadcast tournament_completed event to WebSocket clients using validated schema.
        
        Uses broadcast_tournament_completed() helper which enforces:
        - Privacy: Only registration IDs (no PII leakage)
        - Schema validation: Guaranteed payload structure
        - Condensed rules_applied summary (full audit trail in DB only)
        
        Module 6.1: Updated to use async_to_sync wrapper for async broadcast_tournament_completed.
        
        Event schema (see realtime.utils.broadcast_tournament_completed):
        {
            'type': 'tournament_completed',
            'tournament_id': int,
            'winner_registration_id': int,
            'runner_up_registration_id': int | null,
            'third_place_registration_id': int | null,
            'determination_method': str,
            'requires_review': bool,
            'rules_applied_summary': dict | null,
            'timestamp': str (ISO 8601)
        }
        """
        try:
            from apps.tournaments.realtime.utils import broadcast_tournament_completed
            from asgiref.sync import async_to_sync
            import json
            
            # Condense rules_applied for WebSocket (full audit trail stays in DB)
            rules_summary = None
            if result.rules_applied:
                # rules_applied might be a string (JSON) or already parsed list
                rules_list = result.rules_applied
                if isinstance(rules_list, str):
                    try:
                        rules_list = json.loads(rules_list)
                    except (json.JSONDecodeError, TypeError):
                        rules_list = []
                
                # Extract just the rule names and final outcome for WS
                if isinstance(rules_list, list) and rules_list:
                    rules_summary = {
                        'rules': [step.get('rule') for step in rules_list if isinstance(step, dict) and step.get('rule')],
                        'outcome': rules_list[-1].get('outcome') if isinstance(rules_list[-1], dict) else None
                    }
            
            # Module 6.1: Wrap async broadcast with async_to_sync (sync context)
            async_to_sync(broadcast_tournament_completed)(
                tournament_id=self.tournament.id,
                winner_registration_id=result.winner_id,
                runner_up_registration_id=result.runner_up_id,
                third_place_registration_id=result.third_place_id,
                determination_method=result.determination_method,
                requires_review=result.requires_review,
                rules_applied_summary=rules_summary,
                timestamp=timezone.now().isoformat()
            )
            logger.info(
                f"Broadcast tournament_completed for tournament {self.tournament.id}, "
                f"winner={result.winner_id}, method={result.determination_method}"
            )
        except Exception as e:
            logger.error(
                f"Failed to broadcast tournament_completed for tournament {self.tournament.id}: {e}",
                exc_info=True
            )
