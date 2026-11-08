"""OL-10B: schedule text must use the site timezone, like Django's date/time template filters.

Synthetic aware datetimes; no database. 20:30 UTC on 8 Nov is already 9 Nov in Asia/Dhaka (UTC+6),
which is the case that exposed the original UTC/local mismatch.
"""
from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.template import Context, Template
from django.utils import timezone

from apps.common.display_time import format_local, to_site_time, tz_label
from apps.tournaments.models import Match
from apps.tournaments.views.live import _build_match_timeline_rows

INSTANT = datetime(2026, 11, 8, 20, 30, tzinfo=dt_timezone.utc)


def test_site_time_conversion_changes_the_date_but_not_the_instant():
    local = to_site_time(INSTANT)
    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 11, 9, 2, 30)
    assert local == INSTANT and local.timestamp() == INSTANT.timestamp()


def test_label_is_an_explicit_offset_and_follows_the_site_timezone_setting():
    assert tz_label(INSTANT) == "UTC+06:00"
    assert format_local(INSTANT, "%b %d, %I:%M %p") == "Nov 09, 02:30 AM (UTC+06:00)"
    assert format_local(INSTANT, "%H:%M", label=False) == "02:30"
    with timezone.override("America/New_York"):  # nothing is hardcoded to +06:00
        assert format_local(INSTANT, "%b %d, %I:%M %p") == "Nov 08, 03:30 PM (UTC-05:00)"


def test_naive_values_pass_through_without_a_misleading_label():
    naive = datetime(2026, 11, 8, 20, 30)
    assert format_local(naive, "%H:%M") == "20:30"


def test_match_timeline_text_matches_the_template_filter_for_the_same_instant():
    match = SimpleNamespace(
        scheduled_time=INSTANT, state=Match.SCHEDULED, updated_at=INSTANT, winner_id=None,
        participant1_id=1, participant2_id=2, participant1_name="A", participant2_name="B",
    )
    row = _build_match_timeline_rows(match)[0]
    assert row["description"] == "Match scheduled for November 09, 2026 at 02:30 AM (UTC+06:00)"
    assert row["timestamp"] == INSTANT  # the stored instant is untouched
    rendered = Template("{{ value|date:'F d, Y' }} {{ value|time:'h:i A' }}").render(Context({"value": INSTANT}))
    assert rendered.startswith("November 09, 2026 02:30 AM")  # the filter and the text now agree


def test_countdown_attribute_carries_the_real_instant_not_display_text():
    iso = Template("{{ value|date:'c' }}").render(Context({"value": INSTANT}))
    assert iso == "2026-11-09T02:30:00+06:00"
    assert datetime.fromisoformat(iso) == INSTANT  # same instant: a countdown computed from it is exact
