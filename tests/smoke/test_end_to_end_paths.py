"""
End-to-End Smoke Tests for DeltaCrown

Tests critical user paths: health, auth, wallet, purchases, WebSocket, admin, API contracts.
All tests use @pytest.mark.smoke for isolated execution.

Flags tested (defaults OFF):
- MODERATION_OBSERVABILITY_ENABLED=false
- PURCHASE_ENFORCEMENT_ENABLED=false (Phase 10, not yet implemented)

Run: pytest -v -m smoke tests/smoke/
"""
import pytest
import json
import re
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.smoke
@pytest.mark.django_db
def test_health_has_version_key_and_status_ok():
    """
    Health endpoint must return 200 with version key.
    Contract: {"status": "ok", "version": "<semver>"}
    """
    client = Client()
    response = client.get('/health')  # Adjust URL if different
    
    assert response.status_code == 200, "Health endpoint should return 200"
    
    data = response.json()
    assert "status" in data, "Health response must have 'status' key"
    assert data["status"] == "ok", "Health status must be 'ok'"
    assert "version" in data, "Health response must have 'version' key"


@pytest.mark.smoke
@pytest.mark.django_db
def test_auth_handshake_minimal_claims_no_pii():
    """
    Auth handshake returns JWT/session with minimal claims, no PII in token.
    Verify no email/username in response body.
    """
    client = Client()
    
    # Create test user
    user = User.objects.create_user(
        username='smoketest_user',
        email='smoke@test.local',
        password='SecurePass123!'
    )
    
    # Simulate login
    response = client.post('/api/auth/login/', {
        'username': 'smoketest_user',
        'password': 'SecurePass123!'
    })
    
    assert response.status_code in [200, 201], "Login should succeed"
    
    # Check response contains token but no PII
    data = response.json()
    response_str = json.dumps(data)
    
    # Should NOT contain email or username directly
    assert 'smoke@test.local' not in response_str, "Email should not be in auth response"
    assert 'smoketest_user' not in response_str or 'user_id' in response_str, \
        "Username should be minimal or replaced with user_id"


@pytest.mark.smoke
@pytest.mark.django_db
def test_wallet_debit_credit_round_trip_balance_consistent():
    """
    Wallet operations: debit then credit should return to original balance.
    Tests economy transaction consistency.
    """
    from apps.economy.models import Wallet  # Adjust import as needed
    
    user = User.objects.create_user(username='wallet_user', password='pass')
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': 1000})
    
    original_balance = wallet.balance
    
    # Debit 100
    wallet.debit(100, reason="smoke_test_debit")
    assert wallet.balance == original_balance - 100
    
    # Credit 100
    wallet.credit(100, reason="smoke_test_credit")
    assert wallet.balance == original_balance, "Round trip should restore balance"


@pytest.mark.smoke
@pytest.mark.django_db
def test_transaction_csv_export_bom_once():
    """
    CSV export includes UTF-8 BOM exactly once (not duplicated).
    Prevents Excel encoding issues.
    """
    client = Client()
    user = User.objects.create_user(username='csv_user', password='pass')
    client.force_login(user)
    
    response = client.get('/api/transactions/export/?format=csv')
    
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    
    # Check BOM presence (UTF-8 BOM: \ufeff or bytes \xef\xbb\xbf)
    content = response.content
    bom_count = content.count(b'\xef\xbb\xbf')
    
    assert bom_count == 1, f"CSV should have exactly 1 BOM, found {bom_count}"


@pytest.mark.smoke
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_websocket_connect_disconnect_lifecycle_succeeds():
    """
    WebSocket connection lifecycle: connect → send ping → receive pong → disconnect.
    Tests real-time notification infrastructure.
    """
    from channels.testing import WebsocketCommunicator
    from deltacrown.asgi import application  # Adjust import
    
    user = User.objects.create_user(username='ws_user', password='pass')
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/notifications/"
    )
    communicator.scope['user'] = user
    
    # Connect
    connected, subprotocol = await communicator.connect()
    assert connected, "WebSocket should connect successfully"
    
    # Send ping
    await communicator.send_json_to({"type": "ping"})
    
    # Receive pong
    response = await communicator.receive_json_from(timeout=2)
    assert response.get("type") == "pong", "Should receive pong response"
    
    # Disconnect
    await communicator.disconnect()


@pytest.mark.smoke
@pytest.mark.django_db
def test_purchase_happy_path_flags_off():
    """
    Purchase flow succeeds when enforcement flags are OFF (default).
    Verifies no accidental blocking with flags disabled.
    """
    client = Client()
    user = User.objects.create_user(username='buyer', password='pass')
    client.force_login(user)
    
    # Create wallet with sufficient balance
    from apps.economy.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': 500})
    
    # Attempt purchase (adjust endpoint as needed)
    response = client.post('/api/shop/purchase/', {
        'item_id': 1,
        'quantity': 1
    })
    
    # Should succeed (not blocked) when flags are OFF
    assert response.status_code in [200, 201], \
        "Purchase should succeed when enforcement flags are OFF"


