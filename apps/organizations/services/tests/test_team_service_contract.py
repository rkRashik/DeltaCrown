"""
Test TeamService contract stability (method signatures, DTOs, NotImplementedError behavior).

These tests lock down the TeamService API contract without testing business logic.
All methods should raise NotImplementedError until P2-T3.
"""

import inspect
import pytest
from typing import Optional, List
from dataclasses import is_dataclass

from apps.organizations.services import (
    TeamService,
    TeamIdentity,
    WalletInfo,
    ValidationResult,
    RosterMember,
)


class TestTeamServiceMethodSignatures:
    """Verify TeamService methods exist with correct signatures."""
    
    def test_get_team_identity_signature(self):
        """get_team_identity must have signature: (team_id: int) -> TeamIdentity"""
        sig = inspect.signature(TeamService.get_team_identity)
        
        # Check parameters
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        
        # Check return type
        assert sig.return_annotation == TeamIdentity
    
    def test_get_team_wallet_signature(self):
        """get_team_wallet must have signature: (team_id: int) -> WalletInfo"""
        sig = inspect.signature(TeamService.get_team_wallet)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        assert sig.return_annotation == WalletInfo
    
    def test_validate_roster_signature(self):
        """validate_roster must have correct keyword-only parameters."""
        sig = inspect.signature(TeamService.validate_roster)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        
        # tournament_id and game_id are keyword-only Optional[int]
        assert "tournament_id" in params
        assert params["tournament_id"].kind == inspect.Parameter.KEYWORD_ONLY
        
        assert "game_id" in params
        assert params["game_id"].kind == inspect.Parameter.KEYWORD_ONLY
        
        assert sig.return_annotation == ValidationResult
    
    def test_get_authorized_managers_signature(self):
        """get_authorized_managers must return List[int]."""
        sig = inspect.signature(TeamService.get_authorized_managers)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        assert sig.return_annotation == List[int]
    
    def test_get_team_url_signature(self):
        """get_team_url must have signature: (team_id: int) -> str"""
        sig = inspect.signature(TeamService.get_team_url)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        assert sig.return_annotation == str
    
    def test_get_roster_members_signature(self):
        """get_roster_members must have status parameter with default."""
        sig = inspect.signature(TeamService.get_roster_members)
        
        params = sig.parameters
        assert "team_id" in params
        assert params["team_id"].annotation == int
        
        assert "status" in params
        assert params["status"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["status"].default == "ACTIVE"
        assert params["status"].annotation == str
        
        assert sig.return_annotation == List[RosterMember]
    
    def test_create_temporary_team_signature(self):
        """create_temporary_team must have all keyword-only parameters."""
        sig = inspect.signature(TeamService.create_temporary_team)
        
        params = sig.parameters
        
        # All parameters are keyword-only
        assert "owner_user_id" in params
        assert params["owner_user_id"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["owner_user_id"].annotation == int
        
        assert "game_id" in params
        assert params["game_id"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["game_id"].annotation == int
        
        assert "name" in params
        assert params["name"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["name"].annotation == str
        
        assert "tournament_id" in params
        assert params["tournament_id"].kind == inspect.Parameter.KEYWORD_ONLY
        
        # Return type is int (team ID)
        assert sig.return_annotation == int


class TestTeamServiceNotImplementedBehavior:
    """Verify all methods raise NotImplementedError until business logic is implemented."""
    
    def test_get_team_identity_raises_not_implemented(self):
        """get_team_identity must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.get_team_identity(team_id=42)
    
    def test_get_team_wallet_raises_not_implemented(self):
        """get_team_wallet must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.get_team_wallet(team_id=42)
    
    def test_validate_roster_raises_not_implemented(self):
        """validate_roster must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.validate_roster(team_id=42, tournament_id=100, game_id=1)
    
    def test_get_authorized_managers_raises_not_implemented(self):
        """get_authorized_managers must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.get_authorized_managers(team_id=42)
    
    def test_get_team_url_raises_not_implemented(self):
        """get_team_url must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.get_team_url(team_id=42)
    
    def test_get_roster_members_raises_not_implemented(self):
        """get_roster_members must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.get_roster_members(team_id=42, status="ACTIVE")
    
    def test_create_temporary_team_raises_not_implemented(self):
        """create_temporary_team must raise NotImplementedError until P2-T3."""
        with pytest.raises(NotImplementedError, match="Business logic will be implemented"):
            TeamService.create_temporary_team(
                owner_user_id=123,
                game_id=1,
                name="Test Team",
                tournament_id=100
            )


class TestTeamIdentityDTO:
    """Verify TeamIdentity DTO structure."""
    
    def test_team_identity_is_dataclass(self):
        """TeamIdentity must be a dataclass."""
        assert is_dataclass(TeamIdentity)
    
    def test_team_identity_required_fields(self):
        """TeamIdentity must have all required fields from Compatibility Contract."""
        required_fields = {
            "team_id": int,
            "name": str,
            "slug": str,
            "logo_url": Optional[str],
            "badge_url": Optional[str],
            "game_name": str,
            "game_id": int,
            "region": str,
            "is_verified": bool,
            "is_org_team": bool,
            "organization_name": Optional[str],
            "organization_slug": Optional[str],
        }
        
        # Get field annotations
        annotations = TeamIdentity.__annotations__
        
        # Verify all required fields present
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"


class TestWalletInfoDTO:
    """Verify WalletInfo DTO structure."""
    
    def test_wallet_info_is_dataclass(self):
        """WalletInfo must be a dataclass."""
        assert is_dataclass(WalletInfo)
    
    def test_wallet_info_required_fields(self):
        """WalletInfo must have wallet_id, owner_name, wallet_type, revenue_split."""
        required_fields = ["wallet_id", "owner_name", "wallet_type", "revenue_split"]
        annotations = WalletInfo.__annotations__
        
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"


class TestValidationResultDTO:
    """Verify ValidationResult DTO structure."""
    
    def test_validation_result_is_dataclass(self):
        """ValidationResult must be a dataclass."""
        assert is_dataclass(ValidationResult)
    
    def test_validation_result_required_fields(self):
        """ValidationResult must have is_valid, errors, warnings, roster_data."""
        required_fields = ["is_valid", "errors", "warnings", "roster_data"]
        annotations = ValidationResult.__annotations__
        
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"
    
    def test_validation_result_is_valid_is_bool(self):
        """ValidationResult.is_valid must be bool type."""
        annotations = ValidationResult.__annotations__
        assert annotations["is_valid"] == bool


class TestRosterMemberDTO:
    """Verify RosterMember DTO structure."""
    
    def test_roster_member_is_dataclass(self):
        """RosterMember must be a dataclass."""
        assert is_dataclass(RosterMember)
    
    def test_roster_member_required_fields(self):
        """RosterMember must have all roster-related fields."""
        required_fields = [
            "user_id",
            "username",
            "display_name",
            "role",
            "roster_slot",
            "status",
            "is_tournament_captain",
            "joined_date",
        ]
        annotations = RosterMember.__annotations__
        
        for field_name in required_fields:
            assert field_name in annotations, f"Missing field: {field_name}"


class TestTeamServiceDTOImportability:
    """Verify all DTOs are importable from service root."""
    
    def test_all_dtos_importable(self):
        """All TeamService DTOs must be importable from apps.organizations.services."""
        from apps.organizations.services import (
            TeamIdentity,
            WalletInfo,
            ValidationResult,
            RosterMember,
        )
        
        # Verify they are all dataclasses
        assert is_dataclass(TeamIdentity)
        assert is_dataclass(WalletInfo)
        assert is_dataclass(ValidationResult)
        assert is_dataclass(RosterMember)
