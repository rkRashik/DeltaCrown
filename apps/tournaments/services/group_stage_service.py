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
        if tournament.format not in ['group-stage', 'group-playoff']:
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
                team=registration.team if tournament.participation_type == 'team' else None,
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
        
        # Game-specific stat updates
        match_data = match.result_data or {}
        
        if game_slug in ['efootball', 'fc-mobile', 'fifa']:
            # Goals-based games
            standing1.goals_for += match_data.get('participant1_score', 0)
            standing1.goals_against += match_data.get('participant2_score', 0)
            standing1.goal_difference = standing1.goals_for - standing1.goals_against
            
            standing2.goals_for += match_data.get('participant2_score', 0)
            standing2.goals_against += match_data.get('participant1_score', 0)
            standing2.goal_difference = standing2.goals_for - standing2.goals_against
        
        elif game_slug in ['valorant', 'cs2']:
            # Rounds-based games
            standing1.rounds_won += match_data.get('participant1_rounds', 0)
            standing1.rounds_lost += match_data.get('participant2_rounds', 0)
            standing1.round_difference = standing1.rounds_won - standing1.rounds_lost
            
            standing2.rounds_won += match_data.get('participant2_rounds', 0)
            standing2.rounds_lost += match_data.get('participant1_rounds', 0)
            standing2.round_difference = standing2.rounds_won - standing2.rounds_lost
        
        elif game_slug in ['pubg-mobile', 'free-fire']:
            # Battle Royale games
            standing1.total_kills += match_data.get('participant1_kills', 0)
            standing1.placement_points += Decimal(str(match_data.get('participant1_placement_points', 0)))
            
            standing2.total_kills += match_data.get('participant2_kills', 0)
            standing2.placement_points += Decimal(str(match_data.get('participant2_placement_points', 0)))
        
        elif game_slug == 'mobile-legends':
            # MOBA game
            standing1.total_kills += match_data.get('participant1_kills', 0)
            standing1.total_deaths += match_data.get('participant1_deaths', 0)
            standing1.total_assists += match_data.get('participant1_assists', 0)
            standing1.kda_ratio = standing1.calculate_kda()
            
            standing2.total_kills += match_data.get('participant2_kills', 0)
            standing2.total_deaths += match_data.get('participant2_deaths', 0)
            standing2.total_assists += match_data.get('participant2_assists', 0)
            standing2.kda_ratio = standing2.calculate_kda()
        
        elif game_slug == 'call-of-duty-mobile':
            # COD Mobile
            standing1.total_kills += match_data.get('participant1_eliminations', 0)
            standing1.total_deaths += match_data.get('participant1_deaths', 0)
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
        """Apply tiebreaker rules and assign ranks."""
        # Primary sort by points
        if game_slug in ['efootball', 'fc-mobile', 'fifa']:
            standings.sort(key=lambda s: (
                -s.points,
                -s.goal_difference,
                -s.goals_for,
                -s.matches_won
            ))
        elif game_slug in ['valorant', 'cs2']:
            standings.sort(key=lambda s: (
                -s.points,
                -s.round_difference,
                -s.rounds_won,
                -s.matches_won
            ))
        elif game_slug in ['pubg-mobile', 'free-fire']:
            standings.sort(key=lambda s: (
                -s.points,
                -s.placement_points,
                -s.total_kills
            ))
        elif game_slug == 'mobile-legends':
            standings.sort(key=lambda s: (
                -s.points,
                -s.kda_ratio,
                -s.total_kills
            ))
        elif game_slug == 'call-of-duty-mobile':
            standings.sort(key=lambda s: (
                -s.points,
                -s.total_score,
                -s.total_kills,
                s.total_deaths  # Fewer deaths better
            ))
        else:
            # Default: points, then wins
            standings.sort(key=lambda s: (-s.points, -s.matches_won))
        
        # Assign ranks
        for rank, standing in enumerate(standings, start=1):
            standing.update_rank(rank)
