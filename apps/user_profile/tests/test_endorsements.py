# apps/user_profile/tests/test_endorsements.py
"""
Test suite for Post-Match Endorsement System (P0 Feature).

Tests:
- Permission enforcement (participant verification, time window, match state)
- Uniqueness constraints (one endorsement per endorser per match)
- Teammate verification (same team check)
- Self-endorsement prevention
- Aggregation correctness (skill counts, stats)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta

from apps.user_profile.models import (
    SkillEndorsement,
    EndorsementOpportunity,
    SkillType,
)
from apps.user_profile.services.endorsement_service import (
    can_endorse,
    is_match_participant,
    get_eligible_teammates,
    create_endorsement,
    get_endorsement_stats,
    create_endorsement_opportunities,
    get_pending_endorsement_opportunities,
)
from apps.tournaments.models import Tournament, Match
from apps.core.models import Game

User = get_user_model()


# ============================================================================
# PERMISSION ENFORCEMENT TESTS
# ============================================================================

@pytest.mark.django_db
class TestPermissionEnforcement:
    """Test permission rules for endorsements."""
    
    def test_can_endorse_completed_match(self):
        """User can endorse after match completion."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        can_endorse_flag, error = can_endorse(user1, match)
        
        assert can_endorse_flag is True
        assert error is None
    
    def test_cannot_endorse_incomplete_match(self):
        """User cannot endorse before match completion."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='live',  # Not completed
        )
        
        can_endorse_flag, error = can_endorse(user1, match)
        
        assert can_endorse_flag is False
        assert 'not completed' in error.lower()
    
    def test_cannot_endorse_after_24_hours(self):
        """User cannot endorse after 24-hour window expires."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        # Match completed 25 hours ago
        completed_at = timezone.now() - timedelta(hours=25)
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=completed_at,
        )
        
        can_endorse_flag, error = can_endorse(user1, match)
        
        assert can_endorse_flag is False
        assert 'expired' in error.lower()
    
    def test_cannot_endorse_if_not_participant(self):
        """User cannot endorse if they weren't in the match."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        user3 = User.objects.create_user(username='player3', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        can_endorse_flag, error = can_endorse(user3, match)
        
        assert can_endorse_flag is False
        assert 'participant' in error.lower()


# ============================================================================
# UNIQUENESS CONSTRAINT TESTS
# ============================================================================

@pytest.mark.django_db
class TestUniquenessConstraints:
    """Test uniqueness constraints for endorsements."""
    
    def test_one_endorsement_per_match(self):
        """User can only endorse once per match."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # First endorsement succeeds
        endorsement1 = create_endorsement(
            endorser=user1,
            receiver=user2,
            match=match,
            skill=SkillType.AIM,
        )
        
        assert endorsement1.id
        
        # Second endorsement from same user should fail
        with pytest.raises(PermissionDenied) as exc_info:
            create_endorsement(
                endorser=user1,
                receiver=user2,
                match=match,
                skill=SkillType.CLUTCH,
            )
        
        assert 'already endorsed' in str(exc_info.value).lower()
    
    def test_cannot_endorse_self(self):
        """User cannot endorse themselves."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # Try to self-endorse
        with pytest.raises(ValidationError) as exc_info:
            create_endorsement(
                endorser=user1,
                receiver=user1,  # Same as endorser
                match=match,
                skill=SkillType.AIM,
            )
        
        assert 'yourself' in str(exc_info.value).lower()


# ============================================================================
# TEAMMATE VERIFICATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestTeammateVerification:
    """Test teammate verification for team matches."""
    
    def test_solo_match_can_endorse_opponent(self):
        """In 1v1 match, can endorse opponent."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            participant1_name=user1.username,
            participant2_name=user2.username,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # User1 can endorse User2 (opponent in 1v1)
        endorsement = create_endorsement(
            endorser=user1,
            receiver=user2,
            match=match,
            skill=SkillType.AIM,
        )
        
        assert endorsement.id
        assert endorsement.endorser == user1
        assert endorsement.receiver == user2


