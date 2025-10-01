#!/usr/bin/env python
"""
Clean up tournament data to match model constraints
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

def main():
    print("=== CLEANING TOURNAMENT DATA ===")
    
    tournaments = Tournament.objects.all()
    
    for t in tournaments:
        changed = False
        
        # Fix game choices
        if t.game == "mlbb":
            print(f"Fixing game for '{t.name}': mlbb → valorant")
            t.game = "valorant"
            changed = True
        
        # Fix status choices
        if t.status == "OPEN":
            print(f"Fixing status for '{t.name}': OPEN → PUBLISHED")
            t.status = "PUBLISHED"
            changed = True
        
        if changed:
            t.save()
            print(f"✅ Updated: {t.name}")
    
    print("\n=== FINAL TOURNAMENT STATE ===")
    for t in tournaments:
        print(f"• {t.name}")
        print(f"  Game: {t.game} ({t.get_game_display()})")
        print(f"  Status: {t.status} ({t.get_status_display()})")
        print(f"  Entry Fee: ৳{t.entry_fee_bdt or 0}")
        print(f"  Prize Pool: ৳{t.prize_pool_bdt or 0}")
        print()
    
    print("=== DONE ===")

if __name__ == '__main__':
    main()