import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("Games in database:")
for game in Game.objects.all():
    print(f"  ID: {game.id}, Name: '{game.name}'")
