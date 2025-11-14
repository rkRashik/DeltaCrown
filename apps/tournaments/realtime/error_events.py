"""
WebSocket error event handlers (Module 9.5).
Handles authentication failures, rate limiting, and malformed messages.
"""
import logging
from channels.exceptions import DenyConnection
from django.conf import settings

logger = logging.getLogger('deltacrown.websocket')


class WebSocketErrorHandler:
    """
    Centralized WebSocket error handling.
    Logs errors and sends structured error events to clients.
    """
    
    @staticmethod
    def handle_auth_failure(user_id=None, reason="Authentication failed"):
        """
        Handle WebSocket authentication failure.
        
        Args:
            user_id: User ID if available
            reason: Reason for auth failure
        """
        logger.warning(
            f"WebSocket auth failure: {reason}",
            extra={
                'event_type': 'ws_auth_failure',
                'user_id': user_id,
                'reason': reason,
            }
        )
        raise DenyConnection(f"Authentication failed: {reason}")
    
    @staticmethod
    def handle_rate_limit(user_id, endpoint, limit):
        """
        Handle WebSocket rate limit exceeded.
        
        Args:
            user_id: User ID being rate limited
            endpoint: WebSocket endpoint
            limit: Rate limit that was exceeded
        """
        logger.warning(
            f"WebSocket rate limit exceeded: user={user_id}, endpoint={endpoint}",
            extra={
                'event_type': 'ws_rate_limit',
                'user_id': user_id,
                'endpoint': endpoint,
                'limit': limit,
            }
        )
        return {
            'type': 'error',
            'code': 'RATE_LIMITED',
            'message': f'Rate limit exceeded: {limit}',
        }
    
    @staticmethod
    def handle_malformed_message(user_id, message_type, error):
        """
        Handle malformed WebSocket message.
        
        Args:
            user_id: User ID who sent the message
            message_type: Type of message that was malformed
            error: Error details
        """
        logger.warning(
            f"Malformed WebSocket message: type={message_type}, error={error}",
            extra={
                'event_type': 'ws_malformed_message',
                'user_id': user_id,
                'message_type': message_type,
                'error': str(error),
            }
        )
        return {
            'type': 'error',
            'code': 'MALFORMED_MESSAGE',
            'message': 'Invalid message format',
            'details': {
                'message_type': message_type,
                'error': str(error),
            }
        }
    
    @staticmethod
    def handle_disconnect(user_id, close_code, reason=None):
        """
        Handle WebSocket disconnect.
        
        Args:
            user_id: User ID being disconnected
            close_code: WebSocket close code
            reason: Optional disconnect reason
        """
        log_level = logging.INFO if close_code in [1000, 1001] else logging.WARNING
        logger.log(
            log_level,
            f"WebSocket disconnect: user={user_id}, code={close_code}, reason={reason}",
            extra={
                'event_type': 'ws_disconnect',
                'user_id': user_id,
                'close_code': close_code,
                'reason': reason,
            }
        )
    
    @staticmethod
    def handle_permission_denied(user_id, action, resource_id=None):
        """
        Handle WebSocket permission denied.
        
        Args:
            user_id: User ID being denied
            action: Action that was denied
            resource_id: Optional resource ID
        """
        logger.warning(
            f"WebSocket permission denied: user={user_id}, action={action}",
            extra={
                'event_type': 'ws_permission_denied',
                'user_id': user_id,
                'action': action,
                'resource_id': resource_id,
            }
        )
        return {
            'type': 'error',
            'code': 'PERMISSION_DENIED',
            'message': f'Permission denied for action: {action}',
        }
