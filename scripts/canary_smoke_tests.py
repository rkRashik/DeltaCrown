#!/usr/bin/env python3
"""
Canary Smoke Tests — Phase 5.6 Webhooks
Run immediately after enabling 5% canary flag

Tests 4 critical scenarios:
1. Success path (200 OK)
2. Retry path (503 → 0s/2s/4s)
3. No-retry path (400)
4. Circuit breaker trigger (5 failures → OPEN)
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import PaymentVerification, Tournament
from apps.players.models import Match
from django.contrib.auth import get_user_model

User = get_user_model()

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_step(num, text):
    print(f"{YELLOW}[Step {num}]{RESET} {text}")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"   {text}")

def get_or_create_test_user():
    """Get or create canary test user"""
    user, created = User.objects.get_or_create(
        username='canary_test_user',
        defaults={
            'email': 'canary@test.internal',
            'first_name': 'Canary',
            'last_name': 'Test'
        }
    )
    if created:
        user.set_password('test123canary')
        user.save()
        print_info(f"Created test user: {user.username} (ID: {user.id})")
    else:
        print_info(f"Using existing test user: {user.username} (ID: {user.id})")
    return user

def test_1_success_path():
    """Test 1: Success path (200 OK)"""
    print_header("TEST 1: Success Path (200 OK)")
    
    print_step(1, "Creating test payment verification")
    
    user = get_or_create_test_user()
    tournament = Tournament.objects.filter(status='open').first()
    
    if not tournament:
        print_error("No open tournaments found. Creating one...")
        from apps.core.models import Game
        game = Game.objects.first()
        tournament = Tournament.objects.create(
            title='Canary Test Tournament',
            game=game,
            status='open',
            max_teams=16
        )
        print_success(f"Created tournament: {tournament.title} (ID: {tournament.id})")
    else:
        print_info(f"Using tournament: {tournament.title} (ID: {tournament.id})")
    
    # Create pending payment
    pv = PaymentVerification.objects.create(
        user=user,
        tournament=tournament,
        amount=50.00,
        status='pending'
    )
    print_success(f"Created payment verification (ID: {pv.id})")
    
    print_step(2, "Triggering webhook via status change (pending → verified)")
    pv.status = 'verified'
    pv.save()
    print_success("Status updated to 'verified' — webhook should fire")
    
    print_step(3, "Expected behavior")
    print_info("✅ Webhook delivery attempt logged")
    print_info("✅ HMAC signature generated")
    print_info("✅ Headers: X-Webhook-Signature, X-Webhook-Timestamp, X-Webhook-Id, X-Webhook-Event")
    print_info("✅ Status code: 200/201/202/204")
    print_info("✅ Latency logged (P95 should be <2s)")
    
    print_step(4, "Check logs")
    print_info("grep 'Webhook delivered successfully' /var/log/deltacrown-prod.log | tail -1")
    print_info("Expected: [INFO] Webhook delivered successfully: event=payment_verified, status=200")
    
    print(f"\n{GREEN}{'─'*70}{RESET}")
    print(f"{GREEN}Test 1 Setup Complete — Check receiver logs for 200 OK{RESET}")
    print(f"{GREEN}{'─'*70}{RESET}\n")

def test_2_retry_path():
    """Test 2: Retry path (503 → 0s/2s/4s)"""
    print_header("TEST 2: Retry Path (503 Service Unavailable)")
    
    print(f"{YELLOW}⚠️  NOTE: This test requires receiver to return 503 on first 2 attempts{RESET}\n")
    
    print_step(1, "Receiver setup instructions")
    print_info("Configure your receiver to:")
    print_info("  - Return 503 on attempt 1 (immediate retry)")
    print_info("  - Return 503 on attempt 2 (2s retry)")
    print_info("  - Return 200 on attempt 3 (success)")
    print_info("")
    print_info("Example (Flask):")
    print_info("  attempt_count[webhook_id] += 1")
    print_info("  if attempt_count[webhook_id] <= 2:")
    print_info("      return jsonify({'error': 'Service unavailable'}), 503")
    print_info("  return jsonify({'status': 'accepted'}), 200")
    
    print_step(2, "Triggering webhook")
    user = get_or_create_test_user()
    tournament = Tournament.objects.filter(status='open').first()
    
    pv = PaymentVerification.objects.create(
        user=user,
        tournament=tournament,
        amount=75.00,
        status='pending'
    )
    print_success(f"Created payment verification (ID: {pv.id})")
    
    pv.status = 'verified'
    pv.save()
    print_success("Status updated — webhook with retry should fire")
    
    print_step(3, "Expected behavior")
    print_info("✅ Attempt 1: Immediate (0s delay) → 503")
    print_info("✅ Attempt 2: After 2s delay → 503")
    print_info("✅ Attempt 3: After 4s delay → 200")
    print_info("✅ Total time: ~6 seconds (0 + 2 + 4)")
    
    print_step(4, "Check logs for retry sequence")
    print_info("grep 'payment_verified' /var/log/deltacrown-prod.log | tail -5")
    print_info("")
    print_info("Expected:")
    print_info("  [INFO] Attempting webhook delivery (attempt 1/3)")
    print_info("  [WARN] Webhook delivery failed (attempt 1/3): status=503, retrying in 0s")
    print_info("  [INFO] Attempting webhook delivery (attempt 2/3)")
    print_info("  [WARN] Webhook delivery failed (attempt 2/3): status=503, retrying in 2s")
    print_info("  [INFO] Attempting webhook delivery (attempt 3/3)")
    print_info("  [INFO] Webhook delivered successfully: status=200, total_time=6.2s")
    
    print(f"\n{GREEN}{'─'*70}{RESET}")
    print(f"{GREEN}Test 2 Setup Complete — Check logs for exponential backoff{RESET}")
    print(f"{GREEN}{'─'*70}{RESET}\n")

def test_3_no_retry_path():
    """Test 3: No-retry path (400 Bad Request)"""
    print_header("TEST 3: No-Retry Path (400 Bad Request)")
    
    print(f"{YELLOW}⚠️  NOTE: This test requires receiver to return 400{RESET}\n")
    
    print_step(1, "Receiver setup instructions")
    print_info("Configure your receiver to:")
    print_info("  - Return 400 (e.g., simulate invalid signature)")
    print_info("")
    print_info("Example (Flask):")
    print_info("  return jsonify({'error': 'Invalid signature'}), 400")
    
    print_step(2, "Triggering webhook")
    user = get_or_create_test_user()
    tournament = Tournament.objects.filter(status='open').first()
    
    pv = PaymentVerification.objects.create(
        user=user,
        tournament=tournament,
        amount=100.00,
        status='pending'
    )
    print_success(f"Created payment verification (ID: {pv.id})")
    
    pv.status = 'verified'
    pv.save()
    print_success("Status updated — webhook should fire (NO RETRY)")
    
    print_step(3, "Expected behavior")
    print_info("✅ Attempt 1: Immediate → 400")
    print_info("✅ NO RETRY (4xx = client error, no point retrying)")
    print_info("✅ Notification continues (email sent despite webhook failure)")
    print_info("✅ Error isolated (doesn't break notification system)")
    
    print_step(4, "Check logs")
    print_info("grep 'payment_verified' /var/log/deltacrown-prod.log | tail -3")
    print_info("")
    print_info("Expected:")
    print_info("  [INFO] Attempting webhook delivery (attempt 1/3)")
    print_info("  [ERROR] Webhook delivery failed (attempt 1/3): status=400, client error")
    print_info("  [WARN] Webhook delivery aborted: event=payment_verified, reason=4xx_error")
    
    print(f"\n{GREEN}{'─'*70}{RESET}")
    print(f"{GREEN}Test 3 Setup Complete — Verify single attempt (no retry){RESET}")
    print(f"{GREEN}{'─'*70}{RESET}\n")

def test_4_circuit_breaker():
    """Test 4: Circuit breaker trigger (5 failures → OPEN)"""
    print_header("TEST 4: Circuit Breaker (5 Failures → OPEN)")
    
    print(f"{YELLOW}⚠️  NOTE: This test requires receiver to return 500 for all requests{RESET}\n")
    
    print_step(1, "Receiver setup instructions")
    print_info("Configure your receiver to:")
    print_info("  - Return 500 for all webhook attempts")
    print_info("")
    print_info("Example (Flask):")
    print_info("  return jsonify({'error': 'Internal server error'}), 500")
    
    print_step(2, "Triggering 5 consecutive webhooks")
    user = get_or_create_test_user()
    tournament = Tournament.objects.filter(status='open').first()
    
    payment_ids = []
    for i in range(1, 6):
        pv = PaymentVerification.objects.create(
            user=user,
            tournament=tournament,
            amount=50.00 + i,
            status='pending'
        )
        pv.status = 'verified'
        pv.save()
        payment_ids.append(pv.id)
        print_success(f"Webhook {i}/5 triggered (payment ID: {pv.id})")
    
    print_step(3, "Expected behavior")
    print_info("✅ Webhooks 1-5: Each tries 3 times, all fail (15 attempts total)")
    print_info("✅ After 5th failure: Circuit breaker OPENS")
    print_info("✅ Webhook 6: Blocked immediately (no attempt)")
    print_info("✅ After 60s: Circuit transitions to HALF_OPEN (one probe)")
    print_info("✅ If probe succeeds: CLOSED (resume normal)")
    print_info("✅ If probe fails: Reopens (another 60s wait)")
    
    print_step(4, "Check logs for circuit breaker state")
    print_info("grep 'Circuit breaker' /var/log/deltacrown-prod.log | tail -10")
    print_info("")
    print_info("Expected:")
    print_info("  [INFO] Circuit breaker failure recorded: 1/5")
    print_info("  [INFO] Circuit breaker failure recorded: 2/5")
    print_info("  [INFO] Circuit breaker failure recorded: 3/5")
    print_info("  [INFO] Circuit breaker failure recorded: 4/5")
    print_info("  [INFO] Circuit breaker failure recorded: 5/5")
    print_info("  [ERROR] Circuit breaker OPENED: 5 failures in 120s window")
    print_info("  [WARN] Webhook delivery blocked: circuit breaker is OPEN")
    
    print_step(5, "Test circuit breaker blocking")
    print_info("Trigger one more webhook immediately:")
    
    pv = PaymentVerification.objects.create(
        user=user,
        tournament=tournament,
        amount=200.00,
        status='pending'
    )
    pv.status = 'verified'
    pv.save()
    print_success(f"Webhook 6 triggered (payment ID: {pv.id}) — should be BLOCKED")
    
    print_info("")
    print_info("Expected log:")
    print_info("  [WARN] Webhook delivery blocked: circuit breaker is OPEN (will probe in 60s)")
    
    print(f"\n{GREEN}{'─'*70}{RESET}")
    print(f"{GREEN}Test 4 Setup Complete — Wait 60s for probe attempt{RESET}")
    print(f"{GREEN}{'─'*70}{RESET}\n")

def run_all_tests():
    """Run all 4 smoke tests"""
    print(f"\n{BLUE}╔═══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║  Canary Smoke Tests — Phase 5.6 Webhooks                         ║{RESET}")
    print(f"{BLUE}║  Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'):^53} ║{RESET}")
    print(f"{BLUE}╚═══════════════════════════════════════════════════════════════════╝{RESET}\n")
    
    print(f"{YELLOW}Prerequisites:{RESET}")
    print_info("✅ Feature flag NOTIFICATIONS_WEBHOOK_ENABLED=True")
    print_info("✅ WEBHOOK_ENDPOINT configured")
    print_info("✅ WEBHOOK_SECRET loaded from secrets manager")
    print_info("✅ Receiver endpoint accessible (HTTPS)")
    print_info("✅ Receiver implements HMAC verification")
    print_info("")
    
    input(f"{YELLOW}Press Enter to start tests...{RESET}")
    
    # Run tests
    test_1_success_path()
    input(f"\n{YELLOW}Press Enter to continue to Test 2...{RESET}")
    
    test_2_retry_path()
    input(f"\n{YELLOW}Press Enter to continue to Test 3...{RESET}")
    
    test_3_no_retry_path()
    input(f"\n{YELLOW}Press Enter to continue to Test 4...{RESET}")
    
    test_4_circuit_breaker()
    
    # Summary
    print_header("TEST SUITE COMPLETE")
    print(f"{GREEN}All 4 smoke test scenarios triggered successfully!{RESET}\n")
    
    print(f"{YELLOW}Next Steps:{RESET}")
    print_info("1. Check sender logs: tail -f /var/log/deltacrown-prod.log | grep -i webhook")
    print_info("2. Check receiver logs: Verify HMAC signatures, timestamps, webhook_ids")
    print_info("3. Run monitoring scripts: bash scripts/monitor_success_rate.sh")
    print_info("4. Verify PII clean: bash scripts/monitor_pii.sh")
    print_info("5. Check circuit breaker state: bash scripts/monitor_circuit_breaker.sh")
    print_info("")
    print_info("If all tests pass → Monitor for 24 hours → Proceed to 25% canary")
    print_info("")
    
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Monitoring Targets (24h @ 5%):{RESET}")
    print_info("• Success rate: ≥95% (rollback if <90%)")
    print_info("• P95 latency: <2000ms")
    print_info("• Circuit breaker opens: <5 per day")
    print_info("• PII leaks: 0 (immediate rollback)")
    print(f"{BLUE}{'='*70}{RESET}\n")

if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n\n{RED}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
