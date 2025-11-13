#!/usr/bin/env python3
"""
Webhook HMAC-SHA256 Signature Verification Tool

This script demonstrates how to verify webhook signatures sent by DeltaCrown.
It can be used by webhook receivers to validate incoming requests.

Usage:
    python verify_webhook_signature.py

Features:
    - Generate HMAC-SHA256 signatures for test payloads
    - Verify received signatures against expected values
    - Constant-time comparison (timing-attack resistant)
    - Example payloads for all notification events
"""

import hmac
import hashlib
import json
from typing import Dict, Any, Tuple


class WebhookVerifier:
    """Utility class for webhook signature verification."""
    
    def __init__(self, secret: str):
        """
        Initialize verifier with webhook secret.
        
        Args:
            secret: Shared secret key (same as WEBHOOK_SECRET in DeltaCrown settings)
        """
        self.secret = secret.encode('utf-8')
    
    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for a payload.
        
        Args:
            payload: Dictionary payload to sign
            
        Returns:
            64-character hexadecimal signature string
        """
        # Serialize to JSON (compact, no spaces)
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        
        # Calculate HMAC-SHA256
        signature = hmac.new(
            self.secret,
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_signature(self, payload: Dict[str, Any], received_signature: str) -> bool:
        """
        Verify a received signature matches the expected value.
        
        Args:
            payload: Dictionary payload to verify
            received_signature: Signature received in X-Webhook-Signature header
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = self.generate_signature(payload)
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, received_signature)
    
    def verify_request(self, body: bytes, received_signature: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a complete webhook request (body + signature).
        
        Args:
            body: Raw request body bytes
            received_signature: Signature from X-Webhook-Signature header
            
        Returns:
            Tuple of (is_valid, parsed_payload)
        """
        try:
            # Parse JSON payload
            payload = json.loads(body.decode('utf-8'))
            
            # Verify signature
            is_valid = self.verify_signature(payload, received_signature)
            
            return is_valid, payload
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"❌ Failed to parse payload: {e}")
            return False, {}


# Example notification payloads
EXAMPLE_PAYLOADS = {
    "payment_verified": {
        "event": "payment_verified",
        "data": {
            "event": "payment_verified",
            "title": "Payment Verified",
            "body": "Your payment for 'Summer Championship 2025' has been verified.",
            "url": "/tournaments/123/payment/",
            "recipient_count": 1,
            "tournament_id": 123,
            "match_id": None
        },
        "metadata": {
            "created": 1,
            "skipped": 0,
            "email_sent": 1
        }
    },
    "match_scheduled": {
        "event": "match_scheduled",
        "data": {
            "event": "match_scheduled",
            "title": "Match Scheduled",
            "body": "Your match in 'Summer Championship 2025' is scheduled for Nov 15, 2025 at 18:00 UTC.",
            "url": "/tournaments/123/matches/456/",
            "recipient_count": 10,
            "tournament_id": 123,
            "match_id": 456
        },
        "metadata": {
            "created": 10,
            "skipped": 0,
            "email_sent": 10
        }
    },
    "tournament_starting": {
        "event": "tournament_starting",
        "data": {
            "event": "tournament_starting",
            "title": "Tournament Starting Soon",
            "body": "'Summer Championship 2025' begins in 1 hour. Good luck!",
            "url": "/tournaments/123/",
            "recipient_count": 50,
            "tournament_id": 123,
            "match_id": None
        },
        "metadata": {
            "created": 50,
            "skipped": 0,
            "email_sent": 50
        }
    }
}


def main():
    """Run interactive webhook verification demo."""
    print("=" * 70)
    print("DeltaCrown Webhook Signature Verification Tool")
    print("=" * 70)
    print()
    
    # Configuration
    SECRET = "test-webhook-secret-key-2025"
    verifier = WebhookVerifier(SECRET)
    
    print(f"🔑 Secret Key: {SECRET}")
    print()
    
    # Test each example payload
    for event_name, payload in EXAMPLE_PAYLOADS.items():
        print("-" * 70)
        print(f"📤 Event: {event_name}")
        print("-" * 70)
        
        # Generate signature
        signature = verifier.generate_signature(payload)
        
        # Show payload
        print(f"\n📦 Payload:")
        print(json.dumps(payload, indent=2))
        
        # Show signature
        print(f"\n🔏 Generated Signature:")
        print(f"X-Webhook-Signature: {signature}")
        
        # Verify signature
        is_valid = verifier.verify_signature(payload, signature)
        print(f"\n✓ Verification: {'✅ VALID' if is_valid else '❌ INVALID'}")
        
        # Test with tampered payload
        tampered_payload = payload.copy()
        tampered_payload["data"]["title"] = "TAMPERED"
        is_tampered_valid = verifier.verify_signature(tampered_payload, signature)
        print(f"✓ Tampered Payload: {'❌ REJECTED' if not is_tampered_valid else '⚠️ ACCEPTED (BUG!)'}")
        
        print()
    
    # Full request verification example
    print("=" * 70)
    print("Complete Request Verification Example")
    print("=" * 70)
    print()
    
    example_payload = EXAMPLE_PAYLOADS["payment_verified"]
    example_body = json.dumps(example_payload, separators=(',', ':')).encode('utf-8')
    example_signature = verifier.generate_signature(example_payload)
    
    print("📥 Simulating incoming webhook request:")
    print()
    print("POST /webhooks/deltacrown HTTP/1.1")
    print("Host: your-server.com")
    print("Content-Type: application/json")
    print(f"X-Webhook-Signature: {example_signature}")
    print("X-Webhook-Event: payment_verified")
    print("User-Agent: DeltaCrown-Webhook/1.0")
    print()
    print(f"Body: {example_body.decode('utf-8')}")
    print()
    
    # Verify request
    is_valid, parsed_payload = verifier.verify_request(example_body, example_signature)
    
    if is_valid:
        print("✅ Signature verified successfully!")
        print(f"✅ Event: {parsed_payload.get('event')}")
        print(f"✅ Recipients: {parsed_payload.get('data', {}).get('recipient_count')}")
        print()
        print("🎉 Request is authentic - process webhook")
    else:
        print("❌ Signature verification failed!")
        print("⚠️ Request may be forged or tampered - reject webhook")
    
    print()
    print("=" * 70)
    print("Integration Example (Python Flask)")
    print("=" * 70)
    print()
    print("""
from flask import Flask, request, jsonify
from verify_webhook_signature import WebhookVerifier

app = Flask(__name__)
verifier = WebhookVerifier(secret="your-webhook-secret")

@app.route('/webhooks/deltacrown', methods=['POST'])
def handle_webhook():
    # Get signature from header
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 401
    
    # Verify signature
    is_valid, payload = verifier.verify_request(request.data, signature)
    
    if not is_valid:
        return jsonify({'error': 'Invalid signature'}), 403
    
    # Process webhook
    event = payload.get('event')
    data = payload.get('data', {})
    
    print(f"Received {event}: {data.get('title')}")
    
    # Your business logic here...
    
    return jsonify({'status': 'accepted'}), 202
""")
    
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
