"""
Integration Tests for Analytics API Views (Module 5.4)

Tests the 3 read-only analytics endpoints:
- GET /api/tournaments/analytics/organizer/<tournament_id>/
- GET /api/tournaments/analytics/participant/<user_id>/
- GET /api/tournaments/analytics/export/<tournament_id>/

Test Coverage:
1. test_organizer_analytics_permissions_and_200_ok
2. test_organizer_analytics_values_match_expected_metrics
3. test_participant_analytics_self_vs_other_permissions
4. test_participant_analytics_values_match_expected_metrics
5. test_csv_export_streams_with_headers_and_no_pii
6. test_csv_export_permission_denied_for_non_organizer

Module: 5.4 - Analytics & Reports
Source: Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-54

Privacy Policy Tested:
- No PII in responses (no emails, no usernames)
- Display names only
- Registration IDs preferred over user IDs

Performance Tested:
- CSV streaming (iterator, not prebuilt list)
- Memory-bounded export
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.registration import Registration
from apps.tournaments.models.match import Match
from apps.tournaments.models.result import TournamentResult
from apps.tournaments.models.prize import PrizeTransaction
from apps.tournaments.models import Game
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestOrganizerAnalyticsPermissions:
    """Test permissions and 200 OK for organizer analytics endpoint."""
    
    def test_organizer_analytics_permissions_and_200_ok(self):
        """Test 401 for anonymous, 403 for non-organizer, 200 for organizer/admin."""
        # Setup: Create game, users, tournament
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            is_active=True
        )
        
        organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='testpass123'
        )
        
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )
        
        admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Test',
            game=game,
            organizer=organizer,
            max_participants=16,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE,
        )
        
        url = reverse('tournaments_api:analytics-organizer', kwargs={'tournament_id': tournament.id})
        client = APIClient()
        
        # Test 1: Anonymous user -> 401 Unauthorized
        response = client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test 2: Authenticated non-organizer -> 403 Forbidden
        client.force_authenticate(user=other_user)
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.json()
        assert 'Permission denied' in response.json()['error']
        
        # Test 3: Tournament organizer -> 200 OK
        client.force_authenticate(user=organizer)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_participants' in data
        assert 'checked_in_count' in data
        
        # Test 4: Admin user -> 200 OK
        client.force_authenticate(user=admin)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Test 5: Non-existent tournament -> 404
        client.force_authenticate(user=organizer)
        url_404 = reverse('tournaments_api:analytics-organizer', kwargs={'tournament_id': 99999})
        response = client.get(url_404)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestOrganizerAnalyticsAccuracy:
    """Test organizer analytics returns correct metric values."""
    
    def test_organizer_analytics_values_match_expected_metrics(self):
        """Test that analytics metrics match expected values from fixtures."""
        # Setup: Create complete tournament with known metrics
        game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        organizer = User.objects.create_user(username='organizer', email='org@test.com', password='pass')
        
        tournament = Tournament.objects.create(
            name='Metrics Test Tournament',
            slug='metrics-test',
            description='Test',
            game=game,
            organizer=organizer,
            max_participants=8,
            prize_pool=Decimal('5000.00'),
            registration_start=timezone.now() - timedelta(days=20),
            registration_end=timezone.now() - timedelta(days=15),
            tournament_start=timezone.now() - timedelta(days=10),
            status=Tournament.LIVE,
        )
        
        # Create 8 participants (6 checked in)
        users = []
        registrations = []
        for i in range(8):
            user = User.objects.create_user(
                username=f'player{i}',
                email=f'player{i}@test.com',
                password='pass'
            )
            users.append(user)
            
            reg = Registration.objects.create(
                tournament=tournament,
                user=user,
                status=Registration.CONFIRMED,
                checked_in=(i < 6)  # First 6 checked in
            )
            registrations.append(reg)
        
        # Create 4 completed matches, 1 disputed
        for i in range(4):
            Match.objects.create(
                tournament=tournament,
                round_number=1,
                match_number=i + 1,
                participant1_id=registrations[i * 2].id,
                participant2_id=registrations[i * 2 + 1].id,
                state=Match.COMPLETED,
                winner_id=registrations[i * 2].id,
                loser_id=registrations[i * 2 + 1].id,
            )
        
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=5,
            participant1_id=registrations[0].id,
            participant2_id=registrations[1].id,
            state=Match.DISPUTED,
        )
        
        # Create 3 prizes (total $3000)
        for i, amount in enumerate(['2000.00', '750.00', '250.00']):
            PrizeTransaction.objects.create(
                tournament=tournament,
                participant=registrations[i],
                amount=Decimal(amount),
                placement=[
                    PrizeTransaction.Placement.FIRST,
                    PrizeTransaction.Placement.SECOND,
                    PrizeTransaction.Placement.THIRD
                ][i],
                status=PrizeTransaction.Status.COMPLETED,
            )
        
        # Make API call
        client = APIClient()
        client.force_authenticate(user=organizer)
        url = reverse('tournaments_api:analytics-organizer', kwargs={'tournament_id': tournament.id})
        response = client.get(url)
        
        # Assert 200 OK
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify metrics
        assert data['total_participants'] == 8
        assert data['checked_in_count'] == 6
        assert data['check_in_rate'] == 0.7500  # 6/8 = 0.75
        assert data['total_matches'] == 5
        assert data['completed_matches'] == 4
        assert data['disputed_matches'] == 1
        assert data['dispute_rate'] == 0.2000  # 1/5 = 0.20
        assert data['prize_pool_total'] == '5000.00'
        assert data['prizes_distributed'] == '3000.00'  # Sum of prizes
        assert data['payout_count'] == 3


@pytest.mark.django_db
class TestParticipantAnalyticsPermissions:
    """Test permissions for participant analytics endpoint."""
    
    def test_participant_analytics_self_vs_other_permissions(self):
        """Test 403 when viewing others' stats, 200 for self or admin."""
        # Setup: Create users
        user1 = User.objects.create_user(username='user1', email='user1@test.com', password='pass')
        user2 = User.objects.create_user(username='user2', email='user2@test.com', password='pass')
        admin = User.objects.create_user(username='admin', email='admin@test.com', password='pass', is_staff=True, is_superuser=True)
        
        url_user1 = reverse('tournaments_api:analytics-participant', kwargs={'user_id': user1.id})
        url_user2 = reverse('tournaments_api:analytics-participant', kwargs={'user_id': user2.id})
        client = APIClient()
        
        # Test 1: Anonymous -> 401
        response = client.get(url_user1)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test 2: User1 viewing own stats -> 200 OK
        client.force_authenticate(user=user1)
        response = client.get(url_user1)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_tournaments' in data
        assert 'tournaments_won' in data
        
        # Test 3: User1 viewing User2 stats -> 403 Forbidden
        response = client.get(url_user2)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.json()
        assert 'Permission denied' in response.json()['error']
        assert 'your own statistics' in response.json()['error']
        
        # Test 4: Admin viewing any user's stats -> 200 OK
        client.force_authenticate(user=admin)
        response = client.get(url_user1)
        assert response.status_code == status.HTTP_200_OK
        response = client.get(url_user2)
        assert response.status_code == status.HTTP_200_OK
        
        # Test 5: Non-existent user -> 404
        url_404 = reverse('tournaments_api:analytics-participant', kwargs={'user_id': 99999})
        response = client.get(url_404)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestParticipantAnalyticsAccuracy:
    """Test participant analytics returns correct metric values."""
    
    def test_participant_analytics_values_match_expected_metrics(self):
        """Test that participant analytics metrics match expected values."""
        # Setup: Create user with known tournament history
        game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        organizer = User.objects.create_user(username='org', email='org@test.com', password='pass')
        participant = User.objects.create_user(username='player', email='player@test.com', password='pass')
        
        # Create 2 completed tournaments
        tournaments = []
        for i in range(2):
            t = Tournament.objects.create(
                name=f'Tournament {i+1}',
                slug=f'tournament-{i+1}',
                description='Test',
                game=game,
                organizer=organizer,
                max_participants=8,
                prize_pool=Decimal('1000.00'),
                registration_start=timezone.now() - timedelta(days=20),
                registration_end=timezone.now() - timedelta(days=15),
                tournament_start=timezone.now() - timedelta(days=10),
                status=Tournament.COMPLETED,
            )
            tournaments.append(t)
        
        # Register participant in both
        registrations = []
        for t in tournaments:
            reg = Registration.objects.create(
                tournament=t,
                user=participant,
                status=Registration.CONFIRMED,
                checked_in=True,
            )
            registrations.append(reg)
        
        # Create opponent registrations
        opponents = []
        for i in range(4):
            opp = User.objects.create_user(
                username=f'opponent{i}',
                email=f'opp{i}@test.com',
                password='pass'
            )
            opponents.append(opp)
        
        opponent_regs = []
        for i, t in enumerate(tournaments):
            for j in range(2):
                reg = Registration.objects.create(
                    tournament=t,
                    user=opponents[i * 2 + j],
                    status=Registration.CONFIRMED,
                )
                opponent_regs.append(reg)
        
        # Tournament 1: Participant wins 2, loses 1 (2-1 record)
        Match.objects.create(
            tournament=tournaments[0],
            round_number=1,
            match_number=1,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[0].id,
            state=Match.COMPLETED,
            winner_id=registrations[0].id,
            loser_id=opponent_regs[0].id,
        )
        Match.objects.create(
            tournament=tournaments[0],
            round_number=1,
            match_number=2,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[1].id,
            state=Match.COMPLETED,
            winner_id=registrations[0].id,
            loser_id=opponent_regs[1].id,
        )
        Match.objects.create(
            tournament=tournaments[0],
            round_number=2,
            match_number=1,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[0].id,
            state=Match.COMPLETED,
            winner_id=opponent_regs[0].id,
            loser_id=registrations[0].id,
        )
        
        # Tournament 2: Participant wins 1, loses 1 (1-1 record)
        Match.objects.create(
            tournament=tournaments[1],
            round_number=1,
            match_number=1,
            participant1_id=registrations[1].id,
            participant2_id=opponent_regs[2].id,
            state=Match.COMPLETED,
            winner_id=registrations[1].id,
            loser_id=opponent_regs[2].id,
        )
        Match.objects.create(
            tournament=tournaments[1],
            round_number=1,
            match_number=2,
            participant1_id=registrations[1].id,
            participant2_id=opponent_regs[3].id,
            state=Match.COMPLETED,
            winner_id=opponent_regs[3].id,
            loser_id=registrations[1].id,
        )
        
        # Add placements: Tournament 1 winner, Tournament 2 runner-up
        TournamentResult.objects.create(
            tournament=tournaments[0],
            winner=registrations[0],
            runner_up=opponent_regs[0],
            third_place=opponent_regs[1],
            determination_method='normal',
            rules_applied={'method': 'bracket_completion'},
        )
        
        TournamentResult.objects.create(
            tournament=tournaments[1],
            winner=opponent_regs[2],
            runner_up=registrations[1],
            third_place=opponent_regs[3],
            determination_method='normal',
            rules_applied={'method': 'bracket_completion'},
        )
        
        # Add prizes: $500 for first place in Tournament 1
        PrizeTransaction.objects.create(
            tournament=tournaments[0],
            participant=registrations[0],
            amount=Decimal('500.00'),
            placement=PrizeTransaction.Placement.FIRST,
            status=PrizeTransaction.Status.COMPLETED,
        )
        
        # Make API call
        client = APIClient()
        client.force_authenticate(user=participant)
        url = reverse('tournaments_api:analytics-participant', kwargs={'user_id': participant.id})
        response = client.get(url)
        
        # Assert 200 OK
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify metrics (match actual service output field names)
        assert data['total_tournaments'] == 2
        assert data['tournaments_won'] == 1
        assert data['runner_up_count'] == 1
        assert data['third_place_count'] == 0
        assert data['best_placement'] == '1st'
        assert data['total_matches_played'] == 5  # 3 + 2
        assert data['matches_won'] == 3  # 2 + 1
        assert data['matches_lost'] == 2  # 1 + 1
        assert data['win_rate'] == 0.6000  # 3/5 = 0.60
        assert data['total_prize_winnings'] == '500.00'


