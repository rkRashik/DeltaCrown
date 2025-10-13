import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

# Check VALORANT tournament
valo_tournament = Tournament.objects.filter(slug='test-valorant-championship-2025').first()
if valo_tournament:
    print(f"✅ VALORANT Tournament Found")
    print(f"   Name: {valo_tournament.name}")
    print(f"   Game: {valo_tournament.game}")
    print(f"   Game type: {type(valo_tournament.game)}")
    print(f"   Has 'code' attr: {hasattr(valo_tournament.game, 'code')}")
    print(f"   Tournament type: {valo_tournament.tournament_type}")
    print()

# Check eFootball tournament
efb_tournament = Tournament.objects.filter(slug='test-efootball-tournament').first()
if efb_tournament:
    print(f"✅ eFootball Tournament Found")
    print(f"   Name: {efb_tournament.name}")
    print(f"   Game: {efb_tournament.game}")
    print(f"   Game type: {type(efb_tournament.game)}")
    print(f"   Has 'code' attr: {hasattr(efb_tournament.game, 'code')}")
    print(f"   Tournament type: {efb_tournament.tournament_type}")
