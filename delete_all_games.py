"""Delete all games to start fresh seeding."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

count = Game.objects.all().count()
print(f"Found {count} games in database")
print("Deleting all games...")
Game.objects.all().delete()
print(f"✓ Successfully deleted {count} games")
print("\nNow run: python manage.py seed_games")
