import pytest
from django.contrib.auth import get_user_model
from apps.tournaments.models import Match, Tournament
from apps.corelib.brackets import report_result

User = get_user_model()

@pytest.mark.django_db
def test_report_match_result():
    ua = User.objects.create_user("user_a", password="pw")
    ub = User.objects.create_user("user_b", password="pw")
    pa, pb = ua.profile, ub.profile

    t = Tournament.objects.create(
        name="Test Tournament",
        reg_open_at="2025-01-01T00:00:00Z",
        reg_close_at="2025-01-02T00:00:00Z",
        start_at="2025-01-03T00:00:00Z",
        end_at="2025-01-04T00:00:00Z",
        slot_size=2,
    )
    m = Match.objects.create(tournament=t, round_no=1, position=1, user_a=pa, user_b=pb, best_of=1)

    report_result(m, score_a=3, score_b=1, reporter=pa)
    m.refresh_from_db()

    assert m.score_a == 3
    assert m.score_b == 1
    assert m.state in {"REPORTED", "VERIFIED"}
    assert (m.winner_user_id == pa.id) or (m.winner_team_id is not None)
