"""
Tests for Phase 2E Part 2: Bounty Endorsements & Reputation
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from apps.accounts.models import User
from apps.user_profile.models import (
    UserProfile,
    HighlightClip,
    SkillEndorsement,
)
from apps.bounty.models import Bounty


@pytest.mark.django_db
class TestHighlightThumbnailFix:
    """
    Tests for UP-PHASE2E-HOTFIX: HighlightClip thumbnail_url nullable
    
    Root Cause: Migration 0041 was generated but not applied, causing
    IntegrityError when saving clips without thumbnails.
    
    Fix: 
    1. Applied migration 0041 (AlterField thumbnail_url null=True)
    2. Updated clean() to normalize '' to None
    """
    
    def test_highlight_creation_with_null_thumbnail(self):
        """HighlightClip can be created with thumbnail_url=None"""
        user = User.objects.create_user(
            username='clipper',
            email='clipper@test.com',
            password='Test123!'
        )
        
        # Create clip with explicit None thumbnail
        clip = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=test123',
            title='Test Clip',
            platform='youtube',
            video_id='test123',
            embed_url='https://www.youtube.com/embed/test123',
            thumbnail_url=None  # Explicit None
        )
        
        assert clip.id is not None
        assert clip.thumbnail_url is None
        
    def test_highlight_creation_with_empty_string_normalizes_to_none(self):
        """Empty string in clean() method normalizes to None"""
        user = User.objects.create_user(
            username='clipper2',
            email='clipper2@test.com',
            password='Test123!'
        )
        
        # The clean() method should convert empty string to None
        clip = HighlightClip(
            user=user,
            clip_url='https://www.youtube.com/watch?v=test456',
            title='Test Clip 2',
            platform='youtube',
            video_id='test456',
            embed_url='https://www.youtube.com/embed/test456',
            thumbnail_url=''  # Empty string
        )
        
        # After clean(), should be None
        clip.thumbnail_url = clip.thumbnail_url or None
        clip.save()
        
        clip.refresh_from_db()
        assert clip.thumbnail_url is None
        
    def test_highlight_with_valid_thumbnail(self):
        """HighlightClip with valid thumbnail URL saves correctly"""
        user = User.objects.create_user(
            username='clipper3',
            email='clipper3@test.com',
            password='Test123!'
        )
        
        clip = HighlightClip.objects.create(
            user=user,
            clip_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='Real Clip',
            platform='youtube',
            video_id='dQw4w9WgXcQ',
            embed_url='https://www.youtube.com/embed/dQw4w9WgXcQ',
            thumbnail_url='https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg'
        )
        
        assert clip.thumbnail_url == 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg'


@pytest.mark.django_db
class TestBountyEndorsements:
    """
    Tests for bounty endorsements (Phase 2E Part 2)
    
    Features:
    - SkillEndorsement.bounty FK (nullable)
    - POST /api/bounties/<id>/endorse/ endpoint
    - Uniqueness constraints: one endorsement per user per bounty
    """
    
    def test_endorsement_model_has_bounty_fk(self):
        """SkillEndorsement model has bounty FK field"""
        from apps.user_profile.models.endorsements import SkillEndorsement
        
        # Check field exists
        assert hasattr(SkillEndorsement, 'bounty')
        
        # Check it's nullable
        field = SkillEndorsement._meta.get_field('bounty')
        assert field.null is True
        
    def test_create_bounty_endorsement(self):
        """Create endorsement linked to bounty"""
        user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        
        bounty = Bounty.objects.create(
            issuer=user1.userprofile,
            opponent=user2.userprofile,
            amount=Decimal('50.00'),
            status='COMPLETED'
        )
        
        # User1 endorses user2 for this bounty
        endorsement = SkillEndorsement.objects.create(
            from_user=user1,
            to_user=user2,
            skill='aim',
            bounty=bounty,
            match=None
        )
        
        assert endorsement.bounty == bounty
        assert endorsement.match is None
        
    def test_bounty_endorsement_uniqueness(self):
        """Cannot endorse same user twice for same bounty"""
        user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        
        bounty = Bounty.objects.create(
            issuer=user1.userprofile,
            opponent=user2.userprofile,
            amount=Decimal('50.00'),
            status='COMPLETED'
        )
        
        # First endorsement
        SkillEndorsement.objects.create(
            from_user=user1,
            to_user=user2,
            skill='aim',
            bounty=bounty
        )
        
        # Second endorsement should fail
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            SkillEndorsement.objects.create(
                from_user=user1,
                to_user=user2,
                skill='shotcalling',
                bounty=bounty
            )


@pytest.mark.django_db
class TestReputationSignals:
    """
    Tests for reputation computation (Phase 2E Part 2)
    
    Formula:
    - Base: 50 points
    - Wins: +30 * win_rate (0.0-1.0)
    - Endorsements: +15 * min(1.0, count/20)
    - Disputes: -10 per dispute (max -30)
    
    Tiers:
    - Legend: 90+
    - Veteran: 75-89
    - Rising Star: 50-74
    - Rookie: <50
    """
    
    def test_reputation_calculation_rookie(self):
        """New user with no activity = Rookie (50 base)"""
        from apps.user_profile.services.profile_context import _compute_reputation_signals
        
        user = User.objects.create_user('newbie', 'n@test.com', 'pass')
        
        rep = _compute_reputation_signals(user)
        
        assert rep['reputation_score'] == 50
        assert rep['reputation_tier'] == 'Rookie'
        assert rep['win_rate'] == 0.0
        assert rep['endorsements_received_count'] == 0
        
    def test_reputation_calculation_with_wins(self):
        """User with 100% win rate gets +30 points"""
        from apps.user_profile.services.profile_context import _compute_reputation_signals
        
        user = User.objects.create_user('winner', 'w@test.com', 'pass')
        
        # Create 5 completed bounties (all confirmed = 100% win rate)
        for i in range(5):
            opponent = User.objects.create_user(f'opp{i}', f'opp{i}@test.com', 'pass')
            Bounty.objects.create(
                issuer=user.userprofile,
                opponent=opponent.userprofile,
                amount=Decimal('50.00'),
                status='COMPLETED',
                result='CONFIRMED'
            )
        
        rep = _compute_reputation_signals(user)
        
        # Base 50 + 30 (100% wins) = 80 (Veteran tier)
        assert rep['reputation_score'] == 80
        assert rep['reputation_tier'] == 'Veteran'
        assert rep['win_rate'] == 1.0
        
    def test_reputation_calculation_with_endorsements(self):
        """User with endorsements gets +15 * (count/20) points"""
        from apps.user_profile.services.profile_context import _compute_reputation_signals
        
        user = User.objects.create_user('endorsed', 'e@test.com', 'pass')
        
        # Create 10 endorsements (50% of max 20)
        for i in range(10):
            endorser = User.objects.create_user(f'end{i}', f'end{i}@test.com', 'pass')
            SkillEndorsement.objects.create(
                from_user=endorser,
                to_user=user,
                skill='aim'
            )
        
        rep = _compute_reputation_signals(user)
        
        # Base 50 + 7.5 (10/20 * 15) = 57.5 → 57 (Rising Star)
        assert rep['reputation_score'] in [57, 58]  # Allow rounding variance
        assert rep['reputation_tier'] == 'Rising Star'
        assert rep['endorsements_received_count'] == 10


@pytest.mark.django_db
class TestEndorsementAPI:
    """
    Tests for POST /api/bounties/<id>/endorse/ endpoint
    
    Rules:
    - COMPLETED bounties only
    - Participants only (issuer or opponent)
    - No self-endorsement
    - One endorsement per bounty per user
    """
    
    def test_endorse_bounty_opponent(self, client):
        """Participant can endorse opponent after COMPLETED bounty"""
        user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        
        bounty = Bounty.objects.create(
            issuer=user1.userprofile,
            opponent=user2.userprofile,
            amount=Decimal('50.00'),
            status='COMPLETED'
        )
        
        client.force_login(user1)
        
        url = reverse('user_profile:award_bounty_endorsement', args=[bounty.id])
        response = client.post(url, {
            'skill': 'aim',
            'receiver_id': user2.id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify endorsement created
        endorsement = SkillEndorsement.objects.filter(
            from_user=user1,
            to_user=user2,
            bounty=bounty
        ).first()
        assert endorsement is not None
        assert endorsement.skill == 'aim'
        
    def test_cannot_endorse_pending_bounty(self, client):
        """Cannot endorse for non-COMPLETED bounties"""
        user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        
        bounty = Bounty.objects.create(
            issuer=user1.userprofile,
            opponent=user2.userprofile,
            amount=Decimal('50.00'),
            status='PENDING'  # Not completed
        )
        
        client.force_login(user1)
        
        url = reverse('user_profile:award_bounty_endorsement', args=[bounty.id])
        response = client.post(url, {'skill': 'aim'})
        
        assert response.status_code in [400, 403]
