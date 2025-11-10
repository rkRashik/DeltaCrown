"""
Management Command: Refresh Tournament Analytics Materialized View

Module 6.2: Materialized Views for Analytics
Phase 6 Sprint 1

Implements: PHASE_6_IMPLEMENTATION_PLAN.md#module-62-materialized-views-for-analytics

Usage:
    # Full refresh (all tournaments)
    python manage.py refresh_analytics

    # Targeted refresh (single tournament)
    python manage.py refresh_analytics --tournament 123

    # Dry-run mode (show SQL without executing)
    python manage.py refresh_analytics --dry-run

    # Verbose output
    python manage.py refresh_analytics --verbosity 2

Safety:
    - Uses REFRESH MATERIALIZED VIEW CONCURRENTLY (non-blocking)
    - Requires unique index on tournament_id (created in migration 0009)
    - Failed refresh leaves prior materialized view intact
    - Logs duration and row counts for monitoring
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refresh tournament analytics materialized view"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tournament',
            type=int,
            help='Tournament ID for targeted refresh (default: refresh all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show SQL without executing',
        )
        parser.add_argument(
            '--no-concurrent',
            action='store_true',
            help='Use blocking refresh (not recommended for production)',
        )
    
    def handle(self, *args, **options):
        tournament_id = options.get('tournament')
        dry_run = options.get('dry_run', False)
        concurrent = not options.get('no_concurrent', False)
        verbosity = options.get('verbosity', 1)
        
        start_time = timezone.now()
        
        # Build SQL
        # Note: PostgreSQL materialized views don't support row-level refresh
        # For "targeted" refresh, we still REFRESH the entire MV but log it as targeted
        if tournament_id:
            operation = f"Targeted refresh for tournament {tournament_id} (full MV refresh)"
            logger.info(f"Targeted refresh for tournament {tournament_id} (refreshing entire MV)")
        else:
            operation = f"Full refresh ({('concurrent' if concurrent else 'blocking')})"
        
        # Always use REFRESH MATERIALIZED VIEW (targeted refresh not supported)
        concurrent_keyword = "CONCURRENTLY" if concurrent else ""
        sql = f"REFRESH MATERIALIZED VIEW {concurrent_keyword} tournament_analytics_summary;"
        
        # Dry-run mode: show SQL and exit
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY-RUN MODE: {operation}"))
            self.stdout.write(sql)
            return
        
        # Execute refresh
        try:
            with connection.cursor() as cursor:
                if verbosity >= 2:
                    self.stdout.write(f"Executing: {operation}")
                
                cursor.execute(sql)
                
                # Get row count
                cursor.execute("SELECT COUNT(*) FROM tournament_analytics_summary;")
                row_count = cursor.fetchone()[0]
                
                duration_ms = (timezone.now() - start_time).total_seconds() * 1000
                
                logger.info(
                    f"Analytics MV refresh: {operation}, {row_count} rows, {duration_ms:.2f}ms"
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {operation} complete: {row_count} tournaments, {duration_ms:.2f}ms"
                    )
                )
        
        except Exception as e:
            logger.error(f"Analytics MV refresh failed: {e}", exc_info=True)
            raise CommandError(f"Refresh failed: {e}")
