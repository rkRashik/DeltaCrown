"""
Tests for BracketEditorService (Epic 3.3)

Covers:
- swap_participants() - swap two matches
- move_participant() - move participant between matches
- remove_participant() - create bye in match
- repair_bracket() - fix integrity issues
- validate_bracket() - detect errors/warnings
- Audit logging - verify BracketEditLog records

Test count: 15 tests
"""

import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import (
    Game,
    Tournament,
    Match,
    TournamentStage,
    BracketEditLog,
)
from apps.teams.models import Team
from apps.tournaments.services.bracket_editor_service import (
    BracketEditorService,
    ValidationResult,
)

User = get_user_model()


@pytest.mark.django_db
class TestBracketEditorService:
    """Test suite for Epic 3.3 Bracket Editor Service."""
    
    @pytest.fixture
    def game(self):
        """Create test game."""
        return Game.objects.create(
            name="Test Game",
            slug="test-game",
        )
    
    @pytest.fixture
    def organizer(self):
        """Create test organizer."""
        return User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="pass123"
        )
    
    @pytest.fixture
    def tournament(self, game, organizer):
        """Create test tournament."""
        return Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=8,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=8),
        )
    
    @pytest.fixture
    def stage(self, tournament):
        """Create test tournament stage."""
        return TournamentStage.objects.create(
            tournament=tournament,
            name="Playoffs",
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            order=1,
            start_date=timezone.now(),
        )
    
    @pytest.fixture
    def teams(self):
        """Create 8 test teams."""
        teams = []
        for i in range(1, 9):
            team = Team.objects.create(
                name=f"Team {i}",
                tag=f"T{i}",
            )
            teams.append(team)
        return teams
    
    @pytest.fixture
    def matches(self, tournament, stage, teams):
        """
        Create test bracket (Single Elimination, 8 teams).
        
        Round 1 (Quarterfinals):
            Match 1: Team 1 vs Team 2
            Match 2: Team 3 vs Team 4
            Match 3: Team 5 vs Team 6
            Match 4: Team 7 vs Team 8
        
        Round 2 (Semifinals):
            Match 5: Winner of 1 vs Winner of 2 (empty)
            Match 6: Winner of 3 vs Winner of 4 (empty)
        
        Round 3 (Finals):
            Match 7: Winner of 5 vs Winner of 6 (empty)
        """
        matches = []
        
        # Round 1 (Quarterfinals)
        for i in range(4):
            match = Match.objects.create(
                tournament=tournament,
                round_number=1,
                match_number=i + 1,
                participant1_id=teams[i * 2].id,
                participant1_name=teams[i * 2].name,
                participant2_id=teams[i * 2 + 1].id,
                participant2_name=teams[i * 2 + 1].name,
                state=Match.SCHEDULED,
                lobby_info={"stage_id": stage.id},
            )
            matches.append(match)
        
        # Round 2 (Semifinals) - empty
        for i in range(2):
            match = Match.objects.create(
                tournament=tournament,
                round_number=2,
                match_number=i + 1,
                participant1_id=None,
                participant1_name="",
                participant2_id=None,
                participant2_name="",
                state=Match.SCHEDULED,
                lobby_info={"stage_id": stage.id},
            )
            matches.append(match)
        
        # Round 3 (Finals) - empty
        match = Match.objects.create(
            tournament=tournament,
            round_number=3,
            match_number=1,
            participant1_id=None,
            participant1_name="",
            participant2_id=None,
            participant2_name="",
            state=Match.SCHEDULED,
            lobby_info={"stage_id": stage.id},
        )
        matches.append(match)
        
        return matches
    
    # -------------------------------------------------------------------------
    # swap_participants() tests
    # -------------------------------------------------------------------------
    
    def test_swap_participants_success(self, matches, teams):
        """Test successful participant swap between two matches."""
        match1 = matches[0]  # Team 1 vs Team 2
        match2 = matches[1]  # Team 3 vs Team 4
        
        # Verify initial state
        assert match1.participant1_id == teams[0].id
        assert match1.participant2_id == teams[1].id
        assert match2.participant1_id == teams[2].id
        assert match2.participant2_id == teams[3].id
        
        # Swap
        BracketEditorService.swap_participants(match1.id, match2.id)
        
        # Verify swap
        match1.refresh_from_db()
        match2.refresh_from_db()
        
        assert match1.participant1_id == teams[2].id  # Team 3
        assert match1.participant2_id == teams[3].id  # Team 4
        assert match2.participant1_id == teams[0].id  # Team 1
        assert match2.participant2_id == teams[1].id  # Team 2
        
        # Verify names swapped too
        assert match1.participant1_name == teams[2].name
        assert match1.participant2_name == teams[3].name
        assert match2.participant1_name == teams[0].name
        assert match2.participant2_name == teams[1].name
    
    def test_swap_participants_creates_audit_log(self, matches, stage):
        """Test swap operation creates audit log entry."""
        match1 = matches[0]
        match2 = matches[1]
        
        # Clear any existing logs
        BracketEditLog.objects.all().delete()
        
        BracketEditorService.swap_participants(match1.id, match2.id)
        
        # Verify audit log
        logs = BracketEditLog.objects.filter(operation="swap")
        assert logs.count() == 1
        
        log = logs.first()
        assert log.stage_id == stage.id
        assert log.operation == "swap"
        assert set(log.match_ids) == {match1.id, match2.id}
        assert "match1_participants" in log.old_data
        assert "match2_participants" in log.old_data
    
    def test_swap_participants_rejects_completed_match(self, matches, teams):
        """Test cannot swap if either match is completed."""
        match1 = matches[0]
        match2 = matches[1]
        
        # Mark match1 as completed (need winner/loser for constraint)
        match1.state = Match.COMPLETED
        match1.winner_id = teams[0].id
        match1.loser_id = teams[1].id
        match1.save()
        
        with pytest.raises(ValidationError, match="Cannot swap participants in completed matches"):
            BracketEditorService.swap_participants(match1.id, match2.id)
    
    def test_swap_participants_rejects_live_match(self, matches):
        """Test cannot swap if either match is live."""
        match1 = matches[0]
        match2 = matches[1]
        
        # Mark match2 as live
        match2.state = Match.LIVE
        match2.save()
        
        with pytest.raises(ValidationError, match="Cannot swap participants in live matches"):
            BracketEditorService.swap_participants(match1.id, match2.id)
    
    # -------------------------------------------------------------------------
    # move_participant() tests
    # -------------------------------------------------------------------------
    
    def test_move_participant_to_empty_slot(self, matches, teams):
        """Test moving participant from one match to another (empty slot)."""
        match1 = matches[0]  # Team 1 vs Team 2
        match5 = matches[4]  # Empty semifinal
        
        # Move Team 1 from match1 to match5
        BracketEditorService.move_participant(
            participant_id=teams[0].id,
            from_match_id=match1.id,
            to_match_id=match5.id,
            slot=1,
        )
        
        # Verify move
        match1.refresh_from_db()
        match5.refresh_from_db()
        
        assert match1.participant1_id is None  # Removed from match1
        assert match1.participant1_name == ""
        assert match1.participant2_id == teams[1].id  # Team 2 still there
        
        assert match5.participant1_id == teams[0].id  # Team 1 moved to match5
        assert match5.participant1_name == teams[0].name
    
    def test_move_participant_auto_slot(self, matches, teams):
        """Test moving participant with auto slot selection."""
        match1 = matches[0]
        match5 = matches[4]
        
        # Move without specifying slot (should use first available)
        BracketEditorService.move_participant(
            participant_id=teams[0].id,
            from_match_id=match1.id,
            to_match_id=match5.id,
            slot=None,  # Auto-select
        )
        
        match5.refresh_from_db()
        assert match5.participant1_id == teams[0].id
    
    def test_move_participant_replaces_existing(self, matches, teams):
        """Test moving participant to occupied slot replaces it."""
        match1 = matches[0]  # Team 1 vs Team 2
        match2 = matches[1]  # Team 3 vs Team 4
        
        # Move Team 1 to match2 slot 1 (replacing Team 3)
        BracketEditorService.move_participant(
            participant_id=teams[0].id,
            from_match_id=match1.id,
            to_match_id=match2.id,
            slot=1,
        )
        
        match1.refresh_from_db()
        match2.refresh_from_db()
        
        assert match1.participant1_id is None  # Team 1 removed
        assert match2.participant1_id == teams[0].id  # Team 1 replaced Team 3
        assert match2.participant2_id == teams[3].id  # Team 4 still there
    
    def test_move_participant_not_found(self, matches, teams):
        """Test error when participant not in source match."""
        match1 = matches[0]
        match5 = matches[4]
        
        with pytest.raises(ValidationError, match="Participant .* not found in match"):
            BracketEditorService.move_participant(
                participant_id=teams[5].id,  # Team 6 not in match1
                from_match_id=match1.id,
                to_match_id=match5.id,
            )
    
    def test_move_participant_no_available_slot(self, matches, teams):
        """Test error when target match has no available slots."""
        match1 = matches[0]  # Team 1 vs Team 2
        match2 = matches[1]  # Team 3 vs Team 4 (both slots full)
        
        with pytest.raises(ValidationError, match="No available slots"):
            BracketEditorService.move_participant(
                participant_id=teams[0].id,
                from_match_id=match1.id,
                to_match_id=match2.id,
                slot=None,  # Auto-select fails
            )
    
    # -------------------------------------------------------------------------
    # remove_participant() tests
    # -------------------------------------------------------------------------
    
    def test_remove_participant_creates_bye(self, matches, teams):
        """Test removing participant creates bye (empty slot)."""
        match1 = matches[0]  # Team 1 vs Team 2
        
        BracketEditorService.remove_participant(match1.id, teams[0].id)
        
        match1.refresh_from_db()
        assert match1.participant1_id is None  # Team 1 removed
        assert match1.participant1_name == ""
        assert match1.participant2_id == teams[1].id  # Team 2 still there
    
    def test_remove_participant_slot2(self, matches, teams):
        """Test removing participant from slot 2."""
        match1 = matches[0]
        
        BracketEditorService.remove_participant(match1.id, teams[1].id)
        
        match1.refresh_from_db()
        assert match1.participant1_id == teams[0].id  # Team 1 still there
        assert match1.participant2_id is None  # Team 2 removed
        assert match1.participant2_name == ""
    
    def test_remove_participant_not_found(self, matches, teams):
        """Test error when participant not in match."""
        match1 = matches[0]
        
        with pytest.raises(ValidationError, match="Participant .* not found"):
            BracketEditorService.remove_participant(match1.id, teams[5].id)
    
    # -------------------------------------------------------------------------
    # repair_bracket() tests
    # -------------------------------------------------------------------------
    
    def test_repair_bracket_cancels_empty_matches(self, tournament, stage, matches):
        """Test repair cancels matches with both slots empty."""
        match5 = matches[4]  # Empty semifinal
        match6 = matches[5]  # Empty semifinal
        
        assert match5.state == Match.SCHEDULED
        assert match6.state == Match.SCHEDULED
        
        # Repair bracket
        result = BracketEditorService.repair_bracket(stage.id)
        
        # Verify empty matches cancelled
        match5.refresh_from_db()
        match6.refresh_from_db()
        
        assert match5.state == Match.CANCELLED
        assert match6.state == Match.CANCELLED
        assert result["cancelled_empty_matches"] == 3  # matches 5, 6, 7
    
    # -------------------------------------------------------------------------
    # validate_bracket() tests
    # -------------------------------------------------------------------------
    
    def test_validate_bracket_detects_empty_match_error(self, stage, matches):
        """Test validation detects uncancelled empty matches."""
        result = BracketEditorService.validate_bracket(stage.id)
        
        assert not result.is_valid
        assert len(result.errors) == 3  # Matches 5, 6, 7 are empty
        assert "has no participants and is not cancelled" in result.errors[0]
    
    def test_validate_bracket_detects_duplicate_participant(self, tournament, stage, teams):
        """Test validation detects duplicate participant in same round."""
        # Create TWO matches in round 1 with Team 1 in both
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=10,
            participant1_id=teams[0].id,
            participant1_name=teams[0].name,
            participant2_id=teams[2].id,
            participant2_name=teams[2].name,
            state=Match.SCHEDULED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Second match ALSO with Team 1 (duplicate!)
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=11,
            participant1_id=teams[0].id,  # Duplicate Team 1
            participant1_name=teams[0].name,
            participant2_id=teams[3].id,
            participant2_name=teams[3].name,
            state=Match.SCHEDULED,
            lobby_info={"stage_id": stage.id},
        )
        
        result = BracketEditorService.validate_bracket(stage.id)
        
        assert not result.is_valid
        assert any(f"Participant {teams[0].id}" in err and "appears multiple times" in err for err in result.errors)
    
    def test_validate_bracket_success_after_repair(self, stage, matches):
        """Test validation passes after repairing bracket."""
        # Repair empty matches
        BracketEditorService.repair_bracket(stage.id)
        
        # Validate
        result = BracketEditorService.validate_bracket(stage.id)
        
        # Should have warnings but no errors (empty matches now cancelled)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_bracket_warns_incomplete_early_rounds(self, tournament, stage, teams):
        """Test validation warns about incomplete early rounds when later rounds complete."""
        # Create match in round 1 (pending)
        match1 = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant1_name=teams[0].name,
            participant2_id=teams[1].id,
            participant2_name=teams[1].name,
            state=Match.SCHEDULED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Create match in round 2 (completed)
        match2 = Match.objects.create(
            tournament=tournament,
            round_number=2,
            match_number=1,
            participant1_id=teams[2].id,
            participant1_name=teams[2].name,
            participant2_id=teams[3].id,
            participant2_name=teams[3].name,
            state=Match.COMPLETED,
            winner_id=teams[2].id,
            loser_id=teams[3].id,
            lobby_info={"stage_id": stage.id},
        )
        
        result = BracketEditorService.validate_bracket(stage.id)
        
        # Should warn about incomplete match in earlier round
        assert len(result.warnings) > 0
        assert any("is incomplete" in warn and "has completed matches" in warn for warn in result.warnings)


@pytest.mark.django_db
class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization to dict."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
        )
        
        data = result.to_dict()
        
        assert data == {
            "is_valid": False,
            "errors": ["Error 1", "Error 2"],
            "warnings": ["Warning 1"],
        }
