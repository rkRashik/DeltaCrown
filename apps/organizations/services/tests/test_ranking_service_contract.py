"""
Test RankingService contract stability (method signatures, DTOs, NotImplementedError behavior).

These tests lock down the RankingService API contract without testing business logic.
All methods should raise NotImplementedError until P2-T5.
"""

import inspect
import pytest
from typing import Optional, List, Tuple, Dict
from dataclasses import is_dataclass

from apps.organizations.services import (
    RankingService,
    RankingSnapshot,
    MatchResultDelta,
)


class TestRankingServiceMethodSignatures:
    """Verify RankingService methods exist with correct signatures."""
    
    def test_calculate_tier_signature(self):
        """calculate_tier must have signature: (crown_points: int) -> str"""
        sig = inspect.signature(RankingService.calculate_tier)
        
        params = sig.parameters
        assert "crown_points" in params
        assert params["crown_points"].annotation == int
        assert sig.return_annotation == str
    
    def test_calculate_cp_delta_signature(self):
        """calculate_cp_delta must return Tuple[int, int]."""
        sig = inspect.signature(RankingService.calculate_cp_delta)
        
        params = sig.parameters
        assert "winner_tier" in params
        assert params["winner_tier"].annotation == str
        
        assert "loser_tier" in params
        assert params["loser_tier"].annotation == str
        
        assert sig.return_annotation == Tuple[int, int]
    
    def test_apply_match_result_signature(self):
        """apply_match_result must have winner/loser team IDs and keyword-only params."""
        sig = inspect.signature(RankingService.apply_match_result)
        
        params = sig.parameters
        assert "winner_team_id" in params
        assert params["winner_team_id"].annotation == int
        
        assert "loser_team_id" in params
        assert params["loser_team_id"].annotation == int
        
        assert "match_id" in params
        assert params["match_id"].kind == inspect.Parameter.KEYWORD_ONLY
        
        assert "is_tournament_match" in params
        assert params["is_tournament_match"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["is_tournament_match"].default is False
        
        assert sig.return_annotation == MatchResultDelta
    
    def test_recompute_team_ranking_signature(self):
        """recompute_team_ranking must have signature: (team_id: int) -> RankingSnapshot"""
        sig = inspect.signature(RankingService.recompute_team_ranking)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        assert sig.return_annotation == RankingSnapshot
    
    def test_recompute_organization_ranking_signature(self):
        """recompute_organization_ranking must have signature: (organization_id: int) -> RankingSnapshot"""
        sig = inspect.signature(RankingService.recompute_organization_ranking)
        
        params = sig.parameters
        assert "organization_id" in params
        assert params["organization_id"].annotation == int
        assert sig.return_annotation == RankingSnapshot
    
    def test_get_team_ranking_signature(self):
        """get_team_ranking must have signature: (team_id: int) -> RankingSnapshot"""
        sig = inspect.signature(RankingService.get_team_ranking)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        assert sig.return_annotation == RankingSnapshot
    
    def test_get_organization_ranking_signature(self):
        """get_organization_ranking must have signature: (organization_id: int) -> RankingSnapshot"""
        sig = inspect.signature(RankingService.get_organization_ranking)
        
        params = sig.parameters
        assert "organization_id" in params
        assert params["organization_id"].annotation == int
        assert sig.return_annotation == RankingSnapshot
    
    def test_get_leaderboard_signature(self):
        """get_leaderboard must have keyword-only parameters."""
        sig = inspect.signature(RankingService.get_leaderboard)
        
        params = sig.parameters
        
        assert "entity_type" in params
        assert params["entity_type"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["entity_type"].default == "TEAM"
        
        assert "game_id" in params
        assert params["game_id"].kind == inspect.Parameter.KEYWORD_ONLY
        
        assert "region" in params
        assert params["region"].kind == inspect.Parameter.KEYWORD_ONLY
        
        assert "limit" in params
        assert params["limit"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["limit"].default == 100
        
        assert sig.return_annotation == List[RankingSnapshot]


class TestRankingServiceNotImplementedBehavior:
    """Verify all methods raise NotImplementedError until business logic is implemented."""
    
    def test_calculate_tier_raises_not_implemented(self):
        """calculate_tier must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.calculate_tier(crown_points=5000)
    
    def test_calculate_cp_delta_raises_not_implemented(self):
        """calculate_cp_delta must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.calculate_cp_delta(winner_tier="GOLD", loser_tier="SILVER")
    
    def test_apply_match_result_raises_not_implemented(self):
        """apply_match_result must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.apply_match_result(
                winner_team_id=42,
                loser_team_id=99,
                match_id=12345,
                is_tournament_match=True
            )
    
    def test_recompute_team_ranking_raises_not_implemented(self):
        """recompute_team_ranking must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.recompute_team_ranking(team_id=42)
    
    def test_recompute_organization_ranking_raises_not_implemented(self):
        """recompute_organization_ranking must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.recompute_organization_ranking(organization_id=42)
    
    def test_get_team_ranking_raises_not_implemented(self):
        """get_team_ranking must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.get_team_ranking(team_id=42)
    
    def test_get_organization_ranking_raises_not_implemented(self):
        """get_organization_ranking must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.get_organization_ranking(organization_id=42)
    
    def test_get_leaderboard_raises_not_implemented(self):
        """get_leaderboard must raise NotImplementedError until P2-T5."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            RankingService.get_leaderboard(
                entity_type="TEAM",
                game_id=1,
                region="BD",
                limit=50
            )


class TestRankingSnapshotDTO:
    """Verify RankingSnapshot DTO structure."""
    
    def test_ranking_snapshot_is_dataclass(self):
        """RankingSnapshot must be a dataclass."""
        assert is_dataclass(RankingSnapshot)
    
    def test_ranking_snapshot_required_fields(self):
        """RankingSnapshot must have all required fields."""
        required_fields = [
            "entity_id",
            "entity_type",
            "crown_points",
            "tier",
            "rank_position",
            "percentile",
            "matches_played",
            "win_rate",
            "last_match_date",
        ]
        annotations = RankingSnapshot.__annotations__
        
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"
    
    def test_ranking_snapshot_entity_type_is_string(self):
        """RankingSnapshot.entity_type must be str type."""
        annotations = RankingSnapshot.__annotations__
        assert annotations["entity_type"] == str
    
    def test_ranking_snapshot_tier_is_string(self):
        """RankingSnapshot.tier must be str type."""
        annotations = RankingSnapshot.__annotations__
        assert annotations["tier"] == str


class TestMatchResultDeltaDTO:
    """Verify MatchResultDelta DTO structure."""
    
    def test_match_result_delta_is_dataclass(self):
        """MatchResultDelta must be a dataclass."""
        assert is_dataclass(MatchResultDelta)
    
    def test_match_result_delta_required_fields(self):
        """MatchResultDelta must have all CP change fields."""
        required_fields = [
            "winner_cp_gain",
            "loser_cp_loss",
            "winner_new_tier",
            "loser_new_tier",
            "winner_tier_changed",
            "loser_tier_changed",
        ]
        annotations = MatchResultDelta.__annotations__
        
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"
    
    def test_match_result_delta_cp_fields_are_int(self):
        """MatchResultDelta CP fields must be int type."""
        annotations = MatchResultDelta.__annotations__
        assert annotations["winner_cp_gain"] == int
        assert annotations["loser_cp_loss"] == int
    
    def test_match_result_delta_tier_changed_are_bool(self):
        """MatchResultDelta tier_changed fields must be bool type."""
        annotations = MatchResultDelta.__annotations__
        assert annotations["winner_tier_changed"] == bool
        assert annotations["loser_tier_changed"] == bool


class TestRankingServiceDTOImportability:
    """Verify all DTOs are importable from service root."""
    
    def test_all_dtos_importable(self):
        """All RankingService DTOs must be importable from apps.organizations.services."""
        from apps.organizations.services import (
            RankingSnapshot,
            MatchResultDelta,
        )
        
        # Verify they are all dataclasses
        assert is_dataclass(RankingSnapshot)
        assert is_dataclass(MatchResultDelta)
