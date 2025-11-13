# apps/tournaments/tests/api/test_matches_api.py
import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.tournaments.models import Match, Tournament, Bracket, Dispute

User = get_user_model()


@pytest.fixture
def participant1_user(db):
    """Create participant 1 user."""
    return User.objects.create_user(
        username="participant1",
        email="p1@test.com",
        password="pass123"
    )


@pytest.fixture
def participant2_user(db):
    """Create participant 2 user."""
    return User.objects.create_user(
        username="participant2",
        email="p2@test.com",
        password="pass123"
    )


@pytest.fixture
def staff_user(db):
    """Create staff user."""
    user = User.objects.create_superuser(
        username="staff",
        email="staff@test.com",
        password="pass123"
    )
    user.refresh_from_db()
    assert user.is_staff is True
    return user


@pytest.fixture
def other_user(db):
    """Create non-participant user."""
    return User.objects.create_user(
        username="other",
        email="other@test.com",
        password="pass123"
    )


@pytest.fixture
def tournament(db, game_factory, tournament_factory):
    """Create a tournament with proper Game FK."""
    game = game_factory(slug='valorant', name='Valorant', team_size=5, profile_id_field='riot_id')
    return tournament_factory(
        game=game,
        participation_type='solo',
        max_participants=8,
        entry_fee=0
    )


@pytest.fixture
def bracket(tournament):
    """Create a bracket."""
    return Bracket.objects.create(
        tournament=tournament,
        format="single-elimination",  # Not 'bracket_type'
        total_rounds=3,
        total_matches=7
    )


@pytest.fixture
def match_scheduled(bracket, participant1_user, participant2_user):
    """Create scheduled match."""
    return Match.objects.create(
        tournament=bracket.tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=participant1_user.id,
        participant1_name="participant1",
        participant2_id=participant2_user.id,
        participant2_name="participant2",
        state='scheduled',
        lobby_info={}
    )


@pytest.fixture
def match_live(bracket, participant1_user, participant2_user):
    """Create live match."""
    return Match.objects.create(
        tournament=bracket.tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        participant1_id=participant1_user.id,
        participant1_name="participant1",
        participant2_id=participant2_user.id,
        participant2_name="participant2",
        state='live',
        started_at=timezone.now(),
        lobby_info={}
    )


@pytest.fixture
def match_pending_result(bracket, participant1_user, participant2_user):
    """Create pending_result match."""
    return Match.objects.create(
        tournament=bracket.tournament,
        bracket=bracket,
        round_number=1,
        match_number=3,
        participant1_id=participant1_user.id,
        participant1_name="participant1",
        participant2_id=participant2_user.id,
        participant2_name="participant2",
        state='pending_result',
        started_at=timezone.now(),
        participant1_score=2,
        participant2_score=1,
        lobby_info={}
    )


@pytest.fixture
def match_disputed(bracket, participant1_user, participant2_user):
    """Create disputed match."""
    match = Match.objects.create(
        tournament=bracket.tournament,
        bracket=bracket,
        round_number=1,
        match_number=4,
        participant1_id=participant1_user.id,
        participant1_name="participant1",
        participant2_id=participant2_user.id,
        participant2_name="participant2",
        state='disputed',
        started_at=timezone.now(),
        participant1_score=2,
        participant2_score=2,
        lobby_info={}
    )
    
    # Create dispute
    Dispute.objects.create(
        match=match,
        initiated_by_id=participant1_user.id,
        reason='score_mismatch',
        description='Scores do not match',
        status='open'
    )
    
    return match


@pytest.fixture
def participant1_client(participant1_user):
    """API client for participant 1."""
    client = APIClient()
    client.force_login(participant1_user)
    return client


@pytest.fixture
def participant2_client(participant2_user):
    """API client for participant 2."""
    client = APIClient()
    client.force_login(participant2_user)
    return client


@pytest.fixture
def staff_client(staff_user):
    """API client for staff."""
    client = APIClient()
    client.force_login(staff_user)
    return client


