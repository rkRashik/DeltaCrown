"""Worker-independent bracket advancement recovery (advance_pending_matches)."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.brackets.models import Bracket, BracketNode
from apps.games.models.game import Game
from apps.tournaments.models import Match, Tournament
from apps.tournaments.services.bracket_recovery import advance_pending_matches

pytestmark = pytest.mark.django_db


@pytest.fixture
def tree(db):
    cache.clear()
    organizer = get_user_model().objects.create_user(
        username='rec-org', email='rec-org@test.com', password='pass123'
    )
    game = Game.objects.create(
        name='Recovery Game', slug='recovery-game', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Recovery Cup', slug='recovery-cup', organizer=organizer, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now - timedelta(days=1),
        tournament_start=now - timedelta(hours=3), tournament_end=now + timedelta(days=1),
        status=Tournament.LIVE,
    )
    bracket = Bracket.objects.create(
        tournament=tournament, bracket_type=Bracket.SINGLE_ELIMINATION,
        seeding_method=Bracket.SLOT_ORDER, status=Bracket.ACTIVE,
    )
    final = BracketNode.objects.create(
        bracket=bracket, position=3, round_number=2, match_number_in_round=1, parent_slot=None
    )
    semis = []
    for n, (p1, p2) in enumerate([(1, 2), (3, 4)], start=1):
        match = Match.objects.create(
            tournament=tournament, round_number=1, match_number=n,
            participant1_id=p1, participant2_id=p2, state=Match.SCHEDULED,
        )
        node = BracketNode.objects.create(
            bracket=bracket, position=n, round_number=1, match_number_in_round=n,
            participant1_id=p1, participant1_name=f'P{p1}',
            participant2_id=p2, participant2_name=f'P{p2}',
            parent_node=final, parent_slot=n, match=match,
        )
        semis.append((match, node))
    return tournament, final, semis


def _finish(match, winner_id, age=timedelta(days=30)):
    """Complete without the post-save signal chain, as if the signal failed."""
    Match.objects.filter(pk=match.pk).update(
        state=Match.COMPLETED, winner_id=winner_id, loser_id=winner_id + 100,
        updated_at=timezone.now() - age,
    )


def test_worker_off_progression(tree):
    _, final, semis = tree
    _finish(semis[0][0], winner_id=1)

    assert advance_pending_matches()['advanced'] == 1

    final.refresh_from_db()
    semis[0][1].refresh_from_db()
    assert final.participant1_id == 1
    assert semis[0][1].winner_id == 1


def test_retry_after_failure(tree):
    _, final, semis = tree
    _finish(semis[0][0], winner_id=1)

    with patch(
        'apps.tournaments.services.bracket_service.BracketService.update_bracket_after_match',
        side_effect=RuntimeError('boom'),
    ):
        assert advance_pending_matches()['failed'] == 1
    semis[0][1].refresh_from_db()
    assert semis[0][1].winner_id is None  # still pending, nothing half-written

    assert advance_pending_matches()['advanced'] == 0  # backoff holds it back
    cache.clear()
    assert advance_pending_matches()['advanced'] == 1
    final.refresh_from_db()
    assert final.participant1_id == 1


def test_idempotent_and_no_duplicate_final_match(tree):
    tournament, final, semis = tree
    _finish(semis[0][0], winner_id=1)
    _finish(semis[1][0], winner_id=4)

    assert advance_pending_matches()['advanced'] == 2
    assert advance_pending_matches() == {'advanced': 0, 'skipped': 0, 'failed': 0}

    assert Match.objects.filter(tournament=tournament, round_number=2).count() == 1


def test_ignores_recent_invalid_and_non_live(tree):
    tournament, final, semis = tree
    _finish(semis[0][0], winner_id=1, age=timedelta(seconds=5))  # inside grace period
    _finish(semis[1][0], winner_id=99)  # winner is not a participant
    assert advance_pending_matches()['advanced'] == 0

    _finish(semis[0][0], winner_id=1)
    Tournament.objects.filter(pk=tournament.pk).update(status=Tournament.COMPLETED)
    assert advance_pending_matches()['advanced'] == 0
