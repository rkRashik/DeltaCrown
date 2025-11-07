"""
Integration tests for MatchService (Module 1.4)

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: MatchService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Match workflows)

Test Coverage:
- Match creation and participant pairing
- Check-in workflow
- State transitions (SCHEDULED → LIVE → COMPLETED)
- Result submission and confirmation
- Dispute creation and resolution
- Forfeit and cancellation
- Match statistics

Target: >80% coverage
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.tournaments.models import (
    Tournament,
    Game,
    Bracket,
    Match,
    Dispute,
    Registration
)
from apps.tournaments.services.match_service import MatchService


@pytest.mark.django_db
class TestMatchServiceCreation:
    """Test match creation workflows"""

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
            status=Tournament.PUBLISHED,
            enable_check_in=True
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

    def test_create_match_minimal(self, tournament, bracket):
        """Test creating match with minimal required fields"""
        match = MatchService.create_match(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        assert match.id is not None
        assert match.tournament == tournament
        assert match.bracket == bracket
        assert match.round_number == 1
        assert match.match_number == 1
        assert match.state == Match.READY  # No scheduled_time, so READY

    def test_create_match_with_participants(self, tournament, bracket):
        """Test creating match with participants"""
        scheduled_time = timezone.now() + timedelta(hours=2)
        
        match = MatchService.create_match(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            scheduled_time=scheduled_time
        )

        assert match.participant1_id == 101
        assert match.participant1_name == "Team Alpha"
        assert match.participant2_id == 102
        assert match.participant2_name == "Team Beta"
        assert match.state == Match.SCHEDULED
        assert match.check_in_deadline is not None

    def test_create_match_duplicate_validation(self, tournament, bracket):
        """Test duplicate match validation"""
        MatchService.create_match(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1
        )

        with pytest.raises(ValidationError, match="already exists"):
            MatchService.create_match(
                tournament=tournament,
                bracket=bracket,
                round_number=1,
                match_number=1
            )

    def test_create_match_invalid_round_number(self, tournament, bracket):
        """Test invalid round number validation"""
        with pytest.raises(ValidationError, match="at least 1"):
            MatchService.create_match(
                tournament=tournament,
                bracket=bracket,
                round_number=0,
                match_number=1
            )


@pytest.mark.django_db
class TestMatchServiceCheckIn:
    """Test check-in workflow"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=1),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(hours=12),
            status=Tournament.PUBLISHED,
            enable_check_in=True
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.GENERATED,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def match(self, tournament, bracket):
        return MatchService.create_match(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            scheduled_time=timezone.now() + timedelta(hours=2)
        )

    def test_check_in_participant1(self, match):
        """Test participant 1 check-in"""
        updated_match = MatchService.check_in_participant(
            match=match,
            participant_id=101
        )

        assert updated_match.participant1_checked_in is True
        assert updated_match.participant2_checked_in is False
        assert updated_match.state == Match.CHECK_IN

    def test_check_in_both_participants(self, match):
        """Test both participants check in"""
        MatchService.check_in_participant(match, 101)
        updated_match = MatchService.check_in_participant(match, 102)

        assert updated_match.participant1_checked_in is True
        assert updated_match.participant2_checked_in is True
        assert updated_match.state == Match.READY

    def test_check_in_invalid_participant(self, match):
        """Test check-in with invalid participant ID"""
        with pytest.raises(ValidationError, match="not in this match"):
            MatchService.check_in_participant(match, 999)


