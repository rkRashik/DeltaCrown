"""
P0 Safety Tests - Wallet Gating + URL Validation
Tests for critical security features in profile expansion.

Test Coverage:
- Wallet data never exposed to non-owners
- URL validation rejects non-whitelisted domains
- HTTPS enforcement
- Video ID character whitelist
"""
import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.user_profile.views.public_profile_views import public_profile_view
from apps.user_profile.services.url_validator import (
    validate_highlight_url,
    validate_stream_url,
    validate_affiliate_url,
)

User = get_user_model()


class WalletGatingTest(TestCase):
    """Test wallet data is never exposed to non-owners."""
    
    def setUp(self):
        """Create test users and profiles."""
        self.owner = User.objects.create_user(username='owner', password='pass123')
        self.visitor = User.objects.create_user(username='visitor', password='pass123')
        self.owner_profile = UserProfile.objects.create(user=self.owner)
        self.factory = RequestFactory()
    
    def test_wallet_visible_for_owner(self):
        """Owner sees wallet data in context."""
        request = self.factory.get(f'/@{self.owner.username}/')
        request.user = self.owner
        
        response = profile_public_v2(request, username=self.owner.username)
        context = response.context_data
        
        assert context['wallet_visible'] is True, "Wallet should be visible to owner"
        assert context['wallet'] is not None, "Wallet object should be in context"
    
    def test_wallet_hidden_for_non_owner(self):
        """Non-owner does NOT see wallet data in context."""
        request = self.factory.get(f'/@{self.owner.username}/')
        request.user = self.visitor
        
        response = profile_public_v2(request, username=self.owner.username)
        context = response.context_data
        
        assert context['wallet_visible'] is False, "Wallet should be hidden from non-owner"
        assert context['wallet'] is None, "Wallet object should NOT be in context"
        assert context['wallet_transactions'] == [], "Transactions should be empty list"
    
    def test_wallet_hidden_for_anonymous(self):
        """Anonymous user does NOT see wallet data."""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get(f'/@{self.owner.username}/')
        request.user = AnonymousUser()
        
        response = profile_public_v2(request, username=self.owner.username)
        context = response.context_data
        
        assert context['wallet_visible'] is False, "Wallet should be hidden from anonymous"
        assert context['wallet'] is None, "Wallet object should NOT be in context"


class HighlightURLValidationTest(TestCase):
    """Test highlight URL validation (YouTube, Twitch, Medal.tv)."""
    
    def test_youtube_watch_url_valid(self):
        """YouTube watch URL is accepted."""
        result = validate_highlight_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert result['valid'] is True
        assert result['platform'] == 'youtube'
        assert result['video_id'] == 'dQw4w9WgXcQ'
        assert 'embed' in result['embed_url']
    
    def test_youtube_short_url_valid(self):
        """YouTube short URL (youtu.be) is accepted."""
        result = validate_highlight_url("https://youtu.be/dQw4w9WgXcQ")
        assert result['valid'] is True
        assert result['platform'] == 'youtube'
        assert result['video_id'] == 'dQw4w9WgXcQ'
    
    def test_twitch_clip_url_valid(self):
        """Twitch clip URL is accepted."""
        result = validate_highlight_url("https://clips.twitch.tv/AwesomeClipSlug")
        assert result['valid'] is True
        assert result['platform'] == 'twitch'
        assert result['video_id'] == 'AwesomeClipSlug'
        assert 'parent=' in result['embed_url'], "Twitch embed must have parent param"
    
    def test_medal_clip_url_valid(self):
        """Medal.tv clip URL is accepted."""
        result = validate_highlight_url("https://medal.tv/clip/abc123")
        assert result['valid'] is True
        assert result['platform'] == 'medal'
        assert result['video_id'] == 'abc123'
    
    def test_http_url_rejected(self):
        """HTTP URL is rejected (HTTPS only)."""
        result = validate_highlight_url("http://youtube.com/watch?v=abc123")
        assert result['valid'] is False
        assert 'HTTPS' in result['error']
    
    def test_non_whitelisted_domain_rejected(self):
        """Non-whitelisted domain is rejected."""
        result = validate_highlight_url("https://vimeo.com/123456789")
        assert result['valid'] is False
        assert 'not whitelisted' in result['error']
    
    def test_xss_video_id_rejected(self):
        """Video ID with special characters is rejected (XSS prevention)."""
        result = validate_highlight_url("https://youtube.com/watch?v=<script>alert('xss')</script>")
        assert result['valid'] is False
        assert 'invalid characters' in result['error']
    
    def test_path_traversal_video_id_rejected(self):
        """Video ID with path traversal is rejected."""
        result = validate_highlight_url("https://youtube.com/watch?v=../../etc/passwd")
        assert result['valid'] is False
        assert 'invalid characters' in result['error']


