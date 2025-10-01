#!/usr/bin/env python
"""
Quick script to check tournament data in the database
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament, Registration

def main():
    print("=== TOURNAMENT DATA CHECK ===")
    print()
    
    # Check tournaments
    tournaments = Tournament.objects.all().order_by('-created_at')
    print(f"📊 Total Tournaments: {tournaments.count()}")
    print()
    
    if tournaments.exists():
        print("🏆 Tournament Details:")
        for t in tournaments:
            print(f"   • {t.name}")
            print(f"     - Game: {t.get_game_display()}")
            print(f"     - Status: {t.get_status_display()}")
            print(f"     - Slug: {t.slug}")
            print(f"     - Entry Fee: ৳{t.entry_fee_bdt or 0}")
            print(f"     - Prize Pool: ৳{t.prize_pool_bdt or 0}")
            print(f"     - Banner: {t.banner_url or 'No banner'}")
            print(f"     - Registration URL: {t.register_url}")
            print(f"     - Detail URL: {t.get_absolute_url()}")
            
            # Check registration count
            reg_count = Registration.objects.filter(tournament=t).count()
            print(f"     - Registrations: {reg_count}")
            print()
    else:
        print("❌ No tournaments found in database!")
        print()
        print("Creating sample tournaments...")
        
        # Create sample tournaments
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # Valorant tournament
        valorant_t = Tournament.objects.create(
            name="Valorant Championship 2025",
            slug="valorant-championship-2025",
            game="valorant",
            status="PUBLISHED",
            entry_fee_bdt=500,
            prize_pool_bdt=10000,
            slot_size=32,
            reg_open_at=now - timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=10),
            end_at=now + timedelta(days=12),
            short_description="Join the ultimate Valorant championship with the best players in Bangladesh."
        )
        
        # eFootball tournament
        efootball_t = Tournament.objects.create(
            name="eFootball Masters Cup",
            slug="efootball-masters-cup",
            game="efootball",
            status="PUBLISHED",
            entry_fee_bdt=200,
            prize_pool_bdt=5000,
            slot_size=64,
            reg_open_at=now - timedelta(days=2),
            reg_close_at=now + timedelta(days=5),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
            short_description="The biggest eFootball tournament in Bangladesh."
        )
        
        # Free tournament
        free_t = Tournament.objects.create(
            name="Free Fire Friday",
            slug="free-fire-friday",
            game="valorant",  # Using valorant as we only have these two games
            status="PUBLISHED",
            entry_fee_bdt=0,
            prize_pool_bdt=2000,
            slot_size=16,
            reg_open_at=now - timedelta(hours=6),
            reg_close_at=now + timedelta(days=2),
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=4),
            short_description="Weekly free tournament for everyone!"
        )
        
        print(f"✅ Created 3 sample tournaments:")
        print(f"   • {valorant_t.name}")
        print(f"   • {efootball_t.name}")
        print(f"   • {free_t.name}")
        print()
    
    # Check registrations
    registrations = Registration.objects.all()
    print(f"📝 Total Registrations: {registrations.count()}")
    
    if registrations.exists():
        print("Recent registrations:")
        for reg in registrations.order_by('-created_at')[:5]:
            print(f"   • {reg.user.username if reg.user else 'No user'} → {reg.tournament.name}")
    
    print()
    print("=== END CHECK ===")

if __name__ == '__main__':
    main()
