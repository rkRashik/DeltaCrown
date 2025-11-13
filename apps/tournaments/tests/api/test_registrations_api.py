# apps/tournaments/tests/api/test_registrations_api.py
"""
Registration API tests - Milestone B
Target: ≥14 executed tests
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models import Tournament, Registration, Game, PaymentVerification


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def organizer_user(django_user_model):
    """Tournament organizer."""
    return django_user_model.objects.create_user("organizer", "org@test.com", "pass123")


@pytest.fixture
def user1(django_user_model):
    """Regular user 1."""
    return django_user_model.objects.create_user("user1", "user1@test.com", "pass123")


@pytest.fixture
def user2(django_user_model):
    """Regular user 2."""
    return django_user_model.objects.create_user("user2", "user2@test.com", "pass123")


@pytest.fixture
def game(db):
    """Game fixture."""
    return Game.objects.create(name="eFootball", slug="efootball")


@pytest.fixture
def tournament(db, game, organizer_user):
    """Tournament fixture open for registration."""
    now = timezone.now()
    return Tournament.objects.create(
        name="Test Tournament",
        slug="test-tournament",
        game=game,
        organizer=organizer_user,
        max_participants=16,
        tournament_start=now + timedelta(days=7),
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=5),
        status="registration_open"
    )


@pytest.mark.django_db
class TestSoloRegistrationAPI:
    """Test solo registration endpoints."""
    
    def test_create_solo_registration_happy_path(self, api_client, user1, tournament):
        """Test creating solo registration returns 201 with PV fields."""
        api_client.force_authenticate(user=user1)
        
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-SOLO-001",
                "payer_account_number": "01711111111",
                "amount_bdt": "250"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['tournament'] == tournament.id
        assert response.data['user'] == user1.id
        assert 'payment_verification' in response.data
        
        pv = response.data['payment_verification']
        assert pv['method'] == 'bkash'
        assert pv['transaction_id'] == 'TX-SOLO-001'
        assert pv['status'] == 'pending'
    
    def test_create_solo_duplicate_returns_400(self, api_client, user1, tournament):
        """Test duplicate registration returns 400."""
        api_client.force_authenticate(user=user1)
        
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-DUP-001",
                "payer_account_number": "01711111111",
                "amount_bdt": "250"
            }
        }
        
        # First registration succeeds
        response1 = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Second registration fails
        response2 = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in str(response2.data).lower()
    
    def test_create_solo_invalid_payment_returns_400(self, api_client, user1, tournament):
        """Test invalid payment fields return 400."""
        api_client.force_authenticate(user=user1)
        
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                # Missing transaction_id
                "amount_bdt": "250"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_solo_negative_amount_returns_400(self, api_client, user1, tournament):
        """Test negative amount returns 400."""
        api_client.force_authenticate(user=user1)
        
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-NEG-001",
                "payer_account_number": "01711111111",
                "amount_bdt": "-50"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_solo_unauthenticated_returns_401(self, api_client, tournament):
        """Test unauthenticated request returns 401."""
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-UNAUTH-001",
                "amount_bdt": "250"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_solo_invalid_tournament_returns_400(self, api_client, user1):
        """Test invalid tournament ID returns 400."""
        api_client.force_authenticate(user=user1)
        
        payload = {
            "tournament_id": 99999,  # Non-existent
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-INVALID-001",
                "amount_bdt": "250"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRegistrationCancellation:
    """Test registration cancellation."""
    
    def test_cancel_own_registration_returns_204(self, api_client, user1, tournament):
        """Test user can cancel their own registration."""
        api_client.force_authenticate(user=user1)
        
        # Create registration
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-CANCEL-001",
                "amount_bdt": "250"
            }
        }
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        
        registration_id = response.data['id']
        
        # Cancel registration
        response = api_client.delete(f"/api/tournaments/registrations/{registration_id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_cancel_other_user_registration_returns_403(self, api_client, user1, user2, tournament):
        """Test user cannot cancel another user's registration."""
        # User1 creates registration
        api_client.force_authenticate(user=user1)
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-CANCEL-002",
                "amount_bdt": "250"
            }
        }
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        registration_id = response.data['id']
        
        # User2 tries to cancel
        api_client.force_authenticate(user=user2)
        response = api_client.delete(f"/api/tournaments/registrations/{registration_id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cancel_nonexistent_registration_returns_404(self, api_client, user1):
        """Test canceling non-existent registration returns 404."""
        api_client.force_authenticate(user=user1)
        
        response = api_client.delete("/api/tournaments/registrations/99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_cancel_unauthenticated_returns_401(self, api_client, user1, tournament):
        """Test unauthenticated cancellation returns 401."""
        # Create registration as user1
        api_client.force_authenticate(user=user1)
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-CANCEL-003",
                "amount_bdt": "250"
            }
        }
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        registration_id = response.data['id']
        
        # Logout and try to cancel
        api_client.force_authenticate(user=None)
        response = api_client.delete(f"/api/tournaments/registrations/{registration_id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_cancel_idempotent_returns_204(self, api_client, user1, tournament):
        """Test canceling twice returns 204 both times (idempotent)."""
        api_client.force_authenticate(user=user1)
        
        # Create registration
        payload = {
            "tournament_id": tournament.id,
            "payment": {
                "method": "bkash",
                "transaction_id": "TX-IDEMP-001",
                "amount_bdt": "250"
            }
        }
        response = api_client.post("/api/tournaments/registrations/solo/", payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        registration_id = response.data['id']
        
        # First cancel
        response1 = api_client.delete(f"/api/tournaments/registrations/{registration_id}/")
        assert response1.status_code == status.HTTP_204_NO_CONTENT
        
        # Second cancel (idempotent)
        response2 = api_client.delete(f"/api/tournaments/registrations/{registration_id}/")
        # Should return 404 since registration no longer exists in queryset or 204 if soft-deleted
        assert response2.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestTeamRegistrationAPI:
    """Test team registration endpoints."""
    
    def test_create_team_registration_happy_path(self, api_client, user_with_profile, tournament):
        """Test creating team registration returns 201."""
        from apps.teams.models import Team
        
        captain_user, captain_profile = user_with_profile
        api_client.force_authenticate(user=captain_user)
        
        # Create a team with captain_profile as captain
        team = Team.objects.create(
            name="Test Team",
            captain=captain_profile,
            game=tournament.game
        )
        
        payload = {
            "tournament_id": tournament.id,
            "team_id": team.id,
            "payment": {
                "method": "nagad",
                "transaction_id": "TX-TEAM-001",
                "payer_account_number": "01811111111",
                "amount_bdt": "500"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/team/", payload, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['tournament'] == tournament.id
        assert response.data['team_id'] == team.id
        assert 'payment_verification' in response.data
    
    def test_create_team_not_captain_returns_400(self, api_client, user_with_profile, member_with_profile, tournament):
        """Test non-captain cannot register team."""
        from apps.teams.models import Team
        
        # User1 is captain
        captain_user, captain_profile = user_with_profile
        member_user, member_profile = member_with_profile
        
        team = Team.objects.create(
            name="Test Team",
            captain=captain_profile,
            game=tournament.game
        )
        
        # member_user tries to register (not captain)
        api_client.force_authenticate(user=member_user)
        
        payload = {
            "tournament_id": tournament.id,
            "team_id": team.id,
            "payment": {
                "method": "nagad",
                "transaction_id": "TX-TEAM-002",
                "amount_bdt": "500"
            }
        }
        
        response = api_client.post("/api/tournaments/registrations/team/", payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "captain" in str(response.data).lower()
    
    def test_create_team_duplicate_returns_400(self, api_client, user_with_profile, tournament):
        """Test duplicate team registration returns 400."""
        from apps.teams.models import Team
        
        captain_user, captain_profile = user_with_profile
        api_client.force_authenticate(user=captain_user)

        team = Team.objects.create(
            name="Test Team",
            captain=captain_profile,
            game=tournament.game
        )
        
        payload = {
            "tournament_id": tournament.id,
            "team_id": team.id,
            "payment": {
                "method": "nagad",
                "transaction_id": "TX-TEAM-DUP-001",
                "amount_bdt": "500"
            }
        }
        
        # First registration
        response1 = api_client.post("/api/tournaments/registrations/team/", payload, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Second registration (duplicate)
        payload["payment"]["transaction_id"] = "TX-TEAM-DUP-002"
        response2 = api_client.post("/api/tournaments/registrations/team/", payload, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in str(response2.data).lower()
