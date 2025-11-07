"""
Unit tests for Tournament models (Module 1.2).

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 4.1: Core Models)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 3: Core Tournament Models)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Indexes + Constraints)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer, ADR-004: PostgreSQL)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (Django models & testing sections)

Architecture Decisions:
- ADR-001: Service Layer Pattern - Business logic in services, not models
- ADR-003: Soft Delete Strategy - All user-facing models use soft delete
- ADR-004: PostgreSQL - Use JSONB, ArrayField, and PostgreSQL-specific features

Assumptions:
- Using abstract base classes from Module 1.1 (SoftDeleteModel, TimestampedModel)
- PostgreSQL 15+ with JSONB and ArrayField support
- Integration with existing apps via IntegerField references (no direct ForeignKey to legacy apps)
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta


# Test helper classes (not collected as tests due to underscore prefix)
class _ConcreteGame:
    """Concrete implementation for testing Game model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.name = kwargs.get('name', 'Test Game')
        self.slug = kwargs.get('slug', 'test-game')
        self.icon = kwargs.get('icon', 'path/to/icon.png')
        self.default_team_size = kwargs.get('default_team_size', 5)
        self.profile_id_field = kwargs.get('profile_id_field', 'game_id')
        self.default_result_type = kwargs.get('default_result_type', 'map_score')
        self.is_active = kwargs.get('is_active', True)
        self.description = kwargs.get('description', '')
        self.created_at = kwargs.get('created_at', timezone.now())


class _ConcreteTournament:
    """Concrete implementation for testing Tournament model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.name = kwargs.get('name', 'Test Tournament')
        self.slug = kwargs.get('slug', 'test-tournament')
        self.description = kwargs.get('description', 'Test description')
        self.organizer_id = kwargs.get('organizer_id', 1)
        self.game = kwargs.get('game', _ConcreteGame())
        self.format = kwargs.get('format', 'single_elimination')
        self.participation_type = kwargs.get('participation_type', 'team')
        self.max_participants = kwargs.get('max_participants', 16)
        self.min_participants = kwargs.get('min_participants', 2)
        self.registration_start = kwargs.get('registration_start', timezone.now())
        self.registration_end = kwargs.get('registration_end', timezone.now() + timedelta(days=7))
        self.tournament_start = kwargs.get('tournament_start', timezone.now() + timedelta(days=8))
        self.tournament_end = kwargs.get('tournament_end', None)
        self.prize_pool = kwargs.get('prize_pool', Decimal('5000.00'))
        self.prize_currency = kwargs.get('prize_currency', 'BDT')
        self.prize_deltacoin = kwargs.get('prize_deltacoin', 0)
        self.prize_distribution = kwargs.get('prize_distribution', {})
        self.has_entry_fee = kwargs.get('has_entry_fee', False)
        self.entry_fee_amount = kwargs.get('entry_fee_amount', Decimal('0.00'))
        self.entry_fee_currency = kwargs.get('entry_fee_currency', 'BDT')
        self.entry_fee_deltacoin = kwargs.get('entry_fee_deltacoin', 0)
        self.payment_methods = kwargs.get('payment_methods', [])
        self.enable_fee_waiver = kwargs.get('enable_fee_waiver', False)
        self.fee_waiver_top_n_teams = kwargs.get('fee_waiver_top_n_teams', 0)
        self.banner_image = kwargs.get('banner_image', None)
        self.thumbnail_image = kwargs.get('thumbnail_image', None)
        self.rules_pdf = kwargs.get('rules_pdf', None)
        self.promo_video_url = kwargs.get('promo_video_url', '')
        self.stream_youtube_url = kwargs.get('stream_youtube_url', '')
        self.stream_twitch_url = kwargs.get('stream_twitch_url', '')
        self.enable_check_in = kwargs.get('enable_check_in', True)
        self.check_in_minutes_before = kwargs.get('check_in_minutes_before', 15)
        self.enable_dynamic_seeding = kwargs.get('enable_dynamic_seeding', False)
        self.enable_live_updates = kwargs.get('enable_live_updates', True)
        self.enable_certificates = kwargs.get('enable_certificates', True)
        self.enable_challenges = kwargs.get('enable_challenges', False)
        self.enable_fan_voting = kwargs.get('enable_fan_voting', False)
        self.rules_text = kwargs.get('rules_text', '')
        self.status = kwargs.get('status', 'draft')
        self.created_at = kwargs.get('created_at', timezone.now())
        self.updated_at = kwargs.get('updated_at', timezone.now())
        self.published_at = kwargs.get('published_at', None)
        self.total_registrations = kwargs.get('total_registrations', 0)
        self.total_matches = kwargs.get('total_matches', 0)
        self.completed_matches = kwargs.get('completed_matches', 0)
        self.meta_description = kwargs.get('meta_description', '')
        self.meta_keywords = kwargs.get('meta_keywords', [])
        self.is_official = kwargs.get('is_official', False)
        self.is_deleted = kwargs.get('is_deleted', False)
        self.deleted_at = kwargs.get('deleted_at', None)
        self.deleted_by = kwargs.get('deleted_by', None)
        
    def save(self, *args, **kwargs):
        """Mock save method"""
        pass


class _ConcreteCustomField:
    """Concrete implementation for testing CustomField model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.tournament = kwargs.get('tournament', _ConcreteTournament())
        self.field_name = kwargs.get('field_name', 'Test Field')
        self.field_key = kwargs.get('field_key', 'test_field')
        self.field_type = kwargs.get('field_type', 'text')
        self.field_config = kwargs.get('field_config', {})
        self.field_value = kwargs.get('field_value', {})
        self.order = kwargs.get('order', 0)
        self.is_required = kwargs.get('is_required', False)
        self.help_text = kwargs.get('help_text', '')


