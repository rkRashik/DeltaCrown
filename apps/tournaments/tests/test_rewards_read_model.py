from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone

from apps.games.models import Game
from apps.tournaments.models import (
    Certificate,
    BracketNode,
    Match,
    PrizeClaim,
    PrizeTransaction,
    Registration,
    Tournament,
    TournamentResult,
)
from apps.brackets.models import Bracket
from apps.organizations.models import Team
from apps.tournaments.services.prize_config_service import PrizeConfigService
from apps.tournaments.services.post_finalization_service import PostFinalizationService
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.rewards_read_model import TournamentRewardsReadModel
from apps.tournaments.views.detail import tournament_prize_overview

User = get_user_model()


def _game():
    return Game.objects.create(slug='rewards-game', name='Rewards Game', is_active=True)


def _user(username):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.test',
        password='pass1234',
    )


def _tournament(
    organizer,
    game,
    *,
    slug='rewards-cup',
    status=Tournament.COMPLETED,
    participation_type=Tournament.SOLO,
):
    now = timezone.now()
    return Tournament.objects.create(
        name='Rewards Cup',
        slug=slug,
        description='Rewards integration test tournament.',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIMINATION,
        participation_type=participation_type,
        max_participants=8,
        min_participants=2,
        prize_pool=Decimal('50000.00'),
        prize_currency='BDT',
        prize_deltacoin=10000,
        registration_start=now - timedelta(days=10),
        registration_end=now - timedelta(days=5),
        tournament_start=now - timedelta(days=2),
        status=status,
    )


def _registration(tournament, user):
    return Registration.objects.create(
        tournament=tournament,
        user=user,
        status=Registration.CONFIRMED,
        registration_data={},
    )


def _team(name, owner, game):
    return Team.objects.create(
        name=name,
        created_by=owner,
        game_id=game.id,
        region='BD',
    )


def _team_registration(tournament, team):
    return Registration.objects.create(
        tournament=tournament,
        team_id=team.id,
        status=Registration.CONFIRMED,
        registration_data={},
    )


def _completed_match(
    tournament,
    bracket,
    *,
    round_number,
    match_number,
    winner,
    loser,
    winner_score=2,
    loser_score=1,
):
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=round_number,
        match_number=match_number,
        participant1_id=winner.id,
        participant1_name=winner.user.username,
        participant2_id=loser.id,
        participant2_name=loser.user.username,
        state=Match.COMPLETED,
        winner_id=winner.id,
        loser_id=loser.id,
        participant1_score=winner_score,
        participant2_score=loser_score,
    )


def _seed_rewards_fixture():
    organizer = _user('rewards_org')
    game = _game()
    tournament = _tournament(organizer, game)
    winner_user = _user('winner')
    runner_user = _user('runner')
    winner = _registration(tournament, winner_user)
    runner = _registration(tournament, runner_user)

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 50000,
        'coin_pool': 10000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 35000, 'coins': 7000},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 15000, 'coins': 3000},
        ],
        'special_awards': [{
            'id': 'mvp',
            'title': 'Tournament MVP',
            'description': 'Best overall performance',
            'type': 'cash',
            'icon': 'medal',
            'fiat': 2000,
            'coins': 500,
            'recipient_id': winner.id,
            'recipient_name': 'Winner Alias',
            'reward_text': 'MVP bonus',
        }],
        'certificates_enabled': True,
    }, actor=organizer)

    TournamentResult.objects.create(
        tournament=tournament,
        winner=winner,
        runner_up=runner,
        determination_method='normal',
        final_standings=[
            {
                'placement': 1,
                'registration_id': winner.id,
                'team_name': winner.user.username,
                'source': 'test',
            },
            {
                'placement': 2,
                'registration_id': runner.id,
                'team_name': runner.user.username,
                'source': 'test',
            },
        ],
    )

    transaction = PrizeTransaction.objects.create(
        tournament=tournament,
        participant=winner,
        placement=PrizeTransaction.Placement.FIRST,
        amount=Decimal('7000.00'),
        status=PrizeTransaction.Status.PENDING,
    )
    claim = PrizeClaim.objects.create(
        prize_transaction=transaction,
        claimed_by=winner_user,
        payout_method=PrizeClaim.PAYOUT_BKASH,
        payout_destination='01700000000',
        admin_notes='internal review note',
    )
    certificate = Certificate.objects.create(
        tournament=tournament,
        participant=winner,
        certificate_type=Certificate.WINNER,
        placement='1st',
        certificate_hash='a' * 64,
    )
    return tournament, organizer, winner, runner, claim, certificate


