# apps/tournaments/views/public.py
from __future__ import annotations

from typing import Dict, Tuple, Any, Optional

from django.apps import apps
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import (
    BooleanField,
    Case,
    Count,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.urls import reverse



# Prefer app-local imports; fall back to apps.get_model to survive refactors
try:
    from ..models import Tournament, Registration, PaymentVerification
except Exception:  # pragma: no cover
    Tournament = apps.get_model("tournaments", "Tournament")
    Registration = apps.get_model("tournaments", "Registration")
    PaymentVerification = apps.get_model("tournaments", "PaymentVerification")


# ---------------------------
# Helpers & constants
# ---------------------------

GAME_CHOICES: Tuple[Tuple[str, str], ...] = (
    ("valorant", "Valorant"),
    ("efootball", "eFootball"),
    ("pubg", "PUBG Mobile"),
    ("freefire", "Free Fire"),
    ("codm", "Call of Duty Mobile"),
    ("mlbb", "Mobile Legends"),
    ("csgo", "CS2/CS:GO"),
    ("fc26", "FC 26"),
)

STATUS_RANK = {"OPEN": 0, "UPCOMING": 1, "ONGOING": 2, "COMPLETED": 3}


def _now():
    return timezone.now()


def _tpl_exists(name: str) -> bool:
    try:
        get_template(name)
        return True
    except TemplateDoesNotExist:
        return False


def _get_profile(user):
    """Return UserProfile for accounts.User, or None (without creating)."""
    if not getattr(user, "is_authenticated", False):
        return None
    prof = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if prof:
        return prof
    try:
        UserProfile = apps.get_model("user_profile", "UserProfile")
        return UserProfile.objects.filter(user=user).first()
    except Exception:
        return None


def _registration_owner_filter_kwargs(user) -> Dict[str, object]:
    """
    Build the correct filter for Registration owner:
    - If model has `profile` FK â†’ use profile
    - Else if model has `user`:
        - If it's FK to UserProfile â†’ use profile
        - If it's FK to accounts.User â†’ use user
    - Else â†’ return empty (matches nothing)
    """
    profile = _get_profile(user)

    try:
        Registration._meta.get_field("profile")
        return {"profile": profile} if profile else {"id__in": []}
    except Exception:
        pass

    try:
        f = Registration._meta.get_field("user")
        remote = getattr(f, "remote_field", None)
        remote_model_name = getattr(getattr(remote, "model", None), "__name__", "")
        if remote_model_name in ("UserProfile", "Profile"):
            return {"user": profile} if profile else {"id__in": []}
        return {"user": user}
    except Exception:
        pass

    return {"id__in": []}


def _status_for(t: Tournament) -> str:
    now = _now()
    start_at = getattr(t, "start_at", None)
    end_at = getattr(t, "end_at", None)
    reg_open_at = getattr(t, "reg_open_at", None)
    reg_close_at = getattr(t, "reg_close_at", None)
    bracket_state = str(getattr(t, "bracket_state", "")).upper()

    if bracket_state in ("FINISHED", "COMPLETED"):
        return "COMPLETED"
    if bracket_state in ("RUNNING", "LIVE"):
        return "ONGOING"

    if end_at and end_at <= now:
        return "COMPLETED"
    if start_at and start_at <= now:
        return "ONGOING"

    if reg_open_at and reg_close_at:
        if reg_open_at <= now <= reg_close_at:
            return "OPEN"
        if now < reg_open_at:
            return "UPCOMING"
        if now > reg_close_at and (not start_at or now < start_at):
            return "UPCOMING"

    if start_at:
        return "UPCOMING" if now < start_at else "ONGOING"
    return "UPCOMING"


def _annotate_listing(qs):
    qs = qs.annotate(registrations_count=Coalesce(Count("registrations", distinct=True), Value(0)))

    # Prize pool â†’ prefer prize_pool_bdt, else prize_total, else 0
    if hasattr(Tournament, "prize_pool_bdt"):
        qs = qs.annotate(prize_total_anno=F("prize_pool_bdt"))
    elif hasattr(Tournament, "prize_total"):
        qs = qs.annotate(prize_total_anno=F("prize_total"))
    else:
        qs = qs.annotate(prize_total_anno=Value(0, output_field=IntegerField()))

    # Entry fee â†’ prefer entry_fee_bdt, else entry_fee, else 0
    if hasattr(Tournament, "entry_fee_bdt"):
        qs = qs.annotate(entry_fee_anno=F("entry_fee_bdt"))
    elif hasattr(Tournament, "entry_fee"):
        qs = qs.annotate(entry_fee_anno=F("entry_fee"))
    else:
        qs = qs.annotate(entry_fee_anno=Value(0, output_field=IntegerField()))

    # Organizer verified (optional)
    if hasattr(Tournament, "organizer_verified"):
        qs = qs.annotate(organizer_verified_anno=F("organizer_verified"))
    else:
        qs = qs.annotate(organizer_verified_anno=Value(False, output_field=BooleanField()))
    return qs


def _apply_filters(request, qs):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()
    game = (request.GET.get("game") or "").strip()

    if q:
        filters = Q()
        for f in ("name", "title", "slug", "short_description", "description"):
            try:
                Tournament._meta.get_field(f)
                filters |= Q(**{f"{f}__icontains": q})
            except Exception:
                continue
        if filters:
            qs = qs.filter(filters)

    if game and hasattr(Tournament, "game"):
        qs = qs.filter(game=game)

    if status in {"OPEN", "UPCOMING", "ONGOING", "COMPLETED"}:
        ids = [t.id for t in qs.only("id", "start_at") if _status_for(t) == status]
        qs = qs.filter(id__in=ids)

    for key in ("format", "platform", "region"):
        val = (request.GET.get(key) or "").strip()
        if val and hasattr(Tournament, key):
            qs = qs.filter(**{key: val})

    online = (request.GET.get("online") or "").strip().lower()
    if online in ("1", "true", "on") and hasattr(Tournament, "is_online"):
        qs = qs.filter(is_online=True)

    checkin = (request.GET.get("checkin") or "").strip().lower()
    if checkin in ("1", "true", "on"):
        for key in ("check_in_required", "requires_check_in"):
            if hasattr(Tournament, key):
                qs = qs.filter(**{key: True})
                break

    def _int(s, default=None):
        try:
            return int(s)
        except Exception:
            return default

    fee_min = _int(request.GET.get("fee_min"))
    fee_max = _int(request.GET.get("fee_max"))
    if hasattr(Tournament, "entry_fee_bdt"):
        if fee_min is not None:
            qs = qs.filter(entry_fee_bdt__gte=fee_min)
        if fee_max is not None:
            qs = qs.filter(entry_fee_bdt__lte=fee_max)
    elif hasattr(Tournament, "entry_fee"):
        if fee_min is not None:
            qs = qs.filter(entry_fee__gte=fee_min)
        if fee_max is not None:
            qs = qs.filter(entry_fee__lte=fee_max)

    prize_min = _int(request.GET.get("prize_min"))
    prize_max = _int(request.GET.get("prize_max"))
    if hasattr(Tournament, "prize_pool_bdt"):
        if prize_min is not None:
            qs = qs.filter(prize_pool_bdt__gte=prize_min)
        if prize_max is not None:
            qs = qs.filter(prize_pool_bdt__lte=prize_max)
    elif hasattr(Tournament, "prize_total"):
        if prize_min is not None:
            qs = qs.filter(prize_total__gte=prize_min)
        if prize_max is not None:
            qs = qs.filter(prize_total__lte=prize_max)

    return qs


def _apply_powersort(request, qs):
    sort = (request.GET.get("sort") or "powersort").lower()

    if sort == "soon":
        return qs.order_by(
            F("start_at").asc(nulls_last=True),
            "-prize_total_anno",
            "-registrations_count",
            "-organizer_verified_anno",
            "-id",
        )
    if sort == "prize":
        return qs.order_by("-prize_total_anno", F("start_at").asc(nulls_last=True))
    if sort == "popular":
        return qs.order_by("-registrations_count", F("start_at").asc(nulls_last=True))
    if sort == "new":
        return qs.order_by("-id")

    objs = list(qs.only("id", "start_at", "end_at", "reg_open_at", "reg_close_at"))
    if not objs:
        return qs.order_by("-id")

    id_to_rank: Dict[int, int] = {t.id: STATUS_RANK.get(_status_for(t), 9) for t in objs}
    whens = [When(id=tid, then=Value(rank)) for tid, rank in id_to_rank.items()]
    qs = qs.annotate(_status_rank=Case(*whens, default=Value(9), output_field=IntegerField()))

    return qs.order_by(
        "_status_rank",
        F("start_at").asc(nulls_last=True),
        "-prize_total_anno",
        "-registrations_count",
        "-organizer_verified_anno",
        "-id",
    )


def _extract_rules(obj: Any) -> Optional[str]:
    """
    Pull rules text from several possible locations: rules, registration_policy, settings{rules|policy|text}.
    """
    for fname in ("rules", "registration_policy", "tournament_rules"):
        if hasattr(obj, fname):
            val = getattr(obj, fname)
            if val:
                return str(val)
    for fname in ("settings",):
        if hasattr(obj, fname):
            val = getattr(obj, fname)
            if isinstance(val, dict):
                for key in ("rules", "tournament_rules", "policy", "text", "content"):
                    txt = val.get(key)
                    if txt:
                        return str(txt)
    return None


def _extract_description(obj: Any) -> Optional[str]:
    for fname in ("description", "long_description", "short_description"):
        if hasattr(obj, fname):
            val = getattr(obj, fname)
            if val:
                return str(val)
    return None


def _banner_url(obj: Any, request) -> Optional[str]:
    """
    SAFE: only access .url if a file is associated.
    """
    for fname in ("banner", "cover", "image", "thumbnail"):
        if hasattr(obj, fname):
            f = getattr(obj, fname)
            # If no file set, FileField.name is "" â†’ skip
            try:
                name = getattr(f, "name", "") or ""
            except Exception:
                name = ""
            if not name:
                continue
            # With a name present, .url should be safe
            try:
                url = f.url
            except Exception:
                url = None
            if url:
                try:
                    if str(url).startswith(("http://", "https://")):
                        return str(url)
                    return request.build_absolute_uri(url)
                except Exception:
                    return str(url)
    return None


def _try_reverse(name: str, *args, **kwargs) -> Optional[str]:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except Exception:
        return None


def _compute_register_url(t: Tournament) -> str:
    slug_kw = {"slug": t.slug}
    for name in [
        "tournaments:register",
        "tournaments:registration",
        "tournaments:register_team",
        "tournaments:join",
        "tournaments:signup",
        "tournaments:enroll",
        "register",
    ]:
        url = _try_reverse(name, **slug_kw)
        if url:
            return url
    return f"/tournaments/{t.slug}/register/"


def _paginate(request, qs, per_page=12):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page") or 1
    try:
        return paginator.page(page_number), paginator
    except PageNotAnInteger:
        return paginator.page(1), paginator
    except EmptyPage:
        return paginator.page(paginator.num_pages), paginator


def _my_registrations_map(user) -> Dict[int, Registration]:
    if not getattr(user, "is_authenticated", False):
        return {}
    owner = _registration_owner_filter_kwargs(user)
    regs = (
        Registration.objects.select_related("tournament")
        .filter(**owner)
        .order_by("-created_at")
    )
    by_tid = {}
    for r in regs:
        by_tid[r.tournament_id] = r
    return by_tid


# ---------------------------
# Pages
# ---------------------------

def hub(request):
    """
    Hub page with guided discovery + curated rows + explore grid.
    Defensive and independent of minor model differences.
    """
    from apps.tournaments.models import Tournament  # local import to avoid circulars

    q = request.GET.get("q") or ""
    status = request.GET.get("status")
    start = request.GET.get("start")
    fee = request.GET.get("fee")
    sort = request.GET.get("sort")

    base = Tournament.objects.all()

    # minimal fields mapping for templates
    base = base.annotate().select_related().order_by("-id")

    # search
    if q:
        base = base.filter(
            Q(title__icontains=q) |
            Q(game__icontains=q)
        )

    # status filter (open/live/etc). Adjust to your actual fields.
    if status == "open":
        base = base.filter(is_open=True) if hasattr(Tournament, "is_open") else base
    elif status == "live":
        base = base.filter(status="live") if hasattr(Tournament, "status") else base

    # start window (≤7d)
    if start == "7d":
        from django.utils import timezone
        now = timezone.now()
        in7 = now + timezone.timedelta(days=7)
        if hasattr(Tournament, "starts_at"):
            base = base.filter(starts_at__gte=now, starts_at__lte=in7)

    # fee filter
    if fee == "free":
        if hasattr(Tournament, "fee_amount"):
            base = base.filter(fee_amount=0)

    # curated subsets
    live_qs = base.filter(status="live")[:6] if hasattr(Tournament, "status") else []
    starting_soon_qs = []
    new_this_week_qs = []
    free_qs = []

    if hasattr(Tournament, "starts_at"):
        from django.utils import timezone
        now = timezone.now()
        soon = now + timezone.timedelta(days=7)
        starting_soon_qs = base.filter(starts_at__gte=now, starts_at__lte=soon).order_by("starts_at")[:6]
        # "new this week" as recently created
        new_this_week_qs = base.filter(created_at__gte=now - timezone.timedelta(days=7))[:6] if hasattr(Tournament, "created_at") else base[:6]
    if hasattr(Tournament, "fee_amount"):
        free_qs = base.filter(fee_amount=0)[:6]

    # explore grid sorting
    grid = base
    if sort == "new":
        grid = grid.order_by("-id")
    elif sort == "fee_asc" and hasattr(Tournament, "fee_amount"):
        grid = grid.order_by("fee_amount")

    tournaments = list(grid[:24])  # cap first page

    for t in tournaments:
        resolved_banner = getattr(t, "banner_url", None) or _banner_url(t)
        object.__setattr__(t, "dc_banner_url", resolved_banner)
        resolved_status = getattr(t, "status", None) or _status_for_card(t)
        object.__setattr__(t, "dc_status", resolved_status)
        resolved_reg = getattr(t, "register_url", None) or _register_url(t)
        object.__setattr__(t, "dc_register_url", resolved_reg)

    # game registry + counts (include card image)
    games = []
    for g in GAME_REGISTRY:
        cnt = base.filter(game=g["slug"]).count() if hasattr(Tournament, "game") else 0
        games.append({
            "slug": g["slug"],
            "name": g["name"],
            "icon_url": g.get("icon_url"),
            "primary": g.get("primary", "#7c3aed"),
            "image": g.get("image"),  # <<< used by card background
            "count": cnt,
        })

    my_states = _compute_my_states(request, tournaments)

    ctx = {
        "q": q, "sort": sort,
        "tournaments": tournaments,
        "live_tournaments": live_qs,
        "starting_soon": starting_soon_qs,
        "new_this_week": new_this_week_qs,
        "free_tournaments": free_qs,
        "games": games,
        "my_reg_states": my_states,
    }

    # --- stats (defensive) ---
    stats = {"total_active": 0, "players_this_month": 0, "prize_pool_month": "0"}
    try:
        from django.utils import timezone
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # total active
        if hasattr(Tournament, "is_open"):
            stats["total_active"] = base.filter(is_open=True).count()
        else:
            stats["total_active"] = base.count()
        # players this month (best-effort)
        try:
            from apps.tournaments.models import Registration
            stats["players_this_month"] = Registration.objects.filter(created_at__gte=this_month_start).count()
        except Exception:
            stats["players_this_month"] = 0
        # prize pool (sum) — if you have a field prize_pool
        if hasattr(Tournament, "prize_pool"):
            from django.db.models import Sum
            total = base.filter(created_at__gte=this_month_start).aggregate(s=Sum("prize_pool")).get("s") or 0
            stats["prize_pool_month"] = f"{int(total):,}"
    except Exception:
        pass

    ctx.update({"stats": stats})

    return render(request, "tournaments/hub.html", ctx)


def list_by_game(request, game):
    from apps.tournaments.models import Tournament

    q = request.GET.get("q") or ""
    fee = request.GET.get("fee")
    status = request.GET.get("status")
    start = request.GET.get("start")
    sort = request.GET.get("sort")

    base = Tournament.objects.all()
    if hasattr(Tournament, "game"):
        base = base.filter(game=game)

    if q:
        base = base.filter(Q(title__icontains=q))

    if fee == "free" and hasattr(Tournament, "fee_amount"):
        base = base.filter(fee_amount=0)

    if status == "open":
        base = base.filter(is_open=True) if hasattr(Tournament, "is_open") else base

    if start == "7d" and hasattr(Tournament, "starts_at"):
        from django.utils import timezone
        now = timezone.now()
        soon = now + timezone.timedelta(days=7)
        base = base.filter(starts_at__gte=now, starts_at__lte=soon)

    if sort == "new":
        base = base.order_by("-id")
    elif sort == "fee_asc" and hasattr(Tournament, "fee_amount"):
        base = base.order_by("fee_amount")

    tournaments = list(base[:36])

    for t in tournaments:
        resolved_banner = getattr(t, "banner_url", None) or _banner_url(t)
        object.__setattr__(t, "_dc_banner_url", resolved_banner)
        resolved_status = getattr(t, "status", None) or _status_for_card(t)
        object.__setattr__(t, "_dc_status", resolved_status)
        resolved_reg = getattr(t, "register_url", None) or _register_url(t)
        object.__setattr__(t, "_dc_register_url", resolved_reg)


    # game meta from registry (future-proof, even if no Game model)
    gm = next((g for g in GAME_REGISTRY if g["slug"] == game), {"slug": game, "name": game.title(), "icon_url": "", "primary": "#7c3aed"})
    total = base.count()
    my_states = _compute_my_states(request, tournaments)

    ctx = {
        "q": q, "sort": sort,
        "game": game, "game_meta": gm,
        "tournaments": tournaments,
        "total": total,
        "my_reg_states": my_states,
    }
    return render(request, "tournaments/list_by_game.html", ctx)


def detail(request, slug: str):
    t = get_object_or_404(Tournament.objects.select_related(), slug=slug)
    status = _status_for(t)
    now = _now()

    # Countdown target
    check_in_start = getattr(t, "check_in_starts_at", None) or getattr(t, "checkin_starts_at", None)
    start_at = getattr(t, "start_at", None)
    countdown_to = check_in_start or start_at

    # Slots left (capacity - verified regs)
    capacity = getattr(t, "capacity", None)
    owner = _registration_owner_filter_kwargs(request.user)
    regs_qs = Registration.objects.filter(tournament=t, **owner)
    all_regs = Registration.objects.filter(tournament=t)
    verified_total = (
        all_regs.filter(state__in=["VERIFIED", "APPROVED"]).count()
        if hasattr(Registration, "state")
        else all_regs.count()
    )
    slots_left = max((capacity or 0) - verified_total, 0) if capacity else None

    # Prize & entry
    prize_total = getattr(t, "prize_pool_bdt", getattr(t, "prize_total", 0))
    entry_fee = getattr(t, "entry_fee_bdt", getattr(t, "entry_fee", 0))

    # My registration / PV
    my_reg = regs_qs.select_related().first()
    my_pv_state = None
    if my_reg and hasattr(my_reg, "payment_verification"):
        pv = getattr(my_reg, "payment_verification")
        my_pv_state = getattr(pv, "status", None)

    # CTA
    cta = "register"
    if status == "COMPLETED":
        cta = "closed"
    elif my_reg:
        reg_state = str(getattr(my_reg, "state", "")).upper()
        if reg_state in ("PENDING", "SUBMITTED"):
            cta = "view_receipt" if my_pv_state else "continue"
        elif reg_state in ("VERIFIED", "APPROVED"):
            ci_start = getattr(t, "check_in_starts_at", None) or getattr(t, "checkin_starts_at", None)
            ci_end = getattr(t, "check_in_ends_at", None) or getattr(t, "checkin_ends_at", None)
            if ci_start and ci_end and ci_start <= now <= ci_end:
                cta = "check_in"
            elif start_at and now >= start_at:
                cta = "your_matches"
            else:
                cta = "registered"
        else:
            cta = "continue"

    # Content extraction & URLs
    rules_html = _extract_rules(t)
    description_html = _extract_description(t)
    banner_url = _banner_url(t, request)
    register_url = _compute_register_url(t)

    ctx = {
        "t": t,
        "tournament": t,
        "status": status,
        "countdown_to": countdown_to,
        "slots_left": slots_left,
        "prize_total": prize_total,
        "entry_fee": entry_fee,
        "my_registration": my_reg,
        "my_pv_state": my_pv_state,
        "rules_html": rules_html,
        "description_html": description_html,
        "banner_url": banner_url,
        "register_url": register_url,
        # Optional partials
        "has_organizer_badge": _tpl_exists("tournaments/_organizer_badge.html"),
        "has_prize_pool": _tpl_exists("tournaments/_prize_pool.html"),
        "has_schedule_timeline": _tpl_exists("tournaments/_schedule_timeline.html"),
        "has_rules_drawer": _tpl_exists("tournaments/_rules_drawer.html"),
        "has_participants_grid": _tpl_exists("tournaments/_participants_grid.html"),
        "has_bracket": _tpl_exists("tournaments/bracket.html"),
        "has_standings": _tpl_exists("tournaments/standings.html"),
        "has_stream_embed": _tpl_exists("tournaments/_stream_embed.html"),
        "cta": cta,
    }
    return render(request, "tournaments/detail.html", ctx)


# Image paths are relative to STATIC_URL and will be resolved by the template via {% static %}
GAME_REGISTRY = [
    {"slug": "valorant",       "name": "Valorant",        "icon_url": "", "primary": "#ff4655", "image": "img/game_cards/Valorant.jpg"},
    {"slug": "efootball",      "name": "eFootball",       "icon_url": "", "primary": "#1e90ff", "image": "img/game_cards/efootball.jpeg"},
    # CS2: user typo "cse" noted; include both keys to be safe
    {"slug": "cs2",            "name": "Counter-Strike 2","icon_url": "", "primary": "#f59e0b", "image": "img/game_cards/CS2.jpg"},
    {"slug": "cse",            "name": "Counter-Strike 2","icon_url": "", "primary": "#f59e0b", "image": "img/game_cards/CS2.jpg"},
    {"slug": "fc26",           "name": "FC 26",           "icon_url": "", "primary": "#22c55e", "image": "img/game_cards/FC26.jpg"},
    {"slug": "mobilelegend",   "name": "Mobile Legends",  "icon_url": "", "primary": "#7c3aed", "image": "img/game_cards/MobileLegend.jpg"},
    {"slug": "pubg",           "name": "PUBG Mobile",     "icon_url": "", "primary": "#10b981", "image": "img/game_cards/PUBG.jpeg"},
]

def _status_for_card(t):
    # Basic guard; customize to your status fields
    try:
        return t.status
    except Exception:
        # infer from dates if needed
        return "open" if getattr(t, "is_open", True) else "closed"

def _banner_url(t):
    # If your model provides a property, prefer that
    url = getattr(t, "banner_url", None)
    if url:
        return url
    # fallback from ImageField `banner`
    banner = getattr(t, "banner", None)
    try:
        return banner.url if banner else None
    except Exception:
        return None

def _register_url(t):
    try:
        return reverse("tournaments:register", args=[t.slug])
    except Exception:
        return getattr(t, "register_url", None) or "#"

def _compute_my_states(request, tournaments):
    """
    Returns { tournament.id: {registered: bool, cta: 'continue'|'receipt'|None, cta_url: str|None} }
    Falls back gracefully if Registration/PaymentVerification models differ.
    """
    states = {}
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return states
    ids = [getattr(t, "id") for t in tournaments if getattr(t, "id", None)]
    if not ids:
        return states

    # Try to import models; guard failures
    try:
        from apps.tournaments.models import Registration
    except Exception:
        Registration = None
    try:
        from apps.tournaments.models import PaymentVerification
    except Exception:
        PaymentVerification = None

    reg_qs = []
    if Registration:
        try:
            reg_qs = list(Registration.objects.filter(user=user, tournament_id__in=ids).values("tournament_id", "id"))
        except Exception:
            reg_qs = []

    pv_map = {}
    if PaymentVerification and reg_qs:
        try:
            reg_ids = [r["id"] for r in reg_qs]
            for pv in PaymentVerification.objects.filter(registration_id__in=reg_ids).values("registration_id","status"):
                pv_map[pv["registration_id"]] = pv["status"]
        except Exception:
            pv_map = {}

    reg_by_tid = {}
    for r in reg_qs:
        reg_by_tid[r["tournament_id"]] = r["id"]

    for t in tournaments:
        tid = getattr(t, "id", None)
        if not tid:
            continue
        if tid in reg_by_tid:
            reg_id = reg_by_tid[tid]
            status = pv_map.get(reg_id)
            # Choose CTA based on PV status
            if status in (None, "pending", "rejected"):
                states[tid] = {"registered": True, "cta": "continue", "cta_url": _register_url(t)}
            elif status in ("verified", "approved"):
                try:
                    receipt_url = reverse("tournaments:registration_receipt", args=[t.slug])
                except Exception:
                    receipt_url = _register_url(t)
                states[tid] = {"registered": True, "cta": "receipt", "cta_url": receipt_url}
            else:
                states[tid] = {"registered": True, "cta": None, "cta_url": None}
        else:
            states[tid] = {"registered": False, "cta": None, "cta_url": None}
    return states
