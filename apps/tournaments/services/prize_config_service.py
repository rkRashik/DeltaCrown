"""
Prize Configuration Service.

Owns the organizer-facing prize *configuration* layer, separate from existing
payout execution (PayoutService) and placement derivation (PlacementService).

Why a separate config layer:
  * Tournament model already has `prize_pool`, `prize_currency`,
    `prize_deltacoin`, `prize_distribution`. Those are the legacy "amount per
    placement" fields and can still be used as-is for plain percentage splits.
  * Modern UX wants per-placement labels ("Champion", "Runner Up", ...), a
    coin (DeltaCoin) split alongside fiat, and a list of "special awards"
    (MVP, Golden Boot, hardware drops, sponsor codes) that aren't tied to
    placement.
  * Persisting that config in `tournament.config['prizes']` JSONB avoids new
    tables for V1 while remaining cleanly migratable later.

Schema (config['prizes']):

    {
        "currency": "BDT",
        "fiat_pool": 50000,
        "coin_pool": 10000,
        "placements": [
            {"rank": 1, "title": "Champion",   "percent": 50, "fiat": 25000, "coins": 5000},
            {"rank": 2, "title": "Runner Up",  "percent": 30, "fiat": 15000, "coins": 3000},
            {"rank": 3, "title": "Third Place","percent": 15, "fiat":  7500, "coins": 1500},
            {"rank": 4, "title": "Semi-Final", "percent":  5, "fiat":  2500, "coins":  500}
        ],
        "special_awards": [
            {"id": "mvp", "title": "Tournament MVP", "description": "...",
             "type": "cash"|"hardware"|"digital", "icon": "medal",
             "fiat": 0, "coins": 2500, "reward_text": ""}
        ],
        "certificates_enabled": true,
        "updated_at": "2026-04-24T12:34:56Z"
    }

The service is intentionally thin: it normalises input, persists it, and
combines it with the live placement payload for read-side consumers.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.tournaments.models import Tournament
logger = logging.getLogger(__name__)


_DEFAULT_PLACEMENTS = [
    {'rank': 1, 'title': 'Champion',     'percent': 50, 'fiat': 0, 'coins': 0},
    {'rank': 2, 'title': 'Runner Up',    'percent': 30, 'fiat': 0, 'coins': 0},
    {'rank': 3, 'title': 'Third Place',  'percent': 15, 'fiat': 0, 'coins': 0},
    {'rank': 4, 'title': 'Semi-Finalist', 'percent': 5, 'fiat': 0, 'coins': 0},
]

_VALID_AWARD_TYPES = frozenset({'cash', 'hardware', 'digital'})


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f'{n}th'
    return f'{n}{ {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th") }'


def _to_int(value: Any, default: int = 0, *, minimum: int = 0) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, v)


def _to_decimal(value: Any, default: Decimal = Decimal('0')) -> Decimal:
    if value in (None, ''):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _slugify(value: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
    return s or 'award'


class PrizeConfigService:

    @classmethod
    def get_config(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Return the prize configuration (always serializable, never None).

        Falls back to a sensible default derived from the tournament's existing
        prize_pool / prize_currency / prize_deltacoin / prize_distribution
        legacy fields so brand-new tournaments don't show an empty panel.
        """
        config = tournament.config if isinstance(tournament.config, dict) else {}
        prizes = config.get('prizes') if isinstance(config.get('prizes'), dict) else None
        if prizes:
            return cls._normalize_for_read(prizes, tournament)
        return cls._derive_default(tournament)

    @classmethod
    def save_config(
        cls,
        tournament: Tournament,
        payload: Dict[str, Any],
        *,
        actor=None,
    ) -> Dict[str, Any]:
        """Validate + persist the prize configuration onto tournament.config."""
        normalized = cls._normalize_for_write(payload)
        config = tournament.config if isinstance(tournament.config, dict) else {}
        config['prizes'] = normalized
        tournament.config = config

        # Mirror the gross fiat pool / coin pool to the legacy Tournament
        # fields so other surfaces (HUB legacy display, admin) stay in sync.
        try:
            tournament.prize_pool = _to_decimal(normalized.get('fiat_pool'))
            tournament.prize_deltacoin = _to_int(normalized.get('coin_pool'))
            currency = (normalized.get('currency') or 'BDT')[:10].upper()
            tournament.prize_currency = currency
            tournament.save(update_fields=[
                'config', 'prize_pool', 'prize_deltacoin', 'prize_currency',
            ])
        except Exception:
            tournament.save(update_fields=['config'])

        logger.info(
            'Prize config updated for tournament %s by %s',
            getattr(tournament, 'slug', tournament.id),
            getattr(actor, 'username', 'system'),
        )
        return cls.get_config(tournament)

    @classmethod
    def public_payload(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Public/HUB-compatible payload: prize config merged with live placements.

        Delegates to TournamentRewardsReadModel so public, HUB, and TOC
        surfaces share one read-side truth. Kept here for legacy callers.
        """
        from apps.tournaments.services.rewards_read_model import (
            TournamentRewardsReadModel,
        )
        return TournamentRewardsReadModel.public_payload(tournament)

    # ── internals ───────────────────────────────────────────────────────

    @classmethod
    def _derive_default(cls, tournament: Tournament) -> Dict[str, Any]:
        currency = (getattr(tournament, 'prize_currency', None) or 'BDT')[:10].upper()
        fiat_pool = int(_to_decimal(getattr(tournament, 'prize_pool', 0)))
        coin_pool = int(getattr(tournament, 'prize_deltacoin', 0) or 0)

        legacy_dist = getattr(tournament, 'prize_distribution', None) or {}
        placements = []
        if isinstance(legacy_dist, dict) and legacy_dist:
            for raw_key, raw_value in legacy_dist.items():
                rank = _to_int(re.sub(r'\D', '', str(raw_key) or '0'), 0)
                if rank <= 0:
                    continue
                fiat = int(_to_decimal(raw_value))
                placements.append({
                    'rank': rank,
                    'title': _ordinal(rank),
                    'percent': 0 if not fiat_pool else round((fiat / fiat_pool) * 100),
                    'fiat': fiat,
                    'coins': 0,
                })
            placements.sort(key=lambda p: p['rank'])
        if not placements:
            placements = [dict(p) for p in _DEFAULT_PLACEMENTS]
            for p in placements:
                p['fiat'] = round(fiat_pool * (p['percent'] / 100))
                p['coins'] = round(coin_pool * (p['percent'] / 100))

        return {
            'currency': currency,
            'fiat_pool': fiat_pool,
            'coin_pool': coin_pool,
            'placements': placements,
            'special_awards': [],
            'certificates_enabled': bool(
                getattr(tournament, 'enable_certificates', True)
            ),
            'updated_at': None,
        }

    @classmethod
    def _normalize_for_write(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        currency = (str(payload.get('currency') or 'BDT'))[:10].upper()
        fiat_pool = _to_int(payload.get('fiat_pool'), 0)
        coin_pool = _to_int(payload.get('coin_pool'), 0)

        raw_placements = payload.get('placements') or []
        placements: List[Dict[str, Any]] = []
        seen_ranks = set()
        for raw in raw_placements:
            if not isinstance(raw, dict):
                continue
            rank = _to_int(raw.get('rank'), 0)
            if rank <= 0 or rank in seen_ranks:
                continue
            seen_ranks.add(rank)
            title = str(raw.get('title') or _ordinal(rank))[:80]
            percent = max(0, min(100, _to_int(raw.get('percent'), 0)))
            fiat = _to_int(raw.get('fiat'), 0)
            coins = _to_int(raw.get('coins'), 0)
            placements.append({
                'rank': rank,
                'title': title,
                'percent': percent,
                'fiat': fiat,
                'coins': coins,
            })
        placements.sort(key=lambda p: p['rank'])

        raw_awards = payload.get('special_awards') or []
        special_awards: List[Dict[str, Any]] = []
        for raw in raw_awards:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get('title') or '').strip()[:120]
            if not title:
                continue
            atype = str(raw.get('type') or 'cash').lower()
            if atype not in _VALID_AWARD_TYPES:
                atype = 'cash'
            aid = str(raw.get('id') or '').strip()[:60] or _slugify(title)
            # Recipient fields — manual assignment by organizer.
            recipient_id = _to_int(raw.get('recipient_id'), 0) or None
            recipient_name = str(raw.get('recipient_name') or '').strip()[:120]
            special_awards.append({
                'id': aid,
                'title': title,
                'description': str(raw.get('description') or '').strip()[:400],
                'type': atype,
                'icon': str(raw.get('icon') or 'medal')[:40],
                'fiat': _to_int(raw.get('fiat'), 0),
                'coins': _to_int(raw.get('coins'), 0),
                'reward_text': str(raw.get('reward_text') or '').strip()[:240],
                'recipient_id': recipient_id,
                'recipient_name': recipient_name,
            })

        return {
            'currency': currency,
            'fiat_pool': fiat_pool,
            'coin_pool': coin_pool,
            'placements': placements,
            'special_awards': special_awards,
            'certificates_enabled': bool(payload.get('certificates_enabled', True)),
            'updated_at': timezone.now().isoformat(),
        }

    @classmethod
    def _normalize_for_read(cls, prizes: Dict[str, Any], tournament: Tournament) -> Dict[str, Any]:
        # Defensive normalisation in case persisted shape drifts.
        out = dict(prizes)
        out['currency'] = (str(out.get('currency') or 'BDT'))[:10].upper()
        out['fiat_pool'] = _to_int(out.get('fiat_pool'), 0)
        out['coin_pool'] = _to_int(out.get('coin_pool'), 0)
        out['placements'] = [
            {
                'rank': _to_int(p.get('rank'), 0, minimum=1),
                'title': str(p.get('title') or '').strip()[:80] or _ordinal(_to_int(p.get('rank'), 0)),
                'percent': max(0, min(100, _to_int(p.get('percent'), 0))),
                'fiat': _to_int(p.get('fiat'), 0),
                'coins': _to_int(p.get('coins'), 0),
            }
            for p in (out.get('placements') or []) if isinstance(p, dict)
        ]
        awards: List[Dict[str, Any]] = []
        for raw in out.get('special_awards') or []:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get('title') or '').strip()[:120]
            if not title:
                continue
            atype = str(raw.get('type') or 'cash').lower()
            if atype not in _VALID_AWARD_TYPES:
                atype = 'cash'
            recipient_id = _to_int(raw.get('recipient_id'), 0) or None
            recipient_name = str(raw.get('recipient_name') or '').strip()[:120]
            awards.append({
                'id': str(raw.get('id') or '').strip()[:60] or _slugify(title),
                'title': title,
                'description': str(raw.get('description') or '').strip()[:400],
                'type': atype,
                'icon': str(raw.get('icon') or 'medal')[:40],
                'fiat': _to_int(raw.get('fiat'), 0),
                'coins': _to_int(raw.get('coins'), 0),
                'reward_text': str(raw.get('reward_text') or '').strip()[:240],
                'recipient_id': recipient_id,
                'recipient_name': recipient_name,
                'awaiting_recipient': not bool(recipient_id or recipient_name),
            })
        out['special_awards'] = awards
        out['certificates_enabled'] = bool(out.get('certificates_enabled', True))
        return out


__all__ = ['PrizeConfigService']
