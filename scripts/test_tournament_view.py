#!/usr/bin/env python
"""
Test tournament view data
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import RequestFactory
from apps.tournaments.views.public import hub

def main():
    print("=== TESTING TOURNAMENT HUB VIEW ===")
    
    # Create a fake request
    factory = RequestFactory()
    request = factory.get('/tournaments/')
    request.user = type('MockUser', (), {'is_authenticated': False})()
    
    try:
        response = hub(request)
        print("✅ Hub view executed successfully")
        print(f"Status code: {response.status_code}")
        
        # Test the context
        from apps.tournaments.models import Tournament
        tournaments = Tournament.objects.all()[:3]
        
        print(f"\n📊 Found {tournaments.count()} tournaments")
        
        # Test annotation
        from apps.tournaments.views.public import annotate_cards
        annotate_cards(tournaments)
        
        print("\n🏷️ Tournament data after annotation:")
        for t in tournaments:
            print(f"   • {getattr(t, 'dc_title', 'NO TITLE')}")
            print(f"     - dc_url: {getattr(t, 'dc_url', 'NO URL')}")
            print(f"     - dc_game: {getattr(t, 'dc_game', 'NO GAME')}")
            print(f"     - dc_fee_amount: {getattr(t, 'dc_fee_amount', 'NO FEE')}")
            print(f"     - dc_status: {getattr(t, 'dc_status', 'NO STATUS')}")
            print(f"     - register_url: {getattr(t, 'register_url', 'NO REG URL')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()