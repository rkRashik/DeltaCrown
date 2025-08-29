import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.core import mail

pytestmark = pytest.mark.django_db

def _profile(username, email):
    from django.contrib.auth import get_user_model
    from apps.user_profile.models import UserProfile
    U = get_user_model()
    u = U.objects.create_user(username=username, email=email, password="x")
    p, _ = UserProfile.objects.get_or_create(user=u, defaults={"display_name": username})
    return p

def _tournament():
    from apps.tournaments.models import Tournament, TournamentSettings
    now = timezone.now()
    t = Tournament.objects.create(
        name=f"QA Cup {now.timestamp()}",
        reg_open_at=now,
        reg_close_at=now + timedelta(hours=1),
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=5),
        slot_size=8,
        entry_fee_bdt=Decimal("50.00"),
        prize_pool_bdt=0,
    )
    TournamentSettings.objects.get_or_create(
        tournament=t,
        defaults=dict(round_duration_mins=40, round_gap_mins=5, check_in_open_mins=60, check_in_close_mins=15),
    )
    return t

def test_happy_path_end_to_end(settings):
    # use in-memory email backend
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    from apps.tournaments.models import Registration, Match
    from apps.notifications.models import Notification
    from apps.tournaments.services.scheduling import auto_schedule_matches
    from django.core.management import call_command

    # players
    p1 = _profile("rahim", "rahim@example.com")
    p2 = _profile("karim", "karim@example.com")

    # tournament + settings
    t = _tournament()

    # both confirmed (one verified payment)
    Registration.objects.create(tournament=t, user=p1, status="CONFIRMED", payment_status="verified")
    Registration.objects.create(tournament=t, user=p2, status="CONFIRMED", payment_status="pending")

    # one match
    m = Match.objects.create(tournament=t, round_no=1, position=1, user_a=p1, user_b=p2)

    # schedule all matches from tournament start
    updated = auto_schedule_matches(t)
    assert updated >= 1

    # move start to 30 minutes from now -> inside check-in window (open=60, close=15)
    m.refresh_from_db()
    m.start_at = timezone.now() + timedelta(minutes=30)
    m.save(update_fields=["start_at"])

    # send reminders
    call_command("send_checkin_reminders")

    # notifications + emails
    assert Notification.objects.filter(type="checkin_open", match=m).count() >= 2
    assert len(mail.outbox) >= 2
