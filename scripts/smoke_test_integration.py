"""
Manual E2E Smoke Test for UP-INTEGRATION-01
============================================

PREREQUISITES:
1. Set environment: USER_PROFILE_INTEGRATION_ENABLED=true
2. Run migrations: python manage.py migrate
3. Have test users/games ready

TEST FLOW:
1. Create tournament
2. Register user
3. Approve registration
4. Verify payment (if applicable)
5. Check-in toggle
6. Submit match result + finalize
7. Complete tournament / mark winner

VERIFICATION QUERIES (Run in Django shell):
```python
from apps.user_profile.models import UserActivity, UserProfileStats
from django.contrib.auth import get_user_model

User = get_user_model()

# Check activity events created
events = UserActivity.objects.filter(
    event_type__startswith='tournament.'
).order_by('-timestamp')

print(f"Total tournament events: {events.count()}")
for event in events[:10]:
    print(f"  {event.timestamp}: {event.event_type} - {event.metadata.get('idempotency_key')}")

# Check idempotency keys are deterministic (no timestamps)
keys = [e.metadata.get('idempotency_key') for e in events if e.metadata.get('idempotency_key')]
print(f"\nSample idempotency keys:")
for key in keys[:5]:
    print(f"  {key}")

# Check stats recomputed
user_id = 1  # Replace with actual test user
stats = UserProfileStats.objects.filter(user_id=user_id).first()
if stats:
    print(f"\nUser {user_id} stats:")
    print(f"  Tournaments participated: {stats.tournaments_participated}")
    print(f"  Matches played: {stats.matches_played}")
    print(f"  Matches won: {stats.matches_won}")
```

PASS CRITERIA:
✅ Each tournament event creates exactly ONE UserActivity record
✅ Idempotency keys are deterministic (no timestamps, format: event:id:status)
✅ Duplicate calls don't create duplicate records
✅ Stats recompute when match/tournament finalizes
✅ Tournaments continue to work normally (no errors)
"""

# ACTUAL TEST EXECUTION (run with manage.py shell)
import os
os.environ['USER_PROFILE_INTEGRATION_ENABLED'] = 'true'

from django.db import transaction
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import UserActivity

User = get_user_model()

# Setup test data
test_user = User.objects.first()
tournament = Tournament.objects.filter(status='registration_open').first()

if not test_user or not tournament:
    print("⚠️  Missing test data. Create user and tournament first.")
else:
    print("=" * 60)
    print("SMOKE TEST: UP-INTEGRATION-01")
    print("=" * 60)
    
    # Baseline event count
    baseline_count = UserActivity.objects.filter(
        user_id=test_user.id,
        event_type__startswith='tournament.'
    ).count()
    print(f"Baseline events for user {test_user.id}: {baseline_count}")
    
    # TEST 1: Registration approval
    print("\n[TEST 1] Registration Approval...")
    with transaction.atomic():
        registration = Registration.objects.create(
            tournament=tournament,
            user=test_user,
            status='pending'
        )
        
        # Approve registration
        RegistrationService.approve_registration(
            registration_id=registration.id,
            approved_by_id=test_user.id
        )
    
    # Verify event created
    new_events = UserActivity.objects.filter(
        user_id=test_user.id,
        event_type='tournament.registration.approved'
    ).order_by('-timestamp')
    
    if new_events.exists():
        event = new_events.first()
        idempotency_key = event.metadata.get('idempotency_key', 'MISSING')
        print(f"✅ Event created: {event.event_type}")
        print(f"   Idempotency key: {idempotency_key}")
        
        # Check key format (should be: registration_status:{reg_id}:approved)
        expected_key_pattern = f"registration_status:{registration.id}:approved"
        if idempotency_key == expected_key_pattern:
            print(f"✅ Idempotency key is deterministic")
        else:
            print(f"❌ Idempotency key mismatch!")
            print(f"   Expected: {expected_key_pattern}")
            print(f"   Got: {idempotency_key}")
    else:
        print("❌ No event created!")
    
    # TEST 2: Idempotency check (call again)
    print("\n[TEST 2] Idempotency Check (re-approve)...")
    try:
        with transaction.atomic():
            registration.status = 'pending'
            registration.save()
            RegistrationService.approve_registration(
                registration_id=registration.id,
                approved_by_id=test_user.id
            )
    except Exception as e:
        print(f"   (Service may reject re-approval: {e})")
    
    # Count events again
    final_count = UserActivity.objects.filter(
        user_id=test_user.id,
        event_type='tournament.registration.approved'
    ).count()
    
    if final_count == 1:
        print(f"✅ Idempotency maintained: still {final_count} event(s)")
    else:
        print(f"❌ Duplicate events created! Count: {final_count}")
    
    print("\n" + "=" * 60)
    print("SMOKE TEST COMPLETE")
    print("=" * 60)
    print(f"\nFinal event count for user {test_user.id}: {UserActivity.objects.filter(user_id=test_user.id, event_type__startswith='tournament.').count()}")
