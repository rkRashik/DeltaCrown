import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.tournaments.api.toc.settings_service import TOCSettingsService
from apps.tournaments.models.form_configuration import TournamentFormConfiguration
from apps.tournaments.views.smart_registration import SmartRegistrationView


@pytest.mark.django_db
def test_update_form_configuration_coerces_string_booleans(game_factory, tournament_factory):
    game = game_factory(slug='valorant', name='Valorant', team_size=5)
    tournament = tournament_factory(game=game, participation_type='team')

    payload = {
        'enable_captain_phone_field': 'false',
        'enable_team_bio': 'true',
        'enable_payment_screenshot_field': '0',
        'communication_channels': [
            {'key': 'phone', 'label': 'Phone', 'required': 'true'},
            {'key': 'discord', 'label': 'Discord', 'required': 'false'},
        ],
    }

    TOCSettingsService.update_form_configuration(tournament, payload)

    cfg = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
    assert cfg.enable_captain_phone_field is False
    assert cfg.enable_team_bio is True
    assert cfg.enable_payment_screenshot_field is False
    assert cfg.communication_channels[0]['required'] is True
    assert cfg.communication_channels[1]['required'] is False


@pytest.mark.django_db
def test_smart_registration_context_shows_required_team_contact_channels(game_factory, tournament_factory):
    game = game_factory(slug='valorant', name='Valorant', team_size=5)
    tournament = tournament_factory(game=game, participation_type='team')

    cfg = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
    cfg.enable_captain_phone_field = False
    cfg.enable_captain_discord_field = False
    cfg.enable_captain_whatsapp_field = False
    cfg.communication_channels = [
        {
            'key': 'phone',
            'label': 'Phone',
            'placeholder': 'Your phone number',
            'icon': 'phone',
            'required': True,
            'type': 'tel',
        },
        {
            'key': 'discord',
            'label': 'Discord',
            'placeholder': 'username',
            'icon': 'discord',
            'required': False,
            'type': 'text',
        },
    ]
    cfg.save(update_fields=[
        'enable_captain_phone_field',
        'enable_captain_discord_field',
        'enable_captain_whatsapp_field',
        'communication_channels',
        'updated_at',
    ])

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username='smart_reg_contract_user',
        email='smart-reg-contract@example.com',
        password='pass1234',
    )

    request = RequestFactory().get('/')
    request.user = user

    view = SmartRegistrationView()
    view.request = request
    context = view._build_context(request, tournament, eligibility={'status': 'open'})

    visibility = context['contact_field_visibility']
    assert visibility['team_phone'] is True
    assert visibility['team_discord'] is True
    assert 'phone' in context['required_contact_channels']
