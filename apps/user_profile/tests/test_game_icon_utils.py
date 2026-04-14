import pytest

from apps.user_profile import utils


@pytest.fixture(autouse=True)
def auto_create_user_profiles():
    """Override DB-dependent autouse fixture from parent conftest."""
    yield


@pytest.fixture(autouse=True)
def clear_game_icon_cache():
    utils._resolve_game_icon_url.cache_clear()
    yield
    utils._resolve_game_icon_url.cache_clear()


def test_get_game_icon_url_uses_first_existing_candidate(monkeypatch):
    find_calls = []
    static_calls = []

    def fake_find(path):
        find_calls.append(path)
        if path == 'img/games/valorant.svg':
            return '/abs/static/img/games/valorant.svg'
        return None

    def fake_static(path):
        static_calls.append(path)
        return '/static/img/games/valorant.abcd1234.svg'

    monkeypatch.setattr(utils.finders, 'find', fake_find)
    monkeypatch.setattr(utils, 'static', fake_static)

    icon_url = utils.get_game_icon_url('valorant')

    assert icon_url == '/static/img/games/valorant.abcd1234.svg'
    assert find_calls[0] == 'user_profile/game_icons/valorant.svg'
    assert find_calls[1] == 'img/games/valorant.svg'
    assert static_calls == ['img/games/valorant.svg']


def test_get_game_icon_url_uses_default_icon_chain_when_primary_missing(monkeypatch):
    static_calls = []

    def fake_find(path):
        if path == 'img/game_logos/logos/default-game.svg':
            return '/abs/static/img/game_logos/logos/default-game.svg'
        return None

    def fake_static(path):
        static_calls.append(path)
        return '/static/img/game_logos/logos/default-game.12345678.svg'

    monkeypatch.setattr(utils.finders, 'find', fake_find)
    monkeypatch.setattr(utils, 'static', fake_static)

    icon_url = utils.get_game_icon_url('valorant')

    assert icon_url == '/static/img/game_logos/logos/default-game.12345678.svg'
    assert static_calls == ['img/game_logos/logos/default-game.svg']


def test_get_game_icon_url_uses_last_resort_when_no_assets_exist(monkeypatch, settings):
    settings.STATIC_URL = '/static/'
    static_calls = []

    def fake_find(_path):
        return None

    def fake_static(path):
        static_calls.append(path)
        return '/should/not/be/called'

    monkeypatch.setattr(utils.finders, 'find', fake_find)
    monkeypatch.setattr(utils, 'static', fake_static)

    icon_url = utils.get_game_icon_url('valorant')

    assert icon_url == '/static/img/teams/default-logo.svg'
    assert static_calls == []
