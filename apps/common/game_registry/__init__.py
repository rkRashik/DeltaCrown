"""
DeltaCrown Game Registry - REMOVED
===================================

⛔ **REMOVED IN PHASE 4 - DECEMBER 2025** ⛔

This module has been REMOVED and replaced by the centralized games app.
All game configuration is now in `apps.games`.

**MIGRATION (REQUIRED):**
```python
# OLD (DO NOT USE):
from apps.common.game_registry import get_game, get_choices, normalize_slug

# NEW (USE THIS):
from apps.games.services import game_service
from apps.games.models import Game

# Get a game
game = game_service.get_game('valorant')

# Get game choices for forms
choices = game_service.get_choices()

# Normalize game slug
slug = game_service.normalize_slug('PUBGM')  # Returns 'pubg-mobile'

# Get roster limits
limits = game_service.get_roster_limits(game)

# Get tournament config
config = game_service.get_tournament_config(game)

# Get tiebreakers
tiebreakers = game_service.get_tiebreakers(game)

# Get player identity fields
identity_configs = game_service.get_identity_validation_rules(game)
```

**MIGRATION GUIDE:**
See Documents/Modify_TeamApp_&_GameApp/PHASE4_IMPLEMENTATION_SUMMARY.md

Created: November 2025
Deprecated: December 2025 (Phase 3)
Removed: December 2025 (Phase 4)
"""

# Hard error on any import attempt
raise RuntimeError(
    "apps.common.game_registry has been removed. "
    "Use apps.games.services.game_service instead. "
    "See Documents/Modify_TeamApp_&_GameApp/PHASE4_IMPLEMENTATION_SUMMARY.md for migration guide."
)
