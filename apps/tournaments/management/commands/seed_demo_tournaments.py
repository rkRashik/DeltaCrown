"""
Django Management Command: Seed Demo Tournaments
=================================================

Creates realistic demo tournament data for testing and development.

Usage:
    python manage.py seed_demo_tournaments [--clear]

Options:
    --clear: Delete existing demo tournaments before seeding

What it creates:
1. 20+ demo teams across multiple games
2. GROUP_PLAYOFF tournament (VALORANT Winter Cup) - LIVE
3. SINGLE_ELIMINATION tournament (eFootball Champions) - COMPLETED
4. SINGLE_ELIMINATION tournament (CS2 Elite) - LIVE
5. Registration-open tournament (MLBB Rising Stars)

All using REAL model field names verified from source code.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from apps.tournaments.models import Tournament, Registration, Match, Group, GroupStanding, Game, Bracket, BracketNode
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.tournament_service import TournamentService
from apps.tournaments.services.bracket_service import BracketService
from apps.teams.models import Team
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed realistic demo tournament data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing demo tournaments before seeding',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing demo data...'))
            self._clear_demo_data()
        
        with transaction.atomic():
            self.stdout.write('Creating demo data...\n')
            
            # Create demo teams first
            teams = self._create_demo_teams()
            self.stdout.write(self.style.SUCCESS(f'âœ… Created {len(teams)} demo teams'))
            
            # Create 4 demo tournaments
            t1 = self._create_group_playoff_tournament(teams)
            self.stdout.write(self.style.SUCCESS(f'âœ… Created GROUP_PLAYOFF tournament: {t1.slug}'))
            
            t2 = self._create_completed_single_elim(teams)
            self.stdout.write(self.style.SUCCESS(f'âœ… Created COMPLETED tournament: {t2.slug}'))
            
            t3 = self._create_live_single_elim(teams)
            self.stdout.write(self.style.SUCCESS(f'âœ… Created LIVE tournament: {t3.slug}'))
            
            t4 = self._create_registration_open_tournament(teams)
            self.stdout.write(self.style.SUCCESS(f'âœ… Created REGISTRATION_OPEN tournament: {t4.slug}'))
        
        self.stdout.write(self.style.SUCCESS('\nðŸŽ‰ Demo tournament seeding complete!'))
        self.stdout.write('\nTest URLs:')
        self.stdout.write('  /tournaments/valorant-winter-cup-demo/')
        self.stdout.write('  /tournaments/efootball-champions-demo/')
        self.stdout.write('  /tournaments/cs2-elite-demo/')
        self.stdout.write('  /tournaments/mlbb-rising-demo/')
    
    def _clear_demo_data(self):
        """Delete existing demo data"""
        demo_slugs = [
            'valorant-winter-cup-demo',
            'efootball-champions-demo',
            'cs2-elite-demo',
            'mlbb-rising-demo'
        ]
        Tournament.objects.filter(slug__in=demo_slugs).delete()
        
        # Delete demo teams
        Team.objects.filter(slug__startswith='demo-team-').delete()
    
    def _get_or_create_organizer(self):
        """Get or create demo organizer user"""
        user, created = User.objects.get_or_create(
            username='demo_organizer',
            defaults={
                'email': 'demo@deltacrown.gg',
                'is_active': True
            }
        )
        return user
    
    def _create_demo_teams(self):
        """Create 24 demo teams (8 per game: Valorant, eFootball, CS2)"""
        organizer = self._get_or_create_organizer()
        teams = []
        
        team_names = [
            'Phoenix', 'Titans', 'Dragons', 'Vipers', 'Storm', 'Thunder',
            'Lightning', 'Blaze', 'Frost', 'Shadow', 'Eclipse', 'Nova',
            'Apex', 'Legends', 'Elite', 'Prime', 'Valor', 'Glory',
            'Honor', 'Destiny', 'Fury', 'Rage', 'Chaos', 'Order'
        ]
        
        games = ['valorant', 'efootball', 'cs2']
        
        for i, name in enumerate(team_names):
            game = games[i % 3]
            slug = f'demo-team-{i+1:02d}'
            
            team, created = Team.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f'Demo {name}',
                    'tag': name[:4].upper(),
                    'game': game,
                    'region': 'BD',
                    'description': f'Demo team for {game} tournaments',
                    'is_active': True,
                    'is_public': True,
                }
            )
            teams.append(team)
        
        return teams
    
    def _create_group_playoff_tournament(self, teams):
        """
        Create GROUP_PLAYOFF tournament with:
        - 16 teams in 4 groups
        - Group stage matches
        - Group standings
        - Knockout bracket
        """
        organizer = self._get_or_create_organizer()
        game = Game.objects.get(slug='valorant')
        
        # Get 16 valorant teams
        valorant_teams = [t for t in teams if t.game == 'valorant'][:16]
        
        tournament, created = Tournament.objects.get_or_create(
            slug='valorant-winter-cup-demo',
            defaults={
                'name': 'VALORANT Winter Cup 2025 (Demo)',
                'game': game,
                'format': Tournament.GROUP_PLAYOFF,
                'participation_type': Tournament.TEAM,
                'status': Tournament.LIVE,
                'registration_start': timezone.now() - timedelta(days=30),
                'registration_end': timezone.now() - timedelta(days=15),
                'tournament_start': timezone.now() - timedelta(days=7),
                'tournament_end': timezone.now() + timedelta(days=7),
                'max_participants': 16,
                'has_entry_fee': True,
                'entry_fee_amount': Decimal('500.00'),
                'prize_pool': Decimal('50000.00'),
                'description': 'Demo GROUP_PLAYOFF tournament with group â†’ knockout stages.',
                'config': {
                    'group_stage': {
                        'group_count': 4,
                        'advancement_count': 2
                    }
                },
                'organizer': organizer
            }
        )
        
        if created:
            # Create registrations
            for i, team in enumerate(valorant_teams):
                Registration.objects.create(
                    tournament=tournament,
                    team_id=team.id,
                    status=Registration.CONFIRMED,
                    slot_number=i + 1,
                    checked_in=True,
                    checked_in_at=timezone.now() - timedelta(days=7)
                )
            
            # Create groups manually (service has bugs with team_id)
            groups = []
            group_names = ['Group A', 'Group B', 'Group C', 'Group D']
            for idx, group_name in enumerate(group_names):
                group = Group.objects.create(
                    tournament=tournament,
                    name=group_name,
                    display_order=idx + 1,
                    max_participants=4,
                    advancement_count=2
                )
                groups.append(group)
            
            # Assign teams to groups and create standings
            for i, team in enumerate(valorant_teams):
                group_idx = i // 4
                group = groups[group_idx]
                
                played = random.randint(2, 4)
                won = random.randint(1, played)
                lost = played - won
                
                GroupStanding.objects.create(
                    group=group,
                    team_id=team.id,
                    rank=i % 4 + 1,
                    matches_played=played,
                    matches_won=won,
                    matches_drawn=0,
                    matches_lost=lost,
                    points=Decimal(str(won * 3)),
                    rounds_won=random.randint(won * 8, won * 13),
                    rounds_lost=random.randint(lost * 5, lost * 13)
                )
            
            # Create some group matches
            match_number = 1
            # Preload all teams for name lookup - get from groups we just created
            all_team_ids = []
            for group in groups:
                standings = list(GroupStanding.objects.filter(group=group))
                all_team_ids.extend([s.team_id for s in standings])
            teams_map = {t.id: t for t in Team.objects.filter(id__in=all_team_ids)}
            
            for group in groups:
                standings = list(GroupStanding.objects.filter(group=group))
                team_ids = [s.team_id for s in standings]
                
                # Create 2-3 matches per group
                for i in range(min(3, len(team_ids) - 1)):
                    if i + 1 < len(team_ids):
                        # Randomly pick match state
                        is_completed = random.random() < 0.4
                        is_live = not is_completed and random.random() < 0.3
                        
                        if is_completed:
                            state = Match.COMPLETED
                            p1_score = random.randint(10, 13)
                            p2_score = random.randint(5, p1_score - 1)  
                            winner = team_ids[i]  # p1 always wins
                            loser = team_ids[i + 1]
                        elif is_live:
                            state = Match.LIVE
                            p1_score = random.randint(0, 8)
                            p2_score = random.randint(0, 8)
                            winner = None
                            loser = None
                        else:
                            state = Match.SCHEDULED
                            p1_score = 0
                            p2_score = 0
                            winner = None
                            loser = None
                        
                        Match.objects.create(
                            tournament=tournament,
                            round_number=1,
                            match_number=match_number,
                            participant1_id=team_ids[i],
                            participant1_name=teams_map[team_ids[i]].name,
                            participant2_id=team_ids[i + 1],
                            participant2_name=teams_map[team_ids[i + 1]].name,
                            participant1_score=p1_score,
                            participant2_score=p2_score,
                            state=state,
                            winner_id=winner,
                            loser_id=loser,
                            scheduled_time=timezone.now() - timedelta(hours=random.randint(1, 48))
                        )
                        match_number += 1
            
            # Standings already created with manual data above
        
        return tournament
    
    def _create_completed_single_elim(self, teams):
        """Create completed SINGLE_ELIMINATION tournament"""
        organizer = self._get_or_create_organizer()
        game = Game.objects.get(slug='efootball')
        
        # Get 8 efootball teams
        efootball_teams = [t for t in teams if t.game == 'efootball'][:8]
        
        tournament, created = Tournament.objects.get_or_create(
            slug='efootball-champions-demo',
            defaults={
                'name': 'eFootball Champions 2025 (Demo)',
                'game': game,
                'format': Tournament.SINGLE_ELIM,
                'participation_type': Tournament.TEAM,
                'status': Tournament.COMPLETED,
                'registration_start': timezone.now() - timedelta(days=60),
                'registration_end': timezone.now() - timedelta(days=45),
                'tournament_start': timezone.now() - timedelta(days=30),
                'tournament_end': timezone.now() - timedelta(days=23),
                'max_participants': 8,
                'has_entry_fee': True,
                'entry_fee_amount': Decimal('200.00'),
                'prize_pool': Decimal('25000.00'),
                'description': 'Demo completed tournament.',
                'config': {},
                'organizer': organizer
            }
        )
        
        if created:
            # Create registrations
            for i, team in enumerate(efootball_teams):
                Registration.objects.create(
                    tournament=tournament,
                    team_id=team.id,
                    status=Registration.CONFIRMED,
                    slot_number=i + 1
                )
            
            # Create bracket matches (8 teams = 7 matches: 4 QF + 2 SF + 1 F)
            team_ids = [t.id for t in efootball_teams]
            teams_map = {t.id: t for t in efootball_teams}
            
            # Quarterfinals (round 1)
            qf_winners = []
            for i in range(4):
                p1 = team_ids[i * 2]
                p2 = team_ids[i * 2 + 1]
                winner = p1 if random.random() < 0.5 else p2
                qf_winners.append(winner)
                
                Match.objects.create(
                    tournament=tournament,
                    round_number=1,
                    match_number=i + 1,
                    participant1_id=p1,
                    participant1_name=teams_map[p1].name,
                    participant2_id=p2,
                    participant2_name=teams_map[p2].name,
                    participant1_score=3 if winner == p1 else random.randint(0, 2),
                    participant2_score=3 if winner == p2 else random.randint(0, 2),
                    state=Match.COMPLETED,
                    winner_id=winner,
                    loser_id=p2 if winner == p1 else p1,
                    completed_at=timezone.now() - timedelta(days=27)
                )
            
            # Semifinals (round 2)
            sf_winners = []
            for i in range(2):
                p1 = qf_winners[i * 2]
                p2 = qf_winners[i * 2 + 1]
                winner = p1 if random.random() < 0.5 else p2
                sf_winners.append(winner)
                
                Match.objects.create(
                    tournament=tournament,
                    round_number=2,
                    match_number=i + 1,
                    participant1_id=p1,
                    participant1_name=teams_map[p1].name,
                    participant2_id=p2,
                    participant2_name=teams_map[p2].name,
                    participant1_score=3 if winner == p1 else random.randint(0, 2),
                    participant2_score=3 if winner == p2 else random.randint(0, 2),
                    state=Match.COMPLETED,
                    winner_id=winner,
                    loser_id=p2 if winner == p1 else p1,
                    completed_at=timezone.now() - timedelta(days=25)
                )
            
            # Final (round 3)
            final_winner = sf_winners[0]
            Match.objects.create(
                tournament=tournament,
                round_number=3,
                match_number=1,
                participant1_id=sf_winners[0],
                participant1_name=teams_map[sf_winners[0]].name,
                participant2_id=sf_winners[1],
                participant2_name=teams_map[sf_winners[1]].name,
                participant1_score=3,
                participant2_score=1,
                state=Match.COMPLETED,
                winner_id=final_winner,
                loser_id=sf_winners[1],
                completed_at=timezone.now() - timedelta(days=24)
            )
            
            # Generate bracket from existing matches
            self._generate_bracket_from_matches(tournament, efootball_teams)
        
        return tournament
    
    def _create_live_single_elim(self, teams):
        """Create live SINGLE_ELIMINATION tournament"""
        organizer = self._get_or_create_organizer()
        game = Game.objects.get(slug='cs2')
        
        # Get 8 CS2 teams
        cs2_teams = [t for t in teams if t.game == 'cs2'][:8]
        
        tournament, created = Tournament.objects.get_or_create(
            slug='cs2-elite-demo',
            defaults={
                'name': 'CS2 Elite Showdown (Demo)',
                'game': game,
                'format': Tournament.SINGLE_ELIM,
                'participation_type': Tournament.TEAM,
                'status': Tournament.LIVE,
                'registration_start': timezone.now() - timedelta(days=21),
                'registration_end': timezone.now() - timedelta(days=14),
                'tournament_start': timezone.now() - timedelta(days=3),
                'tournament_end': timezone.now() + timedelta(days=4),
                'max_participants': 8,
                'has_entry_fee': False,
                'prize_pool': Decimal('15000.00'),
                'description': 'Demo live tournament.',
                'config': {},
                'organizer': organizer
            }
        )
        
        if created:
            # Create registrations
            for i, team in enumerate(cs2_teams):
                Registration.objects.create(
                    tournament=tournament,
                    team_id=team.id,
                    status=Registration.CONFIRMED,
                    slot_number=i + 1
                )
            
            # Create matches
            team_ids = [t.id for t in cs2_teams]
            teams_map = {t.id: t for t in cs2_teams}
            
            # Quarterfinals - completed
            qf_winners = []
            for i in range(4):
                p1 = team_ids[i * 2]
                p2 = team_ids[i * 2 + 1]
                winner = p1 if i % 2 == 0 else p2
                qf_winners.append(winner)
                
                Match.objects.create(
                    tournament=tournament,
                    round_number=1,
                    match_number=i + 1,
                    participant1_id=p1,
                    participant1_name=teams_map[p1].name,
                    participant2_id=p2,
                    participant2_name=teams_map[p2].name,
                    participant1_score=16 if winner == p1 else random.randint(8, 14),
                    participant2_score=16 if winner == p2 else random.randint(8, 14),
                    state=Match.COMPLETED,
                    winner_id=winner,
                    loser_id=p2 if winner == p1 else p1,
                    completed_at=timezone.now() - timedelta(hours=12)
                )
            
            # Semifinals - one live, one scheduled
            Match.objects.create(
                tournament=tournament,
                round_number=2,
                match_number=1,
                participant1_id=qf_winners[0],
                participant1_name=teams_map[qf_winners[0]].name,
                participant2_id=qf_winners[1],
                participant2_name=teams_map[qf_winners[1]].name,
                participant1_score=8,
                participant2_score=6,
                state=Match.LIVE,
                scheduled_time=timezone.now() - timedelta(hours=1)
            )
            
            Match.objects.create(
                tournament=tournament,
                round_number=2,
                match_number=2,
                participant1_id=qf_winners[2],
                participant1_name=teams_map[qf_winners[2]].name,
                participant2_id=qf_winners[3],
                participant2_name=teams_map[qf_winners[3]].name,
                participant1_score=0,
                participant2_score=0,
                state=Match.SCHEDULED,
                scheduled_time=timezone.now() + timedelta(hours=3)
            )
            
            # Final - scheduled
            Match.objects.create(
                tournament=tournament,
                round_number=3,
                match_number=1,
                participant1_id=qf_winners[0],
                participant1_name=teams_map[qf_winners[0]].name,
                participant2_id=qf_winners[2],
                participant2_name=teams_map[qf_winners[2]].name,
                participant1_score=0,
                participant2_score=0,
                state=Match.SCHEDULED,
                scheduled_time=timezone.now() + timedelta(days=2)
            )
            
            # Generate bracket structure from matches
            self._generate_bracket_from_matches(tournament, cs2_teams)
        
        return tournament
    
    def _create_registration_open_tournament(self, teams):
        """Create registration-open tournament"""
        organizer = self._get_or_create_organizer()
        
        # Use mlbb game
        try:
            game = Game.objects.get(slug='mlbb')
        except Game.DoesNotExist:
            # Fallback to valorant if mlbb doesn't exist
            game = Game.objects.get(slug='valorant')
        
        # Get first 12 teams (any game)
        some_teams = teams[:12]
        
        tournament, created = Tournament.objects.get_or_create(
            slug='mlbb-rising-demo',
            defaults={
                'name': 'Mobile Legends Rising Stars (Demo)',
                'game': game,
                'format': Tournament.DOUBLE_ELIM,
                'participation_type': Tournament.TEAM,
                'status': Tournament.REGISTRATION_OPEN,
                'registration_start': timezone.now() - timedelta(days=5),
                'registration_end': timezone.now() + timedelta(days=10),
                'tournament_start': timezone.now() + timedelta(days=15),
                'tournament_end': timezone.now() + timedelta(days=22),
                'max_participants': 32,
                'has_entry_fee': True,
                'entry_fee_amount': Decimal('300.00'),
                'prize_pool': Decimal('35000.00'),
                'description': 'Demo registration-open tournament.',
                'config': {},
                'organizer': organizer
            }
        )
        
        if created:
            # Create some registrations (mix of confirmed and pending)
            for i, team in enumerate(some_teams):
                status = Registration.CONFIRMED if i < 8 else Registration.PENDING
                Registration.objects.create(
                    tournament=tournament,
                    team_id=team.id,
                    status=status,
                    slot_number=i + 1 if status == Registration.CONFIRMED else None
                )
        
        return tournament
    
    def _generate_bracket_from_matches(self, tournament, teams):
        """Generate bracket structure from existing matches"""
        # Create bracket object
        bracket, created = Bracket.objects.get_or_create(
            tournament=tournament,
            defaults={
                'format': 'single-elimination',
                'bracket_structure': {},
                'is_finalized': True,
                'total_rounds': 3,  # For 8 teams: QF, SF, F
                'total_matches': 7,  # 4+2+1
                'seeding_method': 'slot-order'
            }
        )
        
        if not created:
            return bracket
        
        # Get all matches ordered by round and match number
        matches = Match.objects.filter(
            tournament=tournament
        ).order_by('round_number', 'match_number')
        
        # Create bracket nodes for each match
        # For single-elim: each match is a node
        nodes_by_round = {}
        position_counter = 1
        
        for match in matches:
            node = BracketNode.objects.create(
                bracket=bracket,
                round_number=match.round_number,
                match_number_in_round=match.match_number,
                match=match,
                position=position_counter,  # Unique position across all rounds
                participant1_id=match.participant1_id,
                participant1_name=match.participant1_name,
                participant2_id=match.participant2_id,
                participant2_name=match.participant2_name,
            )
            position_counter += 1
            
            if match.round_number not in nodes_by_round:
                nodes_by_round[match.round_number] = []
            nodes_by_round[match.round_number].append(node)
        
        # Link parent-child relationships
        # Each pair of nodes in round N feeds into one node in round N+1
        for round_num in sorted(nodes_by_round.keys())[:-1]:
            current_round = nodes_by_round[round_num]
            next_round = nodes_by_round.get(round_num + 1, [])
            
            for i, parent_node in enumerate(next_round):
                # Two matches from current round feed this parent
                left_child_idx = i * 2
                right_child_idx = i * 2 + 1
                
                if left_child_idx < len(current_round):
                    current_round[left_child_idx].parent_match = parent_node
                    current_round[left_child_idx].save()
                    
                if right_child_idx < len(current_round):
                    current_round[right_child_idx].parent_match = parent_node
                    current_round[right_child_idx].save()
        
        return bracket