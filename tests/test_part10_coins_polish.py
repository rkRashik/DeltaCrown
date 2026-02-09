# tests/test_part10_coins_polish.py
import pytest

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction, CoinPolicy
from apps.economy import services as coin_services
from apps.tournaments.models import Tournament, Registration, Match
from apps.organizations.models import Team, TeamMembership


def _profile(user):
    from apps.user_profile.models import UserProfile
    p, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username})
    return p


@pytest.mark.django_db
def test_participation_awarded_once_on_verified_payment(django_user_model):
    u = django_user_model.objects.create_user(username="p1", email="p1@example.com", password="x")
    p = _profile(u)

    # SOLO tournament for a user registration (eFootball = solo)
    t = Tournament.objects.create(name="Cup", game="efootball")
    CoinPolicy.objects.get_or_create(tournament=t, defaults=dict(participation=5, top4=25, runner_up=50, winner=100))

    reg = Registration.objects.create(tournament=t, user=p, status="confirmed", payment_status="verified")

    # Ensure there is exactly one PV per registration, then flip to verified
    from apps.tournaments.models import PaymentVerification
    pv, _ = PaymentVerification.objects.get_or_create(
        registration=reg,
        defaults=dict(method="bkash", amount_bdt=100)
    )
    pv.method = "bkash"
    pv.amount_bdt = 100
    pv.status = "verified"
    pv.save()

    # Signal should award once
    w = DeltaCrownWallet.objects.get(profile=p)
    assert w.cached_balance == 5
    assert DeltaCrownTransaction.objects.filter(wallet=w, reason="participation").count() == 1

    # Saving PV again should not create duplicates (idempotency)
    pv.save()
    w.refresh_from_db()
    assert w.cached_balance == 5
    assert DeltaCrownTransaction.objects.filter(wallet=w, reason="participation").count() == 1


@pytest.mark.django_db
def test_backfill_awards_for_existing_verified_regs(django_user_model):
    # Setup users
    u1 = django_user_model.objects.create_user(username="solo", email="solo@example.com", password="x")
    u2 = django_user_model.objects.create_user(username="cpt", email="cpt@example.com", password="x")
    u3 = django_user_model.objects.create_user(username="m1", email="m1@example.com", password="x")
    u4 = django_user_model.objects.create_user(username="m2", email="m2@example.com", password="x")

    p1 = _profile(u1)
    cpt = _profile(u2)
    m1 = _profile(u3)
    m2 = _profile(u4)

    # SOLO tournament (user reg)
    t_solo = Tournament.objects.create(name="Backfill Cup (Solo)", game="efootball")
    CoinPolicy.objects.get_or_create(tournament=t_solo, defaults=dict(participation=5, top4=0, runner_up=0, winner=0))

    # TEAM tournament (team reg)
    t_team = Tournament.objects.create(name="Backfill Cup (Team)", game="valorant")
    CoinPolicy.objects.get_or_create(tournament=t_team, defaults=dict(participation=5, top4=0, runner_up=0, winner=0))

    solo_reg = Registration.objects.create(tournament=t_solo, user=p1, status="confirmed", payment_status="verified")

    team = Team.objects.create(name="Alpha", tag="ALP", captain=cpt)
    # app auto-creates captain membership; ensure idempotent
    TeamMembership.objects.get_or_create(team=team, profile=cpt, defaults={"role": "CAPTAIN"})
    TeamMembership.objects.get_or_create(team=team, profile=m1, defaults={"role": "PLAYER"})
    TeamMembership.objects.get_or_create(team=team, profile=m2, defaults={"role": "PLAYER"})

    team_reg = Registration.objects.create(tournament=t_team, team=team, status="confirmed", payment_status="verified")

    from apps.tournaments.models import PaymentVerification
    # Ensure one PV per registration, set to verified
    pv1, _ = PaymentVerification.objects.get_or_create(
        registration=solo_reg, defaults=dict(method="bkash", amount_bdt=100)
    )
    pv1.method = "bkash"
    pv1.amount_bdt = 100
    pv1.status = "verified"
    pv1.save()

    pv2, _ = PaymentVerification.objects.get_or_create(
        registration=team_reg, defaults=dict(method="bkash", amount_bdt=100)
    )
    pv2.method = "bkash"
    pv2.amount_bdt = 100
    pv2.status = "verified"
    pv2.save()

    # Now run backfill
    processed = coin_services.backfill_participation_for_verified_payments()
    assert processed >= 2

    # Check wallets
    assert DeltaCrownWallet.objects.get(profile=p1).cached_balance == 5
    assert DeltaCrownWallet.objects.get(profile=cpt).cached_balance == 5
    assert DeltaCrownWallet.objects.get(profile=m1).cached_balance == 5
    assert DeltaCrownWallet.objects.get(profile=m2).cached_balance == 5


@pytest.mark.django_db
def test_award_placements_is_idempotent(django_user_model):
    # Build two teams with captains
    uA = django_user_model.objects.create_user(username="cA", email="cA@example.com", password="x")
    uB = django_user_model.objects.create_user(username="cB", email="cB@example.com", password="x")
    cpA = _profile(uA)
    cpB = _profile(uB)

    teamA = Team.objects.create(name="A", tag="A", captain=cpA)
    teamB = Team.objects.create(name="B", tag="B", captain=cpB)

    # app usually auto-creates captain membership; guard against duplicates
    TeamMembership.objects.get_or_create(team=teamA, profile=cpA, defaults={"role": "CAPTAIN"})
    TeamMembership.objects.get_or_create(team=teamB, profile=cpB, defaults={"role": "CAPTAIN"})

    t = Tournament.objects.create(name="V5", game="valorant")
    CoinPolicy.objects.get_or_create(tournament=t, defaults=dict(participation=0, top4=10, runner_up=50, winner=100))

    # final: teamA vs teamB, teamA wins
    final = Match.objects.create(tournament=t, round_no=4, position=1, team_a=teamA, team_b=teamB, winner_team=teamA)
    # semifinals (for top4)
    Match.objects.create(tournament=t, round_no=3, position=1, team_a=teamA, team_b=teamB, winner_team=teamA)
    Match.objects.create(tournament=t, round_no=3, position=2, team_a=teamA, team_b=teamB, winner_team=teamB)

    a1 = coin_services.award_placements(t)
    a2 = coin_services.award_placements(t)

    # Should not duplicate winner/runner_up/top4 per wallet
    wA = DeltaCrownWallet.objects.get(profile=cpA)
    wB = DeltaCrownWallet.objects.get(profile=cpB)
    assert DeltaCrownTransaction.objects.filter(wallet=wA, reason="winner").count() == 1
    assert DeltaCrownTransaction.objects.filter(wallet=wB, reason="runner_up").count() == 1
    # top4 at most once per captain
    assert DeltaCrownTransaction.objects.filter(reason="top4", wallet=wA).count() <= 1
    assert DeltaCrownTransaction.objects.filter(reason="top4", wallet=wB).count() <= 1