@pytest.fixture
def other_client(other_user):
    """API client for non-participant."""
    client = APIClient()
    client.force_login(other_user)
    return client


# ========== TestMatchStart ==========

@pytest.mark.django_db
class TestMatchStart:
    def test_start_happy_path_scheduled_to_live_staff_only(
        self, staff_client, match_scheduled
    ):
        """Staff starts match: SCHEDULED → LIVE."""
        url = f"/api/tournaments/matches/{match_scheduled.id}/start/"
        resp = staff_client.post(url)
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'live'
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_scheduled.refresh_from_db()
        assert match_scheduled.state == 'live'
        assert match_scheduled.started_at is not None
    
    def test_start_invalid_state_conflict_409(
        self, staff_client, match_live
    ):
        """Cannot start already started match."""
        url = f"/api/tournaments/matches/{match_live.id}/start/"
        resp = staff_client.post(url)
        
        assert resp.status_code == 409, resp.data
        assert 'Invalid state transition' in resp.data['detail']


# ========== TestMatchSubmitResult ==========

@pytest.mark.django_db
class TestMatchSubmitResult:
    def test_submit_result_happy_path_live_to_pending_result_for_participant1(
        self, participant1_client, match_live
    ):
        """Participant 1 submits result: LIVE → PENDING_RESULT."""
        url = f"/api/tournaments/matches/{match_live.id}/submit-result/"
        payload = {
            "score": 3,
            "opponent_score": 1,
            "evidence": "http://screenshot.com/proof.png",
            "notes": {"comment": "gg wp"}
        }
        
        resp = participant1_client.post(url, payload, format='json')
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'pending_result'
        assert resp.data['sides']['A']['score'] == 3
        assert resp.data['sides']['B']['score'] == 1
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_live.refresh_from_db()
        assert match_live.state == 'pending_result'
        assert match_live.participant1_score == 3
        assert match_live.participant2_score == 1
    
    def test_submit_result_forbidden_for_non_participant_403(
        self, other_client, match_live
    ):
        """Non-participant gets 403."""
        url = f"/api/tournaments/matches/{match_live.id}/submit-result/"
        payload = {"score": 3, "opponent_score": 1}
        
        resp = other_client.post(url, payload, format='json')
        
        assert resp.status_code == 403, resp.data
    
    def test_submit_result_idempotent_replay_returns_same_body(
        self, participant1_client, match_live
    ):
        """Idempotency-Key replay returns same response."""
        url = f"/api/tournaments/matches/{match_live.id}/submit-result/"
        payload = {"score": 3, "opponent_score": 1}
        headers = {"HTTP_IDEMPOTENCY_KEY": "key123"}
        
        # First call
        resp1 = participant1_client.post(url, payload, format='json', **headers)
        assert resp1.status_code == 200
        assert resp1.data['meta']['idempotent_replay'] is False
        
        # Replay
        resp2 = participant1_client.post(url, payload, format='json', **headers)
        assert resp2.status_code == 200
        assert resp2.data['meta']['idempotent_replay'] is True
        assert resp2.data['id'] == resp1.data['id']
    
    def test_submit_result_invalid_state_from_scheduled_conflict_409(
        self, participant1_client, match_scheduled
    ):
        """Cannot submit result before match starts."""
        url = f"/api/tournaments/matches/{match_scheduled.id}/submit-result/"
        payload = {"score": 3, "opponent_score": 1}
        
        resp = participant1_client.post(url, payload, format='json')
        
        assert resp.status_code == 409, resp.data
        assert 'Invalid state transition' in resp.data['detail']


# ========== TestMatchConfirm ==========

