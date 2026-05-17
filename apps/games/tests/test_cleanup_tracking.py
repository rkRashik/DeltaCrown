"""Tests for MediaCleanupCandidate tracking and MediaCleanupService."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from django.test import TestCase
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game_field(name: str = ""):
    """Mock an ImageField-like object."""
    field = MagicMock()
    field.name = name
    field.__bool__ = lambda self: bool(name)
    return field


def _approved_name(sub="icons/test_icon_abc"):
    return f"media/games/{sub}"


def _blocked_name():
    return "media/match_media/screenshot.jpg"


# ---------------------------------------------------------------------------
# Model: MediaCleanupCandidate
# ---------------------------------------------------------------------------

class MediaCleanupCandidateModelTests(TestCase):

    def _make(self, file_name="media/games/icons/old.png", hours_offset=48, status="pending"):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        return MediaCleanupCandidate.objects.create(
            file_name=file_name,
            storage_type="cloudinary",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
            reason="replaced",
            status=status,
            eligible_after=timezone.now() + timedelta(hours=hours_offset),
        )

    def test_create_for_field_creates_row(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        c = MediaCleanupCandidate.create_for_field(
            file_name="media/games/icons/old_abc",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
        )
        self.assertIsNotNone(c)
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_PENDING)

    def test_create_for_field_deduplicates_pending(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        MediaCleanupCandidate.create_for_field(
            file_name="media/games/icons/same_abc",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
        )
        second = MediaCleanupCandidate.create_for_field(
            file_name="media/games/icons/same_abc",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
        )
        self.assertIsNone(second)
        self.assertEqual(
            MediaCleanupCandidate.objects.filter(
                file_name="media/games/icons/same_abc"
            ).count(), 1
        )

    def test_is_eligible_true_when_past_retention(self):
        c = self._make(hours_offset=-1)  # eligible_after in the past
        self.assertTrue(c.is_eligible)

    def test_is_eligible_false_when_in_retention(self):
        c = self._make(hours_offset=10)  # eligible_after in the future
        self.assertFalse(c.is_eligible)

    def test_is_eligible_false_when_already_deleted(self):
        c = self._make(hours_offset=-1, status="deleted")
        self.assertFalse(c.is_eligible)


# ---------------------------------------------------------------------------
# Signal helpers: _is_approved and _is_still_referenced
# ---------------------------------------------------------------------------

class SignalHelperTests(TestCase):

    def test_approved_game_icon_folder(self):
        from apps.games.signals_media import _is_approved
        self.assertTrue(_is_approved("media/games/icons/val_abc"))
        self.assertTrue(_is_approved("media/games/logos/val_logo"))
        self.assertTrue(_is_approved("media/games/banners/val_b"))
        self.assertTrue(_is_approved("media/games/cards/val_c"))
        self.assertTrue(_is_approved("media/games/maps/map1"))

    def test_blocked_paths_not_approved(self):
        from apps.games.signals_media import _is_approved
        self.assertFalse(_is_approved("media/match_media/screenshot.jpg"))
        self.assertFalse(_is_approved("media/payment_proofs/receipt.jpg"))
        self.assertFalse(_is_approved("media/kyc/doc.jpg"))
        self.assertFalse(_is_approved("media/certificates/cert.jpg"))

    def test_empty_name_not_approved(self):
        from apps.games.signals_media import _is_approved
        self.assertFalse(_is_approved(""))
        self.assertFalse(_is_approved(None))

    def test_non_game_folder_not_approved(self):
        from apps.games.signals_media import _is_approved
        self.assertFalse(_is_approved("media/roster_photos/photo.jpg"))


# ---------------------------------------------------------------------------
# Signal integration: candidate created on field change
# ---------------------------------------------------------------------------

class SignalCandidateCreationTests(TestCase):

    def _run_signal_flow(self, old_name: str, new_name: str, game_pk: int = 99):
        """Simulate what the pre/post_save signals do for a Game row."""
        from apps.games.signals_media import _create_candidate

        with patch(
            "apps.games.signals_media._is_still_referenced",
            return_value=False,
        ), patch(
            "apps.games.signals_media._storage_type",
            return_value="cloudinary",
        ):
            _create_candidate(
                file_name=old_name,
                source_model="games.Game",
                source_pk=game_pk,
                field_name="icon",
                reason="replaced",
                metadata={"game_name": "Valorant", "old_file": old_name, "new_file": new_name},
            )

    def test_approved_old_file_creates_candidate(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        self._run_signal_flow(
            old_name="media/games/icons/old_val_abc",
            new_name="media/games/icons/new_val_xyz",
        )
        self.assertTrue(
            MediaCleanupCandidate.objects.filter(
                file_name="media/games/icons/old_val_abc"
            ).exists()
        )

    def test_blocked_old_file_does_not_create_candidate(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        self._run_signal_flow(
            old_name="media/match_media/screenshot.jpg",
            new_name="media/games/icons/new_val.jpg",
        )
        self.assertFalse(
            MediaCleanupCandidate.objects.filter(
                file_name="media/match_media/screenshot.jpg"
            ).exists()
        )

    def test_still_referenced_does_not_create_candidate(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.signals_media import _create_candidate

        with patch(
            "apps.games.signals_media._is_still_referenced",
            return_value=True,  # still referenced
        ):
            _create_candidate(
                file_name="media/games/icons/shared_icon",
                source_model="games.Game",
                source_pk=1,
                field_name="icon",
                reason="replaced",
                metadata={},
            )
        self.assertFalse(
            MediaCleanupCandidate.objects.filter(
                file_name="media/games/icons/shared_icon"
            ).exists()
        )


# ---------------------------------------------------------------------------
# MediaCleanupService
# ---------------------------------------------------------------------------

class MediaCleanupServiceTests(TestCase):

    def _make_eligible(self, file_name="media/games/icons/orphan_abc"):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        return MediaCleanupCandidate.objects.create(
            file_name=file_name,
            storage_type="cloudinary",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
            reason="replaced",
            status=MediaCleanupCandidate.STATUS_PENDING,
            eligible_after=timezone.now() - timedelta(hours=1),
        )

    def _make_not_eligible(self, file_name="media/games/icons/fresh_abc"):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        return MediaCleanupCandidate.objects.create(
            file_name=file_name,
            storage_type="cloudinary",
            source_model="games.Game",
            source_object_id=2,
            source_field="icon",
            reason="replaced",
            status=MediaCleanupCandidate.STATUS_PENDING,
            eligible_after=timezone.now() + timedelta(hours=24),
        )

    def test_dry_run_does_not_delete(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        c = self._make_eligible()
        with patch(
            "apps.games.services.media_cleanup_service._is_still_referenced",
            return_value=False,
        ), patch(
            "apps.games.services.media_cleanup_service._cloudinary_available",
            return_value=True,
        ), patch(
            "apps.games.services.media_cleanup_service._destroy",
        ) as mock_destroy:
            result = MediaCleanupService().process_eligible(dry_run=True)

        mock_destroy.assert_not_called()
        self.assertEqual(result["deleted"], 1)  # dry_run counts as "would delete"
        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_PENDING)

    def test_still_referenced_is_skipped(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        c = self._make_eligible()
        with patch(
            "apps.games.services.media_cleanup_service._is_still_referenced",
            return_value=True,
        ):
            MediaCleanupService().process_eligible(dry_run=False)

        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_SKIPPED)
        self.assertIn("referenced", c.error_message)

    def test_not_eligible_candidate_skipped(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        c = self._make_not_eligible()
        with patch(
            "apps.games.services.media_cleanup_service._is_still_referenced",
            return_value=False,
        ), patch(
            "apps.games.services.media_cleanup_service._cloudinary_available",
            return_value=True,
        ), patch(
            "apps.games.services.media_cleanup_service._destroy",
            return_value=True,
        ) as mock_destroy:
            MediaCleanupService().process_eligible(dry_run=False)

        mock_destroy.assert_not_called()
        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_PENDING)

    def test_eligible_not_referenced_deletes_successfully(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        c = self._make_eligible()
        with patch(
            "apps.games.services.media_cleanup_service._is_still_referenced",
            return_value=False,
        ), patch(
            "apps.games.services.media_cleanup_service._cloudinary_available",
            return_value=True,
        ), patch(
            "apps.games.services.media_cleanup_service._destroy",
            return_value=True,
        ) as mock_destroy:
            result = MediaCleanupService().process_eligible(dry_run=False)

        mock_destroy.assert_called_once_with(c.file_name)
        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_DELETED)
        self.assertIsNotNone(c.deleted_at)
        self.assertEqual(result["deleted"], 1)

    def test_cloudinary_destroy_failure_marks_failed(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        c = self._make_eligible()
        with patch(
            "apps.games.services.media_cleanup_service._is_still_referenced",
            return_value=False,
        ), patch(
            "apps.games.services.media_cleanup_service._cloudinary_available",
            return_value=True,
        ), patch(
            "apps.games.services.media_cleanup_service._destroy",
            return_value=False,
        ):
            MediaCleanupService().process_eligible(dry_run=False)

        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_FAILED)

    def test_blocked_path_is_skipped_at_deletion_time(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from apps.games.services.media_cleanup_service import MediaCleanupService

        # Simulate a wrongly-created candidate with a blocked path.
        c = MediaCleanupCandidate.objects.create(
            file_name="media/match_media/screenshot.jpg",
            storage_type="cloudinary",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
            reason="replaced",
            status=MediaCleanupCandidate.STATUS_PENDING,
            eligible_after=timezone.now() - timedelta(hours=1),
        )
        with patch(
            "apps.games.services.media_cleanup_service._destroy"
        ) as mock_destroy:
            MediaCleanupService().process_eligible(dry_run=False)

        mock_destroy.assert_not_called()
        c.refresh_from_db()
        self.assertEqual(c.status, MediaCleanupCandidate.STATUS_SKIPPED)
