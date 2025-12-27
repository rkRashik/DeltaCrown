import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("\nGames in database:")
for g in Game.objects.all().order_by('id'):
    print(f"  '{g.name}'")
