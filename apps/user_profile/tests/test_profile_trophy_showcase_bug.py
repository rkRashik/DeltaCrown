# apps/user_profile/tests/test_profile_trophy_showcase_bug.py
"""
Regression test for TrophyShowcaseConfig validation error bug.

BUG: Visiting /@username/ crashed with ValidationError when
     pinned_badge_ids was NULL in the database.

FIX: Added blank=True to field and normalize None to [] in clean().
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from apps.user_profile.models import TrophyShowcaseConfig

User = get_user_model()


@pytest.mark.django_db
class TestTrophyShowcaseValidationFix:
    """Test that profile views don't raise ValidationError during GET."""

    def test_profile_view_with_null_badge_ids(self):
        """Profile GET should work even if pinned_badge_ids is None."""
        # Create user with showcase
        user = User.objects.create_user(
            username='testuser',
            password='test123',
            email='test@example.com'
        )
        
        # Simulate old DB row with NULL pinned_badge_ids
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        showcase.pinned_badge_ids = None
        # Use update() to bypass model validation
        TrophyShowcaseConfig.objects.filter(pk=showcase.pk).update(
            pinned_badge_ids=None
        )
        
        # Verify it's actually None in DB
        showcase.refresh_from_db()
        assert showcase.pinned_badge_ids is None
        
        # GET profile page should return 200 (not crash)
        client = Client()
        response = client.get(f'/@{user.username}/')
        
        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}"
    
    def test_profile_view_as_owner(self):
        """Owner viewing their own profile should not raise ValidationError."""
        user = User.objects.create_user(
            username='owner',
            password='test123',
            email='owner@example.com'
        )
        
        # Create showcase with NULL
        TrophyShowcaseConfig.objects.create(user=user)
        TrophyShowcaseConfig.objects.filter(user=user).update(
            pinned_badge_ids=None
        )
        
        # Login and view own profile
        client = Client()
        client.login(username='owner', password='test123')
        response = client.get(f'/@{user.username}/')
        
        assert response.status_code == 200
    
    def test_profile_view_as_visitor(self):
        """Visitor viewing profile should not raise ValidationError."""
        # Create profile owner
        owner = User.objects.create_user(
            username='profileowner',
            password='test123',
            email='owner@example.com'
        )
        TrophyShowcaseConfig.objects.create(user=owner)
        TrophyShowcaseConfig.objects.filter(user=owner).update(
            pinned_badge_ids=None
        )
        
        # Create visitor
        visitor = User.objects.create_user(
            username='visitor',
            password='test123',
            email='visitor@example.com'
        )
        
        # Visitor views owner's profile
        client = Client()
        client.login(username='visitor', password='test123')
        response = client.get(f'/@{owner.username}/')
        
        assert response.status_code == 200
    
    def test_showcase_clean_normalizes_none(self):
        """Model clean() should normalize None to empty list."""
        user = User.objects.create_user(
            username='testuser2',
            password='test123',
            email='test2@example.com'
        )
        
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Simulate NULL from DB
        showcase.pinned_badge_ids = None
        
        # Call clean() manually (normally called by save())
        showcase.clean()
        
        # Should be normalized to []
        assert showcase.pinned_badge_ids == []
    
    def test_showcase_save_with_none(self):
        """Saving showcase with None should normalize to [] and succeed."""
        user = User.objects.create_user(
            username='testuser3',
            password='test123',
            email='test3@example.com'
        )
        
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        showcase.pinned_badge_ids = None
        
        # This should NOT raise ValidationError
        showcase.save()
        
        showcase.refresh_from_db()
        assert showcase.pinned_badge_ids == []