@pytest.mark.django_db
class TestMatchConfirm:
    def test_confirm_happy_path_pending_result_to_completed(
        self, staff_client, match_pending_result
    ):
        """Staff confirms result: PENDING_RESULT → COMPLETED."""
        url = f"/api/tournaments/matches/{match_pending_result.id}/confirm-result/"
        payload = {"decision": "Confirmed after review"}
        
        resp = staff_client.post(url, payload, format='json')
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'completed'
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_pending_result.refresh_from_db()
        assert match_pending_result.state == 'completed'
        assert match_pending_result.winner_id == match_pending_result.participant1_id
        assert match_pending_result.loser_id == match_pending_result.participant2_id
        assert match_pending_result.completed_at is not None
    
    def test_confirm_invalid_state_from_live_conflict_409(
        self, staff_client, match_live
    ):
        """Cannot confirm before result is submitted."""
        url = f"/api/tournaments/matches/{match_live.id}/confirm-result/"
        payload = {"decision": "Confirmed"}
        
        resp = staff_client.post(url, payload, format='json')
        
        assert resp.status_code == 409, resp.data
        assert 'Invalid state transition' in resp.data['detail']
    
    def test_confirm_idempotent_replay(
        self, staff_client, match_pending_result
    ):
        """Idempotency works for confirm."""
        url = f"/api/tournaments/matches/{match_pending_result.id}/confirm-result/"
        headers = {"HTTP_IDEMPOTENCY_KEY": "confirm-key-123"}
        
        # First call
        resp1 = staff_client.post(url, {}, format='json', **headers)
        assert resp1.status_code == 200
        assert resp1.data['meta']['idempotent_replay'] is False
        
        # Replay
        resp2 = staff_client.post(url, {}, format='json', **headers)
        assert resp2.status_code == 200
        assert resp2.data['meta']['idempotent_replay'] is True


# ========== TestMatchDispute ==========

@pytest.mark.django_db
class TestMatchDispute:
    def test_dispute_happy_path_pending_result_to_disputed_by_participant(
        self, participant2_client, match_pending_result
    ):
        """Participant files dispute: PENDING_RESULT → DISPUTED."""
        url = f"/api/tournaments/matches/{match_pending_result.id}/dispute/"
        payload = {
            "reason_code": "SCORE_MISMATCH",
            "notes": {"details": "My score is wrong"},
            "evidence": "http://proof.com/video.mp4"
        }
        
        resp = participant2_client.post(url, payload, format='json')
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'disputed'
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_pending_result.refresh_from_db()
        assert match_pending_result.state == 'disputed'
        
        # Check dispute created
        dispute = Dispute.objects.filter(match=match_pending_result).first()
        assert dispute is not None
        assert dispute.reason == 'score_mismatch'
        assert dispute.status == 'open'
    
    def test_dispute_forbidden_non_participant_403(
        self, other_client, match_pending_result
    ):
        """Non-participant cannot file dispute."""
        url = f"/api/tournaments/matches/{match_pending_result.id}/dispute/"
        payload = {"reason_code": "SCORE_MISMATCH", "notes": {}}
        
        resp = other_client.post(url, payload, format='json')
        
        assert resp.status_code == 403, resp.data
    
    def test_resolve_dispute_happy_path_staff_only(
        self, staff_client, match_disputed
    ):
        """Staff resolves dispute: DISPUTED → COMPLETED."""
        url = f"/api/tournaments/matches/{match_disputed.id}/resolve-dispute/"
        payload = {
            "decision": "OVERRIDE",
            "final_score_a": 3,
            "final_score_b": 1,
            "notes": {"resolution": "Video evidence supports participant 1"}
        }
        
        resp = staff_client.post(url, payload, format='json')
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'completed'
        assert resp.data['sides']['A']['score'] == 3
        assert resp.data['sides']['B']['score'] == 1
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_disputed.refresh_from_db()
        assert match_disputed.state == 'completed'
        assert match_disputed.participant1_score == 3
        assert match_disputed.participant2_score == 1
        assert match_disputed.winner_id == match_disputed.participant1_id
        
        # Check dispute resolved
        dispute = Dispute.objects.get(match=match_disputed)
        assert dispute.status == 'resolved'
    
    def test_resolve_dispute_invalid_state_from_pending_result_conflict_409(
        self, staff_client, match_pending_result
    ):
        """Cannot resolve non-disputed match."""
        url = f"/api/tournaments/matches/{match_pending_result.id}/resolve-dispute/"
        payload = {"decision": "OVERRIDE", "final_score_a": 3, "final_score_b": 1}
        
        resp = staff_client.post(url, payload, format='json')
        
        assert resp.status_code == 409, resp.data
        assert 'Invalid state transition' in resp.data['detail']


