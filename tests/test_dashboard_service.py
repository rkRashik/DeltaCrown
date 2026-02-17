"""
Tests for Organizer Dashboard Service (Module 2.5)

Source: Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.5, lines 250-279)
Target: ≥15 service tests, ≥80% coverage

Test Coverage:
- get_organizer_stats(): 6 tests
- get_tournament_health(): 6 tests  
- get_participant_breakdown(): 6 tests
Total: 18 tests
"""

import pytest
from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.services.dashboard_service import DashboardService
from apps.tournaments.models.tournament import Tournament
from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.match import Match, Dispute
from django.contrib.auth import get_user_model

User = get_user_model()


def create_tournament_fixture(**kwargs):
    """
    Helper to create Tournament instances with all required fields.
    Provides sensible defaults for all required fields.
    """
    now = timezone.now()
    
    defaults = {
        'name': 'Test Tournament',
        'slug': f'test-tournament-{now.timestamp()}',
        'description': 'Test tournament description',
        'format': Tournament.SINGLE_ELIM,
        'participation_type': Tournament.SOLO,
        'max_participants': 16,
        'min_participants': 2,
        'registration_start': now,
        'registration_end': now + timedelta(days=7),
        'tournament_start': now + timedelta(days=10),
        'tournament_end': None,
        'status': Tournament.REGISTRATION_OPEN,
        'has_entry_fee': False,
        'entry_fee_amount': Decimal('0.00'),
        'entry_fee_currency': 'BDT',
        'entry_fee_deltacoin': 0,
        'prize_pool': Decimal('0.00'),
        'prize_currency': 'BDT',
        'prize_deltacoin': 0,
        'prize_distribution': {},
        'payment_methods': [],
        'enable_fee_waiver': False,
        'fee_waiver_top_n_teams': 0,
        'is_official': False,
        'enable_check_in': True,
        'check_in_minutes_before': 15,
        'enable_dynamic_seeding': False,
        'enable_live_updates': True,
        'enable_certificates': True,
    }
    
    # Merge provided kwargs with defaults
    defaults.update(kwargs)
    
    return Tournament.objects.create(**defaults)


