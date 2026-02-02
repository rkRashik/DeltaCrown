"""Minimal tests for competition app models (Phase 3A-B)."""
import pytest
from django.utils import timezone
from apps.competition.models import (
    GameRankingConfig,
    MatchReport,
    MatchVerification,
    TeamGameRankingSnapshot,
    TeamGlobalRankingSnapshot,
)
from apps.organizations.models import Team


@pytest.fixture
def team_factory(db, django_user_model):
    """Factory to create test teams."""
    def make_team(name='Test Team', slug=None, game_id=1):
        import uuid
        unique_slug = slug or f"team-{uuid.uuid4().hex[:8]}"
        # Create a user for team owner
        owner = django_user_model.objects.create_user(
            username=f"owner-{uuid.uuid4().hex[:8]}",
            email=f"owner-{uuid.uuid4().hex[:8]}@example.com"
        )
        return Team.objects.create(
            name=name,
            slug=unique_slug,
            game_id=game_id,
            owner=owner,
        )
    return make_team


@pytest.mark.django_db
class TestGameRankingConfig:
    """Test GameRankingConfig model."""
    
    def test_create_game_ranking_config(self):
        """Should create GameRankingConfig with valid data."""
        config = GameRankingConfig.objects.create(
            game_id='LOL',
            game_name='League of Legends',
            scoring_weights={'tournament_win': 500},
            tier_thresholds={'DIAMOND': 2000},
            decay_policy={'enabled': True},
            verification_rules={'require_opponent_confirmation': True},
        )
        
        assert config.game_id == 'LOL'
        assert config.game_name == 'League of Legends'
        assert config.is_active is True
    
    def test_game_ranking_config_str(self):
        """Should return formatted string representation."""
        config = GameRankingConfig.objects.create(
            game_id='VAL',
            game_name='VALORANT',
        )
        
        assert str(config) == 'VALORANT (VAL)'


@pytest.mark.django_db
class TestMatchReport:
    """Test MatchReport model."""
    
    def test_create_match_report(self, team_factory):
        """Should create MatchReport with valid data."""
        team1 = team_factory(name='Team Alpha')
        team2 = team_factory(name='Team Beta')
        
        report = MatchReport.objects.create(
            game_id='CS2',
            match_type='RANKED',
            team1=team1,
            team2=team2,
            result='WIN',
            evidence_url='https://example.com/evidence',
            played_at=timezone.now(),
        )
        
        assert report.game_id == 'CS2'
        assert report.result == 'WIN'
        assert report.team1 == team1
        assert report.team2 == team2
    
    def test_match_report_str(self, team_factory):
        """Should return formatted string representation."""
        team1 = team_factory(name='Warriors')
        team2 = team_factory(name='Legends')
        
        report = MatchReport.objects.create(
            game_id='DOTA2',
            team1=team1,
            team2=team2,
            result='WIN',
            played_at=timezone.now(),
        )
        
        assert 'Warriors' in str(report)
        assert 'Legends' in str(report)
        assert 'WIN' in str(report)


@pytest.mark.django_db
class TestMatchVerification:
    """Test MatchVerification model."""
    
    def test_create_match_verification(self, team_factory):
        """Should create MatchVerification linked to MatchReport."""
        team1 = team_factory()
        team2 = team_factory()
        
        report = MatchReport.objects.create(
            game_id='RL',
            team1=team1,
            team2=team2,
            result='LOSS',
            played_at=timezone.now(),
        )
        
        verification = MatchVerification.objects.create(
            match_report=report,
            status='PENDING',
            confidence_level='LOW',
        )
        
        assert verification.match_report == report
        assert verification.status == 'PENDING'
        assert verification.confidence_level == 'LOW'
    
    def test_get_ranking_weight(self, team_factory):
        """Should return correct weight multiplier based on confidence."""
        team1 = team_factory()
        report = MatchReport.objects.create(
            game_id='APEX',
            team1=team1,
            result='WIN',
            played_at=timezone.now(),
        )
        
        verification = MatchVerification.objects.create(
            match_report=report,
            confidence_level='HIGH',
        )
        
        assert verification.get_ranking_weight() == 1.0
        
        verification.confidence_level = 'MEDIUM'
        assert verification.get_ranking_weight() == 0.7
        
        verification.confidence_level = 'LOW'
        assert verification.get_ranking_weight() == 0.3
        
        verification.confidence_level = 'NONE'
        assert verification.get_ranking_weight() == 0.0


@pytest.mark.django_db
class TestTeamGameRankingSnapshot:
    """Test TeamGameRankingSnapshot model."""
    
    def test_create_team_game_ranking_snapshot(self, team_factory):
        """Should create TeamGameRankingSnapshot with valid data."""
        team = team_factory(name='Elite Squad')
        
        snapshot = TeamGameRankingSnapshot.objects.create(
            team=team,
            game_id='OW2',
            score=1500,
            tier='GOLD',
            rank=42,
            percentile=75.5,
            verified_match_count=15,
            confidence_level='ESTABLISHED',
            breakdown={'tournament_wins': 1000, 'verified_matches': 500},
        )
        
        assert snapshot.team == team
        assert snapshot.game_id == 'OW2'
        assert snapshot.score == 1500
        assert snapshot.tier == 'GOLD'
        assert snapshot.verified_match_count == 15
    
    def test_team_game_ranking_snapshot_str(self, team_factory):
        """Should return formatted string representation."""
        team = team_factory(name='Champions')
        
        snapshot = TeamGameRankingSnapshot.objects.create(
            team=team,
            game_id='FORT',
            score=2500,
            tier='DIAMOND',
        )
        
        assert 'Champions' in str(snapshot)
        assert 'FORT' in str(snapshot)
        assert 'DIAMOND' in str(snapshot)
        assert '2500' in str(snapshot)


@pytest.mark.django_db
class TestTeamGlobalRankingSnapshot:
    """Test TeamGlobalRankingSnapshot model."""
    
    def test_create_team_global_ranking_snapshot(self, team_factory):
        """Should create TeamGlobalRankingSnapshot with valid data."""
        team = team_factory(name='Global Champions')
        
        snapshot = TeamGlobalRankingSnapshot.objects.create(
            team=team,
            global_score=5000,
            global_tier='PLATINUM',
            global_rank=10,
            games_played=3,
            game_contributions={'LOL': 2000, 'VAL': 1800, 'CS2': 1200},
        )
        
        assert snapshot.team == team
        assert snapshot.global_score == 5000
        assert snapshot.global_tier == 'PLATINUM'
        assert snapshot.games_played == 3
    
    def test_team_global_ranking_snapshot_str(self, team_factory):
        """Should return formatted string representation."""
        team = team_factory(name='Masters')
        
        snapshot = TeamGlobalRankingSnapshot.objects.create(
            team=team,
            global_score=3000,
            global_tier='GOLD',
        )
        
        assert 'Masters' in str(snapshot)
        assert 'Global' in str(snapshot)
        assert 'GOLD' in str(snapshot)
        assert '3000' in str(snapshot)

