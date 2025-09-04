# tests/test_part3_payments.py
import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.tournaments.models import Tournament, PaymentVerification


@pytest.fixture
def admin_user(django_user_model, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )


@pytest.fixture
def rf():
    return RequestFactory()


def _make_profile_for(user):
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _attach_session_and_messages(request):
    """
    Admin actions call message_user(), which requires request.session and request._messages.
    Wire them up manually for RequestFactory-based requests.
    """
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages.storage.fallback import FallbackStorage

    # session
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()

    # messages
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.mark.django_db
def test_payment_verification_autocreated_on_registration(admin_user, django_user_model):
    player_user = django_user_model.objects.create_user("player", "player@example.com", "pass")
    player_profile = _make_profile_for(player_user)
    t = Tournament.objects.create(name="E-Cup P3", game="efootball")

    from apps.tournaments.models import Registration
    reg = Registration.objects.create(tournament=t, user=player_profile)

    pv = getattr(reg, "payment_verification", None)
    assert pv is not None
    assert pv.status == PaymentVerification.Status.PENDING


@pytest.mark.django_db
def test_finance_queue_email_action_sends_mail_from_pending(admin_user, django_user_model, rf):
    # registrant
    u = django_user_model.objects.create_user("u1", "u1@example.com", "pass")
    from apps.user_profile.models import UserProfile
    u_profile, _ = UserProfile.objects.get_or_create(user=u)

    t = Tournament.objects.create(name="E-Cup P3B", game="efootball")
    from apps.tournaments.models import Registration
    reg = Registration.objects.create(tournament=t, user=u_profile)
    pv = reg.payment_verification
    pv.method = PaymentVerification.Method.BKASH
    pv.payer_account_number = "01700000000"
    pv.transaction_id = "BKASH-TX-123456"
    pv.amount_bdt = 150
    pv.save()

    # Get the registered ModelAdmin and its action function safely
    from django.contrib.admin.sites import site
    ma = site._registry[PaymentVerification]  # the registered ModelAdmin

    # get_actions needs a request with a user; messages not required here but harmless
    get_req = _attach_session_and_messages(rf.get("/admin/"))
    get_req.user = admin_user
    actions = dict(ma.get_actions(get_req))
    assert "action_email_registrant" in actions, "Admin action not registered"
    func, _name, _desc = actions["action_email_registrant"]

    # Execute action with a staff request, now including session+messages
    post_req = _attach_session_and_messages(rf.post("/admin/tournaments/paymentverification/"))
    post_req.user = admin_user
    qs = PaymentVerification.objects.filter(pk=pv.pk)
    func(ma, post_req, qs)

    # Assert mail sent
    assert len(mail.outbox) >= 1
    body = mail.outbox[-1].body.lower()
    assert "transaction id" in body and "payer account" in body


@pytest.mark.django_db
def test_verification_helpers_transition_status(admin_user, django_user_model):
    u = django_user_model.objects.create_user("p", "p@example.com", "pass")
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=u)
    t = Tournament.objects.create(name="E-Coin Cup", game="efootball")

    from apps.tournaments.models import Registration
    reg = Registration.objects.create(tournament=t, user=profile)
    pv = reg.payment_verification

    pv.mark_verified(admin_user)
    pv.refresh_from_db()
    assert pv.status == PaymentVerification.Status.VERIFIED
    assert pv.verified_by == admin_user
    assert pv.verified_at is not None

    pv.mark_rejected(admin_user, reason="Mismatch")
    pv.refresh_from_db()
    assert pv.status == PaymentVerification.Status.REJECTED
    assert pv.reject_reason.lower().startswith("mismatch")


@pytest.mark.django_db
def test_valorant_requires_team_registration(django_user_model):
    """
    Validator fires in pre_save. Creating a solo reg for Valorant should error on save().
    """
    u = django_user_model.objects.create_user("vuser", "vuser@example.com", "pass")
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=u)
    t = Tournament.objects.create(name="V-Cup Team Mode", game="valorant")

    from apps.tournaments.models import Registration
    reg = Registration(tournament=t, user=profile)  # no team on a team-mode tourney

    with pytest.raises(ValidationError):
        reg.save()  # pre_save validator fires