@pytest.mark.django_db
class TestMatchServiceStateTransitions:
    """Test match state transitions"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now(),
            registration_opens_at=timezone.now() - timedelta(days=5),
            registration_closes_at=timezone.now() - timedelta(days=1),
            status=Tournament.LIVE
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.IN_PROGRESS,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def ready_match(self, tournament, bracket):
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            state=Match.READY,
            participant1_checked_in=True,
            participant2_checked_in=True
        )
        return match

    def test_transition_to_live(self, ready_match):
        """Test transitioning match to LIVE state"""
        updated_match = MatchService.transition_to_live(ready_match)

        assert updated_match.state == Match.LIVE
        assert updated_match.started_at is not None

    def test_transition_to_live_invalid_state(self, tournament, bracket):
        """Test transition to LIVE from invalid state"""
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=2,
            state=Match.SCHEDULED
        )

        with pytest.raises(ValidationError, match="Cannot start"):
            MatchService.transition_to_live(match)


@pytest.mark.django_db
class TestMatchServiceResultSubmission:
    """Test result submission and confirmation workflows"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now(),
            registration_opens_at=timezone.now() - timedelta(days=5),
            registration_closes_at=timezone.now() - timedelta(days=1),
            status=Tournament.LIVE
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.IN_PROGRESS,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def live_match(self, tournament, bracket):
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            state=Match.LIVE,
            started_at=timezone.now()
        )
        return match

    def test_submit_result_participant1_wins(self, live_match):
        """Test submitting result where participant 1 wins"""
        updated_match = MatchService.submit_result(
            match=live_match,
            submitted_by_id=101,
            participant1_score=13,
            participant2_score=11
        )

        assert updated_match.state == Match.PENDING_RESULT
        assert updated_match.participant1_score == 13
        assert updated_match.participant2_score == 11
        assert updated_match.winner_id == 101
        assert updated_match.loser_id == 102

    def test_submit_result_participant2_wins(self, live_match):
        """Test submitting result where participant 2 wins"""
        updated_match = MatchService.submit_result(
            match=live_match,
            submitted_by_id=102,
            participant1_score=9,
            participant2_score=13
        )

        assert updated_match.winner_id == 102
        assert updated_match.loser_id == 101

    def test_submit_result_negative_score(self, live_match):
        """Test submitting result with negative score"""
        with pytest.raises(ValidationError, match="cannot be negative"):
            MatchService.submit_result(
                match=live_match,
                submitted_by_id=101,
                participant1_score=-1,
                participant2_score=13
            )

    def test_submit_result_tie(self, live_match):
        """Test submitting result with tie score"""
        with pytest.raises(ValidationError, match="cannot end in a tie"):
            MatchService.submit_result(
                match=live_match,
                submitted_by_id=101,
                participant1_score=13,
                participant2_score=13
            )

    def test_confirm_result(self, live_match):
        """Test confirming match result"""
        # Submit result
        updated_match = MatchService.submit_result(
            match=live_match,
            submitted_by_id=101,
            participant1_score=13,
            participant2_score=11
        )

        # Confirm result
        final_match = MatchService.confirm_result(
            match=updated_match,
            confirmed_by_id=102
        )

        assert final_match.state == Match.COMPLETED
        assert final_match.completed_at is not None


