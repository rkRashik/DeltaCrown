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
    """Return UserProfile for auth user, or None (without creating)."""
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
    - If model has `profile` FK → use profile
    - Else if model has `user`:
        - If it's FK to UserProfile → use profile
        - If it's FK to auth.User → use user
    - Else → return empty (matches nothing)
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

    # Prize pool → prefer prize_pool_bdt, else prize_total, else 0
    if hasattr(Tournament, "prize_pool_bdt"):
        qs = qs.annotate(prize_total_anno=F("prize_pool_bdt"))
    elif hasattr(Tournament, "prize_total"):
        qs = qs.annotate(prize_total_anno=F("prize_total"))
    else:
        qs = qs.annotate(prize_total_anno=Value(0, output_field=IntegerField()))

    # Entry fee → prefer entry_fee_bdt, else entry_fee, else 0
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
            # If no file set, FileField.name is "" → skip
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
    /tournaments/ : Spotlight + Directory + My Registrations + Explore grid with filters.
    """
    qs = Tournament.objects.all().select_related()
    qs = _annotate_listing(qs)
    qs = _apply_filters(request, qs)
    qs = _apply_powersort(request, qs)

    page_obj, paginator = _paginate(request, qs, per_page=12)

    # Attach a UI-only banner url (avoid clashing with @property banner_url)
    objects = list(page_obj.object_list)
    for obj in objects:
        setattr(obj, "ui_banner_url", _banner_url(obj, request))

    # Spotlight
    spotlight = Tournament.objects.all()
    if hasattr(Tournament, "is_featured"):
        spotlight = spotlight.filter(is_featured=True)
    elif hasattr(Tournament, "organizer_verified"):
        spotlight = spotlight.filter(organizer_verified=True)
    spotlight = _annotate_listing(spotlight).order_by("-prize_total_anno", "-id")[:6]
    spotlight = list(spotlight)
    for s in spotlight:
        setattr(s, "ui_banner_url", _banner_url(s, request))

    # Directory counts per game
    directory_counts = {}
    if hasattr(Tournament, "game"):
        counts = (
            Tournament.objects.values_list("game")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        directory_counts = {code: c for code, c in counts}

    game_cards = [
        {"code": code, "label": label, "count": directory_counts.get(code, 0)}
        for code, label in GAME_CHOICES
    ]

    ctx = {
        "page_obj": page_obj,
        "paginator": paginator,
        "object_list": objects,   # each has ui_banner_url
        "spotlight": spotlight,   # each has ui_banner_url
        "games": GAME_CHOICES,
        "directory_counts": directory_counts,
        "game_cards": game_cards,
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
        "status_list": ["open", "upcoming", "ongoing", "completed"],
        "my_registrations": _my_registrations_map(request.user),
    }
    return render(request, "tournaments/hub.html", ctx)


def list_by_game(request, game: str):
    """ /tournaments/<game>/  -> reuse hub() with game filter """
    request.GET._mutable = True
    request.GET["game"] = game
    return hub(request)


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
