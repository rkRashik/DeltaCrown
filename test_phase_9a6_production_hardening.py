"""
Phase 9A-6: Game Passports Production Hardening Tests

Test Coverage:
1. Schema completeness for all 11 active games
2. CRUD operations with proper error codes
3. Duplicate prevention (409)
4. Lock enforcement (403 LOCKED, 403 VERIFIED_LOCK)
5. API contract verification
6. Admin verification actions
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GameProfile, GamePassportSchema


class SchemaCompletenessTests(TestCase):
    """Test that ALL 11 games have complete schemas"""
    
    fixtures = ['games.json']
    
    def setUp(self):
        # Seed identity configs for all games
        from django.core.management import call_command
        call_command('seed_identity_configs', verbosity=0)
    
    def test_all_games_have_schemas(self):
        """Every active game must have at least 3 fields"""
        games = Game.objects.filter(is_active=True)
        self.assertGreaterEqual(games.count(), 11, "Should have 11+ active games")
        
        for game in games:
            config_count = GamePlayerIdentityConfig.objects.filter(game=game).count()
            self.assertGreaterEqual(
                config_count, 3,
                f"{game.display_name} ({game.slug}) has only {config_count} fields (minimum 3 required)"
            )
    
    def test_valorant_has_complete_schema(self):
        """VALORANT should have 6 fields (riot_id, ign, region, rank, peak_rank, role)"""
        valorant = Game.objects.get(slug='valorant')
        configs = GamePlayerIdentityConfig.objects.filter(game=valorant)
        
        self.assertEqual(configs.count(), 6, "VALORANT should have 6 fields")
        
        field_names = [c.field_name for c in configs]
        required_fields = ['riot_id', 'ign', 'region', 'rank', 'peak_rank', 'role']
        for field in required_fields:
            self.assertIn(field, field_names, f"VALORANT missing field: {field}")
    
    def test_api_returns_schemas(self):
        """GET /profile/api/games/ should return schemas for all games"""
        client = Client()
        response = client.get('/profile/api/games/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('games', data)
        games = data['games']
        self.assertGreaterEqual(len(games), 11)
        
        for game in games:
            self.assertIn('passport_schema', game)
            schema = game['passport_schema']
            self.assertGreaterEqual(
                len(schema), 3,
                f"{game['display_name']} API returns only {len(schema)} fields"
            )


class CRUDOperationTests(TestCase):
    """Test create/update/delete operations with proper error codes"""
    
    fixtures = ['games.json']
    
    def setUp(self):
        from django.core.management import call_command
        call_command('seed_identity_configs', verbosity=0)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        self.valorant = Game.objects.get(slug='valorant')
    
    def test_create_success(self):
        """Creating a valid passport should return 201"""
        payload = {
            'game_id': self.valorant.id,
            'ign': 'TestPlayer',
            'region': 'NA',
            'rank': 'gold',
            'passport_data': {
                'riot_id': 'TestPlayer#NA1',
                'ign': 'TestPlayer',
                'region': 'NA',
                'rank': 'gold'
            }
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('passport', data)
    
    def test_create_duplicate_returns_409(self):
        """Creating duplicate passport should return 409 DUPLICATE"""
        # Create first passport
        GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='ExistingPlayer'
        )
        
        # Attempt duplicate
        payload = {
            'game_id': self.valorant.id,
            'ign': 'NewPlayer',
            'passport_data': {'riot_id': 'NewPlayer#NA1'}
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
        self.assertEqual(data['error'].get('code'), 'DUPLICATE_GAME_PASSPORT')
    
    def test_update_locked_returns_403(self):
        """Updating locked passport should return 403 LOCKED"""
        # Create locked passport
        locked_until = timezone.now() + timedelta(days=10)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='LockedPlayer',
            locked_until=locked_until
        )
        
        payload = {
            'id': passport.id,
            'ign': 'NewName'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data.get('error', {}).get('code'), 'LOCKED')
    
    def test_update_verified_returns_403(self):
        """Updating verified passport should return 403 VERIFIED_LOCK"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='VerifiedPlayer',
            verification_status='VERIFIED'
        )
        
        payload = {
            'id': passport.id,
            'ign': 'NewName'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data.get('error', {}).get('code'), 'VERIFIED_LOCK')
    
    def test_delete_success(self):
        """Deleting unlocked passport should succeed"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='DeleteMe'
        )
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps({'id': passport.id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        
        # Verify actually deleted
        self.assertFalse(GameProfile.objects.filter(id=passport.id).exists())
    
    def test_delete_locked_returns_403(self):
        """Deleting locked passport should return 403"""
        locked_until = timezone.now() + timedelta(days=10)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='LockedForDeletion',
            locked_until=locked_until
        )
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps({'id': passport.id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)


class AdminVerificationTests(TestCase):
    """Test admin verification actions"""
    
    fixtures = ['games.json']
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        self.valorant = Game.objects.get(slug='valorant')
        
        self.passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            in_game_name='PlayerToVerify',
            verification_status='PENDING'
        )
    
    def test_admin_can_mark_verified(self):
        """Admin should be able to mark passport as VERIFIED"""
        from django.contrib.admin.sites import AdminSite
        from apps.user_profile.admin import GameProfileAdmin
        from django.http import HttpRequest
        
        admin_site = AdminSite()
        admin_obj = GameProfileAdmin(GameProfile, admin_site)
        
        request = HttpRequest()
        request.user = self.admin
        
        queryset = GameProfile.objects.filter(id=self.passport.id)
        admin_obj.mark_as_verified(request, queryset)
        
        self.passport.refresh_from_db()
        self.assertEqual(self.passport.verification_status, 'VERIFIED')
        self.assertIsNotNone(self.passport.verified_at)
        self.assertEqual(self.passport.verified_by, self.admin)
    
    def test_admin_can_mark_flagged(self):
        """Admin should be able to mark passport as FLAGGED"""
        from django.contrib.admin.sites import AdminSite
        from apps.user_profile.admin import GameProfileAdmin
        from django.http import HttpRequest
        
        admin_site = AdminSite()
        admin_obj = GameProfileAdmin(GameProfile, admin_site)
        
        request = HttpRequest()
        request.user = self.admin
        
        queryset = GameProfile.objects.filter(id=self.passport.id)
        admin_obj.mark_as_flagged(request, queryset)
        
        self.passport.refresh_from_db()
        self.assertEqual(self.passport.verification_status, 'FLAGGED')


class APIContractTests(TestCase):
    """Test API responses match documented contracts"""
    
    fixtures = ['games.json']
    
    def setUp(self):
        from django.core.management import call_command
        call_command('seed_identity_configs', verbosity=0)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_games_api_contract(self):
        """GET /profile/api/games/ should match expected schema"""
        response = self.client.get('/profile/api/games/')
        data = response.json()
        
        # Top-level structure
        self.assertIn('games', data)
        
        # Game structure
        for game in data['games']:
            required_keys = ['id', 'slug', 'display_name', 'passport_schema', 'rules']
            for key in required_keys:
                self.assertIn(key, game, f"Game missing key: {key}")
            
            # Schema structure
            for field in game['passport_schema']:
                field_keys = ['key', 'label', 'type', 'required', 'immutable']
                for key in field_keys:
                    self.assertIn(key, field, f"Schema field missing key: {key}")
    
    def test_passports_api_contract(self):
        """GET /profile/api/game-passports/ should match expected schema"""
        response = self.client.get('/profile/api/game-passports/')
        data = response.json()
        
        self.assertIn('passports', data)
        self.assertIsInstance(data['passports'], list)
    
    def test_error_responses_have_structure(self):
        """Error responses should have consistent structure"""
        # Trigger 409 duplicate error
        valorant = Game.objects.get(slug='valorant')
        GameProfile.objects.create(
            user=self.user,
            game=valorant,
            in_game_name='Existing'
        )
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': valorant.id,
                'ign': 'Duplicate'
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertIn('success', data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('code', data['error'])
        self.assertIn('message', data['error'])


# Run tests
if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(['test_phase_9a6_production_hardening'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        exit(1)
    else:
        print("\n✅ All Phase 9A-6 tests passed!")
        exit(0)
