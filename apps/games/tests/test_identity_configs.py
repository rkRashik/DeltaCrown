"""
Tests for Game Identity Field Configurations

Validates that seed_games.py properly creates identity field configs for all games
and that the API endpoint returns them correctly ordered.

Run with: python manage.py test apps.games.tests.test_identity_configs
"""
import pytest
from django.core.management import call_command
from django.test import TestCase
from apps.games.models import Game, GamePlayerIdentityConfig


class TestGameIdentityConfigs(TestCase):
    """Test game identity field configurations"""
    
    @classmethod
    def setUpClass(cls):
        """Seed games once for all tests"""
        super().setUpClass()
        call_command('seed_games')
    
    def test_all_games_have_identity_configs(self):
        """Each game must have at least one identity config"""
        games = Game.objects.all()
        assert games.count() == 11, "Expected 11 games"
        
        for game in games:
            configs = GamePlayerIdentityConfig.objects.filter(game=game)
            assert configs.count() > 0, f"{game.name} has no identity configs"
    
    def test_identity_config_counts_match_catalog(self):
        """Verify each game has the expected number of identity fields"""
        expected_counts = {
            'valorant': 6,
            'cs2': 5,
            'dota2': 5,
            'ea-fc': 5,
            'efootball': 6,
            'pubgm': 6,
            'mlbb': 6,
            'freefire': 4,
            'codm': 6,
            'rocketleague': 5,
            'r6siege': 6,
        }
        
        for slug, expected_count in expected_counts.items():
            game = Game.objects.filter(slug=slug).first()
            if game:
                actual_count = GamePlayerIdentityConfig.objects.filter(game=game).count()
                assert actual_count == expected_count, \
                    f"{game.name} has {actual_count} configs, expected {expected_count}"
    
    def test_total_identity_configs_count(self):
        """Total identity configs should be 60 (sum of all games)"""
        total = GamePlayerIdentityConfig.objects.count()
        assert total == 60, f"Expected 60 total identity configs, got {total}"
    
    def test_identity_fields_are_ordered(self):
        """Identity fields must have sequential ordering starting from 1"""
        games = Game.objects.all()
        
        for game in games:
            configs = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
            orders = [c.order for c in configs]
            
            # Check that orders start at 1 and are sequential
            assert orders[0] == 1, f"{game.name} first field order is {orders[0]}, expected 1"
            assert orders == list(range(1, len(orders) + 1)), \
                f"{game.name} has non-sequential ordering: {orders}"
    
    def test_required_fields_have_correct_flags(self):
        """Primary identity fields should be marked as required"""
        # Check a few known required fields
        valorant = Game.objects.get(slug='valorant')
        riot_id = GamePlayerIdentityConfig.objects.get(game=valorant, field_name='riot_id')
        assert riot_id.is_required is True, "VALORANT riot_id should be required"
        
        cs2 = Game.objects.get(slug='cs2')
        steam_id = GamePlayerIdentityConfig.objects.get(game=cs2, field_name='steam_id')
        assert steam_id.is_required is True, "CS2 steam_id should be required"
        assert steam_id.is_immutable is True, "CS2 steam_id should be immutable"
    
    def test_optional_fields_exist(self):
        """Each game should have at least one optional field"""
        games = Game.objects.all()
        
        for game in games:
            optional_fields = GamePlayerIdentityConfig.objects.filter(
                game=game, 
                is_required=False
            )
            assert optional_fields.exists(), \
                f"{game.name} has no optional fields (expected ign, rank, role, etc.)"
    
    def test_seeding_is_idempotent(self):
        """Running seed_games multiple times should not create duplicates"""
        initial_count = GamePlayerIdentityConfig.objects.count()
        
        # Run seed again
        call_command('seed_games')
        
        after_count = GamePlayerIdentityConfig.objects.count()
        assert after_count == initial_count, \
            f"Seeding created duplicates: {initial_count} -> {after_count}"
    
    def test_field_names_are_unique_per_game(self):
        """No game should have duplicate field names"""
        games = Game.objects.all()
        
        for game in games:
            field_names = list(
                GamePlayerIdentityConfig.objects.filter(game=game)
                .values_list('field_name', flat=True)
            )
            unique_names = set(field_names)
            assert len(field_names) == len(unique_names), \
                f"{game.name} has duplicate field names: {field_names}"


class TestIdentityConfigAPIData(TestCase):
    """Test that identity configs are correctly exposed via API"""
    
    @classmethod
    def setUpClass(cls):
        """Seed games once for all tests"""
        super().setUpClass()
        call_command('seed_games')
    
    def test_valorant_has_all_fields(self):
        """VALORANT should have 6 identity fields in correct order"""
        game = Game.objects.get(slug='valorant')
        configs = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        field_names = [c.field_name for c in configs]
        expected = ['riot_id', 'ign', 'region', 'rank', 'peak_rank', 'role']
        assert field_names == expected, \
            f"VALORANT fields mismatch: {field_names} != {expected}"
    
    def test_cs2_has_all_fields(self):
        """CS2 should have 5 identity fields in correct order"""
        game = Game.objects.get(slug='cs2')
        configs = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        
        field_names = [c.field_name for c in configs]
        expected = ['steam_id', 'ign', 'region', 'premier_rating', 'role']
        assert field_names == expected, \
            f"CS2 fields mismatch: {field_names} != {expected}"
    
    def test_mlbb_has_dual_identifiers(self):
        """MLBB should have both game_id and server_id as required fields"""
        game = Game.objects.get(slug='mlbb')
        
        game_id = GamePlayerIdentityConfig.objects.get(game=game, field_name='game_id')
        assert game_id.is_required is True, "MLBB game_id should be required"
        assert game_id.is_immutable is True, "MLBB game_id should be immutable"
        
        server_id = GamePlayerIdentityConfig.objects.get(game=game, field_name='server_id')
        assert server_id.is_required is True, "MLBB server_id should be required"
        assert server_id.is_immutable is True, "MLBB server_id should be immutable"

