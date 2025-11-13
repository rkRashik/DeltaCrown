"""
WebhookService - Delivers notifications via HTTP webhooks with HMAC signing.

MILESTONE F: Phase 5 - Webhook Delivery Service
Implements secure webhook delivery with:
- HMAC-SHA256 signature generation
- Exponential backoff retry logic (3 attempts)
- Configurable timeouts and endpoints
- Comprehensive logging
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class WebhookService:
    """
    Delivers event notifications to external webhook endpoints.
    
    Features:
    - HMAC-SHA256 signature for request verification
    - Exponential backoff retry (3 attempts: 0s, 2s, 8s)
    - Configurable timeout (default 10s)
    - Comprehensive error handling and logging
    
    Configuration (settings.py):
        WEBHOOK_ENDPOINT = 'https://api.example.com/webhooks/notifications'
        WEBHOOK_SECRET = 'your-secret-key-here'
        WEBHOOK_TIMEOUT = 10  # seconds
        WEBHOOK_MAX_RETRIES = 3
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize WebhookService.
        
        Args:
            endpoint: Webhook URL (defaults to settings.WEBHOOK_ENDPOINT)
            secret: HMAC secret key (defaults to settings.WEBHOOK_SECRET)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts (including initial request)
        """
        self.endpoint = endpoint or getattr(settings, 'WEBHOOK_ENDPOINT', None)
        self.secret = secret or getattr(settings, 'WEBHOOK_SECRET', '')
        self.timeout = timeout if timeout is not None else getattr(settings, 'WEBHOOK_TIMEOUT', 10)
        self.max_retries = max_retries if max_retries is not None else getattr(settings, 'WEBHOOK_MAX_RETRIES', 3)
    
    def generate_signature(self, payload: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.
        
        Args:
            payload: JSON string payload
            
        Returns:
            Hex-encoded HMAC signature
            
        Example:
            >>> service = WebhookService(secret='my-secret')
            >>> sig = service.generate_signature('{"event": "test"}')
            >>> sig  # '9a3c7b...'
        """
        if not self.secret:
            logger.warning("WEBHOOK_SECRET not configured - signature will be empty")
            return ''
        
        signature = hmac.new(
            key=self.secret.encode('utf-8'),
            msg=payload.encode('utf-8'),
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
        Deliver webhook with retry logic.
        
        Args:
            event: Event name (e.g., 'payment_verified', 'tournament_completed')
            data: Event data dictionary
            metadata: Optional metadata (user_id, timestamp, etc.)
            
        Returns:
            Tuple of (success: bool, response_data: dict or None)
            
        Retry Logic:
            - Attempt 1: Immediate (delay=0s)
            - Attempt 2: After 2s (exponential backoff: 2^1)
            - Attempt 3: After 8s (exponential backoff: 2^3)
            
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
        
        # Prepare payload
        payload_dict = {
            'event': event,
            'data': data,
            'metadata': metadata or {},
        }
        payload_json = json.dumps(payload_dict, separators=(',', ':'))
        
        # Generate signature
        signature = self.generate_signature(payload_json)
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': event,
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
                        f"status={response.status_code}, attempt={attempt}"
                    )
                    
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
                        return False, None
            
            except requests.exceptions.Timeout:
                logger.warning(
                    f"Webhook timeout: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"timeout={self.timeout}s"
                )
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Webhook connection error: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"error={str(e)[:100]}"
                )
            
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Webhook request failed: event={event}, attempt={attempt}/{self.max_retries}, "
                    f"error={str(e)[:100]}"
                )
        
        # All retries exhausted
        logger.error(
            f"Webhook delivery failed after {self.max_retries} attempts: "
            f"event={event}, endpoint={self.endpoint}"
        )
        return False, None
    
    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        Verify HMAC signature for incoming webhook (for webhook receivers).
        
        Args:
            payload: Raw JSON string payload
            signature: Received signature from X-Webhook-Signature header
            
        Returns:
            True if signature is valid, False otherwise
            
        Example:
            >>> service = WebhookService(secret='my-secret')
            >>> payload = '{"event": "test"}'
            >>> sig = service.generate_signature(payload)
            >>> service.verify_signature(payload, sig)
            True
        """
        expected_signature = self.generate_signature(payload)
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)


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
