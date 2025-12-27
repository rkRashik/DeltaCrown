import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print(f"Total games: {Game.objects.count()}")
print(f"Active games: {Game.objects.filter(is_active=True).count()}")

if Game.objects.exists():
    for game in Game.objects.all()[:5]:
        print(f"\n{game.name} (active={game.is_active})")
        print(f"  ID: {game.id}")
        print(f"  Identity configs: {game.identity_configs.count()}")
else:
    print("\n❌ NO GAMES IN DATABASE!")
    print("Run: python manage.py seed_games")
