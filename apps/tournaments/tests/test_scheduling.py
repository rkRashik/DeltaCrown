# apps/tournaments/tests/test_scheduling.py
import pytest
from datetime import timedelta
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _create_tournament(**overrides):
    """Create a Tournament compatible with your fields."""
    from apps.tournaments.models import Tournament

    now = timezone.now()
    ts = str(now.timestamp()).replace(".", "")

    reg_open = overrides.get("reg_open_at", now)
    reg_close = overrides.get("reg_close_at", reg_open + timedelta(hours=1))
    start = overrides.get("start_at", reg_close + timedelta(hours=1))
    end = overrides.get("end_at", start + timedelta(hours=2))

    t = Tournament.objects.create(
        name=overrides.get("name", f"Sched Cup {ts}"),
        # slug auto-filled from name by model.save()
        reg_open_at=reg_open,
        reg_close_at=reg_close,
        start_at=start,
        end_at=end,
        slot_size=overrides.get("slot_size", 8),
        entry_fee_bdt=overrides.get("entry_fee_bdt", 0),
        prize_pool_bdt=overrides.get("prize_pool_bdt", 0),
        # status has default "DRAFT"
    )
    return t


def _make_match(t, round_no, position=1):
    """Create a minimal Match; validations in clean() won't run unless full_clean() is called."""
    from apps.tournaments.models import Match
    return Match.objects.create(tournament=t, round_no=round_no, position=position)


def test_auto_schedule_assigns_times_across_rounds():
    from apps.tournaments.models import TournamentSettings
    from apps.tournaments.services.scheduling import auto_schedule_matches

    t = _create_tournament()
    # Ensure settings exist with known knobs
    s = getattr(t, "settings", None) or TournamentSettings.objects.create(tournament=t)
    s.round_duration_mins = 40
    s.round_gap_mins = 5
    s.save()

    # Round 1 -> two matches; Round 2 -> one match
    m1 = _make_match(t, 1, 1)
    m2 = _make_match(t, 1, 2)
    m3 = _make_match(t, 2, 1)

    updated = auto_schedule_matches(t)
    assert updated == 3

    # Refresh from DB
    m1.refresh_from_db(); m2.refresh_from_db(); m3.refresh_from_db()

    assert m1.start_at == t.start_at
    assert m2.start_at == t.start_at
    assert m3.start_at == t.start_at + timedelta(minutes=40 + 5)


def test_clear_schedule_removes_start_times():
    from apps.tournaments.models import TournamentSettings
    from apps.tournaments.services.scheduling import auto_schedule_matches, clear_schedule

    t = _create_tournament()
    s = getattr(t, "settings", None) or TournamentSettings.objects.create(tournament=t)
    s.round_duration_mins = 30
    s.round_gap_mins = 10
    s.save()

    m1 = _make_match(t, 1, 1)
    m2 = _make_match(t, 2, 1)

    auto_schedule_matches(t)
    m1.refresh_from_db(); m2.refresh_from_db()
    assert m1.start_at is not None and m2.start_at is not None

    cleared = clear_schedule(t)
    assert cleared == 2

    m1.refresh_from_db(); m2.refresh_from_db()
    assert m1.start_at is None and m2.start_at is None


def test_checkin_window_helpers():
    from apps.tournaments.models import TournamentSettings
    from apps.tournaments.services.scheduling import get_checkin_window

    t = _create_tournament()
    s = getattr(t, "settings", None) or TournamentSettings.objects.create(tournament=t)
    s.check_in_open_mins = 60
    s.check_in_close_mins = 15
    s.save()

    m = _make_match(t, 1, 1)
    # Give the match a start time
    m.start_at = t.start_at
    m.save(update_fields=["start_at"])

    open_dt, close_dt = get_checkin_window(m)
    assert open_dt == t.start_at - timedelta(minutes=60)
    assert close_dt == t.start_at - timedelta(minutes=15)
