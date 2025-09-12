# apps/tournaments/views/public.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, F, Value, IntegerField, BooleanField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.timesince import timesince

# Prefer app-local imports; fall back to apps.get_model in case of refactors
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

STATUS_RANK = {
    "OPEN": 0,        # accepting registrations
    "UPCOMING": 1,    # announced; reg not open yet
    "ONGOING": 2,     # bracket running
    "COMPLETED": 3,   # finished
}

def _now():
    return timezone.now()


def _status_for(t: Tournament) -> str:
    """
    Derive a coarse tournament lifecycle status from available fields.
    Works even if some fields are missing.
    """
    now = _now()
    start_at = getattr(t, "start_at", None)
    end_at = getattr(t, "end_at", None)
    reg_open_at = getattr(t, "reg_open_at", None)
    reg_close_at = getattr(t, "reg_close_at", None)
    bracket_state = getattr(t, "bracket_state", "")  # optional, e.g. RUNNING/FINISHED

    # Bracket-driven overrides
    if str(bracket_state).upper() in ("FINISHED", "COMPLETED"):
        return "COMPLETED"
    if str(bracket_state).upper() in ("RUNNING", "LIVE"):
        return "ONGOING"

    # Time-based fallbacks
    if end_at and end_at <= now:
        return "COMPLETED"
    if start_at and start_at <= now:
        return "ONGOING"

    # Registration window
    if reg_open_at and reg_close_at:
        if reg_open_at <= now <= reg_close_at:
            return "OPEN"
        if now < reg_open_at:
            return "UPCOMING"
        if now > reg_close_at and (not start_at or now < start_at):
            # Reg closed but event not started yet
            return "UPCOMING"

    # Minimal fallback using start time only
    if start_at:
        return "UPCOMING" if now < start_at else "ONGOING"

    return "UPCOMING"


def _annotate_listing(qs):
    """
    Adds defensive annotations needed for sorting/cards.
    - registrations_count
    - prize_total (fallback 0)
    - entry_fee (fallback 0)
    - organizer_verified (fallback False)
    """
    qs = qs.annotate(
        registrations_count=Coalesce(Count("registrations", distinct=True), Value(0)),
    )
    # Optional numeric/boolean fields (prize_total, entry_fee, organizer_verified)
    if hasattr(Tournament, "prize_total"):
        qs = qs.annotate(prize_total_anno=F("prize_total"))
    else:
        qs = qs.annotate(prize_total_anno=Value(0, output_field=IntegerField()))

    if hasattr(Tournament, "entry_fee"):
        qs = qs.annotate(entry_fee_anno=F("entry_fee"))
    else:
        qs = qs.annotate(entry_fee_anno=Value(0, output_field=IntegerField()))

    if hasattr(Tournament, "organizer_verified"):
        qs = qs.annotate(organizer_verified_anno=F("organizer_verified"))
    else:
        qs = qs.annotate(organizer_verified_anno=Value(False, output_field=BooleanField()))

    return qs


def _apply_filters(request, qs):
    """
    Faceted filters via query params (all optional & safe):
      - q: search name/slug/description
      - status: open/upcoming/ongoing/completed
      - game: code
      - format, platform: exact match if fields exist
      - fee_min, fee_max (ints)
      - prize_min, prize_max (ints)
      - checkin: '1' filter events requiring check-in (if field exists)
      - region, online: exact flags if exist
    """
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

    # Post-filter by derived status (done in Python; acceptable for page sizes)
    if status in {"OPEN", "UPCOMING", "ONGOING", "COMPLETED"}:
        ids = [t.id for t in qs.only("id", "start_at") if _status_for(t) == status]
        qs = qs.filter(id__in=ids)

    # format/platform filters
    for key in ("format", "platform", "region"):
        val = (request.GET.get(key) or "").strip()
        if val and hasattr(Tournament, key):
            qs = qs.filter(**{key: val})

    # online toggle
    online = (request.GET.get("online") or "").strip().lower()
    if online in ("1", "true", "on") and hasattr(Tournament, "is_online"):
        qs = qs.filter(is_online=True)

    # check-in required toggle
    checkin = (request.GET.get("checkin") or "").strip().lower()
    if checkin in ("1", "true", "on"):
        for key in ("check_in_required", "requires_check_in"):
            if hasattr(Tournament, key):
                qs = qs.filter(**{key: True})
                break

    # fee/prize ranges
    def _int(s, default=None):
        try:
            return int(s)
        except Exception:
            return default

    fee_min = _int(request.GET.get("fee_min"))
    fee_max = _int(request.GET.get("fee_max"))
    if hasattr(Tournament, "entry_fee"):
        if fee_min is not None:
            qs = qs.filter(entry_fee__gte=fee_min)
        if fee_max is not None:
            qs = qs.filter(entry_fee__lte=fee_max)

    prize_min = _int(request.GET.get("prize_min"))
    prize_max = _int(request.GET.get("prize_max"))
    if hasattr(Tournament, "prize_total"):
        if prize_min is not None:
            qs = qs.filter(prize_total__gte=prize_min)
        if prize_max is not None:
            qs = qs.filter(prize_total__lte=prize_max)

    return qs


