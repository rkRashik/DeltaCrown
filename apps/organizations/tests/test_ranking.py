"""
Tests for TeamRanking and OrganizationRanking models.

Coverage:
- TeamRanking: CP updates, tier calculation, decay logic, hot streak
- OrganizationRanking: empire score calculation, aggregation

Performance: This file should run in <4 seconds.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from apps.organizations.models import TeamRanking, OrganizationRanking
from apps.organizations.choices import RankingTier
from apps.organizations.tests.factories import (
    TeamFactory,
    LegacyTeamFactory,
    TeamRankingFactory,
    OrganizationFactory,
    OrganizationRankingFactory,
)


@pytest.mark.django_db
class TestTeamRanking:
    """Test suite for TeamRanking model."""
    
    def test_create_ranking(self):
        """Test creating a team ranking record."""
        team = LegacyTeamFactory.create()
        ranking = TeamRanking.objects.create(
            team=team,
            current_cp=1000,
            season_cp=1000,
            all_time_cp=1000,
            tier=RankingTier.SILVER,
        )
        
        assert ranking.pk is not None
        assert ranking.team == team
        assert ranking.current_cp == 1000
    
    def test_one_to_one_relationship(self):
        """Test that team can only have one ranking record."""
        team = LegacyTeamFactory.create()
        TeamRankingFactory.create(team=team)
        
        # Attempting to create second ranking for same team should fail
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TeamRanking.objects.create(
                team=team,
                current_cp=500,
                season_cp=500,
                all_time_cp=500,
                tier=RankingTier.BRONZE,
            )
    
    def test_str_representation(self):
        """Test string representation of TeamRanking."""
        team = LegacyTeamFactory.create(name="Sentinels")
        ranking = TeamRankingFactory.create(
            team=team,
            current_cp=15000,
            tier=RankingTier.DIAMOND,
        )
        
        expected = "Sentinels: 15000 CP (DIAMOND)"
        assert str(ranking) == expected
    
    def test_recalculate_tier_crown(self):
        """Test tier calculation for CROWN tier (≥80,000 CP)."""
        ranking = TeamRankingFactory.create(current_cp=100000, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.CROWN
    
    def test_recalculate_tier_ascendant(self):
        """Test tier calculation for ASCENDANT tier (≥40,000 CP)."""
        ranking = TeamRankingFactory.create(current_cp=50000, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.ASCENDANT
    
    def test_recalculate_tier_diamond(self):
        """Test tier calculation for DIAMOND tier (≥15,000 CP)."""
        ranking = TeamRankingFactory.create(current_cp=20000, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.DIAMOND
    
    def test_recalculate_tier_platinum(self):
        """Test tier calculation for PLATINUM tier (≥5,000 CP)."""
        ranking = TeamRankingFactory.create(current_cp=7000, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.PLATINUM
    
    def test_recalculate_tier_gold(self):
        """Test tier calculation for GOLD tier (≥1,500 CP)."""
        ranking = TeamRankingFactory.create(current_cp=2000, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.GOLD
    
    def test_recalculate_tier_silver(self):
        """Test tier calculation for SILVER tier (≥500 CP)."""
        ranking = TeamRankingFactory.create(current_cp=800, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.SILVER
    
    def test_recalculate_tier_bronze(self):
        """Test tier calculation for BRONZE tier (≥50 CP)."""
        ranking = TeamRankingFactory.create(current_cp=100, tier=RankingTier.UNRANKED)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.BRONZE
    
    def test_recalculate_tier_unranked(self):
        """Test tier calculation for UNRANKED tier (<50 CP)."""
        ranking = TeamRankingFactory.create(current_cp=25, tier=RankingTier.BRONZE)
        
        ranking.recalculate_tier()
        
        assert ranking.tier == RankingTier.UNRANKED
    
    def test_update_cp_positive_delta(self):
        """Test updating CP with positive delta (winning points)."""
        ranking = TeamRankingFactory.create(
            current_cp=1000,
            season_cp=1000,
            all_time_cp=1000,
            tier=RankingTier.SILVER,
        )
        
        ranking.update_cp(points_delta=500, reason="Tournament Win")
        
        assert ranking.current_cp == 1500
        assert ranking.season_cp == 1500
        assert ranking.all_time_cp == 1500
        # Should recalculate tier to GOLD (≥1500 CP)
        assert ranking.tier == RankingTier.GOLD
    
    def test_update_cp_negative_delta(self):
        """Test updating CP with negative delta (losing points)."""
        ranking = TeamRankingFactory.create(
            current_cp=1000,
            season_cp=1000,
            all_time_cp=1000,
        )
        
        ranking.update_cp(points_delta=-300, reason="Match Loss")
        
        assert ranking.current_cp == 700
        assert ranking.season_cp == 700
        # all_time_cp never decreases
        assert ranking.all_time_cp == 1000
    
    def test_update_cp_prevents_negative_cp(self):
        """Test that CP cannot go below 0."""
        ranking = TeamRankingFactory.create(current_cp=100, season_cp=100, all_time_cp=100)
        
        ranking.update_cp(points_delta=-500, reason="Penalty")
        
        # CP should be capped at 0
        assert ranking.current_cp == 0
        assert ranking.season_cp == 0
    
    def test_apply_decay_inactive_team(self):
        """Test CP decay for team inactive >7 days (5% reduction)."""
        ranking = TeamRankingFactory.create(
            current_cp=1000,
            season_cp=1000,
            last_activity_date=date.today() - timedelta(days=10),  # 10 days ago
        )
        
        ranking.apply_decay()
        
        # 5% decay = 1000 * 0.95 = 950
        assert ranking.current_cp == 950
        assert ranking.season_cp == 950
        assert ranking.last_decay_applied == date.today()
    
    def test_apply_decay_active_team_no_decay(self):
        """Test that active team (within 7 days) does not get decay."""
        ranking = TeamRankingFactory.create(
            current_cp=1000,
            season_cp=1000,
            last_activity_date=date.today() - timedelta(days=3),  # 3 days ago
        )
        
        ranking.apply_decay()
        
        # No decay (still active)
        assert ranking.current_cp == 1000
        assert ranking.season_cp == 1000
    
    def test_apply_decay_boundary_exactly_7_days(self):
        """Test decay boundary at exactly 7 days (should not decay)."""
        ranking = TeamRankingFactory.create(
            current_cp=1000,
            season_cp=1000,
            last_activity_date=date.today() - timedelta(days=7),  # Exactly 7 days
        )
        
        ranking.apply_decay()
        
        # No decay at exactly 7 days (decay triggers after >7 days)
        assert ranking.current_cp == 1000
    
    def test_update_hot_streak_activates_after_3_wins(self):
        """Test that hot streak activates after 3+ wins."""
        ranking = TeamRankingFactory.create(
            is_hot_streak=False,
            streak_count=2,
        )
        
        # Third consecutive win
        ranking.update_hot_streak(won_match=True)
        
        assert ranking.streak_count == 3
        assert ranking.is_hot_streak is True
    
    def test_update_hot_streak_continues(self):
        """Test that hot streak continues on additional wins."""
        ranking = TeamRankingFactory.create(
            is_hot_streak=True,
            streak_count=5,
        )
        
        ranking.update_hot_streak(won_match=True)
        
        assert ranking.streak_count == 6
        assert ranking.is_hot_streak is True
    
    def test_update_hot_streak_breaks_on_loss(self):
        """Test that hot streak breaks on loss."""
        ranking = TeamRankingFactory.create(
            is_hot_streak=True,
            streak_count=5,
        )
        
        ranking.update_hot_streak(won_match=False)
        
        assert ranking.streak_count == 0
        assert ranking.is_hot_streak is False
    
    def test_update_hot_streak_win_before_threshold(self):
        """Test that hot streak does not activate before 3 wins."""
        ranking = TeamRankingFactory.create(
            is_hot_streak=False,
            streak_count=1,
        )
        
        ranking.update_hot_streak(won_match=True)
        
        assert ranking.streak_count == 2
        assert ranking.is_hot_streak is False  # Not yet at threshold
    
    def test_global_rank_nullable(self):
        """Test that global_rank can be null (unranked teams)."""
        ranking = TeamRankingFactory.create(global_rank=None)
        
        assert ranking.global_rank is None
    
    def test_rank_change_fields_default_zero(self):
        """Test that rank change fields default to 0."""
        ranking = TeamRankingFactory.create()
        
        assert ranking.rank_change_24h == 0
        assert ranking.rank_change_7d == 0


@pytest.mark.django_db
class TestOrganizationRanking:
    """Test suite for OrganizationRanking model."""
    
    def test_create_organization_ranking(self):
        """Test creating an organization ranking record."""
        org = OrganizationFactory.create()
        ranking = OrganizationRanking.objects.create(
            organization=org,
            empire_score=10000,
        )
        
        assert ranking.pk is not None
        assert ranking.organization == org
        assert ranking.empire_score == 10000
    
    def test_one_to_one_relationship(self):
        """Test that organization can only have one ranking record."""
        org = OrganizationFactory.create()
        OrganizationRankingFactory.create(organization=org)
        
        # Attempting to create second ranking should fail
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            OrganizationRanking.objects.create(
                organization=org,
                empire_score=5000,
            )
    
    def test_str_representation(self):
        """Test string representation of OrganizationRanking."""
        org = OrganizationFactory.create(name="Team Liquid")
        ranking = OrganizationRankingFactory.create(
            organization=org,
            empire_score=50000,
        )
        
        expected = "Team Liquid: 50000 Empire Score"
        assert str(ranking) == expected
    
    def test_recalculate_empire_score_with_teams(self):
        """Test empire score calculation from top 3 teams (weights: 1.0, 0.75, 0.5)."""
        org = OrganizationFactory.create()
        ranking = OrganizationRankingFactory.create(organization=org, empire_score=0)
        
        # Create teams with rankings (top 3 teams by CP)
        team1 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team1, current_cp=10000)  # Best team
        
        team2 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team2, current_cp=8000)  # Second best
        
        team3 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team3, current_cp=6000)  # Third best
        
        # Create fourth team (should not count)
        team4 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team4, current_cp=4000)
        
        ranking.recalculate_empire_score()
        
        # Empire Score = 10000*1.0 + 8000*0.75 + 6000*0.5 = 10000 + 6000 + 3000 = 19000
        assert ranking.empire_score == 19000
    
    def test_recalculate_empire_score_with_less_than_3_teams(self):
        """Test empire score calculation with only 2 teams."""
        org = OrganizationFactory.create()
        ranking = OrganizationRankingFactory.create(organization=org, empire_score=0)
        
        team1 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team1, current_cp=10000)
        
        team2 = TeamFactory.create(organization=org, owner=None)
        TeamRankingFactory.create(team=team2, current_cp=5000)
        
        ranking.recalculate_empire_score()
        
        # Empire Score = 10000*1.0 + 5000*0.75 = 10000 + 3750 = 13750
        assert ranking.empire_score == 13750
    
    def test_recalculate_empire_score_with_no_teams(self):
        """Test empire score calculation with no teams (should be 0)."""
        org = OrganizationFactory.create()
        ranking = OrganizationRankingFactory.create(organization=org, empire_score=5000)
        
        # No teams created
        ranking.recalculate_empire_score()
        
        assert ranking.empire_score == 0
    
    def test_recalculate_empire_score_ignores_temporary_teams(self):
        """Test that temporary teams are excluded from empire score."""
        org = OrganizationFactory.create()
        ranking = OrganizationRankingFactory.create(organization=org, empire_score=0)
        
        # Create permanent team
        team1 = TeamFactory.create(organization=org, owner=None, is_temporary=False)
        TeamRankingFactory.create(team=team1, current_cp=10000)
        
        # Create temporary team (should not count)
        team2 = TeamFactory.create(organization=org, owner=None, is_temporary=True)
        TeamRankingFactory.create(team=team2, current_cp=20000)
        
        ranking.recalculate_empire_score()
        
        # Only team1 should count
        assert ranking.empire_score == 10000
    
    def test_recalculate_empire_score_ignores_inactive_teams(self):
        """Test that non-ACTIVE teams are excluded from empire score."""
        from apps.organizations.choices import TeamStatus
        
        org = OrganizationFactory.create()
        ranking = OrganizationRankingFactory.create(organization=org, empire_score=0)
        
        # Create ACTIVE team
        team1 = TeamFactory.create(organization=org, owner=None, status=TeamStatus.ACTIVE)
        TeamRankingFactory.create(team=team1, current_cp=10000)
        
        # Create SUSPENDED team (should not count)
        team2 = TeamFactory.create(organization=org, owner=None, status=TeamStatus.SUSPENDED)
        TeamRankingFactory.create(team=team2, current_cp=20000)
        
        ranking.recalculate_empire_score()
        
        # Only team1 should count
        assert ranking.empire_score == 10000
    
    def test_global_rank_nullable(self):
        """Test that global_rank can be null."""
        ranking = OrganizationRankingFactory.create(global_rank=None)
        
        assert ranking.global_rank is None
    
    def test_total_trophies_defaults_to_zero(self):
        """Test that total_trophies defaults to 0."""
        ranking = OrganizationRankingFactory.create()
        
        assert ranking.total_trophies == 0
    
    def test_last_calculated_timestamp(self):
        """Test that last_calculated timestamp is set."""
        ranking = OrganizationRankingFactory.create()
        
        assert ranking.last_calculated is not None
