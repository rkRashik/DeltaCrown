import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("\n===== CURRENT RANK STATUS =====\n")
games = Game.objects.all().order_by('id')
for game in games:
    ranks_count = len(game.available_ranks) if game.available_ranks else 0
    print(f"{game.name}: {ranks_count} ranks")
