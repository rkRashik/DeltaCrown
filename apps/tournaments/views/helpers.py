from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Tuple, List
from dataclasses import dataclass
import re

from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.timesince import timesince
from django.utils.html import strip_tags

# Optional: sanitize with bleach if present; otherwise safe fallback
try:
    import bleach  # type: ignore
except Exception:  # bleach not installed
    bleach = None  # pragma: no cover

# Robust model getters (work even if import ordering changes)
Tournament = apps.get_model("tournaments", "Tournament")

# ---------- Game visual registry (used by detail hero + hub cards) ----------
# Provide theme colors and optional static assets per game.
GAME_REGISTRY: Dict[str, Dict[str, Any]] = {
    "valorant": {
        "name": "Valorant",
        "primary": "#ff4655",
        "glowA": "#ff4655",
        "glowB": "#7c3aed",
        "icon": "img/games/valorant.svg",
        "card_image": "img/game_cards/Valorant.jpg",
    },
    "efootball": {
        "name": "eFootball",
        "primary": "#1e90ff",
        "glowA": "#1e90ff",
        "glowB": "#facc15",
        "icon": "img/games/efootball.svg",
        "card_image": "img/game_cards/efootball.jpeg",
    },
    "cs2": {
        "name": "Counter-Strike 2",
        "primary": "#f59e0b",
        "glowA": "#f59e0b",
        "glowB": "#06b6d4",
        "icon": "img/games/cs2.svg",
        "card_image": "img/game_cards/CS2.jpg",
    },
    "fc26": {
        "name": "FC 26",
        "primary": "#22c55e",
        "glowA": "#22c55e",
        "glowB": "#8b5cf6",
        "icon": "img/games/fc.svg",
        "card_image": "img/game_cards/FC26.jpg",
    },
    "mobilelegend": {
        "name": "Mobile Legends",
        "primary": "#7c3aed",
        "glowA": "#7c3aed",
        "glowB": "#06b6d4",
        "icon": "img/games/mlbb.svg",
        "card_image": "img/game_cards/MobileLegend.jpg",
    },
    "pubg": {
        "name": "PUBG Mobile",
        "primary": "#10b981",
        "glowA": "#10b981",
        "glowB": "#f59e0b",
        "icon": "img/games/pubg.svg",
        "card_image": "img/game_cards/PUBG.jpeg",
    },
}

# ---------- tiny utils ----------
def now():
    return timezone.now()

def first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

def coerce_int(v):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return None

def fmt_money(v):
    if v in (None, ""):
        return None
    try:
        iv = int(float(v))
        return f"{iv:,}"
    except Exception:
        return str(v)

def as_bool(v, default=None):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1","true","yes","y","on"): return True
    if s in ("0","false","no","n","off"): return False
    return default

def maybe_text(*cands):
    for c in cands:
        if isinstance(c, str) and c.strip():
            return c
    return None

def as_html(v):
    return v  # pass-through for rich text

def slugify_game(v: Optional[str]) -> str:
    if not v:
        return "generic"
    s = str(v).strip().lower()
    s = s.replace(" ", "").replace("_", "").replace("-", "")
    # common aliases
    aliases = {"efootballmobile": "efootball", "mlbb": "mobilelegend", "csgo": "cs2"}
    return aliases.get(s, s)

