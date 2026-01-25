"""
Management command to manually trigger vNext ranking jobs.

This command provides a CLI interface for running ranking tasks without
waiting for Celery beat scheduling. Useful for:
- Manual verification during development
- Emergency recalculations after data fixes
- Testing task behavior

Usage:
    # Run all jobs
    python manage.py run_vnext_rank_jobs --all
    
    # Run specific jobs
    python manage.py run_vnext_rank_jobs --recalc-teams
    python manage.py run_vnext_rank_jobs --decay
    python manage.py run_vnext_rank_jobs --recalc-orgs
    
    # With filters
    python manage.py run_vnext_rank_jobs --recalc-teams --game-id 1 --region NA
    python manage.py run_vnext_rank_jobs --decay --cutoff-days 14
    
    # Limit for testing
    python manage.py run_vnext_rank_jobs --recalc-teams --limit 10

Phase 4 - Task P4-T2
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.organizations.tasks.rankings import (
    recalculate_team_rankings,
    apply_inactivity_decay,
    recalculate_organization_rankings,
)


class Command(BaseCommand):
    help = 'Manually trigger vNext ranking jobs (bypasses Celery beat schedule)'
    
    def add_arguments(self, parser):
        # Job selection
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all ranking jobs in sequence'
        )
        parser.add_argument(
            '--recalc-teams',
            action='store_true',
            help='Recalculate team rankings (tier updates)'
        )
        parser.add_argument(
            '--decay',
            action='store_true',
            help='Apply inactivity decay to teams'
        )
        parser.add_argument(
            '--recalc-orgs',
            action='store_true',
            help='Recalculate organization rankings (empire score)'
        )
        
        # Filters for team recalculation
        parser.add_argument(
            '--game-id',
            type=int,
            help='Filter teams by game ID'
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Filter teams by region (e.g., NA, EU, APAC)'
        )
        
        # Decay options
        parser.add_argument(
            '--cutoff-days',
            type=int,
            default=7,
            help='Days of inactivity before decay (default: 7)'
        )
        
        # General options
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of records processed (for testing)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='use_async',
            help='Run tasks asynchronously via Celery (instead of synchronously)'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        
        # Validate at least one job selected
        jobs_selected = (
            options['all'] or
            options['recalc_teams'] or
            options['decay'] or
            options['recalc_orgs']
        )
        
        if not jobs_selected:
            raise CommandError(
                'No jobs selected. Use --all or specify individual jobs '
                '(--recalc-teams, --decay, --recalc-orgs)'
            )
        
        use_async = options['use_async']
        
        self.stdout.write(
            self.style.SUCCESS('=' * 70)
        )
        self.stdout.write(
            self.style.SUCCESS('vNext Ranking Jobs - Manual Trigger')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 70)
        )
        self.stdout.write(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Mode: {'Async (Celery)' if use_async else 'Synchronous'}\n")
        
        results = {}
        
        # ====================================================================
        # JOB 1: Recalculate Team Rankings
        # ====================================================================
        
        if options['all'] or options['recalc_teams']:
            self.stdout.write(
                self.style.WARNING('\n[1/3] Recalculating Team Rankings...')
            )
            
            kwargs = {}
            if options['game_id']:
                kwargs['game_id'] = options['game_id']
                self.stdout.write(f"  Filter: game_id = {options['game_id']}")
            if options['region']:
                kwargs['region'] = options['region']
                self.stdout.write(f"  Filter: region = {options['region']}")
            if options['limit']:
                kwargs['limit'] = options['limit']
                self.stdout.write(f"  Limit: {options['limit']} teams")
            
            if use_async:
                task = recalculate_team_rankings.delay(**kwargs)
                self.stdout.write(
                    self.style.SUCCESS(f"  Task queued: {task.id}")
                )
                results['recalc_teams'] = {'task_id': task.id}
            else:
                result = recalculate_team_rankings(**kwargs)
                results['recalc_teams'] = result
                self._print_result(result)
        
        # ====================================================================
        # JOB 2: Apply Inactivity Decay
        # ====================================================================
        
        if options['all'] or options['decay']:
            self.stdout.write(
                self.style.WARNING('\n[2/3] Applying Inactivity Decay...')
            )
            
            kwargs = {'cutoff_days': options['cutoff_days']}
            if options['limit']:
                kwargs['limit'] = options['limit']
                self.stdout.write(f"  Limit: {options['limit']} teams")
            
            self.stdout.write(f"  Cutoff: {options['cutoff_days']} days")
            
            if use_async:
                task = apply_inactivity_decay.delay(**kwargs)
                self.stdout.write(
                    self.style.SUCCESS(f"  Task queued: {task.id}")
                )
                results['decay'] = {'task_id': task.id}
            else:
                result = apply_inactivity_decay(**kwargs)
                results['decay'] = result
                self._print_result(result)
        
        # ====================================================================
        # JOB 3: Recalculate Organization Rankings
        # ====================================================================
        
        if options['all'] or options['recalc_orgs']:
            self.stdout.write(
                self.style.WARNING('\n[3/3] Recalculating Organization Rankings...')
            )
            
            kwargs = {}
            if options['limit']:
                kwargs['limit'] = options['limit']
                self.stdout.write(f"  Limit: {options['limit']} organizations")
            
            if use_async:
                task = recalculate_organization_rankings.delay(**kwargs)
                self.stdout.write(
                    self.style.SUCCESS(f"  Task queued: {task.id}")
                )
                results['recalc_orgs'] = {'task_id': task.id}
            else:
                result = recalculate_organization_rankings(**kwargs)
                results['recalc_orgs'] = result
                self._print_result(result)
        
        # ====================================================================
        # SUMMARY
        # ====================================================================
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '=' * 70)
        )
        self.stdout.write(
            self.style.SUCCESS('Summary')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 70)
        )
        
        if use_async:
            self.stdout.write(
                self.style.WARNING(
                    'Tasks queued asynchronously. Check Celery logs for results.'
                )
            )
            for job_name, result in results.items():
                self.stdout.write(f"  {job_name}: Task ID {result['task_id']}")
        else:
            total_processed = 0
            total_updated = 0
            total_errors = 0
            
            for job_name, result in results.items():
                if 'teams_processed' in result:
                    total_processed += result['teams_processed']
                    total_updated += result.get('teams_updated', 0)
                    total_errors += result.get('errors', 0)
                elif 'orgs_processed' in result:
                    total_processed += result['orgs_processed']
                    total_updated += result.get('orgs_updated', 0)
                    total_errors += result.get('errors', 0)
            
            self.stdout.write(f"Total Processed: {total_processed}")
            self.stdout.write(f"Total Updated: {total_updated}")
            if total_errors > 0:
                self.stdout.write(
                    self.style.ERROR(f"Total Errors: {total_errors}")
                )
            self.stdout.write(f"Duration: {duration:.2f}s")
        
        self.stdout.write(
            self.style.SUCCESS('\nDone! ✅')
        )
    
    def _print_result(self, result):
        """Print task result in formatted style."""
        for key, value in result.items():
            label = key.replace('_', ' ').title()
            
            if key == 'errors' and value > 0:
                self.stdout.write(
                    self.style.ERROR(f"  {label}: {value}")
                )
            elif key == 'duration_seconds':
                self.stdout.write(
                    self.style.SUCCESS(f"  {label}: {value}s")
                )
            else:
                self.stdout.write(f"  {label}: {value}")
