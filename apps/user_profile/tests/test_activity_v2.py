"""
UP-UI-RESTORE-02: Activity Page Tests

Tests activity feed page rendering, pagination, and privacy filtering.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()


class ActivityPageTestCase(TestCase):
    """Test activity page rendering and functionality"""
    
    def setUp(self):
        """Create test user and profile"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='activitytest',
            email='activity@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.display_name = 'Activity Test User'
        self.profile.save()
    
    def test_activity_page_renders_for_public_user(self):
        """Test activity page renders for public profile"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'activitytest'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Activity Feed')
        self.assertContains(response, '@activitytest')
    
    def test_activity_page_shows_breadcrumb(self):
        """Test activity page shows breadcrumb navigation"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'activitytest'})
        response = self.client.get(url)
        
        profile_url = reverse('user_profile:profile_public_v2', kwargs={'username': 'activitytest'})
        self.assertContains(response, profile_url)
        self.assertContains(response, '@activitytest')
    
    def test_activity_page_shows_empty_state(self):
        """Test activity page shows empty state when no activities"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'activitytest'})
        response = self.client.get(url)
        
        self.assertContains(response, 'No Activity Yet')
    
    def test_activity_page_nonexistent_user_404(self):
        """Test activity page returns 404 for nonexistent user"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_activity_page_handles_pagination_param(self):
        """Test activity page handles page parameter"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'activitytest'})
        response = self.client.get(url + '?page=2')
        
        self.assertEqual(response.status_code, 200)
    
    def test_activity_page_handles_invalid_pagination(self):
        """Test activity page handles invalid page parameter gracefully"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'activitytest'})
        response = self.client.get(url + '?page=invalid')
        
        # Should default to page 1
        self.assertEqual(response.status_code, 200)


class ActivityPrivacyTestCase(TestCase):
    """Test activity feed privacy filtering"""
    
    def setUp(self):
        """Create test users"""
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        
        self.owner_profile, _ = UserProfile.objects.get_or_create(user=self.owner)
        self.owner_profile.display_name = 'Activity Owner'
        self.owner_profile.save()
    
    def test_activity_page_accessible_to_public(self):
        """Test activity page is accessible to non-logged-in users"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'owner'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_activity_page_accessible_to_owner(self):
        """Test activity page is accessible to profile owner"""
        self.client.login(username='owner', password='testpass123')
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'owner'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_activity_page_shows_owner_cta_when_empty(self):
        """Test empty state shows CTA for owner"""
        self.client.login(username='owner', password='testpass123')
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'owner'})
        response = self.client.get(url)
        
        self.assertContains(response, 'Start competing in tournaments')
        self.assertContains(response, 'Browse Tournaments')
    
    def test_activity_page_shows_different_message_for_visitors(self):
        """Test empty state shows different message for visitors"""
        self.client.login(username='viewer', password='testpass123')
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'owner'})
        response = self.client.get(url)
        
        self.assertContains(response, "hasn't participated in any events yet")


class ActivityEventDisplayTestCase(TestCase):
    """Test activity event display formatting"""
    
    def setUp(self):
        """Create test user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='eventtest',
            email='event@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
    
    def test_activity_page_has_event_icons(self):
        """Test activity page template includes event type icons"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'eventtest'})
        response = self.client.get(url)
        
        # Check for icon conditionals in template
        self.assertContains(response, 'tournament_joined')
        self.assertContains(response, 'tournament_won')
        self.assertContains(response, 'match_won')
        self.assertContains(response, 'achievement_earned')
    
    def test_activity_page_has_glassmorphic_styling(self):
        """Test activity page uses glassmorphic design"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'eventtest'})
        response = self.client.get(url)
        
        self.assertContains(response, 'bg-slate-900/60')
        self.assertContains(response, 'backdrop-blur-lg')
        self.assertContains(response, 'border-white/10')
