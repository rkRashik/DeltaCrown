# tests/test_part6_registration_pv.py
import pytest
from django.test import RequestFactory

from apps.tournaments.models import Tournament, PaymentVerification
from apps.tournaments.services.registration import SoloRegistrationInput, register_efootball_player


@pytest.fixture
def admin_user(django_user_model, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )


def _attach_session_and_messages(request):
    """Attach session + messages so admin.message_user works in tests."""
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages.storage.fallback import FallbackStorage
    # session
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    # messages
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.mark.django_db
def test_pv_populated_on_solo_registration(django_user_model):
    from django.utils import timezone
    from datetime import timedelta
    from apps.tournaments.models import Game
    organizer = django_user_model.objects.create_user("org", "org@example.com", "pass")
    u = django_user_model.objects.create_user("p1", "p1@example.com", "pass")
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=u)
    game = Game.objects.create(name="eFootball", slug="efootball")
    now = timezone.now()
    t = Tournament.objects.create(
        name="E-Cup P6",
        game=game,
        organizer=organizer,
        max_participants=16,
        tournament_start=now + timedelta(days=7),
        registration_start=now,
        registration_end=now + timedelta(days=5)
    )

    data = SoloRegistrationInput(
        tournament_id=t.id,
        user_id=u.id,  # Pass User ID, not UserProfile ID
        payment_method="bkash",
        payment_reference="TX-ABC-123",
        payer_account_number="017XXXXXXXX",
        amount_bdt=150.0,
    )
    reg = register_efootball_player(data)

    pv = getattr(reg, "payment_verification", None)
    assert pv is not None
    assert pv.method == "bkash"
    assert pv.transaction_id == "TX-ABC-123"
    assert pv.payer_account_number.endswith("X")
    assert pv.amount_bdt in (150, 150.0)


@pytest.mark.django_db
def test_admin_duplicate_transaction_id_block(admin_user, django_user_model):
    from django.utils import timezone
    from datetime import timedelta
    from apps.tournaments.models import Game
    organizer = django_user_model.objects.create_user("org", "org@example.com", "pass")
    # two regs, same transaction id
    u1 = django_user_model.objects.create_user("a", "a@example.com", "pass")
    u2 = django_user_model.objects.create_user("b", "b@example.com", "pass")
    from apps.user_profile.models import UserProfile
    p1, _ = UserProfile.objects.get_or_create(user=u1)
    p2, _ = UserProfile.objects.get_or_create(user=u2)
    game = Game.objects.create(name="eFootball", slug="efootball")
    now = timezone.now()
    t = Tournament.objects.create(
        name="E-Cup P6 Dups",
        game=game,
        organizer=organizer,
        max_participants=16,
        tournament_start=now + timedelta(days=7),
        registration_start=now,
        registration_end=now + timedelta(days=5)
    )

    reg1 = register_efootball_player(SoloRegistrationInput(tournament_id=t.id, user_id=u1.id, payment_method="bkash", payment_reference="DUP-TX", payer_account_number="017...", amount_bdt=100))
    reg2 = register_efootball_player(SoloRegistrationInput(tournament_id=t.id, user_id=u2.id, payment_method="bkash", payment_reference="DUP-TX", payer_account_number="018...", amount_bdt=100))

    pv1 = reg1.payment_verification
    pv2 = reg2.payment_verification

    # verify pv1 via admin action
    from apps.tournaments.admin.payment_verification import PaymentVerificationAdmin
    from django.contrib.admin.sites import AdminSite
    ma = PaymentVerificationAdmin(PaymentVerification, AdminSite())

    rf = RequestFactory()
    req = _attach_session_and_messages(rf.post("/admin/tournaments/paymentverification/"))
    req.user = admin_user

    ma.action_verify(req, PaymentVerification.objects.filter(pk=pv1.pk))
    pv1.refresh_from_db()
    assert pv1.status == PaymentVerification.Status.VERIFIED

    # now try to verify pv2 with same tx => should skip
    ma.action_verify(req, PaymentVerification.objects.filter(pk=pv2.pk))
    pv2.refresh_from_db()
    assert pv2.status == PaymentVerification.Status.PENDING
