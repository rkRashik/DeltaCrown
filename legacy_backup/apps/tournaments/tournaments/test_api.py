"""
API Tests for Tournament Models

Quick verification that API endpoints are working correctly.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestTournamentAPI:
    """Test Tournament API endpoints"""
    
    def test_tournament_list_endpoint(self):
        """Test that tournament list endpoint is accessible"""
        client = APIClient()
        
        # Try to access list endpoint
        # Note: Actual URL pattern depends on main urls.py configuration
        # This is a basic smoke test
        response = client.get('/api/tournaments/tournaments/')
        
        # Should return 200 OK (even if empty list)
        assert response.status_code == 200
        assert 'results' in response.data or isinstance(response.data, list)
    
    def test_schedule_list_endpoint(self):
        """Test that schedule list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/schedules/')
        assert response.status_code == 200
    
    def test_capacity_list_endpoint(self):
        """Test that capacity list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/capacity/')
        assert response.status_code == 200
    
    def test_finance_list_endpoint(self):
        """Test that finance list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/finance/')
        assert response.status_code == 200
    
    def test_media_list_endpoint(self):
        """Test that media list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/media/')
        assert response.status_code == 200
    
    def test_rules_list_endpoint(self):
        """Test that rules list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/rules/')
        assert response.status_code == 200
    
    def test_archive_list_endpoint(self):
        """Test that archive list endpoint is accessible"""
        client = APIClient()
        response = client.get('/api/tournaments/archive/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestAPICustomActions:
    """Test custom API actions"""
    
    def test_tournaments_registration_open_action(self):
        """Test registration_open custom action"""
        client = APIClient()
        response = client.get('/api/tournaments/tournaments/registration_open/')
        assert response.status_code == 200
    
    def test_schedules_upcoming_action(self):
        """Test schedules upcoming custom action"""
        client = APIClient()
        response = client.get('/api/tournaments/schedules/upcoming/')
        assert response.status_code == 200
    
    def test_capacity_available_action(self):
        """Test capacity available custom action"""
        client = APIClient()
        response = client.get('/api/tournaments/capacity/available/')
        assert response.status_code == 200
    
    def test_finance_free_action(self):
        """Test finance free tournaments action"""
        client = APIClient()
        response = client.get('/api/tournaments/finance/free/')
        assert response.status_code == 200
    
    def test_archive_archived_action(self):
        """Test archive archived tournaments action"""
        client = APIClient()
        response = client.get('/api/tournaments/archive/archived/')
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
