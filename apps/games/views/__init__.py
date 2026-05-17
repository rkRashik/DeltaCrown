"""
Games views package.

Public API views (games_list, game_identity_schema) live here so that
apps.games.views.games_list continues to resolve after the views/ package
was introduced alongside admin_maintenance.py.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.games.models import Game
from apps.common.media_urls import field_file_url
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def games_list(request):
    try:
        games = Game.objects.filter(is_active=True).order_by('name')
        games_data = [{
            'id': game.id,
            'name': game.name,
            'display_name': game.display_name,
            'slug': game.slug,
            'short_code': game.short_code,
            'category': game.category,
            'game_type': game.game_type,
            'platforms': game.platforms,
            'icon': field_file_url(game.icon) or None,
            'logo': field_file_url(game.logo) or None,
        } for game in games]
        return JsonResponse(games_data, safe=False)
    except Exception as e:
        logger.error("Error fetching games list: %s", e)
        return JsonResponse({'error': 'Failed to fetch games'}, status=500)


@require_http_methods(["GET"])
def game_identity_schema(request, game_id):
    try:
        game = Game.objects.get(id=game_id, is_active=True)
        from apps.games.models import GamePlayerIdentityConfig
        identity_configs = GamePlayerIdentityConfig.objects.filter(game=game).order_by('order')
        fields = [{
            'field_name': 'ign',
            'label': 'In-Game Name (IGN)',
            'type': 'text',
            'required': True,
            'immutable': False,
            'placeholder': 'YourGameName',
            'help_text': 'Your display name in the game',
            'min_length': 2,
            'max_length': 50,
        }]
        for config in identity_configs:
            fields.append({
                'field_name': config.field_name,
                'label': config.display_name,
                'type': config.field_type.lower(),
                'required': config.is_required,
                'immutable': config.is_immutable,
                'placeholder': config.placeholder,
                'help_text': config.help_text,
                'min_length': config.min_length,
                'max_length': config.max_length,
                'validation': config.validation_regex,
                'validation_error': config.validation_error_message,
            })
        optional_fields = []
        if game.platforms and len(game.platforms) > 1:
            optional_fields.append({
                'field_name': 'platform', 'label': 'Platform', 'type': 'select',
                'required': False,
                'choices': [{'value': p, 'label': p} for p in game.platforms],
                'help_text': 'Which platform do you play on?',
            })
        if game.has_servers and hasattr(game, 'roster_config') and game.roster_config and game.roster_config.has_regions:
            regions = game.roster_config.available_regions
            if regions:
                optional_fields.append({
                    'field_name': 'region', 'label': 'Region/Server', 'type': 'select',
                    'required': False,
                    'choices': [{'value': r.get('code', r.get('name', '')), 'label': r.get('name', r.get('code', ''))} for r in regions],
                    'help_text': 'Your game region or server',
                })
        if game.has_rank_system and game.available_ranks:
            optional_fields.append({
                'field_name': 'rank', 'label': 'Rank/Tier', 'type': 'select',
                'required': False, 'choices': game.available_ranks,
                'help_text': 'Your current rank or tier (optional)',
            })
        return JsonResponse({
            'game': {'id': game.id, 'name': game.name, 'display_name': game.display_name,
                     'icon': field_file_url(game.icon) or None},
            'fields': fields,
            'optional_fields': optional_fields,
        })
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    except Exception as e:
        logger.error("Error fetching game schema for game_id=%s: %s", game_id, e)
        return JsonResponse({'error': 'Failed to fetch game schema'}, status=500)
