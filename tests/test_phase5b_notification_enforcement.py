"""
Phase 5B: Notification Delivery Enforcement Tests

Tests for the central enforcement gate that ensures notifications are only
delivered when allowed by user settings.

Test Coverage:
- Channel enforcement (email/push/SMS enabled/disabled)
- Category enforcement (tournaments/teams/economy/system)
- Quiet hours enforcement (timezone-aware, overnight windows)
- Default behavior (no preferences)
- Bypass for critical notifications
"""
import pytest
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.user_profile.models import UserProfile, NotificationPreferences
from apps.notifications.enforcement import (
    can_deliver_notification,
    get_blocked_reason,
    log_suppressed_notification,
)

User = get_user_model()


@pytest.mark.django_db
class TestNotificationEnforcement:
    """Test suite for notification delivery enforcement."""
    
    @pytest.fixture
    def user(self):
        """Create a test user with profile."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        profile = UserProfile.objects.get(user=user)
        profile.timezone_pref = 'Asia/Dhaka'
        profile.save()
        return user
    
    @pytest.fixture
    def prefs(self, user):
        """Create notification preferences for test user."""
        return NotificationPreferences.objects.create(
            user_profile=user.profile,
            email_enabled=True,
            push_enabled=True,
            sms_enabled=False,
            notif_tournaments=True,
            notif_teams=True,
            notif_bounties=True,
            notif_messages=True,
            notif_system=True,
            quiet_hours_enabled=False,
        )
    
    # ===== CHANNEL ENFORCEMENT TESTS =====
    
    def test_email_enabled_allows_delivery(self, user, prefs):
        """Test that email delivery is allowed when email_enabled=True."""
        assert can_deliver_notification(user, 'email', 'tournaments') is True
    
    def test_email_disabled_blocks_delivery(self, user, prefs):
        """Test that email delivery is blocked when email_enabled=False."""
        prefs.email_enabled = False
        prefs.save()
        
        assert can_deliver_notification(user, 'email', 'tournaments') is False
        assert get_blocked_reason(user, 'email', 'tournaments') == 'channel_disabled'
    
    def test_push_enabled_allows_delivery(self, user, prefs):
        """Test that push delivery is allowed when push_enabled=True."""
        assert can_deliver_notification(user, 'push', 'teams') is True
    
    def test_push_disabled_blocks_delivery(self, user, prefs):
        """Test that push delivery is blocked when push_enabled=False."""
        prefs.push_enabled = False
        prefs.save()
        
        assert can_deliver_notification(user, 'push', 'teams') is False
        assert get_blocked_reason(user, 'push', 'teams') == 'channel_disabled'
    
    def test_sms_disabled_blocks_delivery(self, user, prefs):
        """Test that SMS delivery is blocked when sms_enabled=False."""
        assert can_deliver_notification(user, 'sms', 'system') is False
        assert get_blocked_reason(user, 'sms', 'system') == 'channel_disabled'
    
    def test_sms_enabled_allows_delivery(self, user, prefs):
        """Test that SMS delivery is allowed when sms_enabled=True."""
        prefs.sms_enabled = True
        prefs.save()
        
        assert can_deliver_notification(user, 'sms', 'system') is True
    
    # ===== CATEGORY ENFORCEMENT TESTS =====
    
    def test_tournaments_category_enabled_allows_delivery(self, user, prefs):
        """Test that tournament notifications are allowed when category enabled."""
        assert can_deliver_notification(user, 'email', 'tournaments') is True
    
    def test_tournaments_category_disabled_blocks_delivery(self, user, prefs):
        """Test that tournament notifications are blocked when category disabled."""
        prefs.notif_tournaments = False
        prefs.save()
        
        assert can_deliver_notification(user, 'email', 'tournaments') is False
        assert get_blocked_reason(user, 'email', 'tournaments') == 'category_disabled'
    
    def test_teams_category_disabled_blocks_delivery(self, user, prefs):
        """Test that team notifications are blocked when category disabled."""
        prefs.notif_teams = False
        prefs.save()
        
        assert can_deliver_notification(user, 'push', 'teams') is False
        assert get_blocked_reason(user, 'push', 'teams') == 'category_disabled'
    
    def test_bounties_category_disabled_blocks_delivery(self, user, prefs):
        """Test that bounty notifications are blocked when category disabled."""
        prefs.notif_bounties = False
        prefs.save()
        
        assert can_deliver_notification(user, 'email', 'bounties') is False
        assert get_blocked_reason(user, 'email', 'bounties') == 'category_disabled'
    
    def test_economy_maps_to_bounties_category(self, user, prefs):
        """Test that 'economy' category maps to bounties."""
        prefs.notif_bounties = False
        prefs.save()
        
        assert can_deliver_notification(user, 'email', 'economy') is False
        assert get_blocked_reason(user, 'email', 'economy') == 'category_disabled'
    
    def test_messages_category_disabled_blocks_delivery(self, user, prefs):
        """Test that message notifications are blocked when category disabled."""
        prefs.notif_messages = False
        prefs.save()
        
        assert can_deliver_notification(user, 'push', 'messages') is False
    
    def test_system_category_disabled_blocks_delivery(self, user, prefs):
        """Test that system notifications are blocked when category disabled."""
        prefs.notif_system = False
        prefs.save()
        
        assert can_deliver_notification(user, 'email', 'system') is False
    
    # ===== QUIET HOURS ENFORCEMENT TESTS =====
    
    def test_quiet_hours_disabled_allows_delivery_anytime(self, user, prefs):
        """Test that delivery is allowed anytime when quiet hours disabled."""
        prefs.quiet_hours_enabled = False
        prefs.save()
        
        # Test at midnight (would be blocked if quiet hours were enabled)
        now = datetime(2026, 1, 2, 0, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is True
    
    def test_quiet_hours_enabled_blocks_delivery_during_window(self, user, prefs):
        """Test that delivery is blocked during quiet hours window."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)  # 22:00
        prefs.quiet_hours_end = time(8, 0)     # 08:00
        prefs.save()
        
        # Test at 23:30 (in quiet hours)
        now = datetime(2026, 1, 2, 23, 30, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is False
        assert get_blocked_reason(user, 'email', 'tournaments', now=now) == 'quiet_hours'
    
    def test_quiet_hours_enabled_allows_delivery_outside_window(self, user, prefs):
        """Test that delivery is allowed outside quiet hours window."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)  # 22:00
        prefs.quiet_hours_end = time(8, 0)     # 08:00
        prefs.save()
        
        # Test at 10:00 (outside quiet hours)
        now = datetime(2026, 1, 2, 10, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is True
    
    def test_quiet_hours_overnight_window_blocks_before_midnight(self, user, prefs):
        """Test that overnight quiet hours block notifications before midnight."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(23, 0)  # 23:00
        prefs.quiet_hours_end = time(6, 0)     # 06:00
        prefs.save()
        
        # Test at 23:30 (in overnight window)
        now = datetime(2026, 1, 2, 23, 30, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'teams', now=now) is False
    
    def test_quiet_hours_overnight_window_blocks_after_midnight(self, user, prefs):
        """Test that overnight quiet hours block notifications after midnight."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(23, 0)  # 23:00
        prefs.quiet_hours_end = time(6, 0)     # 06:00
        prefs.save()
        
        # Test at 03:00 (in overnight window)
        now = datetime(2026, 1, 3, 3, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'teams', now=now) is False
    
    def test_quiet_hours_overnight_window_allows_outside(self, user, prefs):
        """Test that overnight quiet hours allow notifications outside window."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(23, 0)  # 23:00
        prefs.quiet_hours_end = time(6, 0)     # 06:00
        prefs.save()
        
        # Test at 12:00 (outside overnight window)
        now = datetime(2026, 1, 2, 12, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'teams', now=now) is True
    
    def test_quiet_hours_normal_window_blocks_correctly(self, user, prefs):
        """Test that normal (non-overnight) quiet hours block correctly."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(14, 0)  # 14:00
        prefs.quiet_hours_end = time(16, 0)    # 16:00
        prefs.save()
        
        # Test at 15:00 (in window)
        now = datetime(2026, 1, 2, 15, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'bounties', now=now) is False
        
        # Test at 13:00 (before window)
        now = datetime(2026, 1, 2, 13, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'bounties', now=now) is True
        
        # Test at 17:00 (after window)
        now = datetime(2026, 1, 2, 17, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'bounties', now=now) is True
    
    # ===== TIMEZONE CORRECTNESS TESTS =====
    
    def test_quiet_hours_respects_user_timezone(self, user, prefs):
        """Test that quiet hours use user's timezone, not server timezone."""
        # User in Asia/Dhaka (UTC+6)
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)  # 22:00 Dhaka time
        prefs.quiet_hours_end = time(8, 0)     # 08:00 Dhaka time
        prefs.save()
        
        # 23:00 in Dhaka = 17:00 UTC
        # This should be BLOCKED because it's in Dhaka quiet hours
        now = datetime(2026, 1, 2, 17, 0, tzinfo=ZoneInfo('UTC'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is False
    
    def test_quiet_hours_timezone_conversion(self, user, prefs):
        """Test correct timezone conversion for quiet hours."""
        # User in America/New_York (UTC-5)
        user.profile.timezone_pref = 'America/New_York'
        user.profile.save()
        
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)  # 22:00 New York time
        prefs.quiet_hours_end = time(8, 0)     # 08:00 New York time
        prefs.save()
        
        # 23:00 in New York = 04:00 UTC (next day)
        # This should be BLOCKED because it's in New York quiet hours
        now = datetime(2026, 1, 3, 4, 0, tzinfo=ZoneInfo('UTC'))
        assert can_deliver_notification(user, 'email', 'teams', now=now) is False
        
        # 10:00 in New York = 15:00 UTC
        # This should be ALLOWED because it's outside New York quiet hours
        now = datetime(2026, 1, 2, 15, 0, tzinfo=ZoneInfo('UTC'))
        assert can_deliver_notification(user, 'email', 'teams', now=now) is True
    
    # ===== DEFAULT BEHAVIOR TESTS =====
    
    def test_no_preferences_allows_delivery(self, user):
        """Test that delivery is allowed when user has no preferences."""
        # Don't create NotificationPreferences
        assert can_deliver_notification(user, 'email', 'tournaments') is True
        assert can_deliver_notification(user, 'push', 'teams') is True
        assert can_deliver_notification(user, 'sms', 'system') is True
    
    def test_no_preferences_returns_no_blocked_reason(self, user):
        """Test that get_blocked_reason returns None when no preferences exist."""
        assert get_blocked_reason(user, 'email', 'tournaments') is None
    
    # ===== BYPASS TESTS =====
    
    def test_bypass_user_prefs_allows_delivery(self, user, prefs):
        """Test that bypass_user_prefs=True allows delivery despite preferences."""
        # Disable everything
        prefs.email_enabled = False
        prefs.notif_system = False
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(0, 0)
        prefs.quiet_hours_end = time(23, 59)
        prefs.save()
        
        # Should still allow with bypass
        assert can_deliver_notification(user, 'email', 'system', bypass_user_prefs=True) is True
    
    def test_bypass_ignores_quiet_hours(self, user, prefs):
        """Test that bypass ignores quiet hours."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)
        prefs.quiet_hours_end = time(8, 0)
        prefs.save()
        
        # During quiet hours
        now = datetime(2026, 1, 2, 23, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        
        # Blocked without bypass
        assert can_deliver_notification(user, 'email', 'system', now=now) is False
        
        # Allowed with bypass
        assert can_deliver_notification(user, 'email', 'system', now=now, bypass_user_prefs=True) is True
    
    # ===== EDGE CASES =====
    
    def test_quiet_hours_edge_case_start_time(self, user, prefs):
        """Test delivery at exact start time of quiet hours."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)
        prefs.quiet_hours_end = time(8, 0)
        prefs.save()
        
        # Exactly at start time (22:00:00) should be blocked
        now = datetime(2026, 1, 2, 22, 0, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is False
    
    def test_quiet_hours_edge_case_end_time(self, user, prefs):
        """Test delivery at exact end time of quiet hours."""
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)
        prefs.quiet_hours_end = time(8, 0)
        prefs.save()
        
        # Exactly at end time (08:00:00) should be allowed
        now = datetime(2026, 1, 2, 8, 0, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        assert can_deliver_notification(user, 'email', 'tournaments', now=now) is True
    
    def test_multiple_enforcement_rules_channel_and_category(self, user, prefs):
        """Test that multiple rules can block (channel + category)."""
        # Disable both channel and category
        prefs.email_enabled = False
        prefs.notif_tournaments = False
        prefs.save()
        
        # Should be blocked (channel checked first)
        assert can_deliver_notification(user, 'email', 'tournaments') is False
        assert get_blocked_reason(user, 'email', 'tournaments') == 'channel_disabled'
    
    def test_multiple_enforcement_rules_category_and_quiet_hours(self, user, prefs):
        """Test enforcement with both category and quiet hours blocking."""
        prefs.notif_teams = False
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)
        prefs.quiet_hours_end = time(8, 0)
        prefs.save()
        
        # During quiet hours
        now = datetime(2026, 1, 2, 23, 0, tzinfo=ZoneInfo('Asia/Dhaka'))
        
        # Should be blocked (category checked first)
        assert can_deliver_notification(user, 'email', 'teams', now=now) is False
        assert get_blocked_reason(user, 'email', 'teams', now=now) == 'category_disabled'
    
    def test_log_suppressed_notification(self, user, prefs, caplog):
        """Test that suppressed notifications are logged."""
        prefs.email_enabled = False
        prefs.save()
        
        import logging
        with caplog.at_level(logging.INFO):
            log_suppressed_notification(
                user, 'email', 'tournaments', 'channel_disabled', 
                'Tournament Registration Confirmed'
            )
        
        assert 'SUPPRESSED NOTIFICATION' in caplog.text
        assert 'testuser' in caplog.text
        assert 'email' in caplog.text
        assert 'tournaments' in caplog.text
        assert 'channel_disabled' in caplog.text
