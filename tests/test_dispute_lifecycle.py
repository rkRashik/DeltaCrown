# tests/test_dispute_lifecycle.py
"""
Dispute lifecycle tests — status transitions, validation, evidence handling.

Tests the DisputeRecord state machine:
  open → under_review → resolved_for_submitter
  open → under_review → resolved_for_opponent
  open → under_review → resolved_custom
  open → under_review → dismissed
  open → under_review → escalated → resolved_*
"""
import pytest


class TestDisputeRecordModel:
    """Test DisputeRecord model structure and constants."""

    def test_model_importable(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord is not None

    def test_status_constants_defined(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord.OPEN == 'open'
        assert DisputeRecord.UNDER_REVIEW == 'under_review'
        assert DisputeRecord.ESCALATED == 'escalated'
        assert DisputeRecord.RESOLVED_FOR_SUBMITTER == 'resolved_for_submitter'
        assert DisputeRecord.RESOLVED_FOR_OPPONENT == 'resolved_for_opponent'
        assert DisputeRecord.RESOLVED_CUSTOM == 'resolved_custom'
        assert DisputeRecord.DISMISSED == 'dismissed'

    def test_cancelled_alias_equals_dismissed(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord.CANCELLED == DisputeRecord.DISMISSED

    def test_reason_code_constants_defined(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord.REASON_SCORE_MISMATCH == 'score_mismatch'
        assert DisputeRecord.REASON_WRONG_WINNER == 'wrong_winner'
        assert DisputeRecord.REASON_CHEATING_SUSPICION == 'cheating_suspicion'
        assert DisputeRecord.REASON_INCORRECT_MAP == 'incorrect_map'
        assert DisputeRecord.REASON_MATCH_NOT_PLAYED == 'match_not_played'
        assert DisputeRecord.REASON_OTHER == 'other'

    def test_status_choices_cover_all_constants(self):
        from apps.tournaments.models.dispute import DisputeRecord
        status_values = {choice[0] for choice in DisputeRecord.STATUS_CHOICES}
        expected = {
            'open', 'under_review', 'escalated',
            'resolved_for_submitter', 'resolved_for_opponent',
            'resolved_custom', 'dismissed',
        }
        assert status_values == expected

    def test_reason_choices_cover_all_constants(self):
        from apps.tournaments.models.dispute import DisputeRecord
        reason_values = {choice[0] for choice in DisputeRecord.REASON_CHOICES}
        expected = {
            'score_mismatch', 'wrong_winner', 'cheating_suspicion',
            'incorrect_map', 'match_not_played', 'other',
        }
        assert reason_values == expected

    def test_default_status_is_open(self):
        from apps.tournaments.models.dispute import DisputeRecord
        field = DisputeRecord._meta.get_field('status')
        assert field.default == DisputeRecord.OPEN


class TestDisputeStateMachine:
    """Test is_open() and is_resolved() logic without DB."""

    def _make_dispute(self, status):
        """Create a mock DisputeRecord-like object with status."""
        from apps.tournaments.models.dispute import DisputeRecord
        obj = DisputeRecord.__new__(DisputeRecord)
        obj.status = status
        return obj

    # -- is_open tests --

    def test_open_status_is_open(self):
        d = self._make_dispute('open')
        assert d.is_open()

    def test_under_review_is_open(self):
        d = self._make_dispute('under_review')
        assert d.is_open()

    def test_escalated_is_open(self):
        d = self._make_dispute('escalated')
        assert d.is_open()

    def test_resolved_for_submitter_is_not_open(self):
        d = self._make_dispute('resolved_for_submitter')
        assert not d.is_open()

    def test_resolved_for_opponent_is_not_open(self):
        d = self._make_dispute('resolved_for_opponent')
        assert not d.is_open()

    def test_dismissed_is_not_open(self):
        d = self._make_dispute('dismissed')
        assert not d.is_open()

    # -- is_resolved tests --

    def test_resolved_for_submitter_is_resolved(self):
        d = self._make_dispute('resolved_for_submitter')
        assert d.is_resolved()

    def test_resolved_for_opponent_is_resolved(self):
        d = self._make_dispute('resolved_for_opponent')
        assert d.is_resolved()

    def test_resolved_custom_is_resolved(self):
        d = self._make_dispute('resolved_custom')
        assert d.is_resolved()

    def test_dismissed_is_resolved(self):
        d = self._make_dispute('dismissed')
        assert d.is_resolved()

    def test_open_is_not_resolved(self):
        d = self._make_dispute('open')
        assert not d.is_resolved()

    def test_under_review_is_not_resolved(self):
        d = self._make_dispute('under_review')
        assert not d.is_resolved()

    def test_escalated_is_not_resolved(self):
        d = self._make_dispute('escalated')
        assert not d.is_resolved()


class TestDisputeEvidenceModel:
    """Test DisputeEvidence model structure."""

    def test_evidence_model_importable(self):
        from apps.tournaments.models.dispute import DisputeEvidence
        assert DisputeEvidence is not None

    def test_evidence_has_required_fields(self):
        from apps.tournaments.models.dispute import DisputeEvidence
        field_names = {f.name for f in DisputeEvidence._meta.get_fields()}
        expected_fields = {'dispute', 'uploaded_by', 'url', 'notes', 'created_at'}
        assert expected_fields.issubset(field_names)

    def test_evidence_upload_path_uses_uuid(self):
        from apps.tournaments.models.dispute import _dispute_evidence_upload_to
        path = _dispute_evidence_upload_to(None, "screenshot.png")
        assert path.startswith("disputes/evidence/")
        assert path.endswith(".png")
        filename = path.split("/")[-1]
        name_part = filename.rsplit(".", 1)[0]
        assert len(name_part) == 32  # UUID hex length

    def test_evidence_upload_path_handles_no_extension(self):
        from apps.tournaments.models.dispute import _dispute_evidence_upload_to
        path = _dispute_evidence_upload_to(None, "noextension")
        assert path.endswith(".bin")


class TestDisputeDBConstraints:
    """Test DB-level constraints defined on DisputeRecord."""

    def test_status_check_constraint_exists(self):
        from apps.tournaments.models.dispute import DisputeRecord
        constraint_names = [c.name for c in DisputeRecord._meta.constraints]
        assert 'chk_dispute_record_status_valid' in constraint_names

    def test_model_indexes_defined(self):
        from apps.tournaments.models.dispute import DisputeRecord
        index_names = [idx.name for idx in DisputeRecord._meta.indexes]
        assert 'idx_dispute_submission_status' in index_names
        assert 'idx_dispute_opened_at' in index_names
        assert 'idx_dispute_status' in index_names

    def test_db_table_name(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord._meta.db_table == 'tournaments_dispute_record'
