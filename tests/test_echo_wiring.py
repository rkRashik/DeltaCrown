"""
Test echo consumer to verify ASGI wiring.

If this test passes, the test ASGI app, channel layer, and WebsocketCommunicator
are working correctly. The issue is then in the tournament consumer's connect() logic.
"""
import pytest
from channels.testing import WebsocketCommunicator
from tests.test_asgi import test_application as application


@pytest.mark.asyncio
async def test_echo_consumer_wiring():
    """Test that basic echo consumer works (no auth, no tournament logic)."""
    communicator = WebsocketCommunicator(application, "/ws/test/echo/")
    
    # Step 2: Enable exception visibility
    try:
        connected, subprotocol = await communicator.connect(timeout=5)
        
        assert connected, f"Echo consumer should connect, got close code: {subprotocol}"
        
        # Should receive welcome message
        welcome = await communicator.receive_json_from(timeout=2)
        assert welcome['type'] == 'echo_welcome'
        assert 'Echo consumer connected successfully' in welcome['message']
        
        # Test echo functionality
        await communicator.send_json_to({'test': 'ping'})
        response = await communicator.receive_json_from(timeout=2)
        assert response['type'] == 'echo'
        assert response['received'] == {'test': 'ping'}
        
        await communicator.disconnect()
        print("✓ Echo consumer test PASSED - ASGI wiring is correct")
        
    except Exception as e:
        print(f"✗ Echo consumer test FAILED: {e}")
        raise
