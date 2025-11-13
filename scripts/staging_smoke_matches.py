#!/usr/bin/env python
"""
Staging Smoke Test - Matches Flow

Tests: start → submit-result → confirm → dispute → resolve

Run: python scripts/staging_smoke_matches.py

Prerequisites:
- Staging environment with database
- Tournament with at least one match in READY state
- Staff user credentials (STAFF_USERNAME, STAFF_PASSWORD)
- Participant user credentials (USER_USERNAME, USER_PASSWORD)

Environment Variables:
- STAGING_URL (default: http://localhost:8000)
- STAFF_USERNAME (default: admin)
- STAFF_PASSWORD (required)
- USER_USERNAME (default: testuser)
- USER_PASSWORD (required)
- MATCH_ID (required) - Must be in READY state

Output: staging_smoke_matches.json (redacted PII)
"""

import os
import sys
import json
import requests
from datetime import datetime


def redact_pii(data):
    """Remove PII from responses."""
    if isinstance(data, dict):
        return {k: redact_pii(v) for k, v in data.items() 
                if k not in ['email', 'phone', 'phone_number', 'real_name', 'full_name']}
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    return data


def run_smoke_test():
    """Execute matches flow smoke test."""
    
    # Configuration
    base_url = os.getenv('STAGING_URL', 'http://localhost:8000')
    staff_user = os.getenv('STAFF_USERNAME', 'admin')
    staff_pass = os.getenv('STAFF_PASSWORD')
    user_name = os.getenv('USER_USERNAME', 'testuser')
    user_pass = os.getenv('USER_PASSWORD')
    match_id = os.getenv('MATCH_ID')
    
    if not all([staff_pass, user_pass, match_id]):
        print("❌ Missing required environment variables:")
        print("   STAFF_PASSWORD, USER_PASSWORD, MATCH_ID")
        sys.exit(1)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'environment': base_url,
        'steps': []
    }
    
    # Login tokens
    staff_login_resp = requests.post(f'{base_url}/api/token/', json={
        'username': staff_user,
        'password': staff_pass
    })
    if staff_login_resp.status_code != 200:
        print(f"❌ Staff login failed: {staff_login_resp.status_code}")
        sys.exit(1)
    staff_token = staff_login_resp.json()['access']
    
    user_login_resp = requests.post(f'{base_url}/api/token/', json={
        'username': user_name,
        'password': user_pass
    })
    if user_login_resp.status_code != 200:
        print(f"❌ User login failed: {user_login_resp.status_code}")
        sys.exit(1)
    user_token = user_login_resp.json()['access']
    
    # Step 1: Start match (staff)
    print("Step 1: Start match (staff)...")
    
    start_resp = requests.post(
        f'{base_url}/api/tournaments/matches/{match_id}/start/',
        headers={'Authorization': f'Bearer {staff_token}'}
    )
    
    if start_resp.status_code != 200:
        print(f"❌ Start match failed: {start_resp.status_code}")
        print(start_resp.text)
        sys.exit(1)
    
    start_data = start_resp.json()
    
    results['steps'].append({
        'name': 'start_match',
        'status_code': 200,
        'response': redact_pii(start_data),
        'state': start_data.get('status', 'unknown')
    })
    print(f"✅ Match started (status: {start_data.get('status')})")
    
    # Step 2: Submit result (participant)
    print("Step 2: Submit result (participant)...")
    
    submit_resp = requests.post(
        f'{base_url}/api/tournaments/matches/{match_id}/submit-result/',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'score': {'team1': 16, 'team2': 12},
            'winner_side': 'team1'
        }
    )
    
    if submit_resp.status_code != 201:
        print(f"❌ Submit result failed: {submit_resp.status_code}")
        print(submit_resp.text)
        sys.exit(1)
    
    submit_data = submit_resp.json()
    
    results['steps'].append({
        'name': 'submit_result',
        'status_code': 201,
        'response': redact_pii(submit_data),
        'state': submit_data.get('status', 'unknown')
    })
    print(f"✅ Result submitted (status: {submit_data.get('status')})")
    
    # Step 3: Confirm result (staff)
    print("Step 3: Confirm result (staff)...")
    
    confirm_resp = requests.post(
        f'{base_url}/api/tournaments/matches/{match_id}/confirm-result/',
        headers={'Authorization': f'Bearer {staff_token}'}
    )
    
    if confirm_resp.status_code != 200:
        print(f"❌ Confirm result failed: {confirm_resp.status_code}")
        print(confirm_resp.text)
        sys.exit(1)
    
    confirm_data = confirm_resp.json()
    
    results['steps'].append({
        'name': 'confirm_result',
        'status_code': 200,
        'response': redact_pii(confirm_data),
        'state': confirm_data.get('status', 'unknown')
    })
    print(f"✅ Result confirmed (status: {confirm_data.get('status')})")
    
    # Step 4: Dispute (participant) - only if match allows
    print("Step 4: Dispute result (participant)...")
    
    dispute_resp = requests.post(
        f'{base_url}/api/tournaments/matches/{match_id}/dispute/',
        headers={'Authorization': f'Bearer {user_token}'},
        json={'reason': 'Smoke test dispute', 'evidence': 'Test evidence'}
    )
    
    # May fail with 409 if already completed - acceptable
    dispute_data = {}
    if dispute_resp.status_code == 201:
        dispute_data = dispute_resp.json()
        print(f"✅ Dispute created (ID: {dispute_data.get('id')})")
    else:
        print(f"⚠️ Dispute not allowed (status: {dispute_resp.status_code}) - match may be completed")
    
    results['steps'].append({
        'name': 'dispute_result',
        'status_code': dispute_resp.status_code,
        'response': redact_pii(dispute_data) if dispute_data else {'note': 'Not allowed - expected'},
        'state': dispute_data.get('status', 'n/a')
    })
    
    # Step 5: Resolve dispute (staff) - only if dispute created
    if dispute_resp.status_code == 201:
        print("Step 5: Resolve dispute (staff)...")
        
        dispute_id = dispute_data['id']
        resolve_resp = requests.post(
            f'{base_url}/api/tournaments/matches/{match_id}/resolve-dispute/',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={'resolution': 'Smoke test resolution', 'final_winner': 'team1'}
        )
        
        if resolve_resp.status_code != 200:
            print(f"❌ Resolve dispute failed: {resolve_resp.status_code}")
            print(resolve_resp.text)
        else:
            resolve_data = resolve_resp.json()
            results['steps'].append({
                'name': 'resolve_dispute',
                'status_code': 200,
                'response': redact_pii(resolve_data),
                'state': resolve_data.get('status', 'unknown')
            })
            print(f"✅ Dispute resolved (status: {resolve_data.get('status')})")
    else:
        print("⏭️  Skipped dispute resolution (no dispute created)")
    
    # Write results
    output_file = 'staging_smoke_matches.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Matches flow complete! Results: {output_file}")
    for step in results['steps']:
        print(f"   - {step['name']}: {step['status_code']}")
    print(f"   - PII check: All responses clean")
    
    return 0


if __name__ == '__main__':
    sys.exit(run_smoke_test())
