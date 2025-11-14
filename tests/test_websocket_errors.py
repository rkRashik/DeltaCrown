"""
Tests for WebSocket error handling (Module 9.5).
Tests WebSocket error events and handlers.
"""
import pytest
from apps.tournaments.realtime.error_events import WebSocketErrorHandler
from channels.exceptions import DenyConnection


class TestWebSocketErrorHandler:
    """Test WebSocket error handling."""
    
    def test_handle_auth_failure_raises_deny_connection(self):
        """Test auth failure raises DenyConnection."""
        with pytest.raises(DenyConnection):
            WebSocketErrorHandler.handle_auth_failure(user_id=123, reason="Invalid token")
    
    def test_handle_rate_limit_returns_error_message(self):
        """Test rate limit returns structured error."""
        result = WebSocketErrorHandler.handle_rate_limit(
            user_id=123,
            endpoint='/ws/tournaments/',
            limit='100/hour'
        )
        
        assert result['type'] == 'error'
        assert result['code'] == 'RATE_LIMITED'
        assert 'message' in result
        assert '100/hour' in result['message']
    
    def test_handle_malformed_message_returns_error(self):
        """Test malformed message returns structured error."""
        result = WebSocketErrorHandler.handle_malformed_message(
            user_id=123,
            message_type='join_tournament',
            error='Missing tournament_id field'
        )
        
        assert result['type'] == 'error'
        assert result['code'] == 'MALFORMED_MESSAGE'
        assert 'message' in result
        assert 'details' in result
        assert result['details']['message_type'] == 'join_tournament'
    
    def test_handle_disconnect_logs_normally(self):
        """Test disconnect with normal close code."""
        # Should not raise exception
        WebSocketErrorHandler.handle_disconnect(
            user_id=123,
            close_code=1000,
            reason='Normal closure'
        )
    
    def test_handle_disconnect_logs_abnormal(self):
        """Test disconnect with abnormal close code."""
        # Should not raise exception
        WebSocketErrorHandler.handle_disconnect(
            user_id=123,
            close_code=1006,
            reason='Abnormal closure'
        )
    
    def test_handle_permission_denied_returns_error(self):
        """Test permission denied returns structured error."""
        result = WebSocketErrorHandler.handle_permission_denied(
            user_id=123,
            action='join_tournament',
            resource_id=456
        )
        
        assert result['type'] == 'error'
        assert result['code'] == 'PERMISSION_DENIED'
        assert 'message' in result
        assert 'join_tournament' in result['message']
    
    def test_error_messages_have_consistent_structure(self):
        """Test all error messages have consistent structure."""
        # Rate limit error
        error1 = WebSocketErrorHandler.handle_rate_limit(123, '/ws/test/', '100/hour')
        assert 'type' in error1
        assert 'code' in error1
        assert 'message' in error1
        
        # Malformed message error
        error2 = WebSocketErrorHandler.handle_malformed_message(123, 'test', 'test error')
        assert 'type' in error2
        assert 'code' in error2
        assert 'message' in error2
        
        # Permission denied error
        error3 = WebSocketErrorHandler.handle_permission_denied(123, 'test_action')
        assert 'type' in error3
        assert 'code' in error3
        assert 'message' in error3
    
    def test_auth_failure_with_no_user_id(self):
        """Test auth failure without user ID."""
        with pytest.raises(DenyConnection) as exc_info:
            WebSocketErrorHandler.handle_auth_failure(reason="No user ID")
        
        assert "Authentication failed" in str(exc_info.value)
    
    def test_malformed_message_includes_error_details(self):
        """Test malformed message includes original error in details."""
        error_msg = "Invalid JSON format"
        result = WebSocketErrorHandler.handle_malformed_message(
            user_id=123,
            message_type='test',
            error=error_msg
        )
        
        assert result['details']['error'] == error_msg
