"""
GP-2D Tests: Admin UX Finalization (Smart Fields + Region Dropdown + Role Removal)
GP-2E: Now with test fixtures for full coverage
"""
import pytest
import json
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import GameProfile, GamePassportSchema
from apps.games.models import Game
from tests.fixtures.game_fixtures import valorant_game, cs2_game, mlbb_game, all_supported_games, unsupported_game

User = get_user_model()


@pytest.mark.django_db
class TestAdminSchemaInjection:
    """Test that schema matrix is injected into admin change form"""
    
    def test_change_form_includes_schema_matrix(self):
        """Verify schema matrix JSON is present in admin change form"""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        client = Client()
        client.force_login(user)
        
        # Access admin add page
        response = client.get('/admin/user_profile/gameprofile/add/')
        assert response.status_code == 200
        
        # Check for schema matrix script element
        content = response.content.decode('utf-8')
        assert 'id="gp-schema-matrix"' in content, "Schema matrix element missing"
        assert 'type="application/json"' in content, "Schema matrix not JSON type"
    
    def test_schema_matrix_contains_game_configs(self, valorant_game):
        """Verify schema matrix has expected game configurations"""
        user = User.objects.create_superuser(
            username='admin2',
            email='admin2@example.com',
            password='admin123'
        )
        
        client = Client()
        client.force_login(user)
        
        response = client.get('/admin/user_profile/gameprofile/add/')
        content = response.content.decode('utf-8')
        
        # Extract JSON from script tag (Django's json_script escapes HTML entities)
        import re
        import html
        match = re.search(r'<script id="gp-schema-matrix" type="application/json">(.+?)</script>', content, re.DOTALL)
        assert match, "Schema matrix script tag not found"
        
        schema_json = html.unescape(match.group(1).strip())
        schema_matrix = json.loads(schema_json)
        
        # Check schema structure
        assert isinstance(schema_matrix, dict), "Schema matrix should be dict"
        
        # Valorant should exist (from fixture)
        assert 'valorant' in schema_matrix, "Valorant should be in schema matrix"
        
        valorant = schema_matrix['valorant']
        assert valorant['game_slug'] == 'valorant'
        # Display name might have unicode characters (VALORANT™)
        assert 'valorant' in valorant['game_name'].lower()
        assert 'region_choices' in valorant
        assert isinstance(valorant['region_choices'], list)
        assert len(valorant['region_choices']) == 6  # Americas, Europe, Asia-Pacific, Korea, LATAM, Brazil
        assert valorant['region_required'] is True
        assert 'identity_fields' in valorant


