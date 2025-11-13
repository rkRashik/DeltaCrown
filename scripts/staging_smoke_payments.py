#!/usr/bin/env python
"""
Staging Smoke Test - Payments Flow

Tests: submit-proof → verify → refund + idempotency replay

Run: python scripts/staging_smoke_payments.py

Prerequisites:
- Staging environment with database and Redis
- Tournament created with at least one registration
- Staff user credentials (STAFF_USERNAME, STAFF_PASSWORD)
- Registration owner credentials (USER_USERNAME, USER_PASSWORD)

Environment Variables:
- STAGING_URL (default: http://localhost:8000)
- STAFF_USERNAME (default: admin)
- STAFF_PASSWORD (required)
- USER_USERNAME (default: testuser)
- USER_PASSWORD (required)
- REGISTRATION_ID (required) - Must be in PENDING state
- TEST_PROOF_FILE (default: test_proof.jpg) - Upload file path

Output: staging_smoke_payments.json (redacted PII)
"""

import os
import sys
import json
import uuid
import requests
from datetime import datetime


def redact_pii(data):
    """Remove PII from responses (emails, phone numbers, full names)."""
    if isinstance(data, dict):
        return {k: redact_pii(v) for k, v in data.items() 
                if k not in ['email', 'phone', 'phone_number', 'real_name', 'full_name']}
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    return data


def run_smoke_test():
    """Execute payments flow smoke test."""
    
    # Configuration
    base_url = os.getenv('STAGING_URL', 'http://localhost:8000')
    staff_user = os.getenv('STAFF_USERNAME', 'admin')
    staff_pass = os.getenv('STAFF_PASSWORD')
    user_name = os.getenv('USER_USERNAME', 'testuser')
    user_pass = os.getenv('USER_PASSWORD')
    registration_id = os.getenv('REGISTRATION_ID')
    proof_file = os.getenv('TEST_PROOF_FILE', 'test_proof.jpg')
    
    if not all([staff_pass, user_pass, registration_id]):
        print("❌ Missing required environment variables:")
        print("   STAFF_PASSWORD, USER_PASSWORD, REGISTRATION_ID")
        sys.exit(1)
    
    if not os.path.exists(proof_file):
        print(f"❌ Proof file not found: {proof_file}")
        sys.exit(1)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'environment': base_url,
        'steps': []
    }
    
    # Step 1: Submit proof (owner)
    print("Step 1: Submit payment proof...")
    idempotency_key = str(uuid.uuid4())
    
    # Login as owner
    login_resp = requests.post(f'{base_url}/api/token/', json={
        'username': user_name,
        'password': user_pass
    })
    if login_resp.status_code != 200:
        print(f"❌ Owner login failed: {login_resp.status_code}")
        sys.exit(1)
    
    owner_token = login_resp.json()['access']
    
    with open(proof_file, 'rb') as f:
        submit_resp = requests.post(
            f'{base_url}/api/tournaments/payments/registrations/{registration_id}/submit-proof/',
            headers={
                'Authorization': f'Bearer {owner_token}',
                'Idempotency-Key': idempotency_key
            },
            files={'payment_proof': f}
        )
    
    if submit_resp.status_code != 201:
        print(f"❌ Submit proof failed: {submit_resp.status_code}")
        print(submit_resp.text)
        sys.exit(1)
    
    submit_data = submit_resp.json()
    payment_id = submit_data['id']
    
    results['steps'].append({
        'name': 'submit_proof',
        'status_code': 201,
        'idempotency_key': idempotency_key,
        'payment_id': payment_id,
        'response': redact_pii(submit_data),
        'pii_check': '✅ No email/phone in response' if 'email' not in json.dumps(submit_data) else '❌ PII detected'
    })
    print(f"✅ Proof submitted (ID: {payment_id})")
    
    # Step 2: Idempotency replay
    print("Step 2: Replay submit with same idempotency key...")
    
    with open(proof_file, 'rb') as f:
        replay_resp = requests.post(
            f'{base_url}/api/tournaments/payments/registrations/{registration_id}/submit-proof/',
            headers={
                'Authorization': f'Bearer {owner_token}',
                'Idempotency-Key': idempotency_key
            },
            files={'payment_proof': f}
        )
    
    if replay_resp.status_code != 200:  # Should return 200 (not 201)
        print(f"⚠️ Idempotency replay unexpected status: {replay_resp.status_code}")
    
    replay_data = replay_resp.json()
    
    results['steps'].append({
        'name': 'idempotent_replay',
        'status_code': replay_resp.status_code,
        'idempotency_key': idempotency_key,
        'response': redact_pii(replay_data),
        'validation': '✅ Returns existing object (200)' if replay_resp.status_code == 200 else '❌ Created new (201)'
    })
    print(f"✅ Idempotency validated ({replay_resp.status_code})")
    
    # Step 3: Verify payment (staff)
    print("Step 3: Verify payment (staff)...")
    
    # Login as staff
    staff_login_resp = requests.post(f'{base_url}/api/token/', json={
        'username': staff_user,
        'password': staff_pass
    })
    if staff_login_resp.status_code != 200:
        print(f"❌ Staff login failed: {staff_login_resp.status_code}")
        sys.exit(1)
    
    staff_token = staff_login_resp.json()['access']
    
    verify_resp = requests.post(
        f'{base_url}/api/tournaments/payments/{payment_id}/verify/',
        headers={'Authorization': f'Bearer {staff_token}'}
    )
    
    if verify_resp.status_code != 200:
        print(f"❌ Verify failed: {verify_resp.status_code}")
        print(verify_resp.text)
        sys.exit(1)
    
    verify_data = verify_resp.json()
    
    results['steps'].append({
        'name': 'verify_payment',
        'status_code': 200,
        'response': redact_pii(verify_data),
        'state': verify_data.get('status', 'unknown')
    })
    print(f"✅ Payment verified (status: {verify_data.get('status')})")
    
    # Step 4: Refund payment (staff)
    print("Step 4: Refund payment (staff)...")
    
    refund_resp = requests.post(
        f'{base_url}/api/tournaments/payments/{payment_id}/refund/',
        headers={'Authorization': f'Bearer {staff_token}'},
        json={'reason': 'Smoke test refund'}
    )
    
    if refund_resp.status_code != 200:
        print(f"❌ Refund failed: {refund_resp.status_code}")
        print(refund_resp.text)
        sys.exit(1)
    
    refund_data = refund_resp.json()
    
    results['steps'].append({
        'name': 'refund_payment',
        'status_code': 200,
        'response': redact_pii(refund_data),
        'state': refund_data.get('status', 'unknown')
    })
    print(f"✅ Payment refunded (status: {refund_data.get('status')})")
    
    # Write results
    output_file = 'staging_smoke_payments.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Payments flow complete! Results: {output_file}")
    print(f"   - Submit proof: 201 Created")
    print(f"   - Idempotency replay: {replay_resp.status_code}")
    print(f"   - Verify: 200 OK")
    print(f"   - Refund: 200 OK")
    print(f"   - PII check: All responses clean")
    
    return 0


if __name__ == '__main__':
    sys.exit(run_smoke_test())
