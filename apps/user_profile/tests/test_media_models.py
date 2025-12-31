"""
Tests for P0 Media Models - StreamConfig, HighlightClip, PinnedHighlight
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.user_profile.models import StreamConfig, HighlightClip, PinnedHighlight
from apps.games.models import Game

User = get_user_model()


# ===========================
# FIXTURES
# ===========================

@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def user2(db):
    """Create a second test user."""
    return User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123'
    )


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        description='Test game description'
    )


# ===========================
# STREAMCONFIG TESTS
# ===========================

@pytest.mark.django_db
class TestStreamConfig:
    """Test StreamConfig model validation and behavior."""
    
    def test_twitch_stream_valid(self, user):
        """Test Twitch channel URL is accepted."""
        stream = StreamConfig(
            user=user,
            stream_url='https://www.twitch.tv/shroud',
            is_active=True
        )
        stream.save()
        
        assert stream.platform == 'twitch'
        assert stream.channel_id == 'shroud'
        assert 'player.twitch.tv' in stream.embed_url
        assert 'parent=deltacrown.com' in stream.embed_url
    
    def test_youtube_stream_valid(self, user):
        """Test YouTube channel URL is accepted."""
        stream = StreamConfig(
            user=user,
            stream_url='https://www.youtube.com/channel/UC_test_channel_id',
            is_active=True
        )
        stream.save()
        
        assert stream.platform == 'youtube'
        assert stream.channel_id == 'UC_test_channel_id'
        assert 'youtube.com/embed/live_stream' in stream.embed_url
    
    def test_http_stream_rejected(self, user):
        """Test HTTP URLs are rejected (HTTPS only)."""
        stream = StreamConfig(
            user=user,
            stream_url='http://www.twitch.tv/shroud',  # HTTP not HTTPS
            is_active=True
        )
        
        with pytest.raises(ValidationError) as exc_info:
            stream.save()
        
        assert 'stream_url' in str(exc_info.value)
    
    def test_non_whitelisted_stream_rejected(self, user):
        """Test non-whitelisted domains are rejected."""
        stream = StreamConfig(
            user=user,
            stream_url='https://evil.com/fake_stream',
            is_active=True
        )
        
        with pytest.raises(ValidationError) as exc_info:
            stream.save()
        
        assert 'stream_url' in str(exc_info.value)
    
    def test_one_stream_per_user(self, user):
        """Test OneToOne constraint: only one stream config per user."""
        # Create first stream
        StreamConfig.objects.create(
            user=user,
            stream_url='https://www.twitch.tv/shroud',
            is_active=True
        )
        
        # Try to create second stream for same user
        with pytest.raises(Exception):  # Django IntegrityError or ValidationError
            StreamConfig.objects.create(
                user=user,
                stream_url='https://www.youtube.com/channel/UC_other',
                is_active=True
            )
    
    def test_embed_url_auto_generated(self, user):
        """Test embed_url is auto-generated server-side."""
        stream = StreamConfig(
            user=user,
            stream_url='https://www.twitch.tv/ninja',
            is_active=True
        )
        stream.save()
        
        # embed_url should be populated automatically
        assert stream.embed_url is not None
        assert stream.embed_url != ''
        assert 'ninja' in stream.embed_url


# ===========================
# HIGHLIGHTCLIP TESTS
# ===========================

@pytest.mark.django_db
class TestHighlightClip:
    """Test HighlightClip model validation and behavior."""
    
    def test_youtube_clip_valid(self, user):
        """Test YouTube video URL is accepted."""
        clip = HighlightClip(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Test Clip'
        )
        clip.save()
        
        assert clip.platform == 'youtube'
        assert clip.video_id == 'dQw4w9WgXcQ'
        assert 'youtube.com/embed/dQw4w9WgXcQ' in clip.embed_url
        assert 'img.youtube.com' in clip.thumbnail_url
    
    def test_twitch_clip_valid(self, user):
        """Test Twitch clip URL is accepted."""
        clip = HighlightClip(
            user=user,
            clip_url='https://clips.twitch.tv/AwesomeClipSlug',
            title='Twitch Clip'
        )
        clip.save()
        
        assert clip.platform == 'twitch'
        assert clip.video_id == 'AwesomeClipSlug'
        assert 'clips.twitch.tv/embed' in clip.embed_url
    
    def test_medal_clip_valid(self, user):
        """Test Medal.tv clip URL is accepted."""
        clip = HighlightClip(
            user=user,
            clip_url='https://medal.tv/games/valorant/clips/abc123/d1NmxW1337',
            title='Medal Clip'
        )
        clip.save()
        
        assert clip.platform == 'medal'
        assert 'medal.tv' in clip.embed_url
    
    def test_http_clip_rejected(self, user):
        """Test HTTP URLs are rejected (HTTPS only)."""
        clip = HighlightClip(
            user=user,
            clip_url='http://www.youtube.com/watch?v=dQw4w9WgXcQ',  # HTTP
            title='Test Clip'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            clip.save()
        
        assert 'clip_url' in str(exc_info.value)
    
    def test_xss_clip_rejected(self, user):
        """Test XSS payloads in URLs are rejected."""
        xss_urls = [
            'https://youtube.com/<script>alert(1)</script>',
            'https://youtube.com/javascript:alert(1)',
            'https://youtube.com/data:text/html,<script>alert(1)</script>',
        ]
        
        for xss_url in xss_urls:
            clip = HighlightClip(
                user=user,
                clip_url=xss_url,
                title='XSS Attempt'
            )
            
            with pytest.raises(ValidationError):
                clip.save()
    
    def test_path_traversal_clip_rejected(self, user):
        """Test path traversal attempts are rejected."""
        traversal_urls = [
            'https://youtube.com/../../../etc/passwd',
            'https://youtube.com/..%2F..%2F..%2Fetc%2Fpasswd',
        ]
        
        for traversal_url in traversal_urls:
            clip = HighlightClip(
                user=user,
                clip_url=traversal_url,
                title='Path Traversal'
            )
            
            with pytest.raises(ValidationError):
                clip.save()
    
    def test_multiple_clips_allowed(self, user):
        """Test ForeignKey allows multiple clips per user."""
        clip1 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Clip 1'
        )
        
        clip2 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=abc123456',
            title='Clip 2'
        )
        
        assert user.highlightclip_set.count() == 2
        assert clip1.id != clip2.id
    
    def test_display_order_sorting(self, user):
        """Test display_order field and sorting."""
        clip1 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video1',
            title='Clip 1',
            display_order=10
        )
        
        clip2 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video2',
            title='Clip 2',
            display_order=20
        )
        
        # Clips should be ordered by display_order descending
        clips = list(user.highlightclip_set.all())
        assert clips[0].display_order == 20
        assert clips[1].display_order == 10
    
    def test_game_tagging(self, user, game):
        """Test game FK relationship."""
        clip = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Game Clip',
            game=game
        )
        
        assert clip.game == game
        assert clip.game.name == 'Test Game'


# ===========================
# PINNEDHIGHLIGHT TESTS
# ===========================

@pytest.mark.django_db
class TestPinnedHighlight:
    """Test PinnedHighlight model validation and behavior."""
    
    def test_pin_own_clip(self, user):
        """Test user can pin their own clip."""
        clip = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='My Clip'
        )
        
        pinned = PinnedHighlight(
            user=user,
            clip=clip
        )
        pinned.save()
        
        assert pinned.user == user
        assert pinned.clip == clip
    
    def test_cannot_pin_others_clip(self, user, user2):
        """Test user cannot pin another user's clip."""
        clip = HighlightClip.objects.create(
            user=user2,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Other User Clip'
        )
        
        pinned = PinnedHighlight(
            user=user,
            clip=clip
        )
        
        with pytest.raises(ValidationError) as exc_info:
            pinned.save()
        
        assert 'You can only pin your own clips' in str(exc_info.value)
    
    def test_only_one_pin_per_user(self, user):
        """Test OneToOne constraint: only one pinned highlight per user."""
        clip1 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video1',
            title='Clip 1'
        )
        
        clip2 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video2',
            title='Clip 2'
        )
        
        # Pin first clip
        PinnedHighlight.objects.create(
            user=user,
            clip=clip1
        )
        
        # Try to pin second clip for same user
        with pytest.raises(Exception):  # Django IntegrityError
            PinnedHighlight.objects.create(
                user=user,
                clip=clip2
            )
    
    def test_change_pinned_clip(self, user):
        """Test user can change their pinned clip."""
        clip1 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video1',
            title='Clip 1'
        )
        
        clip2 = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=video2',
            title='Clip 2'
        )
        
        # Pin first clip
        pinned = PinnedHighlight.objects.create(
            user=user,
            clip=clip1
        )
        
        assert pinned.clip == clip1
        
        # Change to second clip
        pinned.clip = clip2
        pinned.save()
        
        assert pinned.clip == clip2
    
    def test_delete_cascade(self, user):
        """Test pinned highlight deletes when clip is deleted."""
        clip = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Clip'
        )
        
        pinned = PinnedHighlight.objects.create(
            user=user,
            clip=clip
        )
        
        assert PinnedHighlight.objects.filter(user=user).exists()
        
        # Delete clip
        clip.delete()
        
        # Pinned highlight should be deleted (CASCADE)
        assert not PinnedHighlight.objects.filter(user=user).exists()
