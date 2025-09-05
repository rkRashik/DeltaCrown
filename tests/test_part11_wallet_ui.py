# tests/test_part11_wallet_ui.py
import io
import csv
import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.economy.models import DeltaCrownTransaction
from apps.economy import services as coin_services
from apps.tournaments.models import Tournament


def _profile(user):
    from apps.user_profile.models import UserProfile
    p, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username})
    return p


@pytest.mark.django_db
def test_wallet_page_shows_balance_and_transactions(client, django_user_model):
    u = django_user_model.objects.create_user(username="w1", password="x")
    p = _profile(u)

    # Make some transactions
    t = Tournament.objects.create(name="Solo Cup", game="efootball")
    coin_services.manual_adjust(coin_services.wallet_for(p), 10, note="Seed")
    coin_services.award(
        profile=p,
        amount=5,
        reason=DeltaCrownTransaction.Reason.PARTICIPATION,
        tournament=t,
        note="Participation",
    )

    client.force_login(u)
    resp = client.get(reverse("economy:wallet"))
    assert resp.status_code == 200
    # Balance visible
    assert "coins" in resp.content.decode().lower()
    # At least one of our rows present
    body = resp.content.decode()
    assert "Participation" in body or "Seed" in body


@pytest.mark.django_db
def test_wallet_filters_and_csv(client, django_user_model):
    u = django_user_model.objects.create_user(username="w2", password="x")
    p = _profile(u)
    w = coin_services.wallet_for(p)

    # Create 2 reasons w/ dates
    tx1 = coin_services.manual_adjust(w, 50, note="OLD_A_TX")
    tx2 = coin_services.manual_adjust(w, -20, note="NEW_B_TX")
    # Nudge dates: tx1 older by 5 days
    five_days_ago = timezone.now() - dt.timedelta(days=5)
    tx1.created_at = five_days_ago
    tx1.save(update_fields=["created_at"])

    client.force_login(u)

    # Filter: start should exclude tx1 (older)
    url = reverse("economy:wallet") + f"?start={(timezone.now()-dt.timedelta(days=2)).date().isoformat()}"
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "OLD_A_TX" not in html  # filtered out
    assert "NEW_B_TX" in html      # remains

    # CSV export: include both when no filters
    resp_csv = client.get(reverse("economy:wallet") + "?format=csv")
    assert resp_csv.status_code == 200
    assert resp_csv["Content-Type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(resp_csv.content.decode())))
    assert rows[0] == [
        "created_at",
        "amount",
        "reason",
        "note",
        "tournament",
        "registration_id",
        "match_id",
        "idempotency_key",
    ]
    # Header + at least 2 rows for tx1 & tx2
    assert any(r[3] == "OLD_A_TX" for r in rows[1:])
    assert any(r[3] == "NEW_B_TX" for r in rows[1:])


@pytest.mark.django_db
def test_wallet_pagination(client, django_user_model):
    u = django_user_model.objects.create_user(username="w3", password="x")
    p = _profile(u)
    w = coin_services.wallet_for(p)

    # Create 35 rows (row35 is newest given creation order)
    for i in range(35):
        coin_services.manual_adjust(w, 1, note=f"row{i+1}")

    client.force_login(u)
    # Page 1 (newest 20)
    resp1 = client.get(reverse("economy:wallet"))
    assert resp1.status_code == 200
    html1 = resp1.content.decode()
    assert "row35" in html1  # newest should be present on page 1

    # Page 2 (older remainder)
    resp2 = client.get(reverse("economy:wallet") + "?page=2")
    assert resp2.status_code == 200
    html2 = resp2.content.decode()
    assert "row1" in html2           # oldest should be present on page 2
    assert "row35" not in html2      # newest should not be on page 2
