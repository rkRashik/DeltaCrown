"""
Hub Modules 3 & 5 — Resources Hub + Bounty Board Tests

Tests for:
- TournamentSponsor model (creation, validation, ordering)
- PrizeClaim model (creation, validation, status lifecycle)
- HubResourcesAPIView (GET /hub/api/resources/)
- HubPrizeClaimAPIView (GET + POST /hub/api/prize-claim/)

Sprint 12 — Batch 1 expansion.
"""

import json

import pytest
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.sponsor import TournamentSponsor
from apps.tournaments.models.prize_claim import PrizeClaim
from apps.tournaments.models.prize import PrizeTransaction
from apps.tournaments.models import Registration
from apps.tournaments.services.tournament_service import TournamentService

User = get_user_model()
pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def user():
    return User.objects.create_user(
        username='hubplayer', email='hub@test.com', password='pass1234'
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        username='otherplayer', email='other@test.com', password='pass1234'
    )


@pytest.fixture
def game():
    return Game.objects.create(
        name='Valorant', slug='valorant',
        default_team_size=5, profile_id_field='riot_id',
        default_result_type='map_score', is_active=True,
    )


@pytest.fixture
def tournament(user, game):
    now = timezone.now()
    data = {
        'name': 'Hub Test Tournament',
        'description': 'Testing Hub Modules 3 & 5',
        'game_id': game.id,
        'format': Tournament.SINGLE_ELIM,
        'participation_type': Tournament.SOLO,
        'max_participants': 16,
        'min_participants': 2,
        'registration_start': now - timedelta(days=7),
        'registration_end': now - timedelta(days=1),
        'tournament_start': now - timedelta(hours=2),
        'prize_pool': Decimal('10000.00'),
        'prize_currency': 'BDT',
        'prize_distribution': {'1': '50%', '2': '30%', '3': '20%'},
        'prize_deltacoin': 500,
        'rules_text': '# Tournament Rules\n\n- Be respectful\n- No cheating',
    }
    t = TournamentService.create_tournament(organizer=user, data=data)
    # Add social fields
    t.social_discord = 'https://discord.gg/test'
    t.social_twitter = 'https://twitter.com/test'
    t.contact_email = 'org@test.com'
    t.save(update_fields=['social_discord', 'social_twitter', 'contact_email'])
    return t


@pytest.fixture
def registration(user, tournament):
    return Registration.objects.create(
        user=user,
        tournament=tournament,
        status=Registration.CONFIRMED,
    )


@pytest.fixture
def prize_transaction(tournament, registration):
    return PrizeTransaction.objects.create(
        tournament=tournament,
        participant=registration,
        placement=PrizeTransaction.Placement.FIRST,
        amount=Decimal('5000.00'),
        status=PrizeTransaction.Status.COMPLETED,
    )


@pytest.fixture
def sponsor(tournament):
    return TournamentSponsor.objects.create(
        tournament=tournament,
        name='Acme Gaming',
        tier=TournamentSponsor.TIER_GOLD,
        website_url='https://acme.gg',
        description='Premier gaming sponsor',
        is_active=True,
    )


# ============================================================================
# TournamentSponsor Model Tests
# ============================================================================

class TestTournamentSponsorModel:

    def test_create_sponsor(self, tournament):
        s = TournamentSponsor.objects.create(
            tournament=tournament,
            name='TestCorp',
            tier=TournamentSponsor.TIER_TITLE,
        )
        assert s.pk is not None
        assert s.name == 'TestCorp'
        assert s.tier == 'title'
        assert s.is_active is True

    def test_str_representation(self, sponsor):
        assert 'Acme Gaming' in str(sponsor)

    def test_ordering(self, tournament):
        TournamentSponsor.objects.create(tournament=tournament, name='Z Bronze', tier=TournamentSponsor.TIER_BRONZE, display_order=1)
        TournamentSponsor.objects.create(tournament=tournament, name='A Gold', tier=TournamentSponsor.TIER_GOLD, display_order=1)
        TournamentSponsor.objects.create(tournament=tournament, name='B Title', tier=TournamentSponsor.TIER_TITLE, display_order=1)

        sponsors = list(TournamentSponsor.objects.filter(tournament=tournament).values_list('name', flat=True))
        # title < gold < silver < bronze < partner
        assert sponsors[0] == 'B Title'
        assert sponsors[1] == 'A Gold'

    def test_inactive_sponsor_excluded(self, tournament):
        TournamentSponsor.objects.create(tournament=tournament, name='Hidden', tier=TournamentSponsor.TIER_GOLD, is_active=False)
        active = TournamentSponsor.objects.filter(tournament=tournament, is_active=True)
        assert active.filter(name='Hidden').count() == 0

    def test_tier_choices(self):
        choices = [c[0] for c in TournamentSponsor.TIER_CHOICES]
        assert 'title' in choices
        assert 'gold' in choices
        assert 'silver' in choices
        assert 'bronze' in choices
        assert 'partner' in choices


# ============================================================================
# PrizeClaim Model Tests
# ============================================================================

