"""
Games API endpoints for frontend
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.games.models import Game
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def games_list(request):
    """
    Get list of all active games.
    
    Returns:
        JSON: List of games with basic info
    """
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
            'icon': game.icon.url if game.icon else None,
            'logo': game.logo.url if game.logo else None,
        } for game in games]
        
        return JsonResponse(games_data, safe=False)
    
    except Exception as e:
        logger.error(f"Error fetching games list: {e}")
        return JsonResponse({
            'error': 'Failed to fetch games'
        }, status=500)


@require_http_methods(["GET"])
def game_identity_schema(request, game_id):
    """
    Get identity schema for a specific game.
    
    Returns JSON with required fields for game passport creation.
    """
    try:
        game = Game.objects.get(id=game_id, is_active=True)
        
        # Get identity configuration from GamePlayerIdentityConfig
        from apps.games.models import GamePlayerIdentityConfig
        identity_configs = GamePlayerIdentityConfig.objects.filter(
            game=game
        ).order_by('order')
        
        fields = []
        for config in identity_configs:
            field = {
                'field_name': config.field_name,  # Keep original field name
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
            }
            fields.append(field)
        
        # If no custom identity config, return default fields
        if not fields:
            fields = [
                {
                    'field_name': 'ign',
                    'label': 'In-Game Name (IGN)',
                    'type': 'text',
                    'required': True,
                    'immutable': False,
                    'placeholder': 'YourGameName',
                    'help_text': 'Your player name in the game',
                    'min_length': 3,
                    'max_length': 50,
                },
                {
                    'field_name': 'region',
                    'label': 'Region/Server',
                    'type': 'text',
                    'required': False,
                    'immutable': False,
                    'placeholder': 'NA, EU, Asia, etc.',
                    'help_text': 'Your game region or server',
                    'max_length': 20,
                },
                {
                    'field_name': 'rank',
                    'label': 'Rank/Tier',
                    'type': 'text',
                    'required': False,
                    'immutable': False,
                    'placeholder': 'e.g. Diamond, Master',
                    'help_text': 'Your current rank or tier (optional)',
                    'max_length': 50,
                }
            ]
        
        return JsonResponse({
            'game': {
                'id': game.id,
                'name': game.name,
                'display_name': game.display_name,
                'icon': game.icon.url if game.icon else None,
            },
            'fields': fields
        })
    
    except Game.DoesNotExist:
        return JsonResponse({
            'error': 'Game not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching game schema for game_id={game_id}: {e}")
        return JsonResponse({
            'error': 'Failed to fetch game schema'
        }, status=500)