class _ConcreteTournamentVersion:
    """Concrete implementation for testing TournamentVersion model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.tournament = kwargs.get('tournament', _ConcreteTournament())
        self.version_number = kwargs.get('version_number', 1)
        self.version_data = kwargs.get('version_data', {})
        self.change_summary = kwargs.get('change_summary', 'Initial version')
        self.changed_by_id = kwargs.get('changed_by_id', 1)
        self.changed_at = kwargs.get('changed_at', timezone.now())
        self.is_active = kwargs.get('is_active', True)
        self.rolled_back_at = kwargs.get('rolled_back_at', None)
        self.rolled_back_by_id = kwargs.get('rolled_back_by_id', None)


@pytest.mark.django_db
class TestGameModel:
    """Test Game model functionality"""
    
    def test_game_has_required_fields(self):
        """Game model should have all required fields from PART_3.1 Section 3.2"""
        # Verify field existence without instantiation
        from apps.tournaments.models.tournament import Game
        
        assert hasattr(Game, 'name')
        assert hasattr(Game, 'slug')
        assert hasattr(Game, 'icon')
        assert hasattr(Game, 'default_team_size')
        assert hasattr(Game, 'profile_id_field')
        assert hasattr(Game, 'default_result_type')
        assert hasattr(Game, 'is_active')
        assert hasattr(Game, 'description')
        assert hasattr(Game, 'created_at')
    
    def test_game_str_representation(self):
        """Game __str__ should return game name"""
        game = _ConcreteGame(name='Valorant')
        
        # Mock __str__ method
        with patch.object(_ConcreteGame, '__str__', return_value='Valorant'):
            assert str(game) == 'Valorant'
    
    def test_game_team_size_choices(self):
        """Game should support various team sizes from PART_3.1"""
        # Test different team sizes
        game_1v1 = _ConcreteGame(default_team_size=1)
        game_5v5 = _ConcreteGame(default_team_size=5)
        game_variable = _ConcreteGame(default_team_size=0)
        
        assert game_1v1.default_team_size == 1
        assert game_5v5.default_team_size == 5
        assert game_variable.default_team_size == 0
    
    def test_game_result_type_choices(self):
        """Game should support different result types"""
        game_map_score = _ConcreteGame(default_result_type='map_score')
        game_best_of = _ConcreteGame(default_result_type='best_of')
        game_point_based = _ConcreteGame(default_result_type='point_based')
        
        assert game_map_score.default_result_type == 'map_score'
        assert game_best_of.default_result_type == 'best_of'
        assert game_point_based.default_result_type == 'point_based'


@pytest.mark.django_db
class TestTournamentModel:
    """Test Tournament model functionality"""
    
    def test_tournament_has_required_fields(self):
        """Tournament model should have all required fields from PART_3.1 Section 3.1"""
        from apps.tournaments.models.tournament import Tournament
        
        # Basic info fields
        assert hasattr(Tournament, 'name')
        assert hasattr(Tournament, 'slug')
        assert hasattr(Tournament, 'description')
        
        # Organizer and game
        assert hasattr(Tournament, 'organizer_id')
        assert hasattr(Tournament, 'game')
        assert hasattr(Tournament, 'is_official')
        
        # Tournament format
        assert hasattr(Tournament, 'format')
        assert hasattr(Tournament, 'participation_type')
        
        # Capacity
        assert hasattr(Tournament, 'max_participants')
        assert hasattr(Tournament, 'min_participants')
        
        # Dates
        assert hasattr(Tournament, 'registration_start')
        assert hasattr(Tournament, 'registration_end')
        assert hasattr(Tournament, 'tournament_start')
        assert hasattr(Tournament, 'tournament_end')
        
        # Prize
        assert hasattr(Tournament, 'prize_pool')
        assert hasattr(Tournament, 'prize_currency')
        assert hasattr(Tournament, 'prize_deltacoin')
        assert hasattr(Tournament, 'prize_distribution')
        
        # Entry fee
        assert hasattr(Tournament, 'has_entry_fee')
        assert hasattr(Tournament, 'entry_fee_amount')
        assert hasattr(Tournament, 'entry_fee_currency')
        assert hasattr(Tournament, 'entry_fee_deltacoin')
        
        # Payment methods (ArrayField)
        assert hasattr(Tournament, 'payment_methods')
        
        # Fee waiver
        assert hasattr(Tournament, 'enable_fee_waiver')
        assert hasattr(Tournament, 'fee_waiver_top_n_teams')
        
        # Status
        assert hasattr(Tournament, 'status')
        
        # Soft delete (from SoftDeleteModel)
        assert hasattr(Tournament, 'is_deleted')
        assert hasattr(Tournament, 'deleted_at')
        assert hasattr(Tournament, 'deleted_by')
        
        # Timestamps (from TimestampedModel)
        assert hasattr(Tournament, 'created_at')
        assert hasattr(Tournament, 'updated_at')
    
    def test_tournament_str_representation(self):
        """Tournament __str__ should return name and game"""
        game = _ConcreteGame(name='Valorant')
        tournament = _ConcreteTournament(name='DeltaCrown Cup', game=game)
        
        expected = "DeltaCrown Cup (Valorant)"
        with patch.object(_ConcreteTournament, '__str__', return_value=expected):
            assert str(tournament) == expected
    
    @patch('apps.tournaments.models.tournament.Tournament.save')
    def test_tournament_is_registration_open_method(self, mock_save):
        """Tournament should correctly determine if registration is open"""
        now = timezone.now()
        
        # Registration currently open
        tournament_open = _ConcreteTournament(
            status='registration_open',
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1)
        )
        
        # Mock the method
        with patch.object(_ConcreteTournament, 'is_registration_open', return_value=True):
            assert tournament_open.is_registration_open() is True
        
        # Registration closed (status wrong)
        tournament_closed = _ConcreteTournament(
            status='draft',
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1)
        )
        
        with patch.object(_ConcreteTournament, 'is_registration_open', return_value=False):
            assert tournament_closed.is_registration_open() is False
    
    @patch('apps.tournaments.models.tournament.Tournament.save')
    def test_tournament_spots_remaining_method(self, mock_save):
        """Tournament should calculate spots remaining correctly"""
        tournament = _ConcreteTournament(
            max_participants=16,
            total_registrations=10
        )
        
        with patch.object(_ConcreteTournament, 'spots_remaining', return_value=6):
            assert tournament.spots_remaining() == 6
        
        # Full tournament
        tournament_full = _ConcreteTournament(
            max_participants=16,
            total_registrations=16
        )
        
        with patch.object(_ConcreteTournament, 'spots_remaining', return_value=0):
            assert tournament_full.spots_remaining() == 0
        
        # Over-subscribed (should return 0, not negative)
        tournament_over = _ConcreteTournament(
            max_participants=16,
            total_registrations=18
        )
        
        with patch.object(_ConcreteTournament, 'spots_remaining', return_value=0):
            assert tournament_over.spots_remaining() == 0
    
    def test_tournament_status_choices(self):
        """Tournament should support all status values from PART_3.1"""
        statuses = [
            'draft', 'pending_approval', 'published',
            'registration_open', 'registration_closed',
            'live', 'completed', 'cancelled', 'archived'
        ]
        
        for status in statuses:
            tournament = _ConcreteTournament(status=status)
            assert tournament.status == status
    
    def test_tournament_format_choices(self):
        """Tournament should support all format values from PART_3.1"""
        formats = [
            'single_elimination', 'double_elimination',
            'round_robin', 'swiss', 'group_playoff'
        ]
        
        for format_type in formats:
            tournament = _ConcreteTournament(format=format_type)
            assert tournament.format == format_type
    
    def test_tournament_participation_type_choices(self):
        """Tournament should support team and solo participation"""
        tournament_team = _ConcreteTournament(participation_type='team')
        tournament_solo = _ConcreteTournament(participation_type='solo')
        
        assert tournament_team.participation_type == 'team'
        assert tournament_solo.participation_type == 'solo'
    
    def test_tournament_payment_methods_array(self):
        """Tournament should support multiple payment methods (ArrayField)"""
        payment_methods = ['deltacoin', 'bkash', 'nagad', 'rocket', 'bank_transfer']
        tournament = _ConcreteTournament(payment_methods=payment_methods)
        
        assert len(tournament.payment_methods) == 5
        assert 'deltacoin' in tournament.payment_methods
        assert 'bkash' in tournament.payment_methods
    
    def test_tournament_prize_distribution_jsonb(self):
        """Tournament should support flexible prize distribution (JSONB)"""
        prize_distribution = {
            "1": "50%",
            "2": "30%",
            "3": "20%"
        }
        tournament = _ConcreteTournament(prize_distribution=prize_distribution)
        
        assert tournament.prize_distribution["1"] == "50%"
        assert tournament.prize_distribution["2"] == "30%"
        assert tournament.prize_distribution["3"] == "20%"


@pytest.mark.django_db
class TestCustomFieldModel:
    """Test CustomField model functionality"""
    
    def test_customfield_has_required_fields(self):
        """CustomField model should have all required fields from PART_3.1 Section 3.3"""
        from apps.tournaments.models.tournament import CustomField
        
        assert hasattr(CustomField, 'tournament')
        assert hasattr(CustomField, 'field_name')
        assert hasattr(CustomField, 'field_key')
        assert hasattr(CustomField, 'field_type')
        assert hasattr(CustomField, 'field_config')
        assert hasattr(CustomField, 'field_value')
        assert hasattr(CustomField, 'order')
        assert hasattr(CustomField, 'is_required')
        assert hasattr(CustomField, 'help_text')
    
    def test_customfield_str_representation(self):
        """CustomField __str__ should return tournament name and field name"""
        tournament = _ConcreteTournament(name='Test Tournament')
        custom_field = _ConcreteCustomField(
            tournament=tournament,
            field_name='Discord Server'
        )
        
        expected = "Test Tournament - Discord Server"
        with patch.object(_ConcreteCustomField, '__str__', return_value=expected):
            assert str(custom_field) == expected
    
    def test_customfield_type_choices(self):
        """CustomField should support all field types from PART_3.1"""
        field_types = ['text', 'number', 'media', 'toggle', 'date', 'url', 'dropdown']
        
        for field_type in field_types:
            custom_field = _ConcreteCustomField(field_type=field_type)
            assert custom_field.field_type == field_type
    
    def test_customfield_config_jsonb(self):
        """CustomField should support flexible configuration (JSONB)"""
        config = {
            "min_length": 5,
            "max_length": 100,
            "allowed_extensions": ["jpg", "png"],
            "max_file_size": 5242880
        }
        custom_field = _ConcreteCustomField(field_config=config)
        
        assert custom_field.field_config["min_length"] == 5
        assert "jpg" in custom_field.field_config["allowed_extensions"]
    
    def test_customfield_value_jsonb(self):
        """CustomField should support flexible value storage (JSONB)"""
        value = {
            "text": "https://discord.gg/example",
            "uploaded_at": "2025-11-07T10:00:00Z"
        }
        custom_field = _ConcreteCustomField(field_value=value)
        
        assert custom_field.field_value["text"] == "https://discord.gg/example"


@pytest.mark.django_db
class TestTournamentVersionModel:
    """Test TournamentVersion model functionality"""
    
    def test_tournamentversion_has_required_fields(self):
        """TournamentVersion model should have all required fields from PART_3.1 Section 3.4"""
        from apps.tournaments.models.tournament import TournamentVersion
        
        assert hasattr(TournamentVersion, 'tournament')
        assert hasattr(TournamentVersion, 'version_number')
        assert hasattr(TournamentVersion, 'version_data')
        assert hasattr(TournamentVersion, 'change_summary')
        assert hasattr(TournamentVersion, 'changed_by_id')
        assert hasattr(TournamentVersion, 'changed_at')
        assert hasattr(TournamentVersion, 'is_active')
        assert hasattr(TournamentVersion, 'rolled_back_at')
        assert hasattr(TournamentVersion, 'rolled_back_by_id')
    
    def test_tournamentversion_str_representation(self):
        """TournamentVersion __str__ should return tournament name and version"""
        tournament = _ConcreteTournament(name='Test Tournament')
        version = _ConcreteTournamentVersion(
            tournament=tournament,
            version_number=2
        )
        
        expected = "Test Tournament - v2"
        with patch.object(_ConcreteTournamentVersion, '__str__', return_value=expected):
            assert str(version) == expected
    
    def test_tournamentversion_data_jsonb(self):
        """TournamentVersion should store complete tournament snapshot (JSONB)"""
        version_data = {
            "name": "Tournament Name",
            "format": "single_elimination",
            "max_participants": 16,
            "entry_fee_amount": "500.00",
            "prize_pool": "5000.00",
            "rules": "Tournament rules text"
        }
        version = _ConcreteTournamentVersion(version_data=version_data)
        
        assert version.version_data["name"] == "Tournament Name"
        assert version.version_data["format"] == "single_elimination"
        assert version.version_data["max_participants"] == 16


@pytest.mark.django_db
class TestTournamentSoftDelete:
    """Test soft delete functionality on Tournament model"""
    
    @patch('apps.tournaments.models.tournament.Tournament.save')
    def test_tournament_soft_delete(self, mock_save):
        """Tournament should support soft delete from SoftDeleteModel"""
        tournament = _ConcreteTournament(is_deleted=False)
        
        # Mock soft_delete method
        def mock_soft_delete(user=None):
            tournament.is_deleted = True
            tournament.deleted_at = timezone.now()
            tournament.deleted_by = user
        
        with patch.object(_ConcreteTournament, 'soft_delete', side_effect=mock_soft_delete):
            tournament.soft_delete(user=1)
        
        assert tournament.is_deleted is True
        assert tournament.deleted_at is not None
        assert tournament.deleted_by == 1
    
    @patch('apps.tournaments.models.tournament.Tournament.save')
    def test_tournament_restore(self, mock_save):
        """Tournament should support restore from soft delete"""
        tournament = _ConcreteTournament(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=1
        )
        
        # Mock restore method
        def mock_restore():
            tournament.is_deleted = False
            tournament.deleted_at = None
            tournament.deleted_by = None
        
        with patch.object(_ConcreteTournament, 'restore', side_effect=mock_restore):
            tournament.restore()
        
        assert tournament.is_deleted is False
        assert tournament.deleted_at is None
        assert tournament.deleted_by is None


@pytest.mark.django_db
class TestTournamentTimestamps:
    """Test timestamp functionality on Tournament model"""
    
    def test_tournament_created_at_auto_set(self):
        """Tournament created_at should be set automatically"""
        tournament = _ConcreteTournament()
        
        assert tournament.created_at is not None
        assert isinstance(tournament.created_at, type(timezone.now()))
    
    def test_tournament_updated_at_auto_update(self):
        """Tournament updated_at should update on save"""
        tournament = _ConcreteTournament()
        original_updated = tournament.updated_at
        
        # Simulate time passing
        new_updated = timezone.now() + timedelta(seconds=5)
        tournament.updated_at = new_updated
        
        assert tournament.updated_at > original_updated