class TestGamePassportDropdownOptions(TestCase):
    """Test dropdown options for SELECT fields in Game Passports"""
    
    @classmethod
    def setUpClass(cls):
        """Seed games once for all tests"""
        super().setUpClass()
        call_command('seed_games')
    
    def test_all_games_have_passport_schemas(self):
        """Each game must have a GamePassportSchema with dropdown options"""
        from apps.user_profile.models import GamePassportSchema
        
        games = Game.objects.all()
        assert games.count() == 11, "Expected 11 games"
        
        for game in games:
            schema = GamePassportSchema.objects.filter(game=game).first()
            assert schema is not None, f"{game.name} has no GamePassportSchema"
    
    def test_mlbb_has_server_choices(self):
        """MLBB must have server_choices for Server Region field"""
        from apps.user_profile.models import GamePassportSchema
        
        game = Game.objects.get(slug='mlbb')
        schema = GamePassportSchema.objects.get(game=game)
        
        assert schema.server_choices is not None, "MLBB server_choices is None"
        assert len(schema.server_choices) > 0, "MLBB server_choices is empty"
        assert len(schema.server_choices) == 5, f"MLBB should have 5 server regions, got {len(schema.server_choices)}"
        
        # Verify structure
        for choice in schema.server_choices:
            assert 'value' in choice, "server_choices missing 'value' key"
            assert 'label' in choice, "server_choices missing 'label' key"
    
    def test_ea_fc_has_platform_division_mode_choices(self):
        """EA FC must have platform_choices, division_choices, and mode_choices"""
        from apps.user_profile.models import GamePassportSchema
        
        game = Game.objects.get(slug='ea-fc')
        schema = GamePassportSchema.objects.get(game=game)
        
        # Test platform_choices
        assert schema.platform_choices is not None, "EA FC platform_choices is None"
        assert len(schema.platform_choices) > 0, "EA FC platform_choices is empty"
        assert len(schema.platform_choices) == 6, f"EA FC should have 6 platforms, got {len(schema.platform_choices)}"
        
        # Test division_choices
        assert schema.division_choices is not None, "EA FC division_choices is None"
        assert len(schema.division_choices) > 0, "EA FC division_choices is empty"
        assert len(schema.division_choices) == 11, f"EA FC should have 11 divisions, got {len(schema.division_choices)}"
        
        # Test mode_choices
        assert schema.mode_choices is not None, "EA FC mode_choices is None"
        assert len(schema.mode_choices) > 0, "EA FC mode_choices is empty"
        assert len(schema.mode_choices) == 5, f"EA FC should have 5 modes, got {len(schema.mode_choices)}"
        
        # Verify structure
        for choice in schema.platform_choices:
            assert 'value' in choice, "platform_choices missing 'value' key"
            assert 'label' in choice, "platform_choices missing 'label' key"
        
        for choice in schema.division_choices:
            assert 'value' in choice, "division_choices missing 'value' key"
            assert 'label' in choice, "division_choices missing 'label' key"
            assert 'tier' in choice, "division_choices missing 'tier' key"
    
    def test_free_fire_has_server_choices(self):
        """Free Fire must have server_choices for Server field"""
        from apps.user_profile.models import GamePassportSchema
        
        game = Game.objects.get(slug='freefire')
        schema = GamePassportSchema.objects.get(game=game)
        
        assert schema.server_choices is not None, "Free Fire server_choices is None"
        assert len(schema.server_choices) > 0, "Free Fire server_choices is empty"
        assert len(schema.server_choices) == 4, f"Free Fire should have 4 server regions, got {len(schema.server_choices)}"
    
    def test_valorant_has_rank_and_role_choices(self):
        """VALORANT must have rank_choices and role_choices"""
        from apps.user_profile.models import GamePassportSchema
        
        game = Game.objects.get(slug='valorant')
        schema = GamePassportSchema.objects.get(game=game)
        
        assert schema.rank_choices is not None, "VALORANT rank_choices is None"
        assert len(schema.rank_choices) > 0, "VALORANT rank_choices is empty"
        assert len(schema.rank_choices) == 25, f"VALORANT should have 25 ranks, got {len(schema.rank_choices)}"
        
        assert schema.role_choices is not None, "VALORANT role_choices is None"
        assert len(schema.role_choices) > 0, "VALORANT role_choices is empty"
        assert len(schema.role_choices) == 4, f"VALORANT should have 4 roles, got {len(schema.role_choices)}"
    
    def test_cs2_has_premier_rating_choices(self):
        """CS2 must have premier_rating_choices for Premier Rating field"""
        from apps.user_profile.models import GamePassportSchema
        
        game = Game.objects.get(slug='cs2')
        schema = GamePassportSchema.objects.get(game=game)
        
        assert schema.premier_rating_choices is not None, "CS2 premier_rating_choices is None"
        assert len(schema.premier_rating_choices) > 0, "CS2 premier_rating_choices is empty"
        assert len(schema.premier_rating_choices) == 7, f"CS2 should have 7 premier rating tiers, got {len(schema.premier_rating_choices)}"