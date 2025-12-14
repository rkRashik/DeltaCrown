"""
Tests for Homepage Content Management System

Tests the HomePageContent model, singleton behavior, and context provider.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.siteui.models import HomePageContent
from apps.siteui.homepage_context import get_homepage_context

User = get_user_model()


class HomePageContentModelTest(TestCase):
    """Test HomePageContent model behavior."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_singleton_creation(self):
        """Test that only one HomePageContent instance can exist."""
        # First instance should succeed
        content1 = HomePageContent.get_instance()
        self.assertIsNotNone(content1)
        self.assertEqual(content1.pk, 1)
        
        # Second attempt should return same instance
        content2 = HomePageContent.get_instance()
        self.assertEqual(content1.pk, content2.pk)
        
        # Total count should be 1
        self.assertEqual(HomePageContent.objects.count(), 1)
    
    def test_manual_creation_blocked(self):
        """Test that manually creating a second instance raises ValidationError."""
        # Create first instance
        HomePageContent.get_instance()
        
        # Attempting to create another should fail
        with self.assertRaises(ValidationError):
            content2 = HomePageContent()
            content2.save()
    
    def test_default_content_initialized(self):
        """Test that default content is properly initialized."""
        content = HomePageContent.get_instance()
        
        # Check hero section
        self.assertEqual(content.hero_title, "From the Delta to the Crown")
        self.assertEqual(content.hero_subtitle, "Where Champions Rise")
        self.assertIn("geography does not define destiny", content.hero_description)
        
        # Check CTAs
        self.assertEqual(content.primary_cta_text, "Join Tournament")
        self.assertEqual(content.primary_cta_url, "/tournaments/")
        self.assertEqual(content.secondary_cta_text, "Explore Teams")
        
        # Check JSON fields initialized
        self.assertIsInstance(content.hero_highlights, list)
        self.assertGreater(len(content.hero_highlights), 0)
        self.assertIsInstance(content.ecosystem_pillars, list)
        self.assertEqual(len(content.ecosystem_pillars), 8)  # 8 pillars
        self.assertIsInstance(content.games_data, list)
        self.assertEqual(len(content.games_data), 11)  # 11 official games
        self.assertIsInstance(content.payment_methods, list)
        self.assertEqual(len(content.payment_methods), 4)  # 4 payment methods
        
        # Check platform info
        self.assertEqual(content.platform_founded_year, 2025)
        self.assertEqual(content.platform_founder, "Redwanul Rashik")
    
    def test_section_toggles_default_enabled(self):
        """Test that all sections are enabled by default."""
        content = HomePageContent.get_instance()
        
        self.assertTrue(content.problem_section_enabled)
        self.assertTrue(content.pillars_section_enabled)
        self.assertTrue(content.games_section_enabled)
        self.assertTrue(content.tournaments_section_enabled)
        self.assertTrue(content.teams_section_enabled)
        self.assertTrue(content.payments_section_enabled)
        self.assertTrue(content.deltacoin_section_enabled)
        self.assertTrue(content.community_section_enabled)
        self.assertTrue(content.roadmap_section_enabled)
        self.assertTrue(content.final_cta_section_enabled)
    
    def test_updated_by_tracking(self):
        """Test that updated_by field tracks the last editor."""
        content = HomePageContent.get_instance()
        
        # Initially should be None
        self.assertIsNone(content.updated_by)
        
        # Update with user
        content.updated_by = self.user
        content.hero_title = "New Title"
        content.save()
        
        # Reload and check
        content.refresh_from_db()
        self.assertEqual(content.updated_by, self.user)


class HomePageContextProviderTest(TestCase):
    """Test homepage_context.py context provider."""
    
    def test_get_homepage_context_returns_dict(self):
        """Test that get_homepage_context returns a structured dict."""
        context = get_homepage_context()
        
        self.assertIsInstance(context, dict)
        self.assertIn('homepage_content', context)
        self.assertIn('hero', context)
        self.assertIn('live_stats', context)
        self.assertIn('sections_enabled', context)
    
    def test_hero_context_structure(self):
        """Test hero context has correct structure."""
        context = get_homepage_context()
        hero = context['hero']
        
        self.assertIn('badge_text', hero)
        self.assertIn('title', hero)
        self.assertIn('subtitle', hero)
        self.assertIn('description', hero)
        self.assertIn('primary_cta', hero)
        self.assertIn('secondary_cta', hero)
        self.assertIn('highlights', hero)
        
        # Check CTA structure
        self.assertIn('text', hero['primary_cta'])
        self.assertIn('url', hero['primary_cta'])
        self.assertIn('icon', hero['primary_cta'])
    
    def test_live_stats_computed(self):
        """Test that live_stats contains computed values."""
        context = get_homepage_context()
        stats = context['live_stats']
        
        self.assertIn('players_count', stats)
        self.assertIn('tournaments_count', stats)
        self.assertIn('teams_count', stats)
        self.assertIn('games_count', stats)
        
        # games_count should always be 11 (static)
        self.assertEqual(stats['games_count'], 11)
        
        # Counts should be non-negative integers
        self.assertIsInstance(stats['players_count'], int)
        self.assertGreaterEqual(stats['players_count'], 0)
    
    def test_sections_enabled_map(self):
        """Test that sections_enabled provides boolean flags."""
        context = get_homepage_context()
        sections = context['sections_enabled']
        
        self.assertIsInstance(sections, dict)
        self.assertIn('problem', sections)
        self.assertIn('pillars', sections)
        self.assertIn('games', sections)
        self.assertIn('payments', sections)
        
        # All should be booleans
        for key, value in sections.items():
            self.assertIsInstance(value, bool)
    
    def test_all_sections_present(self):
        """Test that all expected sections are in context."""
        context = get_homepage_context()
        
        expected_sections = [
            'hero', 'problem', 'pillars', 'games',
            'tournaments', 'teams', 'payments', 'deltacoin',
            'community', 'roadmap', 'final_cta', 'platform'
        ]
        
        for section in expected_sections:
            self.assertIn(section, context, f"Missing section: {section}")
    
    def test_context_safe_with_no_content(self):
        """Test that context provider handles missing HomePageContent gracefully."""
        # Delete all content
        HomePageContent.objects.all().delete()
        
        # Should still return valid context (via get_or_create)
        context = get_homepage_context()
        
        self.assertIsInstance(context, dict)
        self.assertIn('hero', context)
        self.assertIn('live_stats', context)
        
        # New instance should be created
        self.assertEqual(HomePageContent.objects.count(), 1)


class HomePageContentAdminTest(TestCase):
    """Test admin interface behavior."""
    
    def test_str_representation(self):
        """Test __str__ returns readable format."""
        content = HomePageContent.get_instance()
        str_repr = str(content)
        
        self.assertIn("Homepage Content", str_repr)
        self.assertIn("Updated:", str_repr)


# Pytest fixtures for use in other tests
@pytest.fixture
def homepage_content():
    """Fixture to get HomePageContent instance."""
    return HomePageContent.get_instance()


@pytest.fixture
def homepage_context():
    """Fixture to get homepage context."""
    return get_homepage_context()
