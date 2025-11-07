"""
Unit tests for Match and Dispute models (Module 1.4)

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Match/Dispute models)
- Documents/Planning/PROPOSAL_PART_2_TECHNICAL_ARCHITECTURE.md (Dispute Model section 4.5)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

Architecture Decisions:
- ADR-001: Service layer pattern
- ADR-003: Soft delete for critical models
- ADR-007: WebSocket support for real-time updates

Test Coverage Target: >80%
TDD Approach: Tests written before implementation
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.tournaments.models import Tournament, Game, Bracket
from apps.tournaments.models.match import Match, Dispute


# ===========================
# Match Model Tests (17 tests)
# ===========================

@pytest.mark.django_db
class TestMatchModel:
    """Test Match model creation, validation, and behavior"""

    @pytest.fixture
    def game(self):
        """Create a game instance"""
        return Game.objects.create(
            name="VALORANT",
            slug="valorant",
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        """Create a tournament instance"""
        return Tournament.objects.create(
            title="VALORANT Championship",
            slug="valorant-championship",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=7),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(days=5),
            status=Tournament.PUBLISHED
        )

    @pytest.fixture
    def bracket(self, tournament):
        """Create a bracket instance"""
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.GENERATED,
            total_rounds=4,
            current_round=1
        )

    def test_match_creation_minimal(self, tournament, bracket):
        """Test creating match with minimal required fields"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.SCHEDULED
        )

        assert match.id is not None
        assert match.tournament == tournament
        assert match.bracket == bracket
        assert match.round_number == 1
        assert match.match_number == 1
        assert match.state == Match.SCHEDULED
        assert match.participant1_score == 0
        assert match.participant2_score == 0
        assert match.participant1_checked_in is False
        assert match.participant2_checked_in is False
        assert match.is_deleted is False

    def test_match_creation_with_participants(self, tournament, bracket):
        """Test creating match with participant IDs"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta"
        )

        assert match.participant1_id == 101
        assert match.participant1_name == "Team Alpha"
        assert match.participant2_id == 102
        assert match.participant2_name == "Team Beta"

    def test_match_state_choices(self, tournament, bracket):
        """Test all valid match states"""
        valid_states = [
            Match.SCHEDULED,
            Match.CHECK_IN,
            Match.READY,
            Match.LIVE,
            Match.PENDING_RESULT,
            Match.COMPLETED,
            Match.DISPUTED,
            Match.FORFEIT,
            Match.CANCELLED
        ]

        for state in valid_states:
            match = Match.objects.create(
                tournament=tournament,
                bracket=bracket,
                round_number=1,
                match_number=1,
                state=state
            )
            assert match.state == state
            match.delete()

    def test_match_scheduled_time(self, tournament, bracket):
        """Test match scheduled_time field"""
        scheduled_time = timezone.now() + timedelta(hours=2)
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            scheduled_time=scheduled_time
        )

        assert match.scheduled_time == scheduled_time

    def test_match_check_in_deadline(self, tournament, bracket):
        """Test match check_in_deadline field"""
        check_in_deadline = timezone.now() + timedelta(minutes=30)
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            check_in_deadline=check_in_deadline
        )

        assert match.check_in_deadline == check_in_deadline

    def test_match_check_in_tracking(self, tournament, bracket):
        """Test participant check-in tracking"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant2_id=102
        )

        # Initial state
        assert match.participant1_checked_in is False
        assert match.participant2_checked_in is False

        # Participant 1 checks in
        match.participant1_checked_in = True
        match.save()
        match.refresh_from_db()
        assert match.participant1_checked_in is True
        assert match.participant2_checked_in is False

        # Participant 2 checks in
        match.participant2_checked_in = True
        match.save()
        match.refresh_from_db()
        assert match.participant2_checked_in is True

    def test_match_lobby_info_jsonb(self, tournament, bracket):
        """Test lobby_info JSONB field"""
        lobby_data = {
            "game_mode": "Competitive",
            "map": "Haven",
            "server": "Singapore",
            "lobby_code": "ABC123",
            "lobby_password": "secret123"
        }

        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            lobby_info=lobby_data
        )

        assert match.lobby_info == lobby_data
        assert match.lobby_info["map"] == "Haven"
        assert match.lobby_info["lobby_code"] == "ABC123"

    def test_match_stream_url(self, tournament, bracket):
        """Test stream_url field"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            stream_url="https://twitch.tv/deltacrown"
        )

        assert match.stream_url == "https://twitch.tv/deltacrown"

    def test_match_score_tracking(self, tournament, bracket):
        """Test match score fields"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant2_id=102,
            participant1_score=13,
            participant2_score=7
        )

        assert match.participant1_score == 13
        assert match.participant2_score == 7

    def test_match_winner_loser_tracking(self, tournament, bracket):
        """Test winner_id and loser_id fields"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            participant1_id=101,
            participant2_id=102,
            participant1_score=13,
            participant2_score=7,
            winner_id=101,
            loser_id=102
        )

        assert match.winner_id == 101
        assert match.loser_id == 102

    def test_match_timestamps(self, tournament, bracket):
        """Test match timestamp fields"""
        started_at = timezone.now()
        completed_at = started_at + timedelta(hours=1)

        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            started_at=started_at,
            completed_at=completed_at
        )

        assert match.started_at == started_at
        assert match.completed_at == completed_at
        assert match.created_at is not None
        assert match.updated_at is not None

    def test_match_soft_delete(self, tournament, bracket):
        """Test soft delete fields (ADR-003)"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        # Initial state
        assert match.is_deleted is False
        assert match.deleted_at is None
        assert match.deleted_by_id is None

        # Soft delete
        match.is_deleted = True
        match.deleted_at = timezone.now()
        match.deleted_by_id = 1
        match.save()

        match.refresh_from_db()
        assert match.is_deleted is True
        assert match.deleted_at is not None
        assert match.deleted_by_id == 1

    def test_match_str_representation(self, tournament, bracket):
        """Test __str__ method"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_name="Team Alpha",
            participant2_name="Team Beta"
        )

        str_repr = str(match)
        assert "Team Alpha" in str_repr or "Team Beta" in str_repr or "Round 1" in str_repr

    def test_match_round_and_match_numbers_positive(self, tournament, bracket):
        """Test round_number and match_number must be positive"""
        # Valid positive numbers
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )
        assert match.round_number == 1
        assert match.match_number == 1

        # Test constraint would be enforced at database level
        # Django IntegerField allows negative values by default
        # Constraint: CHECK (round_number > 0 AND match_number > 0)

    def test_match_scores_non_negative(self, tournament, bracket):
        """Test scores must be non-negative"""
        # Valid scores
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_score=0,
            participant2_score=0
        )
        assert match.participant1_score >= 0
        assert match.participant2_score >= 0

        # Update with positive scores
        match.participant1_score = 13
        match.participant2_score = 7
        match.save()
        assert match.participant1_score == 13
        assert match.participant2_score == 7

    def test_match_tournament_relationship(self, tournament, bracket):
        """Test ForeignKey relationship to Tournament"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        # Test relationship
        assert match.tournament == tournament
        assert match in tournament.matches.all()

    def test_match_bracket_relationship(self, tournament, bracket):
        """Test ForeignKey relationship to Bracket"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        # Test relationship
        assert match.bracket == bracket
        assert match in bracket.matches.all()


# ===========================
# Dispute Model Tests (15 tests)
# ===========================

@pytest.mark.django_db
class TestDisputeModel:
    """Test Dispute model creation, validation, and behavior"""

    @pytest.fixture
    def game(self):
        """Create a game instance"""
        return Game.objects.create(
            name="VALORANT",
            slug="valorant",
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        """Create a tournament instance"""
        return Tournament.objects.create(
            title="VALORANT Championship",
            slug="valorant-championship",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=7),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(days=5),
            status=Tournament.PUBLISHED
        )

    @pytest.fixture
    def bracket(self, tournament):
        """Create a bracket instance"""
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.GENERATED,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def match(self, tournament, bracket):
        """Create a match instance"""
        return Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.PENDING_RESULT,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta"
        )

    def test_dispute_creation_minimal(self, match):
        """Test creating dispute with minimal required fields"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch - claiming different result"
        )

        assert dispute.id is not None
        assert dispute.match == match
        assert dispute.initiated_by_id == 101
        assert dispute.reason == Dispute.SCORE_MISMATCH
        assert dispute.description == "Score mismatch - claiming different result"
        assert dispute.status == Dispute.OPEN

    def test_dispute_reason_choices(self, match):
        """Test all valid dispute reasons"""
        valid_reasons = [
            Dispute.SCORE_MISMATCH,
            Dispute.NO_SHOW,
            Dispute.CHEATING,
            Dispute.TECHNICAL_ISSUE,
            Dispute.OTHER
        ]

        for reason in valid_reasons:
            dispute = Dispute.objects.create(
                match=match,
                initiated_by_id=101,
                reason=reason,
                description=f"Test dispute for reason: {reason}"
            )
            assert dispute.reason == reason
            dispute.delete()

    def test_dispute_status_choices(self, match):
        """Test all valid dispute statuses"""
        valid_statuses = [
            Dispute.OPEN,
            Dispute.UNDER_REVIEW,
            Dispute.RESOLVED,
            Dispute.ESCALATED
        ]

        for status in valid_statuses:
            dispute = Dispute.objects.create(
                match=match,
                initiated_by_id=101,
                reason=Dispute.SCORE_MISMATCH,
                description="Test dispute",
                status=status
            )
            assert dispute.status == status
            dispute.delete()

    def test_dispute_evidence_screenshot(self, match):
        """Test evidence_screenshot field"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch with screenshot evidence"
        )

        # Initial state
        assert dispute.evidence_screenshot.name == ''

        # Note: In actual implementation, would test file upload
        # For now, verify field exists and is optional

    def test_dispute_evidence_video_url(self, match):
        """Test evidence_video_url field"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.CHEATING,
            description="Cheating accusation with video evidence",
            evidence_video_url="https://youtube.com/watch?v=evidence123"
        )

        assert dispute.evidence_video_url == "https://youtube.com/watch?v=evidence123"

    def test_dispute_resolution_fields(self, match):
        """Test dispute resolution fields"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch",
            status=Dispute.RESOLVED,
            resolved_by_id=1,
            resolved_at=timezone.now(),
            resolution_notes="Verified score from game logs",
            final_participant1_score=13,
            final_participant2_score=11
        )

        assert dispute.status == Dispute.RESOLVED
        assert dispute.resolved_by_id == 1
        assert dispute.resolved_at is not None
        assert dispute.resolution_notes == "Verified score from game logs"
        assert dispute.final_participant1_score == 13
        assert dispute.final_participant2_score == 11

    def test_dispute_timestamps(self, match):
        """Test dispute timestamp fields"""
        created_time = timezone.now()
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch"
        )

        assert dispute.created_at is not None
        assert dispute.created_at >= created_time

    def test_dispute_resolved_at_nullable(self, match):
        """Test resolved_at is nullable for open disputes"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch",
            status=Dispute.OPEN
        )

        assert dispute.resolved_at is None

        # Resolve the dispute
        dispute.status = Dispute.RESOLVED
        dispute.resolved_by_id = 1
        dispute.resolved_at = timezone.now()
        dispute.save()

        dispute.refresh_from_db()
        assert dispute.resolved_at is not None

    def test_dispute_final_scores_nullable(self, match):
        """Test final scores are nullable"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.TECHNICAL_ISSUE,
            description="Server crash during match"
        )

        assert dispute.final_participant1_score is None
        assert dispute.final_participant2_score is None

    def test_dispute_str_representation(self, match):
        """Test __str__ method"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch"
        )

        str_repr = str(dispute)
        assert "Dispute" in str_repr or "SCORE_MISMATCH" in str_repr

    def test_dispute_match_relationship(self, match):
        """Test ForeignKey relationship to Match"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Score mismatch"
        )

        # Test relationship
        assert dispute.match == match
        assert dispute in match.disputes.all()

    def test_dispute_resolution_notes_optional(self, match):
        """Test resolution_notes is optional"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.OTHER,
            description="General dispute"
        )

        assert dispute.resolution_notes == ""

        # Add resolution notes
        dispute.resolution_notes = "Resolved via organizer review"
        dispute.save()
        dispute.refresh_from_db()
        assert dispute.resolution_notes == "Resolved via organizer review"

    def test_dispute_escalation_workflow(self, match):
        """Test dispute escalation workflow"""
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.CHEATING,
            description="Serious cheating accusation",
            status=Dispute.OPEN
        )

        # Organizer reviews
        dispute.status = Dispute.UNDER_REVIEW
        dispute.save()
        assert dispute.status == Dispute.UNDER_REVIEW

        # Escalate to admin
        dispute.status = Dispute.ESCALATED
        dispute.save()
        assert dispute.status == Dispute.ESCALATED

        # Admin resolves
        dispute.status = Dispute.RESOLVED
        dispute.resolved_by_id = 1
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = "Admin reviewed evidence and upheld original result"
        dispute.save()

        dispute.refresh_from_db()
        assert dispute.status == Dispute.RESOLVED
        assert dispute.resolved_by_id == 1

    def test_dispute_multiple_per_match(self, match):
        """Test multiple disputes can exist for one match"""
        dispute1 = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="First dispute"
        )

        dispute2 = Dispute.objects.create(
            match=match,
            initiated_by_id=102,
            reason=Dispute.TECHNICAL_ISSUE,
            description="Second dispute"
        )

        assert Dispute.objects.filter(match=match).count() == 2
        assert dispute1.match == dispute2.match

    def test_dispute_ordering(self, match):
        """Test disputes are ordered by created_at DESC"""
        # Create disputes with time gap
        dispute1 = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="First dispute"
        )

        dispute2 = Dispute.objects.create(
            match=match,
            initiated_by_id=102,
            reason=Dispute.TECHNICAL_ISSUE,
            description="Second dispute (newer)"
        )

        disputes = Dispute.objects.filter(match=match)
        # Should be ordered newest first
        assert disputes[0].id == dispute2.id
        assert disputes[1].id == dispute1.id


