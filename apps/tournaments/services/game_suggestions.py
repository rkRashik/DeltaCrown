"""
Game-specific tournament creation suggestions.

Provides intelligent defaults and contextual tips for the tournament
creation wizard. Combines hardcoded esports domain knowledge with
dynamic data from Game, GameRosterConfig, and GameTournamentConfig models.

Used by: apps.tournaments.views.create.TournamentCreatePageView
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Per-Game Suggestions (hardcoded esports domain knowledge)
# ─────────────────────────────────────────────────────────────────────

GAME_TIPS: Dict[str, Dict[str, Any]] = {
    'valorant': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 Tactical FPS',
        'tips': [
            'Best with 8, 16, or 32 teams for clean brackets',
            'Enable map veto for competitive integrity',
            'BO3 for playoffs, BO1 for group stage',
        ],
        'rule_template': (
            '• Standard Valorant competitive rules apply\n'
            '• Map pool: All active competitive maps\n'
            '• Overtime: Standard (first to 13, OT MR3)\n'
            '• Coaching allowed during tactical timeouts only\n'
            '• All agents allowed unless specified'
        ),
    },
    'cs2': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 Tactical FPS',
        'tips': [
            'MR12 format recommended for competitive play',
            'Enable knife round for side selection',
            'Anti-cheat verification recommended for online events',
        ],
        'rule_template': (
            '• Standard CS2 competitive ruleset\n'
            '• Map pool: Active duty maps\n'
            '• MR12 format, overtime MR3\n'
            '• VAC / FACEIT AC required\n'
            '• Knife round for side selection'
        ),
    },
    'pubgm': {
        'recommended_format': 'round_robin',
        'recommended_participation': 'team',
        'recommended_platform': 'mobile',
        'recommended_sizes': [16, 20, 24],
        'match_format_label': 'Multi-match series (3-5 maps)',
        'subtitle': '4-Man Squad Battle Royale',
        'tips': [
            'Use placement + kill scoring (PMPL format)',
            '16-20 teams per lobby for best experience',
            'Multiple matches across 2-3 days recommended',
        ],
        'rule_template': (
            '• PUBG Mobile competitive rules\n'
            '• Scoring: PMPL format (placement + kills)\n'
            '• Emulator players must declare\n'
            '• UID verification required\n'
            '• Map rotation: Erangel, Miramar, Sanhok'
        ),
    },
    'mlbb': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'mobile',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 MOBA',
        'tips': [
            'Draft pick mode for competitive integrity',
            'BO3 recommended for elimination matches',
            'Consider banning newly released heroes',
        ],
        'rule_template': (
            '• Draft pick mode required\n'
            '• All heroes allowed unless specified\n'
            '• Pause limit: 2 per team per match\n'
            '• Remake if disconnect before 3:00\n'
            '• No win-trading or intentional feeding'
        ),
    },
    'ea-fc': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'solo',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16, 32, 64],
        'match_format_label': 'BO1 (Finals: BO3)',
        'subtitle': '1v1 Sports Simulation',
        'tips': [
            '1v1 solo format works best',
            'Specify allowed game modes (FUT/Kickoff/Online Seasons)',
            'Half length: 6 minutes standard',
        ],
        'rule_template': (
            '• Online Friendlies mode\n'
            '• Half length: 6 minutes\n'
            '• Any team/formation allowed\n'
            '• Legacy defending: OFF\n'
            '• No custom tactics restrictions'
        ),
    },
    'efootball': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'solo',
        'recommended_platform': 'mobile',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO1 (Finals: BO3)',
        'subtitle': '1v1 Sports Simulation',
        'tips': [
            'Similar setup to EA FC',
            'Specify Dream Team or standard teams',
            'Match time: 10 minutes recommended',
        ],
        'rule_template': (
            '• Standard match settings\n'
            '• Match time: 10 minutes\n'
            '• Any team allowed\n'
            '• No lag-switching or exploits'
        ),
    },
    'freefire': {
        'recommended_format': 'round_robin',
        'recommended_participation': 'team',
        'recommended_platform': 'mobile',
        'recommended_sizes': [12, 16, 24],
        'match_format_label': 'Multi-match series',
        'subtitle': '4-Man Squad Battle Royale',
        'tips': [
            'Similar to PUBG Mobile format',
            'Placement + kill scoring recommended',
            'Custom room: Squad mode, Bermuda/Kalahari',
        ],
        'rule_template': (
            '• Free Fire competitive rules\n'
            '• Scoring: placement + kills\n'
            '• Custom room settings: Squad mode\n'
            '• All characters allowed\n'
            '• Pet skills: Allowed unless restricted'
        ),
    },
    'codm': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'mobile',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 Tactical FPS (Mobile)',
        'tips': [
            'Search & Destroy mode for competitive',
            'Hardpoint also popular for variety',
            'Consider banning certain operators/equipment',
        ],
        'rule_template': (
            '• S&D competitive rules\n'
            '• Map pool: All ranked S&D maps\n'
            '• Scorestreak limit: Optional\n'
            '• Operator skills: Allowed unless restricted'
        ),
    },
    'dota2': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 MOBA',
        'tips': [
            "Captain's Mode for competitive",
            'BO3 minimum for playoffs',
            'Consider regional server selection',
        ],
        'rule_template': (
            "• Captain's Mode\n"
            '• All heroes allowed\n'
            '• Pause limit: 3 per team\n'
            '• Lobby: Tournament mode\n'
            '• Server: AUTO or specified region'
        ),
    },
    'rocketleague': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16, 32],
        'match_format_label': 'BO5 (Finals: BO7)',
        'subtitle': '3v3 Vehicular Sports',
        'tips': [
            '3v3 standard format',
            'BO5 is the competitive standard',
            'Private match with no mutators',
        ],
        'rule_template': (
            '• 3v3 Standard Soccar\n'
            '• 5 minute matches\n'
            '• Unlimited boost\n'
            '• No mutators\n'
            '• Overtime: Unlimited (first goal wins)'
        ),
    },
    'r6siege': {
        'recommended_format': 'single_elimination',
        'recommended_participation': 'team',
        'recommended_platform': 'pc',
        'recommended_sizes': [8, 16],
        'match_format_label': 'BO3 (Finals: BO5)',
        'subtitle': '5v5 Tactical FPS',
        'tips': [
            'Competitive map pool only',
            'Operator ban phase recommended',
            '6th pick enabled for competitive integrity',
        ],
        'rule_template': (
            '• Competitive rules\n'
            '• 7 rounds per half\n'
            '• Operator bans: 1 ATK + 1 DEF per team\n'
            '• 6th pick enabled\n'
            '• Map pool: Competitive rotation only'
        ),
    },
}


def get_game_suggestion(game_slug: str) -> Optional[Dict[str, Any]]:
    """
    Get suggestion data for a specific game.

    Args:
        game_slug: Game slug (e.g., 'valorant', 'pubgm')

    Returns:
        Dict with recommendation fields, or None if not found.
    """
    slug = (game_slug or '').lower().strip()
    return GAME_TIPS.get(slug)


def get_all_game_suggestions() -> Dict[str, Dict[str, Any]]:
    """Return the full game tips dictionary for embedding in template context."""
    return GAME_TIPS


def build_game_intelligence_payload(games_queryset) -> list:
    """
    Build a JSON-serialisable list combining DB model data with
    hardcoded game tips for the creation wizard frontend.

    Args:
        games_queryset: QuerySet of active Game objects.

    Returns:
        List of dicts ready for JSON serialisation.
    """
    payload = []
    for game in games_queryset:
        roster = getattr(game, 'roster_config', None)
        tourney_cfg = getattr(game, 'tournament_config', None)
        tips = GAME_TIPS.get(game.slug, {})

        entry = {
            # Identity
            'id': game.id,
            'name': game.name,
            'display_name': game.display_name,
            'slug': game.slug,
            'short_code': game.short_code,

            # Classification
            'category': game.category,
            'category_label': dict(game.CATEGORY_CHOICES).get(game.category, game.category),
            'game_type': game.game_type,
            'platforms': game.platforms or [],

            # Branding
            'primary_color': game.primary_color or '#7c3aed',
            'secondary_color': game.secondary_color or '#1e1b4b',
            'accent_color': game.accent_color or '',
            'primary_color_rgb': game.primary_color_rgb,
            'icon_url': game.icon.url if game.icon else '',
            'logo_url': game.logo.url if game.logo else '',
            'card_image_url': game.card_image.url if game.card_image else '',

            # Roster intelligence
            'team_size_display': roster.get_team_size_display() if roster else '5v5',
            'max_team_size': roster.max_team_size if roster else 5,
            'min_team_size': roster.min_team_size if roster else 1,
            'max_substitutes': roster.max_substitutes if roster else 2,

            # Tournament config intelligence
            'supported_formats': {
                'single_elimination': tourney_cfg.supports_single_elimination if tourney_cfg else True,
                'double_elimination': tourney_cfg.supports_double_elimination if tourney_cfg else True,
                'round_robin': tourney_cfg.supports_round_robin if tourney_cfg else True,
                'swiss': tourney_cfg.supports_swiss if tourney_cfg else False,
                'group_playoff': tourney_cfg.supports_group_stage if tourney_cfg else True,
            },
            'default_match_format': tourney_cfg.default_match_format if tourney_cfg else 'BO3',
            'scoring_type': tourney_cfg.default_scoring_type if tourney_cfg else 'WIN_LOSS',
            'allow_draws': tourney_cfg.allow_draws if tourney_cfg else False,

            # Smart suggestions (hardcoded domain knowledge)
            'recommended_format': tips.get('recommended_format', 'single_elimination'),
            'recommended_participation': tips.get('recommended_participation', 'team'),
            'recommended_platform': tips.get('recommended_platform', 'pc'),
            'recommended_sizes': tips.get('recommended_sizes', [8, 16, 32]),
            'match_format_label': tips.get('match_format_label', 'BO3'),
            'subtitle': tips.get('subtitle', ''),
            'tips': tips.get('tips', []),
            'rule_template': tips.get('rule_template', ''),
        }
        payload.append(entry)

    return payload