class TestPrizeClaimModel:

    def test_create_claim(self, prize_transaction, user):
        claim = PrizeClaim.objects.create(
            prize_transaction=prize_transaction,
            claimed_by=user,
            payout_method=PrizeClaim.PAYOUT_BKASH,
            payout_destination='017****678',
        )
        assert claim.pk is not None
        assert claim.status == PrizeClaim.STATUS_PENDING
        assert claim.claimed_at is not None

    def test_one_to_one_constraint(self, prize_transaction, user):
        PrizeClaim.objects.create(
            prize_transaction=prize_transaction,
            claimed_by=user,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PrizeClaim.objects.create(
                prize_transaction=prize_transaction,
                claimed_by=user,
            )

    def test_status_lifecycle(self, prize_transaction, user):
        claim = PrizeClaim.objects.create(
            prize_transaction=prize_transaction,
            claimed_by=user,
        )
        assert claim.status == PrizeClaim.STATUS_PENDING

        claim.status = PrizeClaim.STATUS_PROCESSING
        claim.save(update_fields=['status'])
        claim.refresh_from_db()
        assert claim.status == PrizeClaim.STATUS_PROCESSING

        claim.status = PrizeClaim.STATUS_PAID
        claim.paid_at = timezone.now()
        claim.save(update_fields=['status', 'paid_at'])
        claim.refresh_from_db()
        assert claim.status == PrizeClaim.STATUS_PAID
        assert claim.paid_at is not None

    def test_payout_method_choices(self):
        methods = [c[0] for c in PrizeClaim.PAYOUT_METHOD_CHOICES]
        assert 'deltacoin' in methods
        assert 'bkash' in methods
        assert 'nagad' in methods
        assert 'rocket' in methods
        assert 'bank' in methods

    def test_str_representation(self, prize_transaction, user):
        claim = PrizeClaim.objects.create(
            prize_transaction=prize_transaction,
            claimed_by=user,
        )
        s = str(claim)
        assert 'hubplayer' in s or str(prize_transaction.id) in s


# ============================================================================
# HubResourcesAPIView Tests
# ============================================================================

class TestHubResourcesAPI:

    def test_unauthenticated_returns_redirect(self, client, tournament):
        url = f'/tournaments/{tournament.slug}/hub/api/resources/'
        resp = client.get(url)
        # LoginRequiredMixin → redirect to login
        assert resp.status_code in (302, 403)

    def test_unregistered_user_denied(self, client, tournament, other_user):
        client.force_login(other_user)
        url = f'/tournaments/{tournament.slug}/hub/api/resources/'
        resp = client.get(url)
        assert resp.status_code == 403

    def test_registered_user_gets_resources(self, client, tournament, user, registration, sponsor):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/resources/'
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()

        # Rules
        assert 'rules' in data
        assert 'Tournament Rules' in data['rules']['text']

        # Social links
        assert 'social_links' in data
        keys = [l['key'] for l in data['social_links']]
        assert 'discord' in keys
        assert 'twitter' in keys

        # Contact
        assert data['contact_email'] == 'org@test.com'

        # Sponsors
        assert len(data['sponsors']) >= 1
        assert data['sponsors'][0]['name'] == 'Acme Gaming'
        assert data['sponsors'][0]['tier'] == 'gold'

    def test_no_inactive_sponsors(self, client, tournament, user, registration):
        TournamentSponsor.objects.create(
            tournament=tournament, name='Hidden', tier='gold', is_active=False,
        )
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/resources/'
        resp = client.get(url)
        data = resp.json()
        names = [s['name'] for s in data['sponsors']]
        assert 'Hidden' not in names


# ============================================================================
# HubPrizeClaimAPIView Tests
# ============================================================================

class TestHubPrizeClaimAPI:

    def test_get_prize_info(self, client, tournament, user, registration, prize_transaction):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()

        assert 'prize_pool' in data
        assert data['prize_pool']['total'] == '10000.00'
        assert data['prize_pool']['currency'] == 'BDT'

        assert len(data['your_prizes']) == 1
        assert data['your_prizes'][0]['placement'] == '1st'
        assert data['your_prizes'][0]['claimed'] is False

    def test_claim_prize_success(self, client, tournament, user, registration, prize_transaction):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({
                'transaction_id': prize_transaction.id,
                'payout_method': 'bkash',
                'payout_destination': '01712345678',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['success'] is True
        assert data['status'] == 'pending'

        # Verify claim exists
        claim = PrizeClaim.objects.get(prize_transaction=prize_transaction)
        assert claim.payout_method == 'bkash'
        assert claim.claimed_by == user

    def test_double_claim_rejected(self, client, tournament, user, registration, prize_transaction):
        PrizeClaim.objects.create(
            prize_transaction=prize_transaction,
            claimed_by=user,
        )
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({'transaction_id': prize_transaction.id}),
            content_type='application/json',
        )
        assert resp.status_code == 409
        assert 'already been claimed' in resp.json()['error']

    def test_invalid_transaction_id(self, client, tournament, user, registration):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({'transaction_id': 99999}),
            content_type='application/json',
        )
        assert resp.status_code == 404

    def test_invalid_payout_method(self, client, tournament, user, registration, prize_transaction):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({
                'transaction_id': prize_transaction.id,
                'payout_method': 'paypal',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'Invalid payout method' in resp.json()['error']

    def test_unregistered_user_cannot_claim(self, client, tournament, other_user, prize_transaction):
        client.force_login(other_user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({'transaction_id': prize_transaction.id}),
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_missing_transaction_id(self, client, tournament, user, registration):
        client.force_login(user)
        url = f'/tournaments/{tournament.slug}/hub/api/prize-claim/'
        resp = client.post(
            url,
            data=json.dumps({}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'required' in resp.json()['error']
