import pytest

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction, CoinPolicy
from apps.economy import services as coin_services
from apps.tournaments.models import Tournament, Match


def _profile(user):
    from apps.user_profile.models import UserProfile
    p, _ = UserProfile.objects.get_or_create(user=user)
    return p


@pytest.mark.django_db
def test_participation_award_on_payment_verified(django_user_model):
    # users/profiles
    u = django_user_model.objects.create_user("p", "p@example.com", "pass")
    p = _profile(u)

    # tournament (solo)
    t = Tournament.objects.create(name="E5", game="efootball")
    CoinPolicy.objects.get_or_create(tournament=t, defaults=dict(participation=7, top4=25, runner_up=50, winner=100))

    # registration + PV
    from apps.tournaments.models import Registration, PaymentVerification
    reg = Registration.objects.create(tournament=t, user=p)
    # use existing PV if auto-created; otherwise create it
    pv, _ = PaymentVerification.objects.get_or_create(registration=reg, defaults={"method": "bkash", "status": "pending"})
    # verify -> should award
    pv.mark_verified(django_user_model.objects.create_user("admin", "a@e.com", "pass"))
    # trigger service directly (signal also does it, but keep deterministic)
    coin_services.award_participation_for_registration(reg)

    w = DeltaCrownWallet.objects.get(profile=p)
    assert w.cached_balance == 7
    assert DeltaCrownTransaction.objects.filter(wallet=w, reason="participation").count() == 1


@pytest.mark.django_db
def test_placement_awards_solo(django_user_model):
    # two users + profiles
    u1 = django_user_model.objects.create_user("a", "a@x.com", "pass")
    u2 = django_user_model.objects.create_user("b", "b@x.com", "pass")
    p1, p2 = _profile(u1), _profile(u2)
    t = Tournament.objects.create(name="Final Solo", game="efootball")
    CoinPolicy.objects.get_or_create(tournament=t, defaults=dict(participation=5, top4=25, runner_up=50, winner=100))

    # final match only: p1 vs p2, p1 wins
    m = Match.objects.create(tournament=t, round_no=3, position=1, user_a=p1, user_b=p2, winner_user=p1)

    awards = coin_services.award_placements(t)
    # winner 100, runner-up 50
    w1 = DeltaCrownWallet.objects.get(profile=p1)
    w2 = DeltaCrownWallet.objects.get(profile=p2)
    assert any(tx.amount == 100 and tx.reason == "winner" for tx in w1.transactions.all())
    assert any(tx.amount == 50 and tx.reason == "runner_up" for tx in w2.transactions.all())


@pytest.mark.django_db
def test_placement_awards_valorant_team(django_user_model):
    # create two teams (each with 5 active members)
    from apps.organizations.models import Team, TeamMembership
    # captains
    cu1 = django_user_model.objects.create_user("cap1", "c1@x.com", "pass")
    cu2 = django_user_model.objects.create_user("cap2", "c2@x.com", "pass")
    cp1, cp2 = _profile(cu1), _profile(cu2)
    teamA = Team.objects.create(name="Alpha", tag="ALP", captain=cp1)
    teamB = Team.objects.create(name="Bravo", tag="BRV", captain=cp2)
    # add a few members
    for i in range(4):
        u = django_user_model.objects.create_user(f"a{i}", f"a{i}@x.com", "pass")
        TeamMembership.objects.create(team=teamA, profile=_profile(u), role="PLAYER")
    for i in range(4):
        u = django_user_model.objects.create_user(f"b{i}", f"b{i}@x.com", "pass")
        TeamMembership.objects.create(team=teamB, profile=_profile(u), role="PLAYER")

    t = Tournament.objects.create(name="V5", game="valorant")
    CoinPolicy.objects.get_or_create(tournament=t, defaults=dict(participation=5, top4=25, runner_up=50, winner=100))

    # final: teamA vs teamB, teamA wins
    m = Match.objects.create(tournament=t, round_no=4, position=1, team_a=teamA, team_b=teamB, winner_team=teamA)

    awards = coin_services.award_placements(t)
    # assert at least captain of A got 100, captain of B got 50
    wpA = DeltaCrownWallet.objects.get(profile=cp1)
    wpB = DeltaCrownWallet.objects.get(profile=cp2)
    assert any(tx.amount == 100 and tx.reason == "winner" for tx in wpA.transactions.all())
    assert any(tx.amount == 50 and tx.reason == "runner_up" for tx in wpB.transactions.all())
