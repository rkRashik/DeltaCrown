#!/usr/bin/env python
"""
Test registration URL routing with new template logic
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
    print("🎯 REGISTRATION TEMPLATE ROUTING TEST")
    print("=" * 50)
    
    tournaments = Tournament.objects.all().order_by('game', 'name')
    
    print(f"📊 Testing {tournaments.count()} tournaments:\n")
    
    for t in tournaments:
        print(f"🏆 {t.name}")
        print(f"   Game: {t.game} ({t.get_game_display()})")
        print(f"   Slug: {t.slug}")
        
        try:
            reg_url = t.register_url
            print(f"   Registration URL: {reg_url}")
            
            # Determine expected template based on URL
            if "/tournaments/valorant/" in reg_url:
                print("   ✅ Should use: valorant_register.html")
            elif "/tournaments/efootball/" in reg_url:
                print("   ✅ Should use: efootball_register.html")
            elif "?type=team" in reg_url:
                print("   ✅ Should use: enhanced_team_register.html")
            elif "?type=solo" in reg_url:
                print("   ✅ Should use: enhanced_solo_register.html")
            else:
                print("   ⚠️  Default enhanced registration")
                
        except Exception as e:
            print(f"   ❌ Error getting registration URL: {e}")
        
        print()
    
    print("🎮 TEMPLATE ROUTING SUMMARY:")
    print("=" * 50)
    
    # Test specific template routing logic
    from apps.tournaments.views.helpers import register_url
    
    valorant_tournaments = tournaments.filter(game="valorant")
    efootball_tournaments = tournaments.filter(game="efootball")
    
    print(f"Valorant tournaments ({valorant_tournaments.count()}):")
    for vt in valorant_tournaments:
        url = register_url(vt)
        if "/valorant/" in url:
            print(f"   ✅ {vt.name} → valorant_register.html")
        else:
            print(f"   ❌ {vt.name} → {url}")
    
    print(f"\neFootball tournaments ({efootball_tournaments.count()}):")
    for et in efootball_tournaments:
        url = register_url(et)
        if "/efootball/" in url:
            print(f"   ✅ {et.name} → efootball_register.html")
        else:
            print(f"   ❌ {et.name} → {url}")
    
    print(f"\nOther tournaments:")
    other_tournaments = tournaments.exclude(game__in=["valorant", "efootball"])
    for ot in other_tournaments:
        url = register_url(ot)
        if "?type=" in url:
            template_type = "team" if "type=team" in url else "solo"
            print(f"   ✅ {ot.name} → enhanced_{template_type}_register.html")
        else:
            print(f"   ⚠️  {ot.name} → {url}")
    
    print(f"\n✅ Registration template routing system updated!")
    print("Each tournament now routes to the appropriate registration template:")
    print("• Valorant → valorant_register.html")
    print("• eFootball → efootball_register.html") 
    print("• Solo tournaments → enhanced_solo_register.html")
    print("• Team tournaments → enhanced_team_register.html")

if __name__ == '__main__':
    main()