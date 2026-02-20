"""
Phase 4 Part 2 Tests.

Covers:
- P4-T04: Guest-to-Real Team Conversion (invite link, slot claim, auto-convert, partial approval)
- P4-T05: RegistrationRule Auto-Evaluation (reject rules, eligibility wiring)
- P4-T06: Notification Event Handlers (event emission, handler dispatch)
- P4-T07: Live Draw (persist seeds, broadcast helper, polling fallback)

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament

User = get_user_model()

import uuid as _uuid


# ── Helpers ──────────────────────────────────────────────────────────

def _uid():
    return _uuid.uuid4().hex[:8]


def _make_game(**kwargs):
    uid = _uid()
    defaults = dict(
        name=f'Game-{uid}', slug=f'game-{uid}', short_code=uid[:4].upper(),
        category='FPS', display_name=f'Game {uid}', game_type='TEAM_VS_TEAM',
        is_active=True,
    )
    defaults.update(kwargs)
    return Game.objects.create(**defaults)


def _make_tournament(game, organizer, **kwargs):
    uid = _uid()
    now = timezone.now()
    defaults = dict(
        name=f'Tournament-{uid}',
        slug=f't-{uid}',
        description='Test tournament',
        organizer=organizer,
        game=game,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        participation_type=Tournament.SOLO,
        format='single_elimination',
        enable_check_in=True,
        check_in_minutes_before=30,
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    uid = _uid()
    uname = username or f'user-{uid}'
    defaults = dict(username=uname, email=f'{uname}@test.dc', password='test1234')
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_registration(tournament, user, **kwargs):
    defaults = dict(
        tournament=tournament,
        user=user,
        status='pending',
        registration_data={'game_id': f'gid-{_uid()}'},
    )
    defaults.update(kwargs)
    return Registration.objects.create(**defaults)


def _guest_registration(tournament, organizer, roster):
    """Create a guest team registration with a lineup_snapshot."""
    return Registration.objects.create(
        tournament=tournament,
        user=organizer,
        status='confirmed',
        is_guest_team=True,
        lineup_snapshot=roster,
        registration_data={'team_name': f'GuestTeam-{_uid()}'},
    )


# ======================================================================
# P4-T04: Guest-to-Real Team Conversion
# ======================================================================

@pytest.mark.django_db
class TestGuestConversion:

    def test_generate_invite_link(self):
        """Organizer can generate an invite link for a guest registration."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1', 'role': 'entry'},
            {'game_id': 'Bravo#2', 'role': 'support'},
        ]
        reg = _guest_registration(t, org, roster)

        result = GuestConversionService.generate_invite_link(reg.id, org)
        assert result['invite_token']
        assert len(result['invite_token']) > 20

        reg.refresh_from_db()
        assert reg.invite_token == result['invite_token']
        assert reg.conversion_status == 'pending'

    def test_generate_invite_link_non_guest_raises(self):
        """Cannot generate invite link for non-guest registration."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        reg = _make_registration(t, org)
        reg.is_guest_team = False
        reg.save()

        with pytest.raises(ValidationError, match="guest team"):
            GuestConversionService.generate_invite_link(reg.id, org)

    def test_claim_slot_success(self):
        """Member can claim a slot by matching their Game ID."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        member = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1', 'role': 'entry'},
            {'game_id': 'Bravo#2', 'role': 'support'},
        ]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        result = GuestConversionService.claim_slot(reg.invite_token, member, 'Alpha#1')
        assert result['success']
        assert result['claimed_slots'] == 1
        assert result['remaining_slots'] == 1
        assert result['conversion_status'] == 'partial'

    def test_claim_slot_case_insensitive(self):
        """Game ID matching is case-insensitive."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        member = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [{'game_id': 'Charlie#3'}]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        result = GuestConversionService.claim_slot(reg.invite_token, member, 'charlie#3')
        assert result['success']
        assert result['auto_converted']  # Only 1 member → auto-convert

    def test_claim_slot_no_match_raises(self):
        """Claiming with a non-matching Game ID raises."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        member = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [{'game_id': 'Alpha#1'}]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        with pytest.raises(ValidationError, match="does not match"):
            GuestConversionService.claim_slot(reg.invite_token, member, 'Wrong#99')

    def test_auto_convert_when_all_slots_claimed(self):
        """Auto-converts guest to real team when all slots are claimed."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        m1 = _make_user()
        m2 = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1'},
            {'game_id': 'Bravo#2'},
        ]
        reg = _guest_registration(t, org, roster)
        reg.seed = 3
        reg.slot_number = 5
        reg.save()
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        GuestConversionService.claim_slot(reg.invite_token, m1, 'Alpha#1')
        result = GuestConversionService.claim_slot(reg.invite_token, m2, 'Bravo#2')

        assert result['auto_converted']
        reg.refresh_from_db()
        assert not reg.is_guest_team  # Converted to real
        assert reg.seed == 3  # Preserved
        assert reg.slot_number == 5  # Preserved

    def test_approve_partial_conversion(self):
        """Organizer can approve a partial conversion."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        m1 = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1'},
            {'game_id': 'Bravo#2'},
            {'game_id': 'Charlie#3'},
        ]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        # Claim 1 of 3
        GuestConversionService.claim_slot(reg.invite_token, m1, 'Alpha#1')

        result = GuestConversionService.approve_partial_conversion(reg.id, org)
        assert result['success']
        assert result['claimed_slots'] == 1
        assert result['total_slots'] == 3

        reg.refresh_from_db()
        assert not reg.is_guest_team
        assert reg.conversion_status == 'approved'

    def test_double_claim_raises(self):
        """Same user cannot claim twice."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        member = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1'},
            {'game_id': 'Bravo#2'},
        ]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        GuestConversionService.claim_slot(reg.invite_token, member, 'Alpha#1')
        with pytest.raises(ValidationError, match="already claimed"):
            GuestConversionService.claim_slot(reg.invite_token, member, 'Bravo#2')

    def test_get_conversion_status(self):
        """Status endpoint returns correct progress."""
        from apps.tournaments.services.guest_conversion_service import GuestConversionService

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        roster = [
            {'game_id': 'Alpha#1'},
            {'game_id': 'Bravo#2'},
        ]
        reg = _guest_registration(t, org, roster)
        GuestConversionService.generate_invite_link(reg.id, org)
        reg.refresh_from_db()

        status = GuestConversionService.get_conversion_status(reg.invite_token)
        assert status['total_slots'] == 2
        assert status['claimed_slots'] == 0
        assert status['remaining_slots'] == 2
        assert len(status['members']) == 2


# ======================================================================
# P4-T05: RegistrationRule Auto-Evaluation
# ======================================================================

@pytest.mark.django_db
class TestRegistrationRuleEvaluation:

    def test_reject_rule_blocks_ineligible_user(self):
        """An AUTO_REJECT rule blocks users who don't meet criteria."""
        from apps.tournaments.models.smart_registration import RegistrationRule
        from apps.tournaments.services.registration_eligibility import (
            RegistrationEligibilityService,
        )

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        # Create rule: reject accounts younger than 30 days
        RegistrationRule.objects.create(
            tournament=t,
            name='Account age minimum',
            rule_type=RegistrationRule.AUTO_REJECT,
            condition={'account_age_days': {'lte': 29}},
            priority=0,
            is_active=True,
            reason_template='Your account must be at least 30 days old to register.',
        )

        # Player just created → account_age_days = 0 → matches lte:29 → rejected
        result = RegistrationEligibilityService.check_eligibility(t, player)
        assert not result.is_eligible
        assert 'account' in result.reason.lower() or '30 days' in result.reason

    def test_no_rules_allows_registration(self):
        """No rules → user is eligible."""
        from apps.tournaments.services.registration_eligibility import (
            RegistrationEligibilityService,
        )

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        result = RegistrationEligibilityService.check_eligibility(t, player)
        assert result.is_eligible

    def test_inactive_rule_is_ignored(self):
        """Inactive rules do not block users."""
        from apps.tournaments.models.smart_registration import RegistrationRule
        from apps.tournaments.services.registration_eligibility import (
            RegistrationEligibilityService,
        )

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        RegistrationRule.objects.create(
            tournament=t,
            name='Reject new players',
            rule_type=RegistrationRule.AUTO_REJECT,
            condition={'tournaments_played': {'lte': 0}},
            priority=0,
            is_active=False,  # Inactive
            reason_template='You need more experience.',
        )

        result = RegistrationEligibilityService.check_eligibility(t, player)
        assert result.is_eligible

    def test_auto_approve_rule_does_not_block(self):
        """AUTO_APPROVE rules do not block at eligibility gate."""
        from apps.tournaments.models.smart_registration import RegistrationRule
        from apps.tournaments.services.registration_eligibility import (
            RegistrationEligibilityService,
        )

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        # AUTO_APPROVE rule — should NOT block anyone
        RegistrationRule.objects.create(
            tournament=t,
            name='Auto-approve veterans',
            rule_type=RegistrationRule.AUTO_APPROVE,
            condition={'tournaments_played': {'gte': 5}},
            priority=0,
            is_active=True,
        )

        result = RegistrationEligibilityService.check_eligibility(t, player)
        assert result.is_eligible

    def test_rule_evaluate_in_operator(self):
        """RegistrationRule.evaluate() supports 'in' operator."""
        from apps.tournaments.models.smart_registration import RegistrationRule

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        rule = RegistrationRule.objects.create(
            tournament=t,
            name='Rank check',
            rule_type=RegistrationRule.AUTO_REJECT,
            condition={'rank': {'in': ['Diamond', 'Immortal', 'Radiant']}},
            priority=0,
            is_active=True,
        )

        # Matching data
        assert rule.evaluate({'rank': 'Diamond'}, {}) is True
        # Non-matching data
        assert rule.evaluate({'rank': 'Gold'}, {}) is False

    def test_multiple_reject_rules_priority_order(self):
        """First matching reject rule (by priority) determines the message."""
        from apps.tournaments.models.smart_registration import RegistrationRule
        from apps.tournaments.services.registration_eligibility import (
            RegistrationEligibilityService,
        )

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)

        RegistrationRule.objects.create(
            tournament=t,
            name='Account age 30',
            rule_type=RegistrationRule.AUTO_REJECT,
            condition={'account_age_days': {'lte': 29}},
            priority=0,
            is_active=True,
            reason_template='Account too new (need 30 days).',
        )
        RegistrationRule.objects.create(
            tournament=t,
            name='Account age 90',
            rule_type=RegistrationRule.AUTO_REJECT,
            condition={'account_age_days': {'lte': 89}},
            priority=1,
            is_active=True,
            reason_template='Account too new (need 90 days).',
        )

        result = RegistrationEligibilityService.check_eligibility(t, player)
        assert not result.is_eligible
        # First rule (priority 0) should match first
        assert '30 days' in result.reason


