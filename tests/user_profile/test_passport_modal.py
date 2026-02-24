"""
Task 1 Tests: Game Passport Modal Schema-Driven Fields

Test Coverage:
- Settings page injects games queryset
- Settings page injects schema JSON matrix
- Modal renders Valorant-specific fields (riot_name + tagline)
- Modal renders MLBB-specific fields (User ID + Zone ID)
- Modal renders Steam-only fields (Steam ID64)
- Invalid submission shows field-level errors
"""
import json
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.games.models import Game, GamePlayerIdentityConfig
from apps.games.constants import SUPPORTED_GAMES
from apps.user_profile.models import GameProfile

User = get_user_model()


class PassportModalContextTests(TestCase):
    """Test settings page injects correct context for passport modal"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testplayer', password='testpass123')
        
        # Create test games matching SUPPORTED_GAMES
        self.valorant = Game.objects.create(
            slug='valorant',
            name='VALORANT',
            display_name='VALORANT',
            platforms=['PC'],
            category='fps'
        )
        self.cs2 = Game.objects.create(
            slug='cs2',
            name='Counter-Strike 2',
            display_name='Counter-Strike 2',
            platforms=['PC', 'Steam'],
            category='fps'
        )
        self.mlbb = Game.objects.create(
            slug='mlbb',
            name='Mobile Legends',
            display_name='Mobile Legends: Bang Bang',
            platforms=['Android', 'iOS'],
            category='moba'
        )
        
        # Create identity configs for Valorant (riot_name + tagline)
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='riot_name',
            display_name='Riot ID',
            field_type='text',
            is_required=True,
            placeholder='PlayerName',
            help_text='Your Riot ID without the tagline',
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='tagline',
            display_name='Tagline',
            field_type='text',
            is_required=True,
            placeholder='NA1',
            help_text='Your Riot tagline (e.g., NA1, EUW)',
            validation_regex=r'^[A-Za-z0-9]+$',
            order=2
        )
        
        # Create identity config for CS2 (steam_id64 only)
        GamePlayerIdentityConfig.objects.create(
            game=self.cs2,
            field_name='steam_id64',
            display_name='Steam ID64',
            field_type='text',
            is_required=True,
            placeholder='76561198012345678',
            help_text='Your 17-digit Steam ID64',
            validation_regex=r'^\d{17}$',
            order=1
        )
        
        # Create identity configs for MLBB (numeric_id + zone_id)
        GamePlayerIdentityConfig.objects.create(
            game=self.mlbb,
            field_name='numeric_id',
            display_name='Player ID',
            field_type='text',
            is_required=True,
            placeholder='123456789',
            help_text='Your numeric player ID',
            validation_regex=r'^\d+$',
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.mlbb,
            field_name='zone_id',
            display_name='Zone ID',
            field_type='text',
            is_required=True,
            placeholder='1234',
            help_text='Your zone/server ID',
            validation_regex=r'^\d+$',
            order=2
        )
    
    def test_settings_page_injects_games_queryset(self):
        """Settings page should pass 'games' queryset to template"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('games', response.context)
        
        games = list(response.context['games'])
        self.assertEqual(len(games), 3)
        
        # Verify games are ordered by name
        game_names = [g.name for g in games]
        self.assertEqual(game_names, sorted(game_names))
        
        # Verify expected games present
        game_slugs = {g.slug for g in games}
        self.assertIn('valorant', game_slugs)
        self.assertIn('cs2', game_slugs)
        self.assertIn('mlbb', game_slugs)
    
    def test_settings_page_injects_schema_json_matrix(self):
        """Settings page should inject game_schemas_json for JS consumption"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('game_schemas_json', response.context)
        
        # Parse schema JSON
        schema_json = response.context['game_schemas_json']
        schemas = json.loads(schema_json)
        
        # Verify structure for Valorant
        self.assertIn('valorant', schemas)
        valorant_schema = schemas['valorant']
        self.assertEqual(valorant_schema['game_id'], self.valorant.id)
        self.assertEqual(valorant_schema['name'], 'VALORANT')
        self.assertEqual(valorant_schema['display_name'], 'VALORANT')
        self.assertEqual(valorant_schema['platforms'], ['PC'])
        self.assertEqual(len(valorant_schema['fields']), 2)
        
        # Verify riot_name field
        riot_name_field = next(f for f in valorant_schema['fields'] if f['field_name'] == 'riot_name')
        self.assertEqual(riot_name_field['display_name'], 'Riot ID')
        self.assertEqual(riot_name_field['field_type'], 'text')
        self.assertTrue(riot_name_field['is_required'])
        self.assertEqual(riot_name_field['placeholder'], 'PlayerName')
        
        # Verify tagline field
        tagline_field = next(f for f in valorant_schema['fields'] if f['field_name'] == 'tagline')
        self.assertEqual(tagline_field['display_name'], 'Tagline')
        self.assertTrue(tagline_field['is_required'])
        self.assertEqual(tagline_field['validation_regex'], r'^[A-Za-z0-9]+$')
    
    def test_modal_renders_valorant_fields_schema(self):
        """Valorant schema should contain riot_name + tagline fields"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        schemas = json.loads(response.context['game_schemas_json'])
        valorant_schema = schemas['valorant']
        
        field_names = [f['field_name'] for f in valorant_schema['fields']]
        self.assertIn('riot_name', field_names)
        self.assertIn('tagline', field_names)
        
        # Verify field order
        self.assertEqual(valorant_schema['fields'][0]['field_name'], 'riot_name')
        self.assertEqual(valorant_schema['fields'][1]['field_name'], 'tagline')
    
    def test_modal_renders_mlbb_fields_schema(self):
        """MLBB schema should contain numeric_id + zone_id fields"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        schemas = json.loads(response.context['game_schemas_json'])
        mlbb_schema = schemas['mlbb']
        
        field_names = [f['field_name'] for f in mlbb_schema['fields']]
        self.assertIn('numeric_id', field_names)
        self.assertIn('zone_id', field_names)
        
        # Verify both are required
        for field in mlbb_schema['fields']:
            self.assertTrue(field['is_required'])
        
        # Verify regex validation for numeric fields
        numeric_id_field = next(f for f in mlbb_schema['fields'] if f['field_name'] == 'numeric_id')
        self.assertEqual(numeric_id_field['validation_regex'], r'^\d+$')
    
    def test_modal_renders_steam_only_fields_schema(self):
        """CS2 schema should contain only steam_id64 field"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        schemas = json.loads(response.context['game_schemas_json'])
        cs2_schema = schemas['cs2']
        
        # Only one field for Steam games
        self.assertEqual(len(cs2_schema['fields']), 1)
        
        steam_field = cs2_schema['fields'][0]
        self.assertEqual(steam_field['field_name'], 'steam_id64')
        self.assertEqual(steam_field['display_name'], 'Steam ID64')
        self.assertTrue(steam_field['is_required'])
        self.assertEqual(steam_field['placeholder'], '76561198012345678')
        self.assertEqual(steam_field['validation_regex'], r'^\d{17}$')
    
    def test_schema_includes_help_text_for_all_fields(self):
        """All schema fields should include help_text for user guidance"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        schemas = json.loads(response.context['game_schemas_json'])
        
        for game_slug, schema in schemas.items():
            for field in schema['fields']:
                self.assertIn('help_text', field)
                self.assertIsNotNone(field['help_text'])
                self.assertGreater(len(field['help_text']), 0, 
                    f"Field {field['field_name']} in {game_slug} has empty help_text")


class PassportAPIEndpointTests(TestCase):
    """Test /api/passports/create/ endpoint validation"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testplayer', password='testpass123')
        
        self.valorant = Game.objects.create(
            slug='valorant',
            name='VALORANT',
            display_name='VALORANT',
            platforms=['PC'],
            category='fps'
        )
        
        # Create identity configs
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='riot_name',
            display_name='Riot ID',
            field_type='text',
            is_required=True,
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='tagline',
            display_name='Tagline',
            field_type='text',
            is_required=True,
            validation_regex=r'^[A-Za-z0-9]+$',
            order=2
        )
    
    def test_invalid_submission_returns_field_errors(self):
        """POST with missing required fields should return field-level errors"""
        url = '/api/passports/create/'
        
        # Missing tagline (required field)
        payload = {
            'game': 'valorant',
            'identity_data': {
                'riot_name': 'TestPlayer',
                # Missing 'tagline'
            }
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
        
        # Should indicate missing tagline
        errors = data['errors']
        self.assertTrue(
            any('tagline' in str(errors).lower() for _ in [errors]) or
            any('required' in str(errors).lower() for _ in [errors])
        )
    
    def test_invalid_regex_validation_returns_error(self):
        """POST with invalid format should return validation error"""
        url = '/api/passports/create/'
        
        # Invalid tagline format (contains special chars)
        payload = {
            'game': 'valorant',
            'identity_data': {
                'riot_name': 'TestPlayer',
                'tagline': 'Invalid#Tag',  # Should fail regex ^[A-Za-z0-9]+$
            }
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