@pytest.mark.django_db
class TestGetOrganizerStats:
    """Test suite for DashboardService.get_organizer_stats()"""
    
    def test_get_organizer_stats_empty(self):
        """Test organizer with no tournaments"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['organizer_id'] == user.id
        assert stats['total_tournaments'] == 0
        assert stats['active_tournaments'] == 0
        assert stats['total_participants'] == 0
        assert stats['total_revenue'] == 0.0
        assert stats['pending_actions']['pending_payments'] == 0
        assert stats['pending_actions']['open_disputes'] == 0
    
    def test_get_organizer_stats_with_tournaments(self):
        """Test organizer with multiple tournaments"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        # Create 3 tournaments
        t1 = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=32,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500')
        )
        t2 = create_tournament_fixture(
            name='Tournament 2',
            slug='tournament-2',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            has_entry_fee=True,
            entry_fee_amount=Decimal('300')
        )
        t3 = create_tournament_fixture(
            name='Tournament 3',
            slug='tournament-3',
            organizer=user,
            game=game,
            status=Tournament.COMPLETED,
            max_participants=64,
            has_entry_fee=True,
            entry_fee_amount=Decimal('1000')
        )
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['total_tournaments'] == 3
        assert stats['active_tournaments'] == 2  # LIVE + REGISTRATION_OPEN
    
    def test_get_organizer_stats_with_participants(self):
        """Test participant counting (confirmed registrations only)"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        # Create participants
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        
        # Confirmed registrations
        Registration.objects.create(
            tournament=tournament,
            user=player1,
            status=Registration.CONFIRMED
        )
        Registration.objects.create(
            tournament=tournament,
            user=player2,
            status=Registration.CONFIRMED
        )
        
        # Pending registration (should not count)
        Registration.objects.create(
            tournament=tournament,
            user=player3,
            status=Registration.PENDING
        )
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['total_participants'] == 2  # Only confirmed
    
    def test_get_organizer_stats_with_revenue(self):
        """Test revenue calculation from verified payments"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            entry_fee_amount=Decimal('500'),
            has_entry_fee=True,
            participation_type=Tournament.SOLO
        )
        
        # Create participants with payments
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        
        reg1 = Registration.objects.create(
            tournament=tournament,
            user=player1,
            status=Registration.CONFIRMED
        )
        reg2 = Registration.objects.create(
            tournament=tournament,
            user=player2,
            status=Registration.CONFIRMED
        )
        reg3 = Registration.objects.create(
            tournament=tournament,
            user=player3,
            status=Registration.PENDING
        )
        
        # Verified payments (must have verified_by AND verified_at for payment_verification_complete constraint)
        Payment.objects.create(
            registration=reg1,
            amount=Decimal('500'),
            payment_method='bkash',
            transaction_id='TXN001',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        Payment.objects.create(
            registration=reg2,
            amount=Decimal('500'),
            payment_method='nagad',
            transaction_id='TXN002',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        
        # Pending payment (should not count)
        Payment.objects.create(
            registration=reg3,
            amount=Decimal('500'),
            payment_method='rocket',
            transaction_id='TXN003',
            status=Payment.PENDING
        )
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['total_revenue'] == 1000.0  # Only verified
    
    def test_get_organizer_stats_with_pending_actions(self):
        """Test pending payments and disputes counting"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=32,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500'),
            participation_type=Tournament.SOLO
        )
        
        # Create registrations with pending payments
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        
        reg1 = Registration.objects.create(
            tournament=tournament,
            user=player1,
            status=Registration.PAYMENT_SUBMITTED
        )
        reg2 = Registration.objects.create(
            tournament=tournament,
            user=player2,
            status=Registration.CONFIRMED
        )
        
        Payment.objects.create(
            registration=reg1,
            amount=Decimal('500'),
            payment_method='bkash',
            transaction_id='TXN001',
            status=Payment.PENDING
        )
        Payment.objects.create(
            registration=reg2,
            amount=Decimal('500'),
            payment_method='nagad',
            transaction_id='TXN002',
            status=Payment.SUBMITTED
        )
        
        # Create matches with disputes
        from apps.tournaments.models.bracket import Bracket
        bracket = Bracket.objects.create(tournament=tournament, format=tournament.format)
        
        match1 = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.DISPUTED
        )
        match2 = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=1,
            match_number=2,
            state=Match.DISPUTED
        )
        
        Dispute.objects.create(
            match=match1,
            initiated_by_id=player1.id,
            reason=Dispute.SCORE_MISMATCH,
            description='Score mismatch',
            status=Dispute.OPEN
        )
        Dispute.objects.create(
            match=match2,
            initiated_by_id=player2.id,
            reason=Dispute.NO_SHOW,
            description='No show',
            status=Dispute.UNDER_REVIEW
        )
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['pending_actions']['pending_payments'] == 2
        assert stats['pending_actions']['open_disputes'] == 2
    
    def test_get_organizer_stats_excludes_soft_deleted(self):
        """Test that soft-deleted tournaments are excluded"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        # Active tournament
        create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=32
        )
        
        # Soft-deleted tournament
        deleted_tournament = create_tournament_fixture(
            name='Tournament 2',
            slug='tournament-2',
            organizer=user,
            game=game,
            status=Tournament.CANCELLED,
            max_participants=16
        )
        deleted_tournament.deleted_at = timezone.now()
        deleted_tournament.save()
        
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        
        assert stats['total_tournaments'] == 1  # Only active


@pytest.mark.django_db
class TestGetTournamentHealth:
    """Test suite for DashboardService.get_tournament_health()"""
    
    def test_get_tournament_health_basic(self):
        """Test basic tournament health metrics"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert health['tournament_id'] == tournament.id
        assert health['payments']['pending'] == 0
        assert health['payments']['verified'] == 0
        assert health['payments']['rejected'] == 0
        assert health['disputes']['open'] == 0
        assert health['disputes']['resolved'] == 0
        assert health['completion_rate'] == 0.0
        assert health['registration_progress']['registered'] == 0
        assert health['registration_progress']['capacity'] == 32
        assert health['registration_progress']['percentage'] == 0.0
    
    def test_get_tournament_health_with_payments(self):
        """Test payment statistics in health metrics"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500'),
            participation_type=Tournament.SOLO
        )
        
        # Create registrations with various payment statuses
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        player4 = User.objects.create_user(username='player4', email='p4@test.com')
        
        reg1 = Registration.objects.create(tournament=tournament, user=player1)
        reg2 = Registration.objects.create(tournament=tournament, user=player2)
        reg3 = Registration.objects.create(tournament=tournament, user=player3)
        reg4 = Registration.objects.create(tournament=tournament, user=player4)
        
        Payment.objects.create(
            registration=reg1, amount=Decimal('500'),
            payment_method='bkash', transaction_id='TXN001',
            status=Payment.PENDING
        )
        Payment.objects.create(
            registration=reg2, amount=Decimal('500'),
            payment_method='nagad', transaction_id='TXN002',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        Payment.objects.create(
            registration=reg3, amount=Decimal('500'),
            payment_method='rocket', transaction_id='TXN003',
            status=Payment.REJECTED
        )
        Payment.objects.create(
            registration=reg4, amount=Decimal('500'),
            payment_method='bkash', transaction_id='TXN004',
            status=Payment.SUBMITTED
        )
        
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert health['payments']['pending'] == 2  # PENDING + SUBMITTED
        assert health['payments']['verified'] == 1
        assert health['payments']['rejected'] == 1
    
    def test_get_tournament_health_with_disputes(self):
        """Test dispute statistics in health metrics"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=16,
            participation_type=Tournament.SOLO
        )
        
        from apps.tournaments.models.bracket import Bracket
        bracket = Bracket.objects.create(tournament=tournament, format=tournament.format)
        
        # Create matches with disputes
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        
        match1 = Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=1, state=Match.DISPUTED
        )
        match2 = Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=2, state=Match.DISPUTED
        )
        # COMPLETED matches must have winner (chk_match_completed_has_winner constraint)
        # Note: Match uses winner_id/loser_id (generic IDs), not winner_user_id/winner_team_id
        match3 = Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=3, state=Match.COMPLETED,
            participant1_id=player1.id,
            winner_id=player1.id,
            loser_id=player1.id
        )
        
        Dispute.objects.create(
            match=match1, initiated_by_id=player1.id,
            reason=Dispute.SCORE_MISMATCH, description='Dispute 1',
            status=Dispute.OPEN
        )
        Dispute.objects.create(
            match=match2, initiated_by_id=player1.id,
            reason=Dispute.NO_SHOW, description='Dispute 2',
            status=Dispute.UNDER_REVIEW
        )
        Dispute.objects.create(
            match=match3, initiated_by_id=player1.id,
            reason=Dispute.TECHNICAL_ISSUE, description='Dispute 3',
            status=Dispute.RESOLVED
        )
        
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert health['disputes']['open'] == 2  # OPEN + UNDER_REVIEW
        assert health['disputes']['resolved'] == 1
    
    def test_get_tournament_health_completion_rate(self):
        """Test match completion rate calculation"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=8,
            participation_type=Tournament.SOLO
        )
        
        from apps.tournaments.models.bracket import Bracket
        bracket = Bracket.objects.create(tournament=tournament, format=tournament.format)
        
        # Create matches with various states
        # COMPLETED matches must have winner and loser (chk_match_completed_has_winner constraint)
        # Note: Match uses winner_id/loser_id (generic IDs), not winner_user_id/winner_team_id
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=1, state=Match.COMPLETED,
            participant1_id=player1.id,
            participant2_id=player2.id,
            winner_id=player1.id,
            loser_id=player2.id
        )
        Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=2, state=Match.COMPLETED,
            participant1_id=player1.id,
            participant2_id=player2.id,
            winner_id=player1.id,
            loser_id=player2.id
        )
        Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=3, state=Match.LIVE
        )
        Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=4, state=Match.SCHEDULED
        )
        
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert health['completion_rate'] == 0.5  # 2 completed / 4 total
    
    def test_get_tournament_health_registration_progress(self):
        """Test registration progress calculation"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=20,
            participation_type=Tournament.SOLO
        )
        
        # Create confirmed registrations
        for i in range(15):
            player = User.objects.create_user(
                username=f'player{i}',
                email=f'p{i}@test.com'
            )
            Registration.objects.create(
                tournament=tournament,
                user=player,
                status=Registration.CONFIRMED
            )
        
        # Create pending registration (should not count)
        player_pending = User.objects.create_user(username='pending', email='pending@test.com')
        Registration.objects.create(
            tournament=tournament,
            user=player_pending,
            status=Registration.PENDING
        )
        
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert health['registration_progress']['registered'] == 15
        assert health['registration_progress']['capacity'] == 20
        assert health['registration_progress']['percentage'] == 75.0
    
    def test_get_tournament_health_permission_denied(self):
        """Test permission denied for non-organizer"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com')
        other_user = User.objects.create_user(username='other', email='other@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32
        )
        
        with pytest.raises(PermissionDenied, match='not authorized'):
            DashboardService.get_tournament_health(
                tournament_id=tournament.id,
                requesting_user_id=other_user.id
            )
    
    def test_get_tournament_health_staff_access(self):
        """Test staff can access any tournament health"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com')
        # Create staff user - set is_staff after creation due to User model behavior
        staff_user = User.objects.create(
            username='staff',
            email='staff@test.com'
        )
        staff_user.set_password('testpass123')
        staff_user.save()
        # Set is_staff after initial save
        User.objects.filter(id=staff_user.id).update(is_staff=True)
        staff_user.refresh_from_db()
        
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32
        )
        
        # Should not raise PermissionDenied
        health = DashboardService.get_tournament_health(
            tournament_id=tournament.id,
            requesting_user_id=staff_user.id
        )
        
        assert health['tournament_id'] == tournament.id


@pytest.mark.django_db
class TestGetParticipantBreakdown:
    """Test suite for DashboardService.get_participant_breakdown()"""
    
    def test_get_participant_breakdown_basic(self):
        """Test basic participant breakdown with no filters"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        # Create registrations
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        
        reg1 = Registration.objects.create(
            tournament=tournament,
            user=player1,
            status=Registration.CONFIRMED
        )
        reg2 = Registration.objects.create(
            tournament=tournament,
            user=player2,
            status=Registration.CONFIRMED
        )
        
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert breakdown['count'] == 2
        assert len(breakdown['results']) == 2
        # Check participant IDs exist (order-independent)
        participant_ids = [r['participant_id'] for r in breakdown['results']]
        assert player1.id in participant_ids
        assert player2.id in participant_ids
        assert all(r['participant_type'] == 'solo' for r in breakdown['results'])
    
    def test_get_participant_breakdown_team_tournament(self):
        """Test participant breakdown for team tournament"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            participation_type=Tournament.TEAM
        )
        
        # Create team registrations (using team_id)
        # Note: Team tournaments use EITHER team_id OR user, not both (registration_user_xor_team constraint)
        
        reg1 = Registration.objects.create(
            tournament=tournament,
            team_id=101,
            status=Registration.CONFIRMED
        )
        reg2 = Registration.objects.create(
            tournament=tournament,
            team_id=102,
            status=Registration.CONFIRMED
        )
        
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        assert breakdown['count'] == 2
        # Check team IDs exist (order-independent)
        participant_ids = [r['participant_id'] for r in breakdown['results']]
        assert 101 in participant_ids
        assert 102 in participant_ids
        assert all(r['participant_type'] == 'team' for r in breakdown['results'])
    
    def test_get_participant_breakdown_with_payment_filter(self):
        """Test filtering by payment status"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500'),
            participation_type=Tournament.SOLO
        )
        
        # Create registrations with different payment statuses
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        
        reg1 = Registration.objects.create(tournament=tournament, user=player1)
        reg2 = Registration.objects.create(tournament=tournament, user=player2)
        reg3 = Registration.objects.create(tournament=tournament, user=player3)
        
        # VERIFIED payments must have verified_by AND verified_at (payment_verification_complete constraint)
        Payment.objects.create(
            registration=reg1, amount=Decimal('500'),
            payment_method='bkash', transaction_id='TXN001',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        Payment.objects.create(
            registration=reg2, amount=Decimal('500'),
            payment_method='nagad', transaction_id='TXN002',
            status=Payment.PENDING
        )
        Payment.objects.create(
            registration=reg3, amount=Decimal('500'),
            payment_method='rocket', transaction_id='TXN003',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        
        # Filter by VERIFIED
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id,
            filters={'payment_status': Payment.VERIFIED}
        )
        
        assert breakdown['count'] == 2
        assert all(r['payment_status'] == Payment.VERIFIED for r in breakdown['results'])
    
    def test_get_participant_breakdown_with_checkin_filter(self):
        """Test filtering by check-in status"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        # Create registrations with different check-in statuses
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        
        Registration.objects.create(
            tournament=tournament, user=player1,
            checked_in=True, status=Registration.CONFIRMED
        )
        Registration.objects.create(
            tournament=tournament, user=player2,
            checked_in=False, status=Registration.CONFIRMED
        )
        Registration.objects.create(
            tournament=tournament, user=player3,
            checked_in=True, status=Registration.CONFIRMED
        )
        
        # Filter by checked in
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id,
            filters={'check_in_status': 'CHECKED_IN'}
        )
        
        assert breakdown['count'] == 2
        assert all(r['check_in_status'] == 'CHECKED_IN' for r in breakdown['results'])
    
    def test_get_participant_breakdown_with_match_stats(self):
        """Test match statistics in breakdown"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.LIVE,
            max_participants=8,
            participation_type=Tournament.SOLO
        )
        
        from apps.tournaments.models.bracket import Bracket
        bracket = Bracket.objects.create(tournament=tournament, format=tournament.format)
        
        # Create players
        player1 = User.objects.create_user(username='player1', email='p1@test.com')
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        
        Registration.objects.create(tournament=tournament, user=player1, status=Registration.CONFIRMED)
        Registration.objects.create(tournament=tournament, user=player2, status=Registration.CONFIRMED)
        
        # Create completed matches
        # Note: Match uses participant1_id/winner_id/loser_id (generic IDs)
        match1 = Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=1, match_number=1,
            participant1_id=player1.id,
            participant2_id=player2.id,
            winner_id=player1.id,
            loser_id=player2.id,
            state=Match.COMPLETED
        )
        match2 = Match.objects.create(
            tournament=tournament, bracket=bracket,
            round_number=2, match_number=1,
            participant1_id=player1.id,
            participant2_id=player2.id,
            winner_id=player2.id,
            loser_id=player1.id,
            state=Match.COMPLETED
        )
        
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id
        )
        
        # Find player1's stats
        player1_result = next(r for r in breakdown['results'] if r['participant_id'] == player1.id)
        
        assert player1_result['match_stats']['matches_played'] == 2
        assert player1_result['match_stats']['wins'] == 1
        assert player1_result['match_stats']['losses'] == 1
    
    def test_get_participant_breakdown_pagination(self):
        """Test pagination parameters"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        # Create 25 registrations
        for i in range(25):
            player = User.objects.create_user(
                username=f'player{i}',
                email=f'p{i}@test.com'
            )
            Registration.objects.create(
                tournament=tournament,
                user=player,
                status=Registration.CONFIRMED
            )
        
        # Get first page (limit=10)
        breakdown_page1 = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id,
            limit=10,
            offset=0
        )
        
        assert breakdown_page1['count'] == 25
        assert len(breakdown_page1['results']) == 10
        
        # Get second page
        breakdown_page2 = DashboardService.get_participant_breakdown(
            tournament_id=tournament.id,
            requesting_user_id=user.id,
            limit=10,
            offset=10
        )
        
        assert breakdown_page2['count'] == 25
        assert len(breakdown_page2['results']) == 10
        
        # Ensure different results
        page1_ids = {r['participant_id'] for r in breakdown_page1['results']}
        page2_ids = {r['participant_id'] for r in breakdown_page2['results']}
        assert len(page1_ids & page2_ids) == 0  # No overlap
    
    def test_get_participant_breakdown_permission_denied(self):
        """Test permission denied for non-organizer"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com')
        other_user = User.objects.create_user(username='other', email='other@test.com')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=32,
            participation_type=Tournament.SOLO
        )
        
        with pytest.raises(PermissionDenied, match='not authorized'):
            DashboardService.get_participant_breakdown(
                tournament_id=tournament.id,
                requesting_user_id=other_user.id
            )
