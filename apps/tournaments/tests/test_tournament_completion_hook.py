"""
Auto-finalize hook + organizer recovery + Swiss TOC classification.

Covers the three highest-priority tournament-engine fixes:

* When the last match of a LIVE tournament completes, the lifecycle must
  transition LIVE → COMPLETED automatically (no more "stuck LIVE" state).
* The TOC organizer recovery endpoint must finalize a stuck tournament,
  enforce permissions, and gate `force=True` to superusers.
* Swiss tournaments must NOT be served the bracket-tree tab; they should
  show the Standings tab instead.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.tournaments.models import Match, Tournament
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.lifecycle_service import (
    TournamentLifecycleService,
)


User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='finalize_organizer',
        email='finalize_organizer@test.test',
        password='pass1234',
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='finalize_super',
        email='finalize_super@test.test',
        password='pass1234',
    )


@pytest.fixture
def outsider(db):
    return User.objects.create_user(
        username='finalize_outsider',
        email='finalize_outsider@test.test',
        password='pass1234',
    )


@pytest.fixture
def game(db):
    return Game.objects.create(
        slug='finalize-test-game',
        name='Finalize Test Game',
        is_active=True,
    )


def _make_live_tournament(organizer, game, *, slug, fmt=Tournament.SINGLE_ELIMINATION):
    now = timezone.now()
    return Tournament.objects.create(
        name=f'Finalize {slug}',
        slug=slug,
        organizer=organizer,
        game=game,
        format=fmt,
        participation_type=Tournament.SOLO,
        max_participants=8,
        min_participants=2,
        prize_pool=Decimal('0.00'),
        registration_start=now - timedelta(days=10),
        registration_end=now - timedelta(days=5),
        tournament_start=now - timedelta(days=1),
        status=Tournament.LIVE,
    )


def _make_match(tournament, *, p1, p2, state=Match.SCHEDULED, winner=None):
    loser = None
    if winner is not None:
        loser = p2 if winner.id == p1.id else p1
    return Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=Match.objects.filter(tournament=tournament).count() + 1,
        participant1_id=p1.id,
        participant1_name=p1.username,
        participant2_id=p2.id,
        participant2_name=p2.username,
        state=state,
        winner_id=winner.id if winner else None,
        loser_id=loser.id if loser else None,
        participant1_score=1 if (winner and winner.id == p1.id) else 0,
        participant2_score=1 if (winner and winner.id == p2.id) else 0,
    )


# ---------------------------------------------------------------------------
# Service-level: maybe_finalize_tournament
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaybeFinalizeTournament:
    def test_finalizes_when_all_matches_complete(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='finalize-svc-1')
        p1 = User.objects.create_user(username='svc-p1', email='svc-p1@t.t', password='x')
        p2 = User.objects.create_user(username='svc-p2', email='svc-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.COMPLETED, winner=p1)

        finalized, reason = TournamentLifecycleService.maybe_finalize_tournament(t.id)

        t.refresh_from_db()
        assert finalized is True, reason
        assert t.status == Tournament.COMPLETED
        assert t.tournament_end is not None

    def test_blocks_when_matches_still_incomplete(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='finalize-svc-2')
        p1 = User.objects.create_user(username='svc2-p1', email='svc2-p1@t.t', password='x')
        p2 = User.objects.create_user(username='svc2-p2', email='svc2-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)

        finalized, reason = TournamentLifecycleService.maybe_finalize_tournament(t.id)

        t.refresh_from_db()
        assert finalized is False
        assert t.status == Tournament.LIVE
        assert reason and 'incomplete' in reason.lower()

    def test_idempotent_when_already_completed(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='finalize-svc-3')
        t.status = Tournament.COMPLETED
        t.save(update_fields=['status'])

        finalized, reason = TournamentLifecycleService.maybe_finalize_tournament(t.id)

        assert finalized is False
        assert reason == 'Already completed'

    def test_force_bypasses_guard_with_incomplete_matches(self, organizer, game, superuser):
        t = _make_live_tournament(organizer, game, slug='finalize-svc-4')
        p1 = User.objects.create_user(username='svc4-p1', email='svc4-p1@t.t', password='x')
        p2 = User.objects.create_user(username='svc4-p2', email='svc4-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)

        finalized, _ = TournamentLifecycleService.maybe_finalize_tournament(
            t.id, actor=superuser, force=True,
        )

        t.refresh_from_db()
        assert finalized is True
        assert t.status == Tournament.COMPLETED


# ---------------------------------------------------------------------------
# Bracket hook: completing the final match auto-finalizes the tournament.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBracketHookAutoFinalize:
    def test_completing_last_unlinked_match_finalizes_tournament(self, organizer, game):
        """RR/Swiss/manual: match has no BracketNode, hook still runs."""
        t = _make_live_tournament(organizer, game, slug='hook-rr-1', fmt=Tournament.ROUND_ROBIN)
        p1 = User.objects.create_user(username='hook-rr-p1', email='hook-rr-p1@t.t', password='x')
        p2 = User.objects.create_user(username='hook-rr-p2', email='hook-rr-p2@t.t', password='x')
        m = _make_match(t, p1=p1, p2=p2, state=Match.COMPLETED, winner=p1)

        BracketService.update_bracket_after_match(m)

        t.refresh_from_db()
        assert t.status == Tournament.COMPLETED

    def test_completing_one_of_many_does_not_finalize(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='hook-rr-2', fmt=Tournament.ROUND_ROBIN)
        p1 = User.objects.create_user(username='hook-rr2-p1', email='hook-rr2-p1@t.t', password='x')
        p2 = User.objects.create_user(username='hook-rr2-p2', email='hook-rr2-p2@t.t', password='x')
        # Pending match keeps tournament LIVE
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)
        m_done = _make_match(t, p1=p1, p2=p2, state=Match.COMPLETED, winner=p1)

        BracketService.update_bracket_after_match(m_done)

        t.refresh_from_db()
        assert t.status == Tournament.LIVE


# ---------------------------------------------------------------------------
# TOC API: organizer recovery endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFinalizeAPIEndpoint:
    def _url(self, slug):
        return reverse('toc_api:lifecycle-finalize', kwargs={'slug': slug})

    def test_organizer_can_finalize_when_matches_complete(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='api-finalize-1')
        p1 = User.objects.create_user(username='api1-p1', email='api1-p1@t.t', password='x')
        p2 = User.objects.create_user(username='api1-p2', email='api1-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.COMPLETED, winner=p1)

        client = APIClient()
        client.force_authenticate(user=organizer)
        resp = client.post(self._url(t.slug), {}, format='json')

        assert resp.status_code == 200
        assert resp.data['finalized'] is True
        assert resp.data['status'] == Tournament.COMPLETED

    def test_organizer_cannot_finalize_when_matches_incomplete(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='api-finalize-2')
        p1 = User.objects.create_user(username='api2-p1', email='api2-p1@t.t', password='x')
        p2 = User.objects.create_user(username='api2-p2', email='api2-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)

        client = APIClient()
        client.force_authenticate(user=organizer)
        resp = client.post(self._url(t.slug), {}, format='json')

        assert resp.status_code == 400
        assert resp.data['finalized'] is False
        t.refresh_from_db()
        assert t.status == Tournament.LIVE

    def test_force_finalize_requires_superuser(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='api-finalize-3')
        p1 = User.objects.create_user(username='api3-p1', email='api3-p1@t.t', password='x')
        p2 = User.objects.create_user(username='api3-p2', email='api3-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)

        client = APIClient()
        client.force_authenticate(user=organizer)
        resp = client.post(self._url(t.slug), {'force': True}, format='json')

        assert resp.status_code == 403
        t.refresh_from_db()
        assert t.status == Tournament.LIVE

    def test_superuser_force_bypasses_guard(self, organizer, game, superuser):
        t = _make_live_tournament(organizer, game, slug='api-finalize-4')
        p1 = User.objects.create_user(username='api4-p1', email='api4-p1@t.t', password='x')
        p2 = User.objects.create_user(username='api4-p2', email='api4-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.SCHEDULED)

        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post(self._url(t.slug), {'force': True}, format='json')

        assert resp.status_code == 200
        assert resp.data['finalized'] is True
        t.refresh_from_db()
        assert t.status == Tournament.COMPLETED

    def test_outsider_cannot_finalize(self, organizer, game, outsider):
        t = _make_live_tournament(organizer, game, slug='api-finalize-5')
        p1 = User.objects.create_user(username='api5-p1', email='api5-p1@t.t', password='x')
        p2 = User.objects.create_user(username='api5-p2', email='api5-p2@t.t', password='x')
        _make_match(t, p1=p1, p2=p2, state=Match.COMPLETED, winner=p1)

        client = APIClient()
        client.force_authenticate(user=outsider)
        resp = client.post(self._url(t.slug), {}, format='json')

        assert resp.status_code == 403
        t.refresh_from_db()
        assert t.status == Tournament.LIVE


# ---------------------------------------------------------------------------
# TOC tab classification: Swiss must NOT show Brackets, must show Standings.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSwissTOCClassification:
    def _ctx_for(self, tournament, user):
        from unittest.mock import MagicMock

        from apps.tournaments.views.toc import TOCView
        view = TOCView()
        view.tournament = tournament
        view.request = MagicMock()
        view.request.user = user
        view.kwargs = {'slug': tournament.slug}
        return view.get_context_data()

    def test_swiss_has_no_brackets_tab(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='swiss-tabs-1', fmt='swiss')
        ctx = self._ctx_for(t, organizer)

        tab_ids = {tab['id'] for tab in ctx['toc_tabs']}
        assert 'brackets' not in tab_ids
        assert 'standings' in tab_ids
        assert ctx['has_brackets'] is False
        assert ctx['has_standings'] is True

    def test_single_elim_keeps_brackets_tab(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='se-tabs-1')
        ctx = self._ctx_for(t, organizer)

        tab_ids = {tab['id'] for tab in ctx['toc_tabs']}
        assert 'brackets' in tab_ids
        assert ctx['has_brackets'] is True
        assert ctx['has_standings'] is False

    def test_round_robin_has_standings_no_brackets(self, organizer, game):
        t = _make_live_tournament(organizer, game, slug='rr-tabs-1', fmt=Tournament.ROUND_ROBIN)
        ctx = self._ctx_for(t, organizer)

        tab_ids = {tab['id'] for tab in ctx['toc_tabs']}
        assert 'brackets' not in tab_ids
        assert 'standings' in tab_ids


# ---------------------------------------------------------------------------
# DE Grand Finals Reset correctness.
#
# Bracket layout used by these tests:
#
#     WB Final ──┐                   (child1 of GF, parent_slot=1)
#                ├──> GF ──> GFR (is_bye=True)
#     LB Final ──┘                   (child2 of GF, parent_slot=2)
#
# Rules under test:
#   * WB finalist (slot 1) wins GF → no reset, GFR stays a bye.
#   * LB finalist (slot 2) wins GF → reset is scheduled with both finalists.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDEGrandFinalReset:
    def _build_de_gf_fixture(self, organizer, game, slug):
        from apps.brackets.models import Bracket, BracketNode

        t = _make_live_tournament(
            organizer, game, slug=slug, fmt=Tournament.DOUBLE_ELIMINATION,
        )
        bracket = Bracket.objects.create(
            tournament=t,
            format=Bracket.DOUBLE_ELIMINATION,
            total_rounds=4,
            total_matches=4,
        )

        wb_winner = User.objects.create_user(
            username=f'{slug}-wb', email=f'{slug}-wb@t.t', password='x',
        )
        lb_winner = User.objects.create_user(
            username=f'{slug}-lb', email=f'{slug}-lb@t.t', password='x',
        )

        # Pre-completed feeder matches so the only remaining work is the GF.
        wb_final_match = _make_match(
            t, p1=wb_winner, p2=lb_winner, state=Match.COMPLETED, winner=wb_winner,
        )
        lb_final_match = _make_match(
            t, p1=lb_winner, p2=wb_winner, state=Match.COMPLETED, winner=lb_winner,
        )

        wb_final_node = BracketNode.objects.create(
            bracket=bracket, position=1,
            round_number=1, match_number_in_round=1,
            bracket_type=BracketNode.MAIN,
            participant1_id=wb_winner.id, participant1_name=wb_winner.username,
            participant2_id=lb_winner.id, participant2_name=lb_winner.username,
            winner_id=wb_winner.id,
            match=wb_final_match,
        )
        lb_final_node = BracketNode.objects.create(
            bracket=bracket, position=2,
            round_number=1, match_number_in_round=1,
            bracket_type=BracketNode.LOSERS,
            participant1_id=lb_winner.id, participant1_name=lb_winner.username,
            participant2_id=wb_winner.id, participant2_name=wb_winner.username,
            winner_id=lb_winner.id,
            match=lb_final_match,
        )
        gfr_node = BracketNode.objects.create(
            bracket=bracket, position=4,
            round_number=3, match_number_in_round=1,
            bracket_type=BracketNode.MAIN,
            is_bye=True,
        )
        gf_match = _make_match(t, p1=wb_winner, p2=lb_winner)  # SCHEDULED
        gf_node = BracketNode.objects.create(
            bracket=bracket, position=3,
            round_number=2, match_number_in_round=1,
            bracket_type=BracketNode.MAIN,
            participant1_id=wb_winner.id, participant1_name=wb_winner.username,
            participant2_id=lb_winner.id, participant2_name=lb_winner.username,
            child1_node=wb_final_node, child2_node=lb_final_node,
            parent_node=gfr_node, parent_slot=1,
            match=gf_match,
        )
        wb_final_node.parent_node = gf_node
        wb_final_node.parent_slot = 1
        wb_final_node.save(update_fields=['parent_node', 'parent_slot'])
        lb_final_node.parent_node = gf_node
        lb_final_node.parent_slot = 2
        lb_final_node.save(update_fields=['parent_node', 'parent_slot'])

        return {
            'tournament': t,
            'bracket': bracket,
            'wb_winner': wb_winner,
            'lb_winner': lb_winner,
            'gf_match': gf_match,
            'gf_node': gf_node,
            'gfr_node': gfr_node,
        }

    def _complete_match(self, match, winner, loser):
        match.state = Match.COMPLETED
        match.winner_id = winner.id
        match.loser_id = loser.id
        match.participant1_score = 1 if match.participant1_id == winner.id else 0
        match.participant2_score = 1 if match.participant2_id == winner.id else 0
        match.save()

    def test_wb_winner_wins_gf_does_not_schedule_reset(self, organizer, game):
        from apps.brackets.models import BracketNode

        f = self._build_de_gf_fixture(organizer, game, 'de-wb-wins')
        self._complete_match(f['gf_match'], winner=f['wb_winner'], loser=f['lb_winner'])

        BracketService.update_bracket_after_match(f['gf_match'])

        gfr = BracketNode.objects.get(id=f['gfr_node'].id)
        assert gfr.is_bye is True, 'GFR should remain a bye when WB finalist wins GF'
        assert gfr.participant1_id is None
        assert gfr.participant2_id is None
        assert gfr.match_id is None, 'No reset Match should be scheduled'

        # Tournament should auto-finalize: the GF was the last outstanding match.
        f['tournament'].refresh_from_db()
        assert f['tournament'].status == Tournament.COMPLETED

    def test_lb_winner_wins_gf_schedules_reset_match(self, organizer, game):
        from apps.brackets.models import BracketNode

        f = self._build_de_gf_fixture(organizer, game, 'de-lb-wins')
        self._complete_match(f['gf_match'], winner=f['lb_winner'], loser=f['wb_winner'])

        BracketService.update_bracket_after_match(f['gf_match'])

        gfr = BracketNode.objects.get(id=f['gfr_node'].id)
        assert gfr.is_bye is False, 'GFR should activate when LB finalist wins GF'
        # Both finalists must be seeded — one per slot, regardless of order.
        seeded = {gfr.participant1_id, gfr.participant2_id}
        assert seeded == {f['wb_winner'].id, f['lb_winner'].id}
        assert gfr.match_id is not None, 'Reset Match must be scheduled'

        reset_match = Match.objects.get(id=gfr.match_id)
        assert reset_match.state == Match.SCHEDULED
        assert {reset_match.participant1_id, reset_match.participant2_id} == {
            f['wb_winner'].id, f['lb_winner'].id,
        }

        # Tournament must NOT finalize until the reset match completes.
        f['tournament'].refresh_from_db()
        assert f['tournament'].status == Tournament.LIVE

    def test_lb_wins_then_reset_completes_finalizes_tournament(self, organizer, game):
        from apps.brackets.models import BracketNode

        f = self._build_de_gf_fixture(organizer, game, 'de-lb-then-reset')
        self._complete_match(f['gf_match'], winner=f['lb_winner'], loser=f['wb_winner'])
        BracketService.update_bracket_after_match(f['gf_match'])

        gfr = BracketNode.objects.get(id=f['gfr_node'].id)
        reset_match = Match.objects.get(id=gfr.match_id)

        # LB winner wins reset too (becomes overall champion).
        self._complete_match(reset_match, winner=f['lb_winner'], loser=f['wb_winner'])
        BracketService.update_bracket_after_match(reset_match)

        f['tournament'].refresh_from_db()
        assert f['tournament'].status == Tournament.COMPLETED
