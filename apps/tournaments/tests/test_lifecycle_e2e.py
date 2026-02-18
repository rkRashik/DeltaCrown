"""
Phase 6 — Task 6.5: Lifecycle End-to-End Integration Test

Full happy-path test that walks a tournament through the entire lifecycle:
    DRAFT → PUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED
          → LIVE → COMPLETED  (+ completion pipeline)  → ARCHIVED  (+ archive snapshot)

This is the single most important test in the tournament system — it proves
the state machine, pipeline, and archive all work together.
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.games.models.game import Game

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def game(db):
    return Game.objects.create(
        name='E2E Lifecycle Game', slug='e2e-lifecycle',
        display_name='E2E Lifecycle Game', short_code='E2E',
        category='FPS', game_type='TEAM_VS_TEAM',
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='e2e_organizer', email='e2e_org@test.test', password='pass123',
    )


@pytest.fixture
def tournament(db, game, organizer):
    """A DRAFT tournament with all dates in the past for smooth auto-advance."""
    past = timezone.now() - timedelta(days=60)
    return Tournament.objects.create(
        name='E2E Full Lifecycle',
        slug=f'e2e-lifecycle-{int(timezone.now().timestamp() * 1e6)}',
        description='End-to-end lifecycle test tournament.',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='team',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('2000'),
        registration_start=past,
        registration_end=past + timedelta(days=7),
        tournament_start=past + timedelta(days=10),
        registration_form_overrides={'enabled': True},
        status=Tournament.DRAFT,
    )


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullLifecycleE2E:
    """Walk a tournament through every status on the happy path."""

    def test_happy_path_full_lifecycle(self, tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        # 1. DRAFT → PUBLISHED
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        assert t.status == Tournament.PUBLISHED
        assert t.published_at is not None

        # 2. PUBLISHED → REGISTRATION_OPEN  (force, dates are in the past)
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.REGISTRATION_OPEN,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.REGISTRATION_OPEN

        # 3. REGISTRATION_OPEN → REGISTRATION_CLOSED (force)
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.REGISTRATION_CLOSED,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.REGISTRATION_CLOSED

        # 4. REGISTRATION_CLOSED → LIVE (force)
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.LIVE,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.LIVE

        # 5. LIVE → COMPLETED (force)
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.COMPLETED,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.COMPLETED

        # 6. Run the completion pipeline on the COMPLETED tournament
        from apps.tournaments.services.completion_pipeline import CompletionPipeline
        report = CompletionPipeline.run(
            tournament.id, actor=organizer,
            skip_certificates=True, skip_notifications=True,
        )
        assert report.tournament_id == tournament.id
        assert report.status in ('success', 'partial')

        # Pipeline metadata should be persisted
        tournament.refresh_from_db()
        assert 'completion_pipeline' in (tournament.config or {})

        # 7. Generate archive snapshot
        from apps.tournaments.services.archive_service import ArchiveService
        archive = ArchiveService.generate(tournament.id)
        assert archive['version'] == 1
        assert archive['tournament']['name'] == 'E2E Full Lifecycle'
        assert 'participants' in archive
        assert 'matches' in archive
        assert 'statistics' in archive

        # Archive should be persisted in config
        tournament.refresh_from_db()
        assert 'archive' in (tournament.config or {})

        # 8. COMPLETED → ARCHIVED
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.ARCHIVED,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.ARCHIVED

        # Verify the audit trail has all transitions
        from apps.tournaments.models.tournament import TournamentVersion
        versions = TournamentVersion.objects.filter(
            tournament_id=tournament.id,
        ).order_by('version_number')
        assert versions.count() >= 6  # At least 6 status transitions

    def test_cancel_from_any_active_status(self, tournament, organizer):
        """Cancellation should work from multiple active statuses."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        # Publish first
        TournamentLifecycleService.transition(
            tournament.id, Tournament.PUBLISHED, actor=organizer,
        )

        # Cancel from PUBLISHED
        t = TournamentLifecycleService.transition(
            tournament.id, Tournament.CANCELLED,
            actor=organizer, reason='Changed plans',
        )
        assert t.status == Tournament.CANCELLED

    def test_cannot_transition_backwards(self, tournament, organizer):
        """Once moved forward, cannot go back to a previous status."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        TournamentLifecycleService.transition(
            tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        TournamentLifecycleService.transition(
            tournament.id, Tournament.REGISTRATION_OPEN,
            actor=organizer, force=True,
        )

        # Trying to go back to PUBLISHED should fail
        with pytest.raises(ValidationError, match="Invalid transition"):
            TournamentLifecycleService.transition(
                tournament.id, Tournament.PUBLISHED, actor=organizer,
            )

    def test_auto_advance_walks_happy_path(self, tournament, organizer):
        """auto_advance should move through date-driven transitions.

        Since we have no real registrations, only PUBLISHED→REG_OPEN will
        auto-advance.  We verify subsequent date-driven transitions with
        force=True to exercise the wiring without needing participant fixtures.
        """
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        # Publish (dates are all in the past)
        TournamentLifecycleService.transition(
            tournament.id, Tournament.PUBLISHED, actor=organizer,
        )

        # First auto_advance: PUBLISHED → REG_OPEN (no participant guard)
        tournament.refresh_from_db()
        result1 = TournamentLifecycleService.auto_advance(tournament)
        assert result1 == Tournament.REGISTRATION_OPEN

        # REG_OPEN → REG_CLOSED requires min participants — force it
        tournament.refresh_from_db()
        TournamentLifecycleService.transition(
            tournament.id, Tournament.REGISTRATION_CLOSED,
            actor=organizer, force=True,
        )
        tournament.refresh_from_db()
        assert tournament.status == Tournament.REGISTRATION_CLOSED

        # REG_CLOSED → LIVE requires min participants — force it
        TournamentLifecycleService.transition(
            tournament.id, Tournament.LIVE,
            actor=organizer, force=True,
        )
        tournament.refresh_from_db()
        assert tournament.status == Tournament.LIVE

        # No more auto-advances from LIVE (needs match completion)
        result4 = TournamentLifecycleService.auto_advance(tournament)
        assert result4 is None

    def test_completion_pipeline_rejects_non_completed(self, tournament, organizer):
        """Pipeline should not run on a LIVE tournament."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.completion_pipeline import CompletionPipeline

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE]:
            TournamentLifecycleService.transition(
                tournament.id, status, actor=organizer, force=True,
            )

        with pytest.raises(ValidationError, match="COMPLETED"):
            CompletionPipeline.run(tournament.id)

    def test_archive_rejects_live_tournament(self, tournament, organizer):
        """Archive should not work on a LIVE tournament."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.archive_service import ArchiveService

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE]:
            TournamentLifecycleService.transition(
                tournament.id, status, actor=organizer, force=True,
            )

        with pytest.raises(ValidationError, match="COMPLETED or ARCHIVED"):
            ArchiveService.generate(tournament.id)
