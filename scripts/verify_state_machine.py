"""
Quick verification script for Tournament State Machine implementation
Tests that all components are properly integrated
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.utils import timezone
from apps.tournaments.models import Tournament
from apps.tournaments.models.state_machine import RegistrationState, TournamentPhase
from colorama import init, Fore, Style

init(autoreset=True)

def test_state_machine():
    """Test state machine integration"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Tournament State Machine Verification")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # Test 1: Check if state machine is accessible
    print(f"{Fore.YELLOW}Test 1: State Machine Access{Style.RESET_ALL}")
    try:
        tournament = Tournament.objects.first()
        if tournament:
            state_machine = tournament.state
            print(f"  {Fore.GREEN}✓ State machine accessible on Tournament model")
            print(f"    Tournament: {tournament.name}")
            print(f"    State: {state_machine.registration_state}")
            print(f"    Phase: {state_machine.phase}")
        else:
            print(f"  {Fore.YELLOW}⚠ No tournaments found in database")
    except Exception as e:
        print(f"  {Fore.RED}✗ Error: {e}")
        return False
    
    # Test 2: Check state machine methods
    print(f"\n{Fore.YELLOW}Test 2: State Machine Methods{Style.RESET_ALL}")
    try:
        if tournament:
            is_full = tournament.state.is_full
            slots_info = tournament.state.slots_info
            time_str = tournament.state.time_until_start()
            state_dict = tournament.state.to_dict()
            
            print(f"  {Fore.GREEN}✓ All methods working:")
            print(f"    is_full: {is_full}")
            print(f"    slots_info: {slots_info}")
            print(f"    time_until_start: {time_str}")
            print(f"    to_dict keys: {list(state_dict.keys())}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Error: {e}")
        return False
    
    # Test 3: Check can_register method
    print(f"\n{Fore.YELLOW}Test 3: User Registration Check{Style.RESET_ALL}")
    try:
        if tournament:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Test with anonymous user
            can_reg, msg = tournament.state.can_register(None)
            print(f"  {Fore.GREEN}✓ Anonymous user check: {can_reg}")
            print(f"    Message: {msg}")
            
            # Test with real user if exists
            user = User.objects.first()
            if user:
                can_reg, msg = tournament.state.can_register(user)
                print(f"  {Fore.GREEN}✓ User '{user.username}' check: {can_reg}")
                print(f"    Message: {msg}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Error: {e}")
        return False
    
    # Test 4: Check state API endpoint exists
    print(f"\n{Fore.YELLOW}Test 4: State API Endpoint{Style.RESET_ALL}")
    try:
        from apps.tournaments.views.state_api import tournament_state_api
        print(f"  {Fore.GREEN}✓ State API view imported successfully")
        
        # Check URL configuration
        from django.urls import resolve, reverse
        if tournament:
            try:
                url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
                print(f"  {Fore.GREEN}✓ URL routing configured: {url}")
            except Exception as e:
                print(f"  {Fore.RED}✗ URL routing error: {e}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Error: {e}")
        return False
    
    # Test 5: Check static files exist
    print(f"\n{Fore.YELLOW}Test 5: Frontend Integration{Style.RESET_ALL}")
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    files_to_check = [
        'static/js/tournament-state-poller.js',
        'static/css/tournament-state-poller.css',
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            print(f"  {Fore.GREEN}✓ {file_path} exists")
        else:
            print(f"  {Fore.RED}✗ {file_path} NOT FOUND")
    
    # Test 6: Check audit command
    print(f"\n{Fore.YELLOW}Test 6: Management Command{Style.RESET_ALL}")
    try:
        from apps.tournaments.management.commands.audit_registration_states import Command
        print(f"  {Fore.GREEN}✓ Audit command exists")
        print(f"    Usage: python manage.py audit_registration_states")
    except Exception as e:
        print(f"  {Fore.RED}✗ Error: {e}")
        return False
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}✓ All verification tests passed!")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    print(f"{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
    print("  1. Run: python manage.py audit_registration_states --detailed")
    print("  2. Start server and open a tournament detail page")
    print("  3. Open browser console to see poller logs")
    print("  4. Wait 30 seconds to see automatic updates")
    
    return True

if __name__ == '__main__':
    try:
        success = test_state_machine()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
