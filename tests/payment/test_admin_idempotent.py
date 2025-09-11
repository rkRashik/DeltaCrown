import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_payment_verification_admin_idempotent(client):
    User = get_user_model()
    admin = User.objects.create_superuser(username="admin", email="a@a.com", password="x")
    client.force_login(admin)

    from apps.tournaments.models import Tournament, Registration, PaymentVerification
    from apps.user_profile.models import UserProfile

    t = Tournament.objects.create(name="Test Cup", slug="test-cup", game="efootball")
    u = User.objects.create_user(username="player", password="x")
    # profile auto-created via signals; fetch it
    prof = UserProfile.objects.get(user=u)
    reg = Registration.objects.create(tournament=t, user=prof)
    pv, _ = PaymentVerification.objects.get_or_create(registration=reg, defaults={"status": PaymentVerification.Status.PENDING})

    url = "/admin/tournaments/paymentverification/"

    resp1 = client.post(url, {
        "action": "action_verify",
        "_selected_action": [str(pv.id)],
    }, follow=True)
    assert resp1.status_code == 200
    pv.refresh_from_db()
    assert pv.status == PaymentVerification.Status.VERIFIED
    assert pv.verified_by == admin
    assert pv.verified_at is not None

    resp2 = client.post(url, {
        "action": "action_verify",
        "_selected_action": [str(pv.id)],
    }, follow=True)
    assert resp2.status_code == 200
    pv.refresh_from_db()
    assert pv.status == PaymentVerification.Status.VERIFIED
    assert b"Skipped" in resp2.content
