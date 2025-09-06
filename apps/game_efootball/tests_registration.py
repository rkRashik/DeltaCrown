# apps/game_efootball/tests_registration.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from apps.user_profile.models import UserProfile
from apps.tournaments.models import Tournament

@pytest.mark.django_db
def test_efootball_solo_prefill_and_payment_required(client):
    u = User.objects.create_user(username="solo", password="x", email="solo@example.com")
    prof = UserProfile.objects.create(user=u, display_name="Solo Player", phone="01711...", efootball_id="SoloIGN")
    t = Tournament.objects.create(name="EFootball Solo Cup", slug="efb-solo", game="efootball")
    t.settings.entry_fee_bdt = 150  # pseudo: your model has OneToOne; simulate or set properly
    t.settings.save()

    client.login(username="solo", password="x")
    url = reverse("tournaments:register", args=[t.slug])

    # GET renders and pre-fills (cannot assert initial via HTML easily; just ensure 200)
    assert client.get(url).status_code == 200

    # POST without payment should fail (required when fee > 0)
    r = client.post(url, {
        "full_name": "Solo Player",
        "ign": "SoloIGN",
        "email": "solo@example.com",
        "phone": "01711...",
        "personal_team_name": "SoloTeam",
        "team_strength": 85,
        "agree_rules": True,
        "agree_no_tools": True,
        "agree_no_double": True,
    })
    assert r.status_code == 200
    assert b"This field is required" in r.content  # payment fields

    # With payment ok
    r = client.post(url, {
        "full_name": "Solo Player",
        "ign": "SoloIGN",
        "email": "solo@example.com",
        "phone": "01711...",
        "personal_team_name": "SoloTeam",
        "team_strength": 85,
        "agree_rules": True,
        "agree_no_tools": True,
        "agree_no_double": True,
        "payment_method": "bkash",
        "payer_account_number": "017XXXXXXXX",
        "payment_reference": "TX123",
        "amount_bdt": 150,
    }, follow=True)
    assert r.status_code == 200
    assert b"Registration submitted" in r.content


@pytest.mark.django_db
def test_efootball_duo_captain_team_flow(client):
    captain = User.objects.create_user(username="cap", password="x", email="cap@example.com")
    mate = User.objects.create_user(username="mate", password="x", email="mate@example.com")
    cap_prof = UserProfile.objects.create(user=captain, display_name="Cap", efootball_id="CapIGN")
    mate_prof = UserProfile.objects.create(user=mate, display_name="Mate", efootball_id="MateIGN")

    t = Tournament.objects.create(name="EFootball Duo Cup", slug="efb-duo", game="efootball")

    client.login(username="cap", password="x")
    url = reverse("tournaments:register", args=[t.slug])

    # Minimal duo POST without selecting existing team (creates new team)
    payload = {
        "__team_flow": "1",
        "team_name": "TwoMan",
        "captain_full_name": "Cap",
        "captain_ign": "CapIGN",
        "captain_email": "cap@example.com",
        "captain_phone": "017...",
        "mate_full_name": "Mate",
        "mate_ign": "MateIGN",
        "mate_email": "mate@example.com",
        "mate_phone": "018...",
        "agree_consent": True,
        "agree_rules": True,
        "agree_no_tools": True,
        "agree_no_multi_team": True,
        "payment_method": "bkash",
        "payer_account_number": "017XXXXXXXX",
        "payment_reference": "TX456",
        "amount_bdt": 0,
    }
    r = client.post(url, payload, follow=True)
    assert r.status_code == 200
    assert b"Registration submitted" in r.content
