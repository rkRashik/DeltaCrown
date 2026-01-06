import django
django.setup()

from apps.games.models import Game, GamePlayerIdentityConfig

games = Game.objects.filter(is_active=True)
print(f'\nActive Games ({games.count()}):')
for g in games:
    print(f'  - {g.slug}: {g.display_name}')

print(f'\n\nIdentity Configs ({GamePlayerIdentityConfig.objects.count()}):')
configs = GamePlayerIdentityConfig.objects.select_related('game').all()
for c in configs:
    print(f'  - {c.game.slug}: {c.field_name} ({c.display_name}) - Type: {c.field_type}, Required: {c.is_required}')
