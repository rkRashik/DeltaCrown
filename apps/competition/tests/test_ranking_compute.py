"""
Tests for Ranking Compute and Snapshot Services

Phase 3A-D: Test ranking calculation, snapshot updates, and team detail integration
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.competition.models import (
    MatchReport,
    MatchVerification,
    GameRankingConfig,
    TeamGameRankingSnapshot,
    TeamGlobalRankingSnapshot,
)
from apps.competition.services import RankingComputeService, SnapshotService
from apps.organizations.models import Team, TeamMembership, Organization
from apps.organizations.choices import MembershipRole, MembershipStatus

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def organization():
    """Create test organization"""
    ceo = User.objects.create_user(username="ceo", email="ceo@test.com", password="password")
    return Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)


@pytest.fixture
def team1(organization):
    """Create team 1"""
    return Team.objects.create(
        name="Team Alpha",
        slug="team-alpha",
        organization=organization,
        game_id=1,
        region="Bangladesh"
    )


@pytest.fixture
def team2(organization):
    """Create team 2"""
    return Team.objects.create(
        name="Team Beta",
        slug="team-beta",
        organization=organization,
        game_id=1,
        region="Bangladesh"
    )


@pytest.fixture
def owner_user(team1):
    """Create team owner"""
    user = User.objects.create_user(username="owner", email="owner@test.com", password="password")
    TeamMembership.objects.create(
        team=team1,
        user=user,
        role=MembershipRole.OWNER,
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
def game_config():
    """Create game ranking config with standard weights"""
    return GameRankingConfig.objects.create(
        game_id="LOL",
        game_name="League of Legends",
        is_active=True,
        scoring_weights={
            'verified_match_win': 10,
            'tournament_win': 500,
        },
        tier_thresholds={
            'DIAMOND': 2000,
            'PLATINUM': 1200,
            'GOLD': 600,
            'SILVER': 250,
            'BRONZE': 100,
        },
        decay_policy={
            'enabled': True,
            'inactivity_threshold_days': 30,
            'decay_rate_per_day': 0.01,
        }
    )


@pytest.fixture
def verified_match(team1, team2, owner_user, opponent_user, game_config):
    """Create a verified match win for team1"""
    played_at = timezone.now() - timedelta(hours=2)
    
    match_report = MatchReport.objects.create(
        team1=team1,
        team2=team2,
        game_id="LOL",
        match_type='RANKED',
        result='WIN',
        submitted_by=owner_user,
        played_at=played_at,
    )
    
    verification = MatchVerification.objects.create(
        match_report=match_report,
        status='CONFIRMED',
        confidence_level='HIGH',
        verified_at=timezone.now(),
        verified_by=opponent_user,
    )
    
    return match_report


# ============================================================================
# RANKING COMPUTE SERVICE TESTS
# ============================================================================

class TestRankingComputeService:
    """Test ranking score calculation"""
    
    def test_compute_team_game_score_no_matches(self, team1, game_config):
        """Test score calculation for team with no matches"""
        score, breakdown = RankingComputeService.compute_team_game_score(team1, "LOL")
        
        assert score == 0
        assert breakdown['verified_match_score'] == 0
        assert breakdown['tournament_score'] == 0
        assert breakdown['total_verified_matches'] == 0
    
    def test_compute_team_game_score_with_verified_match(self, team1, verified_match, game_config):
        """Test score calculation with one verified match win"""
        score, breakdown = RankingComputeService.compute_team_game_score(team1, "LOL")
        
        # 1 win * 10 points * 1.0 (HIGH confidence) = 10
        assert score == 10
        assert breakdown['verified_match_score'] == 10
        assert breakdown['total_verified_matches'] == 1
    
    def test_compute_team_game_score_with_multiple_wins(self, team1, team2, owner_user, game_config):
        """Test score calculation with multiple verified wins"""
        # Create 5 verified match wins
        for i in range(5):
            match = MatchReport.objects.create(
                team1=team1,
                team2=team2,
                game_id="LOL",
                match_type='RANKED',
                result='WIN',
                submitted_by=owner_user,
                played_at=timezone.now() - timedelta(hours=i),
            )
            MatchVerification.objects.create(
                match_report=match,
                status='CONFIRMED',
                confidence_level='HIGH',
            )
        
        score, breakdown = RankingComputeService.compute_team_game_score(team1, "LOL")
        
        # 5 wins * 10 points * 1.0 = 50
        assert score == 50
        assert breakdown['total_verified_matches'] == 5
    
    def test_compute_team_game_score_confidence_weights(self, team1, team2, owner_user, game_config):
        """Test that confidence levels affect score calculation"""
        # HIGH confidence match (1.0 weight)
        match_high = MatchReport.objects.create(
            team1=team1,
            team2=team2,
            game_id="LOL",
            match_type='RANKED',
            result='WIN',
            submitted_by=owner_user,
            played_at=timezone.now() - timedelta(hours=1),
        )
        MatchVerification.objects.create(
            match_report=match_high,
            status='CONFIRMED',
            confidence_level='HIGH',
        )
        
        # MEDIUM confidence match (0.7 weight)
        match_medium = MatchReport.objects.create(
            team1=team1,
            team2=team2,
            game_id="LOL",
            match_type='RANKED',
            result='WIN',
            submitted_by=owner_user,
            played_at=timezone.now() - timedelta(hours=2),
        )
        MatchVerification.objects.create(
            match_report=match_medium,
            status='PENDING',
            confidence_level='MEDIUM',
        )
        
        score, breakdown = RankingComputeService.compute_team_game_score(team1, "LOL")
        
        # HIGH: 10 * 1.0 = 10, MEDIUM not counted (status=PENDING)
        # Only CONFIRMED/ADMIN_VERIFIED count
        assert score == 10
        assert breakdown['total_verified_matches'] == 1  # Only CONFIRMED counts
    
    def test_compute_tier_assignment(self, game_config):
        """Test tier assignment based on score thresholds"""
        thresholds = game_config.tier_thresholds
        
        assert RankingComputeService.compute_tier(2500, thresholds) == 'DIAMOND'
        assert RankingComputeService.compute_tier(1500, thresholds) == 'PLATINUM'
        assert RankingComputeService.compute_tier(700, thresholds) == 'GOLD'
        assert RankingComputeService.compute_tier(300, thresholds) == 'SILVER'
        assert RankingComputeService.compute_tier(150, thresholds) == 'BRONZE'
        assert RankingComputeService.compute_tier(50, thresholds) == 'UNRANKED'
    
    def test_compute_confidence_level(self):
        """Test confidence level calculation based on match count"""
        assert RankingComputeService.compute_confidence_level(25) == 'STABLE'
        assert RankingComputeService.compute_confidence_level(15) == 'ESTABLISHED'
        assert RankingComputeService.compute_confidence_level(5) == 'PROVISIONAL'
        assert RankingComputeService.compute_confidence_level(0) == 'PROVISIONAL'
    
    def test_compute_team_global_score(self, team1, game_config):
        """Test global score aggregation across games"""
        # Create another game config
        GameRankingConfig.objects.create(
            game_id="VAL",
            game_name="Valorant",
            is_active=True,
            scoring_weights={'verified_match_win': 10},
            tier_thresholds={'GOLD': 500},
        )
        
        global_score, breakdown = RankingComputeService.compute_team_global_score(team1)
        
        # Team has no matches yet, so global score should be 0
        assert global_score == 0
        assert breakdown['games_played'] == 0


# ============================================================================
# SNAPSHOT SERVICE TESTS
# ============================================================================

class TestSnapshotService:
    """Test snapshot creation and updates"""
    
    def test_update_team_game_snapshot_creates_new(self, team1, game_config):
        """Test creating new game snapshot"""
        snapshot = SnapshotService.update_team_game_snapshot(team1, "LOL")
        
        assert snapshot is not None
        assert snapshot.team == team1
        assert snapshot.game_id == "LOL"
        assert snapshot.score == 0  # No matches yet
        assert snapshot.tier == 'UNRANKED'
        assert snapshot.verified_match_count == 0
        assert snapshot.confidence_level == 'PROVISIONAL'
    
    def test_update_team_game_snapshot_updates_existing(self, team1, verified_match, game_config):
        """Test updating existing game snapshot after new matches"""
        # Create initial snapshot
        snapshot1 = SnapshotService.update_team_game_snapshot(team1, "LOL")
        assert snapshot1.score == 10
        assert snapshot1.verified_match_count == 1
        
        # Add another verified match
        match2 = MatchReport.objects.create(
            team1=team1,
            team2=verified_match.team2,
            game_id="LOL",
            match_type='RANKED',
            result='WIN',
            submitted_by=verified_match.submitted_by,
            played_at=timezone.now() - timedelta(hours=1),
        )
        MatchVerification.objects.create(
            match_report=match2,
            status='CONFIRMED',
            confidence_level='HIGH',
        )
        
        # Update snapshot
        snapshot2 = SnapshotService.update_team_game_snapshot(team1, "LOL")
        
        assert snapshot2.id == snapshot1.id  # Same record updated
        assert snapshot2.score == 20  # 2 wins * 10
        assert snapshot2.verified_match_count == 2
    
    def test_update_team_global_snapshot(self, team1, verified_match, game_config):
        """Test global snapshot creation"""
        # Create game snapshot first
        SnapshotService.update_team_game_snapshot(team1, "LOL")
        
        # Create global snapshot
        global_snapshot = SnapshotService.update_team_global_snapshot(team1)
        
        assert global_snapshot is not None
        assert global_snapshot.team == team1
        assert global_snapshot.global_score == 10  # Sum of all game scores
        assert global_snapshot.games_played == 1
        assert 'LOL' in global_snapshot.game_contributions
    
    def test_snapshot_rank_calculation(self, team1, team2, game_config):
        """Test that ranks are assigned correctly"""
        # Give team1 more score than team2
        for i in range(5):
            match = MatchReport.objects.create(
                team1=team1,
                team2=team2,
                game_id="LOL",
                match_type='RANKED',
                result='WIN',
                submitted_by=team1.vnext_memberships.first().user if team1.vnext_memberships.exists() else None,
                played_at=timezone.now() - timedelta(hours=i),
            )
            MatchVerification.objects.create(
                match_report=match,
                status='CONFIRMED',
                confidence_level='HIGH',
            )
        
        # Update snapshots for both teams
        SnapshotService.update_team_game_snapshot(team1, "LOL")
        SnapshotService.update_team_game_snapshot(team2, "LOL")
        
        # Recalculate ranks
        SnapshotService._recalculate_ranks("LOL")
        
        # Refresh from DB
        snapshot1 = TeamGameRankingSnapshot.objects.get(team=team1, game_id="LOL")
        snapshot2 = TeamGameRankingSnapshot.objects.get(team=team2, game_id="LOL")
        
        # Team1 should have better rank (lower number = better)
        assert snapshot1.rank is not None
        assert snapshot2.rank is not None
        assert snapshot1.rank < snapshot2.rank  # Team1 has more wins


# ============================================================================
# TEAM DETAIL INTEGRATION TESTS
# ============================================================================

class TestTeamDetailIntegration:
    """Test that stats appear correctly in team detail context"""
    
    def test_stats_with_no_snapshots(self, team1):
        """Test stats dict returns defaults when no snapshots exist"""
        from apps.organizations.services.team_detail_context import _build_stats_context
        
        stats = _build_stats_context(team1, is_restricted=False)
        
        assert stats['score'] == 0
        assert stats['tier'] == 'UNRANKED'
        assert stats['global_score'] == 0
        assert stats['verified_match_count'] == 0
    
    @pytest.mark.xfail(reason="Phase 3A-C: Integration with team detail context not yet complete. _build_stats_context needs to read from snapshots when COMPETITION_APP_ENABLED=True")
    def test_stats_with_snapshots(self, team1, verified_match, game_config):
        """Test stats dict uses real snapshot data when available"""
        from apps.organizations.services.team_detail_context import _build_stats_context
        
        # Create snapshots
        SnapshotService.update_team_game_snapshot(team1, "LOL")
        SnapshotService.update_team_global_snapshot(team1)
        
        # Get stats
        stats = _build_stats_context(team1, is_restricted=False)
        
        assert stats['score'] == 10
        assert stats['global_score'] == 10
        assert stats['verified_match_count'] == 1
        assert stats['confidence_level'] == 'PROVISIONAL'
    
    def test_stats_restricted_for_private_teams(self, team1):
        """Test stats hidden for restricted (private + unauthorized) viewers"""
        from apps.organizations.services.team_detail_context import _build_stats_context
        
        stats = _build_stats_context(team1, is_restricted=True)
        
        # Should return defaults (no real data exposed)
        assert stats['score'] == 0
        assert stats['tier'] == 'UNRANKED'
