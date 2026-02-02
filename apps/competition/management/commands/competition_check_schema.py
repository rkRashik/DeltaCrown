"""Management command to check competition app schema readiness."""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    """Check if competition app schema is ready for use."""
    
    help = 'Check if competition tables exist and app is properly configured'
    
    def handle(self, *args, **options):
        """Execute the schema check."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('COMPETITION APP SCHEMA CHECK')
        self.stdout.write('=' * 60 + '\n')
        
        # Check feature flag
        enabled = getattr(settings, 'COMPETITION_APP_ENABLED', False)
        if enabled:
            self.stdout.write(self.style.SUCCESS('✓ COMPETITION_APP_ENABLED = True'))
        else:
            self.stdout.write(self.style.WARNING('✗ COMPETITION_APP_ENABLED = False'))
            self.stdout.write('  → Competition features are disabled')
        
        self.stdout.write('')
        
        # Check schema readiness
        try:
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names(cursor)
                
                required_tables = {
                    'competition_game_ranking_config',
                    'competition_match_report',
                    'competition_match_verification',
                    'competition_team_game_ranking_snapshot',
                    'competition_team_global_ranking_snapshot',
                }
                
                existing_tables = required_tables & set(table_names)
                missing_tables = required_tables - set(table_names)
                
                if missing_tables:
                    self.stdout.write(self.style.ERROR('✗ Schema NOT Ready - Missing Tables:'))
                    for table in sorted(missing_tables):
                        self.stdout.write(f'  - {table}')
                    
                    self.stdout.write('\n' + self.style.WARNING('RECOMMENDED ACTION:'))
                    self.stdout.write('  Run migrations to create missing tables:')
                    self.stdout.write(self.style.SUCCESS('  $ python manage.py migrate competition'))
                    
                    if enabled:
                        self.stdout.write('\n' + self.style.ERROR('⚠ WARNING:'))
                        self.stdout.write('  COMPETITION_APP_ENABLED=True but tables missing!')
                        self.stdout.write('  Django admin will be hidden to prevent crashes.')
                else:
                    self.stdout.write(self.style.SUCCESS('✓ Schema Ready - All Tables Exist:'))
                    for table in sorted(existing_tables):
                        self.stdout.write(f'  - {table}')
                    
                    if not enabled:
                        self.stdout.write('\n' + self.style.WARNING('NOTE:'))
                        self.stdout.write('  Tables exist but COMPETITION_APP_ENABLED=False')
                        self.stdout.write('  To enable competition features:')
                        self.stdout.write('  1. Set COMPETITION_APP_ENABLED=True in settings')
                        self.stdout.write('  2. Seed initial game configs if needed')
                        self.stdout.write('  3. Restart application')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database Error: {str(e)}'))
            self.stdout.write('\n' + self.style.WARNING('Cannot check schema readiness'))
        
        self.stdout.write('\n' + '=' * 60 + '\n')