class StreamURLValidationTest(TestCase):
    """Test stream URL validation (Twitch, YouTube Live, Facebook Gaming)."""
    
    def test_twitch_channel_url_valid(self):
        """Twitch channel URL is accepted."""
        result = validate_stream_url("https://twitch.tv/shroud")
        assert result['valid'] is True
        assert result['platform'] == 'twitch'
        assert result['channel_id'] == 'shroud'
        assert 'parent=' in result['embed_url'], "Twitch embed must have parent param"
    
    def test_youtube_channel_url_valid(self):
        """YouTube channel URL is accepted."""
        result = validate_stream_url("https://youtube.com/@pewdiepie")
        assert result['valid'] is True
        assert result['platform'] == 'youtube'
        assert result['channel_id'] == 'pewdiepie'
    
    def test_http_stream_url_rejected(self):
        """HTTP stream URL is rejected."""
        result = validate_stream_url("http://twitch.tv/shroud")
        assert result['valid'] is False
        assert 'HTTPS' in result['error']
    
    def test_non_whitelisted_stream_domain_rejected(self):
        """Non-whitelisted stream domain is rejected."""
        result = validate_stream_url("https://mixer.com/ninja")
        assert result['valid'] is False
        assert 'not whitelisted' in result['error']


class AffiliateURLValidationTest(TestCase):
    """Test affiliate URL validation (Amazon, Logitech, Razer)."""
    
    def test_amazon_url_valid(self):
        """Amazon product URL is accepted."""
        result = validate_affiliate_url("https://amazon.com/dp/B08EXAMPLE")
        assert result['valid'] is True
        assert result['platform'] == 'amazon'
    
    def test_logitech_url_valid(self):
        """Logitech product URL is accepted."""
        result = validate_affiliate_url("https://logitech.com/en-us/products/mice/g-pro-wireless.html")
        assert result['valid'] is True
        assert result['platform'] == 'logitech'
    
    def test_http_affiliate_url_rejected(self):
        """HTTP affiliate URL is rejected."""
        result = validate_affiliate_url("http://amazon.com/dp/B08EXAMPLE")
        assert result['valid'] is False
        assert 'HTTPS' in result['error']
    
    def test_non_whitelisted_affiliate_domain_rejected(self):
        """Non-whitelisted affiliate domain is rejected."""
        result = validate_affiliate_url("https://malicious-site.com/product")
        assert result['valid'] is False
        assert 'not whitelisted' in result['error']


class EmbedSandboxTest(TestCase):
    """Test iframe sandbox attributes are present (template-level check)."""
    
    # NOTE: This would be tested in template rendering tests
    # For now, we ensure URL validator returns safe embed URLs
    
    def test_embed_url_uses_https(self):
        """Embed URLs always use HTTPS."""
        result = validate_highlight_url("https://youtube.com/watch?v=abc123")
        assert result['embed_url'].startswith('https://'), "Embed URL must be HTTPS"
    
    def test_twitch_embed_includes_parent_param(self):
        """Twitch embed URLs include parent parameter."""
        result = validate_highlight_url("https://clips.twitch.tv/AwesomeClip")
        assert 'parent=' in result['embed_url'], "Twitch embed must include parent param"
        assert 'deltacrown.com' in result['embed_url'], "Parent param must be our domain"
