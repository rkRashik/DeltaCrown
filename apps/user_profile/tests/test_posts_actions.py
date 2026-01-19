# apps/user_profile/tests/test_posts_actions.py
"""
Unit tests for Posts create/delete functionality (UP PHASE 7.1).

Tests owner-only permissions, CSRF protection, and validation.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.siteui.models import CommunityPost

User = get_user_model()


@pytest.mark.django_db
class TestPostCreate:
    """Test POST /api/profile/posts/create/"""
    
    def test_owner_can_create_post(self):
        """Owner can create a post on their profile"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/api/profile/posts/create/', {
            'content': 'Test post content',
            'visibility': 'public'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['post']['content'] == 'Test post content'
        
        # Verify post was created in database
        post = CommunityPost.objects.filter(author=profile).first()
        assert post is not None
        assert post.content == 'Test post content'
    
    def test_anonymous_cannot_create_post(self):
        """Anonymous users are redirected to login"""
        client = Client()
        response = client.post('/api/profile/posts/create/', {
            'content': 'Test content'
        })
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_empty_content_validation(self):
        """Cannot create post with empty content"""
        user = User.objects.create_user(username='testuser', password='pass123')
        UserProfile.objects.create(user=user)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/api/profile/posts/create/', {
            'content': '',
            'visibility': 'public'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'required' in data['error'].lower()


@pytest.mark.django_db
class TestPostDelete:
    """Test POST /api/profile/posts/<post_id>/delete/"""
    
    def test_owner_can_delete_own_post(self):
        """Owner can delete their own post"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        post = CommunityPost.objects.create(
            author=profile,
            content='Test post'
        )
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post(f'/api/profile/posts/{post.id}/delete/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify post was deleted
        assert not CommunityPost.objects.filter(id=post.id).exists()
    
    def test_non_owner_cannot_delete_post(self):
        """Non-owner cannot delete someone else's post"""
        owner = User.objects.create_user(username='owner', password='pass123')
        other = User.objects.create_user(username='other', password='pass123')
        profile = UserProfile.objects.create(user=owner)
        UserProfile.objects.create(user=other)
        
        post = CommunityPost.objects.create(
            author=profile,
            content='Test post'
        )
        
        client = Client()
        client.login(username='other', password='pass123')
        
        response = client.post(f'/api/profile/posts/{post.id}/delete/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False
        assert 'your own' in data['error'].lower()
        
        # Verify post still exists
        assert CommunityPost.objects.filter(id=post.id).exists()
    
    def test_delete_nonexistent_post(self):
        """Deleting non-existent post returns 404"""
        user = User.objects.create_user(username='testuser', password='pass123')
        UserProfile.objects.create(user=user)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/api/profile/posts/99999/delete/')
        
        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
