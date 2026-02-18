"""
Phase 6 — Task 6.2: Service Integration Tests

Integration tests for the Phase 5 services:
- TournamentLifecycleService: transition graph, guards, auto-advance
- CompletionPipeline: post-completion steps
- ArchiveService: snapshot generation

Uses real DB (requires @pytest.mark.django_db).
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def game(db):
    return Game.objects.create(
        name='Valorant Test', slug='valorant-test',
        display_name='VALORANT™', short_code='VALT',
        category='FPS', game_type='TEAM_VS_TEAM',
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='org_lifecycle', email='org@lifecycle.test', password='pass123',
    )


@pytest.fixture
def draft_tournament(db, game, organizer):
    """A DRAFT tournament with future dates."""
    now = timezone.now()
    return Tournament.objects.create(
        name='Lifecycle Test',
        slug=f'lifecycle-test-{int(now.timestamp() * 1e6)}',
        description='A test tournament for lifecycle transitions.',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='team',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('1000'),
        registration_start=now + timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=10),
        registration_form_overrides={'enabled': True},
        status=Tournament.DRAFT,
    )


@pytest.fixture
def past_dates_tournament(db, game, organizer):
    """A DRAFT tournament with all dates in the past (for auto-advance)."""
    past = timezone.now() - timedelta(days=30)
    return Tournament.objects.create(
        name='Past Dates Test',
        slug=f'past-dates-{int(timezone.now().timestamp() * 1e6)}',
        description='Tournament with past dates for auto-advance testing.',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='solo',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('500'),
        registration_start=past,
        registration_end=past + timedelta(days=5),
        tournament_start=past + timedelta(days=7),
        registration_form_overrides={'enabled': True},
        status=Tournament.DRAFT,
    )


# ---------------------------------------------------------------------------
# TournamentLifecycleService Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLifecycleTransitions:
    """Test the formal state machine transitions."""

    def test_draft_to_published(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        t = TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        assert t.status == Tournament.PUBLISHED
        assert t.published_at is not None

    def test_draft_to_cancelled(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        t = TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.CANCELLED,
            actor=organizer, reason='Not enough interest',
        )
        assert t.status == Tournament.CANCELLED

    def test_invalid_transition_raises(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        with pytest.raises(ValidationError, match="Invalid transition"):
            TournamentLifecycleService.transition(
                draft_tournament.id, Tournament.COMPLETED, actor=organizer,
            )

    def test_draft_to_live_not_allowed(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        with pytest.raises(ValidationError, match="Invalid transition"):
            TournamentLifecycleService.transition(
                draft_tournament.id, Tournament.LIVE, actor=organizer,
            )

    def test_cancelled_to_archived(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.CANCELLED, actor=organizer,
        )
        t = TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.ARCHIVED, actor=organizer,
        )
        assert t.status == Tournament.ARCHIVED

    def test_published_to_registration_open_guard_future_date(self, draft_tournament, organizer):
        """Guard blocks if registration_start is in the future."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        with pytest.raises(ValidationError, match="in the future"):
            TournamentLifecycleService.transition(
                draft_tournament.id, Tournament.REGISTRATION_OPEN, actor=organizer,
            )

    def test_force_skips_guard(self, draft_tournament, organizer):
        """force=True bypasses guard checks."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        t = TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.REGISTRATION_OPEN,
            actor=organizer, force=True,
        )
        assert t.status == Tournament.REGISTRATION_OPEN


@pytest.mark.django_db
class TestLifecycleHelpers:
    """Test helper methods: allowed_transitions, can_transition."""

    def test_allowed_transitions_for_draft(self, draft_tournament):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        allowed = TournamentLifecycleService.allowed_transitions(draft_tournament)
        assert Tournament.PUBLISHED in allowed
        assert Tournament.CANCELLED in allowed
        assert Tournament.REGISTRATION_OPEN in allowed
        assert Tournament.PENDING_APPROVAL in allowed
        assert Tournament.COMPLETED not in allowed

    def test_can_transition_returns_tuple(self, draft_tournament):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        ok, reason = TournamentLifecycleService.can_transition(
            draft_tournament, Tournament.PUBLISHED,
        )
        assert ok is True
        assert reason is None

    def test_can_transition_invalid(self, draft_tournament):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        ok, reason = TournamentLifecycleService.can_transition(
            draft_tournament, Tournament.ARCHIVED,
        )
        assert ok is False
        assert reason is not None


@pytest.mark.django_db
class TestLifecycleAutoAdvance:
    """Test date-driven auto-advance logic."""

    def test_auto_advance_published_to_reg_open(self, past_dates_tournament, organizer):
        """A PUBLISHED tournament with past registration_start should auto-advance."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        # First publish it
        TournamentLifecycleService.transition(
            past_dates_tournament.id, Tournament.PUBLISHED,
            actor=organizer, force=True,
        )
        past_dates_tournament.refresh_from_db()
        assert past_dates_tournament.status == Tournament.PUBLISHED

        # Auto-advance should move it to REGISTRATION_OPEN
        result = TournamentLifecycleService.auto_advance(past_dates_tournament)
        assert result == Tournament.REGISTRATION_OPEN

    def test_auto_advance_no_op_for_draft(self, draft_tournament):
        """Draft tournaments are not auto-advanced."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        result = TournamentLifecycleService.auto_advance(draft_tournament)
        assert result is None

    def test_auto_advance_all_batch(self, past_dates_tournament, organizer):
        """auto_advance_all processes multiple tournaments."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        # Set up a published tournament
        TournamentLifecycleService.transition(
            past_dates_tournament.id, Tournament.PUBLISHED,
            actor=organizer, force=True,
        )

        results = TournamentLifecycleService.auto_advance_all()
        assert Tournament.REGISTRATION_OPEN in results