# ============================================================================
# AGGREGATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestEndorsementAggregation:
    """Test endorsement aggregation for profile display."""
    
    def test_get_endorsement_stats_empty(self):
        """Stats for user with no endorsements."""
        user = User.objects.create_user(username='player1', password='test123')
        
        stats = get_endorsement_stats(user)
        
        assert stats['total_endorsements'] == 0
        assert stats['skills'] == []
        assert stats['top_skill'] is None
        assert stats['top_skill_count'] == 0
        assert stats['unique_matches'] == 0
        assert stats['unique_endorsers'] == 0
    
    def test_get_endorsement_stats_with_data(self):
        """Stats for user with endorsements."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        user3 = User.objects.create_user(username='player3', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        # Create 3 matches
        matches = []
        for i in range(3):
            match = Match.objects.create(
                tournament=tournament,
                round_number=1,
                match_number=i + 1,
                participant1_id=user1.id,
                participant2_id=user2.id if i < 2 else user3.id,
                state='completed',
                completed_at=timezone.now(),
            )
            matches.append(match)
        
        # Create endorsements:
        # - 2x AIM endorsements for user1
        # - 1x CLUTCH endorsement for user1
        SkillEndorsement.objects.create(
            match=matches[0],
            endorser=user2,
            receiver=user1,
            skill_name=SkillType.AIM,
        )
        
        SkillEndorsement.objects.create(
            match=matches[1],
            endorser=user2,
            receiver=user1,
            skill_name=SkillType.AIM,
        )
        
        SkillEndorsement.objects.create(
            match=matches[2],
            endorser=user3,
            receiver=user1,
            skill_name=SkillType.CLUTCH,
        )
        
        stats = get_endorsement_stats(user1)
        
        assert stats['total_endorsements'] == 3
        assert len(stats['skills']) == 2  # AIM and CLUTCH
        
        # Find AIM skill stats
        aim_stats = next(s for s in stats['skills'] if s['name'] == SkillType.AIM)
        assert aim_stats['count'] == 2
        assert aim_stats['percentage'] == pytest.approx(66.7, abs=0.1)
        
        # Find CLUTCH skill stats
        clutch_stats = next(s for s in stats['skills'] if s['name'] == SkillType.CLUTCH)
        assert clutch_stats['count'] == 1
        assert clutch_stats['percentage'] == pytest.approx(33.3, abs=0.1)
        
        # Top skill should be AIM (highest count)
        assert stats['top_skill'] == SkillType.AIM
        assert stats['top_skill_count'] == 2
        
        # Unique counts
        assert stats['unique_matches'] == 3
        assert stats['unique_endorsers'] == 2  # user2 and user3


# ============================================================================
# ENDORSEMENT OPPORTUNITY TESTS
# ============================================================================

@pytest.mark.django_db
class TestEndorsementOpportunities:
    """Test endorsement opportunity tracking."""
    
    def test_create_opportunities_for_completed_match(self):
        """Opportunities created when match completes."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # Create opportunities
        count = create_endorsement_opportunities(match)
        
        assert count == 2  # One for each participant
        
        # Verify opportunities exist
        opp1 = EndorsementOpportunity.objects.get(match=match, player=user1)
        opp2 = EndorsementOpportunity.objects.get(match=match, player=user2)
        
        assert opp1.is_used is False
        assert opp2.is_used is False
        assert opp1.expires_at == match.completed_at + timedelta(hours=24)
        assert opp2.expires_at == match.completed_at + timedelta(hours=24)
    
    def test_opportunity_marked_used_after_endorsement(self):
        """Opportunity marked as used after endorsement creation."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # Create opportunity
        opportunity = EndorsementOpportunity.objects.create(
            match=match,
            player=user1,
            expires_at=match.completed_at + timedelta(hours=24),
        )
        
        assert opportunity.is_used is False
        
        # Create endorsement
        create_endorsement(
            endorser=user1,
            receiver=user2,
            match=match,
            skill=SkillType.AIM,
        )
        
        # Opportunity should be marked as used
        opportunity.refresh_from_db()
        assert opportunity.is_used is True
        assert opportunity.used_at is not None
    
    def test_get_pending_opportunities(self):
        """Get pending endorsement opportunities for user."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        # Create 2 matches
        match1 = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        match2 = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='completed',
            completed_at=timezone.now() - timedelta(hours=1),
        )
        
        # Create opportunities
        create_endorsement_opportunities(match1)
        create_endorsement_opportunities(match2)
        
        # Get pending opportunities for user1
        pending = get_pending_endorsement_opportunities(user1)
        
        assert len(pending) == 2
        assert all(not opp.is_used for opp in pending)
        assert all(not opp.is_expired for opp in pending)


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestEndorsementValidation:
    """Test endorsement model validation."""
    
    def test_model_clean_prevents_self_endorsement(self):
        """Model.clean() prevents self-endorsement."""
        user = User.objects.create_user(username='player1', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user.id,
            participant2_id=user.id,
            state='completed',
            completed_at=timezone.now(),
        )
        
        # Try to create self-endorsement directly (bypassing service)
        endorsement = SkillEndorsement(
            match=match,
            endorser=user,
            receiver=user,
            skill_name=SkillType.AIM,
        )
        
        with pytest.raises(ValidationError) as exc_info:
            endorsement.full_clean()
        
        assert 'yourself' in str(exc_info.value).lower()
    
    def test_model_clean_checks_match_completion(self):
        """Model.clean() checks match completion."""
        user1 = User.objects.create_user(username='player1', password='test123')
        user2 = User.objects.create_user(username='player2', password='test123')
        
        game = Game.objects.create(name='Valorant', slug='valorant')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=game,
            registration_type='solo',
            max_participants=16,
        )
        
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=user1.id,
            participant2_id=user2.id,
            state='live',  # Not completed
        )
        
        endorsement = SkillEndorsement(
            match=match,
            endorser=user1,
            receiver=user2,
            skill_name=SkillType.AIM,
        )
        
        with pytest.raises(ValidationError) as exc_info:
            endorsement.full_clean()
        
        assert 'completed' in str(exc_info.value).lower()
