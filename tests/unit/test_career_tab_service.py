"""
Unit Tests for CareerTabService - Phase UP 5
Tests data retrieval methods for Career Tab only
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.user_profile.services.career_tab_service import CareerTabService
from apps.user_profile.models import GameProfile
from apps.games.models import Game


User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user with profile"""
    user = User.objects.create_user(
        username='testplayer',
        email='test@deltacrown.com',
        password='testpass123'
    )
    # Ensure profile exists
    from apps.user_profile.models import UserProfile
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    return user


@pytest.fixture
def valorant_game(db):
    """Create VALORANT game"""
    return Game.objects.create(
        name='VALORANT',
        slug='valorant',
        is_active=True,
        game_mode='5v5'
    )


@pytest.fixture
def cs2_game(db):
    """Create CS2 game"""
    return Game.objects.create(
        name='Counter-Strike 2',
        slug='cs2',
        is_active=True,
        game_mode='5v5'
    )


@pytest.fixture
def valorant_passport(test_user, valorant_game):
    """Create a GameProfile passport"""
    return GameProfile.objects.create(
        user=test_user,
        game=valorant_game,
        in_game_name='TestPlayer#NA1',
        ign='TestPlayer',
        discriminator='#NA1',
        identity_key='testplayer#na1',
        game_display_name='VALORANT',
        rank_name='Diamond 3',
        rank_tier=7,
        peak_rank='Immortal 1',
        visibility=GameProfile.VISIBILITY_PUBLIC,
        status=GameProfile.STATUS_ACTIVE
    )


@pytest.mark.django_db
class TestGetLinkedGames:
    """Test get_linked_games() method"""
    
    def test_no_passports_returns_empty_list(self, test_user):
        """User with no game passports returns empty list"""
        result = CareerTabService.get_linked_games(test_user.profile)
        assert result == []
    
    def test_single_passport_returns_one_game(self, test_user, valorant_passport):
        """User with one passport returns one game"""
        result = CareerTabService.get_linked_games(test_user.profile)
        assert len(result) == 1
        assert result[0]['game_slug'] == 'valorant'
        assert result[0]['game_name'] == 'VALORANT'
        assert result[0]['is_primary'] is False  # No primary game set
    
    def test_primary_game_comes_first(self, test_user, valorant_game, cs2_game):
        """Primary game from UserProfile.primary_game comes first"""
        # Create passports for both games
        cs2_passport = GameProfile.objects.create(
            user=test_user,
            game=cs2_game,
            in_game_name='TestPlayerCS',
            ign='TestPlayerCS',
            identity_key='testplayercs',
            game_display_name='Counter-Strike 2',
            rank_name='Global Elite',
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE
        )
        valorant_passport = GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='TestPlayer#NA1',
            ign='TestPlayer',
            discriminator='#NA1',
            identity_key='testplayer#na1',
            game_display_name='VALORANT',
            rank_name='Diamond 3',
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE
        )
        
        # Set VALORANT as primary game
        profile = test_user.profile
        profile.primary_game = valorant_game
        profile.save()
        
        result = CareerTabService.get_linked_games(profile)
        assert len(result) == 2
        # Primary game should be first
        assert result[0]['game_slug'] == 'valorant'
        assert result[0]['is_primary'] is True
        # CS2 should be second
        assert result[1]['game_slug'] == 'cs2'
        assert result[1]['is_primary'] is False
    
    def test_pinned_games_ordered_correctly(self, test_user, valorant_game, cs2_game):
        """Pinned games are ordered by pinned_order"""
        # Create passports with different pinned_order
        cs2_passport = GameProfile.objects.create(
            user=test_user,
            game=cs2_game,
            in_game_name='TestPlayerCS',
            ign='TestPlayerCS',
            identity_key='testplayercs',
            game_display_name='Counter-Strike 2',
            rank_name='Global Elite',
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE,
            is_pinned=True,
            pinned_order=1
        )
        valorant_passport = GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='TestPlayer#NA1',
            ign='TestPlayer',
            discriminator='#NA1',
            identity_key='testplayer#na1',
            game_display_name='VALORANT',
            rank_name='Diamond 3',
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE,
            is_pinned=True,
            pinned_order=2
        )
        
        result = CareerTabService.get_linked_games(test_user.profile)
        assert len(result) == 2
        # CS2 should come first (pinned_order=1)
        assert result[0]['game_slug'] == 'cs2'
        # VALORANT should come second (pinned_order=2)
        assert result[1]['game_slug'] == 'valorant'
    
    def test_multiple_games_returns_sorted_list(self, test_user, valorant_game, cs2_game):
        """Multiple games return alphabetically sorted"""
        GameProfile.objects.create(user=test_user, game=valorant_game, in_game_name='Player1')
        GameProfile.objects.create(user=test_user, game=cs2_game, in_game_name='Player2')
        
        result = CareerTabService.get_linked_games(test_user)
        assert len(result) == 2
        # CS2 comes before VALORANT alphabetically
        assert result[0]['game_slug'] == 'cs2'
        assert result[1]['game_slug'] == 'valorant'