pytestmark = pytest.mark.django_db


def test_public_payload_excludes_admin_and_claim_fields():
    tournament, _, _, _, _, _ = _seed_rewards_fixture()

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert payload['surface'] == 'public'
    assert payload['placements'][0]['winner']['team_name'] == 'winner'
    assert 'registration_id' not in payload['placements'][0]['winner']
    assert 'registration_id' not in payload['standings'][0]
    assert 'registration_id' not in payload['top4'][0]
    assert 'recipient_id' not in payload['special_awards'][0]
    assert 'claim' not in payload['standings'][0]
    assert 'payout_destination' not in str(payload)
    assert 'internal review note' not in str(payload)


def test_hub_payload_includes_current_participant_claim_and_certificate():
    tournament, _, winner, _, claim, certificate = _seed_rewards_fixture()

    payload = TournamentRewardsReadModel.hub_payload(
        tournament,
        user=winner.user,
        registration=winner,
    )

    assert payload['surface'] == 'hub'
    assert payload['your_result']['rank'] == 1
    assert payload['your_result']['claim']['status'] == claim.status
    assert any(
        badge['title'] == 'Champion'
        for badge in payload['your_result']['achievement_badges']
    )
    assert payload['your_prizes'][0]['claim_status'] == claim.status
    assert payload['certificate']['id'] == certificate.id
    assert payload['certificate']['download_url'].endswith(f'/{certificate.id}/?format=pdf')


def test_toc_payload_includes_operations_fields():
    tournament, organizer, _, _, claim, certificate = _seed_rewards_fixture()

    payload = TournamentRewardsReadModel.toc_payload(tournament, user=organizer)
    first = payload['operations']['placements'][0]

    assert payload['surface'] == 'toc'
    assert payload['capabilities']['can_manage_payouts'] is True
    assert first['claim']['id'] == claim.id
    assert first['claim']['payout_destination'] == '01700000000'
    assert first['payout']['transaction_id'] == claim.prize_transaction_id
    assert first['certificate']['id'] == certificate.id
    assert first['contact']['enabled'] is False


def test_live_tournament_with_result_reads_as_completed_without_writing_standings():
    organizer = _user('live_result_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='live-result-rewards-cup',
        status=Tournament.LIVE,
    )
    winner = _registration(tournament, _user('live_winner'))
    runner = _registration(tournament, _user('live_runner'))

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 10000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 7000, 'coins': 700},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 3000, 'coins': 300},
        ],
        'special_awards': [],
    }, actor=organizer)

    result = TournamentResult.objects.create(
        tournament=tournament,
        winner=winner,
        runner_up=runner,
        determination_method='normal',
        final_standings=[],
    )

    public_payload = TournamentRewardsReadModel.public_payload(tournament)
    toc_payload = TournamentRewardsReadModel.toc_payload(tournament, user=organizer)

    assert public_payload['result_status']['completed'] is True
    assert public_payload['result_status']['tournament_status'] == Tournament.COMPLETED
    assert public_payload['result_status']['message'] != 'Tournament not completed yet.'
    assert public_payload['placements'][0]['winner']['team_name'] == 'live_winner'
    assert public_payload['achievements'][0]['title'] == 'Champion'
    assert toc_payload['operations']['status']['completed'] is True
    assert toc_payload['operations']['placements'][0]['team_name'] == 'live_winner'

    result.refresh_from_db()
    assert result.final_standings == []