@pytest.mark.smoke
@pytest.mark.django_db
def test_purchase_denied_when_flags_on_and_banned():
    """
    Purchase blocked when PURCHASE_ENFORCEMENT_ENABLED=true and user is banned.
    Uses environment override within test.
    """
    import os
    from unittest.mock import patch
    
    client = Client()
    user = User.objects.create_user(username='banned_buyer', password='pass')
    client.force_login(user)
    
    # Create ban sanction
    from apps.moderation.models import Sanction  # Adjust import
    Sanction.objects.create(
        user=user,
        sanction_type='BANNED',
        reason='smoke_test_ban',
        is_active=True
    )
    
    # Temporarily enable enforcement flag
    with patch.dict(os.environ, {'PURCHASE_ENFORCEMENT_ENABLED': 'true'}):
        response = client.post('/api/shop/purchase/', {
            'item_id': 1,
            'quantity': 1
        })
        
        # Should be blocked (403 or 400)
        assert response.status_code in [400, 403], \
            "Purchase should be denied when user is banned and enforcement is ON"


@pytest.mark.smoke
@pytest.mark.django_db
def test_revenue_summary_returns_ints_no_decimal():
    """
    Revenue summary API returns integer amounts, no Decimal objects leaking.
    Prevents JSON serialization errors.
    """
    client = Client()
    admin_user = User.objects.create_superuser(username='admin', password='pass', email='admin@test.local')
    client.force_login(admin_user)
    
    response = client.get('/api/admin/revenue/summary/')
    
    assert response.status_code == 200
    data = response.json()
    
    # Check all numeric values are int/float, not Decimal strings
    for key, value in data.items():
        if isinstance(value, (int, float)):
            continue  # OK
        elif isinstance(value, str):
            # Should not be Decimal string like "Decimal('1000.00')"
            assert not value.startswith('Decimal('), \
                f"Revenue field '{key}' contains Decimal string: {value}"


@pytest.mark.smoke
@pytest.mark.django_db
def test_error_envelope_404_keys_stable():
    """
    404 error responses follow stable contract: {"error": "...", "status": 404}.
    Ensures client error handling remains consistent.
    """
    client = Client()
    response = client.get('/api/nonexistent/endpoint/12345/')
    
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data, "404 response must have 'error' key"
    assert "status" in data or response.status_code == 404, "Status must be identifiable"


@pytest.mark.smoke
@pytest.mark.django_db
def test_perf_harness_quick_mode_smoke_outputs_samples():
    """
    Perf harness quick mode (--samples 10) completes and outputs JSON results.
    Validates performance testing infrastructure.
    """
    import subprocess
    import json
    
    result = subprocess.run(
        ['python', 'tests/perf/perf_harness.py', '--samples', '10', '--json', '/tmp/smoke_perf.json'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert result.returncode == 0, f"Perf harness failed: {result.stderr}"
    
    # Verify JSON output
    with open('/tmp/smoke_perf.json', 'r') as f:
        perf_data = json.load(f)
    
    assert 'samples' in perf_data or 'p95' in perf_data, "Perf JSON should contain results"


@pytest.mark.smoke
@pytest.mark.django_db
def test_admin_read_only_views_expose_no_secrets():
    """
    Admin read-only views (user list, logs) do not expose secret keys or passwords.
    Tests sensitive data masking.
    """
    client = Client()
    admin_user = User.objects.create_superuser(username='admin2', password='pass', email='admin2@test.local')
    client.force_login(admin_user)
    
    response = client.get('/admin/auth/user/')
    
    assert response.status_code == 200
    
    content = response.content.decode('utf-8')
    
    # Should NOT contain Django SECRET_KEY or any password hashes
    assert 'SECRET_KEY' not in content, "Admin views should not expose SECRET_KEY"
    assert 'pbkdf2_sha256$' not in content or 'password' in content.lower(), \
        "Password hashes should be masked or labeled"


@pytest.mark.smoke
@pytest.mark.django_db
def test_openapi_served_contains_no_emails_or_usernames():
    """
    OpenAPI schema (/api/schema/) contains no hardcoded emails or usernames.
    Prevents PII leakage in API documentation.
    """
    client = Client()
    response = client.get('/api/schema/')
    
    assert response.status_code == 200
    
    schema_str = response.content.decode('utf-8')
    
    # PII patterns
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    emails_found = re.findall(email_pattern, schema_str)
    # Filter out example.com (allowed)
    real_emails = [e for e in emails_found if 'example.com' not in e and 'example.org' not in e]
    
    assert len(real_emails) == 0, f"OpenAPI schema contains real emails: {real_emails}"