@pytest.mark.django_db
class TestLifecycleAuditTrail:
    """Ensure transitions create version records."""

    def test_transition_creates_version(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.models.tournament import TournamentVersion

        before_count = TournamentVersion.objects.filter(tournament=draft_tournament).count()
        TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        after_count = TournamentVersion.objects.filter(tournament=draft_tournament).count()
        assert after_count == before_count + 1

    def test_version_records_from_to_status(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.models.tournament import TournamentVersion

        TournamentLifecycleService.transition(
            draft_tournament.id, Tournament.PUBLISHED, actor=organizer,
        )
        version = TournamentVersion.objects.filter(
            tournament=draft_tournament,
        ).order_by('-version_number').first()
        assert 'draft' in version.change_summary.lower()
        assert 'published' in version.change_summary.lower()


# ---------------------------------------------------------------------------
# CompletionPipeline Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCompletionPipeline:
    """Test the completion pipeline."""

    def test_requires_completed_status(self, draft_tournament):
        from apps.tournaments.services.completion_pipeline import CompletionPipeline

        with pytest.raises(ValidationError, match="COMPLETED"):
            CompletionPipeline.run(draft_tournament.id)

    def test_run_on_completed_tournament(self, draft_tournament, organizer):
        """Pipeline runs without fatal errors on a COMPLETED tournament."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.completion_pipeline import CompletionPipeline

        # Force the tournament through to COMPLETED
        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED]:
            TournamentLifecycleService.transition(
                draft_tournament.id, status, actor=organizer, force=True,
            )

        report = CompletionPipeline.run(
            draft_tournament.id, actor=organizer,
            skip_certificates=True, skip_notifications=True,
        )
        assert report.tournament_id == draft_tournament.id
        assert report.status in ('success', 'partial')

    def test_pipeline_metadata_persisted_in_config(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.completion_pipeline import CompletionPipeline

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED]:
            TournamentLifecycleService.transition(
                draft_tournament.id, status, actor=organizer, force=True,
            )

        CompletionPipeline.run(
            draft_tournament.id, skip_certificates=True, skip_notifications=True,
        )
        draft_tournament.refresh_from_db()
        config = draft_tournament.config or {}
        assert 'completion_pipeline' in config
        assert 'ran_at' in config['completion_pipeline']


# ---------------------------------------------------------------------------
# ArchiveService Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArchiveService:
    """Test archive snapshot generation."""

    def test_requires_completed_or_archived(self, draft_tournament):
        from apps.tournaments.services.archive_service import ArchiveService

        with pytest.raises(ValidationError, match="COMPLETED or ARCHIVED"):
            ArchiveService.generate(draft_tournament.id)

    def test_generate_archive(self, draft_tournament, organizer):
        """Archive generates a versioned snapshot with required keys."""
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.archive_service import ArchiveService

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED]:
            TournamentLifecycleService.transition(
                draft_tournament.id, status, actor=organizer, force=True,
            )

        archive = ArchiveService.generate(draft_tournament.id)
        assert archive['version'] == 1
        assert 'tournament' in archive
        assert 'participants' in archive
        assert 'matches' in archive
        assert 'brackets' in archive
        assert 'standings' in archive
        assert 'statistics' in archive
        assert archive['tournament']['name'] == 'Lifecycle Test'

    def test_get_archive_retrieves_persisted_data(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.archive_service import ArchiveService

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED]:
            TournamentLifecycleService.transition(
                draft_tournament.id, status, actor=organizer, force=True,
            )

        ArchiveService.generate(draft_tournament.id)
        retrieved = ArchiveService.get_archive(draft_tournament.id)
        assert retrieved is not None
        assert retrieved['tournament']['id'] == draft_tournament.id

    def test_archive_statistics_fields(self, draft_tournament, organizer):
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        from apps.tournaments.services.archive_service import ArchiveService

        for status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
                       Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED]:
            TournamentLifecycleService.transition(
                draft_tournament.id, status, actor=organizer, force=True,
            )

        archive = ArchiveService.generate(draft_tournament.id)
        stats = archive['statistics']
        assert 'total_participants' in stats
        assert 'total_matches' in stats
        assert 'completion_rate' in stats
