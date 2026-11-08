"""Mobile tournament UX regressions (OL-10A): login CTA, CSP nonce, bracket a11y, form labels.

Synthetic data on a disposable database; pages are rendered through the real views.
"""
import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Registration, Tournament

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def world(db):
    organizer = User.objects.create_user(username='mu-organizer', email='mu-org@example.test')
    players = [User.objects.create_user(username=f'mu-p{n}', email=f'mu-p{n}@example.test') for n in range(1, 5)]
    game = Game.objects.create(
        name='eFootball', slug='efootball', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now()
    common = dict(
        organizer=organizer, game=game, format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO, max_participants=4, min_participants=2,
    )
    open_cup = Tournament.objects.create(
        name='Mobile Open Cup', slug='mobile-open', status=Tournament.REGISTRATION_OPEN,
        registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=3),
        tournament_start=now + timedelta(days=4), tournament_end=now + timedelta(days=5), **common,
    )
    live_cup = Tournament.objects.create(
        name='Mobile Live Cup', slug='mobile-live', status=Tournament.LIVE,
        registration_start=now - timedelta(days=3), registration_end=now - timedelta(days=2),
        tournament_start=now - timedelta(hours=1), tournament_end=now + timedelta(days=1), **common,
    )
    for player in players:
        Registration.objects.create(
            tournament=live_cup, user=player, status=Registration.CONFIRMED,
            registration_data={'game_id': f'{player.username}-efootball'},
        )
    TOCBracketsService.generate_bracket(live_cup, organizer, {})
    return {'open': open_cup, 'live': live_cup, 'players': players}


def _get(path, user=None):
    client = Client()
    if user is not None:
        client.force_login(user)
    return client.get(path, secure=True)


def test_anonymous_visitor_gets_a_login_cta_while_registration_is_open(world):
    response = _get('/tournaments/mobile-open/')
    assert response.status_code == 200
    cta = response.context['detail_cta_primary']
    assert cta['label'] == 'Log in to register' and not cta['disabled']
    assert cta['url'].endswith('?next=/tournaments/mobile-open/register/')
    assert response.context['detail_cta_state'] == 'register'


def test_anonymous_cta_stays_closed_when_registration_is_not_open(world):
    response = _get('/tournaments/mobile-live/')
    cta = response.context['detail_cta_primary']
    assert cta['disabled'] and cta['label'] == 'Registration Closed'
    assert response.context['detail_cta_note'] == 'Registration is closed for this tournament.'


def test_registered_and_signed_in_viewers_keep_their_ctas(world):
    registered = _get('/tournaments/mobile-live/', world['players'][0]).context['detail_cta_primary']
    assert registered['kind'] == 'hub'
    outsider = User.objects.create_user(username='mu-outsider', email='mu-out@example.test')
    assert _get('/tournaments/mobile-open/', outsider).context['detail_cta_primary']['kind'] != 'login'


def test_mobile_detail_inline_script_carries_the_csp_nonce(world):
    html = _get('/tournaments/mobile-open/').content.decode()
    tags = [m for m in re.finditer(r'<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>', html, re.S)
            if 'tdm-tab-btn' in m.group('body')]
    assert tags, 'mobile tab/countdown script not rendered'
    assert all('nonce=' in m.group('attrs') for m in tags)


def test_bracket_is_keyboard_and_screen_reader_usable(world):
    html = _get('/tournaments/mobile-live/bracket/').content.decode()
    assert 'role="region"' in html and 'aria-label="Bracket, scrolls horizontally"' in html
    assert 'role="dialog" aria-modal="true"' in html
    assert html.count('role="button" tabindex="0"') >= 2  # both round-one cards are keyboard reachable
    assert 'buildRoundNav' in html  # phone round jump navigation
    assert 'activeMatch.score1 ??' not in html and 'activeMatch.score2 ??' not in html  # Alpine CSP build cannot parse `??`
    assert 'new Date(activeMatch' not in html


def test_registration_contact_inputs_are_labelled(world):
    html = _get('/tournaments/mobile-open/register/', world['players'][0]).content.decode()
    assert 'name="coordinator_email"' in html
    for name in ('coordinator_email', 'country'):
        assert f'for="solo-{name}"' in html and f'id="solo-{name}"' in html
