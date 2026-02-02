"""
Tests for Competition Services

Phase 3A-C: Test MatchReportService and VerificationService
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.competition.models import MatchReport, MatchVerification, GameRankingConfig
from apps.competition.services import MatchReportService, VerificationService
from apps.organizations.models import Team, TeamMembership, Organization
from apps.organizations.choices import MembershipRole, MembershipStatus

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    """Create test organization"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    ceo = User.objects.create_user(username="ceo", email="ceo@test.com", password="password")
    return Organization.objects.create(
        name="Test Org",
        slug="test-org",
        ceo=ceo
    )


@pytest.fixture
def team1(organization):
    """Create team 1"""
    return Team.objects.create(
        name="Team Alpha",
        slug="team-alpha",
        organization=organization,
        game_id=1,  # Generic game ID for testing
        region="Bangladesh"
    )


@pytest.fixture
def team2(organization):
    """Create team 2"""
    return Team.objects.create(
        name="Team Beta",
        slug="team-beta",
        organization=organization,
        game_id=1,  # Generic game ID for testing
        region="Bangladesh"
    )


@pytest.fixture
def owner_user(team1):
    """Create team owner user"""
    user = User.objects.create_user(username="owner", email="owner@test.com", password="password")
    TeamMembership.objects.create(
        team=team1,
        user=user,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE
    )
    return user


@pytest.fixture
def admin_user(team1):
    """Create team manager user (has admin permissions)"""
    user = User.objects.create_user(username="manager", email="manager@test.com", password="password")
    TeamMembership.objects.create(
        team=team1,
        user=user,
        role=MembershipRole.MANAGER,
        status=MembershipStatus.ACTIVE
    )
    return user


@pytest.fixture
def member_user(team1):
    """Create team member user (regular player)"""
    user = User.objects.create_user(username="member", email="member@test.com", password="password")
    TeamMembership.objects.create(
        team=team1,
        user=user,
        role=MembershipRole.PLAYER,
        status=MembershipStatus.ACTIVE
    )
    return user


@pytest.fixture
def opponent_user(team2):
    """Create opponent team member"""
    user = User.objects.create_user(username="opponent", email="opponent@test.com", password="password")
    TeamMembership.objects.create(
        team=team2,
        user=user,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE
    )
    return user


@pytest.fixture
def staff_user():
    """Create staff user"""
    user = User.objects.create_superuser(username="staff", email="staff@test.com", password="password")
    return user


@pytest.fixture
def game_config():
    """Create game ranking config"""
    return GameRankingConfig.objects.create(
        game_id="LOL",
        game_name="League of Legends"
    )


class TestMatchReportService:
    """Test MatchReportService"""
    
    def test_submit_match_report_success_owner(self, owner_user, team1, team2, game_config):
        """Test successful match report submission by owner"""
        played_at = timezone.now() - timedelta(hours=2)
        
        report = MatchReportService.submit_match_report(
            submitted_by=owner_user,
            team1=team1,
            team2=team2,
            game_id="LOL",
            result="WIN",
            played_at=played_at,
            evidence_url="https://example.com/proof"
        )
        
        assert report is not None
        assert report.team1 == team1
        assert report.team2 == team2
        assert report.result == "WIN"
        assert report.evidence_url == "https://example.com/proof"
        assert MatchVerification.objects.filter(match_report=report).exists()
    
    def test_submit_match_report_success_admin(self, admin_user, team1, team2, game_config):
        """Test successful match report submission by admin"""
        played_at = timezone.now() - timedelta(hours=1)
        
        report = MatchReportService.submit_match_report(
            submitted_by=admin_user,
            team1=team1,
            team2=team2,
            game_id="LOL",
            result="LOSS",
            played_at=played_at
        )
        
        assert report is not None
        assert report.result == "LOSS"
    
    def test_submit_match_report_permission_denied_member(self, member_user, team1, team2, game_config):
        """Test permission denied for regular member"""
        played_at = timezone.now() - timedelta(hours=1)
        
        with pytest.raises(PermissionDenied, match="Only team owners and managers"):
            MatchReportService.submit_match_report(
                submitted_by=member_user,
                team1=team1,
                team2=team2,
                game_id="LOL",
                result="WIN",
                played_at=played_at
            )
    
    def test_submit_match_report_permission_denied_non_member(self, opponent_user, team1, team2, game_config):
        """Test permission denied for non-member"""
        played_at = timezone.now() - timedelta(hours=1)
        
        with pytest.raises(PermissionDenied, match="must be a member"):
            MatchReportService.submit_match_report(
                submitted_by=opponent_user,
                team1=team1,
                team2=team2,
                game_id="LOL",
                result="WIN",
                played_at=played_at
            )
    
    def test_submit_match_report_same_team(self, owner_user, team1, game_config):
        """Test validation error for same team matchup"""
        played_at = timezone.now() - timedelta(hours=1)
        
        with pytest.raises(ValidationError, match="Cannot report a match against your own team"):
            MatchReportService.submit_match_report(
                submitted_by=owner_user,
                team1=team1,
                team2=team1,
                game_id="LOL",
                result="WIN",
                played_at=played_at
            )
    
    def test_submit_match_report_invalid_game(self, owner_user, team1, team2):
        """Test validation error for unsupported game"""
        played_at = timezone.now() - timedelta(hours=1)
        
        with pytest.raises(ValidationError, match="Game .* not supported"):
            MatchReportService.submit_match_report(
                submitted_by=owner_user,
                team1=team1,
                team2=team2,
                game_id="INVALID_GAME",
                result="WIN",
                played_at=played_at
            )
    
    def test_submit_match_report_future_date(self, owner_user, team1, team2, game_config):
        """Test validation error for future date"""
        played_at = timezone.now() + timedelta(hours=1)
        
        with pytest.raises(ValidationError, match="cannot be in the future"):
            MatchReportService.submit_match_report(
                submitted_by=owner_user,
                team1=team1,
                team2=team2,
                game_id="LOL",
                result="WIN",
                played_at=played_at
            )


