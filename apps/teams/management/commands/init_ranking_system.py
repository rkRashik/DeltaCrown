# apps/teams/management/commands/init_ranking_system.py
"""
Management command to initialize the team ranking system with default criteria.

Usage:
    python manage.py init_ranking_system
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.teams.models import RankingCriteria, Team
from apps.teams.services.ranking_service import ranking_service


class Command(BaseCommand):
    help = 'Initialize team ranking system with default criteria and calculate initial points'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-recalculation',
            action='store_true',
            help='Skip recalculating existing team points',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing Team Ranking System...'))
        
        # Create or get default ranking criteria
        with transaction.atomic():
            criteria, created = RankingCriteria.objects.get_or_create(
                is_active=True,
                defaults={
                    'tournament_participation': 50,
                    'tournament_winner': 500,
                    'tournament_runner_up': 300,
                    'tournament_top_4': 150,
                    'points_per_member': 10,
                    'points_per_month_age': 30,
                    'achievement_points': 100,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS('✅ Created default ranking criteria')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Ranking criteria already exists')
                )

        # Display current criteria
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Current Ranking Criteria:')
        self.stdout.write('='*50)
        self.stdout.write(f'Tournament Participation: {criteria.tournament_participation} points')
        self.stdout.write(f'Tournament Winner: {criteria.tournament_winner} points')
        self.stdout.write(f'Tournament Runner-up: {criteria.tournament_runner_up} points')
        self.stdout.write(f'Tournament Top 4: {criteria.tournament_top_4} points')
        self.stdout.write(f'Per Active Member: {criteria.points_per_member} points')
        self.stdout.write(f'Per Month Age: {criteria.points_per_month_age} points')
        self.stdout.write(f'Achievement Bonus: {criteria.achievement_points} points')

        # Calculate initial points for all teams
        if not options['skip_recalculation']:
            self.stdout.write('\n' + '='*50)
            self.stdout.write('Calculating Initial Team Points...')
            self.stdout.write('='*50)
            
            result = ranking_service.recalculate_all_teams()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Processed {result["teams_processed"]} teams, '
                        f'{result["teams_updated"]} had point changes'
                    )
                )
                
                if result['errors']:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  {len(result["errors"])} errors occurred'
                        )
                    )
                    for error in result['errors'][:5]:
                        self.stdout.write(f'   - {error}')
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to calculate team points')
                )

        # Show top teams
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Top 10 Teams by Points:')
        self.stdout.write('='*50)
        
        top_teams = ranking_service.get_team_rankings(limit=10)
        
        if top_teams:
            for ranking in top_teams:
                team = ranking['team']
                points = ranking['points']
                self.stdout.write(
                    f'{ranking["rank"]:2d}. {team.name:<30} {points:>6d} points '
                    f'({team.game or "No Game"})'
                )
        else:
            self.stdout.write('No teams found.')

        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ Team Ranking System Initialized Successfully!'))
        self.stdout.write('='*50)
        self.stdout.write('Next steps:')
        self.stdout.write('1. Visit Django Admin → Team Ranking Points to manage the system')
        self.stdout.write('2. Use the admin interface to adjust individual team points')
        self.stdout.write('3. Tournament results will automatically update team points')
        self.stdout.write('4. Run "python manage.py recalculate_team_rankings" for bulk updates')
