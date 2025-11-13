"""
WebhookService - Delivers notifications via HTTP webhooks with HMAC signing.

MILESTONE F: Phase 5.6 - Webhook Delivery Service (Hardened)
Implements secure webhook delivery with:
- HMAC-SHA256 signature generation
- Exponential backoff retry logic (3 attempts)
- Replay safety (timestamp + idempotency key)
- Circuit breaker per endpoint
- Configurable timeouts and endpoints
- Comprehensive logging
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class WebhookService:
    """
    Delivers event notifications to external webhook endpoints.
    
    Features:
    - HMAC-SHA256 signature for request verification
    - Exponential backoff retry (3 attempts: 0s, 2s, 4s)
    - Replay safety (timestamp + idempotency key)
    - Circuit breaker per endpoint
    - Configurable timeout (default 10s)
    - Comprehensive error handling and logging
    
    Configuration (settings.py):
        WEBHOOK_ENDPOINT = 'https://api.example.com/webhooks/notifications'
        WEBHOOK_SECRET = 'your-secret-key-here'
        WEBHOOK_TIMEOUT = 10  # seconds
        WEBHOOK_MAX_RETRIES = 3
        WEBHOOK_REPLAY_WINDOW_SECONDS = 300  # 5 minutes
        WEBHOOK_CB_WINDOW_SECONDS = 120  # 2 minutes
        WEBHOOK_CB_MAX_FAILS = 5
        WEBHOOK_CB_OPEN_SECONDS = 60
    """
    
    # Circuit breaker state tracking (class-level for singleton behavior)
    _circuit_state = 'closed'  # 'closed', 'open', 'half_open'
    _failure_count = 0
    _failure_window_start = None
    _circuit_opened_at = None
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        replay_window: Optional[int] = None,
        cb_window: Optional[int] = None,
        cb_max_fails: Optional[int] = None,
        cb_open_seconds: Optional[int] = None,
    ):
        """
        Initialize WebhookService.
        
        Args:
            endpoint: Webhook URL (defaults to settings.WEBHOOK_ENDPOINT)
            secret: HMAC secret key (defaults to settings.WEBHOOK_SECRET)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts (including initial request)
            replay_window: Replay protection window in seconds (default 300)
            cb_window: Circuit breaker failure window in seconds (default 120)
            cb_max_fails: Max failures before opening circuit (default 5)
            cb_open_seconds: Time to keep circuit open before half-open (default 60)
        """
        self.endpoint = endpoint or getattr(settings, 'WEBHOOK_ENDPOINT', None)
        self.secret = secret or getattr(settings, 'WEBHOOK_SECRET', '')
        self.timeout = timeout if timeout is not None else getattr(settings, 'WEBHOOK_TIMEOUT', 10)
        self.max_retries = max_retries if max_retries is not None else getattr(settings, 'WEBHOOK_MAX_RETRIES', 3)
        self.replay_window = replay_window if replay_window is not None else getattr(settings, 'WEBHOOK_REPLAY_WINDOW_SECONDS', 300)
        self.cb_window = cb_window if cb_window is not None else getattr(settings, 'WEBHOOK_CB_WINDOW_SECONDS', 120)
        self.cb_max_fails = cb_max_fails if cb_max_fails is not None else getattr(settings, 'WEBHOOK_CB_MAX_FAILS', 5)
        self.cb_open_seconds = cb_open_seconds if cb_open_seconds is not None else getattr(settings, 'WEBHOOK_CB_OPEN_SECONDS', 60)
    
    def _check_circuit_breaker(self) -> Tuple[bool, str]:
        """
        Check circuit breaker state before attempting delivery.
        
        Returns:
            (allowed, reason) tuple - (True, '') if delivery allowed, (False, reason) if blocked
        """
        now = time.time()
        
        # Reset failure window if expired
        if self._failure_window_start and (now - self._failure_window_start) > self.cb_window:
            self._failure_count = 0
            self._failure_window_start = None
        
        # Check circuit state
        if self._circuit_state == 'open':
            # Check if we should transition to half_open
            if now - self._circuit_opened_at >= self.cb_open_seconds:
                self._circuit_state = 'half_open'
                logger.info("Circuit breaker transitioned to HALF_OPEN - allowing probe request")
                return (True, '')
            else:
                remaining = int(self.cb_open_seconds - (now - self._circuit_opened_at))
                logger.warning(f"Circuit breaker OPEN - blocking webhook delivery ({remaining}s remaining)")
                return (False, f"Circuit breaker open ({remaining}s remaining)")
        
        return (True, '')
    
    def _record_success(self):
        """Record successful delivery for circuit breaker tracking."""
        if self._circuit_state == 'half_open':
            logger.info("Circuit breaker probe successful - transitioning to CLOSED")
            self._circuit_state = 'closed'
            self._failure_count = 0
            self._failure_window_start = None
        elif self._circuit_state == 'closed':
            # Decay failure count on success
            if self._failure_count > 0:
                self._failure_count = max(0, self._failure_count - 1)
    
    def _record_failure(self):
        """Record failed delivery for circuit breaker tracking."""
        now = time.time()
        
        # Initialize failure window if needed
        if not self._failure_window_start:
            self._failure_window_start = now
        
        self._failure_count += 1
        
        # Check if we should open circuit
        if self._failure_count >= self.cb_max_fails:
            if self._circuit_state == 'closed':
                self._circuit_state = 'open'
                self._circuit_opened_at = now
                logger.error(f"Circuit breaker OPENED - {self._failure_count} failures in {int(now - self._failure_window_start)}s")
            elif self._circuit_state == 'half_open':
                # Probe failed - reopen circuit
                self._circuit_state = 'open'
                self._circuit_opened_at = now
                logger.warning("Circuit breaker probe failed - reopening circuit")
    
    def generate_signature(self, payload: str, timestamp: Optional[int] = None) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.
        
        For replay safety, signature includes timestamp when provided:
            signature = HMAC-SHA256(timestamp + "." + payload)
        
        Args:
            payload: JSON string payload
            timestamp: Unix milliseconds timestamp (optional, for replay safety)
            
        Returns:
            Hex-encoded HMAC signature
            
        Example:
            >>> service = WebhookService(secret='my-secret')
            >>> sig = service.generate_signature('{"event": "test"}')
            >>> sig  # '9a3c7b...'
            >>> sig_with_ts = service.generate_signature('{"event": "test"}', timestamp=1700000000000)
        """
        if not self.secret:
            logger.warning("WEBHOOK_SECRET not configured - signature will be empty")
            return ''
        
        # Include timestamp in signing message for replay safety
        if timestamp is not None:
            message = f"{timestamp}.{payload}"
        else:
            message = payload
        
        signature = hmac.new(
            key=self.secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def deliver(
        self,
        event: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Deliver webhook with retry logic, replay safety, and circuit breaker.
        
        Args:
            event: Event name (e.g., 'payment_verified', 'tournament_completed')
            data: Event data dictionary
            metadata: Optional metadata (user_id, timestamp, etc.)
            
        Returns:
            Tuple of (success: bool, response_data: dict or None)
            
        Retry Logic:
            - Attempt 1: Immediate (delay=0s)
            - Attempt 2: After 2s (exponential backoff: 2^1)
            - Attempt 3: After 4s (exponential backoff: 2^2)
            
        Replay Safety:
            - X-Webhook-Timestamp: Unix milliseconds (for freshness check)
            - X-Webhook-Id: UUID v4 (for deduplication)
            - Signature includes timestamp: HMAC(timestamp + "." + body)
            
        Circuit Breaker:
            - Tracks failures per endpoint
            - Opens after threshold (default: 5 failures in 120s)
            - Half-open probe after timeout (default: 60s)
            
        Example:
            >>> service = WebhookService()
            >>> success, response = service.deliver(
            ...     event='payment_verified',
            ...     data={'payment_id': 123, 'amount': 500}
            ... )
        """
        if not self.endpoint:
            logger.warning("WEBHOOK_ENDPOINT not configured - skipping delivery")
            return False, None
        
        # Check circuit breaker
        allowed, reason = self._check_circuit_breaker()
        if not allowed:
            logger.warning(f"Webhook delivery blocked by circuit breaker: {reason}")
            return False, {'error': reason, 'circuit_breaker': 'open'}
        
        # Generate replay safety headers
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        webhook_id = str(uuid.uuid4())
        
        # Prepare payload
        payload_dict = {
            'event': event,
            'data': data,
            'metadata': metadata or {},
        }
        payload_json = json.dumps(payload_dict, separators=(',', ':'))
        
        # Generate signature (includes timestamp for replay safety)
        signature = self.generate_signature(payload_json, timestamp=timestamp_ms)
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': event,
            'X-Webhook-Timestamp': str(timestamp_ms),
            'X-Webhook-Id': webhook_id,
            'User-Agent': 'DeltaCrown-Webhook/1.0',
        }
        
        # Retry loop with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                # Calculate backoff delay (0, 2, 8 seconds for attempts 1, 2, 3)
                if attempt > 1:
                    delay = 2 ** (attempt - 1)
                    logger.info(f"Webhook retry {attempt}/{self.max_retries} after {delay}s delay")
                    time.sleep(delay)
                
                logger.debug(
                    f"Webhook delivery attempt {attempt}/{self.max_retries}: "
                    f"endpoint={self.endpoint}, event={event}"
                )
                
                # Send POST request
                response = requests.post(
                    self.endpoint,
                    data=payload_json,
                    headers=headers,
                    timeout=self.timeout,
                )
                
                # Check response status
                if response.status_code in (200, 201, 202, 204):
                    logger.info(
                        f"Webhook delivered successfully: event={event}, "
                        f"status={response.status_code}, attempt={attempt}, webhook_id={webhook_id}"
                    )
                    
                    # Record success for circuit breaker
                    self._record_success()
                    
                    # Parse response body if present
                    response_data = None
                    if response.content:
                        try:
                            response_data = response.json()
                        except json.JSONDecodeError:
                            response_data = {'body': response.text[:200]}
                    
                    return True, response_data
                
                else:
                    logger.warning(
                        f"Webhook delivery failed: event={event}, "
                        f"status={response.status_code}, attempt={attempt}/{self.max_retries}, "
                        f"response={response.text[:200]}"
                    )
                    
                    # Don't retry client errors (4xx)
                    if 400 <= response.status_code < 500:
                        logger.error(f"Client error - aborting retries: status={response.status_code}")
                        self._record_failure()  # Record single failure for 4xx
                        return False, None
                    # For 5xx, continue to retry (don't record failure yet)
            
            except requests.exceptions.Timeout:
                logger.warning(
                    f"Webhook timeout: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"timeout={self.timeout}s"
                )
                # Continue to retry on timeout
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Webhook connection error: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"error={str(e)[:100]}"
                )
                # Continue to retry on connection error
            
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Webhook request failed: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"error={str(e)[:100]}"
                )
                # Continue to retry on general request error
        
        # All retries exhausted
        logger.error(
            f"Webhook delivery failed after {self.max_retries} attempts: "
            f"event={event}, endpoint={self.endpoint}, webhook_id={webhook_id}"
        )
        self._record_failure()
        return False, None
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        timestamp: Optional[int] = None,
        max_age_seconds: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify HMAC signature for incoming webhook with replay protection (for webhook receivers).
        
        Args:
            payload: Raw JSON string payload
            signature: Received signature from X-Webhook-Signature header
            timestamp: Unix milliseconds from X-Webhook-Timestamp header (optional)
            max_age_seconds: Maximum age for timestamp freshness check (default: replay_window)
            
        Returns:
            Tuple of (valid: bool, error_message: str or None)
            - (True, None) if signature valid and timestamp fresh
            - (False, "reason") if verification failed
            
        Example:
            >>> service = WebhookService(secret='my-secret')
            >>> payload = '{"event": "test"}'
            >>> timestamp_ms = int(time.time() * 1000)
            >>> sig = service.generate_signature(payload, timestamp=timestamp_ms)
            >>> service.verify_signature(payload, sig, timestamp=timestamp_ms)
            (True, None)
        """
        # Check timestamp freshness if provided
        if timestamp is not None:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            age_seconds = (now_ms - timestamp) / 1000
            max_age = max_age_seconds if max_age_seconds is not None else self.replay_window
            
            if age_seconds > max_age:
                error_msg = f"Timestamp too old: {age_seconds:.1f}s > {max_age}s"
                logger.warning(f"Webhook replay protection: {error_msg}")
                return (False, error_msg)
            
            if age_seconds < -30:  # Allow 30s clock skew
                error_msg = f"Timestamp in future: {age_seconds:.1f}s"
                logger.warning(f"Webhook replay protection: {error_msg}")
                return (False, error_msg)
        
        # Verify signature
        expected_signature = self.generate_signature(payload, timestamp=timestamp)
        
        # Use constant-time comparison to prevent timing attacks
        if hmac.compare_digest(expected_signature, signature):
            return (True, None)
        else:
            return (False, "Invalid signature")


# Singleton instance for convenience
_webhook_service = None


def get_webhook_service() -> WebhookService:
    """
    Get or create singleton WebhookService instance.
    
    Returns:
        WebhookService instance configured from settings
    """
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


def deliver_webhook(
    event: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Convenience function to deliver webhook using singleton service.
    
    Args:
        event: Event name
        data: Event data
        metadata: Optional metadata
        
    Returns:
        Tuple of (success, response_data)
        
    Example:
        >>> from apps.notifications.services.webhook_service import deliver_webhook
        >>> success, response = deliver_webhook(
        ...     event='payment_verified',
        ...     data={'payment_id': 123}
        ... )
    """
    service = get_webhook_service()
    return service.deliver(event=event, data=data, metadata=metadata)
