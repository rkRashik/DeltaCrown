#!/usr/bin/env python
"""
Quick test script for tournament system fixes.
Run with: python scripts/test_tournament_fixes.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.tournaments.models import Tournament

print("=" * 60)
print("Testing Tournament System Fixes")
print("=" * 60)

# Test 1: Date Validation
print("\n1. Testing date validation...")
try:
    t = Tournament(
        name='Test Tournament',
        slug='test-validation',
        game='valorant',
        status='DRAFT',
        reg_open_at=timezone.now() + timedelta(days=2),
        reg_close_at=timezone.now() + timedelta(days=1),  # BEFORE open_at - INVALID
    )
    t.full_clean()
    print("   ❌ FAILED: Should have raised ValidationError")
except ValidationError as e:
    print(f"   ✅ PASSED: Caught validation error - {list(e.message_dict.keys())}")

# Test 2: Slot Size Validation
print("\n2. Testing slot size validation...")
try:
    t = Tournament(
        name='Test Tournament',
        slug='test-slots',
        game='valorant',
        status='DRAFT',
        slot_size=1  # Too small - INVALID
    )
    t.full_clean()
    print("   ❌ FAILED: Should have raised ValidationError for slot_size")
except ValidationError as e:
    print(f"   ✅ PASSED: Caught validation error - {list(e.message_dict.keys())}")

# Test 3: Status Field
print("\n3. Testing status field...")
t = Tournament(
    name='Test Tournament',
    slug='test-status',
    game='valorant'
)
print(f"   Default status: {t.status}")
print(f"   ✅ PASSED: Status defaults to DRAFT" if t.status == 'DRAFT' else "   ❌ FAILED")

# Test 4: Status Choices
print("\n4. Testing status choices...")
choices = [choice[0] for choice in Tournament.Status.choices]
expected = ['DRAFT', 'PUBLISHED', 'RUNNING', 'COMPLETED']
if choices == expected:
    print(f"   ✅ PASSED: Status choices correct: {choices}")
else:
    print(f"   ❌ FAILED: Expected {expected}, got {choices}")

# Test 5: Game Choices
print("\n5. Testing game choices...")
game_choices = [choice[0] for choice in Tournament.Game.choices]
expected_games = ['valorant', 'efootball']
if game_choices == expected_games:
    print(f"   ✅ PASSED: Game choices correct: {game_choices}")
else:
    print(f"   ❌ FAILED: Expected {expected_games}, got {game_choices}")

# Test 6: Entry Fee Property
print("\n6. Testing entry_fee property...")
t = Tournament(
    name='Test Tournament',
    slug='test-fee',
    game='valorant',
    entry_fee_bdt=100.00
)
if t.entry_fee == 100.00:
    print(f"   ✅ PASSED: entry_fee property works")
else:
    print(f"   ❌ FAILED: entry_fee = {t.entry_fee}, expected 100.00")

# Test 7: State Machine Integration
print("\n7. Testing state machine integration...")
t = Tournament(
    name='Test Tournament',
    slug='test-state',
    game='valorant',
    status='PUBLISHED'
)
state = t.state
if hasattr(state, 'registration_state') and hasattr(state, 'tournament_phase'):
    print(f"   ✅ PASSED: State machine accessible")
    print(f"      Phase: {state.tournament_phase}")
    print(f"      Is published: {state.is_published}")
else:
    print(f"   ❌ FAILED: State machine not accessible")

print("\n" + "=" * 60)
print("Testing Complete!")
print("=" * 60)

# Test 8: Game Config Validation (if models exist)
print("\n8. Testing game config validation...")
try:
    from apps.game_valorant.models import ValorantConfig
    from apps.game_efootball.models import EfootballConfig
    
    # Create tournament
    t_valorant = Tournament.objects.create(
        name='Valorant Test',
        slug='valorant-test-config',
        game='valorant',
        status='DRAFT'
    )
    
    # Try to add eFootball config to Valorant tournament
    efb_config = EfootballConfig(tournament=t_valorant)
    try:
        efb_config.full_clean()
        print("   ❌ FAILED: Should prevent eFootball config on Valorant tournament")
        t_valorant.delete()
    except ValidationError as e:
        print(f"   ✅ PASSED: Game config validation works")
        print(f"      Error: {str(e)[:80]}...")
        t_valorant.delete()
        
except ImportError:
    print("   ⏭️  SKIPPED: Game config models not available")
except Exception as e:
    print(f"   ⚠️  ERROR: {str(e)[:80]}...")

print("\n✅ All tests completed!")
