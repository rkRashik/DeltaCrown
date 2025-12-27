import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game
import json

print("=== Testing Game API Data ===\n")

# Test Call of Duty Mobile
codm = Game.objects.filter(name__icontains='Call of Duty').first()
if codm:
    print(f"Game: {codm.name}")
    print(f"Identity configs: {codm.identity_configs.count()}")
    for c in codm.identity_configs.all():
        print(f"  - {c.field_name}: {c.display_name} (required={c.is_required})")
    print(f"Platforms: {codm.platforms}")
    print(f"Has roster config: {hasattr(codm, 'roster_config') and codm.roster_config is not None}")
    if hasattr(codm, 'roster_config') and codm.roster_config:
        print(f"  Has regions: {codm.roster_config.has_regions}")
        if codm.roster_config.has_regions:
            print(f"  Regions: {codm.roster_config.available_regions}")

print("\n=== All Games ===")
for game in Game.objects.filter(is_active=True)[:11]:
    print(f"\n{game.name}:")
    print(f"  Platforms: {game.platforms}")
    configs = list(game.identity_configs.all())
    print(f"  Identity fields: {[c.field_name for c in configs]}")
