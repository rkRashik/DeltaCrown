import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings

from apps.tournaments.models import Match
from apps.tournaments.models.result_submission import MatchResultSubmission
from apps.tournaments.services.evidence_cleanup import purge_tournament_result_evidence_files


GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@pytest.mark.django_db
def test_purge_tournament_result_evidence_files_deletes_file_and_keeps_submission_row(
    tmp_path,
    game_factory,
    tournament_factory,
    participant_user,
):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        game = game_factory(slug="valorant-evidence-cleanup", name="Valorant", team_size=5, profile_id_field="riot_id")
        tournament = tournament_factory(game=game, participation_type="solo")

        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=participant_user.id,
            participant1_name="Player One",
            participant2_id=999999,
            participant2_name="Player Two",
        )

        proof_file = SimpleUploadedFile("proof.gif", GIF_BYTES, content_type="image/gif")
        submission = MatchResultSubmission.objects.create(
            match=match,
            submitted_by_user=participant_user,
            submitted_by_team_id=None,
            raw_result_payload={"score_for": 2, "score_against": 1},
            proof_screenshot=proof_file,
            submitter_notes="Evidence attached",
        )

        stored_name = str(submission.proof_screenshot.name)
        storage = submission.proof_screenshot.storage

        assert stored_name
        assert storage.exists(stored_name)

        stats = purge_tournament_result_evidence_files(tournament.id)

        submission.refresh_from_db()

        assert stats["tournament_id"] == tournament.id
        assert stats["scanned"] == 1
        assert stats["deleted"] == 1
        assert stats["failed"] == 0
        assert not submission.proof_screenshot
        assert MatchResultSubmission.objects.filter(pk=submission.pk).exists()
        assert not storage.exists(stored_name)
