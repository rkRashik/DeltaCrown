"""
Test get_endorsements_summary() function.

Regression test for Phase 2B.1.3 fix.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.services import endorsement_service
from apps.matches.models import Match, MatchParticipant
from apps.tournaments.models import Tournament
from apps.user_profile.models import SkillEndorsement, SkillType

User = get_user_model()


@pytest.mark.django_db
class TestEndorsementSummary:
    """Test get_endorsements_summary() returns correct key names."""
    
    def test_get_endorsements_summary_returns_correct_keys(self, user, other_user, completed_match):
        """Verify get_endorsements_summary() returns total_count and by_skill."""
        # Create endorsement
        SkillEndorsement.objects.create(
            match=completed_match,
            endorser=other_user,
            receiver=user,
            skill_name=SkillType.LEADERSHIP,
        )
        
        # Call function
        summary = endorsement_service.get_endorsements_summary(user)
        
        # Verify keys
        assert 'total_count' in summary, "Missing 'total_count' key"
        assert 'by_skill' in summary, "Missing 'by_skill' key"
        assert 'top_skill' in summary, "Missing 'top_skill' key"
        assert 'recent_endorsements' in summary, "Missing 'recent_endorsements' key"
        
        # Verify values
        assert summary['total_count'] == 1
        assert len(summary['by_skill']) == 1
        assert summary['top_skill'] == SkillType.LEADERSHIP
        assert len(summary['recent_endorsements']) == 1
    
    def test_get_endorsements_summary_when_empty(self, user):
        """Verify get_endorsements_summary() handles users with no endorsements."""
        summary = endorsement_service.get_endorsements_summary(user)
        
        # Verify empty state
        assert summary['total_count'] == 0
        assert summary['by_skill'] == []
        assert summary['top_skill'] is None
        assert summary['recent_endorsements'] == []
    
    def test_get_endorsements_summary_multiple_skills(self, user, other_user, completed_match):
        """Verify get_endorsements_summary() aggregates multiple skills."""
        # Create multiple endorsements
        SkillEndorsement.objects.create(
            match=completed_match,
            endorser=other_user,
            receiver=user,
            skill_name=SkillType.LEADERSHIP,
        )
        SkillEndorsement.objects.create(
            match=completed_match,
            endorser=other_user,
            receiver=user,
            skill_name=SkillType.COMMUNICATION,
        )
        
        summary = endorsement_service.get_endorsements_summary(user)
        
        # Verify aggregation
        assert summary['total_count'] == 2
        assert len(summary['by_skill']) == 2
        
        # Verify skill breakdown
        skill_names = [skill['name'] for skill in summary['by_skill']]
        assert SkillType.LEADERSHIP in skill_names
        assert SkillType.COMMUNICATION in skill_names


# Fixtures
@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='testpass123',
    )


@pytest.fixture
def tournament():
    """Create test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        status='completed',
    )


@pytest.fixture
def completed_match(tournament, user, other_user):
    """Create completed match with participants."""
    match = Match.objects.create(
        tournament=tournament,
        status='completed',
        result_status='confirmed',
    )
    
    # Add participants
    MatchParticipant.objects.create(match=match, user=user, team='team1')
    MatchParticipant.objects.create(match=match, user=other_user, team='team1')
    
    return match