# ========== TestMatchCancel ==========

@pytest.mark.django_db
class TestMatchCancel:
    def test_cancel_any_state_staff_only_transitions_to_cancelled(
        self, staff_client, match_scheduled
    ):
        """Staff can cancel from any state."""
        url = f"/api/tournaments/matches/{match_scheduled.id}/cancel/"
        payload = {
            "reason_code": "ORGANIZER_REQUEST",
            "notes": {"comment": "Participant 1 did not appear"}
        }
        
        resp = staff_client.post(url, payload, format='json')
        
        assert resp.status_code == 200, resp.data
        assert resp.data['state'] == 'cancelled'
        assert resp.data['meta']['idempotent_replay'] is False
        
        match_scheduled.refresh_from_db()
        assert match_scheduled.state == 'cancelled'
        assert 'cancellation' in match_scheduled.lobby_info
    
    def test_cancel_forbidden_non_staff_403(
        self, participant1_client, match_scheduled
    ):
        """Non-staff cannot cancel match."""
        url = f"/api/tournaments/matches/{match_scheduled.id}/cancel/"
        payload = {"reason_code": "OTHER", "notes": {}}
        
        resp = participant1_client.post(url, payload, format='json')
        
        assert resp.status_code == 403, resp.data


# ========== TestMatchPII ==========

@pytest.mark.django_db
class TestMatchPII:
    def test_list_and_detail_do_not_expose_pii(
        self, participant1_client, match_scheduled
    ):
        """Match responses contain only IDs, no usernames/emails."""
        # Test list
        list_url = "/api/tournaments/matches/"
        list_resp = participant1_client.get(list_url)
        assert list_resp.status_code == 200
        
        for match_data in list_resp.data['results']:
            assert 'username' not in str(match_data)
            assert 'email' not in str(match_data)
            assert 'participant_id' in str(match_data)  # IDs OK
        
        # Test detail
        detail_url = f"/api/tournaments/matches/{match_scheduled.id}/"
        detail_resp = participant1_client.get(detail_url)
        assert detail_resp.status_code == 200
        
        assert 'username' not in str(detail_resp.data)
        assert 'email' not in str(detail_resp.data)
        assert detail_resp.data['sides']['A']['participant_id'] == match_scheduled.participant1_id


# ========== TestMatchEdgeCases ==========

@pytest.mark.django_db
class TestMatchEdgeCases:
    def test_confirm_result_rejects_tie_scores(
        self, staff_client, bracket, participant1_user, participant2_user
    ):
        """Ties are rejected in confirm_result (documented behavior)."""
        match = Match.objects.create(
            tournament=bracket.tournament,
            bracket=bracket,
            round_number=1,
            match_number=99,
            participant1_id=participant1_user.id,
            participant1_name="participant1",
            participant2_id=participant2_user.id,
            participant2_name="participant2",
            state='pending_result',
            started_at=timezone.now(),
            participant1_score=2,
            participant2_score=2,  # TIE
            lobby_info={}
        )
        
        url = f"/api/tournaments/matches/{match.id}/confirm-result/"
        resp = staff_client.post(url, {}, format='json')
        
        # Should reject ties
        assert resp.status_code == 400, resp.data
        assert 'tie' in resp.data['detail'].lower() or 'winner' in resp.data['detail'].lower()
    
    @pytest.mark.skip(reason="Team membership lookup not yet implemented - TODO: wire TeamMember.objects.filter(team_id=participant_id, user=request.user)")
    def test_submit_result_team_captain_vs_member_permission(
        self, participant1_client, bracket
    ):
        """
        TODO: Test that team captains can submit results, but regular members cannot.
        Requires TeamMember model lookup: TeamMember.objects.filter(team_id=match.participant1_id, user=request.user).exists()
        """
        # Placeholder - implement when team mode is enabled
        pass

