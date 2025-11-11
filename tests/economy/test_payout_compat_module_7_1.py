import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model

from apps.tournaments.models import Game, Tournament, Registration, TournamentResult, PrizeTransaction
from apps.tournaments.services.payout_service import PayoutService
from apps.economy import services as econ_services

User = get_user_model()


@pytest.mark.django_db(transaction=True)
def test_payout_service_works_with_new_economy_credit_shim():
    """Shim PayoutService.award to call the new economy.credit() and ensure payouts still work.

    This test patches the imported award symbol inside the payout service module to a shim
    that calls the new economy.credit() service and returns a simple object with an .id
    attribute so the rest of the payout flow (PrizeTransaction creation) proceeds unchanged.
    """

    unique_id = str(uuid.uuid4())[:8]

    # Create game
    game = Game.objects.create(
        name=f"Test Game {unique_id}",
        slug=f"test-game-{unique_id}",
        default_team_size=5,
        profile_id_field='game_id',
        is_active=True,
    )

    # Create organizer and three players
    organizer = User.objects.create_user(username=f"organizer-{unique_id}", email=f"organizer-{unique_id}@example.test")
    user1 = User.objects.create_user(username=f"p1-{unique_id}", email=f"p1-{unique_id}@example.test")
    user2 = User.objects.create_user(username=f"p2-{unique_id}", email=f"p2-{unique_id}@example.test")
    user3 = User.objects.create_user(username=f"p3-{unique_id}", email=f"p3-{unique_id}@example.test")

    now = timezone.now()
    tournament = Tournament.objects.create(
        name=f"Test Tournament {unique_id}",
        slug=f"test-tournament-{unique_id}",
        description="Test description",
        game=game,
        organizer=organizer,
        format=Tournament.SINGLE_ELIM,
        max_participants=16,
        min_participants=2,
        registration_start=now,
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=10),
        tournament_end=now + timedelta(days=12),
        status=Tournament.COMPLETED,
        prize_distribution={'1st': '100.00', '2nd': '50.00', '3rd': '25.00'},
    )

    # Create registrations
    reg1 = Registration.objects.create(tournament=tournament, user=user1, status='confirmed')
    reg2 = Registration.objects.create(tournament=tournament, user=user2, status='confirmed')
    reg3 = Registration.objects.create(tournament=tournament, user=user3, status='confirmed')

    # Create tournament result
    TournamentResult.objects.create(
        tournament=tournament,
        winner=reg1,
        runner_up=reg2,
        third_place=reg3,
        created_by=organizer,
        rules_applied={'method': 'test_fixture'},
    )

    # Shim: adapt economy.credit() (returns dict) to an object with .id attribute
    def award_shim(*, profile, amount, **kwargs):
        # economy.credit expects a UserProfile instance (or id). Convert if a User was passed.
        from django.apps import apps as django_apps
        Profile = django_apps.get_model('user_profile', 'UserProfile')
        profile_obj = None
        try:
            # If a Django User was passed, find the related UserProfile
            profile_obj = Profile.objects.get(user=profile)
        except Exception:
            # Fallback: assume profile is already the correct object
            profile_obj = profile

        # economy.credit expects amount as int
        res = econ_services.credit(profile_obj, int(amount), reason=kwargs.get('reason', ''), idempotency_key=kwargs.get('idempotency_key'))
        class Obj:
            pass
        o = Obj()
        o.id = res['transaction_id']
        return o

    with patch('apps.tournaments.services.payout_service.award', new=award_shim):
        tx_ids = PayoutService.process_payouts(tournament.id, processed_by=organizer)

    # Expect three created tx ids
    assert isinstance(tx_ids, list)
    assert len(tx_ids) == 3

    # Verify PrizeTransaction records exist and are completed
    prize_txs = PrizeTransaction.objects.filter(tournament=tournament)
    assert prize_txs.count() == 3
    assert prize_txs.filter(status=PrizeTransaction.Status.COMPLETED).count() == 3
