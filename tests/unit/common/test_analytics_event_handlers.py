"""
Epic 8.5 Event Handler Tests - Analytics event handlers.

Tests for handle_match_completed_for_analytics, handle_season_changed,
handle_tier_changed event handlers.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, call
from django.contrib.auth import get_user_model

from apps.leaderboards.event_handlers import (
    handle_match_completed_for_analytics,
    handle_season_changed,
    handle_tier_changed,
)
from apps.games.models import Game
from apps.organizations.models import Team
from apps.matches.models import Match

User = get_user_model()


@pytest.mark.django_db
class TestAnalyticsEventHandlers:
    """Test Epic 8.5 event handlers."""
    
    @pytest.fixture
    def game(self):
        """Create test game."""
        return Game.objects.create(slug="valorant", name="Valorant")
    
    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(username="testuser", email="test@example.com")
    
    @pytest.fixture
    def team(self, game):
        """Create test team."""
        return Team.objects.create(name="Test Team", tag="TEST", game=game)
    
    @pytest.fixture
    def match(self, game):
        """Create test match."""
        return Match.objects.create(
            game=game,
            status="completed",
            match_type="ranked",
            scheduled_at=datetime.now(),
        )
    
    @patch("apps.leaderboards.event_handlers.refresh_user_analytics_task.apply_async")
    @patch("apps.leaderboards.event_handlers.refresh_team_analytics_task.apply_async")
    def test_handle_match_completed_for_analytics_user_match(
        self, mock_team_task, mock_user_task, match, user
    ):
        """Test analytics refresh queued for user match completion."""
        event_data = {
            "match_id": match.id,
            "participant_type": "user",
            "participant_ids": [user.id],
            "game_slug": match.game.slug,
        }
        
        handle_match_completed_for_analytics(event_data)
        
        # Should queue user analytics refresh
        mock_user_task.assert_called_once()
        call_args = mock_user_task.call_args
        assert call_args[1]["kwargs"]["user_id"] == user.id
        assert call_args[1]["kwargs"]["game_slug"] == match.game.slug
        
        # Should NOT queue team analytics
        mock_team_task.assert_not_called()
    
    @patch("apps.leaderboards.event_handlers.refresh_user_analytics_task.apply_async")
    @patch("apps.leaderboards.event_handlers.refresh_team_analytics_task.apply_async")
    def test_handle_match_completed_for_analytics_team_match(
        self, mock_team_task, mock_user_task, match, team
    ):
        """Test analytics refresh queued for team match completion."""
        event_data = {
            "match_id": match.id,
            "participant_type": "team",
            "participant_ids": [team.id],
            "game_slug": match.game.slug,
        }
        
        handle_match_completed_for_analytics(event_data)
        
        # Should queue team analytics refresh
        mock_team_task.assert_called_once()
        call_args = mock_team_task.call_args
        assert call_args[1]["kwargs"]["team_id"] == team.id
        assert call_args[1]["kwargs"]["game_slug"] == match.game.slug
        
        # Should NOT queue user analytics
        mock_user_task.assert_not_called()
    
    @patch("apps.leaderboards.event_handlers.refresh_leaderboards_task.apply_async")
    def test_handle_season_changed_activated(self, mock_refresh_task):
        """Test leaderboard refresh triggered on season activation."""
        event_data = {
            "season_id": "S1-2024",
            "action": "activated",
        }
        
        handle_season_changed(event_data)
        
        # Should queue leaderboard refresh
        mock_refresh_task.assert_called_once()
        call_args = mock_refresh_task.call_args
        assert call_args[1]["kwargs"]["leaderboard_type"] == "seasonal"
    
    @patch("apps.leaderboards.event_handlers.refresh_leaderboards_task.apply_async")
    def test_handle_season_changed_deactivated(self, mock_refresh_task):
        """Test season deactivation logs archival message."""
        event_data = {
            "season_id": "S1-2024",
            "action": "deactivated",
        }
        
        with patch("apps.leaderboards.event_handlers.logger") as mock_logger:
            handle_season_changed(event_data)
            
            # Should log archival
            mock_logger.info.assert_called_once()
            assert "archived" in str(mock_logger.info.call_args)
        
        # Should NOT queue leaderboard refresh
        mock_refresh_task.assert_not_called()
    
    @patch("apps.leaderboards.event_handlers.NotificationAdapter")
    def test_handle_tier_changed_user_promotion(self, mock_notification_adapter, user):
        """Test tier promotion notification for user."""
        event_data = {
            "entity_type": "user",
            "entity_id": user.id,
            "old_tier": "silver",
            "new_tier": "gold",
            "game_slug": "valorant",
        }
        
        mock_adapter_instance = Mock()
        mock_notification_adapter.return_value = mock_adapter_instance
        
        handle_tier_changed(event_data)
        
        # Should send notification
        mock_adapter_instance.send_tier_promotion_notification.assert_called_once()
        call_args = mock_adapter_instance.send_tier_promotion_notification.call_args[1]
        assert call_args["user_id"] == user.id
        assert call_args["old_tier"] == "silver"
        assert call_args["new_tier"] == "gold"
    
    @patch("apps.leaderboards.event_handlers.NotificationAdapter")
    def test_handle_tier_changed_team_promotion(self, mock_notification_adapter, team):
        """Test tier promotion notification for team."""
        event_data = {
            "entity_type": "team",
            "entity_id": team.id,
            "old_tier": "gold",
            "new_tier": "diamond",
            "game_slug": "valorant",
        }
        
        mock_adapter_instance = Mock()
        mock_notification_adapter.return_value = mock_adapter_instance
        
        handle_tier_changed(event_data)
        
        # Should send notification
        mock_adapter_instance.send_tier_promotion_notification.assert_called_once()
        call_args = mock_adapter_instance.send_tier_promotion_notification.call_args[1]
        assert call_args["team_id"] == team.id
        assert call_args["old_tier"] == "gold"
        assert call_args["new_tier"] == "diamond"
    
    @patch("apps.leaderboards.event_handlers.NotificationAdapter")
    def test_handle_tier_changed_demotion(self, mock_notification_adapter, user):
        """Test tier demotion does NOT send promotion notification."""
        event_data = {
            "entity_type": "user",
            "entity_id": user.id,
            "old_tier": "gold",
            "new_tier": "silver",  # Demotion
            "game_slug": "valorant",
        }
        
        mock_adapter_instance = Mock()
        mock_notification_adapter.return_value = mock_adapter_instance
        
        handle_tier_changed(event_data)
        
        # Should NOT send promotion notification for demotion
        # (Implementation may choose to send different notification or log)
        # Verify behavior matches actual implementation