def test_completed_tournament_without_result_derives_rewards_from_final_bracket():
    organizer = _user('bracket_result_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='bracket-result-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('rkrashik'))
    runner_up = _registration(tournament, _user('Tower_Tareq'))
    semi_loser_one = _registration(tournament, _user('Semi_Loser_One'))
    semi_loser_two = _registration(tournament, _user('Semi_Loser_Two'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=semi_loser_one,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=2,
        winner=runner_up,
        loser=semi_loser_two,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
        winner_score=2,
        loser_score=1,
    )

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 10000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 7000, 'coins': 700},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 3000, 'coins': 300},
        ],
        'special_awards': [],
    }, actor=organizer)

    assert TournamentResult.objects.filter(tournament=tournament).count() == 0

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert payload['result_status']['results_available'] is True
    assert payload['result_status']['message'] != (
        'Tournament completed. Final result is not available yet.'
    )
    assert payload['standings'][0]['team_name'] == 'rkrashik'
    assert payload['standings'][1]['team_name'] == 'Tower_Tareq'
    assert payload['placements'][0]['winner']['team_name'] == 'rkrashik'
    assert payload['placements'][1]['winner']['team_name'] == 'Tower_Tareq'


def test_no_bronze_match_blocks_rank_three_without_fake_winner():
    organizer = _user('no_bronze_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='no-bronze-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('rkrashik'))
    runner_up = _registration(tournament, _user('Tower_Tareq'))
    semi_loser_one = _registration(tournament, _user('Mastaan'))
    semi_loser_two = _registration(tournament, _user('Pistol_Pappu'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
        bracket_structure={'format': 'single-elimination'},
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=semi_loser_one,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=2,
        winner=runner_up,
        loser=semi_loser_two,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
    )

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 20000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 50, 'fiat': 10000, 'coins': 500},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 6000, 'coins': 300},
            {'rank': 3, 'title': 'Third Place', 'percent': 15, 'fiat': 3000, 'coins': 150},
            {'rank': 4, 'title': 'Fourth Place', 'percent': 5, 'fiat': 1000, 'coins': 50},
        ],
        'special_awards': [],
    }, actor=organizer)

    public_payload = TournamentRewardsReadModel.public_payload(tournament)
    toc_payload = TournamentRewardsReadModel.toc_payload(tournament, user=organizer)
    rank3 = next(row for row in public_payload['placements'] if row['rank'] == 3)
    op_rank3 = next(row for row in toc_payload['operations']['placements'] if row['rank'] == 3)

    assert [row['team_name'] for row in public_payload['standings']] == ['rkrashik', 'Tower_Tareq']
    assert rank3['winner'] is None
    assert rank3['result_label'] == 'Semi-finalist / placement unresolved'
    assert rank3['payout_blocked'] is True
    assert rank3['block_reason'] == 'No bronze match configured, 3rd place cannot be assigned.'
    assert op_rank3['payout']['status'] == 'blocked'


def test_completed_bronze_match_supplies_rank_three_and_four():
    organizer = _user('bronze_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='bronze-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('rkrashik'))
    runner_up = _registration(tournament, _user('Tower_Tareq'))
    bronze_winner = _registration(tournament, _user('Mastaan'))
    bronze_loser = _registration(tournament, _user('Pistol_Pappu'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=4,
        bracket_structure={
            'format': 'single-elimination',
            'third_place_match_enabled': True,
            'bronze_match_enabled': True,
        },
    )
    _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
    )
    bronze_match = _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=2,
        winner=bronze_winner,
        loser=bronze_loser,
    )
    BracketNode.objects.create(
        bracket=bracket,
        position=4,
        round_number=2,
        match_number_in_round=2,
        match=bronze_match,
        participant1_id=bronze_winner.id,
        participant1_name=bronze_winner.user.username,
        participant2_id=bronze_loser.id,
        participant2_name=bronze_loser.user.username,
        winner_id=bronze_winner.id,
        bracket_type=BracketNode.THIRD_PLACE,
    )
    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 20000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 50, 'fiat': 10000, 'coins': 500},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 6000, 'coins': 300},
            {'rank': 3, 'title': 'Third Place', 'percent': 15, 'fiat': 3000, 'coins': 150},
            {'rank': 4, 'title': 'Fourth Place', 'percent': 5, 'fiat': 1000, 'coins': 50},
        ],
        'special_awards': [],
    }, actor=organizer)

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert [row['team_name'] for row in payload['standings'][:4]] == [
        'rkrashik',
        'Tower_Tareq',
        'Mastaan',
        'Pistol_Pappu',
    ]
    assert payload['placements'][2]['winner']['team_name'] == 'Mastaan'
    assert payload['placements'][3]['winner']['team_name'] == 'Pistol_Pappu'


