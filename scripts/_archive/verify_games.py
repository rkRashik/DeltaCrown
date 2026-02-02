import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("=" * 70)
print("UPDATED GAMES IN DATABASE")
print("=" * 70)
print()

games = Game.objects.filter(is_active=True).order_by('name')

for i, game in enumerate(games, 1):
    featured = "⭐ FEATURED" if game.is_featured else ""
    print(f"{i}. {game.display_name} ({game.slug}) {featured}")
    print(f"   Category: {game.category} | Type: {game.game_type}")
    print(f"   Platforms: {', '.join(game.platforms)}")
    print(f"   Developer: {game.developer}")
    print(f"   Colors: {game.primary_color} / {game.secondary_color}")
    print()

print("=" * 70)
print(f"Total: {games.count()} active games")
print(f"Featured: {games.filter(is_featured=True).count()} games")
print("=" * 70)
