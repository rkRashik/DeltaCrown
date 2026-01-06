"""
Phase 9A-4: Comprehensive Game Passports Tests

DEPRECATED: Phase 9A-13 consolidated passport_service.py into game_passport_service.py
This test file references deprecated functions. Update to use GamePassportService methods.

Tests for:
- Duplicate prevention (409)
- Verification lock (403)
- Visibility validation
- Schema completeness
- Smart gap-filling
- Platform integration helpers
"""

import os
import django

# Initialize Django before imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models_main import GameProfile
from apps.user_profile.services.game_passport_service import GamePassportService
import json

User = get_user_model()


class GamePassportsPhase9A4Tests(TestCase):
    """Phase 9A-4: Production readiness tests"""
    
    def setUp(self):
        """Create test user and game"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testplayer', password='testpass123')
        
        # Create test game
        self.game = Game.objects.create(
            name='VALORANT',
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
        
        # Create identity configs
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='riot_id',
            display_name='Riot ID',
            field_type='TEXT',
            is_required=True,
            is_immutable=True,
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='region',
            display_name='Region',
            field_type='select',
            is_required=True,
            order=2
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='rank',
            display_name='Rank',
            field_type='select',
            is_required=False,
            order=3
        )
    
    def test_duplicate_returns_409(self):
        """Test 1: Duplicate game passport returns 409 CONFLICT"""
        # Create first passport
        response1 = self.client.post('/profile/api/game-passports/create/', {
            'game_id': self.game.id,
            'passport_data': {
                'riot_id': 'TestPlayer#NA1',
                'region': 'NA'
            }
        }, content_type='application/json')
        
        self.assertEqual(response1.status_code, 200)
        data1 = response1.json()
        self.assertTrue(data1['success'])
        
        # Try to create duplicate
        response2 = self.client.post('/profile/api/game-passports/create/', {
            'game_id': self.game.id,
            'passport_data': {
                'riot_id': 'TestPlayer2#NA1',
                'region': 'EU'
            }
        }, content_type='application/json')
        
        self.assertEqual(response2.status_code, 409)
        data2 = response2.json()
        self.assertFalse(data2['success'])
        self.assertEqual(data2['error'], 'DUPLICATE_GAME_PASSPORT')
        self.assertIn('already linked', data2['message'].lower())
        self.assertIn('existing_passport_id', data2)
        
        print("[PASS] Duplicate prevention: Returns 409 with DUPLICATE_GAME_PASSPORT error")
    
    def test_verified_lock_returns_403(self):
        """Test 2: Editing verified passport returns 403 VERIFIED_LOCK"""
        # Create and verify passport
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer',
            region='NA',
            metadata={'riot_id': 'TestPlayer#NA1', 'region': 'NA'},
            verification_status='VERIFIED'
        )
        
        # Try to edit verified passport
        response = self.client.post('/profile/api/game-passports/update/', {
            'id': passport.id,
            'passport_data': {
                'riot_id': 'NewPlayer#NA1',  # Try to change immutable field
                'region': 'EU'
            }
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'VERIFIED_LOCK')
        self.assertIn('verified', data['message'].lower())
        
        print("[PASS] Verification lock: Returns 403 VERIFIED_LOCK")
    
    def test_time_lock_returns_403(self):
        """Test 3: Editing time-locked passport returns 403 LOCKED"""
        # Create locked passport
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer',
            region='NA',
            metadata={'riot_id': 'TestPlayer#NA1', 'region': 'NA'},
            locked_until=timezone.now() + timedelta(days=15)
        )
        
        # Try to delete locked passport
        response = self.client.post('/profile/api/game-passports/delete/', {
            'id': passport.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'LOCKED')
        self.assertIn('locked', data['message'].lower())
        self.assertIn('days_remaining', data)
        self.assertGreater(data['days_remaining'], 0)
        
        print("[PASS] Time lock: Returns 403 LOCKED with days remaining")
    
    def test_visibility_validation(self):
        """Test 4: Visibility field validation"""
        # Test invalid visibility
        response = self.client.post('/profile/api/game-passports/create/', {
            'game_id': self.game.id,
            'visibility': 'INVALID',
            'passport_data': {
                'riot_id': 'TestPlayer#NA1',
                'region': 'NA'
            }
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'VALIDATION_ERROR')
        self.assertIn('visibility', data['message'].lower())
        
        # Test valid visibilities
        for visibility in ['PUBLIC', 'PROTECTED', 'PRIVATE']:
            GameProfile.objects.all().delete()  # Clear previous
            response = self.client.post('/profile/api/game-passports/create/', {
                'game_id': self.game.id,
                'visibility': visibility,
                'passport_data': {
                    'riot_id': f'TestPlayer{visibility}#NA1',
                    'region': 'NA'
                }
            }, content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
        
        print("[PASS] Visibility validation: Accepts PUBLIC/PROTECTED/PRIVATE, rejects invalid")
    
    def test_delete_never_500(self):
        """Test 5: Delete always returns structured JSON, never raw 500"""
        # Test delete with missing ID
        response = self.client.post('/profile/api/game-passports/delete/', {
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'VALIDATION_ERROR')
        self.assertIn('message', data)
        
        # Test delete non-existent
        response = self.client.post('/profile/api/game-passports/delete/', {
            'id': 99999
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'NOT_FOUND')
        
        print("[PASS] Delete error handling: Always returns structured JSON")
    
    def test_schema_completeness(self):
        """Test 6: Games API returns complete schema"""
        response = self.client.get('/profile/api/games/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('games', data)
        
        # Find Valorant game
        valorant = next((g for g in data['games'] if g['slug'] == 'valorant'), None)
        self.assertIsNotNone(valorant)
        self.assertIn('passport_schema', valorant)
        
        schema = valorant['passport_schema']
        self.assertGreater(len(schema), 1, "Schema should have multiple fields, not just Game ID")
        
        # Verify required field
        riot_id_field = next((f for f in schema if f['key'] == 'riot_id'), None)
        self.assertIsNotNone(riot_id_field)
        self.assertTrue(riot_id_field['required'])
        self.assertTrue(riot_id_field['immutable'])
        
        print(f"[PASS] Schema completeness: Valorant has {len(schema)} fields")
    
    def test_gap_filling_service(self):
        """Test 7: Smart gap-filling creates/updates passports"""
        # Test create via gap-fill
        success, error, passport = apply_gap_fill(
            self.user,
            self.game,
            {
                'riot_id': 'GapFill#NA1',
                'region': 'NA',
                'rank': 'Diamond'
            }
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(passport)
        self.assertEqual(passport['metadata']['riot_id'], 'GapFill#NA1')
        
        # Test update via gap-fill (add missing field)
        success, error, passport = apply_gap_fill(
            self.user,
            self.game,
            {
                'role': 'Duelist'  # Add new field
            }
        )
        
        self.assertTrue(success)
        self.assertEqual(passport['metadata']['role'], 'Duelist')
        self.assertEqual(passport['metadata']['riot_id'], 'GapFill#NA1')  # Original preserved
        
        print("[PASS] Gap-filling: Creates and updates passports correctly")
    
    def test_missing_fields_detection(self):
        """Test 8: Detect missing required fields"""
        # No passport exists
        missing, existing = get_missing_passport_fields(
            self.user,
            self.game,
            ['riot_id', 'region', 'rank']
        )
        
        self.assertEqual(set(missing), {'riot_id', 'region', 'rank'})
        self.assertEqual(existing, {})
        
        # Create partial passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='Partial',
            metadata={'riot_id': 'Partial#NA1'}  # Missing region
        )
        
        missing, existing = get_missing_passport_fields(
            self.user,
            self.game,
            ['riot_id', 'region', 'rank']
        )
        
        self.assertIn('region', missing)
        self.assertIn('rank', missing)
        self.assertNotIn('riot_id', missing)
        self.assertIsNotNone(existing)
        
        print("[PASS] Missing fields detection: Identifies gaps correctly")
    
    def test_tournament_identity_builder(self):
        """Test 9: Build tournament registration identity"""
        # Create passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TournamentPlayer',
            region='NA',
            rank_name='Immortal',
            metadata={
                'riot_id': 'TournamentPlayer#NA1',
                'region': 'NA',
                'rank': 'Immortal',
                'role': 'Controller'
            },
            verification_status='VERIFIED'
        )
        
        identity = build_registration_identity(self.user, self.game)
        
        self.assertIsNotNone(identity)
        self.assertEqual(identity['primary_id'], 'TournamentPlayer#NA1')
        self.assertEqual(identity['ign'], 'TournamentPlayer')
        self.assertEqual(identity['region'], 'NA')
        self.assertEqual(identity['rank'], 'Immortal')
        self.assertTrue(identity['is_verified'])
        self.assertEqual(identity['game_slug'], 'valorant')
        
        print("[PASS] Tournament identity builder: Constructs canonical payload")
    
    def test_tournament_validation_visibility(self):
        """Test 10: Validate passport visibility for tournaments"""
        # PRIVATE passport blocks tournaments
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='PrivatePlayer',
            metadata={'riot_id': 'Private#NA1', 'region': 'NA'},
            visibility='PRIVATE'
        )
        
        valid, error = validate_passport_for_tournament(self.user, self.game)
        
        self.assertFalse(valid)
        self.assertIn('PRIVATE', error)
        self.assertIn('tournament', error.lower())
        
        # PUBLIC/PROTECTED passports allow tournaments
        passport = GameProfile.objects.get(user=self.user, game=self.game)
        for visibility in ['PUBLIC', 'PROTECTED']:
            passport.visibility = visibility
            passport.save()
            
            valid, error = validate_passport_for_tournament(self.user, self.game)
            self.assertTrue(valid, f"{visibility} passport should allow tournaments")
        
        print("[PASS] Tournament validation: PRIVATE blocks, PUBLIC/PROTECTED allow")


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    failures = test_runner.run_tests(['__main__'])
    
    if failures == 0:
        print("\n" + "="*70)
        print("[SUCCESS] ALL PHASE 9A-4 TESTS PASSED")
        print("="*70)
    else:
        print(f"\n[FAILED] {failures} test(s) failed")
