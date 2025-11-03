# apps/tournaments/management/commands/audit_registration_states.py
"""
Management command to audit registration states for all tournaments.
Usage: python manage.py audit_registration_states [--detailed]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tournaments.models import Tournament


class Command(BaseCommand):
    help = 'Audit and display registration states for all tournaments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed state information',
        )
        parser.add_argument(
            '--game',
            type=str,
            help='Filter by game (valorant, efootball)',
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by status (DRAFT, PUBLISHED, RUNNING, COMPLETED)',
        )

    def handle(self, *args, **options):
        detailed = options.get('detailed', False)
        game_filter = options.get('game')
        status_filter = options.get('status')

        # Build queryset
        qs = Tournament.objects.select_related('settings').order_by('-created_at')
        
        if game_filter:
            qs = qs.filter(game=game_filter)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        tournaments = list(qs)
        
        if not tournaments:
            self.stdout.write(self.style.WARNING('No tournaments found'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n=== Tournament Registration States Audit ==='))
        self.stdout.write(self.style.SUCCESS(f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n'))

        for t in tournaments:
            state = t.state
            reg_state = state.registration_state
            
            # Color code based on state
            if reg_state.value == 'open':
                status_style = self.style.SUCCESS
            elif reg_state.value in ['not_open', 'closed']:
                status_style = self.style.WARNING
            else:
                status_style = self.style.ERROR
            
            self.stdout.write(f'\n{"="*70}')
            self.stdout.write(self.style.HTTP_INFO(f'ID: {t.id} | {t.name}'))
            self.stdout.write(f'Slug: {t.slug}')
            self.stdout.write(f'Game: {t.get_game_display()}')
            self.stdout.write(f'Status: {t.status}')
            self.stdout.write(status_style(f'Registration: {reg_state.value.upper()}'))
            
            can_reg, reason = state.can_register()
            self.stdout.write(f'Reason: {reason}')
            
            if detailed:
                self.stdout.write('\n--- Detailed Info ---')
                self.stdout.write(f'Phase: {state.current_phase.value}')
                self.stdout.write(f'Published: {state.is_published}')
                self.stdout.write(f'Started: {state.is_started}')
                self.stdout.write(f'Completed: {state.is_completed}')
                self.stdout.write(f'Team-based: {state.is_team_based}')
                
                # Dates
                reg_open, reg_close = state.registration_window
                self.stdout.write('\n--- Schedule ---')
                self.stdout.write(f'Start: {state.start_datetime or "Not set"}')
                self.stdout.write(f'Reg Open: {reg_open or "Not set"}')
                self.stdout.write(f'Reg Close: {reg_close or "Not set"}')
                
                # Slots
                slots = state.slots_info
                self.stdout.write('\n--- Capacity ---')
                if slots['has_limit']:
                    self.stdout.write(f'Slots: {slots["taken"]}/{slots["total"]} ({slots["available"]} available)')
                    self.stdout.write(f'Full: {slots["is_full"]}')
                else:
                    self.stdout.write(f'Slots: Unlimited ({slots["taken"]} registered)')
                
                # Time remaining
                if state.time_until_start():
                    self.stdout.write(f'\nTime until start: {state.time_until_start()}')
                if state.time_until_registration_closes():
                    self.stdout.write(f'Time until reg closes: {state.time_until_registration_closes()}')

        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.SUCCESS(f'\nTotal tournaments: {len(tournaments)}'))
        
        # Summary stats
        from collections import Counter
        states_count = Counter(t.state.registration_state.value for t in tournaments)
        self.stdout.write('\n--- Registration State Summary ---')
        for state_name, count in states_count.most_common():
            self.stdout.write(f'{state_name}: {count}')
