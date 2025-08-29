# apps/tournaments/tests/test_manual_payments.py
import types
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _tournament_paid():
    from apps.tournaments.models import Tournament, TournamentSettings
    now = timezone.now()
    t = Tournament.objects.create(
        name=f"PayCup {now.timestamp()}",
        reg_open_at=now,
        reg_close_at=now + timedelta(hours=1),
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=4),
        slot_size=8,
        entry_fee_bdt=Decimal("100.00"),
        prize_pool_bdt=0,
    )
    TournamentSettings.objects.create(
        tournament=t,
        bkash_receive_number="017XXXXXXXX"
    )
    return t


def _profile(username="p1"):
    from django.contrib.auth import get_user_model
    from apps.user_profile.models import UserProfile
    U = get_user_model()
    u = U.objects.create_user(username=username, email=f"{username}@e.com", password="x")
    p, _ = UserProfile.objects.get_or_create(user=u, defaults={"display_name": username})
    return p


def test_registration_requires_payment_fields_for_wallet_methods(settings):
    from apps.tournaments.forms import SoloRegistrationForm
    t = _tournament_paid()
    p = _profile("rahim")
    form = SoloRegistrationForm(
        data={
            "payment_method": "bkash",
            "payment_sender": "",        # missing
            "payment_reference": "",     # missing
        },
        tournament=t,
        user_profile=p,
    )
    assert not form.is_valid()
    assert "payment_sender" in form.errors
    assert "payment_reference" in form.errors


def test_admin_verify_sets_flags_and_status(admin_user):
    from django.contrib.admin.sites import site
    from apps.tournaments.models import Registration
    from apps.tournaments.admin import RegistrationAdmin, action_verify_payment
    t = _tournament_paid()
    p = _profile("karim")
    r = Registration.objects.create(
        tournament=t,
        user=p,
        status="PENDING",
        payment_status="pending",
        payment_method="bkash",
        payment_sender="01700000000",
        payment_reference="TRX123",
    )
    ma = RegistrationAdmin(Registration, site)
    req = types.SimpleNamespace(user=admin_user, META={})
    qs = Registration.objects.filter(pk=r.pk)

    # Call action function with modeladmin + request + queryset
    action_verify_payment(ma, req, qs)

    r.refresh_from_db()
    assert r.payment_status == "verified"
    assert r.status == "CONFIRMED"
    assert r.payment_verified_by == admin_user
    assert r.payment_verified_at is not None
