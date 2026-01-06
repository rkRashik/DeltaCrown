"""
Phase 9A-8: Comprehensive Game Passports Tests
Tests admin health, schema API, CRUD operations, lock enforcement
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GameProfile, GamePassportSchema

User = get_user_model()


class GamePassportsTestSuite(TestCase):
    """Comprehensive test suite for Phase 9A-8"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testplayer', password='testpass123')
        
        # Create test game (Valorant)
        self.game = Game.objects.create(
            name='VALORANT',
            slug='valorant',
            display_name='VALORANT',
            is_active=True,
            has_servers=True,
            primary_color='#ff4655'
        )
        
        # Create identity configs for Valorant
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='riot_id',
            display_name='Riot ID',
            field_type='TEXT',
            is_required=True,
            is_immutable=True,
            placeholder='PlayerName#NA1',
            help_text='Your full Riot ID including tag',
            validation_regex=r'^[a-zA-Z0-9 ]+#[a-zA-Z0-9]+$',
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='region',
            display_name='Region',
            field_type='select',
            is_required=True,
            is_immutable=False,
            help_text='Your game server region',
            order=2
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='rank',
            display_name='Current Rank',
            field_type='select',
            is_required=False,
            is_immutable=False,
            help_text='Your current competitive rank',
            order=3
        )
        
        # Create GamePassportSchema with options
        GamePassportSchema.objects.create(
            game=self.game,
            region_choices=[
                {'value': 'NA', 'label': 'North America'},
                {'value': 'EU', 'label': 'Europe'},
                {'value': 'APAC', 'label': 'Asia Pacific'},
            ],
            rank_choices=[
                {'value': 'iron', 'label': 'Iron'},
                {'value': 'bronze', 'label': 'Bronze'},
                {'value': 'silver', 'label': 'Silver'},
                {'value': 'gold', 'label': 'Gold'},
                {'value': 'platinum', 'label': 'Platinum'},
                {'value': 'diamond', 'label': 'Diamond'},
                {'value': 'immortal', 'label': 'Immortal'},
                {'value': 'radiant', 'label': 'Radiant'},
            ]
        )
    
    def test_admin_migration_health(self):
        """Test 1: Admin columns exist (migration applied)"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check GameProfileAlias table has required columns
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns 
                    WHERE table_name = 'user_profile_gameprofilealias'
                      AND column_name IN ('old_ign', 'old_discriminator', 'old_platform', 'old_region')
                """)
                columns = [row[0] for row in cursor.fetchall()]
                
                self.assertIn('old_ign', columns, "Migration 0051 failed: old_ign column missing")
                self.assertIn('old_discriminator', columns, "Migration 0051 failed: old_discriminator missing")
                self.assertIn('old_platform', columns, "Migration 0051 failed: old_platform missing")
                self.assertIn('old_region', columns, "Migration 0051 failed: old_region missing")
                
                print("✅ Admin migration health: All GameProfileAlias columns exist")
    
    def test_games_api_returns_complete_schema(self):
        """Test 2: Games API returns passport_schema with all fields"""
        response = self.client.get('/profile/api/games/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('games', data)
        self.assertGreater(len(data['games']), 0, "No games returned")
        
        # Check Valorant schema
        valorant = next((g for g in data['games'] if g['slug'] == 'valorant'), None)
        self.assertIsNotNone(valorant, "Valorant not found in games list")
        
        # Verify passport_schema exists and has fields
        self.assertIn('passport_schema', valorant)
        schema = valorant['passport_schema']
        self.assertGreaterEqual(len(schema), 3, "Valorant should have >= 3 fields (riot_id, region, rank)")
        
        # Verify first field (riot_id) has all required properties
        riot_id_field = next((f for f in schema if f['key'] == 'riot_id'), None)
        self.assertIsNotNone(riot_id_field, "riot_id field not found in schema")
        
        required_properties = ['key', 'label', 'type', 'required', 'immutable', 'placeholder', 'help_text']
        for prop in required_properties:
            self.assertIn(prop, riot_id_field, f"riot_id missing property: {prop}")
        
        # Verify select field has options
        region_field = next((f for f in schema if f['key'] == 'region'), None)
        self.assertIsNotNone(region_field, "region field not found in schema")
        self.assertEqual(region_field['type'], 'select', "region should be select type")
        self.assertIn('options', region_field, "select field should have options")
        self.assertGreater(len(region_field['options']), 0, "region should have option choices")
        
        print(f"✅ Games API: Valorant schema has {len(schema)} fields with complete properties")
    
    def test_create_passport_schema_driven(self):
        """Test 3: Create passport with schema-driven payload"""
        payload = {
            'game_id': self.game.id,
            'passport_data': {
                'riot_id': 'TestPlayer#NA1',
                'region': 'NA',
                'rank': 'diamond'
            }
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Create failed: {response.content}")
        data = response.json()
        
        self.assertTrue(data['success'], f"Create not successful: {data}")
        self.assertIn('passport', data)
        
        # Verify passport was created
        passport = GameProfile.objects.filter(user=self.user, game=self.game).first()
        self.assertIsNotNone(passport, "Passport not found in database after creation")
        self.assertEqual(passport.ign, 'TestPlayer', "IGN should be derived from riot_id")
        self.assertEqual(passport.discriminator, 'NA1', "Discriminator should be derived from riot_id")
        self.assertEqual(passport.region, 'NA')
        
        print("✅ Create passport: Schema-driven creation works, IGN derived correctly")
    
    def test_create_passport_missing_required_field(self):
        """Test 4: Create fails with 400 when required field missing"""
        payload = {
            'game_id': self.game.id,
            'passport_data': {
                # Missing riot_id (required)
                'region': 'NA',
                'rank': 'gold'
            }
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 400, not 500
        self.assertEqual(response.status_code, 400, "Should return 400 for missing required field")
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        # Error should mention missing field
        self.assertIn('required', data['error'].lower())
        
        print("✅ Create validation: Returns 400 with clear error for missing required field")
    
    def test_delete_valid_passport(self):
        """Test 5: Delete returns 200 for valid passport"""
        # Create passport first
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer',
            discriminator='NA1',
            region='NA',
            metadata={'riot_id': 'TestPlayer#NA1'}
        )
        
        payload = {'id': passport.id}
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Delete failed: {response.content}")
        data = response.json()
        
        self.assertTrue(data['success'], "Delete should succeed")
        
        # Verify passport was deleted
        exists = GameProfile.objects.filter(id=passport.id).exists()
        self.assertFalse(exists, "Passport should be deleted from database")
        
        print("✅ Delete passport: Returns 200 and removes from database")
    
    def test_delete_invalid_id(self):
        """Test 6: Delete returns 404 for non-existent passport"""
        payload = {'id': 99999}  # Non-existent ID
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 404, not 500
        self.assertEqual(response.status_code, 404, "Should return 404 for non-existent passport")
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        
        print("✅ Delete validation: Returns 404 for non-existent passport")
    
    def test_delete_without_id(self):
        """Test 7: Delete returns 400 when ID missing"""
        payload = {}  # Missing id
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400, "Should return 400 when ID missing")
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('required', data['error'].lower())
        
        print("✅ Delete validation: Returns 400 when ID parameter missing")
    
    def test_delete_locked_passport(self):
        """Test 8: Delete returns 403 when passport is locked"""
        # Create locked passport
        locked_until = timezone.now() + timedelta(days=15)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer',
            discriminator='NA1',
            region='NA',
            metadata={'riot_id': 'LockedPlayer#NA1'},
            locked_until=locked_until
        )
        
        payload = {'id': passport.id}
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 403 (Forbidden/Locked), not 500
        self.assertEqual(response.status_code, 403, "Should return 403 when passport is locked")
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'LOCKED', "Error should be 'LOCKED'")
        self.assertIn('days_remaining', data)
        self.assertGreater(data['days_remaining'], 0)
        
        # Passport should still exist
        exists = GameProfile.objects.filter(id=passport.id).exists()
        self.assertTrue(exists, "Locked passport should NOT be deleted")
        
        print(f"✅ Delete lock enforcement: Returns 403 with {data['days_remaining']} days remaining message")
    
    def test_update_locked_passport(self):
        """Test 9: Update returns 403 when passport is locked"""
        # Create locked passport
        locked_until = timezone.now() + timedelta(days=20)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer',
            discriminator='NA1',
            region='NA',
            metadata={'riot_id': 'LockedPlayer#NA1'},
            locked_until=locked_until
        )
        
        payload = {
            'id': passport.id,
            'passport_data': {
                'riot_id': 'NewName#NA1',  # Try to change identity
                'region': 'EU'
            }
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403, "Should return 403 when trying to update locked passport")
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'LOCKED')
        
        # Verify passport was NOT modified
        passport.refresh_from_db()
        self.assertEqual(passport.ign, 'LockedPlayer', "Locked passport IGN should not change")
        
        print("✅ Update lock enforcement: Returns 403, passport unchanged")
    
    def test_schema_field_types(self):
        """Test 10: Schema includes correct field types"""
        response = self.client.get('/profile/api/games/')
        data = response.json()
        
        valorant = next((g for g in data['games'] if g['slug'] == 'valorant'), None)
        schema = valorant['passport_schema']
        
        # Verify field types
        riot_id = next(f for f in schema if f['key'] == 'riot_id')
        self.assertEqual(riot_id['type'], 'text', "riot_id should be text type")
        
        region = next(f for f in schema if f['key'] == 'region')
        self.assertEqual(region['type'], 'select', "region should be select type")
        
        rank = next(f for f in schema if f['key'] == 'rank')
        self.assertEqual(rank['type'], 'select', "rank should be select type")
        
        print("✅ Schema validation: Field types correctly specified (text, select)")


def run_tests():
    """Run all tests and report results"""
    import sys
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    failures = test_runner.run_tests(['__main__'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    import django
    django.setup()
    run_tests()
