"""Test specifically for dota2 query issue."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("=" * 70)
print("Testing dota2 Query")
print("=" * 70)

print("\nMethod 1: Game.objects.filter(slug='dota2').first()")
game1 = Game.objects.filter(slug='dota2').first()
print(f"Result: {game1}")

print("\nMethod 2: Game.objects.get(slug='dota2')")
try:
    game2 = Game.objects.get(slug='dota2')
    print(f"Result: {game2}")
except Exception as e:
    print(f"Error: {e}")

print("\nMethod 3: Check all slugs")
all_games = Game.objects.all().values_list('slug', 'name')
for slug, name in all_games:
    if 'dota' in slug.lower():
        print(f"Found: {slug} - {name}")

print("\nMethod 4: Filter with icontains")
dota_games = Game.objects.filter(slug__icontains='dota')
print(f"Found {dota_games.count()} games with 'dota' in slug:")
for game in dota_games:
    print(f"  {game.slug} - {game.name}")