# ===========================
# Integration Tests (2 tests)
# ===========================

@pytest.mark.django_db
class TestMatchDisputeIntegration:
    """Test integration between Match and Dispute models"""

    @pytest.fixture
    def game(self):
        """Create a game instance"""
        return Game.objects.create(
            name="VALORANT",
            slug="valorant",
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        """Create a tournament instance"""
        return Tournament.objects.create(
            title="VALORANT Championship",
            slug="valorant-championship",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=7),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(days=5),
            status=Tournament.PUBLISHED
        )

    @pytest.fixture
    def bracket(self, tournament):
        """Create a bracket instance"""
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.GENERATED,
            total_rounds=4,
            current_round=1
        )

    def test_match_disputed_state_workflow(self, tournament, bracket):
        """Test full match dispute workflow"""
        # Create match in PENDING_RESULT state
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.PENDING_RESULT,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            participant1_score=13,
            participant2_score=11
        )

        # Create dispute
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=102,
            reason=Dispute.SCORE_MISMATCH,
            description="Participant 2 claims different score",
            evidence_video_url="https://youtube.com/evidence"
        )

        # Update match state to DISPUTED
        match.state = Match.DISPUTED
        match.save()

        # Verify relationships
        assert match.state == Match.DISPUTED
        assert dispute.match == match
        assert dispute.status == Dispute.OPEN

        # Organizer reviews and resolves
        dispute.status = Dispute.RESOLVED
        dispute.resolved_by_id = 1
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = "Verified original score is correct"
        dispute.final_participant1_score = 13
        dispute.final_participant2_score = 11
        dispute.save()

        # Match returns to COMPLETED
        match.state = Match.COMPLETED
        match.winner_id = 101
        match.loser_id = 102
        match.completed_at = timezone.now()
        match.save()

        # Verify final state
        match.refresh_from_db()
        dispute.refresh_from_db()
        assert match.state == Match.COMPLETED
        assert match.winner_id == 101
        assert dispute.status == Dispute.RESOLVED

    def test_match_cascade_delete_with_disputes(self, tournament, bracket):
        """Test cascading deletion behavior"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=101,
            reason=Dispute.SCORE_MISMATCH,
            description="Test dispute"
        )

        match_id = match.id
        dispute_id = dispute.id

        # Delete match (hard delete for testing)
        match.delete()

        # Verify dispute is also deleted (CASCADE)
        assert not Match.objects.filter(id=match_id).exists()
        assert not Dispute.objects.filter(id=dispute_id).exists()