def test_repair_creates_bronze_match_from_semifinal_losers():
    organizer = _user('repair_bronze_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='efootball-genesis-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('rkrashik'))
    runner_up = _registration(tournament, _user('Tower_Tareq'))
    mastaan = _registration(tournament, _user('Mastaan'))
    pistol = _registration(tournament, _user('Pistol_Pappu'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
        bracket_structure={'format': 'single-elimination'},
    )
    sf1 = _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=mastaan,
    )
    sf2 = _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=2,
        winner=runner_up,
        loser=pistol,
    )
    final = _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
    )
    sf1_node = BracketNode.objects.create(
        bracket=bracket,
        position=1,
        round_number=1,
        match_number_in_round=1,
        match=sf1,
        participant1_id=champion.id,
        participant1_name=champion.user.username,
        participant2_id=mastaan.id,
        participant2_name=mastaan.user.username,
        winner_id=champion.id,
    )
    sf2_node = BracketNode.objects.create(
        bracket=bracket,
        position=2,
        round_number=1,
        match_number_in_round=2,
        match=sf2,
        participant1_id=runner_up.id,
        participant1_name=runner_up.user.username,
        participant2_id=pistol.id,
        participant2_name=pistol.user.username,
        winner_id=runner_up.id,
    )
    final_node = BracketNode.objects.create(
        bracket=bracket,
        position=3,
        round_number=2,
        match_number_in_round=1,
        match=final,
        participant1_id=champion.id,
        participant1_name=champion.user.username,
        participant2_id=runner_up.id,
        participant2_name=runner_up.user.username,
        winner_id=champion.id,
        child1_node=sf1_node,
        child2_node=sf2_node,
    )
    sf1_node.parent_node = final_node
    sf1_node.parent_slot = 1
    sf1_node.save(update_fields=['parent_node', 'parent_slot'])
    sf2_node.parent_node = final_node
    sf2_node.parent_slot = 2
    sf2_node.save(update_fields=['parent_node', 'parent_slot'])

    bronze_match = BracketService.create_bronze_match_from_semifinal_losers(
        tournament.id,
        actor=organizer,
    )
    bronze_node = BracketNode.objects.get(match=bronze_match)

    assert bronze_node.bracket_type == BracketNode.THIRD_PLACE
    assert {bronze_match.participant1_name, bronze_match.participant2_name} == {
        'Mastaan',
        'Pistol_Pappu',
    }
    assert TournamentResult.objects.filter(tournament=tournament).count() == 0


def test_empty_result_standings_use_final_bracket_runner_up():
    organizer = _user('partial_result_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='partial-result-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('partial_rkrashik'))
    runner_up = _registration(tournament, _user('partial_Tower_Tareq'))
    semi_loser_one = _registration(tournament, _user('partial_semis_one'))
    semi_loser_two = _registration(tournament, _user('partial_semis_two'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=semi_loser_one,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=2,
        winner=runner_up,
        loser=semi_loser_two,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
        winner_score=2,
        loser_score=1,
    )
    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 10000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 7000, 'coins': 700},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 3000, 'coins': 300},
        ],
        'special_awards': [],
    }, actor=organizer)
    TournamentResult.objects.create(
        tournament=tournament,
        winner=champion,
        final_bracket=bracket,
        final_standings=[],
    )

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert payload['result_status']['results_available'] is True
    assert payload['standings'][0]['team_name'] == 'partial_rkrashik'
    assert payload['standings'][1]['team_name'] == 'partial_Tower_Tareq'


