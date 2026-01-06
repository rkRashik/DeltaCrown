#!/usr/bin/env python
"""
PHASE 9A-23: Quick verification script for identity_key derivation
Tests the new derive_identity_key function with eFootball, FC26, and Rocket League schemas
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.views.game_passports_api import derive_identity_key


def test_efootball():
    """Test eFootball identity derivation (should use user_id)"""
    print("\n" + "="*60)
    print("TEST 1: eFootball™ 2026 Identity Derivation")
    print("="*60)
    
    try:
        game = Game.objects.get(slug='efootball')
        schema_fields = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        # Test metadata (only required fields)
        metadata = {
            'konami_id': 'testUser789',
            'user_id': 'ABCD-111-222-333'
        }
        
        identity_key, source_field = derive_identity_key(game, metadata, schema_fields)
        
        print(f"✅ SUCCESS")
        print(f"   Metadata: {metadata}")
        print(f"   Identity Key: '{identity_key}'")
        print(f"   Source Field: '{source_field}'")
        print(f"   Expected: user_id (ABCD-111-222-333 → abcd-111-222-333)")
        
        assert source_field == 'user_id', f"Expected 'user_id' but got '{source_field}'"
        assert identity_key == 'abcd-111-222-333', f"Expected 'abcd-111-222-333' but got '{identity_key}'"
        print(f"   ✓ Assertions passed")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_fc26():
    """Test FC26 identity derivation (should use ea_id)"""
    print("\n" + "="*60)
    print("TEST 2: EA SPORTS FC 26 Identity Derivation")
    print("="*60)
    
    try:
        game = Game.objects.get(slug='ea-fc')
        schema_fields = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        metadata = {
            'ea_id': 'myEAAccount123',
            'platform': 'playstation'
        }
        
        identity_key, source_field = derive_identity_key(game, metadata, schema_fields)
        
        print(f"✅ SUCCESS")
        print(f"   Metadata: {metadata}")
        print(f"   Identity Key: '{identity_key}'")
        print(f"   Source Field: '{source_field}'")
        print(f"   Expected: ea_id (myEAAccount123 → myeaaccount123)")
        
        assert source_field == 'ea_id', f"Expected 'ea_id' but got '{source_field}'"
        assert identity_key == 'myeaaccount123', f"Expected 'myeaaccount123' but got '{identity_key}'"
        print(f"   ✓ Assertions passed")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_rocket_league():
    """Test Rocket League identity derivation (should use epic_id)"""
    print("\n" + "="*60)
    print("TEST 3: Rocket League Identity Derivation")
    print("="*60)
    
    try:
        game = Game.objects.get(slug='rocketleague')
        schema_fields = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        metadata = {
            'epic_id': 'MyEpicName',
            'platform': 'epic'
        }
        
        identity_key, source_field = derive_identity_key(game, metadata, schema_fields)
        
        print(f"✅ SUCCESS")
        print(f"   Metadata: {metadata}")
        print(f"   Identity Key: '{identity_key}'")
        print(f"   Source Field: '{source_field}'")
        print(f"   Expected: epic_id (MyEpicName → myepicname)")
        
        assert source_field == 'epic_id', f"Expected 'epic_id' but got '{source_field}'"
        assert identity_key == 'myepicname', f"Expected 'myepicname' but got '{identity_key}'"
        print(f"   ✓ Assertions passed")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_missing_identity():
    """Test error handling when no identity can be derived"""
    print("\n" + "="*60)
    print("TEST 4: Missing Identity Error Handling")
    print("="*60)
    
    try:
        game = Game.objects.get(slug='efootball')
        schema_fields = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        # Empty metadata - should raise ValidationError
        metadata = {}
        
        try:
            identity_key, source_field = derive_identity_key(game, metadata, schema_fields)
            print(f"❌ FAILED: Should have raised ValidationError")
        except django.core.exceptions.ValidationError as ve:
            print(f"✅ SUCCESS: Raised ValidationError as expected")
            print(f"   Error: {ve}")
            print(f"   Error Dict: {ve.error_dict if hasattr(ve, 'error_dict') else 'N/A'}")
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("\n" + "#"*60)
    print("# PHASE 9A-23: Identity Key Derivation Verification")
    print("#"*60)
    
    test_efootball()
    test_fc26()
    test_rocket_league()
    test_missing_identity()
    
    print("\n" + "#"*60)
    print("# ALL TESTS COMPLETE")
    print("#"*60)
    print("\n✅ If all tests passed, the fix is working correctly!")
    print("📋 Next step: Manual testing via browser at /me/settings/")
    print("")
