"""
Pro Loadout API — save/get UserLoadoutProfile + LoadoutDevice + GameLoadoutSetting.
All endpoints require authentication and owner-only access.
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_pro_loadout(user):
    from apps.user_profile.models.pro_loadout import UserLoadoutProfile
    profile = user.profile
    loadout, _ = UserLoadoutProfile.objects.get_or_create(user_profile=profile)
    return loadout


def _serialize_device(d):
    return {
        'id': d.id,
        'category': d.category,
        'category_display': d.get_category_display(),
        'brand': d.brand,
        'model_name': d.model_name,
        'notes': d.notes,
        'is_featured': d.is_featured,
        'order': d.order,
    }


def _serialize_game_setting(gs):
    return {
        'id': gs.id,
        'game_id': gs.game_id,
        'game_slug': gs.game.slug,
        'game_name': gs.game.display_name,
        'platform': gs.platform,
        'mouse_dpi': gs.mouse_dpi,
        'in_game_sensitivity': str(gs.in_game_sensitivity) if gs.in_game_sensitivity is not None else '',
        'scoped_sensitivity': str(gs.scoped_sensitivity) if gs.scoped_sensitivity is not None else '',
        'ads_sensitivity': str(gs.ads_sensitivity) if gs.ads_sensitivity is not None else '',
        'crosshair_code': gs.crosshair_code,
        'resolution': gs.resolution,
        'refresh_rate': gs.refresh_rate,
        'fps_cap': gs.fps_cap,
        'graphics_quality': gs.graphics_quality,
        'gyro_enabled': gs.gyro_enabled,
        'gyro_sensitivity': str(gs.gyro_sensitivity) if gs.gyro_sensitivity is not None else '',
        'hud_code': gs.hud_code,
        'claw_style': gs.claw_style,
        'controller_model': gs.controller_model,
        'horizontal_sensitivity': gs.horizontal_sensitivity,
        'vertical_sensitivity': gs.vertical_sensitivity,
        'deadzone_left': str(gs.deadzone_left) if gs.deadzone_left is not None else '',
        'deadzone_right': str(gs.deadzone_right) if gs.deadzone_right is not None else '',
        'aim_assist': gs.aim_assist,
        'notes': gs.notes,
        'visibility': gs.visibility,
        'edpi': gs.edpi,
    }


# ── GET loadout ───────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def pro_loadout_get(request):
    from apps.user_profile.models.pro_loadout import UserLoadoutProfile, LoadoutDevice, GameLoadoutSetting
    loadout = _get_or_create_pro_loadout(request.user)
    devices = list(LoadoutDevice.objects.filter(loadout=loadout).order_by('order', 'category'))
    game_settings = list(GameLoadoutSetting.objects.filter(loadout=loadout).select_related('game').order_by('game__name', 'platform'))
    return JsonResponse({
        'success': True,
        'loadout': {
            'id': loadout.id,
            'primary_platform': loadout.primary_platform,
            'visibility': loadout.visibility,
        },
        'devices': [_serialize_device(d) for d in devices],
        'game_settings': [_serialize_game_setting(gs) for gs in game_settings],
    })


# ── Save loadout profile ──────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def pro_loadout_save(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = request.POST.dict()

    loadout = _get_or_create_pro_loadout(request.user)
    platform = body.get('primary_platform', '').upper()
    if platform in ('PC', 'MOBILE', 'CONSOLE', 'HYBRID'):
        loadout.primary_platform = platform
    visibility = body.get('visibility', '').upper()
    if visibility in ('PUBLIC', 'PRIVATE'):
        loadout.visibility = visibility
    loadout.save()

    # Also sync back to HardwareLoadout for backward compat
    _sync_to_hardware_loadout(request.user)

    return JsonResponse({'success': True, 'loadout_id': loadout.id})


# ── Device CRUD ───────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def device_save(request):
    from apps.user_profile.models.pro_loadout import LoadoutDevice
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    loadout = _get_or_create_pro_loadout(request.user)
    device_id = body.get('id')

    valid_categories = [c.value for c in LoadoutDevice.Category]
    category = body.get('category', '').upper()
    if category not in valid_categories:
        return JsonResponse({'success': False, 'error': 'Invalid category'}, status=400)

    if device_id:
        try:
            device = LoadoutDevice.objects.get(id=device_id, loadout=loadout)
        except LoadoutDevice.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Device not found'}, status=404)
    else:
        device = LoadoutDevice(loadout=loadout)

    device.category    = category
    device.brand       = str(body.get('brand', ''))[:100]
    device.model_name  = str(body.get('model_name', ''))[:200]
    device.notes       = str(body.get('notes', ''))[:300]
    device.is_featured = bool(body.get('is_featured', False))
    device.order       = int(body.get('order', 0))
    device.save()

    # Sync simple brands back to HardwareLoadout
    _sync_to_hardware_loadout(request.user)

    return JsonResponse({'success': True, 'device': _serialize_device(device)})


@login_required
@require_http_methods(['POST'])
def device_delete(request, device_id):
    from apps.user_profile.models.pro_loadout import LoadoutDevice
    loadout = _get_or_create_pro_loadout(request.user)
    try:
        LoadoutDevice.objects.filter(id=device_id, loadout=loadout).delete()
        _sync_to_hardware_loadout(request.user)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ── GameLoadoutSetting CRUD ───────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def game_setting_save(request):
    from apps.user_profile.models.pro_loadout import GameLoadoutSetting
    from apps.games.models.game import Game
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    loadout = _get_or_create_pro_loadout(request.user)

    game_id = body.get('game_id')
    try:
        game = Game.objects.get(id=game_id, is_active=True)
    except Game.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Game not found'}, status=404)

    platform = body.get('platform', 'PC').upper()
    if platform not in ('PC', 'MOBILE', 'CONSOLE'):
        platform = 'PC'

    gs, _ = GameLoadoutSetting.objects.get_or_create(
        loadout=loadout, game=game, platform=platform
    )

    def _int_or_none(val):
        try: return int(val) if val not in (None, '') else None
        except Exception: return None

    def _dec_or_none(val):
        try: return float(val) if val not in (None, '') else None
        except Exception: return None

    gs.mouse_dpi             = _int_or_none(body.get('mouse_dpi'))
    gs.in_game_sensitivity   = _dec_or_none(body.get('in_game_sensitivity'))
    gs.scoped_sensitivity    = _dec_or_none(body.get('scoped_sensitivity'))
    gs.ads_sensitivity       = _dec_or_none(body.get('ads_sensitivity'))
    gs.crosshair_code        = str(body.get('crosshair_code', ''))[:200]
    gs.resolution            = str(body.get('resolution', ''))[:20]
    gs.refresh_rate          = _int_or_none(body.get('refresh_rate'))
    gs.fps_cap               = _int_or_none(body.get('fps_cap'))
    gs.graphics_quality      = str(body.get('graphics_quality', ''))[:50]
    gs.gyro_enabled          = None if body.get('gyro_enabled') is None else bool(body.get('gyro_enabled'))
    gs.gyro_sensitivity      = _dec_or_none(body.get('gyro_sensitivity'))
    gs.hud_code              = str(body.get('hud_code', ''))[:200]
    gs.claw_style            = str(body.get('claw_style', ''))[:50]
    gs.controller_model      = str(body.get('controller_model', ''))[:100]
    gs.horizontal_sensitivity = _int_or_none(body.get('horizontal_sensitivity'))
    gs.vertical_sensitivity  = _int_or_none(body.get('vertical_sensitivity'))
    gs.deadzone_left         = _dec_or_none(body.get('deadzone_left'))
    gs.deadzone_right        = _dec_or_none(body.get('deadzone_right'))
    gs.aim_assist            = str(body.get('aim_assist', ''))[:50]
    gs.notes                 = str(body.get('notes', ''))[:500]
    vis = body.get('visibility', 'PUBLIC').upper()
    gs.visibility = vis if vis in ('PUBLIC', 'PRIVATE') else 'PUBLIC'
    gs.save()

    return JsonResponse({'success': True, 'game_setting': _serialize_game_setting(gs)})


@login_required
@require_http_methods(['POST'])
def game_setting_delete(request, setting_id):
    from apps.user_profile.models.pro_loadout import GameLoadoutSetting
    loadout = _get_or_create_pro_loadout(request.user)
    GameLoadoutSetting.objects.filter(id=setting_id, loadout=loadout).delete()
    return JsonResponse({'success': True})


# ── Backward compat: sync to HardwareLoadout ─────────────────────────────────

def _sync_to_hardware_loadout(user):
    """Keep HardwareLoadout in sync so old gear tab fallback still works."""
    try:
        from apps.user_profile.models.loadout import HardwareLoadout
        from apps.user_profile.models.pro_loadout import LoadoutDevice, UserLoadoutProfile
        profile = user.profile
        pro = UserLoadoutProfile.objects.filter(user_profile=profile).first()
        if not pro:
            return
        hl, _ = HardwareLoadout.objects.get_or_create(user_profile=profile)
        devices = {d.category: d for d in LoadoutDevice.objects.filter(loadout=pro)}
        if 'MOUSE' in devices:
            hl.mouse_brand = devices['MOUSE'].display_name[:100]
        if 'KEYBOARD' in devices:
            hl.keyboard_brand = devices['KEYBOARD'].display_name[:100]
        if 'HEADSET' in devices:
            hl.headset_brand = devices['HEADSET'].display_name[:100]
        if 'MONITOR' in devices:
            hl.monitor_brand = devices['MONITOR'].display_name[:100]
        hl.loadout_public = (pro.visibility == 'PUBLIC')
        hl.save(update_fields=['mouse_brand', 'keyboard_brand', 'headset_brand', 'monitor_brand', 'loadout_public', 'updated_at'])
    except Exception as e:
        logger.warning("_sync_to_hardware_loadout failed: %s", e)
