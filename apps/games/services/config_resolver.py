"""
Game configuration resolver — single read path for match-flow config.

This module is the canonical resolution layer between the data stores
(``GameMapPool``, ``GameScoringRule``, ``MapPoolEntry``, ``GameMatchConfig``,
``VetoConfiguration``) and the run-time consumers (match room, lobby workflow,
TOC API). Consumers MUST go through here; direct queries against the underlying
tables are the bug we are eliminating.

Design contract
---------------
* **Two tiers per concern**: ``tournament override`` first, ``game default``
  second. Anything else is bug-prone shortcut.
* **No new models, no abstractions**. Just resolution helpers. Future games
  plug in by adding rows to ``GameMapPool`` / ``GameScoringRule`` etc.
* **Defensive against missing data**: if a game has no DB rows the resolver
  falls back to the legacy dict baked into this file (moved out of
  ``match_room.py`` so it lives in one place). The legacy dict is the
  emergency safety net — keep it minimal and grow data, not code.
* **Organizer customization is first-class**: any non-empty tournament-level
  override is preferred over game defaults.

Why this file lives in ``apps.games``: resolution depends on Game data and
the resolver is consumed by multiple apps. ``apps.tournaments`` already
imports ``apps.games`` (Game model) so the dependency direction is correct.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "resolve_map_pool",
    "resolve_map_pool_by_game_slug",
    "resolve_map_pool_meta",
    "resolve_game_branding",
    "resolve_lobby_options",
    "resolve_scoring_rule",
    "LEGACY_MAP_POOL_FALLBACKS",
]


# ── Legacy emergency fallback ───────────────────────────────────────────────
# Used only when both ``MapPoolEntry`` (tournament-level) and ``GameMapPool``
# (game-level) tables are empty for the queried game. Adding new games should
# happen via seeding ``GameMapPool`` rows — NOT by extending this dict.
LEGACY_MAP_POOL_FALLBACKS: Dict[str, List[str]] = {
    "valorant":  ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset"],
    "cs2":       ["Mirage", "Inferno", "Dust II", "Nuke", "Ancient", "Anubis", "Vertigo"],
    "r6siege":   ["Clubhouse", "Coastline", "Border", "Kafe", "Villa", "Chalet"],
    "r6":        ["Clubhouse", "Coastline", "Border", "Kafe", "Villa", "Chalet"],
}


def _normalize_slug(value: Any) -> str:
    return str(value or "").strip().lower()


def _tournament_from(obj: Any):
    """Accept a Tournament, a Match, or anything with .tournament; return the Tournament or None."""
    if obj is None:
        return None
    # Match has .tournament; Tournament has .game directly
    tournament = getattr(obj, "tournament", None)
    return tournament if tournament is not None else obj


# ── Map pool resolution ─────────────────────────────────────────────────────

def _tournament_map_pool(tournament) -> List[str]:
    """Tier 1 — organizer-customized pool stored as MapPoolEntry rows.

    Returns ``[]`` if the tournament has no GameMatchConfig, no MapPoolEntry
    rows, or all entries are inactive. Never raises.
    """
    if tournament is None:
        return []
    try:
        cfg = getattr(tournament, "game_match_config", None)
        if not cfg:
            return []
        rows = (
            cfg.map_pool
               .filter(is_active=True)
               .order_by("order", "map_name")
               .values_list("map_name", flat=True)
        )
        return [name for name in rows if str(name or "").strip()]
    except Exception as exc:
        logger.warning("resolve_map_pool: tournament tier failed tournament=%s err=%s",
                       getattr(tournament, "id", None), exc)
        return []


def _game_map_pool(game_slug: str) -> List[str]:
    """Tier 2 — game-level default pool stored as GameMapPool rows.

    Returns ``[]`` if the game has no rows or all are inactive. Never raises.
    """
    slug = _normalize_slug(game_slug)
    if not slug:
        return []
    try:
        from apps.games.models.map_pool import GameMapPool
        return GameMapPool.get_active_maps_by_slug(slug)
    except Exception as exc:
        logger.warning("resolve_map_pool: game tier failed slug=%s err=%s", slug, exc)
        return []


def _legacy_map_pool(game_slug: str) -> List[str]:
    """Tier 3 — emergency fallback dict.

    P5.7 — This path means neither a tournament-level ``MapPoolEntry`` nor a
    game-level ``GameMapPool`` row exists for this game. Admin action needed:

      1. Seed ``GameMapPool`` rows via Django admin → apps/games → GameMapPool
         (or run ``python manage.py seed_games`` if that command exists).
      2. Once seeded, this fallback is bypassed and the INFO log stops appearing.

    Remove condition: when all production games have ``GameMapPool`` rows seeded,
    this dict can be removed and the list replaced with ``return []``.

    LEGACY_MAP_POOL_FALLBACKS covers: valorant, cs2, r6siege, r6.
    Missing: mlbb, pubgm, freefire, efootball, codm, dota2, ea-fc, rocketleague.
    """
    slug = _normalize_slug(game_slug)
    maps = LEGACY_MAP_POOL_FALLBACKS.get(slug, [])
    if maps:
        logger.info(
            "resolve_map_pool: LEGACY fallback used for game_slug=%s "
            "(GameMapPool empty — seed via admin to remove this fallback). "
            "Removal condition: all games have GameMapPool rows seeded.",
            slug,
        )
    else:
        logger.debug(
            "resolve_map_pool: no fallback for game_slug=%s "
            "(not in LEGACY_MAP_POOL_FALLBACKS and GameMapPool empty)",
            slug,
        )
    return list(maps)


def resolve_map_pool(tournament_or_match: Any) -> List[str]:
    """Return the active map pool for a tournament's match flow.

    Resolution order:
      1. Tournament override — MapPoolEntry rows linked to the tournament's
         GameMatchConfig.
      2. Game default — active GameMapPool rows for the tournament's game.
      3. Legacy fallback dict (deprecated).

    Returns ``[]`` when nothing resolves — callers decide on a UX fallback
    (e.g. ``["Map 1", "Map 2", ...]`` placeholders) instead of this layer
    silently inventing data.
    """
    tournament = _tournament_from(tournament_or_match)
    pool = _tournament_map_pool(tournament)
    if pool:
        return pool

    game = getattr(tournament, "game", None) if tournament is not None else None
    game_slug = _normalize_slug(getattr(game, "slug", ""))
    pool = _game_map_pool(game_slug)
    if pool:
        return pool

    return _legacy_map_pool(game_slug)


def resolve_map_pool_by_game_slug(game_slug: str) -> List[str]:
    """Game-only resolution (no tournament context). For preview/admin paths.

    Skips the tournament tier — use ``resolve_map_pool(match_or_tournament)``
    whenever a tournament is available so organizer overrides take effect.
    """
    slug = _normalize_slug(game_slug)
    return _game_map_pool(slug) or _legacy_map_pool(slug)


# ── Rich map metadata (RP.F — premium UX integration) ──────────────────────

def _serialize_image(image_field: Any) -> str:
    """Render an Image/URL field to a usable URL string. Empty when missing."""
    if image_field is None:
        return ""
    # Django ImageField has .url; URLField is a string.
    try:
        url = getattr(image_field, "url", None)
        if url:
            return str(url)
    except (ValueError, AttributeError):
        # ImageField without a stored file raises ValueError on .url.
        pass
    if isinstance(image_field, str):
        return image_field
    return ""


def _tournament_map_pool_meta(tournament) -> List[Dict[str, str]]:
    """Tier 1 — tournament-level ``MapPoolEntry`` rows as rich dicts."""
    if tournament is None:
        return []
    try:
        cfg = getattr(tournament, "game_match_config", None)
        if not cfg:
            return []
        rows = (
            cfg.map_pool
               .filter(is_active=True)
               .order_by("order", "map_name")
        )
        out: List[Dict[str, str]] = []
        for row in rows:
            name = str(row.map_name or "").strip()
            if not name:
                continue
            out.append({
                "name": name,
                "code": str(getattr(row, "map_code", "") or "").strip(),
                "image_url": _serialize_image(getattr(row, "image", None)),
            })
        return out
    except Exception as exc:
        logger.warning("resolve_map_pool_meta: tournament tier failed err=%s", exc)
        return []


def _game_map_pool_meta(game_slug: str) -> List[Dict[str, str]]:
    """Tier 2 — game-level ``GameMapPool`` rows as rich dicts."""
    slug = _normalize_slug(game_slug)
    if not slug:
        return []
    try:
        from apps.games.models.map_pool import GameMapPool
        rows = (
            GameMapPool.objects
            .filter(game__slug=slug, is_active=True)
            .order_by("order", "map_name")
        )
        out: List[Dict[str, str]] = []
        for row in rows:
            name = str(row.map_name or "").strip()
            if not name:
                continue
            out.append({
                "name": name,
                "code": str(getattr(row, "map_code", "") or "").strip(),
                "image_url": _serialize_image(getattr(row, "image", None)),
            })
        return out
    except Exception as exc:
        logger.warning("resolve_map_pool_meta: game tier failed err=%s", exc)
        return []


def resolve_map_pool_meta(tournament_or_match: Any) -> List[Dict[str, str]]:
    """Return rich map metadata for premium UX rendering.

    Each dict carries ``{"name", "code", "image_url"}``. Resolution follows
    the same tier order as ``resolve_map_pool`` (tournament override → game
    default → legacy fallback name-only). Always returns a list; consumers
    on the FE iterate and render image-aware cards. The simpler
    ``resolve_map_pool`` is preserved for callers that only need names
    (BR scoring, leaderboard, etc.).
    """
    tournament = _tournament_from(tournament_or_match)
    meta = _tournament_map_pool_meta(tournament)
    if meta:
        return meta

    game = getattr(tournament, "game", None) if tournament is not None else None
    game_slug = _normalize_slug(getattr(game, "slug", ""))
    meta = _game_map_pool_meta(game_slug)
    if meta:
        return meta

    # Legacy fallback — name-only entries, no image_url.
    return [
        {"name": name, "code": "", "image_url": ""}
        for name in _legacy_map_pool(game_slug)
    ]


def resolve_lobby_options(tournament_or_match: Any) -> Dict[str, List[Dict[str, str]]]:
    """Return select-option lists for lobby credential fields.

    Lives on ``Game.tournament_config.extra_config['lobby_options']`` so an
    admin can edit per-game options without code changes. Shape:

        {
          "server_regions": [{"code": "...", "label": "..."}, ...],
          "game_modes":     [{"code": "...", "label": "..."}, ...]
        }

    Returns ``{}`` when nothing is configured — FE then falls back to plain
    text inputs. Never raises.
    """
    tournament = _tournament_from(tournament_or_match)
    game = getattr(tournament, "game", None) if tournament is not None else None
    if game is None:
        return {}
    try:
        cfg = getattr(game, "tournament_config", None)
        if not cfg:
            return {}
        extra = cfg.extra_config if isinstance(cfg.extra_config, dict) else {}
        raw = extra.get("lobby_options")
        if not isinstance(raw, dict):
            return {}
        # Normalize: each value must be a list of {code, label} dicts.
        out: Dict[str, List[Dict[str, str]]] = {}
        for key, items in raw.items():
            if not isinstance(items, list):
                continue
            cleaned: List[Dict[str, str]] = []
            for item in items:
                if isinstance(item, dict):
                    code = str(item.get("code") or "").strip()
                    label = str(item.get("label") or code).strip()
                    if code:
                        cleaned.append({"code": code, "label": label})
                elif isinstance(item, str) and item.strip():
                    val = item.strip()
                    cleaned.append({"code": val, "label": val})
            if cleaned:
                out[str(key)] = cleaned
        return out
    except Exception as exc:
        logger.warning("resolve_lobby_options failed err=%s", exc)
        return {}


def resolve_game_branding(tournament_or_match: Any) -> Dict[str, str]:
    """Return per-game branding for the FE.

    The ``Game`` model owns ``primary_color`` / ``accent_color`` / ``icon`` /
    ``logo`` already; this resolver returns a compact dict so the FE doesn't
    need to know the field names or handle missing-FK cases. Keys returned:

        slug, display_name, short_code, category,
        primary_color, secondary_color, accent_color,
        logo_url, icon_url, banner_url

    All keys are strings; empty string when missing. Single source for all
    match-room / TOC / HUB game branding consumption.
    """
    tournament = _tournament_from(tournament_or_match)
    game = getattr(tournament, "game", None) if tournament is not None else None
    if game is None:
        return {
            "slug": "", "display_name": "", "short_code": "", "category": "",
            "primary_color": "", "secondary_color": "", "accent_color": "",
            "logo_url": "", "icon_url": "", "banner_url": "",
        }
    return {
        "slug":            str(getattr(game, "slug", "") or "").strip(),
        "display_name":    str(getattr(game, "display_name", "") or "").strip(),
        "short_code":      str(getattr(game, "short_code", "") or "").strip(),
        "category":        str(getattr(game, "category", "") or "").strip(),
        "primary_color":   str(getattr(game, "primary_color", "") or "").strip(),
        "secondary_color": str(getattr(game, "secondary_color", "") or "").strip(),
        "accent_color":    str(getattr(game, "accent_color", "") or "").strip(),
        "logo_url":        _serialize_image(getattr(game, "logo", None)),
        "icon_url":        _serialize_image(getattr(game, "icon", None)),
        "banner_url":      _serialize_image(getattr(game, "banner", None)),
    }


# ── Scoring rule resolution ─────────────────────────────────────────────────

def resolve_scoring_rule(tournament_or_match: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Return ``(rule_type, config)`` for the active scoring rule, or ``None``.

    Resolution order:
      1. Tournament override — ``GameMatchConfig.scoring_rules`` when it
         carries a ``rule_type`` key.
      2. Game default — active ``GameScoringRule`` for the tournament's game,
         highest ``priority`` first.

    Returns ``None`` when nothing resolves. Callers default to win/loss.

    Note: the BR per-Group ``scoring_matrix`` JSON (used by
    ``BRScoringService``) is intentionally NOT consolidated here — it is
    scheduled to migrate in a later phase since it touches active leaderboard
    computation. Keep new BR scoring config in ``BRScoringMatrix`` so this
    resolver picks it up when consolidation lands.
    """
    tournament = _tournament_from(tournament_or_match)
    if tournament is None:
        return None

    try:
        cfg = getattr(tournament, "game_match_config", None)
        if cfg:
            rules_blob = cfg.scoring_rules if isinstance(cfg.scoring_rules, dict) else {}
            rule_type = str(rules_blob.get("rule_type") or "").strip()
            if rule_type:
                return rule_type, {k: v for k, v in rules_blob.items() if k != "rule_type"}
    except Exception as exc:
        logger.warning("resolve_scoring_rule: tournament tier failed tournament=%s err=%s",
                       getattr(tournament, "id", None), exc)

    game = getattr(tournament, "game", None)
    if game is None:
        return None
    try:
        from apps.games.models.rules import GameScoringRule
        rule = (
            GameScoringRule.objects
            .filter(game=game, is_active=True)
            .order_by("-priority")
            .first()
        )
        if rule:
            cfg_dict = rule.config if isinstance(rule.config, dict) else {}
            return rule.rule_type, dict(cfg_dict)
    except Exception as exc:
        logger.warning("resolve_scoring_rule: game tier failed game=%s err=%s",
                       getattr(game, "slug", None), exc)
    return None
