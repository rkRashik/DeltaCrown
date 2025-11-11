"""
Echo consumer for testing ASGI wiring.

This minimal consumer proves the test ASGI app, channel layer, and 
WebsocketCommunicator are working correctly. If this works, the issue
is in the tournament consumer's connect() logic, not the test infrastructure.
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer


import logging

logger = logging.getLogger(__name__)


class EchoConsumer(AsyncJsonWebsocketConsumer):
    """Minimal consumer that echoes received messages."""
    
    async def connect(self):
        """Accept connection and send welcome."""
        logger.info(f"EchoConsumer.connect() called, scope: {self.scope.get('path')}")
        try:
            await self.accept()
            logger.info("EchoConsumer accepted connection")
            await self.send_json({
                'type': 'echo_welcome',
                'message': 'Echo consumer connected successfully'
            })
            logger.info("EchoConsumer sent welcome message")
        except Exception as e:
            logger.error(f"EchoConsumer.connect() failed: {e}", exc_info=True)
            raise
    
    async def receive_json(self, content):
        """Echo received content back."""
        await self.send_json({
            'type': 'echo',
            'received': content
        })
    
    async def disconnect(self, close_code):
        """Handle disconnect."""
        pass