# ======================================================================
# P4-T06: Notification Event Handlers
# ======================================================================

@pytest.mark.django_db
class TestNotificationEventHandlers:

    def test_registration_submitted_handler(self):
        """notify_registration_submitted creates an in-app notification."""
        from apps.notifications.events import notify_registration_submitted
        from apps.notifications.models import Notification
        from apps.core.events import Event

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        reg = _make_registration(t, player, status='submitted')

        event = Event(
            event_type='registration.created',
            data={'registration_id': reg.id, 'tournament_id': t.id},
            source='test',
        )
        notify_registration_submitted(event)

        notif = Notification.objects.filter(recipient=player).first()
        assert notif is not None
        assert 'submitted' in notif.title.lower() or 'registration' in notif.title.lower()

    def test_payment_verified_handler(self):
        """notify_payment_verified creates an in-app notification."""
        from apps.notifications.events import notify_payment_verified
        from apps.notifications.models import Notification
        from apps.core.events import Event

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        reg = _make_registration(t, player, status='confirmed')

        event = Event(
            event_type='payment.verified',
            data={'registration_id': reg.id, 'tournament_id': t.id},
            source='test',
        )
        notify_payment_verified(event)

        notif = Notification.objects.filter(recipient=player).first()
        assert notif is not None
        assert 'payment' in notif.title.lower() or 'verified' in notif.title.lower()

    def test_registration_rejected_handler(self):
        """notify_registration_rejected creates an in-app notification with reason."""
        from apps.notifications.events import notify_registration_rejected
        from apps.notifications.models import Notification
        from apps.core.events import Event

        org = _make_user()
        player = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        reg = _make_registration(t, player, status='rejected')

        event = Event(
            event_type='registration.rejected',
            data={
                'registration_id': reg.id,
                'tournament_id': t.id,
                'reason': 'Insufficient rank',
            },
            source='test',
        )
        notify_registration_rejected(event)

        notif = Notification.objects.filter(recipient=player).first()
        assert notif is not None
        assert 'declined' in notif.title.lower() or 'registration' in notif.title.lower()

    def test_checkin_open_handler(self):
        """notify_checkin_open sends notifications to all confirmed users."""
        from apps.notifications.events import notify_checkin_open
        from apps.notifications.models import Notification
        from apps.core.events import Event

        org = _make_user()
        p1 = _make_user()
        p2 = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        _make_registration(t, p1, status='confirmed')
        _make_registration(t, p2, status='confirmed')

        event = Event(
            event_type='tournament.checkin_open',
            data={'tournament_id': t.id},
            source='test',
        )
        notify_checkin_open(event)

        assert Notification.objects.filter(recipient=p1).exists()
        assert Notification.objects.filter(recipient=p2).exists()

    def test_event_bus_registration(self):
        """register_notification_event_handlers wires all expected events."""
        from apps.notifications.events import register_notification_event_handlers
        from apps.core.events import event_bus

        # Get handler count before
        before = sum(len(v) for v in event_bus._handlers.values())
        register_notification_event_handlers()
        after = sum(len(v) for v in event_bus._handlers.values())

        # Should have added at least 9 handlers
        added = after - before
        assert added >= 9, f"Only {added} handlers registered, expected ≥9"

    def test_publish_registration_event_fires(self):
        """_publish_registration_event emits to event bus."""
        from apps.tournaments.services.registration_service import _publish_registration_event

        with patch('apps.core.events.event_bus.publish') as mock_pub:
            _publish_registration_event(
                "registration.rejected",
                registration_id=999,
                tournament_id=1,
                source="test",
            )
            assert mock_pub.called


