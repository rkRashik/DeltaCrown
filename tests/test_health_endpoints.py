"""
Tests for health check endpoints (Module 9.5).
Tests /healthz and /readyz endpoints.
"""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_healthz_returns_ok(self):
        """Test /healthz returns 200 OK."""
        client = Client()
        response = client.get('/healthz/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
    
    def test_readyz_all_healthy(self):
        """Test /readyz returns 200 when all dependencies are healthy."""
        client = Client()
        response = client.get('/readiness/')
        
        assert response.status_code == 200
        data = response.json()
        assert 'checks' in data
    
    def test_healthz_no_auth_required(self):
        """Test /healthz does not require authentication."""
        client = Client()
        response = client.get('/healthz/')
        
        assert response.status_code == 200
        # Should not return 401/403
        assert response.status_code not in [401, 403]
    
    def test_readyz_no_auth_required(self):
        """Test /readyz does not require authentication."""
        client = Client()
        response = client.get('/readiness/')
        
        # Should not return 401/403
        assert response.status_code not in [401, 403]
    
    def test_health_response_format(self):
        """Test health check response has correct format."""
        client = Client()
        response = client.get('/healthz/')
        
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'ok'
