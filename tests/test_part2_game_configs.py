# tests/test_part2_game_configs.py
import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament


@pytest.fixture
def admin_logged_client(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    client.login(username="admin", password="pass")
    return client


@pytest.mark.django_db
def test_valorant_tournament_autocreates_valorant_config():
    t = Tournament.objects.create(name="V-Cup", game="valorant")
    # signal should create related config
    assert hasattr(t, "valorant_config")
    t.refresh_from_db()
    assert t.valorant_config is not None
    # default map pool must be a non-empty list
    pool = t.valorant_config.map_pool
    assert isinstance(pool, list) and len(pool) > 0


@pytest.mark.django_db
def test_efootball_tournament_autocreates_efootball_config():
    t = Tournament.objects.create(name="E-Cup", game="efootball")
    assert hasattr(t, "efootball_config")
    t.refresh_from_db()
    assert t.efootball_config is not None
    assert t.efootball_config.match_duration_min > 0


@pytest.mark.django_db
def test_configs_are_mutually_exclusive():
    t = Tournament.objects.create(name="Mix-Cup", game="valorant")
    # creating eFootball config manually on a valorant tournament should fail validation
    from apps.game_efootball.models import EfootballConfig
    conf = EfootballConfig(tournament=t)
    with pytest.raises(ValidationError):
        conf.full_clean()  # triggers model.clean()


@pytest.mark.django_db
def test_admin_change_page_shows_for_valorant(admin_logged_client):
    t = Tournament.objects.create(name="Admin-V", game="valorant")
    url = reverse("admin:tournaments_tournament_change", args=[t.pk])
    r = admin_logged_client.get(url)
    assert r.status_code == 200


@pytest.mark.django_db
def test_admin_change_page_shows_for_efootball(admin_logged_client):
    t = Tournament.objects.create(name="Admin-E", game="efootball")
    url = reverse("admin:tournaments_tournament_change", args=[t.pk])
    r = admin_logged_client.get(url)
    assert r.status_code == 200
