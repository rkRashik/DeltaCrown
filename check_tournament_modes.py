"""Debug script to check tournament mode and team settings"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament
from apps.tournaments.services.registration_service_phase2 import RegistrationServicePhase2

print("=" * 60)
print("TOURNAMENT TEAM MODE DEBUG")
print("=" * 60)

tournaments = Tournament.objects.filter(name__icontains='test', status='PUBLISHED').order_by('game')

for t in tournaments:
    print(f"\n{'='*60}")
    print(f"Tournament: {t.name}")
    print(f"Game: {t.game} ({t.get_game_display()})")
    print(f"Tournament Type: {t.tournament_type}")
    
    # Check settings
    if hasattr(t, 'settings') and t.settings:
        print(f"\n📋 Settings:")
        print(f"  - min_team_size: {t.settings.min_team_size}")
        print(f"  - max_team_size: {t.settings.max_team_size}")
    else:
        print(f"\n❌ No settings found")
    
    # Check if it's detected as team event
    is_team = RegistrationServicePhase2._is_team_event(t)
    print(f"\n🔍 Is Team Event (detected): {is_team}")
    
    if t.tournament_type == 'TEAM' and not is_team:
        print("⚠️ WARNING: Marked as TEAM but not detected!")
    elif t.tournament_type == 'SOLO' and is_team:
        print("⚠️ WARNING: Marked as SOLO but detected as TEAM!")
    else:
        print("✅ Detection matches tournament_type")

print("\n" + "="*60)