def test_team_match_ids_resolve_to_registration_winners():
    organizer = _user('team_result_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='team-result-rewards-cup',
        status=Tournament.COMPLETED,
        participation_type=Tournament.TEAM,
    )
    champion_team = _team('rkrashik', organizer, game)
    runner_team = _team('Tower_Tareq', organizer, game)
    semi_team_one = _team('Semi Team One', organizer, game)
    semi_team_two = _team('Semi Team Two', organizer, game)
    filler_team = _team('Filler Team', organizer, game)
    _team_registration(tournament, filler_team)
    champion = _team_registration(tournament, champion_team)
    runner_up = _team_registration(tournament, runner_team)
    semi_loser_one = _team_registration(tournament, semi_team_one)
    semi_loser_two = _team_registration(tournament, semi_team_two)
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
    )
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=champion_team.id,
        participant1_name=champion_team.name,
        participant2_id=semi_team_one.id,
        participant2_name=semi_team_one.name,
        state=Match.COMPLETED,
        winner_id=champion_team.id,
        loser_id=semi_team_one.id,
        participant1_score=2,
        participant2_score=0,
    )
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        participant1_id=runner_team.id,
        participant1_name=runner_team.name,
        participant2_id=semi_team_two.id,
        participant2_name=semi_team_two.name,
        state=Match.COMPLETED,
        winner_id=runner_team.id,
        loser_id=semi_team_two.id,
        participant1_score=2,
        participant2_score=0,
    )
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=2,
        match_number=1,
        participant1_id=runner_team.id,
        participant1_name=runner_team.name,
        participant2_id=champion_team.id,
        participant2_name=champion_team.name,
        state=Match.COMPLETED,
        winner_id=champion_team.id,
        loser_id=runner_team.id,
        participant1_score=1,
        participant2_score=2,
    )
    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 10000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 7000, 'coins': 700},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 3000, 'coins': 300},
        ],
        'special_awards': [],
    }, actor=organizer)

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert payload['placements'][0]['winner']['team_name'] == 'rkrashik'
    assert payload['placements'][1]['winner']['team_name'] == 'Tower_Tareq'
    assert payload['standings'][0]['team_name'] == 'rkrashik'
    assert payload['standings'][1]['team_name'] == 'Tower_Tareq'


def test_completed_public_prize_api_bypasses_stale_pending_cache():
    organizer = _user('cache_result_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='cache-result-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('cache_rkrashik'))
    runner_up = _registration(tournament, _user('cache_Tower_Tareq'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=1,
        total_matches=1,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=runner_up,
        winner_score=2,
        loser_score=1,
    )
    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 10000,
        'coin_pool': 1000,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 7000, 'coins': 700},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 3000, 'coins': 300},
        ],
        'special_awards': [],
    }, actor=organizer)
    cache.set(f'public_prize_overview_v2_{tournament.id}', {
        'placements': [
            {'rank': 1, 'winner': None},
            {'rank': 2, 'winner': None},
        ],
        'result_status': {
            'completed': True,
            'message': 'Tournament completed. Final result is not available yet.',
        },
    }, timeout=30)

    request = RequestFactory().get(f'/tournaments/{tournament.slug}/api/prizes/')
    response = tournament_prize_overview(request, tournament.slug)
    payload = json.loads(response.content.decode('utf-8'))

    assert response['Cache-Control'] == 'no-store, max-age=0'
    assert payload['placements'][0]['winner']['team_name'] == 'cache_rkrashik'
    assert payload['placements'][1]['winner']['team_name'] == 'cache_Tower_Tareq'
    assert payload['result_status']['message'] != (
        'Tournament completed. Final result is not available yet.'
    )


def test_post_finalization_backfills_result_from_final_bracket():
    organizer = _user('bracket_backfill_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='bracket-backfill-rewards-cup',
        status=Tournament.COMPLETED,
    )
    champion = _registration(tournament, _user('backfill_rkrashik'))
    runner_up = _registration(tournament, _user('backfill_Tower_Tareq'))
    semi_loser_one = _registration(tournament, _user('backfill_semis_one'))
    semi_loser_two = _registration(tournament, _user('backfill_semis_two'))
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=1,
        winner=champion,
        loser=semi_loser_one,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=1,
        match_number=2,
        winner=runner_up,
        loser=semi_loser_two,
    )
    _completed_match(
        tournament,
        bracket,
        round_number=2,
        match_number=1,
        winner=champion,
        loser=runner_up,
        winner_score=2,
        loser_score=1,
    )
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=99,
        participant1_id=champion.id,
        participant1_name=champion.user.username,
        state=Match.SCHEDULED,
    )

    report = PostFinalizationService.run(tournament, actor=organizer)
    result = TournamentResult.objects.get(tournament=tournament)

    assert report.standings_count == 2
    assert result.winner == champion
    assert result.runner_up == runner_up
    assert result.final_standings[0]['team_name'] == 'backfill_rkrashik'
    assert result.final_standings[1]['team_name'] == 'backfill_Tower_Tareq'