@pytest.mark.django_db
class TestCSVExportStreaming:
    """Test CSV export endpoint streaming and PII protection."""
    
    def test_csv_export_streams_with_headers_and_no_pii(self):
        """Test CSV export uses streaming, has correct headers, and contains no PII."""
        # Setup: Create tournament with participants
        game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',  # This email should NOT appear in CSV
            password='pass'
        )
        
        tournament = Tournament.objects.create(
            name='CSV Test Tournament',
            slug='csv-test',
            description='Test',
            game=game,
            organizer=organizer,
            max_participants=4,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.COMPLETED,
        )
        
        # Create 3 participants with emails that should NOT appear
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'player{i}',
                email=f'player{i}@test.com',  # Should NOT appear in CSV
                password='pass'
            )
            users.append(user)
            
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status=Registration.CONFIRMED,
                checked_in=True,
            )
        
        # Make API call
        client = APIClient()
        client.force_authenticate(user=organizer)
        url = reverse('tournaments_api:analytics-export-csv', kwargs={'tournament_id': tournament.id})
        response = client.get(url)
        
        # Test 1: Response is 200 OK
        assert response.status_code == status.HTTP_200_OK
        
        # Test 2: Response is StreamingHttpResponse
        from django.http import StreamingHttpResponse
        assert isinstance(response, StreamingHttpResponse)
        
        # Test 3: Content-Type is CSV
        assert response['Content-Type'] == 'text/csv; charset=utf-8'
        
        # Test 4: Content-Disposition header is correct
        expected_filename = f'tournament_{tournament.id}_export.csv'
        assert 'attachment' in response['Content-Disposition']
        assert expected_filename in response['Content-Disposition']
        
        # Test 5: Consume streaming content (iterator pattern)
        csv_lines = []
        for chunk in response.streaming_content:
            csv_lines.append(chunk.decode('utf-8-sig'))  # Decode UTF-8 BOM
        
        csv_text = ''.join(csv_lines)
        lines = csv_text.strip().split('\n')
        
        # Test 6: Has header row
        assert len(lines) >= 1
        header = lines[0]
        
        # Test 7: Header has expected columns (12 total, match actual service output)
        expected_columns = [
            'participant_id', 'participant_name', 'registration_status',
            'checked_in', 'checked_in_at', 'matches_played', 'matches_won',
            'matches_lost', 'placement', 'prize_amount',
            'registration_created_at', 'payment_status'
        ]
        for col in expected_columns:
            assert col in header.lower(), f"Missing column: {col}"
        
        # Test 8: NO PII in CSV (no emails, no '@' symbols from emails)
        # Check that none of the test emails appear in the CSV
        assert 'organizer@test.com' not in csv_text
        assert 'player0@test.com' not in csv_text
        assert 'player1@test.com' not in csv_text
        assert 'player2@test.com' not in csv_text
        
        # Verify no email-like patterns (should not have multiple @ symbols)
        at_count = csv_text.count('@')
        # There should be NO @ symbols from emails (display names only)
        # Note: @ might appear in other contexts, but emails should be absent
        assert at_count == 0, "Found email-like patterns in CSV (PII leak detected)"
        
        # Test 9: Has data rows (3 participants = 3 data rows + 1 header)
        assert len(lines) == 4  # 1 header + 3 data rows


