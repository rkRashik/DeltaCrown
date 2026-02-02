"""
Compute Initial Rankings Management Command

Phase 3A-D: Bootstrap ranking snapshots from existing verified matches.
Run once after Phase 3A-D deployment to populate initial ranking data.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.competition.models import GameRankingConfig, MatchReport
from apps.competition.services import SnapshotService
from apps.organizations.models import Team


class Command(BaseCommand):
    help = 'Compute initial ranking snapshots for all teams (or specific game)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--game-id',
            type=str,
            help='Compute rankings for specific game only (e.g., LOL, VAL)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be computed without making changes',
        )
        parser.add_argument(
            '--team-slug',
            type=str,
            help='Compute rankings for specific team only (for testing)',
        )
    
    def handle(self, *args, **options):
        game_id = options.get('game_id')
        dry_run = options.get('dry_run', False)
        team_slug = options.get('team_slug')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Validate game_id if provided
        if game_id:
            try:
                config = GameRankingConfig.objects.get(game_id=game_id)
                self.stdout.write(f"Computing rankings for: {config.game_name} ({game_id})")
            except GameRankingConfig.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Invalid game_id: {game_id}"))
                self.stdout.write("Available games:")
                for cfg in GameRankingConfig.objects.all():
                    self.stdout.write(f"  - {cfg.game_id}: {cfg.game_name}")
                return
        else:
            configs = GameRankingConfig.objects.filter(is_active=True)
            self.stdout.write(f"Computing rankings for {configs.count()} games")
        
        # Get teams to process
        if team_slug:
            teams = Team.objects.filter(slug=team_slug, status='ACTIVE')
            if not teams.exists():
                self.stdout.write(self.style.ERROR(f"Team not found: {team_slug}"))
                return
            self.stdout.write(f"Processing single team: {team_slug}")
        else:
            teams = Team.objects.filter(status='ACTIVE')
            self.stdout.write(f"Processing {teams.count()} active teams")
        
        # Show summary of what will be computed
        if dry_run:
            self._show_dry_run_summary(teams, game_id)
            return
        
        # Perform actual computation
        self._compute_rankings(teams, game_id)
    
    def _show_dry_run_summary(self, teams, game_id):
        """Show what would be computed without making changes"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("DRY RUN SUMMARY")
        self.stdout.write("="*60 + "\n")
        
        total_teams = teams.count()
        
        if game_id:
            # Single game mode
            teams_with_matches = 0
            total_matches = 0
            
            for team in teams:
                match_count = MatchReport.objects.filter(
                    Q(team1=team) | Q(team2=team),
                    game_id=game_id,
                    verification__status__in=['CONFIRMED', 'ADMIN_VERIFIED']
                ).count()
                
                if match_count > 0:
                    teams_with_matches += 1
                    total_matches += match_count
            
            self.stdout.write(f"Game: {game_id}")
            self.stdout.write(f"Teams: {total_teams} total")
            self.stdout.write(f"Teams with verified matches: {teams_with_matches}")
            self.stdout.write(f"Total verified matches: {total_matches}")
            self.stdout.write(f"\nWould create/update: {teams_with_matches} game snapshots")
        else:
            # All games mode
            configs = GameRankingConfig.objects.filter(is_active=True)
            
            for config in configs:
                teams_with_matches = 0
                total_matches = 0
                
                for team in teams:
                    match_count = MatchReport.objects.filter(
                        Q(team1=team) | Q(team2=team),
                        game_id=config.game_id,
                        verification__status__in=['CONFIRMED', 'ADMIN_VERIFIED']
                    ).count()
                    
                    if match_count > 0:
                        teams_with_matches += 1
                        total_matches += match_count
                
                self.stdout.write(f"\n{config.game_name} ({config.game_id}):")
                self.stdout.write(f"  Teams with matches: {teams_with_matches}")
                self.stdout.write(f"  Verified matches: {total_matches}")
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Would create/update: {total_teams} global snapshots")
    
    def _compute_rankings(self, teams, game_id):
        """Perform actual ranking computation"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("COMPUTING RANKINGS")
        self.stdout.write("="*60 + "\n")
        
        if game_id:
            # Single game mode
            success_count = 0
            error_count = 0
            
            for team in teams:
                try:
                    snapshot = SnapshotService.update_team_game_snapshot(team, game_id)
                    self.stdout.write(
                        f"✓ {team.slug}: {snapshot.score} pts, "
                        f"{snapshot.tier}, {snapshot.verified_match_count} matches"
                    )
                    success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {team.slug}: {str(e)}")
                    )
                    error_count += 1
            
            # Recalculate ranks
            self.stdout.write("\nRecalculating ranks...")
            SnapshotService._recalculate_ranks(game_id)
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully computed {success_count} snapshots")
            )
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f"✗ {error_count} errors")
                )
        else:
            # All games + global mode
            configs = GameRankingConfig.objects.filter(is_active=True)
            
            game_success = {}
            game_errors = {}
            
            for config in configs:
                self.stdout.write(f"\nProcessing {config.game_name}...")
                success_count = 0
                error_count = 0
                
                for team in teams:
                    try:
                        snapshot = SnapshotService.update_team_game_snapshot(
                            team, config.game_id
                        )
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ {team.slug}: {str(e)}")
                        )
                        error_count += 1
                
                game_success[config.game_id] = success_count
                game_errors[config.game_id] = error_count
                
                self.stdout.write(f"  ✓ {success_count} snapshots created/updated")
                if error_count > 0:
                    self.stdout.write(self.style.ERROR(f"  ✗ {error_count} errors"))
            
            # Update global snapshots
            self.stdout.write("\nProcessing global rankings...")
            global_success = 0
            global_errors = 0
            
            for team in teams:
                try:
                    snapshot = SnapshotService.update_team_global_snapshot(team)
                    global_success += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {team.slug}: {str(e)}")
                    )
                    global_errors += 1
            
            self.stdout.write(f"  ✓ {global_success} global snapshots created/updated")
            if global_errors > 0:
                self.stdout.write(self.style.ERROR(f"  ✗ {global_errors} errors"))
            
            # Recalculate all ranks
            self.stdout.write("\nRecalculating ranks for all games...")
            SnapshotService._recalculate_ranks(None)
            
            # Summary
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS("RANKING COMPUTATION COMPLETE"))
            self.stdout.write("="*60)
            for game_id, count in game_success.items():
                self.stdout.write(f"  {game_id}: {count} snapshots")
            self.stdout.write(f"  GLOBAL: {global_success} snapshots")