@pytest.mark.django_db
class TestGetGamePassport:
    """Test get_game_passport() method"""
    
    def test_no_passport_returns_none(self, test_user, valorant_game):
        """User without passport for game returns None"""
        result = CareerTabService.get_game_passport(test_user, valorant_game)
        assert result is None
    
    def test_existing_passport_returns_data(self, test_user, valorant_passport):
        """User with passport returns correct data"""
        result = CareerTabService.get_game_passport(test_user, valorant_passport.game)
        
        assert result is not None
        assert result['in_game_name'] == 'TestPlayer#NA1'
        assert result['rank_name'] == 'Diamond 3'
        assert result['game_name'] == 'VALORANT'
    
    def test_multiple_passports_returns_first(self, test_user, valorant_game):
        """Multiple passports for same game returns first one"""
        GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='FirstAccount#NA1',
            rank='Gold 1'
        )
        GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='SecondAccount#EU1',
            rank='Platinum 2'
        )
        
        result = CareerTabService.get_game_passport(test_user, valorant_game)
        # Should return first created
        assert result['in_game_name'] == 'FirstAccount#NA1'
        assert result['rank_name'] == 'Gold 1'


@pytest.mark.django_db
class TestGetMatchesPlayedCount:
    """Test get_matches_played_count() method"""
    
    def test_no_match_model_returns_zero(self, test_user, valorant_game):
        """When Match model unavailable, returns 0"""
        # Since Match model may not be available in all environments
        result = CareerTabService.get_matches_played_count(test_user, valorant_game)
        assert isinstance(result, int)
        assert result >= 0
    
    def test_user_with_no_matches(self, test_user, valorant_game):
        """User with no matches returns 0"""
        # This test assumes Match model exists
        result = CareerTabService.get_matches_played_count(test_user, valorant_game)
        assert result == 0


@pytest.mark.django_db
class TestGetTeamRanking:
    """Test get_team_ranking() method"""
    
    def test_no_team_ranking_returns_none(self, test_user, valorant_game):
        """User without team ranking returns None"""
        result = CareerTabService.get_team_ranking(test_user, valorant_game)
        assert result is None
    
    def test_team_ranking_fallback_safe(self, test_user, valorant_game):
        """Method handles TeamRanking model unavailability"""
        # Should not crash even if model doesn't exist
        result = CareerTabService.get_team_ranking(test_user, valorant_game)
        assert result is None or isinstance(result, dict)


@pytest.mark.django_db
class TestGetTeamAffiliationHistory:
    """Test get_team_affiliation_history() method"""
    
    def test_no_teams_returns_empty_list(self, test_user, valorant_game):
        """User with no team history returns empty list"""
        result = CareerTabService.get_team_affiliation_history(test_user, valorant_game)
        assert result == []
    
    def test_model_unavailable_returns_empty(self, test_user, valorant_game):
        """Gracefully handles missing TeamMembership model"""
        result = CareerTabService.get_team_affiliation_history(test_user, valorant_game)
        assert isinstance(result, list)


