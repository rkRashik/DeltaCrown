"""
Advanced Bracket Generation Service

Implements intelligent bracket generation with:
- Seeding algorithms
- Bye handling
- Multiple formats support
- Bracket balancing
"""

import random
from typing import List, Dict, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models import Tournament, Match, Registration, Bracket
from apps.tournaments.models.bracket import BracketNode


class BracketGenerationError(Exception):
    """Raised when bracket generation fails"""
    pass


class BracketGenerator:
    """
    Intelligent bracket generator with advanced features.
    
    Features:
    - Automatic seeding based on player ratings
    - Balanced bracket generation
    - Bye handling for non-power-of-2 participants
    - Multiple format support
    """
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.bracket = None
        
    @transaction.atomic
    def generate(self, seed_method: str = 'random') -> Bracket:
        """
        Generate bracket for tournament.
        
        Args:
            seed_method: 'random', 'rating', 'registration_order'
            
        Returns:
            Created Bracket object
        """
        # Validate tournament state
        self._validate_tournament()
        
        # Get confirmed participants
        participants = self._get_participants()
        
        if len(participants) < 2:
            raise BracketGenerationError("Need at least 2 participants")
        
        # Apply seeding
        seeded_participants = self._apply_seeding(participants, seed_method)
        
        # Generate based on format
        if self.tournament.format == Tournament.SINGLE_ELIM:
            return self._generate_single_elimination(seeded_participants)
        elif self.tournament.format == Tournament.DOUBLE_ELIM:
            return self._generate_double_elimination(seeded_participants)
        elif self.tournament.format == Tournament.ROUND_ROBIN:
            return self._generate_round_robin(seeded_participants)
        elif self.tournament.format == Tournament.SWISS:
            return self._generate_swiss(seeded_participants)
        else:
            raise BracketGenerationError(f"Unsupported format: {self.tournament.format}")
    
    def _validate_tournament(self):
        """Validate tournament is ready for bracket generation"""
        if self.tournament.status not in [Tournament.REGISTRATION_CLOSED, Tournament.CHECK_IN_OPEN]:
            raise BracketGenerationError("Tournament must be in registration_closed or check_in_open state")
        
        if hasattr(self.tournament, 'bracket') and self.tournament.bracket and self.tournament.bracket.is_finalized:
            raise BracketGenerationError("Bracket already generated and finalized")
    
    def _get_participants(self) -> List[Registration]:
        """Get confirmed and checked-in participants"""
        participants = Registration.objects.filter(
            tournament=self.tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        ).select_related('user', 'team')
        
        # If check-in required, only include checked-in participants
        if self.tournament.requires_checkin:
            participants = participants.filter(checked_in=True)
        
        return list(participants)
    
    def _apply_seeding(self, participants: List[Registration], method: str) -> List[Registration]:
        """Apply seeding to participants"""
        if method == 'random':
            random.shuffle(participants)
            return participants
        
        elif method == 'rating':
            # Sort by player/team rating (descending)
            return sorted(participants, key=lambda p: self._get_rating(p), reverse=True)
        
        elif method == 'registration_order':
            # First registered = #1 seed
            return sorted(participants, key=lambda p: p.created_at)
        
        else:
            raise ValueError(f"Unknown seed method: {method}")
    
    def _get_rating(self, registration: Registration) -> float:
        """Get rating for seeding (player or team)"""
        if registration.user_id:
            # Solo tournament - use player rating
            profile = registration.user.profile
            return getattr(profile, 'rating', 1000.0)
        elif registration.team_id:
            # Team tournament - use average team rating
            return getattr(registration.team, 'rating', 1000.0)
        return 1000.0
    
    def _generate_single_elimination(self, participants: List[Registration]) -> Bracket:
        """Generate single elimination bracket"""
        bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=self._calculate_rounds(len(participants)),
            is_finalized=False
        )
        self.bracket = bracket
        
        # Calculate number of byes needed
        next_power_of_2 = 2 ** bracket.total_rounds
        num_byes = next_power_of_2 - len(participants)
        
        # Assign byes to top seeds
        active_participants = participants[num_byes:]
        bye_participants = participants[:num_byes]
        
        # Create round 1 matches
        round_1_winners = list(bye_participants)  # Byes auto-advance
        
        match_number = 1
        for i in range(0, len(active_participants), 2):
            p1 = active_participants[i]
            p2 = active_participants[i + 1] if i + 1 < len(active_participants) else None
            
            match = Match.objects.create(
                tournament=self.tournament,
                bracket=bracket,
                round_number=1,
                match_number=match_number,
                participant1_id=p1.user_id or p1.team_id,
                participant1_name=p1.user.username if p1.user_id else p1.team.name,
                participant2_id=p2.user_id or p2.team_id if p2 else None,
                participant2_name=p2.user.username if p2 and p2.user_id else (p2.team.name if p2 else None),
                state=Match.SCHEDULED,
                scheduled_time=self.tournament.tournament_start
            )
            
            # Create bracket node
            BracketNode.objects.create(
                bracket=bracket,
                match=match,
                round_number=1,
                position=match_number,
                is_bye=p2 is None
            )
            
            match_number += 1
            
            if p2 is None:
                # Bye match - p1 auto-advances
                round_1_winners.append(p1)
        
        # Generate subsequent rounds (empty matches to be filled as tournament progresses)
        self._generate_elimination_rounds(bracket, 2, len(round_1_winners))
        
        bracket.is_finalized = True
        bracket.save()
        
        return bracket
    
    def _generate_double_elimination(self, participants: List[Registration]) -> Bracket:
        """Generate double elimination bracket (winners + losers brackets)"""
        bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.DOUBLE_ELIMINATION,
            total_rounds=self._calculate_rounds(len(participants)) * 2,  # Winners + Losers
            is_finalized=False
        )
        self.bracket = bracket
        
        # Generate winners bracket (same as single elim)
        self._generate_winners_bracket(bracket, participants)
        
        # Generate losers bracket structure
        self._generate_losers_bracket(bracket, len(participants))
        
        bracket.is_finalized = True
        bracket.save()
        
        return bracket
    
    def _generate_round_robin(self, participants: List[Registration]) -> Bracket:
        """Generate round robin bracket (everyone plays everyone)"""
        bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.ROUND_ROBIN,
            total_rounds=len(participants) - 1,
            is_finalized=False
        )
        self.bracket = bracket
        
        # Round robin: generate all possible matchups
        match_number = 1
        for round_num in range(1, len(participants)):
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    p1 = participants[i]
                    p2 = participants[j]
                    
                    Match.objects.create(
                        tournament=self.tournament,
                        bracket=bracket,
                        round_number=round_num,
                        match_number=match_number,
                        participant1_id=p1.user_id or p1.team_id,
                        participant1_name=p1.user.username if p1.user_id else p1.team.name,
                        participant2_id=p2.user_id or p2.team_id,
                        participant2_name=p2.user.username if p2.user_id else p2.team.name,
                        state=Match.SCHEDULED,
                        scheduled_time=self.tournament.tournament_start
                    )
                    
                    match_number += 1
        
        bracket.is_finalized = True
        bracket.save()
        
        return bracket
    
    def _generate_swiss(self, participants: List[Registration]) -> Bracket:
        """Generate Swiss system bracket (initial pairings only)"""
        num_rounds = self._calculate_swiss_rounds(len(participants))
        
        bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SWISS,
            total_rounds=num_rounds,
            is_finalized=False
        )
        self.bracket = bracket
        
        # Swiss round 1: pair top half vs bottom half
        mid = len(participants) // 2
        top_half = participants[:mid]
        bottom_half = participants[mid:]
        
        match_number = 1
        for p1, p2 in zip(top_half, bottom_half):
            Match.objects.create(
                tournament=self.tournament,
                bracket=bracket,
                round_number=1,
                match_number=match_number,
                participant1_id=p1.user_id or p1.team_id,
                participant1_name=p1.user.username if p1.user_id else p1.team.name,
                participant2_id=p2.user_id or p2.team_id,
                participant2_name=p2.user.username if p2.user_id else p2.team.name,
                state=Match.SCHEDULED,
                scheduled_time=self.tournament.tournament_start
            )
            match_number += 1
        
        # Subsequent rounds generated dynamically after each round completes
        
        bracket.is_finalized = True
        bracket.save()
        
        return bracket
    
    def _calculate_rounds(self, num_participants: int) -> int:
        """Calculate number of rounds for elimination bracket"""
        import math
        return math.ceil(math.log2(num_participants))
    
    def _calculate_swiss_rounds(self, num_participants: int) -> int:
        """Calculate optimal Swiss rounds (typically log2(n))"""
        import math
        return max(3, math.ceil(math.log2(num_participants)))
    
    def _generate_elimination_rounds(self, bracket: Bracket, start_round: int, num_matches: int):
        """Generate empty matches for subsequent elimination rounds"""
        current_matches = num_matches
        
        for round_num in range(start_round, bracket.total_rounds + 1):
            current_matches = current_matches // 2
            
            for match_num in range(1, current_matches + 1):
                Match.objects.create(
                    tournament=self.tournament,
                    bracket=bracket,
                    round_number=round_num,
                    match_number=match_num,
                    state=Match.PENDING,
                    # Participants TBD - filled as previous matches complete
                )
    
    def _generate_winners_bracket(self, bracket: Bracket, participants: List[Registration]):
        """Generate winners bracket for double elimination"""
        # Same as single elimination for winners side
        pass  # TODO: Implement
    
    def _generate_losers_bracket(self, bracket: Bracket, num_participants: int):
        """Generate losers bracket structure"""
        # Losers bracket is more complex - alternates feeding from winners bracket
        pass  # TODO: Implement


def generate_bracket_for_tournament(tournament_id: int, seed_method: str = 'random') -> Bracket:
    """
    Convenience function to generate bracket.
    
    Usage:
        bracket = generate_bracket_for_tournament(tournament.id, 'rating')
    """
    tournament = Tournament.objects.get(id=tournament_id)
    generator = BracketGenerator(tournament)
    return generator.generate(seed_method)
