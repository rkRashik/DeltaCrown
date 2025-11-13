# apps/tournaments/games/__init__.py
"""
Game-specific logic modules for different tournament formats.

Modules:
- points: Battle Royale point calculators (FF, PUBG)
- draft: MOBA draft/ban validators (Dota2, MLBB)
- validators: Game-specific ID format validators
"""

from .points import calc_ff_points, calc_pubgm_points
from .draft import validate_dota2_draft, validate_mlbb_draft
from .validators import (
    validate_riot_id,
    validate_steam_id,
    validate_mlbb_uid_zone,
    validate_ea_id,
    validate_konami_id,
    validate_mobile_ign_uid
)

__all__ = [
    # BR Points
    'calc_ff_points',
    'calc_pubgm_points',
    # MOBA Draft
    'validate_dota2_draft',
    'validate_mlbb_draft',
    # ID Validators
    'validate_riot_id',
    'validate_steam_id',
    'validate_mlbb_uid_zone',
    'validate_ea_id',
    'validate_konami_id',
    'validate_mobile_ign_uid',
]