@pytest.mark.django_db
class TestMatchServiceDisputes:
    """Test dispute creation and resolution workflows"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now(),
            registration_opens_at=timezone.now() - timedelta(days=5),
            registration_closes_at=timezone.now() - timedelta(days=1),
            status=Tournament.LIVE
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.IN_PROGRESS,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def pending_result_match(self, tournament, bracket):
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            state=Match.PENDING_RESULT,
            participant1_score=13,
            participant2_score=11,
            winner_id=101,
            loser_id=102
        )
        return match

    def test_report_dispute(self, pending_result_match):
        """Test creating dispute for match"""
        dispute = MatchService.report_dispute(
            match=pending_result_match,
            initiated_by_id=102,
            reason=Dispute.SCORE_MISMATCH,
            description="Claimed score is incorrect",
            evidence_video_url="https://youtube.com/evidence"
        )

        assert dispute.id is not None
        assert dispute.match == pending_result_match
        assert dispute.initiated_by_id == 102
        assert dispute.reason == Dispute.SCORE_MISMATCH
        assert dispute.status == Dispute.OPEN
        assert pending_result_match.state == Match.DISPUTED

    def test_report_dispute_duplicate(self, pending_result_match):
        """Test creating duplicate dispute"""
        MatchService.report_dispute(
            match=pending_result_match,
            initiated_by_id=102,
            reason=Dispute.SCORE_MISMATCH,
            description="First dispute"
        )

        with pytest.raises(ValidationError, match="already exists"):
            MatchService.report_dispute(
                match=pending_result_match,
                initiated_by_id=102,
                reason=Dispute.CHEATING,
                description="Second dispute"
            )

    def test_resolve_dispute_favor_original(self, pending_result_match):
        """Test resolving dispute in favor of original result"""
        dispute = MatchService.report_dispute(
            match=pending_result_match,
            initiated_by_id=102,
            reason=Dispute.SCORE_MISMATCH,
            description="Disputed score"
        )

        resolved_dispute, final_match = MatchService.resolve_dispute(
            dispute=dispute,
            resolved_by_id=1,
            resolution_notes="Verified from game logs - original score correct",
            final_participant1_score=13,
            final_participant2_score=11
        )

        assert resolved_dispute.status == Dispute.RESOLVED
        assert resolved_dispute.resolved_by_id == 1
        assert final_match.state == Match.COMPLETED
        assert final_match.winner_id == 101

    def test_resolve_dispute_overturned(self, pending_result_match):
        """Test resolving dispute with overturned result"""
        dispute = MatchService.report_dispute(
            match=pending_result_match,
            initiated_by_id=102,
            reason=Dispute.SCORE_MISMATCH,
            description="Score was reversed"
        )

        resolved_dispute, final_match = MatchService.resolve_dispute(
            dispute=dispute,
            resolved_by_id=1,
            resolution_notes="Verified - score was reversed",
            final_participant1_score=11,
            final_participant2_score=13
        )

        assert final_match.winner_id == 102
        assert final_match.loser_id == 101

    def test_escalate_dispute(self, pending_result_match):
        """Test escalating dispute to admin"""
        dispute = MatchService.report_dispute(
            match=pending_result_match,
            initiated_by_id=102,
            reason=Dispute.CHEATING,
            description="Serious cheating accusation"
        )

        escalated_dispute = MatchService.escalate_dispute(
            dispute=dispute,
            escalated_by_id=1,
            escalation_notes="Requires admin review"
        )

        assert escalated_dispute.status == Dispute.ESCALATED
        assert "ESCALATED" in escalated_dispute.resolution_notes


@pytest.mark.django_db
class TestMatchServiceCancellation:
    """Test match cancellation and forfeit workflows"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now(),
            registration_opens_at=timezone.now() - timedelta(days=5),
            registration_closes_at=timezone.now() - timedelta(days=1),
            status=Tournament.LIVE
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.IN_PROGRESS,
            total_rounds=4,
            current_round=1
        )

    @pytest.fixture
    def scheduled_match(self, tournament, bracket):
        return Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta",
            state=Match.SCHEDULED
        )

    def test_cancel_match(self, scheduled_match):
        """Test cancelling match"""
        cancelled_match = MatchService.cancel_match(
            match=scheduled_match,
            reason="Tournament reorganization",
            cancelled_by_id=1
        )

        assert cancelled_match.state == Match.CANCELLED
        assert cancelled_match.lobby_info['cancellation_reason'] == "Tournament reorganization"

    def test_forfeit_match_participant1(self, scheduled_match):
        """Test forfeit by participant 1"""
        forfeited_match = MatchService.forfeit_match(
            match=scheduled_match,
            reason="No-show",
            forfeiting_participant_id=101
        )

        assert forfeited_match.state == Match.FORFEIT
        assert forfeited_match.winner_id == 102
        assert forfeited_match.loser_id == 101

    def test_forfeit_match_participant2(self, scheduled_match):
        """Test forfeit by participant 2"""
        forfeited_match = MatchService.forfeit_match(
            match=scheduled_match,
            reason="Technical issues",
            forfeiting_participant_id=102
        )

        assert forfeited_match.winner_id == 101
        assert forfeited_match.loser_id == 102


@pytest.mark.django_db
class TestMatchServiceStatistics:
    """Test match statistics calculations"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now(),
            registration_opens_at=timezone.now() - timedelta(days=5),
            registration_closes_at=timezone.now() - timedelta(days=1),
            status=Tournament.LIVE
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            status=Bracket.IN_PROGRESS,
            total_rounds=4,
            current_round=1
        )

    def test_get_match_stats(self, tournament, bracket):
        """Test calculating match statistics"""
        # Create matches in various states
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED
        )
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=2,
            state=Match.LIVE
        )
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=3,
            state=Match.SCHEDULED
        )
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=4,
            state=Match.DISPUTED
        )

        stats = MatchService.get_match_stats(tournament)

        assert stats['total_matches'] == 4
        assert stats['completed'] == 1
        assert stats['live'] == 1
        assert stats['pending'] == 1
        assert stats['disputed'] == 1
        assert stats['completion_rate'] == 0.25

    def test_get_live_matches(self, tournament, bracket):
        """Test getting live matches"""
        live1 = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.LIVE
        )
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED
        )

        live_matches = MatchService.get_live_matches(tournament)

        assert live_matches.count() == 1
        assert live_matches.first() == live1

    def test_get_participant_matches(self, tournament, bracket):
        """Test getting matches for specific participant"""
        match1 = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            participant1_id=101,
            participant2_id=102
        )
        match2 = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=2,
            match_number=1,
            participant1_id=101,
            participant2_id=103
        )
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=2,
            participant1_id=104,
            participant2_id=105
        )

        participant_matches = MatchService.get_participant_matches(tournament, 101)

        assert participant_matches.count() == 2
        assert match1 in participant_matches
        assert match2 in participant_matches
