"""
Check existing identity configs for all games
"""
from django.core.management.base import BaseCommand
from apps.games.models import Game, GamePlayerIdentityConfig


class Command(BaseCommand):
    help = 'Check existing identity configs'

    def handle(self, *args, **options):
        games = Game.objects.filter(is_active=True)
        self.stdout.write(f'\n✓ Active Games ({games.count()}):')
        for g in games:
            self.stdout.write(f'  - {g.slug}: {g.display_name}')

        self.stdout.write(f'\n\n✓ Identity Configs ({GamePlayerIdentityConfig.objects.count()}):')
        configs = GamePlayerIdentityConfig.objects.select_related('game').all()
        for c in configs:
            self.stdout.write(f'  - {c.game.slug}: {c.field_name} ({c.display_name}) - Type: {c.field_type}, Required: {c.is_required}')
        
        self.stdout.write('\n\n✓ Games WITHOUT identity configs:')
        games_without_configs = Game.objects.filter(is_active=True, identity_configs__isnull=True)
        for g in games_without_configs:
            self.stdout.write(f'  - {g.slug}: {g.display_name}')
