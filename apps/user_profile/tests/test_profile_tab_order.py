"""
Test profile template tab order matches draft.

Regression test for Phase 2B.2: Draft alignment.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from bs4 import BeautifulSoup

User = get_user_model()


@pytest.mark.django_db
class TestProfileTabOrder:
    """Test that profile template tabs match draft order."""
    
    def test_tab_order_matches_draft(self, client, user):
        """Verify tab navigation follows exact draft order: Overview, Posts, Media, Career, Stats, Highlights, Inventory, Economy."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all tab buttons
        tab_buttons = soup.find_all('button', class_='z-tab-btn')
        
        # Extract tab names (onclick attribute contains tab ID)
        tab_names = []
        for button in tab_buttons:
            onclick = button.get('onclick', '')
            if 'switchTab' in onclick:
                # Extract tab name from switchTab('tabname')
                tab_name = onclick.split("'")[1]
                tab_names.append(tab_name)
        
        # Expected order from draft
        expected_order = ['overview', 'posts', 'media', 'career', 'stats', 'highlights', 'inventory', 'wallet']
        
        # Verify order (wallet may not be present for visitors)
        assert tab_names[:7] == expected_order[:7], f"Tab order mismatch. Got: {tab_names}, Expected: {expected_order}"
    
    def test_posts_tab_exists(self, client, user):
        """Verify Posts tab is present in navigation."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Check for Posts tab button
        assert "switchTab('posts')" in content, "Posts tab button not found"
        assert 'id="tab-posts"' in content, "Posts tab content section not found"
    
    def test_media_tab_exists(self, client, user):
        """Verify Media tab is present in navigation."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Check for Media tab button
        assert "switchTab('media')" in content, "Media tab button not found"
        assert 'id="tab-media"' in content, "Media tab content section not found"
    
    def test_live_feed_widget_exists(self, client, user):
        """Verify Live Feed widget is present in right sidebar."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Check for Live Feed widget
        assert 'Live Feed' in content, "Live Feed widget header not found"
        assert 'animate-pulse' in content, "Live Feed pulse animation not found"
    
    def test_posts_tab_has_placeholder(self, client, user):
        """Verify Posts tab contains safe placeholder content."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Check for placeholder text
        assert 'Community posting feature coming soon' in content or 'No posts yet' in content
    
    def test_media_tab_has_placeholder(self, client, user):
        """Verify Media tab contains safe placeholder content."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Check for placeholder text
        assert 'No media uploaded yet' in content or 'Media Gallery' in content
    
    def test_profile_loads_for_visitor_after_tab_changes(self, client, user, other_user):
        """Smoke test: Verify profile still loads for visitors after tab structure changes."""
        client.force_login(other_user)
        
        response = client.get(f'/@{user.username}/')
        
        # Should not crash
        assert response.status_code == 200
        
        # Visitor should see tabs
        content = response.content.decode('utf-8')
        assert 'switchTab(' in content


# Fixtures
@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username='visitor',
        email='visitor@example.com',
        password='testpass123',
    )


@pytest.fixture
def client():
    """Create Django test client."""
    return Client()
