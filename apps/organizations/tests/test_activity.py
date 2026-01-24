"""
Tests for TeamActivityLog model.

Coverage:
- Activity log creation
- Class methods: log_action, get_team_feed, get_user_feed
- Timestamp and metadata handling

Performance: This file should run in <2 seconds.
"""
import pytest
from django.utils import timezone

from apps.organizations.models import TeamActivityLog
from apps.organizations.choices import ActivityActionType
from apps.organizations.tests.factories import (
    TeamFactory,
    TeamActivityLogFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestTeamActivityLog:
    """Test suite for TeamActivityLog model."""
    
    def test_create_activity_log(self):
        """Test creating an activity log entry."""
        team = TeamFactory.create()
        actor = UserFactory.create(username="admin")
        
        log = TeamActivityLog.objects.create(
            team=team,
            action_type=ActivityActionType.UPDATE,
            actor_id=actor.id,
            actor_username=actor.username,
            description="Updated team name",
            metadata={"old_name": "Old Team", "new_name": "New Team"},
        )
        
        assert log.pk is not None
        assert log.team == team
        assert log.action_type == ActivityActionType.UPDATE
        assert log.actor_id == actor.id
    
    def test_str_representation(self):
        """Test string representation of TeamActivityLog."""
        team = TeamFactory.create(name="Sentinels")
        log = TeamActivityLogFactory.create(
            team=team,
            action_type=ActivityActionType.ROSTER_ADD,
            actor_username="tenz",
        )
        
        expected = "ROSTER_ADD on Sentinels by tenz"
        assert str(log) == expected
    
    def test_action_type_choices_validation(self):
        """Test that only valid action types are accepted."""
        log = TeamActivityLogFactory.create(action_type=ActivityActionType.CREATE)
        
        assert log.action_type == ActivityActionType.CREATE
        assert log.action_type in [choice[0] for choice in ActivityActionType.choices]
    
    def test_timestamp_auto_set(self):
        """Test that timestamp is automatically set."""
        log = TeamActivityLogFactory.create()
        
        assert log.timestamp is not None
    
    def test_metadata_json_field(self):
        """Test that metadata field accepts JSON data."""
        log = TeamActivityLogFactory.create(
            metadata={
                "field_changed": "name",
                "old_value": "Old Name",
                "new_value": "New Name",
                "ip_address": "192.168.1.1",
            }
        )
        
        assert log.metadata["field_changed"] == "name"
        assert log.metadata["ip_address"] == "192.168.1.1"
    
    def test_log_action_class_method(self):
        """Test log_action() class method creates log entry."""
        team = TeamFactory.create()
        actor = UserFactory.create(username="manager")
        
        log = TeamActivityLog.log_action(
            team=team,
            action_type=ActivityActionType.ROSTER_ADD,
            actor=actor,
            description="Added new player",
            metadata={"player_id": 123, "role": "PLAYER"},
        )
        
        assert log.pk is not None
        assert log.team == team
        assert log.action_type == ActivityActionType.ROSTER_ADD
        assert log.actor_id == actor.id
        assert log.actor_username == actor.username
        assert log.description == "Added new player"
        assert log.metadata["player_id"] == 123
    
    def test_log_action_without_metadata(self):
        """Test log_action() with no metadata (defaults to empty dict)."""
        team = TeamFactory.create()
        actor = UserFactory.create()
        
        log = TeamActivityLog.log_action(
            team=team,
            action_type=ActivityActionType.DELETE,
            actor=actor,
            description="Deleted team",
        )
        
        assert log.metadata == {}
    
    def test_get_team_feed_returns_recent_logs(self):
        """Test get_team_feed() returns logs for a team, ordered by timestamp."""
        team = TeamFactory.create()
        
        # Create multiple logs at different times
        log1 = TeamActivityLogFactory.create(team=team, action_type=ActivityActionType.CREATE)
        log2 = TeamActivityLogFactory.create(team=team, action_type=ActivityActionType.UPDATE)
        log3 = TeamActivityLogFactory.create(team=team, action_type=ActivityActionType.ROSTER_ADD)
        
        feed = TeamActivityLog.get_team_feed(team=team, limit=10)
        
        # Should return all 3 logs, ordered by timestamp (newest first)
        assert feed.count() == 3
        assert list(feed) == [log3, log2, log1]  # Reversed order (newest first)
    
    def test_get_team_feed_respects_limit(self):
        """Test get_team_feed() respects the limit parameter."""
        team = TeamFactory.create()
        
        # Create 5 logs
        for i in range(5):
            TeamActivityLogFactory.create(team=team)
        
        feed = TeamActivityLog.get_team_feed(team=team, limit=3)
        
        # Should return only 3 most recent logs
        assert feed.count() == 3
    
    def test_get_team_feed_default_limit(self):
        """Test get_team_feed() default limit is 20."""
        team = TeamFactory.create()
        
        # Create 25 logs
        for i in range(25):
            TeamActivityLogFactory.create(team=team)
        
        feed = TeamActivityLog.get_team_feed(team=team)
        
        # Should return only 20 (default limit)
        assert feed.count() == 20
    
    def test_get_team_feed_filters_by_team(self):
        """Test get_team_feed() only returns logs for specified team."""
        team1 = TeamFactory.create()
        team2 = TeamFactory.create()
        
        log1 = TeamActivityLogFactory.create(team=team1)
        log2 = TeamActivityLogFactory.create(team=team2)
        
        feed = TeamActivityLog.get_team_feed(team=team1)
        
        # Should only contain log1
        assert feed.count() == 1
        assert log1 in feed
        assert log2 not in feed
    
    def test_get_user_feed_returns_user_actions(self):
        """Test get_user_feed() returns logs for a specific user."""
        user = UserFactory.create(username="player1")
        
        # Create logs with this user as actor
        log1 = TeamActivityLogFactory.create(
            actor_id=user.id,
            actor_username=user.username,
        )
        log2 = TeamActivityLogFactory.create(
            actor_id=user.id,
            actor_username=user.username,
        )
        
        # Create log with different actor
        other_log = TeamActivityLogFactory.create()
        
        feed = TeamActivityLog.get_user_feed(user=user, limit=10)
        
        # Should only contain logs where user is actor
        assert feed.count() == 2
        assert log1 in feed
        assert log2 in feed
        assert other_log not in feed
    
    def test_get_user_feed_respects_limit(self):
        """Test get_user_feed() respects the limit parameter."""
        user = UserFactory.create()
        
        # Create 5 logs
        for i in range(5):
            TeamActivityLogFactory.create(
                actor_id=user.id,
                actor_username=user.username,
            )
        
        feed = TeamActivityLog.get_user_feed(user=user, limit=3)
        
        # Should return only 3 most recent logs
        assert feed.count() == 3
    
    def test_get_user_feed_default_limit(self):
        """Test get_user_feed() default limit is 20."""
        user = UserFactory.create()
        
        # Create 25 logs
        for i in range(25):
            TeamActivityLogFactory.create(
                actor_id=user.id,
                actor_username=user.username,
            )
        
        feed = TeamActivityLog.get_user_feed(user=user)
        
        # Should return only 20 (default limit)
        assert feed.count() == 20
    
    def test_actor_cached_in_log(self):
        """Test that actor_id and actor_username are cached (not FK)."""
        team = TeamFactory.create()
        actor = UserFactory.create(username="cached_user")
        
        log = TeamActivityLog.log_action(
            team=team,
            action_type=ActivityActionType.UPDATE,
            actor=actor,
            description="Test action",
        )
        
        # Actor info should be cached in log
        assert log.actor_id == actor.id
        assert log.actor_username == actor.username
        
        # Change username (log should retain old username - cached)
        actor.username = "new_username"
        actor.save()
        
        log.refresh_from_db()
        # Cached username should not change
        assert log.actor_username == "cached_user"
    
    def test_multiple_action_types(self):
        """Test creating logs with different action types."""
        team = TeamFactory.create()
        
        log_create = TeamActivityLogFactory.create(
            team=team,
            action_type=ActivityActionType.CREATE,
        )
        log_update = TeamActivityLogFactory.create(
            team=team,
            action_type=ActivityActionType.UPDATE,
        )
        log_delete = TeamActivityLogFactory.create(
            team=team,
            action_type=ActivityActionType.DELETE,
        )
        
        # All action types should be valid
        assert log_create.action_type == ActivityActionType.CREATE
        assert log_update.action_type == ActivityActionType.UPDATE
        assert log_delete.action_type == ActivityActionType.DELETE
    
    def test_description_can_be_long(self):
        """Test that description field accepts long text."""
        long_description = "This is a very long description " * 50  # ~1500 chars
        
        log = TeamActivityLogFactory.create(description=long_description)
        
        assert log.description == long_description
