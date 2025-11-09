"""Simple test to validate test auth middleware works"""
import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from tests.test_auth_middleware import create_test_websocket_app

User = get_user_model()


@pytest.mark.asyncio
@pytest.mark.django_db()  # Remove transaction=True to allow cross-connection visibility
async def test_auth_middleware_sets_user():
    """Test that test auth middleware correctly sets user in scope"""
    import uuid
    
    # Create a simple user with unique username
    @database_sync_to_async
    def create_user():
        unique_id = uuid.uuid4().hex[:10]
        return User.objects.create_user(
            username=f'testuser_{unique_id}',
            email=f'{unique_id}@example.com',
            password='testpass'
        )
    
    user = await create_user()
    
    # Try to connect to tournament channel with test auth
    test_app = create_test_websocket_app()
    communicator = WebsocketCommunicator(
        test_app,
        f"/ws/tournament/999/?user_id={user.id}"  # Tournament doesn't need to exist for auth test
    )
    
    connected, _ = await communicator.connect()
    
    if not connected:
        # Try to get error message
        try:
            response = await communicator.receive_json_from(timeout=1)
            print(f"Error response: {response}")
        except:
            pass
    
    print(f"Connected: {connected}, User ID: {user.id}")
    assert connected, f"Should connect with test auth (user_id={user.id})"
    
    await communicator.disconnect()
