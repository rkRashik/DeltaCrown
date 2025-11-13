"""
Tests for Admin Read-Only Webhook API.

Validates admin API endpoints return correct data with proper authentication.
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.notifications.models import WebhookDelivery
import uuid

User = get_user_model()


@pytest.fixture
def staff_user(db):
    """Create staff user for authentication."""
    return User.objects.create_user(
        username="admin_test",
        email="admin@test.com",
        password="testpass123",
        is_staff=True
    )


@pytest.fixture
def regular_user(db):
    """Create regular user (non-staff) for permission tests."""
    return User.objects.create_user(
        username="regular_test",
        email="regular@test.com",
        password="testpass123",
        is_staff=False
    )


@pytest.fixture
def auth_client(staff_user):
    """Return authenticated client."""
    client = Client()
    client.force_login(staff_user)
    return client


@pytest.fixture
def sample_webhooks(db):
    """Create sample webhook deliveries."""
    now = timezone.now()
    
    webhooks = []
    
    # 5 successful payment_verified webhooks
    for i in range(5):
        webhooks.append(WebhookDelivery.objects.create(
            id=uuid.uuid4(),
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            payload={"payment_id": 1000 + i},
            status_code=200,
            latency_ms=150 + i * 10,
            retry_count=0,
            created_at=now - timedelta(minutes=i),
            delivered_at=now - timedelta(minutes=i),
            circuit_breaker_state="closed",
        ))
    
    # 2 failed match_started webhooks (503)
    for i in range(2):
        webhooks.append(WebhookDelivery.objects.create(
            id=uuid.uuid4(),
            event="match_started",
            endpoint="https://api.example.com/webhooks",
            payload={"match_id": 2000 + i},
            status_code=503,
            latency_ms=None,
            retry_count=1,
            created_at=now - timedelta(minutes=10 + i),
            delivered_at=None,
            error_message="Service Unavailable",
            circuit_breaker_state="closed",
        ))
    
    # 1 webhook with circuit breaker open
    webhooks.append(WebhookDelivery.objects.create(
        id=uuid.uuid4(),
        event="tournament_registration_opened",
        endpoint="https://api.receiver2.com/hooks",
        payload={"tournament_id": 501},
        status_code=503,
        latency_ms=None,
        retry_count=3,
        created_at=now - timedelta(minutes=2),
        delivered_at=None,
        error_message="Circuit breaker open",
        circuit_breaker_state="open",
    ))
    
    return webhooks


@pytest.mark.django_db
class TestWebhookDeliveriesList:
    """Test GET /admin/api/webhooks/deliveries endpoint."""

    def test_list_webhooks_requires_authentication(self):
        """Test that endpoint requires authentication."""
        client = Client()
        response = client.get("/admin/api/webhooks/deliveries")
        assert response.status_code == 302  # Redirect to login

    def test_list_webhooks_requires_staff(self, regular_user):
        """Test that endpoint requires staff permissions."""
        client = Client()
        client.force_login(regular_user)
        response = client.get("/admin/api/webhooks/deliveries")
        assert response.status_code == 302  # Redirect (not authorized)

    def test_list_webhooks_success(self, auth_client, sample_webhooks):
        """Test successful webhook list retrieval."""
        response = auth_client.get("/admin/api/webhooks/deliveries")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "results" in data
        assert data["count"] == 8  # 5 success + 2 failed + 1 CB open
        assert len(data["results"]) == 8

    def test_filter_by_event(self, auth_client, sample_webhooks):
        """Test filtering by event type."""
        response = auth_client.get("/admin/api/webhooks/deliveries?event=payment_verified")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5
        for result in data["results"]:
            assert result["event"] == "payment_verified"

    def test_filter_by_status(self, auth_client, sample_webhooks):
        """Test filtering by status (success/failed)."""
        response = auth_client.get("/admin/api/webhooks/deliveries?status=success")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5  # Only successful webhooks
        for result in data["results"]:
            assert result["status"] == "success"

    def test_filter_by_endpoint(self, auth_client, sample_webhooks):
        """Test filtering by endpoint (partial match)."""
        response = auth_client.get("/admin/api/webhooks/deliveries?endpoint=receiver2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 1
        assert "receiver2" in data["results"][0]["endpoint"]

    def test_pagination(self, auth_client, sample_webhooks):
        """Test pagination parameters."""
        response = auth_client.get("/admin/api/webhooks/deliveries?page_size=3&page=1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["page_size"] == 3
        assert data["page"] == 1
        assert len(data["results"]) == 3
        assert data["total_pages"] == 3  # 8 webhooks / 3 per page

    def test_result_structure(self, auth_client, sample_webhooks):
        """Test that results have expected structure."""
        response = auth_client.get("/admin/api/webhooks/deliveries")
        data = response.json()
        
        result = data["results"][0]
        required_keys = [
            "id", "event", "endpoint", "status", "status_code",
            "created_at", "delivered_at", "latency_ms", "retry_count",
            "circuit_breaker_state"
        ]
        for key in required_keys:
            assert key in result


@pytest.mark.django_db
class TestWebhookDeliveryDetail:
    """Test GET /admin/api/webhooks/deliveries/<id> endpoint."""

    def test_detail_requires_authentication(self, sample_webhooks):
        """Test that endpoint requires authentication."""
        webhook_id = sample_webhooks[0].id
        client = Client()
        response = client.get(f"/admin/api/webhooks/deliveries/{webhook_id}")
        assert response.status_code == 302  # Redirect to login

    def test_detail_success(self, auth_client, sample_webhooks):
        """Test successful webhook detail retrieval."""
        webhook = sample_webhooks[0]
        response = auth_client.get(f"/admin/api/webhooks/deliveries/{webhook.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(webhook.id)
        assert data["event"] == "payment_verified"
        assert data["status_code"] == 200

    def test_detail_not_found(self, auth_client):
        """Test 404 for non-existent webhook."""
        fake_id = uuid.uuid4()
        response = auth_client.get(f"/admin/api/webhooks/deliveries/{fake_id}")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data

    def test_detail_includes_payload(self, auth_client, sample_webhooks):
        """Test that detail includes full payload."""
        webhook = sample_webhooks[0]
        response = auth_client.get(f"/admin/api/webhooks/deliveries/{webhook.id}")
        data = response.json()
        
        assert "payload" in data
        assert data["payload"]["payment_id"] == 1000

    def test_detail_redacts_signature(self, auth_client, sample_webhooks):
        """Test that signature is redacted in headers."""
        webhook = sample_webhooks[0]
        webhook.request_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": "secret_signature_123"
        }
        webhook.save()
        
        response = auth_client.get(f"/admin/api/webhooks/deliveries/{webhook.id}")
        data = response.json()
        
        assert data["request_headers"]["X-Webhook-Signature"] == "***REDACTED***"


@pytest.mark.django_db
class TestWebhookStatistics:
    """Test GET /admin/api/webhooks/statistics endpoint."""

    def test_statistics_requires_authentication(self):
        """Test that endpoint requires authentication."""
        client = Client()
        response = client.get("/admin/api/webhooks/statistics")
        assert response.status_code == 302

    def test_statistics_success(self, auth_client, sample_webhooks):
        """Test successful statistics retrieval."""
        response = auth_client.get("/admin/api/webhooks/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_deliveries" in data
        assert "success_count" in data
        assert "success_rate" in data
        assert "latency" in data
        assert "by_event" in data

    def test_statistics_counts(self, auth_client, sample_webhooks):
        """Test that statistics counts are correct."""
        response = auth_client.get("/admin/api/webhooks/statistics")
        data = response.json()
        
        assert data["total_deliveries"] == 8
        assert data["success_count"] == 5
        assert data["failure_count"] == 3
        assert data["success_rate"] == 62.5  # 5/8 * 100

    def test_statistics_latency_metrics(self, auth_client, sample_webhooks):
        """Test latency percentiles."""
        response = auth_client.get("/admin/api/webhooks/statistics")
        data = response.json()
        
        latency = data["latency"]
        assert latency["min_ms"] == 150
        assert latency["max_ms"] == 190
        assert latency["p50_ms"] is not None
        assert latency["p95_ms"] is not None

    def test_statistics_by_event(self, auth_client, sample_webhooks):
        """Test event breakdown."""
        response = auth_client.get("/admin/api/webhooks/statistics")
        data = response.json()
        
        by_event = data["by_event"]
        payment_stats = next(e for e in by_event if e["event"] == "payment_verified")
        assert payment_stats["count"] == 5
        assert payment_stats["success_count"] == 5
        assert payment_stats["success_rate"] == 100.0

    def test_statistics_circuit_breaker(self, auth_client, sample_webhooks):
        """Test circuit breaker statistics."""
        response = auth_client.get("/admin/api/webhooks/statistics")
        data = response.json()
        
        cb_stats = data["circuit_breaker"]
        assert "opens_last_24h" in cb_stats
        assert "currently_open_endpoints" in cb_stats


@pytest.mark.django_db
class TestCircuitBreakerStatus:
    """Test GET /admin/api/webhooks/circuit-breaker endpoint."""

    def test_circuit_breaker_status_requires_authentication(self):
        """Test that endpoint requires authentication."""
        client = Client()
        response = client.get("/admin/api/webhooks/circuit-breaker")
        assert response.status_code == 302

    def test_circuit_breaker_status_success(self, auth_client, sample_webhooks):
        """Test successful CB status retrieval."""
        response = auth_client.get("/admin/api/webhooks/circuit-breaker")
        assert response.status_code == 200
        
        data = response.json()
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)

    def test_circuit_breaker_status_structure(self, auth_client, sample_webhooks):
        """Test CB status structure."""
        response = auth_client.get("/admin/api/webhooks/circuit-breaker")
        data = response.json()
        
        endpoint = data["endpoints"][0]
        required_keys = [
            "endpoint", "state", "failure_count", "last_failure",
            "last_success", "opens_last_24h", "half_open_probe_due"
        ]
        for key in required_keys:
            assert key in endpoint

    def test_circuit_breaker_detects_open_state(self, auth_client, sample_webhooks):
        """Test that open circuit breakers are detected."""
        response = auth_client.get("/admin/api/webhooks/circuit-breaker")
        data = response.json()
        
        open_endpoints = [e for e in data["endpoints"] if e["state"] == "open"]
        assert len(open_endpoints) == 1
        assert "receiver2" in open_endpoints[0]["endpoint"]
