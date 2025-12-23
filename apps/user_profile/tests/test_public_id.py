"""
Tests for public_id system (UP-M1).

Coverage:
- Auto-assignment via signal (new profiles)
- Backfill for existing profiles without public_id
- Format validation
- Idempotency (repeated saves don't change public_id)
"""
import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import UserProfile
from apps.user_profile.services.public_id import PublicIDGenerator, PublicIDCounter

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPublicIDAssignment:
    """Test automatic public_id assignment via signals."""
    
    def test_new_user_gets_public_id(self):
        """New User → signal creates UserProfile with public_id."""
        user = User.objects.create_user(username='newuser', email='newuser@test.com', password='pass123')
        
        # Signal should have created profile with public_id
        profile = UserProfile.objects.get(user=user)
        assert profile.public_id is not None
        assert PublicIDGenerator.validate_format(profile.public_id)
        assert profile.public_id.startswith('DC-')
    
    def test_existing_profile_without_public_id_gets_backfilled(self):
        """Existing UserProfile without public_id gets one on next User.save()."""
        # Create profile without triggering signal
        user = User.objects.create_user(username='legacy_user', email='legacy@test.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Manually clear public_id (simulate legacy profile)
        profile.public_id = None
        profile.save(update_fields=['public_id'])
        
        assert profile.public_id is None
        
        # Trigger User.save() → signal should backfill
        user.first_name = 'Legacy'
        user.save()
        
        profile.refresh_from_db()
        assert profile.public_id is not None
        assert PublicIDGenerator.validate_format(profile.public_id)
    
    def test_public_id_is_unique(self):
        """Each profile gets unique public_id."""
        user1 = User.objects.create_user(username='user1', email='user1@test.com', password='pass123')
        user2 = User.objects.create_user(username='user2', email='user2@test.com', password='pass123')
        
        profile1 = UserProfile.objects.get(user=user1)
        profile2 = UserProfile.objects.get(user=user2)
        
        assert profile1.public_id != profile2.public_id
    
    def test_public_id_format_validation(self):
        """Public IDs match DC-YY-NNNNNN format."""
        user = User.objects.create_user(username='testuser', email='testuser@test.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Should match DC-YY-NNNNNN
        assert len(profile.public_id) == 12  # DC-25-000001 = 12 chars
        parts = profile.public_id.split('-')
        assert len(parts) == 3
        assert parts[0] == 'DC'
        assert len(parts[1]) == 2  # YY
        assert len(parts[2]) == 6  # NNNNNN
        assert parts[1].isdigit()
        assert parts[2].isdigit()
    
    def test_public_id_persists_on_subsequent_saves(self):
        """public_id doesn't change on subsequent profile saves (idempotent)."""
        user = User.objects.create_user(username='persistent', email='persistent@test.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        original_public_id = profile.public_id
        
        # Update profile multiple times
        profile.display_name = 'New Name'
        profile.save()
        
        profile.bio = 'New bio'
        profile.save()
        
        # public_id should remain unchanged
        profile.refresh_from_db()
        assert profile.public_id == original_public_id


@pytest.mark.django_db(transaction=True)
class TestPublicIDGenerator:
    """Test PublicIDGenerator service directly."""
    
    def test_generate_public_id_creates_counter(self):
        """First generation creates PublicIDCounter for current year."""
        # Clear any existing counters
        PublicIDCounter.objects.all().delete()
        
        public_id = PublicIDGenerator.generate_public_id()
        
        assert public_id is not None
        assert PublicIDGenerator.validate_format(public_id)
        
        # Counter should exist
        from django.utils import timezone
        current_year = timezone.now().year % 100
        counter = PublicIDCounter.objects.get(year=current_year)
        assert counter.counter == 1
    
    def test_generate_sequential_ids(self):
        """Sequential calls generate incrementing IDs."""
        PublicIDCounter.objects.all().delete()
        
        id1 = PublicIDGenerator.generate_public_id()
        id2 = PublicIDGenerator.generate_public_id()
        id3 = PublicIDGenerator.generate_public_id()
        
        # Extract counter values
        counter1 = int(id1.split('-')[2])
        counter2 = int(id2.split('-')[2])
        counter3 = int(id3.split('-')[2])
        
        assert counter1 == 1
        assert counter2 == 2
        assert counter3 == 3
    
    def test_validate_format_accepts_valid_ids(self):
        """Validator accepts correctly formatted IDs."""
        assert PublicIDGenerator.validate_format('DC-25-000001')
        assert PublicIDGenerator.validate_format('DC-30-999999')
        assert PublicIDGenerator.validate_format('DC-99-000042')
    
    def test_validate_format_rejects_invalid_ids(self):
        """Validator rejects malformed IDs."""
        assert not PublicIDGenerator.validate_format('DC-25-1')  # too short
        assert not PublicIDGenerator.validate_format('DC-2025-000001')  # 4-digit year
        assert not PublicIDGenerator.validate_format('XY-25-000001')  # wrong prefix
        assert not PublicIDGenerator.validate_format('DC-25-0000AB')  # non-numeric
        assert not PublicIDGenerator.validate_format('DC25000001')  # no dashes
        assert not PublicIDGenerator.validate_format('')  # empty
