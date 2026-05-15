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
    """Tier 3 — emergency fallback dict. Should be hit rarely; logs when used."""
    slug = _normalize_slug(game_slug)
    maps = LEGACY_MAP_POOL_FALLBACKS.get(slug, [])
    if maps:
        logger.info("resolve_map_pool: using LEGACY fallback for game_slug=%s — "
                    "seed GameMapPool to remove this dependency", slug)
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
