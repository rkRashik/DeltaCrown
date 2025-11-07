from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.http import JsonResponse



def homepage(request):
    # Lightweight context; safe with or without real data
    ctx = {
        "stats": {"teams": 0, "tournaments": 0, "players": 0},
        "tournaments": [],
    }
    return render(request, "homepage.html", ctx)



def home(request):
    """
    Public homepage.
    """
    # Try to pull dynamic stats/tournaments, but never crash
    tournaments_qs = None
    stats = {"teams": 0, "tournaments": 0, "players": 0}

    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            tournaments_qs = Tournament.objects.order_by("-created_at")[:6]
        except Exception:
            tournaments_qs = Tournament.objects.order_by("-id")[:6]
        stats["tournaments"] = Tournament.objects.count()
    except Exception:
        tournaments_qs = None

    try:
        from apps.teams.models import Team  # type: ignore
        stats["teams"] = Team.objects.count()
    except Exception:
        pass

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        stats["players"] = User.objects.count()
    except Exception:
        pass

    context = {
        "tournaments": tournaments_qs,
        "stats": stats,
    }
    return render(request, "homepage.html", context)


def healthz(request):
    """
    Lightweight health endpoint for uptime checks and load balancers.
    Returns HTTP 200 with a tiny JSON body.
    No authentication required.
    
    Phase 2: Module 2.4 - Security Hardening
    """
    return JsonResponse({"status": "ok"})


def readiness(request):
    """
    Readiness check endpoint with dependency validation.
    
    Checks:
        - Database connectivity
        - Redis connectivity (if configured)
        
    Returns HTTP 200 if all checks pass, HTTP 503 if any fail.
    
    Phase 2: Module 2.4 - Security Hardening
    """
    from django.db import connection
    from django.core.cache import cache
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    checks = {}
    all_passed = True
    
    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        all_passed = False
        logger.error(f"Database health check failed: {e}", exc_info=True)
    
    # Check Redis connectivity (if configured)
    if getattr(settings, 'USE_REDIS_CHANNELS', False):
        try:
            # Test Redis with a simple get/set
            cache.set('healthcheck_ping', 'pong', timeout=10)
            value = cache.get('healthcheck_ping')
            if value == 'pong':
                checks['redis'] = 'ok'
            else:
                checks['redis'] = 'error: Value mismatch'
                all_passed = False
        except Exception as e:
            checks['redis'] = f'error: {str(e)}'
            all_passed = False
            logger.error(f"Redis health check failed: {e}", exc_info=True)
    else:
        checks['redis'] = 'disabled'
    
    # Return appropriate status
    if all_passed:
        return JsonResponse({
            'status': 'ready',
            'checks': checks
        })
    else:
        return JsonResponse({
            'status': 'not_ready',
            'checks': checks,
            'error': 'One or more dependency checks failed'
        }, status=503)


def test_game_assets(request):
    """
    Test page for centralized game assets system.
    Shows all configured games and their logos/icons.
    """
    from apps.common.game_assets import GAMES
    return render(request, "test_game_assets.html", {"GAMES": GAMES})

# --------------- Tournaments: List & Detail (safe optional) ---------------

def tournaments_list(request):
    """
    List tournaments in a responsive grid.
    If Tournament model isn't available, renders placeholders.
    """
    qs = None
    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            qs = Tournament.objects.order_by("-created_at")
        except Exception:
            qs = Tournament.objects.order_by("-id")
    except Exception:
        qs = None

    return render(request, "tournaments/list.html", {"tournaments": qs})


def tournament_detail(request, pk: int):
    """
    Show a single tournament with hero, meta, rules, schedule, and CTA.
    Falls back to a placeholder page if model is unavailable or object missing.
    """
    tournament = None
    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            tournament = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:  # type: ignore
            raise Http404("Tournament not found")
    except Exception:
        # If the model itself is missing, we'll render a friendly placeholder
        tournament = None

    return render(request, "tournaments/detail.html", {"tournament": tournament})
