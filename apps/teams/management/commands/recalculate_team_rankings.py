# apps/teams/management/commands/recalculate_team_rankings.py
"""
Management command to recalculate team ranking points.

Usage:
    python manage.py recalculate_team_rankings
    python manage.py recalculate_team_rankings --team "Team Name"
    python manage.py recalculate_team_rankings --game valorant
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.teams.models import Team
from apps.teams.services.ranking_service import ranking_service


class Command(BaseCommand):
    help = 'Recalculate team ranking points based on current criteria'

    def add_arguments(self, parser):
        parser.add_argument(
            '--team',
            type=str,
            help='Recalculate points for a specific team (by name)',
        )
        parser.add_argument(
            '--game',
            type=str,
            help='Recalculate points for teams in a specific game',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be calculated without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each team',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting team ranking recalculation...'))
        
        # Get teams to process
        teams_queryset = Team.objects.all()
        
        if options['team']:
            teams_queryset = teams_queryset.filter(name__icontains=options['team'])
            if not teams_queryset.exists():
                raise CommandError(f'No team found matching "{options["team"]}"')
        
        if options['game']:
            teams_queryset = teams_queryset.filter(game__icontains=options['game'])
            if not teams_queryset.exists():
                raise CommandError(f'No teams found for game "{options["game"]}"')
        
        total_teams = teams_queryset.count()
        self.stdout.write(f'Processing {total_teams} teams...')
        
        # Process teams
        teams_updated = 0
        total_points_change = 0
        errors = []
        
        with transaction.atomic():
            for i, team in enumerate(teams_queryset, 1):
                try:
                    if options['dry_run']:
                        # For dry run, just calculate without saving
                        old_points = team.total_points
                        breakdown = ranking_service.get_team_breakdown(team)
                        
                        # Calculate what the new points would be
                        age_points = ranking_service.calculate_team_age_points(team)
                        member_points = ranking_service.calculate_member_points(team)
                        tournament_points = ranking_service.calculate_tournament_points(team)
                        
                        new_calculated = (
                            age_points + member_points + 
                            tournament_points['participation'] + tournament_points['winner'] +
                            tournament_points['runner_up'] + tournament_points['top_4'] +
                            breakdown.achievement_points
                        )
                        new_total = max(0, new_calculated + breakdown.manual_adjustment_points)
                        points_change = new_total - old_points
                        
                        if options['verbose'] or points_change != 0:
                            self.stdout.write(
                                f'{i:3d}. {team.name:<30} {old_points:>6d} → {new_total:>6d} '
                                f'({points_change:+d}) {"[DRY RUN]" if options["dry_run"] else ""}'
                            )
                        
                        if points_change != 0:
                            teams_updated += 1
                            total_points_change += points_change
                    
                    else:
                        # Actually recalculate and save
                        result = ranking_service.recalculate_team_points(
                            team,
                            reason="Management command recalculation"
                        )
                        
                        if result['success']:
                            if result['points_change'] != 0:
                                teams_updated += 1
                                total_points_change += result['points_change']
                                
                                if options['verbose']:
                                    self.stdout.write(
                                        f'{i:3d}. {team.name:<30} '
                                        f'{result["old_total"]:>6d} → {result["new_total"]:>6d} '
                                        f'({result["points_change"]:+d})'
                                    )
                            elif options['verbose']:
                                self.stdout.write(
                                    f'{i:3d}. {team.name:<30} {result["new_total"]:>6d} (no change)'
                                )
                        else:
                            errors.append(f'{team.name}: {result["error"]}')
                            self.stdout.write(
                                self.style.ERROR(f'Error processing {team.name}: {result["error"]}')
                            )
                
                except Exception as e:
                    errors.append(f'{team.name}: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Unexpected error processing {team.name}: {str(e)}')
                    )
            
            # In dry-run mode, rollback the transaction
            if options['dry_run']:
                transaction.set_rollback(True)
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('RECALCULATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'Teams processed: {total_teams}')
        self.stdout.write(f'Teams updated: {teams_updated}')
        self.stdout.write(f'Total points change: {total_points_change:+d}')
        
        if errors:
            self.stdout.write(self.style.WARNING(f'Errors encountered: {len(errors)}'))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nRecalculation completed successfully!'))