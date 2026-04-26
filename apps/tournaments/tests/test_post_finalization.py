"""
Post-Finalization pipeline tests.

Covers Phase 1–7 of the unified post-completion lifecycle:

* Phase 1 — Authoritative completion rule persists Tournament.status=COMPLETED
* Phase 2 — Pipeline populates final_standings, achievements, announcement
* Phase 3 — Auto-trigger via maybe_finalize_tournament + FinalizeView
* Phase 4 — HUB Command Center renders Champion card (no opponent prompt)
* Phase 5 — Prize page exposes winner names through PrizeConfigService
* Phase 6 — Idempotency (double-run mints no duplicates)

All tests use the public service entry points — no internal helpers.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.games.models import Game
from apps.tournaments.models import (
    Match,
    Registration,
    Tournament,
    TournamentAnnouncement,
)
from apps.tournaments.models.result import TournamentResult
from apps.tournaments.services.lifecycle_service import (
    TournamentLifecycleService,
)
from apps.tournaments.services.post_finalization_service import (
    PostFinalizationService,
)
from apps.tournaments.services.prize_config_service import PrizeConfigService

User = get_user_model()


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='pf_organizer',
        email='pf_organizer@test.test',
        password='pass1234',
    )


@pytest.fixture
def player_one(db):
    return User.objects.create_user(
        username='pf_p1', email='pf_p1@test.test', password='pass1234',
    )


@pytest.fixture
def player_two(db):
    return User.objects.create_user(
        username='pf_p2', email='pf_p2@test.test', password='pass1234',
    )


@pytest.fixture
def game(db):
    return Game.objects.create(
        slug='pf-game', name='PF Game', is_active=True,
    )


def _make_tournament(organizer, game, *, slug, status=Tournament.LIVE):
    now = timezone.now()
    return Tournament.objects.create(
        name=f'PF {slug}',
        slug=slug,
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIMINATION,
        participation_type=Tournament.SOLO,
        max_participants=8,
        min_participants=2,
        prize_pool=Decimal('1000.00'),
        prize_currency='USD',
        registration_start=now - timedelta(days=10),
        registration_end=now - timedelta(days=5),
        tournament_start=now - timedelta(days=1),
        status=status,
    )


def _make_registration(tournament, user):
    return Registration.objects.create(
        tournament=tournament,
        user=user,
        status=Registration.CONFIRMED,
        registration_data={},
    )


def _make_completed_match(tournament, *, winner_reg, loser_reg):
    return Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=Match.objects.filter(tournament=tournament).count() + 1,
        participant1_id=winner_reg.id,
        participant1_name=winner_reg.user.username,
        participant2_id=loser_reg.id,
        participant2_name=loser_reg.user.username,
        state=Match.COMPLETED,
        winner_id=winner_reg.id,
        loser_id=loser_reg.id,
        participant1_score=2,
        participant2_score=1,
    )


def _make_result_with_winner(tournament, winner_reg, runner_up_reg=None):
    return TournamentResult.objects.create(
        tournament=tournament,
        winner=winner_reg,
        runner_up=runner_up_reg,
        determination_method='normal',
    )


# ── Phase 1: completion persistence ─────────────────────────────────────────


@pytest.mark.django_db
class TestCompletionPersistence:

    def test_tournament_result_with_winner_persists_completed(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-persist-1')
        winner = _make_registration(t, player_one)
        loser = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=winner, loser_reg=loser)
        _make_result_with_winner(t, winner, loser)

        report = PostFinalizationService.run(t)

        t.refresh_from_db()
        assert report.status_persisted is True
        assert t.status == Tournament.COMPLETED
        assert t.tournament_end is not None

    def test_no_winner_blocks_persistence_when_finals_not_resolved(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-persist-2')
        winner_reg = _make_registration(t, player_one)
        loser_reg = _make_registration(t, player_two)
        # Match still scheduled, no result yet → cannot complete
        Match.objects.create(
            tournament=t,
            round_number=1, match_number=1,
            participant1_id=winner_reg.id, participant1_name='W',
            participant2_id=loser_reg.id, participant2_name='L',
            state=Match.SCHEDULED,
        )

        report = PostFinalizationService.run(t)
        t.refresh_from_db()

        assert t.status == Tournament.LIVE
        assert report.status_persisted is False
        assert any('completion' in err for err in report.errors)


# ── Phase 2: pipeline populates standings + achievements + announcement ────


@pytest.mark.django_db
class TestPipelinePopulatesAll:

    def test_standings_persisted(self, organizer, game, player_one, player_two):
        t = _make_tournament(organizer, game, slug='pf-pipeline-standings')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        report = PostFinalizationService.run(t)

        result = TournamentResult.objects.get(tournament=t)
        assert report.standings_count >= 2
        assert len(result.final_standings) >= 2
        assert result.final_standings[0]['placement'] == 1
        assert result.final_standings[0]['registration_id'] == w.pk

    def test_achievements_minted_for_podium(
        self, organizer, game, player_one, player_two,
    ):
        from apps.user_profile.models_main import Achievement

        t = _make_tournament(organizer, game, slug='pf-pipeline-achievements')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        PostFinalizationService.run(t)

        champ = Achievement.objects.filter(
            user=player_one, name='Champion',
            context__tournament_id=t.id,
        ).first()
        runner_up = Achievement.objects.filter(
            user=player_two, name='Runner-Up',
            context__tournament_id=t.id,
        ).first()

        assert champ is not None
        assert champ.rarity == 'legendary'
        assert champ.context['placement'] == 1
        assert runner_up is not None
        assert runner_up.context['placement'] == 2

    def test_announcement_published_with_champion_and_runner_up(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-pipeline-announcement')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        report = PostFinalizationService.run(t)

        assert report.announcement_id is not None
        ann = TournamentAnnouncement.objects.get(pk=report.announcement_id)
        assert player_one.username in ann.message
        assert player_two.username in ann.message
        assert 'Champion' in ann.message
        assert ann.is_pinned is True


# ── Phase 3: auto-trigger via maybe_finalize_tournament ────────────────────


@pytest.mark.django_db
class TestAutoTriggerViaLifecycle:

    def test_maybe_finalize_runs_post_finalization(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-auto-trigger-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        ok, _ = TournamentLifecycleService.maybe_finalize_tournament(t.id)

        assert ok is True
        t.refresh_from_db()
        # final_standings populated → pipeline ran
        result = TournamentResult.objects.get(tournament=t)
        assert len(result.final_standings) >= 2
        # announcement published
        assert TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).exists()

    def test_idempotent_path_runs_post_finalization_when_already_completed(
        self, organizer, game, player_one, player_two,
    ):
        """
        Already-COMPLETED tournament re-runs the pipeline so partial prior
        runs converge (e.g. announcement was missing).
        """
        t = _make_tournament(
            organizer, game, slug='pf-auto-trigger-2',
            status=Tournament.COMPLETED,
        )
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        # Manually break: no announcement yet, no standings
        assert not TournamentAnnouncement.objects.filter(tournament=t).exists()

        ok, reason = TournamentLifecycleService.maybe_finalize_tournament(t.id)

        # Already completed → ok=False but pipeline still ran
        assert ok is False
        assert reason == 'Already completed'
        assert TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).exists()


# ── Phase 4: HUB Command Center renders Champion card ──────────────────────


@pytest.mark.django_db
class TestHubCommandCenterCompletedState:

    def test_completed_tournament_renders_champion_card_for_winner(
        self, organizer, game, player_one, player_two,
    ):
        from apps.tournaments.views.hub import _resolve_hub_command_center

        t = _make_tournament(organizer, game, slug='pf-hub-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)
        PostFinalizationService.run(t)
        t.refresh_from_db()

        payload = _resolve_hub_command_center(
            t, registration=w, user=player_one,
        )

        assert payload['show'] is True
        assert payload['outcome_state'] == 'champion'
        assert payload['countdown_text'] == 'COMPLETED'
        assert 'Champion' in payload['title']
        # No opponent assignment
        assert payload['opponent_name'] == ''

    def test_completed_tournament_no_opponent_assignment_for_eliminated(
        self, organizer, game, player_one, player_two,
    ):
        """Even a non-finalist must NOT see 'Awaiting opponent assignment'."""
        from apps.tournaments.views.hub import _resolve_hub_command_center

        t = _make_tournament(organizer, game, slug='pf-hub-2')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        # Third user who lost early
        loser_user = User.objects.create_user(
            username='pf_eliminated', email='pf_eliminated@t.t', password='x',
        )
        elim_reg = _make_registration(t, loser_user)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)
        PostFinalizationService.run(t)
        t.refresh_from_db()

        payload = _resolve_hub_command_center(
            t, registration=elim_reg, user=loser_user,
        )

        assert payload['show'] is True
        assert payload['lobby_state'] == 'completed'
        assert 'Awaiting opponent' not in payload.get('subtitle', '')
        assert payload['cta_label'] == 'View Final Standings'

    def test_runner_up_card_for_runner_up_participant(
        self, organizer, game, player_one, player_two,
    ):
        from apps.tournaments.views.hub import _resolve_hub_command_center

        t = _make_tournament(organizer, game, slug='pf-hub-3')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)
        PostFinalizationService.run(t)
        t.refresh_from_db()

        payload = _resolve_hub_command_center(
            t, registration=l, user=player_two,
        )
        assert payload['outcome_state'] == 'runner_up'


# ── Phase 5: Prize page integration ────────────────────────────────────────


@pytest.mark.django_db
class TestPrizePageWinners:

    def test_public_prize_payload_exposes_winner_names_after_pipeline(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-prize-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        # Before pipeline runs, finalized may be False or winners absent
        PostFinalizationService.run(t)
        t.refresh_from_db()
        payload = PrizeConfigService.public_payload(t)

        assert payload['finalized'] is True
        # The champion placement (rank=1) should expose winner.team_name
        rank1 = next((p for p in payload['placements'] if p['rank'] == 1), None)
        assert rank1 is not None
        assert rank1['winner'] is not None
        assert rank1['winner']['team_name'] == player_one.username


# ── Phase 6 / Phase 7: Idempotency — double-run mints no duplicates ────────


@pytest.mark.django_db
class TestIdempotency:

    def test_double_run_creates_no_duplicate_announcements(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-idem-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        r1 = PostFinalizationService.run(t)
        t.refresh_from_db()
        r2 = PostFinalizationService.run(t)

        ann_count = TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).count()
        assert ann_count == 1
        assert r1.announcement_id == r2.announcement_id

    def test_double_run_creates_no_duplicate_achievements(
        self, organizer, game, player_one, player_two,
    ):
        from apps.user_profile.models_main import Achievement

        t = _make_tournament(organizer, game, slug='pf-idem-2')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        PostFinalizationService.run(t)
        PostFinalizationService.run(t)
        PostFinalizationService.run(t)

        champ_count = Achievement.objects.filter(
            user=player_one, name='Champion',
            context__tournament_id=t.id,
        ).count()
        runner_count = Achievement.objects.filter(
            user=player_two, name='Runner-Up',
            context__tournament_id=t.id,
        ).count()
        assert champ_count == 1
        assert runner_count == 1

    def test_double_run_does_not_change_status_or_tournament_end(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='pf-idem-3')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        PostFinalizationService.run(t)
        t.refresh_from_db()
        first_end = t.tournament_end

        PostFinalizationService.run(t)
        t.refresh_from_db()

        assert t.status == Tournament.COMPLETED
        # tournament_end was set on first run; second run must not bump it.
        assert t.tournament_end == first_end


# ── Auto-convergence: status=LIVE + winner exists → all surfaces show completed


@pytest.mark.django_db
class TestAutoConvergenceWhenStatusStillLive:
    """
    Regression coverage for the "TOC says LIVE despite winner" symptom.

    Setup: TournamentResult with winner exists, but Tournament.status is
    still LIVE (auto-finalize never ran or was rolled back). Every overview
    surface — TOC overview status, TOC lifecycle stepper, HUB lifecycle
    pipeline, HUB command center — must converge to "completed" without
    requiring a manual finalize click.
    """

    def _make_live_with_winner(self, organizer, game, slug):
        t = _make_tournament(organizer, game, slug=slug)
        # Status is intentionally left LIVE.
        assert t.status == Tournament.LIVE

        u_a = User.objects.create_user(
            username=f'{slug}-a', email=f'{slug}-a@t.t', password='x',
        )
        u_b = User.objects.create_user(
            username=f'{slug}-b', email=f'{slug}-b@t.t', password='x',
        )
        w = _make_registration(t, u_a)
        l = _make_registration(t, u_b)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)
        return t, u_a, u_b, w, l

    def test_completion_truth_predicate_fires_on_winner(
        self, organizer, game,
    ):
        from apps.tournaments.services.completion_truth import (
            is_tournament_effectively_completed,
        )
        t, *_ = self._make_live_with_winner(organizer, game, 'conv-truth')
        assert is_tournament_effectively_completed(t) is True

    def test_completion_payload_exposes_winner_when_status_still_live(
        self, organizer, game,
    ):
        from apps.tournaments.services.completion_truth import (
            get_tournament_completion_payload,
        )
        t, u_a, *_ = self._make_live_with_winner(organizer, game, 'conv-payload')

        payload = get_tournament_completion_payload(t)

        assert payload['completed'] is True
        assert payload['has_winner'] is True
        assert payload['winner']['team_name'] == u_a.username

    def test_ensure_post_finalization_persists_status_completed(
        self, organizer, game,
    ):
        from apps.tournaments.services.completion_truth import (
            ensure_post_finalization,
        )
        t, *_ = self._make_live_with_winner(organizer, game, 'conv-persist')
        assert t.status == Tournament.LIVE

        payload = ensure_post_finalization(t)

        t.refresh_from_db()
        assert payload['completed'] is True
        assert payload['converged'] is True
        assert t.status == Tournament.COMPLETED

    def test_ensure_post_finalization_idempotent_double_run(
        self, organizer, game,
    ):
        from apps.tournaments.services.completion_truth import (
            ensure_post_finalization,
        )
        t, *_ = self._make_live_with_winner(organizer, game, 'conv-idem')

        ensure_post_finalization(t)
        t.refresh_from_db()
        ann_count_first = TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).count()

        # Second call after status already converged — must not duplicate.
        ensure_post_finalization(t)
        ann_count_second = TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).count()

        assert ann_count_first == 1
        assert ann_count_second == 1

    def test_toc_overview_returns_completed_status_when_winner_exists(
        self, organizer, game,
    ):
        from apps.tournaments.api.toc.service import TOCService

        t, *_ = self._make_live_with_winner(organizer, game, 'conv-toc-status')

        overview = TOCService.get_overview(t)

        assert overview['status'] == Tournament.COMPLETED
        assert 'completion' in overview
        assert overview['completion']['completed'] is True

    def test_toc_lifecycle_stepper_marks_completed_done_when_winner_exists(
        self, organizer, game,
    ):
        from apps.tournaments.api.toc.service import TOCService

        t, *_ = self._make_live_with_winner(
            organizer, game, 'conv-toc-stepper',
        )

        overview = TOCService.get_overview(t)
        stepper = overview['lifecycle_stepper']

        # Final step is 'completed' and renders as 'done' (terminal lit state)
        last_step = stepper['steps'][-1]
        assert last_step['key'] == 'completed'
        assert last_step['status'] == 'done'

        # No prior step shows 'pending' once the tournament is over.
        for step in stepper['steps'][:-1]:
            assert step['status'] in ('done', 'active'), (
                f"step {step['key']} unexpectedly pending after completion"
            )

        # Next-action label must NOT mention live knockout.
        next_action = stepper.get('next_action') or {}
        assert 'knockout stage is live' not in next_action.get('label', '').lower()
        assert next_action.get('tab') == 'overview'

    def test_toc_quick_actions_do_not_offer_live_only_buttons(
        self, organizer, game,
    ):
        from apps.tournaments.api.toc.service import TOCService

        t, *_ = self._make_live_with_winner(
            organizer, game, 'conv-toc-actions',
        )

        overview = TOCService.get_overview(t)
        action_ids = {a.get('id') for a in overview.get('quick_actions') or []}

        # No "broadcast_update" / "open_checkin" / "start_tournament" once over.
        assert 'broadcast_update' not in action_ids
        assert 'open_checkin' not in action_ids
        assert 'start_tournament' not in action_ids

    def test_hub_lifecycle_pipeline_marks_rewards_active_when_winner_exists(
        self, organizer, game,
    ):
        from apps.tournaments.views.hub import _build_hub_lifecycle_pipeline

        t, *_ = self._make_live_with_winner(organizer, game, 'conv-hub-rewards')

        # Convergence runs separately; the pipeline should still resolve to
        # 'rewards' even without a converged status (defensive override).
        pipeline = _build_hub_lifecycle_pipeline(
            t,
            command_center={'show': True},
            completion_payload={'completed': True},
        )

        assert pipeline['active_key'] == 'rewards'
        assert pipeline['completed'] is True
        assert pipeline['progress_percent'] == 100

    def test_hub_command_center_never_shows_awaiting_opponent_when_completed(
        self, organizer, game,
    ):
        from apps.tournaments.views.hub import _resolve_hub_command_center

        t, u_a, u_b, w, l = self._make_live_with_winner(
            organizer, game, 'conv-hub-target-intel',
        )
        # Don't run convergence first — verify the command center detects
        # completion on its own via the truth helper.

        payload_winner = _resolve_hub_command_center(
            t, registration=w, user=u_a,
        )
        payload_runner = _resolve_hub_command_center(
            t, registration=l, user=u_b,
        )

        for payload in (payload_winner, payload_runner):
            assert payload['show'] is True
            assert payload['lobby_state'] == 'completed'
            assert payload['cta_label'] == 'View Final Standings'
            blob = (
                str(payload.get('title', '')) + ' ' +
                str(payload.get('subtitle', '')) + ' ' +
                str(payload.get('hint', ''))
            ).lower()
            assert 'awaiting opponent' not in blob
            assert 'awaiting opponent assignment' not in blob


# ── FinalizeView idempotent UX ─────────────────────────────────────────────


@pytest.mark.django_db
class TestFinalizeViewIdempotentUX:
    """
    The frontend must read FinalizeView's idempotent response as success,
    not an error. We verify the response shape and re-running the pipeline
    does not duplicate announcements.
    """

    def test_finalize_already_completed_returns_success_with_idempotent_flag(
        self, organizer, game, player_one, player_two,
    ):
        from rest_framework.test import APIClient
        from django.urls import reverse

        t = _make_tournament(
            organizer, game, slug='conv-finalize-1',
            status=Tournament.COMPLETED,
        )
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        client = APIClient()
        client.force_authenticate(user=organizer)
        url = reverse('toc_api:lifecycle-finalize', kwargs={'slug': t.slug})
        resp = client.post(url, {}, format='json')

        assert resp.status_code == 200
        assert resp.data['finalized'] is True
        assert resp.data.get('idempotent') is True
        assert resp.data.get('already_completed') is True
        # Message is human-friendly, not an error string.
        assert 'already finalized' not in resp.data['message'].lower()

    def test_finalize_idempotent_path_does_not_duplicate_announcements(
        self, organizer, game, player_one, player_two,
    ):
        from rest_framework.test import APIClient
        from django.urls import reverse

        t = _make_tournament(
            organizer, game, slug='conv-finalize-2',
            status=Tournament.COMPLETED,
        )
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        client = APIClient()
        client.force_authenticate(user=organizer)
        url = reverse('toc_api:lifecycle-finalize', kwargs={'slug': t.slug})

        client.post(url, {}, format='json')
        client.post(url, {}, format='json')
        client.post(url, {}, format='json')

        ann_count = TournamentAnnouncement.objects.filter(
            tournament=t, is_pinned=True,
        ).count()
        assert ann_count == 1


# ── Prize winner binding fallback ──────────────────────────────────────────


@pytest.mark.django_db
class TestPrizePayloadFallback:
    """
    When a TournamentResult exists with winner FK fields populated but
    ``final_standings`` is empty (legacy tournament, partial pipeline run),
    the prize payload must still bind winner names to placement rows 1..4
    via direct fallback to TournamentResult.{winner,runner_up,third_place,
    fourth_place}.
    """

    def test_prize_payload_binds_winners_when_final_standings_empty(
        self, organizer, game, player_one, player_two,
    ):
        from apps.tournaments.services.rewards_read_model import (
            TournamentRewardsReadModel,
        )

        t = _make_tournament(organizer, game, slug='prize-fallback-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        result = _make_result_with_winner(t, w, l)

        # Force final_standings to be empty so we exercise the fallback.
        result.final_standings = []
        result.save(update_fields=['final_standings'])
        # Sanity: re-read confirms empty.
        result.refresh_from_db()
        assert result.final_standings == []

        payload = TournamentRewardsReadModel.public_payload(t)

        # The rank-1 placement entry must expose a winner with the team_name.
        rank1 = next((p for p in payload['placements'] if p['rank'] == 1), None)
        assert rank1 is not None
        assert rank1['winner'] is not None, (
            'rank 1 winner should bind from TournamentResult.winner '
            'even when final_standings is empty'
        )
        assert rank1['winner']['team_name'] == player_one.username

        rank2 = next((p for p in payload['placements'] if p['rank'] == 2), None)
        if rank2 is not None:
            assert rank2['winner'] is not None
            assert rank2['winner']['team_name'] == player_two.username

    def test_prize_payload_fallback_is_read_only_when_standings_empty(
        self, organizer, game, player_one, player_two,
    ):
        """The fallback path binds winners without mutating final_standings."""
        from apps.tournaments.services.rewards_read_model import (
            TournamentRewardsReadModel,
        )

        t = _make_tournament(organizer, game, slug='prize-fallback-2')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        result = _make_result_with_winner(t, w, l)
        result.final_standings = []
        result.save(update_fields=['final_standings'])

        TournamentRewardsReadModel.public_payload(t)

        result.refresh_from_db()
        assert result.final_standings == []

    def test_prize_payload_no_awaiting_winner_when_result_exists(
        self, organizer, game, player_one, player_two,
    ):
        """
        Smoke test: regardless of how empty the model is, if result.winner
        exists we must bind the winner — never expose 'awaiting' state for
        rank 1.
        """
        from apps.tournaments.services.rewards_read_model import (
            TournamentRewardsReadModel,
        )

        t = _make_tournament(organizer, game, slug='prize-fallback-3')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        result = _make_result_with_winner(t, w, l)
        result.final_standings = []
        result.save(update_fields=['final_standings'])

        payload = TournamentRewardsReadModel.public_payload(t)
        rank1 = next((p for p in payload['placements'] if p['rank'] == 1), None)

        assert rank1 is not None
        # The frontend renders 'Awaiting winner' when payload.winner is None.
        # Our payload must never produce that for an existing result.
        assert rank1['winner'] is not None
        assert rank1['winner']['team_name']


# ── HUB template renders Final Result card (no Awaiting Opponent text) ────


@pytest.mark.django_db
class TestHubOverviewTemplate:
    """
    The HUB overview template must:
      * Hide the legacy Target Intel card when ``is_post_completion`` is True.
      * Render a Final Result card with Champion / Runner-Up / Third names.
      * Never include the "Awaiting Opponent Assignment" string in completed
        renders (regardless of JS state).
    """

    def _render_overview_tab(self, tournament, registration, user):
        from django.template.loader import get_template
        from django.test import RequestFactory
        from apps.tournaments.views.hub import _build_hub_context

        request = RequestFactory().get(f'/tournaments/{tournament.slug}/hub/')
        request.user = user
        ctx = _build_hub_context(request, tournament, registration)
        ctx['request'] = request
        return get_template(
            'tournaments/hub/_tab_overview.html'
        ).render(ctx)

    def test_completed_overview_hides_target_intel_and_shows_final_result(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='hub-tpl-1')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)
        # Convergence runs inside _build_hub_context.

        html = self._render_overview_tab(t, registration=w, user=player_one)

        # No legacy Target Intel ID in the rendered DOM
        assert 'id="hub-overview-intel-card"' not in html
        # Final Result card is rendered
        assert 'hub-overview-final-result-card' in html
        # Champion name appears in the card
        assert player_one.username in html
        # No "Awaiting Opponent Assignment" anywhere
        assert 'Awaiting Opponent Assignment' not in html
        assert 'Awaiting Opponent' not in html

    def test_completed_overview_shows_view_final_standings_and_view_prizes(
        self, organizer, game, player_one, player_two,
    ):
        t = _make_tournament(organizer, game, slug='hub-tpl-2')
        w = _make_registration(t, player_one)
        l = _make_registration(t, player_two)
        _make_completed_match(t, winner_reg=w, loser_reg=l)
        _make_result_with_winner(t, w, l)

        html = self._render_overview_tab(t, registration=w, user=player_one)

        assert 'View Final Standings' in html
        assert 'View Prizes' in html

    def test_pre_completion_overview_still_renders_target_intel(
        self, organizer, game, player_one, player_two,
    ):
        """Sanity: live tournaments still show the legacy widget."""
        t = _make_tournament(organizer, game, slug='hub-tpl-3')
        # No TournamentResult, no completed match → still LIVE.
        w = _make_registration(t, player_one)
        Registration.objects.create(
            tournament=t,
            user=player_two,
            status=Registration.CONFIRMED,
            registration_data={},
        )

        html = self._render_overview_tab(t, registration=w, user=player_one)

        assert 'id="hub-overview-intel-card"' in html
        assert 'hub-overview-final-result-card' not in html
