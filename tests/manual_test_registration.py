"""
Manual test script to verify Registration and Payment models work correctly.
Run with: python manage.py shell < tests/manual_test_registration.py
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.tournaments.models import Game, Tournament, Registration, Payment

User = get_user_model()

# Clean up any existing test data
Game.objects.filter(slug='valorant-test').delete()
User.objects.filter(username__in=['organizer_test', 'player_test']).delete()

# Create test game
game = Game.objects.create(
    name='Valorant Test',
    slug='valorant-test',
    default_team_size=5,
    profile_id_field='valorant_id',
    default_result_type='map_score',
    is_active=True
)
print(f"✓ Created game: {game}")

# Create organizer
organizer = User.objects.create_user(
    username='organizer_test',
    email='organizer@test.com',
    password='test123'
)
print(f"✓ Created organizer: {organizer}")

# Create tournament
now = timezone.now()
tournament = Tournament.objects.create(
    name='Test Tournament',
    slug='test-tournament-manual',
    game=game,
    organizer=organizer,
    format='single_elimination',
    participation_type='team',
    max_participants=16,
    min_participants=4,
    registration_start=now,
    registration_end=now + timedelta(days=7),
    tournament_start=now + timedelta(days=8),
    has_entry_fee=True,
    entry_fee_amount=Decimal('500.00'),
    payment_methods=['bkash', 'nagad']
)
print(f"✓ Created tournament: {tournament}")

# Create player
player = User.objects.create_user(
    username='player_test',
    email='player@test.com',
    password='test123'
)
print(f"✓ Created player: {player}")

# Create registration
registration = Registration.objects.create(
    tournament=tournament,
    user=player,
    registration_data={
        'game_id': 'player#TAG',
        'phone': '+8801712345678',
        'notes': 'Looking forward to participating!'
    }
)
print(f"✓ Created registration: {registration}")
print(f"  - Status: {registration.status}")
print(f"  - Data: {registration.registration_data}")

# Create payment
payment = Payment.objects.create(
    registration=registration,
    payment_method='bkash',
    amount=Decimal('500.00'),
    transaction_id='TXN123456',
    payment_proof='payments/proof123.jpg'
)
print(f"✓ Created payment: {payment}")
print(f"  - Method: {payment.payment_method}")
print(f"  - Amount: {payment.amount}")
print(f"  - Status: {payment.status}")

# Test payment verification
payment.verify(verified_by=organizer, admin_notes='Payment verified successfully')
print(f"✓ Payment verified: {payment.status}")
print(f"  - Verified by: {payment.verified_by}")
print(f"  - Verified at: {payment.verified_at}")

# Test payment properties
print(f"✓ Payment properties:")
print(f"  - is_verified: {payment.is_verified}")
print(f"  - can_be_verified: {payment.can_be_verified}")

# Update registration status
registration.status = 'confirmed'
registration.save()
print(f"✓ Registration confirmed: {registration.status}")

# Test registration properties
print(f"✓ Registration properties:")
print(f"  - has_payment: {registration.has_payment}")
print(f"  - is_confirmed: {registration.is_confirmed}")
print(f"  - participant_identifier: {registration.participant_identifier}")

# Test check-in workflow
registration.check_in_participant(checked_in_by=organizer)
print(f"✓ Registration checked in:")
print(f"  - checked_in: {registration.checked_in}")
print(f"  - checked_in_at: {registration.checked_in_at}")

# Test slot assignment
registration.assign_slot(slot_number=1)
print(f"✓ Slot assigned: {registration.slot_number}")

# Test seeding
registration.assign_seed(seed=1)
print(f"✓ Seed assigned: {registration.seed}")

print("\n✅ All manual tests passed! Models are working correctly.")

# Cleanup
tournament.delete()
game.delete()
User.objects.filter(username__in=['organizer_test', 'player_test']).delete()
print("\n🧹 Cleaned up test data")