class TestVerificationService:
    """Test VerificationService"""
    
    @pytest.fixture
    def pending_match_report(self, owner_user, team1, team2, game_config):
        """Create a pending match report"""
        played_at = timezone.now() - timedelta(hours=1)
        return MatchReportService.submit_match_report(
            submitted_by=owner_user,
            team1=team1,
            team2=team2,
            game_id="LOL",
            result="WIN",
            played_at=played_at
        )
    
    def test_confirm_match_success(self, opponent_user, pending_match_report):
        """Test successful match confirmation by opponent"""
        verification = VerificationService.confirm_match(opponent_user, pending_match_report.id)
        
        assert verification.status == 'CONFIRMED'
        assert verification.confidence_level == 'HIGH'
        assert verification.verified_by == opponent_user
        assert verification.verified_at is not None
    
    def test_confirm_match_permission_denied_reporter(self, owner_user, pending_match_report):
        """Test permission denied when reporter tries to confirm"""
        with pytest.raises(PermissionDenied, match="Only members of the opponent team"):
            VerificationService.confirm_match(owner_user, pending_match_report.id)
    
    def test_dispute_match_success(self, opponent_user, pending_match_report):
        """Test successful match dispute by opponent"""
        verification = VerificationService.dispute_match(
            opponent_user,
            pending_match_report.id,
            "The score was incorrect, we actually won this match"
        )
        
        assert verification.status == 'DISPUTED'
        assert verification.confidence_level == 'NONE'
        assert "DISPUTED" in verification.admin_notes
    
    def test_dispute_match_short_reason(self, opponent_user, pending_match_report):
        """Test validation error for short dispute reason"""
        with pytest.raises(ValidationError, match="at least 10 characters"):
            VerificationService.dispute_match(opponent_user, pending_match_report.id, "Too short")
    
    def test_admin_verify_match_success(self, staff_user, pending_match_report):
        """Test successful admin verification"""
        verification = VerificationService.admin_verify_match(staff_user, pending_match_report.id)
        
        assert verification.status == 'ADMIN_VERIFIED'
        assert verification.confidence_level == 'HIGH'
        assert verification.verified_by == staff_user
    
    def test_admin_verify_match_permission_denied(self, owner_user, pending_match_report):
        """Test permission denied for non-staff"""
        with pytest.raises(PermissionDenied, match="Only staff members"):
            VerificationService.admin_verify_match(owner_user, pending_match_report.id)
    
    def test_reject_match_success(self, staff_user, pending_match_report):
        """Test successful match rejection"""
        verification = VerificationService.reject_match(
            staff_user,
            pending_match_report.id,
            "Fraudulent submission detected"
        )
        
        assert verification.status == 'REJECTED'
        assert verification.confidence_level == 'NONE'
        assert "REJECTED" in verification.admin_notes
        assert "Fraudulent" in verification.admin_notes
    
    def test_reject_match_permission_denied(self, owner_user, pending_match_report):
        """Test permission denied for non-staff rejection"""
        with pytest.raises(PermissionDenied, match="Only staff members"):
            VerificationService.reject_match(owner_user, pending_match_report.id)