def test_placement_achievements_fallback_when_special_awards_absent():
    organizer = _user('achievement_org')
    game = _game()
    tournament = _tournament(organizer, game, slug='achievement-rewards-cup')
    winner = _registration(tournament, _user('achievement_winner'))
    runner = _registration(tournament, _user('achievement_runner'))

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 5000,
        'coin_pool': 0,
        'placements': [
            {'rank': 1, 'title': 'Champion', 'percent': 70, 'fiat': 3500, 'coins': 0},
            {'rank': 2, 'title': 'Runner Up', 'percent': 30, 'fiat': 1500, 'coins': 0},
        ],
        'special_awards': [],
    }, actor=organizer)
    TournamentResult.objects.create(
        tournament=tournament,
        winner=winner,
        runner_up=runner,
        determination_method='normal',
        final_standings=[],
    )

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert [a['title'] for a in payload['achievements'][:2]] == [
        'Champion',
        'Runner-up',
    ]
    assert payload['achievements'][0]['recipient_name'] == 'achievement_winner'
    assert 'recipient_id' not in payload['achievements'][0]


def test_special_awards_persist_recipient_name_and_id():
    out = PrizeConfigService._normalize_for_write({
        'special_awards': [{
            'title': 'Golden Boot',
            'recipient_name': 'Final Boss FC',
            'recipient_id': '42',
        }],
    })

    award = out['special_awards'][0]
    assert award['recipient_name'] == 'Final Boss FC'
    assert award['recipient_id'] == 42


def test_special_awards_save_load_and_render_assignment_state():
    organizer = _user('special_award_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='special-awards-rewards-cup',
        status=Tournament.COMPLETED,
    )

    PrizeConfigService.save_config(tournament, {
        'currency': 'BDT',
        'fiat_pool': 0,
        'coin_pool': 0,
        'placements': [],
        'special_awards': [
            {
                'id': 'mvp',
                'title': 'MVP',
                'description': 'Best player',
                'type': 'cash',
                'icon': 'medal',
                'fiat': 1000,
                'coins': 100,
                'reward_text': 'Bonus',
                'recipient_id': '42',
                'recipient_name': 'Mastaan',
            },
            {
                'id': 'fair-play',
                'title': 'Fair Play',
                'description': 'Cleanest run',
                'type': 'digital',
                'icon': 'award',
                'fiat': 0,
                'coins': 50,
            },
        ],
    }, actor=organizer)

    config = PrizeConfigService.get_config(tournament)
    public_payload = TournamentRewardsReadModel.public_payload(tournament)
    toc_payload = TournamentRewardsReadModel.toc_payload(tournament, user=organizer)

    assert config['special_awards'][0]['recipient_id'] == 42
    assert config['special_awards'][0]['recipient_name'] == 'Mastaan'
    assert config['special_awards'][1]['awaiting_recipient'] is True
    assert public_payload['special_awards'][0]['recipient_name'] == 'Mastaan'
    assert public_payload['special_awards'][1]['recipient_name'] == 'Awaiting assignment'
    assert public_payload['special_awards'][1]['awaiting_recipient'] is True
    assert 'recipient_id' not in public_payload['special_awards'][0]
    assert toc_payload['operations']['special_awards'][0]['recipient_id'] == 42


def test_empty_states_do_not_crash_for_uncompleted_tournament():
    organizer = _user('empty_org')
    game = _game()
    tournament = _tournament(
        organizer,
        game,
        slug='empty-rewards-cup',
        status=Tournament.LIVE,
    )
    tournament.prize_pool = Decimal('0')
    tournament.prize_deltacoin = 0
    tournament.config = {}
    tournament.save(update_fields=['prize_pool', 'prize_deltacoin', 'config'])

    payload = TournamentRewardsReadModel.public_payload(tournament)

    assert payload['result_status']['completed'] is False
    assert payload['empty_states']['not_completed'] is True
    assert payload['empty_states']['no_prize_configured'] is True
    assert payload['standings'] == []
