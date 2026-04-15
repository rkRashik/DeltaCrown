import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Bracket, BracketNode, Game, Match, Registration, Tournament
from apps.tournaments.models.group import Group


User = get_user_model()


@pytest.fixture
def hub_game(db):
    return Game.objects.create(
        name='Hub API Game',
        slug='hub-api-game',
        is_active=True,
    )


@pytest.fixture
def hub_organizer(db):
    return User.objects.create_user(
        username='hub-organizer',
        email='hub-organizer@test.com',
        password='pass123',
    )


@pytest.fixture
def hub_player(db):
    return User.objects.create_user(
        username='hub-player',
        email='hub-player@test.com',
        password='pass123',
    )


@pytest.fixture
def hub_tournament(db, hub_game, hub_organizer):
    now = timezone.now()
    return Tournament.objects.create(
        name='Hub Group Stage Tournament',
        slug='hub-group-stage-tournament',
        organizer=hub_organizer,
        game=hub_game,
        format=Tournament.GROUP_PLAYOFF,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2),
        tournament_end=now + timedelta(days=4),
        status=Tournament.REGISTRATION_OPEN,
    )


@pytest.fixture
def hub_registration(db, hub_tournament, hub_player):
    return Registration.objects.create(
        tournament=hub_tournament,
        user=hub_player,
        status=Registration.CONFIRMED,
        registration_data={},
    )


@pytest.mark.django_db
def test_hub_bracket_api_groups_round_robin_matches_by_group(client, hub_tournament, hub_registration, hub_player):
    group_a = Group.objects.create(
        tournament=hub_tournament,
        name='Group A',
        display_order=0,
        max_participants=4,
        advancement_count=2,
    )
    group_b = Group.objects.create(
        tournament=hub_tournament,
        name='Group B',
        display_order=1,
        max_participants=4,
        advancement_count=2,
    )

    Match.objects.create(
        tournament=hub_tournament,
        round_number=1,
        match_number=1,
        participant1_id=101,
        participant1_name='Alpha',
        participant2_id=102,
        participant2_name='Bravo',
        state=Match.SCHEDULED,
        lobby_info={
            'group_id': group_a.id,
            'group_name': group_a.name,
            'group_label': group_a.name,
        },
    )
    Match.objects.create(
        tournament=hub_tournament,
        round_number=1,
        match_number=2,
        participant1_id=201,
        participant1_name='Charlie',
        participant2_id=202,
        participant2_name='Delta',
        state=Match.SCHEDULED,
        lobby_info={
            'group_id': group_b.id,
            'group_name': group_b.name,
            'group_label': group_b.name,
        },
    )

    client.force_login(hub_player)
    response = client.get(reverse('tournaments:hub_bracket_api', kwargs={'slug': hub_tournament.slug}))

    assert response.status_code == 200
    payload = response.json()

    assert payload['generated'] is True
    assert payload['generated_mode'] == 'group_stage'

    groups = payload.get('group_stage', {}).get('groups', [])
    assert [g.get('group_name') for g in groups] == ['Group A', 'Group B']
    assert groups[0]['rounds'][0]['matches'][0]['group_name'] == 'Group A'
    assert groups[1]['rounds'][0]['matches'][0]['group_name'] == 'Group B'

    flat_round_groups = {r.get('group_name') for r in payload.get('rounds', [])}
    assert flat_round_groups == {'Group A', 'Group B'}


@pytest.mark.django_db
def test_hub_bracket_api_exposes_projected_seeding_pairs_for_pending_group_playoff(
    client,
    hub_tournament,
    hub_registration,
    hub_player,
):
    Group.objects.create(
        tournament=hub_tournament,
        name='Group A',
        display_order=0,
        max_participants=4,
        advancement_count=2,
    )
    Group.objects.create(
        tournament=hub_tournament,
        name='Group B',
        display_order=1,
        max_participants=4,
        advancement_count=2,
    )

    client.force_login(hub_player)
    response = client.get(reverse('tournaments:hub_bracket_api', kwargs={'slug': hub_tournament.slug}))

    assert response.status_code == 200
    payload = response.json()
    assert payload['generated'] is False

    group_ctx = payload.get('group_context') or {}
    assert group_ctx.get('has_groups') is True
    assert group_ctx.get('projected_seeding_pairs') == [
        {'p1_label': 'A1', 'p2_label': 'B2'},
        {'p1_label': 'B1', 'p2_label': 'A2'},
    ]


@pytest.mark.django_db
def test_hub_bracket_api_enriches_future_placeholder_slots_from_bracket_nodes(
    client,
    hub_tournament,
    hub_registration,
    hub_player,
):
    bracket = Bracket.objects.create(
        tournament=hub_tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
        bracket_structure={
            'rounds': [
                {'round_number': 1, 'round_name': 'Semi Finals', 'matches': 2},
                {'round_number': 2, 'round_name': 'Finals', 'matches': 1},
            ]
        },
    )

    Match.objects.create(
        tournament=hub_tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=101,
        participant1_name='Alpha',
        participant2_id=102,
        participant2_name='Bravo',
        state=Match.SCHEDULED,
    )

    BracketNode.objects.create(
        bracket=bracket,
        position=3,
        round_number=2,
        match_number_in_round=1,
        participant1_id=101,
        participant1_name='Alpha',
        participant2_id=None,
        participant2_name='',
    )

    client.force_login(hub_player)
    response = client.get(reverse('tournaments:hub_bracket_api', kwargs={'slug': hub_tournament.slug}))

    assert response.status_code == 200
    payload = response.json()
    assert payload['generated'] is True
    assert payload['generated_mode'] == 'bracket'

    finals_round = next(r for r in payload['rounds'] if r['round_number'] == 2)
    finals_match = next(m for m in finals_round['matches'] if m['match_number'] == 1)

    assert finals_match['id'] is None
    assert finals_match['participant1']['id'] == 101
    assert finals_match['participant1']['name'] == 'Alpha'
    assert finals_match['participant2']['id'] is None
    assert finals_match['participant2']['name'] == 'TBD'