# ---------- content sanitizer ----------
_ALLOWED_TAGS = ["p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "a", "blockquote", "code", "pre", "span"]
_ALLOWED_ATTRS = {"a": ["href", "title", "target", "rel"], "span": ["class"]}

def sanitize_html(html: Optional[str]) -> Optional[str]:
    """
    Best-effort sanitizer: uses bleach if available; else strips tags (keeps line breaks).
    Forbidden: <script>, <style>, inline event handlers.
    """
    if not html:
        return None
    if bleach:
        return bleach.clean(
            html,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRS,
            protocols=["http", "https", "mailto", "tel"],
            strip=True,
        )
    # Fallback: drop <script>/<style>, then strip all tags; keep simple newlines
    txt = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
    txt = strip_tags(txt)
    return txt

# ---------- date/time helpers ----------
def tz_label(tzinfo=None) -> str:
    """
    Render a short TZ label: 'BST | UTC+6' for Bangladesh by default.
    """
    try:
        tz = tzinfo or timezone.get_current_timezone()
        offset = tz.utcoffset(now()) or timezone.timedelta(0)
        hours = int(offset.total_seconds() // 3600)
        sign = "+" if hours >= 0 else "-"
        return f"{getattr(tz, 'zone', 'Local')} | UTC{sign}{abs(hours)}"
    except Exception:
        return "Local Time"

def countdown_to(dt) -> Optional[Dict[str, Any]]:
    """
    Returns remaining time segments + human string until dt, or None if dt is past.
    """
    if not dt:
        return None
    n = now()
    if dt <= n:
        return None
    delta = dt - n
    secs = int(delta.total_seconds())
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return {
        "days": d, "hours": h, "minutes": m, "seconds": s,
        "human": f"in {timesince(n, dt)}",
        "target_iso": dt.isoformat(),
    }

# ---------- readers for common tournament fields ----------
def banner_url_from_file(obj: Any) -> Optional[str]:
    for fname in ("banner", "cover", "image", "thumbnail", "hero"):
        f = getattr(obj, fname, None)
        if not f:
            continue
        try:
            url = f.url
            if url:
                return url
        except Exception:
            if isinstance(f, str) and f:
                return f
    return None

def banner_url(obj: Any) -> Optional[str]:
    try:
        url = getattr(obj, "banner_url", None)
        if url:
            return str(url)
    except Exception:
        pass
    s = getattr(obj, "settings", None)
    if s:
        for name in ("banner", "cover_image", "banner_url"):
            v = getattr(s, name, None)
            if isinstance(v, str) and v:
                return v
    return banner_url_from_file(obj)

def register_url(t: Any) -> str:
    try:
        # Import the team tournament detection function
        from apps.tournaments.views.registration_unified import _is_team_tournament
        
        # Check if this is a team tournament first
        is_team = _is_team_tournament(t)
        
        # If it's a solo tournament, always use unified registration
        if not is_team:
            return reverse("tournaments:unified_register", args=[t.slug])
        
        # For team tournaments, check game type for specialized forms
        game_name = str(getattr(t, 'game', '')).lower()
        game_type = str(getattr(t, 'game_type', '')).lower()
        
        # Check if this is a Valorant team tournament
        if 'valorant' in game_name or 'valorant' in game_type:
            return reverse("tournaments:valorant_register", args=[t.slug])
        
        # Check if this is an eFootball team tournament
        if any(keyword in game_name or keyword in game_type for keyword in ['efootball', 'e-football', 'football', 'fifa', 'pes']):
            return reverse("tournaments:efootball_register", args=[t.slug])
        
        # Use unified registration for other team tournaments
        return reverse("tournaments:unified_register", args=[t.slug])
    except Exception:
        return getattr(t, "register_url", None) or f"/tournaments/{getattr(t,'slug',slugify(str(t)))}/register/"

def read_title(obj: Any) -> str:
    return first(getattr(obj, "title", None), getattr(obj, "name", None), str(obj)) or "Untitled Tournament"

def read_game(obj: Any) -> Optional[str]:
    for f in ("game_name", "game_display", "game_title"):
        v = getattr(obj, f, None)
        if v:
            return str(v)
    v = getattr(obj, "game", None)
    return str(v).title() if v else None

def read_fee_amount(obj: Any):
    for f in ("fee_amount", "entry_fee_bdt", "entry_fee", "fee", "registration_fee"):
        v = getattr(obj, f, None)
        if v not in (None, ""):
            return coerce_int(v)
    return None

def read_prize_amount(obj: Any):
    for f in ("prize_pool", "total_prize", "prize_money_bdt", "prize_money"):
        v = getattr(obj, f, None)
        if v not in (None, ""):
            return coerce_int(v)
    return None

def read_url(obj: Any) -> str:
    try:
        if hasattr(obj, "get_absolute_url") and callable(obj.get_absolute_url):
            u = obj.get_absolute_url()
            if u:
                return u
    except Exception:
        pass
    try:
        slug = getattr(obj, "slug", None)
        if slug:
            return reverse("tournaments:detail", kwargs={"slug": slug})
    except Exception:
        pass
    return "#"

def status_for_card(t: Any) -> str:
    v = getattr(t, "status", None)
    if v:
        return str(v).lower()
    return "open" if getattr(t, "is_open", True) else "closed"

# ---------- computed page state / role / CTA ----------
def computed_state(t: Any) -> str:
    """
    A consistent state for the UI/CTA logic:
      'published' | 'open' | 'filling' | 'locked' | 'live' | 'completed' | 'archived'
    """
    s = getattr(t, "status", None) or getattr(t, "state", None)
    s = str(s).lower() if s else None
    if s in ("draft","published","open","filling","locked","live","complete","completed","archived"):
        return "completed" if s == "complete" else s

    n = now()
    start = first(getattr(t, "starts_at", None), getattr(t, "start_at", None))
    end   = first(getattr(t, "ends_at", None),   getattr(t, "end_at", None))
    reg_o = getattr(t, "reg_open_at", None)
    reg_c = getattr(t, "reg_close_at", None)

    if start and start > n:
        if reg_c and n > reg_c:
            return "locked"
        if reg_o and n < reg_o:
            return "published"
        return "open"
    if start and start <= n and (not end or end >= n):
        return "live"
    if end and end < n:
        return "completed"
    return "published"

def role_for(user, t):
    if not getattr(user, "is_authenticated", False):
        return "visitor"
    try:
        for name in ("registrations", "participants", "teams"):
            if hasattr(t, name):
                rel = getattr(t, name)
                if hasattr(rel, "filter") and rel.filter(user=user).exists():
                    if hasattr(rel.model, "is_captain") and rel.filter(user=user, is_captain=True).exists():
                        return "captain"
                    return "player"
    except Exception:
        pass
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return "admin"
    return "user"

def user_reg(user, t):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        rel = None
        for name in ("registrations", "participants", "teams"):
            if hasattr(t, name):
                rel = getattr(t, name)
                break
        if rel and hasattr(rel, "filter"):
            reg = rel.filter(user=user).first()
            if reg:
                return {
                    "status": getattr(reg, "status", None),
                    "team": first(getattr(reg, "team_name", None), getattr(reg, "team", None)),
                    "payment": getattr(reg, "payment_status", None),
                    "receipt_url": getattr(reg, "receipt_url", None),
                }
    except Exception:
        pass
    return None

def next_cta(user, t, state, entry_fee, reg_url):
    """
    Contextual CTA:
      - open/published/filling: Register / Pay / Check-in / Status
      - locked: Registration closed (or Check-in if allowed)
      - live: Watch Live or Go to Match Hub (if player)
      - completed: View results
    """
    ur = user_reg(user, t)
    paid = (ur and str(first(ur.get("payment"), "")).lower() in ("paid","success","succeeded","confirmed"))
    check_in_required = as_bool(getattr(getattr(t, "settings", None), "check_in_required", None), False)

    if state in ("published", "open", "filling"):
        if not ur:
            return {"label": "Register now", "kind": "register", "url": reg_url}
        if ur and not paid and entry_fee and entry_fee > 0:
            return {"label": "Complete payment", "kind": "pay", "url": reg_url}
        if check_in_required:
            return {"label": "Check-in", "kind": "checkin", "url": reg_url}
        return {"label": "Your status", "kind": "status", "url": reg_url}

    if state == "locked":
        if ur and check_in_required:
            return {"label": "Check-in", "kind": "checkin", "url": reg_url}
        return {"label": "Registration closed", "kind": "closed", "url": None}

    if state == "live":
        live_url = first(getattr(t, "live_stream_url", None), f"/dashboard/tournaments/{getattr(t,'id','')}/matches/")
        return {"label": "Go to Match Hub" if ur else "Watch Live", "kind": "live", "url": live_url}

    if state in ("completed","archived"):
        try:
            url = reverse("tournaments:detail", kwargs={"slug": getattr(t, "slug", "")}) + "?tab=standings"
        except Exception:
            url = f"/tournaments/{getattr(t,'slug','')}/?tab=standings"
        return {"label": "View results", "kind": "results", "url": url}

    return {"label": "Details", "kind": "details", "url": f"/tournaments/{getattr(t,'slug','')}/"}

# ---------- policy, rules, media ----------
def coin_policy_of(t):
    """
    Returns a safe string or None for coin/wallet policy pulled from the tournament or its settings.
    """
    return maybe_text(
        getattr(t, "coin_policy", None),
        getattr(getattr(t, "settings", None), "coin_policy", None),
        getattr(t, "wallet_policy", None),
    )

def rules_pdf_of(t) -> Tuple[Optional[str], Optional[str]]:
    """
    Finds a PDF url/name from several possible field names.
    """
    for field in ("rules_pdf", "rule_pdf", "rules", "rule"):
        f = getattr(t, field, None)
        if f:
            try:
                return getattr(f, "url", None), getattr(f, "name", "").split("/")[-1]
            except Exception:
                if isinstance(f, str):
                    return f, f.split("/")[-1]
    url = getattr(t, "rules_pdf_url", None)
    if isinstance(url, str) and url:
        return url, url.split("/")[-1]
    return None, None

def build_pdf_viewer_config(t, *, theme: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Returns a dict for initializing PDF.js in templates: {url, filename, theme, downloadable}
    """
    url, name = rules_pdf_of(t)
    if not url:
        return None
    theme = theme or "auto"  # templates can switch to 'dark'/'light'
    return {"url": url, "filename": name or "rules.pdf", "theme": theme, "downloadable": False}

# ---------- participants / standings loaders (best-effort) ----------
def load_participants(t) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        rel = None
        for name in ("registrations", "participants", "teams"):
            if hasattr(t, name):
                rel = getattr(t, name)
                break
        if rel and hasattr(rel, "all"):
            for p in rel.all()[:500]:
                out.append({
                    "name": first(getattr(p, "team_name", None), getattr(p, "player_name", None), str(p)),
                    "seed": getattr(p, "seed", None),
                    "status": getattr(p, "status", None),
                    "logo": getattr(p, "logo_url", None) or getattr(getattr(p, "team", None), "logo_url", None),
                    "captain": first(getattr(p, "captain_name", None), getattr(getattr(p, "captain", None), "name", None)),
                    "region": getattr(p, "region", None),
                    "record": getattr(p, "record", None),  # e.g., '12-4'
                })
    except Exception:
        pass
    return out

def load_standings(t) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        rows = getattr(t, "standings", None)
        if rows:
            for r in rows[:300]:
                if isinstance(r, dict):
                    out.append({"rank": r.get("rank"), "name": r.get("name"), "points": r.get("points")})
                else:
                    out.append({"rank": getattr(r, "rank", None), "name": getattr(r, "name", None), "points": getattr(r, "points", None)})
    except Exception:
        pass
    return out

# ---------- live / bracket helpers ----------
def live_stream_info(t) -> Dict[str, Any]:
    """
    Returns {'stream': url|None, 'status': 'live'|'offline'|'standby', 'viewers': int|None}
    """
    url = getattr(t, "live_stream_url", None)
    status = str(getattr(t, "live_status", "")).lower() or ("live" if url else "offline")
    viewers = getattr(t, "live_viewers", None)
    try:
        viewers = int(viewers) if viewers is not None else None
    except Exception:
        viewers = None
    return {"stream": url, "status": status, "viewers": viewers}

def bracket_url_of(t) -> Optional[str]:
    return first(getattr(t, "bracket_embed_url", None), getattr(t, "bracket_url", None))

# ---------- tabs builder (feature-aware) ----------
def build_tabs(*, participants, prize_pool, rules_text, extra_rules, rules_pdf_url, standings, bracket_url, live_info, coin_policy_text) -> List[str]:
    tabs: List[str] = ["overview", "info"]
    if participants: tabs.append("participants")
    if prize_pool or rules_text or extra_rules: tabs.append("prizes")
    if bracket_url: tabs.append("bracket")
    if standings:   tabs.append("standings")
    if live_info.get("stream") or live_info.get("status") == "live": tabs.append("live")
    if rules_text or extra_rules or rules_pdf_url: tabs.append("rules")
    if coin_policy_text: tabs.append("policy")
    tabs.append("support")
    return tabs

# ---------- expose a small pack of meta for the hero (game theming + countdown) ----------
def hero_meta_for(t) -> Dict[str, Any]:
    game_name = read_game(t)
    gslug = slugify_game(game_name)
    g = GAME_REGISTRY.get(gslug, {
        "name": game_name or "Tournament",
        "primary": "#8b5cf6",
        "glowA": "#06b6d4",
        "glowB": "#facc15",
        "icon": None,
        "card_image": None,
    })

    # Countdown: prefer check-in open → reg close → start
    chk_open = first(getattr(t, "check_in_open_at", None), getattr(getattr(t, "settings", None), "check_in_open_at", None))
    reg_close = getattr(t, "reg_close_at", None)
    starts_at = first(getattr(t, "starts_at", None), getattr(t, "start_at", None))
    cdown = countdown_to(first(chk_open, reg_close, starts_at))

    return {
        "game_slug": gslug,
        "game_name": g.get("name"),
        "theme": {"primary": g.get("primary"), "glowA": g.get("glowA"), "glowB": g.get("glowB")},
        "icons": {"game": g.get("icon")},
        "countdown": cdown,
        "tz_label": tz_label(),
    }

# ---------- single stable dc_* mapping for templates ----------
def dc_map(request, t: Any) -> Dict[str, Any]:
    """
    Returns a stable dict of fields used by templates/partials (no crashes on missing data).
    """
    title = read_title(t)
    game = read_game(t)
    fee_amt = read_fee_amount(t)
    prize_amt = read_prize_amount(t)
    fee_text = f"BDT {fmt_money(fee_amt)}" if fee_amt else "Free"
    prize_text = f"BDT {fmt_money(prize_amt)}" if prize_amt else None
    url = read_url(t)
    banner = banner_url(t)
    state = computed_state(t)
    reg_url = register_url(t)
    cta = next_cta(getattr(request, "user", None), t, state, fee_amt, reg_url)

    return {
        "title": title,
        "game": game,
        "fee_amount": fee_amt,
        "fee_text": fee_text,
        "prize_amount": prize_amt,
        "prize_text": prize_text,
        "url": url,
        "banner_url": banner,
        "status": status_for_card(t),
        "state": state,
        "register_url": reg_url,
        "cta": cta,
        "hero": hero_meta_for(t),
    }
