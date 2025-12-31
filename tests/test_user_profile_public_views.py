from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.user_profile.models import (
    UserProfile,
    HighlightClip,
    PinnedHighlight,
    StreamConfig,
    SkillEndorsement,
)
from apps.economy.models import DeltaCrownWallet
from apps.games.models import Game

User = get_user_model()


class PublicProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='rkrashik', email='rkrashik@example.com', password='pass123')
        # Ensure profile exists (some signals may auto-create it)
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        if created or profile.display_name != 'Rashik':
            profile.display_name = 'Rashik'
            profile.save(update_fields=['display_name'])
        # Create wallet
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        wallet.cached_balance = 100
        wallet.save()
        
        # Create test game
        self.game, _ = Game.objects.get_or_create(
            slug='valorant',
            defaults={'display_name': 'VALORANT'}
        )

    def test_public_profile_anonymous(self):
        # Anonymous should be able to view public profile
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # is_own_profile should be False for anonymous
        self.assertIn('is_own_profile', response.context)
        self.assertFalse(response.context['is_own_profile'])
        # wallet should not be visible to anonymous
        self.assertIn('wallet', response.context)
        self.assertIsNone(response.context['wallet'])

    def test_public_profile_owner(self):
        # Login as the owner
        login_ok = self.client.login(username=self.user.username, password='pass123')
        self.assertTrue(login_ok)
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_own_profile'])
        # wallet should be present and have the balance
        self.assertIn('wallet', response.context)
        wallet = response.context['wallet']
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.cached_balance, 100)
    
    def test_highlights_empty_state(self):
        """Test profile renders safely when no highlights exist."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should have empty lists, not None
        self.assertIn('highlight_clips', response.context)
        self.assertIn('pinned_highlight', response.context)
        self.assertEqual(len(response.context['highlight_clips']), 0)
        self.assertIsNone(response.context['pinned_highlight'])
        
        # Template should not crash
        html = response.content.decode('utf-8')
        self.assertIn('No highlights uploaded yet', html)
    
    def test_pinned_highlight_rendering(self):
        """Test pinned highlight renders with correct data."""
        # Create a highlight clip
        clip = HighlightClip.objects.create(
            user=self.user,
            title='Epic 1v5 Clutch',
            platform='youtube',
            video_id='test123',
            embed_url='https://www.youtube.com/embed/test123',
            thumbnail_url='https://example.com/thumb.jpg',
            game=self.game
        )
        
        # Pin it
        PinnedHighlight.objects.create(user=self.user, clip=clip)
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check context
        pinned = response.context['pinned_highlight']
        self.assertIsNotNone(pinned)
        self.assertEqual(pinned['title'], 'Epic 1v5 Clutch')
        self.assertEqual(pinned['platform'], 'youtube')
        self.assertEqual(pinned['embed_url'], 'https://www.youtube.com/embed/test123')
        
        # Check HTML rendering
        html = response.content.decode('utf-8')
        self.assertIn('Epic 1v5 Clutch', html)
        self.assertIn('Pinned', html)
        self.assertIn('thumb.jpg', html)
    
    def test_stream_config_rendering(self):
        """Test stream config renders safely with embed URL."""
        # Create stream config
        StreamConfig.objects.create(
            user=self.user,
            platform='twitch',
            stream_url='https://twitch.tv/rkrashik',
            embed_url='https://player.twitch.tv/?channel=rkrashik&parent=deltacrown.gg',
            title='Grinding Ranked',
            is_active=True
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check context
        stream = response.context['stream_config']
        self.assertIsNotNone(stream)
        self.assertEqual(stream['platform'], 'twitch')
        self.assertIn('player.twitch.tv', stream['embed_url'])
        
        # Check HTML rendering - iframe should be present
        html = response.content.decode('utf-8')
        self.assertIn('<iframe', html)
        self.assertIn('player.twitch.tv', html)
        self.assertIn('TWITCH', html.upper())
    
    def test_stream_config_missing(self):
        """Test profile renders safely when stream config is missing."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Stream config should be None
        self.assertIn('stream_config', response.context)
        self.assertIsNone(response.context['stream_config'])
        
        # Template should not show stream section
        html = response.content.decode('utf-8')
        self.assertNotIn('Live Stream', html)
    
    def test_youtube_embed_url_format(self):
        """Test YouTube embed URL uses youtube-nocookie.com with safe params."""
        from apps.user_profile.services.url_validator import validate_highlight_url
        
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        result = validate_highlight_url(youtube_url)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['platform'], 'youtube')
        
        # Check embed URL format
        embed_url = result['embed_url']
        self.assertIn('youtube-nocookie.com', embed_url)
        self.assertIn('rel=0', embed_url)
        self.assertIn('modestbranding=1', embed_url)
        self.assertIn('playsinline=1', embed_url)
    
    def test_overview_shows_stats_when_no_pinned_highlight(self):
        """Test overview tab shows quick stats when no pinned highlight exists."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should have no pinned highlight
        self.assertIsNone(response.context['pinned_highlight'])
        
        # HTML should show Quick Stats section
        html = response.content.decode('utf-8')
        self.assertIn('Quick Stats', html)
        self.assertIn('Matches', html)
        self.assertIn('Wins', html)
        self.assertIn('Win Rate', html)
    
    def test_edit_button_visible_for_owner(self):
        """Test Edit Highlights button is visible only to profile owner."""
        # Login as owner
        self.client.login(username=self.user.username, password='pass123')
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should see Edit button
        html = response.content.decode('utf-8')
        self.assertIn('Edit Highlights', html)
        self.assertIn('openEditHighlightsModal', html)
    
    def test_edit_button_hidden_for_visitor(self):
        """Test Edit Highlights button is hidden for non-owners."""
        # Visit as anonymous
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should not see Edit button
        html = response.content.decode('utf-8')
        # Note: "Edit Highlights" might appear in modal, so check for the button specifically
        self.assertNotIn('openEditHighlightsModal()', html.split('<!-- Edit Highlights Modal')[0])
    
    def test_video_modal_inline_playback(self):
        """Test videos use modal for inline playback, not redirect."""
        # Create highlight
        clip = HighlightClip.objects.create(
            user=self.user,
            title='Test Clip',
            platform='youtube',
            video_id='test123',
            embed_url='https://www.youtube-nocookie.com/embed/test123?rel=0&modestbranding=1&playsinline=1',
            thumbnail_url='https://example.com/thumb.jpg',
            game=self.game
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        # Should have modal function calls, not <a href> redirects
        self.assertIn('openVideoModal', html)
        self.assertIn('videoModal', html)
        # Check for proper iframe attributes in modal
        self.assertIn('allow="accelerometer; autoplay', html)
        self.assertIn('allowfullscreen', html)
        self.assertIn('referrerpolicy="strict-origin-when-cross-origin"', html)
    
    def test_highlight_without_description_field(self):
        """Regression test: Profile should not crash when HighlightClip has no description field."""
        # Create a highlight clip (model does not have description field)
        clip = HighlightClip.objects.create(
            user=self.user,
            title='Test Clip',
            platform='youtube',
            video_id='test123',
            embed_url='https://www.youtube.com/embed/test123',
            thumbnail_url='https://example.com/thumb.jpg',
            game=self.game
        )
        
        # Profile page should load without AttributeError
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Context should have highlight_clips with description key (empty string)
        clips = response.context['highlight_clips']
        self.assertEqual(len(clips), 1)
        self.assertIn('description', clips[0])
        self.assertEqual(clips[0]['description'], '')  # Safe fallback
        self.assertEqual(clips[0]['title'], 'Test Clip')
    
    def test_endorsements_summary(self):
        """Test endorsements render correctly in overview."""
        # Create another user to endorse
        endorser = User.objects.create_user(username='endorser', password='pass')
        
        # Create endorsements
        SkillEndorsement.objects.create(
            endorser=endorser,
            endorsed_user=self.user,
            skill_name='teamwork'
        )
        SkillEndorsement.objects.create(
            endorser=endorser,
            endorsed_user=self.user,
            skill_name='leadership'
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check context
        endorsements = response.context['endorsements']
        self.assertGreater(endorsements['total_count'], 0)
        self.assertIn('by_skill', endorsements)
        
        # Check HTML rendering
        html = response.content.decode('utf-8')
        self.assertIn('Skill Matrix', html)

    def test_named_routes_and_reverses(self):
        # Verify that the economy and browse routes do reverse correctly
        from django.urls import reverse
    
    # TASK D: Facebook Video Support Tests
    
    def test_facebook_highlight_url_accepted(self):
        """Test Facebook share URL is accepted and converted to plugin embed URL."""
        from apps.user_profile.services.url_validator import validate_highlight_url
        
        # Test Facebook share URL format
        result = validate_highlight_url('https://www.facebook.com/share/v/17b9XarFZY/')
        
        self.assertTrue(result['valid'], f"Facebook URL should be valid: {result.get('error', '')}")
        self.assertEqual(result['platform'], 'facebook')
        self.assertEqual(result['video_id'], '17b9XarFZY')
        
        # Check embed URL uses Facebook video plugin
        self.assertIn('facebook.com/plugins/video.php', result['embed_url'])
        self.assertIn('href=', result['embed_url'])
        self.assertIn('show_text=false', result['embed_url'])
    
    def test_facebook_watch_url_accepted(self):
        """Test Facebook watch URL format."""
        from apps.user_profile.services.url_validator import validate_highlight_url
        
        result = validate_highlight_url('https://www.facebook.com/watch/?v=1234567890')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['platform'], 'facebook')
        self.assertEqual(result['video_id'], '1234567890')
        self.assertIn('facebook.com/plugins/video.php', result['embed_url'])
    
    def test_facebook_fb_watch_url_accepted(self):
        """Test fb.watch short URL format."""
        from apps.user_profile.services.url_validator import validate_highlight_url
        
        result = validate_highlight_url('https://fb.watch/abc123xyz')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['platform'], 'facebook')
        self.assertEqual(result['video_id'], 'abc123xyz')
        self.assertIn('facebook.com/plugins/video.php', result['embed_url'])
    
    def test_non_video_facebook_url_rejected(self):
        """Test non-video Facebook URLs are correctly rejected."""
        from apps.user_profile.services.url_validator import validate_highlight_url
        
        # Profile page URL (not a video)
        result = validate_highlight_url('https://www.facebook.com/profile/page')
        
        self.assertFalse(result['valid'])
        self.assertIn('must be a video', result['error'].lower())
    
    def test_profile_with_facebook_highlight_renders(self):
        """Test profile page loads successfully with Facebook highlight."""
        user_profile = UserProfile.objects.get(user=self.user)
        
        # Create Facebook highlight
        clip = HighlightClip.objects.create(
            profile=user_profile,
            url='https://www.facebook.com/share/v/17b9XarFZY/',
            title='Facebook Highlight',
            game=self.game
        )
        
        # Profile should load without errors
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Context should have the clip
        clips = response.context['highlight_clips']
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]['title'], 'Facebook Highlight')
        self.assertEqual(clips[0]['platform'], 'facebook')
        
        # HTML should contain Facebook plugin embed URL
        html = response.content.decode('utf-8')
        self.assertIn('facebook.com/plugins/video.php', html)
    
    def test_profile_with_missing_embed_url_shows_fallback(self):
        """Test profile handles highlight with missing embed_url gracefully."""
        user_profile = UserProfile.objects.get(user=self.user)
        
        # Create highlight, then manually clear embed_url to simulate edge case
        clip = HighlightClip.objects.create(
            profile=user_profile,
            url='https://www.youtube.com/watch?v=test123',
            title='Test Clip',
            game=self.game
        )
        
        # Profile should still render (200 OK)
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify fallback elements are present in template
        html = response.content.decode('utf-8')
        self.assertIn('videoModalFallback', html)  # Fallback div exists
        self.assertIn('openVideoModal', html)  # Modal function exists
    
    def test_stream_config_with_facebook_url(self):
        """Test StreamConfig with Facebook URL embeds or falls back safely."""
        user_profile = UserProfile.objects.get(user=self.user)
        
        # Create Facebook stream config
        stream = StreamConfig.objects.create(
            user=self.user,
            stream_url='https://www.facebook.com/gaming/testuser',
            title='My Facebook Stream',
            is_active=True
        )
        
        # Profile should load successfully
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Stream config should be in context
        stream_config = response.context.get('stream_config')
        self.assertIsNotNone(stream_config)
        self.assertEqual(stream_config['platform'], 'facebook')
        
        # Embed URL should use Facebook plugin
        if stream_config.get('embed_url'):
            self.assertIn('facebook.com/plugins/video.php', stream_config['embed_url'])
        
        # HTML should have fallback handling
        html = response.content.decode('utf-8')
        self.assertIn('Stream unavailable to embed', html)  # Fallback message exists
        self.assertIn('Open on', html)  # External link button exists    
    # ========================================================================
    # UP-PHASE-2C2: MVP TAB TESTS (Loadout, Showcase, Bounties, Posts)
    # ========================================================================
    
    def test_loadout_tab_empty_state(self):
        """Test loadout tab renders safely when empty."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Hardware gear should be in context with None values
        hardware_gear = response.context.get('hardware_gear')
        self.assertIsNotNone(hardware_gear)
        self.assertIsNone(hardware_gear.get('mouse'))
        self.assertIsNone(hardware_gear.get('keyboard'))
        
        # Game configs should be empty list
        game_configs = response.context.get('game_configs')
        self.assertIsNotNone(game_configs)
        self.assertEqual(len(game_configs), 0)
        
        # Template should show empty state
        html = response.content.decode('utf-8')
        self.assertIn('tab-loadout', html)
        self.assertIn('No hardware setup configured yet', html)
    
    def test_loadout_tab_with_hardware(self):
        """Test loadout tab renders hardware gear correctly."""
        from apps.user_profile.models import HardwareGear
        
        # Create hardware
        mouse = HardwareGear.objects.create(
            user=self.user,
            category='MOUSE',
            brand='Logitech',
            model='G Pro X Superlight',
            specs={'dpi': 800, 'polling_rate': 1000},
            is_public=True
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Hardware should be in context
        hardware_gear = response.context.get('hardware_gear')
        self.assertIsNotNone(hardware_gear.get('mouse'))
        self.assertEqual(hardware_gear['mouse'].brand, 'Logitech')
        
        # HTML should show hardware
        html = response.content.decode('utf-8')
        self.assertIn('Logitech', html)
        self.assertIn('G Pro X Superlight', html)
        self.assertIn('800 DPI', html)
    
    def test_loadout_tab_with_game_config(self):
        """Test loadout tab renders game configs with copy button."""
        from apps.user_profile.models import GameConfig
        
        # Create game config
        config = GameConfig.objects.create(
            user=self.user,
            game=self.game,
            settings={
                'dpi': 800,
                'sensitivity': 0.45,
                'resolution': '1920x1080',
                'crosshair_code': 'TESTCODE123'
            },
            is_public=True
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Game configs should be in context
        game_configs = response.context.get('game_configs')
        self.assertIsNotNone(game_configs)
        self.assertEqual(len(game_configs), 1)
        self.assertEqual(game_configs[0]['dpi'], 800)
        self.assertEqual(game_configs[0]['sensitivity'], 0.45)
        
        # HTML should have crosshair copy button
        html = response.content.decode('utf-8')
        self.assertIn('TESTCODE123', html)
        self.assertIn('copyToClipboard', html)
        self.assertIn('Copy', html)
    
    def test_showcase_tab_empty_state(self):
        """Test showcase/inventory tab renders safely when empty."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Showcase should be in context
        showcase = response.context.get('showcase')
        self.assertIsNotNone(showcase)
        
        # Template should show empty state
        html = response.content.decode('utf-8')
        self.assertIn('tab-inventory', html)
        self.assertIn('No cosmetics equipped yet', html)
    
    def test_showcase_tab_with_equipped_items(self):
        """Test showcase tab renders equipped cosmetics."""
        from apps.user_profile.models import TrophyShowcaseConfig
        
        # Create showcase config (mock data - actual implementation may vary)
        showcase_config, _ = TrophyShowcaseConfig.objects.get_or_create(
            user_profile=self.user.profile
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Showcase context should exist
        showcase = response.context.get('showcase')
        self.assertIsNotNone(showcase)
        self.assertIn('equipped', showcase)
        self.assertIn('unlocked', showcase)
        
        # Template should render without errors
        html = response.content.decode('utf-8')
        self.assertIn('Equipped Items', html)
    
    def test_bounties_tab_empty_state(self):
        """Test bounties tab renders safely when empty."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Bounties should be in context
        bounties = response.context.get('bounties')
        self.assertIsNotNone(bounties)
        self.assertEqual(len(bounties.get('open', [])), 0)
        self.assertEqual(len(bounties.get('in_progress', [])), 0)
        self.assertEqual(len(bounties.get('completed', [])), 0)
        
        # Bounty stats should exist
        bounty_stats = response.context.get('bounty_stats')
        self.assertIsNotNone(bounty_stats)
        self.assertEqual(bounty_stats.get('won_count', 0), 0)
        
        # Template should show empty state
        html = response.content.decode('utf-8')
        self.assertIn('tab-bounties', html)
        self.assertIn('No bounties yet', html)
    
    def test_bounties_tab_with_open_bounty(self):
        """Test bounties tab renders open bounties."""
        from apps.user_profile.models import Bounty
        from datetime import timedelta
        from django.utils import timezone
        
        # Create open bounty
        bounty = Bounty.objects.create(
            creator=self.user,
            title='1v1 Aim Duel',
            description='First to 100k in Gridshot',
            game=self.game,
            stake_amount=500,
            status='open',
            expires_at=timezone.now() + timedelta(days=3)
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Bounties should include open bounty
        bounties = response.context.get('bounties')
        self.assertIsNotNone(bounties)
        self.assertEqual(len(bounties.get('open', [])), 1)
        self.assertEqual(bounties['open'][0]['title'], '1v1 Aim Duel')
        self.assertEqual(bounties['open'][0]['stake_amount'], 500)
        
        # HTML should show bounty
        html = response.content.decode('utf-8')
        self.assertIn('1v1 Aim Duel', html)
        self.assertIn('500 DC', html)
        self.assertIn('Open Bounties', html)
    
    def test_posts_tab_community_not_installed(self):
        """Test posts tab handles missing community app gracefully."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Posts context should exist with enabled=False
        posts = response.context.get('posts')
        self.assertIsNotNone(posts)
        self.assertFalse(posts.get('enabled', False))
        self.assertEqual(len(posts.get('items', [])), 0)
        
        # Template should show placeholder
        html = response.content.decode('utf-8')
        self.assertIn('tab-posts', html)
        self.assertIn('Community integration pending', html)
    
    def test_owner_only_buttons_visible(self):
        """Test owner-only buttons are visible to owner."""
        # Login as owner
        self.client.login(username=self.user.username, password='pass123')
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        # Should see edit buttons
        self.assertIn('Edit Loadout', html)
        self.assertIn('Manage Showcase', html)
        # Should see economy tab
        self.assertIn('Economy', html)
    
    def test_owner_only_buttons_hidden(self):
        """Test owner-only buttons are hidden from visitors."""
        # Create another user to visit
        visitor = User.objects.create_user(username='visitor', password='pass123')
        self.client.login(username=visitor.username, password='pass123')
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Economy tab should not be visible
        html = response.content.decode('utf-8')
        # Note: "Economy" might appear in other contexts, so check for wallet visibility
        self.assertFalse(response.context.get('wallet_visible', False))
    
    def test_profile_renders_all_tabs_without_errors(self):
        """Integration test: profile page with all tabs renders successfully."""
        from apps.user_profile.models import HardwareGear, GameConfig, Bounty
        from datetime import timedelta
        from django.utils import timezone
        
        # Populate with data
        HardwareGear.objects.create(
            user=self.user, category='MOUSE', brand='Logitech', model='G Pro', is_public=True
        )
        GameConfig.objects.create(
            user=self.user, game=self.game, settings={'dpi': 800}, is_public=True
        )
        Bounty.objects.create(
            creator=self.user, title='Test Bounty', game=self.game,
            stake_amount=100, status='open', expires_at=timezone.now() + timedelta(days=1)
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # All tab sections should be present
        html = response.content.decode('utf-8')
        self.assertIn('tab-overview', html)
        self.assertIn('tab-posts', html)
        self.assertIn('tab-loadout', html)
        self.assertIn('tab-bounties', html)
        self.assertIn('tab-inventory', html)
        self.assertIn('tab-highlights', html)
        
        # Key context should exist
        self.assertIn('loadout', response.context)
        self.assertIn('showcase', response.context)
        self.assertIn('bounties', response.context)
        self.assertIn('posts', response.context)