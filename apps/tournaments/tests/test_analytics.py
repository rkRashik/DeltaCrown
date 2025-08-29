# apps/tournaments/tests/test_analytics.py
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _tournament():
    from apps.tournaments.models import Tournament
    now = timezone.now()
    return Tournament.objects.create(
        name=f"Analytica {now.timestamp()}",
        reg_open_at=now,
        reg_close_at=now + timedelta(hours=1),
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=4),
        slot_size=8,
        entry_fee_bdt=Decimal("100.00"),
        prize_pool_bdt=0,
    )


def _profile(username: str, email: str, display_name: str):
    from django.contrib.auth import get_user_model
    from apps.user_profile.models import UserProfile
    U = get_user_model()
    u = U.objects.create_user(username=username, email=email, password="x")
    p, created = UserProfile.objects.get_or_create(
        user=u,
        defaults={"display_name": display_name}
    )
    # If a signal already created it without display_name, update once.
    if not getattr(p, "display_name", None):
        p.display_name = display_name
        p.save(update_fields=["display_name"])
    return p


def test_tournament_stats_counts():
    from apps.tournaments.models import Registration, Match, Bracket
    from apps.tournaments.services.analytics import tournament_stats
    from apps.teams.models import Team

    # Profiles (robust to auto-create signals)
    p1 = _profile("u1", "u1@example.com", "U1")
    p2 = _profile("u2", "u2@example.com", "U2")

    t = _tournament()

    # Registrations:
    # 1) confirmed + verified (solo) -> counts toward revenue
    Registration.objects.create(
        tournament=t, user=p1, status="CONFIRMED", payment_status="verified"
    )
    # 2) confirmed + pending (solo)
    Registration.objects.create(
        tournament=t, user=p2, status="CONFIRMED", payment_status="pending"
    )
    # 3) pending (team) — use team to respect unique_together on (tournament, user)
    team = Team.objects.create(name="Alpha", tag="ALP", captain=p2)
    Registration.objects.create(
        tournament=t, team=team, status="PENDING", payment_status="pending"
    )

    # Matches
    m1 = Match.objects.create(tournament=t, round_no=1, position=1, state="SCHEDULED")
    m2 = Match.objects.create(tournament=t, round_no=1, position=2, state="VERIFIED")
    m3 = Match.objects.create(tournament=t, round_no=2, position=1, state="SCHEDULED")

    m1.start_at = t.start_at                       # scheduled = at start
    m2.start_at = None                             # unscheduled
    m3.start_at = timezone.now() + timedelta(hours=12)  # upcoming within 24h
    Match.objects.bulk_update([m1, m2, m3], ["start_at"])

    # Bracket
    Bracket.objects.create(tournament=t, is_locked=True)

    # Assert
    s = tournament_stats(t)

    regs = s["registrations"]
    assert regs["total"] == 3
    assert regs["confirmed"] == 2
    assert regs["verified_payments"] == 1
    assert regs["revenue_bdt"] == Decimal("100.00")

    mts = s["matches"]
    assert mts["total"] == 3
    assert mts["unscheduled"] == 1
    assert mts["upcoming_24h"] >= 1
    assert mts["max_round"] == 2

    assert s["bracket"]["status"] == "Locked"