def _apply_powersort(request, qs):
    """
    PowerSort tuple:
      1) status_rank (OPEN -> UPCOMING -> ONGOING -> COMPLETED)
      2) start_at ASC
      3) prize_total DESC
      4) registrations_count DESC
      5) organizer_verified DESC
      6) created_at DESC
    We emulate with tuple ordering and safe fallbacks.
    """
    sort = (request.GET.get("sort") or "powersort").lower()

    # Common alternates
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

    # powersort default: we can't order by derived status easily in SQL, so we pre-scan ids by status buckets.
    # Acceptable for typical page sizes; for very large sets, consider a materialized status field.
    ids_by_status: Dict[int, int] = {}
    for t in qs.only("id", "start_at", "end_at", "reg_open_at", "reg_close_at"):
        ids_by_status[t.id] = STATUS_RANK.get(_status_for(t), 9)

    # Annotate the in-Python status rank into a CASE-like sort using a list (coarse)
    ordered_ids = sorted(ids_by_status.items(), key=lambda kv: kv[1])
    if not ordered_ids:
        return qs.order_by("-id")

    # We'll sort by a list of ids in that status order + DB-level tie-breakers
    id_order = [tid for tid, _rank in ordered_ids]
    preserved = [F("id").in_(id_order)]  # coarse pre-filter to favor our list; final order applied below
    qs = qs.order_by(*preserved, F("start_at").asc(nulls_last=True),
                     "-prize_total_anno", "-registrations_count",
                     "-organizer_verified_anno", "-id")
    return qs


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
    regs = (
        Registration.objects.select_related("tournament")
        .filter(user=user)  # adjust if Registration ties to profile/team
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
    /tournaments/ : Spotlight + Directory + My Registrations + Explore grid with filters.
    """
    qs = Tournament.objects.all().select_related()
    qs = _annotate_listing(qs)
    qs = _apply_filters(request, qs)
    qs = _apply_powersort(request, qs)

    page_obj, paginator = _paginate(request, qs, per_page=12)

    # Spotlight: feature a few verified/featured events (optional flags)
    spotlight = Tournament.objects.all()
    if hasattr(Tournament, "is_featured"):
        spotlight = spotlight.filter(is_featured=True)
    elif hasattr(Tournament, "organizer_verified"):
        spotlight = spotlight.filter(organizer_verified=True)
    spotlight = _annotate_listing(spotlight).order_by("-prize_total_anno", "-id")[:6]

    # Directory counts per game
    directory_counts = {}
    if hasattr(Tournament, "game"):
        counts = (
            Tournament.objects.values_list("game")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        directory_counts = {code: c for code, c in counts}

    ctx = {
        "page_obj": page_obj,
        "paginator": paginator,
        "object_list": page_obj.object_list,
        "spotlight": spotlight,
        "games": GAME_CHOICES,
        "directory_counts": directory_counts,
        "query": (request.GET.get("q") or "").strip(),
        "active_game": (request.GET.get("game") or "").strip(),
        "sort": (request.GET.get("sort") or "powersort").lower(),
        "filters": {
            "status": (request.GET.get("status") or "").strip().lower(),
            "format": (request.GET.get("format") or "").strip(),
            "platform": (request.GET.get("platform") or "").strip(),
            "fee_min": request.GET.get("fee_min") or "",
            "fee_max": request.GET.get("fee_max") or "",
            "prize_min": request.GET.get("prize_min") or "",
            "prize_max": request.GET.get("prize_max") or "",
            "checkin": (request.GET.get("checkin") or "").strip().lower() in ("1", "true", "on"),
            "region": (request.GET.get("region") or "").strip(),
            "online": (request.GET.get("online") or "").strip().lower() in ("1", "true", "on"),
        },
        "my_registrations": _my_registrations_map(request.user),
    }
    return render(request, "tournaments/hub.html", ctx)


def list_by_game(request, game: str):
    """
    /tournaments/<game>/
    """
    request.GET._mutable = True  # safe in view context; make game sticky in querystring
    request.GET["game"] = game
    return hub(request)


def detail(request, slug: str):
    t = get_object_or_404(Tournament.objects.select_related(), slug=slug)
    status = _status_for(t)
    now = _now()

    # Countdown target: prefer check-in start, else start time
    check_in_start = getattr(t, "check_in_starts_at", None) or getattr(t, "checkin_starts_at", None)
    start_at = getattr(t, "start_at", None)
    countdown_to = check_in_start or start_at

    # Slots left (capacity - verified regs; defensive)
    capacity = getattr(t, "capacity", None)
    regs_qs = Registration.objects.filter(tournament=t)
    regs_total = regs_qs.count()
    verified = regs_qs.filter(state__in=["VERIFIED", "APPROVED"]).count() if hasattr(Registration, "state") else regs_total
    slots_left = None
    if capacity:
        slots_left = max(capacity - verified, 0)

    # Prize & entry (defensive)
    prize_total = getattr(t, "prize_total", 0)
    entry_fee = getattr(t, "entry_fee", 0)

    # My registration (and PV state) if logged in
    my_reg = None
    my_pv_state = None
    if getattr(request.user, "is_authenticated", False):
        my_reg = Registration.objects.filter(tournament=t, user=request.user).select_related().first()
        if my_reg and hasattr(my_reg, "payment_verification"):
            pv = getattr(my_reg, "payment_verification")
            my_pv_state = getattr(pv, "status", None)

    # CTA state machine
    cta = "register"
    if status in ("COMPLETED",):
        cta = "closed"
    elif my_reg:
        # draft vs submitted
        reg_state = getattr(my_reg, "state", "").upper()
        if reg_state in ("PENDING", "SUBMITTED"):
            cta = "view_receipt" if my_pv_state else "continue"
        elif reg_state in ("VERIFIED", "APPROVED"):
            # Pre-check-in vs check-in window
            # Determine if we're in check-in based on fields
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
    }
    return render(request, "tournaments/detail.html", ctx)