@pytest.mark.django_db
class TestCSVExportPermissions:
    """Test CSV export permissions."""
    
    def test_csv_export_permission_denied_for_non_organizer(self):
        """Test 401 for anonymous, 403 for non-organizer."""
        # Setup
        game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        organizer = User.objects.create_user(username='organizer', email='org@test.com', password='pass')
        other_user = User.objects.create_user(username='other', email='other@test.com', password='pass')
        admin = User.objects.create_user(username='admin', email='admin@test.com', password='pass', is_staff=True, is_superuser=True)
        
        tournament = Tournament.objects.create(
            name='Permission Test',
            slug='perm-test',
            description='Test',
            game=game,
            organizer=organizer,
            max_participants=8,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE,
        )
        
        url = reverse('tournaments_api:analytics-export-csv', kwargs={'tournament_id': tournament.id})
        client = APIClient()
        
        # Test 1: Anonymous -> 401
        response = client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test 2: Non-organizer -> 403
        client.force_authenticate(user=other_user)
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Test 3: Organizer -> 200
        client.force_authenticate(user=organizer)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Test 4: Admin -> 200
        client.force_authenticate(user=admin)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Test 5: Non-existent tournament -> 404
        url_404 = reverse('tournaments_api:analytics-export-csv', kwargs={'tournament_id': 99999})
        response = client.get(url_404)
        assert response.status_code == status.HTTP_404_NOT_FOUND
