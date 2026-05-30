"""
Daily reward API endpoints.

GET  /api/daily-reward/status/   — check claimability + week schedule
POST /api/daily-reward/claim/    — claim today's reward
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


@login_required
@require_GET
def daily_reward_status(request):
    """Return current streak, claimability, and week schedule."""
    from apps.economy.services.daily_reward_service import DailyRewardService
    try:
        status = DailyRewardService.get_status(request.user)
        return JsonResponse({"ok": True, **status})
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("daily_reward_status error")
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)


@login_required
@require_POST
def daily_reward_claim(request):
    """Claim today's daily reward. Idempotent within a calendar day."""
    from apps.economy.services.daily_reward_service import (
        DailyRewardService, AlreadyClaimed, UserSuspended, NoWallet,
    )
    try:
        result = DailyRewardService.claim(request.user)
        return JsonResponse({"ok": True, **result})
    except AlreadyClaimed as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except UserSuspended as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=403)
    except NoWallet as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("daily_reward_claim error")
        return JsonResponse({"ok": False, "error": "Server error. Please try again."}, status=500)