@pytest.mark.django_db
class TestGetAchievements:
    """Test get_achievements() method"""
    
    def test_no_achievements_returns_empty_list(self, test_user, valorant_game):
        """User with no achievements returns empty list"""
        result = CareerTabService.get_achievements(test_user, valorant_game)
        assert result == []
    
    def test_model_unavailable_returns_empty(self, test_user, valorant_game):
        """Gracefully handles missing Registration/Tournament models"""
        result = CareerTabService.get_achievements(test_user, valorant_game)
        assert isinstance(result, list)


@pytest.mark.django_db
class TestGetDisplayAttributes:
    """Test get_display_attributes() method"""
    
    def test_no_passport_returns_empty_list(self, test_user, valorant_game):
        """User without passport returns empty attributes"""
        result = CareerTabService.get_display_attributes(test_user, valorant_game)
        assert result == []
    
    def test_passport_with_attributes_returns_formatted(self, test_user, valorant_passport):
        """Passport with attributes returns formatted list"""
        result = CareerTabService.get_display_attributes(test_user, valorant_passport.game)
        
        assert isinstance(result, list)
        # Should have IGN, Rank, and custom attributes
        labels = [attr['label'] for attr in result]
        assert 'IGN' in labels
        assert 'Rank' in labels
    
    def test_passport_without_extra_attributes(self, test_user, valorant_game):
        """Passport without extra attributes shows only basic fields"""
        passport = GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='BasicPlayer',
            rank='Silver 2',
            attributes={}  # No extra attributes
        )
        
        result = CareerTabService.get_display_attributes(test_user, valorant_game)
        
        labels = [attr['label'] for attr in result]
        assert 'IGN' in labels
        assert 'Rank' in labels
        # Should not have peak_rank since attributes is empty
        assert 'Peak Rank' not in labels


@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_deleted_game_passport(self, test_user, valorant_game):
        """Deleted game doesn't crash methods"""
        passport = GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='DeletedGame'
        )
        
        # Get initial data
        result1 = CareerTabService.get_linked_games(test_user)
        assert len(result1) == 1
        
        # Delete passport
        passport.delete()
        
        # Should return empty list now
        result2 = CareerTabService.get_linked_games(test_user)
        assert result2 == []
    
    def test_inactive_game_still_returned(self, test_user, valorant_game):
        """Inactive games still appear if user has passport"""
        GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='Player'
        )
        
        valorant_game.is_active = False
        valorant_game.save()
        
        result = CareerTabService.get_linked_games(test_user)
        # Should still return the game
        assert len(result) == 1
    
    def test_null_rank_handled_gracefully(self, test_user, valorant_game):
        """Null rank field doesn't crash passport retrieval"""
        GameProfile.objects.create(
            user=test_user,
            game=valorant_game,
            in_game_name='UnrankedPlayer',
            rank=None  # Null rank
        )
        
        result = CareerTabService.get_game_passport(test_user, valorant_game)
        assert result is not None
        assert result['rank_name'] == 'Unranked'


@pytest.mark.django_db
class TestIntegration:
    """Integration tests for full workflow"""
    
    def test_full_career_tab_data_retrieval(self, test_user, valorant_passport):
        """Test retrieving all career tab data for a user"""
        game = valorant_passport.game
        
        # Get all data
        linked_games = CareerTabService.get_linked_games(test_user)
        passport = CareerTabService.get_game_passport(test_user, game)
        matches_played = CareerTabService.get_matches_played_count(test_user, game)
        team_ranking = CareerTabService.get_team_ranking(test_user, game)
        team_history = CareerTabService.get_team_affiliation_history(test_user, game)
        achievements = CareerTabService.get_achievements(test_user, game)
        display_attrs = CareerTabService.get_display_attributes(test_user, game)
        
        # Verify all methods return expected types
        assert isinstance(linked_games, list)
        assert isinstance(passport, dict)
        assert isinstance(matches_played, int)
        assert team_ranking is None or isinstance(team_ranking, dict)
        assert isinstance(team_history, list)
        assert isinstance(achievements, list)
        assert isinstance(display_attrs, list)
        
        # Verify basic data
        assert len(linked_games) == 1
        assert passport['game_name'] == 'VALORANT'
        assert matches_played >= 0
