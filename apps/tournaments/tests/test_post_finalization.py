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
