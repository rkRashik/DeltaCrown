# apps/user_profile/views/loadout_api.py
"""
Loadout API Endpoints - Interactive Owner Flows (Phase 2D)

Endpoints:
- POST /api/profile/loadout/hardware/ - Add/update hardware
- POST /api/profile/loadout/game-config/ - Add/update game config
- DELETE /api/profile/loadout/hardware/<id>/ - Remove hardware
- DELETE /api/profile/loadout/game-config/<id>/ - Remove game config
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
import json

from apps.user_profile.models import HardwareGear, GameConfig
from apps.core.models import Game


@login_required
@require_http_methods(["POST"])
def save_hardware(request):
    """
    Add or update hardware gear.
    
    POST /api/profile/loadout/hardware/
    
    Body (JSON):
    {
        "id": 123,  # Optional: if updating existing
        "category": "MOUSE",
        "brand": "Logitech",
        "model": "G Pro X Superlight",
        "specs": {"dpi": 800, "weight": "63g"},
        "is_public": true
    }
    
    Returns:
        200: {"success": true, "hardware_id": 123}
        400: {"error": "..."}
    """
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Extract fields
    hardware_id = data.get("id")
    category = data.get("category", "").upper()
    brand = data.get("brand", "").strip()
    model = data.get("model", "").strip()
    specs = data.get("specs", {})
    is_public = data.get("is_public", True)
    
    # Validate required fields
    if not category:
        return JsonResponse({"error": "Category is required"}, status=400)
    
    if category not in dict(HardwareGear.HardwareCategory.choices):
        return JsonResponse({"error": f"Invalid category: {category}"}, status=400)
    
    if not brand:
        return JsonResponse({"error": "Brand is required"}, status=400)
    
    if not model:
        return JsonResponse({"error": "Model is required"}, status=400)
    
    try:
        # Update existing or create new
        if hardware_id:
            # Validate ownership
            try:
                hardware = HardwareGear.objects.get(pk=hardware_id, user=request.user)
            except HardwareGear.DoesNotExist:
                return JsonResponse({"error": "Hardware not found or access denied"}, status=404)
            
            hardware.category = category
            hardware.brand = brand
            hardware.model = model
            hardware.specs = specs
            hardware.is_public = is_public
            hardware.save()
            
            message = "Hardware updated successfully"
        else:
            # Create new
            hardware = HardwareGear.objects.create(
                user=request.user,
                category=category,
                brand=brand,
                model=model,
                specs=specs,
                is_public=is_public,
            )
            
            message = "Hardware added successfully"
        
        return JsonResponse({
            "success": True,
            "hardware_id": hardware.id,
            "message": message,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Hardware save error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while saving hardware"}, status=500)


@login_required
@require_http_methods(["POST"])
def save_game_config(request):
    """
    Add or update game config.
    
    POST /api/profile/loadout/game-config/
    
    Body (JSON):
    {
        "id": 456,  # Optional: if updating existing
        "game_id": 1,
        "settings": {
            "dpi": 800,
            "sensitivity": 0.45,
            "resolution": "1920x1080",
            "crosshair_code": "0;P;c;5;o;1;..."
        },
        "notes": "Aggressive entry fragger setup",
        "is_public": true
    }
    
    Returns:
        200: {"success": true, "config_id": 456}
        400: {"error": "..."}
    """
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Extract fields
    config_id = data.get("id")
    game_id = data.get("game_id")
    settings = data.get("settings", {})
    notes = data.get("notes", "").strip()
    is_public = data.get("is_public", True)
    
    # Validate required fields
    if not game_id:
        return JsonResponse({"error": "Game is required"}, status=400)
    
    # Validate game exists
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status=400)
    
    try:
        # Update existing or create new
        if config_id:
            # Validate ownership
            try:
                config = GameConfig.objects.get(pk=config_id, user=request.user)
            except GameConfig.DoesNotExist:
                return JsonResponse({"error": "Config not found or access denied"}, status=404)
            
            config.game = game
            config.settings = settings
            config.notes = notes
            config.is_public = is_public
            config.save()
            
            message = "Config updated successfully"
        else:
            # Create new
            config = GameConfig.objects.create(
                user=request.user,
                game=game,
                settings=settings,
                notes=notes,
                is_public=is_public,
            )
            
            message = "Config added successfully"
        
        return JsonResponse({
            "success": True,
            "config_id": config.id,
            "message": message,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Game config save error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while saving config"}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])  # Support both DELETE and POST for compatibility
def delete_hardware(request, hardware_id):
    """
    Delete hardware gear.
    
    DELETE /api/profile/loadout/hardware/<id>/
    
    Returns:
        200: {"success": true}
        404: {"error": "Hardware not found"}
    """
    
    try:
        hardware = HardwareGear.objects.get(pk=hardware_id, user=request.user)
        hardware.delete()
        
        return JsonResponse({
            "success": True,
            "message": "Hardware deleted successfully",
        })
    
    except HardwareGear.DoesNotExist:
        return JsonResponse({"error": "Hardware not found or access denied"}, status=404)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Hardware delete error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while deleting hardware"}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])  # Support both DELETE and POST for compatibility
def delete_game_config(request, config_id):
    """
    Delete game config.
    
    DELETE /api/profile/loadout/game-config/<id>/
    
    Returns:
        200: {"success": true}
        404: {"error": "Config not found"}
    """
    
    try:
        config = GameConfig.objects.get(pk=config_id, user=request.user)
        config.delete()
        
        return JsonResponse({
            "success": True,
            "message": "Config deleted successfully",
        })
    
    except GameConfig.DoesNotExist:
        return JsonResponse({"error": "Config not found or access denied"}, status=404)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Game config delete error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while deleting config"}, status=500)