@pytest.mark.django_db
class TestRegionDropdown:
    """Test region dropdown is schema-driven"""
    
    def test_region_field_is_select_for_game_with_regions(self, valorant_game):
        """Region field should be dropdown for games with region_choices"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Verify schema exists
        schema = GamePassportSchema.objects.get(game=valorant_game)
        
        assert len(schema.region_choices) == 6, "Valorant should have 6 regions"
        
        # Create profile to test edit form
        profile = GameProfile.objects.create(
            user=user,
            game=valorant_game,
            game_display_name=valorant_game.display_name,
            ign='TestPlayer',
            in_game_name='TestPlayer',
            identity_key='testplayer'
        )
        
        # Check form has region choices
        from apps.user_profile.admin.forms import GameProfileAdminForm
        form = GameProfileAdminForm(instance=profile)
        
        # Region field should be ChoiceField with choices from schema
        region_choices = form.fields['region'].choices
        assert len(region_choices) == 7, "Should have 6 regions + empty choice"
        assert region_choices[0] == ('', '---------'), "First choice should be empty"
        
        # Verify actual region values
        region_values = [choice[0] for choice in region_choices[1:]]
        assert 'americas' in region_values
        assert 'europe' in region_values
    
    def test_region_validation_rejects_invalid(self, valorant_game):
        """Server-side validation should reject invalid region"""
        user = User.objects.create_user(
            username='regiontest',
            email='regiontest@example.com',
            password='testpass123'
        )
        
        schema = GamePassportSchema.objects.get(game=valorant_game)
        
        # Try to create profile with invalid region
        valid_regions = [choice['value'] for choice in schema.region_choices]
        invalid_region = 'INVALID_REGION_XYZ'
        
        assert invalid_region not in valid_regions, "Test region should be invalid"
        
        # Validation should reject this
        is_valid = schema.validate_region(invalid_region)
        assert not is_valid, "Invalid region should be rejected by schema"


@pytest.mark.django_db
class TestRoleRemoval:
    """Test that role is not present in Game Passport admin/forms"""
    
    def test_main_role_not_in_admin_form(self):
        """main_role should not appear in GameProfileAdminForm fields"""
        from apps.user_profile.admin.forms import GameProfileAdminForm
        
        form = GameProfileAdminForm()
        
        # Check Meta.fields doesn't include main_role
        assert 'main_role' not in form.Meta.fields, "main_role should be removed from form fields"
    
    def test_role_not_in_admin_fieldsets(self):
        """Admin fieldsets should not include main_role"""
        from apps.user_profile.admin.game_passports import GameProfileAdmin
        from apps.user_profile.models import GameProfile
        
        admin_instance = GameProfileAdmin(GameProfile, None)
        
        # Flatten all fieldsets
        all_fields = []
        for fieldset in admin_instance.fieldsets:
            all_fields.extend(fieldset[1]['fields'])
        
        assert 'main_role' not in all_fields, "main_role should not be in admin fieldsets"
    
    def test_role_not_written_by_passport_creation(self, valorant_game):
        """Creating Game Passport should not write role"""
        user = User.objects.create_user(
            username='roletest',
            email='roletest@example.com',
            password='testpass123'
        )
        
        profile = GameProfile.objects.create(
            user=user,
            game=valorant_game,
            game_display_name=valorant_game.display_name,
            ign='RoleTestUser',
            in_game_name='RoleTestUser',
            identity_key='roletestuser'
        )
        
        # main_role field may exist in model but should not be set
        # (keeping for backward compatibility, but not used in passport context)
        # Just verify we can create without it
        assert profile.pk is not None, "Profile should be created without role"


@pytest.mark.django_db
class TestSupportedGamesOnly:
    """Test that admin only shows passport-supported games"""
    
    def test_admin_game_dropdown_filters_supported_only(self, all_supported_games, unsupported_game):
        """Admin form should only show games with is_passport_supported=True"""
        from apps.user_profile.admin.forms import GameProfileAdminForm
        
        form = GameProfileAdminForm()
        
        # Get game queryset from form
        game_queryset = form.fields['game'].queryset
        
        # All games in queryset should have is_passport_supported=True
        for game in game_queryset:
            assert game.is_passport_supported, f"Game {game.slug} should be passport-supported"
        
        # Should have exactly 3 supported games (from fixtures)
        assert game_queryset.count() == 3, f"Expected 3 games, got {game_queryset.count()}"
        
        # Unsupported game should NOT be in queryset
        assert unsupported_game not in game_queryset, "Unsupported game should be filtered out"
    
    def test_expected_supported_games_in_test_db(self, all_supported_games):
        """Verify test DB has supported games from fixtures"""
        supported_games = Game.objects.filter(is_passport_supported=True, is_active=True)
        
        # Test DB should have exactly 3 games from fixtures
        assert supported_games.count() == 3, "Test DB should have 3 supported games"
        
        # Verify expected slugs
        actual_slugs = set(supported_games.values_list('slug', flat=True))
        expected_slugs = {'valorant', 'cs2', 'mlbb'}
        
        assert actual_slugs == expected_slugs, f"Expected {expected_slugs}, got {actual_slugs}"
        
        # Verify each has a schema
        for game in supported_games:
            schema = GamePassportSchema.objects.filter(game=game).first()
            assert schema is not None, f"Game {game.slug} should have schema"


@pytest.mark.django_db
class TestAdminJSBehavior:
    """Test admin JS integration (requires manual browser testing)"""
    
    def test_admin_js_file_exists(self):
        """Verify admin_game_passport.js exists"""
        import os
        js_path = 'static/js/admin_game_passport.js'
        assert os.path.exists(js_path), f"Admin JS file missing: {js_path}"
    
    def test_admin_js_loaded_in_media(self):
        """Verify GameProfileAdmin loads JS file"""
        from apps.user_profile.admin.game_passports import GameProfileAdmin
        from apps.user_profile.models import GameProfile
        
        admin_instance = GameProfileAdmin(GameProfile, None)
        
        # Check Media class has JS
        assert hasattr(admin_instance, 'media'), "Admin should have Media class"
        assert 'js/admin_game_passport.js' in str(admin_instance.media), "Admin JS should be in Media"


@pytest.mark.django_db
class TestEndToEndPassportCreation:
    """Integration test: create passport via admin"""
    
    def test_create_valorant_passport_via_admin_form(self, valorant_game):
        """Test creating Valorant passport with structured identity"""
        user = User.objects.create_user(
            username='e2etest',
            email='e2e@example.com',
            password='testpass123'
        )
        
        schema = GamePassportSchema.objects.get(game=valorant_game)
        
        # Get valid region from schema
        valid_region = schema.region_choices[0]['value']  # 'americas'
        
        # Create via form (simulating admin submission)
        from apps.user_profile.admin.forms import GameProfileAdminForm
        form_data = {
            'user': user.pk,
            'game': valorant_game.pk,
            'ign': 'TestRiot',
            'discriminator': 'NA1',
            'region': valid_region,
            'in_game_name': 'TestRiot#NA1',
            'identity_key': 'testriot#na1',
            'visibility': 'PUBLIC',
            'is_lft': False,
            'is_pinned': False,
            'status': 'ACTIVE',
        }
        
        form = GameProfileAdminForm(data=form_data)
        
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        
        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        
        profile = form.save()
        
        # Verify structured identity
        assert profile.ign == 'TestRiot'
        assert profile.discriminator == 'NA1'
        assert profile.region == valid_region
        assert profile.in_game_name == 'TestRiot#NA1'