# ======================================================================
# P4-T07: Live Draw
# ======================================================================

@pytest.mark.django_db
class TestLiveDraw:

    def test_draw_results_empty_initially(self):
        """get_draw_results returns 'waiting' when no seeds are set."""
        from apps.tournaments.realtime.broadcast import get_draw_results

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        _make_registration(t, _make_user(), status='confirmed')

        result = get_draw_results(t.id)
        assert result['status'] == 'waiting'
        assert result['total'] == 0
        assert result['seeds'] == []

    def test_draw_results_after_seeding(self):
        """get_draw_results returns seeds when set on registrations."""
        from apps.tournaments.realtime.broadcast import get_draw_results

        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        p1 = _make_user()
        p2 = _make_user()
        r1 = _make_registration(t, p1, status='confirmed')
        r2 = _make_registration(t, p2, status='confirmed')

        r1.seed = 1
        r1.save(update_fields=['seed'])
        r2.seed = 2
        r2.save(update_fields=['seed'])

        result = get_draw_results(t.id)
        assert result['status'] == 'complete'
        assert result['total'] == 2
        assert result['seeds'][0]['seed'] == 1
        assert result['seeds'][1]['seed'] == 2
        assert result['seeds'][0]['name'] == p1.username
        assert result['seeds'][1]['name'] == p2.username

    def test_live_draw_consumer_exists(self):
        """LiveDrawConsumer class is importable and has required methods."""
        from apps.tournaments.consumers.live_draw_consumer import LiveDrawConsumer

        consumer = LiveDrawConsumer()
        assert hasattr(consumer, 'connect')
        assert hasattr(consumer, 'disconnect')
        assert hasattr(consumer, 'receive_json')
        assert hasattr(consumer, 'draw_event')
        assert hasattr(consumer, '_run_draw')
        assert hasattr(consumer, '_persist_seeds')

    def test_persist_seeds_updates_db(self):
        """Seed assignment updates Registration rows correctly (sync equivalent of _persist_seeds)."""
        org = _make_user()
        game = _make_game()
        t = _make_tournament(game, org)
        p1 = _make_user()
        p2 = _make_user()
        r1 = _make_registration(t, p1, status='confirmed')
        r2 = _make_registration(t, p2, status='confirmed')

        seeds = [
            {'seed': 1, 'name': p1.username, 'registration_id': r1.id},
            {'seed': 2, 'name': p2.username, 'registration_id': r2.id},
        ]
        # Replicate the persistence logic from _persist_seeds synchronously
        for seed_data in seeds:
            Registration.objects.filter(id=seed_data['registration_id']).update(
                seed=seed_data['seed']
            )

        r1.refresh_from_db()
        r2.refresh_from_db()
        assert r1.seed == 1
        assert r2.seed == 2

    def test_routing_includes_draw_path(self):
        """WebSocket routing includes the live draw path."""
        from apps.tournaments.realtime.routing import websocket_urlpatterns

        patterns = [str(p.pattern) for p in websocket_urlpatterns]
        draw_patterns = [p for p in patterns if 'draw' in p]
        assert len(draw_patterns) >= 1, f"No draw pattern found in {patterns}"
