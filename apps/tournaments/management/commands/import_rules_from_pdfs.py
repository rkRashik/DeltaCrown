"""
Management Command: Import Rules from PDFs

Extracts text from tournament rules PDF files and converts them into HTML
for the rules_text field.

Usage:
    python manage.py import_rules_from_pdfs
    python manage.py import_rules_from_pdfs --only-empty
    python manage.py import_rules_from_pdfs --tournament-id 123
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.tournaments.models import Tournament
from apps.tournaments.utils import import_rules_from_pdf


class Command(BaseCommand):
    help = 'Import rules from PDF files into rules_text field for tournaments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--only-empty',
            action='store_true',
            help='Only import for tournaments with empty rules_text',
        )
        parser.add_argument(
            '--tournament-id',
            type=int,
            help='Import rules for a specific tournament ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )
    
    def handle(self, *args, **options):
        only_empty = options['only_empty']
        tournament_id = options.get('tournament_id')
        dry_run = options['dry_run']
        
        # Build queryset
        queryset = Tournament.objects.all()
        
        # Filter by tournament ID if specified
        if tournament_id:
            queryset = queryset.filter(id=tournament_id)
            if not queryset.exists():
                raise CommandError(f'Tournament with ID {tournament_id} does not exist')
        
        # Filter for tournaments with PDF
        queryset = queryset.exclude(
            Q(rules_pdf='') | Q(rules_pdf__isnull=True)
        )
        
        # Filter for empty rules_text if requested
        if only_empty:
            queryset = queryset.filter(
                Q(rules_text='') | Q(rules_text__isnull=True)
            )
        
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No tournaments found matching criteria')
            )
            return
        
        self.stdout.write(
            self.style.NOTICE(f'Found {total_count} tournament(s) with PDF files')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            self.stdout.write('')
        
        # Process tournaments
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for tournament in queryset:
            try:
                tournament_desc = f'{tournament.name} (ID: {tournament.id})'
                
                # Check if we should skip (only if only_empty is True)
                if only_empty and tournament.rules_text and tournament.rules_text.strip():
                    self.stdout.write(f'⏭️  {tournament_desc}: Already has rules_text')
                    skip_count += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        self.style.NOTICE(
                            f'Would import: {tournament_desc} '
                            f'(PDF: {tournament.rules_pdf.name})'
                        )
                    )
                    success_count += 1
                    continue
                
                # Import rules from PDF
                self.stdout.write(f'🔄 Processing: {tournament_desc}...')
                
                html = import_rules_from_pdf(tournament, overwrite=True)
                
                if html:
                    char_count = len(html)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'   ✅ Imported {char_count} characters of HTML'
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'   ⏭️  No text extracted')
                    )
                    skip_count += 1
                    
            except ImportError as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {tournament_desc}: {str(e)}')
                )
                error_count += 1
            except FileNotFoundError:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {tournament_desc}: PDF file not found on disk')
                )
                error_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {tournament_desc}: {str(e)}')
                )
                error_count += 1
        
        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('━' * 60))
        self.stdout.write(self.style.NOTICE('SUMMARY'))
        self.stdout.write(self.style.NOTICE('━' * 60))
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully imported: {success_count} tournament(s)')
            )
        
        if skip_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⏭️  Skipped: {skip_count} tournament(s)')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed: {error_count} tournament(s)')
            )
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('DRY RUN completed - no changes were made')
            )
        
        self.stdout.write(self.style.NOTICE('━' * 60))
