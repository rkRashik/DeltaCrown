"""
Game Configuration API

Provides RESTful endpoints for retrieving game configurations,
fields, and roles for dynamic form generation.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from apps.tournaments.services import GameConfigService


@require_http_methods(["GET"])
@cache_page(60 * 60)  # Cache for 1 hour
def game_config_api(request, game_code):
    """
    Get complete configuration for a specific game.
    
    URL: /api/games/<game_code>/config/
    Method: GET
    
    Args:
        game_code: The game identifier (valorant, cs2, dota2, etc.)
        
    Returns:
        JSON with game info, fields, and roles
        
    Example Response:
        {
            "success": true,
            "game_code": "valorant",
            "config": {
                "game": {
                    "game_code": "valorant",
                    "display_name": "VALORANT",
                    "team_size": 5,
                    "sub_count": 2,
                    ...
                },
                "fields": [
                    {
                        "field_name": "riot_id",
                        "field_label": "Riot ID",
                        "field_type": "text",
                        "is_required": true,
                        ...
                    }
                ],
                "roles": [
                    {
                        "role_code": "duelist",
                        "role_name": "Duelist",
                        "is_unique": false,
                        ...
                    }
                ]
            }
        }
    """
    config = GameConfigService.get_full_config(game_code)
    
    if config is None:
        return JsonResponse({
            'success': False,
            'error': f"Game '{game_code}' not found or is inactive",
            'game_code': game_code
        }, status=404)
    
    return JsonResponse({
        'success': True,
        'game_code': game_code,
        'config': config
    })


@require_http_methods(["GET"])
@cache_page(60 * 60)  # Cache for 1 hour
def all_games_api(request):
    """
    Get list of all available games.
    
    URL: /api/games/
    Method: GET
    
    Query Parameters:
        include_inactive: Set to 'true' to include inactive games (default: false)
        
    Returns:
        JSON with list of games
        
    Example Response:
        {
            "success": true,
            "count": 8,
            "games": [
                {
                    "game_code": "valorant",
                    "display_name": "VALORANT",
                    "roster_description": "5 starters + 2 subs",
                    "is_solo": false,
                    "is_team": true
                },
                ...
            ]
        }
    """
    include_inactive = request.GET.get('include_inactive', 'false').lower() == 'true'
    games = GameConfigService.get_all_games(include_inactive=include_inactive)
    
    games_data = [GameConfigService._serialize_game(game) for game in games]
    
    return JsonResponse({
        'success': True,
        'count': len(games_data),
        'games': games_data
    })


@require_http_methods(["POST"])
def validate_field_api(request, game_code):
    """
    Validate a field value against game configuration.
    
    URL: /api/games/<game_code>/validate/
    Method: POST
    
    POST Data:
        {
            "field_name": "riot_id",
            "value": "Player#1234"
        }
        
    Returns:
        JSON with validation result
        
    Example Response:
        {
            "success": true,
            "field_name": "riot_id",
            "is_valid": true,
            "error": null
        }
    """
    import json
    
    try:
        data = json.loads(request.body)
        field_name = data.get('field_name')
        value = data.get('value')
        
        if not field_name:
            return JsonResponse({
                'success': False,
                'error': 'field_name is required'
            }, status=400)
        
        is_valid, error_message = GameConfigService.validate_field_value(
            game_code, field_name, value
        )
        
        return JsonResponse({
            'success': True,
            'field_name': field_name,
            'is_valid': is_valid,
            'error': error_message
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def validate_roles_api(request, game_code):
    """
    Validate team role assignments.
    
    URL: /api/games/<game_code>/validate-roles/
    Method: POST
    
    POST Data:
        {
            "roles": ["duelist", "controller", "initiator", "sentinel", "igl"]
        }
        
    Returns:
        JSON with validation result
        
    Example Response:
        {
            "success": true,
            "is_valid": true,
            "errors": []
        }
    """
    import json
    
    try:
        data = json.loads(request.body)
        roles = data.get('roles', [])
        
        if not isinstance(roles, list):
            return JsonResponse({
                'success': False,
                'error': 'roles must be an array'
            }, status=400)
        
        is_valid, errors = GameConfigService.validate_team_roles(game_code, roles)
        
        return JsonResponse({
            'success': True,
            'is_valid': is_valid,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
