"""
P6 — Expand apps/games seed data to all actively-supported games.

Seeds (idempotent via get_or_create):
  1. GameMapPool     — maps/battlegrounds/arenas for each game
  2. GameScoringRule — archetype-level scoring defaults
  3. VetoConfiguration — BO1/BO3/BO5 map veto templates for FPS games
  4. GameTournamentConfig.extra_config['lobby_options'] — server/region
     and game mode select lists for each game

Data sources and uncertainty notes
------------------------------------
Maps marked (✓ verified) come from official game wikis/patch notes as of
the knowledge cutoff. Maps marked (🔷 conservative) are known maps that may
have been rotated out of the active competitive pool. Admins can toggle
is_active per-tournament via the Game admin inline or tournament map pool
override. Do NOT rely on these entries as a definitive competitive schedule.

Removal condition: Once all production games have admin-uploaded images and
verified map lists, remove the LEGACY_MAP_POOL_FALLBACKS dict from
apps/games/services/config_resolver.py.
"""

from __future__ import annotations

from django.db import migrations


# ── Maps ────────────────────────────────────────────────────────────────────

# PUBG Mobile battlegrounds (✓ active competitive + notable historical).
PUBGM_MAPS = [
    {"code": "erangel",   "name": "Erangel",   "active": True,  "comp": True,  "order": 1},
    {"code": "miramar",   "name": "Miramar",   "active": True,  "comp": True,  "order": 2},
    {"code": "sanhok",    "name": "Sanhok",    "active": True,  "comp": True,  "order": 3},
    {"code": "vikendi",   "name": "Vikendi",   "active": True,  "comp": True,  "order": 4},
    {"code": "livik",     "name": "Livik",     "active": True,  "comp": True,  "order": 5},
    {"code": "nusa",      "name": "Nusa",      "active": True,  "comp": False, "order": 6},
    {"code": "rondo",     "name": "Rondo",     "active": True,  "comp": False, "order": 7},
]

# FreeFire arenas (✓ active).
FREEFIRE_MAPS = [
    {"code": "bermuda",    "name": "Bermuda",    "active": True, "comp": True,  "order": 1},
    {"code": "kalahari",   "name": "Kalahari",   "active": True, "comp": True,  "order": 2},
    {"code": "purgatory",  "name": "Purgatory",  "active": True, "comp": True,  "order": 3},
    {"code": "alpine",     "name": "Alpine",     "active": True, "comp": True,  "order": 4},
    {"code": "vortex",    "name": "Vortex Island","active": True, "comp": False, "order": 5},
]

# CoD Mobile competitive maps — Standard Hardpoint/SND pool.
CODM_MAPS = [
    {"code": "scrapyard",     "name": "Scrapyard",     "active": True, "comp": True,  "order": 1},
    {"code": "firing-range",  "name": "Firing Range",  "active": True, "comp": True,  "order": 2},
    {"code": "summit",        "name": "Summit",         "active": True, "comp": True,  "order": 3},
    {"code": "cage",          "name": "Cage",           "active": True, "comp": True,  "order": 4},
    {"code": "highrise",      "name": "Highrise",       "active": True, "comp": True,  "order": 5},
    {"code": "terminal",      "name": "Terminal",       "active": True, "comp": True,  "order": 6},
    {"code": "nuketown",      "name": "Nuketown",       "active": False, "comp": True, "order": 7},
]

# MLBB — no traditional map pool (single land / arena). Seed placeholder.
MLBB_MAPS = [
    {"code": "land-of-dawn", "name": "Land of Dawn", "active": True, "comp": True, "order": 1},
]

# eFootball / EA-FC / Rocket League — no spatial maps; omit GameMapPool.
# (The map concept doesn't apply to sports simulations. Seed 0 entries.)

MAPS_BY_SLUG = {
    "pubgm":    PUBGM_MAPS,
    "freefire": FREEFIRE_MAPS,
    "codm":     CODM_MAPS,
    "mlbb":     MLBB_MAPS,
}

# ── Lobby options ────────────────────────────────────────────────────────────

LOBBY_OPTIONS_BY_SLUG = {
    "pubgm": {
        "server_regions": [
            {"code": "ap-south-east", "label": "Asia Pacific — South East"},
            {"code": "ap-south",      "label": "Asia Pacific — South"},
            {"code": "asia-east",     "label": "Asia East"},
            {"code": "eu-west",       "label": "EU West"},
            {"code": "na-east",       "label": "NA East"},
        ],
        "game_modes": [
            {"code": "classic",  "label": "Classic (Squad/Duo/Solo)"},
            {"code": "tdm",      "label": "Team Deathmatch"},
            {"code": "custom",   "label": "Custom Room"},
        ],
    },
    "freefire": {
        "server_regions": [
            {"code": "ap-south-east", "label": "Asia Pacific — South East"},
            {"code": "ap-south",      "label": "Asia Pacific — South"},
            {"code": "mena",          "label": "Middle East & North Africa"},
            {"code": "eu-west",       "label": "EU West"},
            {"code": "latam",         "label": "Latin America"},
        ],
        "game_modes": [
            {"code": "battle-royale", "label": "Battle Royale"},
            {"code": "clash-squad",   "label": "Clash Squad"},
            {"code": "custom",        "label": "Custom Room"},
        ],
    },
    "efootball": {
        "server_regions": [],  # Peer-to-peer; no distinct server regions
        "game_modes": [
            {"code": "exhibition",  "label": "Exhibition (Competitive)"},
            {"code": "league",      "label": "League Match"},
            {"code": "custom",      "label": "Custom Match"},
        ],
    },
    "ea-fc": {
        "server_regions": [],
        "game_modes": [
            {"code": "ko-match",   "label": "KO Match (Competitive)"},
            {"code": "league",     "label": "League Season"},
            {"code": "custom",     "label": "Custom Match"},
        ],
    },
    "mlbb": {
        "server_regions": [
            {"code": "ap-south-east", "label": "Asia Pacific — South East"},
            {"code": "ap-south",      "label": "Asia Pacific — South"},
        ],
        "game_modes": [
            {"code": "classic",  "label": "Classic Mode"},
            {"code": "ranked",   "label": "Ranked Match"},
            {"code": "custom",   "label": "Custom Game"},
        ],
    },
    "codm": {
        "server_regions": [
            {"code": "ap-south-east", "label": "Asia Pacific — South East"},
            {"code": "ap-south",      "label": "Asia Pacific — South"},
            {"code": "na-east",       "label": "NA East"},
            {"code": "eu-west",       "label": "EU West"},
        ],
        "game_modes": [
            {"code": "hardpoint",  "label": "Hardpoint"},
            {"code": "snd",        "label": "Search & Destroy"},
            {"code": "domination", "label": "Domination"},
            {"code": "custom",     "label": "Custom Room"},
        ],
    },
    "r6siege": {
        "server_regions": [
            {"code": "ap-south",  "label": "Asia Pacific — South"},
            {"code": "eu-west",   "label": "EU West"},
            {"code": "na-east",   "label": "NA East"},
        ],
        "game_modes": [
            {"code": "ranked",   "label": "Ranked (Bomb)"},
            {"code": "custom",   "label": "Custom Match"},
        ],
    },
    "dota2": {
        "server_regions": [
            {"code": "sea",    "label": "South East Asia"},
            {"code": "europe", "label": "Europe West"},
            {"code": "us-east","label": "US East"},
        ],
        "game_modes": [
            {"code": "captains-mode", "label": "Captain's Mode (CM)"},
            {"code": "all-pick",      "label": "All Pick"},
            {"code": "custom",        "label": "Lobby Game"},
        ],
    },
}

# ── Scoring rules ─────────────────────────────────────────────────────────────

SCORING_RULES = [
    # Tactical FPS — win/loss per map; match won by map count.
    {
        "slug": "valorant", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "Valorant competitive — win/loss per match. Win determined by round count (13 rounds needed for regulation, OT rules apply).",
        "config": {"rounds_to_win": 13, "overtime_rounds": 3, "max_rounds": 25},
    },
    {
        "slug": "cs2", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "CS2 — win/loss per map. First to 13 rounds wins map.",
        "config": {"rounds_to_win": 13, "overtime_rounds": 3, "max_rounds": 30},
    },
    {
        "slug": "codm", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "CoD Mobile competitive — win/loss per match. Mode-specific round counts.",
        "config": {"rounds_to_win": 3, "points_based": False},
    },
    {
        "slug": "r6siege", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "Rainbow Six Siege — win/loss per round. First to 6 wins (OT if tied 5-5).",
        "config": {"rounds_to_win": 6, "overtime": True},
    },
    # MOBA — win/loss (destroy enemy base).
    {
        "slug": "mlbb", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "Mobile Legends: Bang Bang — win/loss. Objective: destroy enemy base.",
        "config": {},
    },
    {
        "slug": "dota2", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "Dota 2 — win/loss per game. Objective: destroy Ancient.",
        "config": {},
    },
    # Sports — aggregate score.
    {
        "slug": "efootball", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "eFootball — win/loss by final score. Goals determine winner; PK tiebreaker if applicable.",
        "config": {"overtime": True, "penalties": True},
    },
    {
        "slug": "ea-fc", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "EA Sports FC — win/loss by final score.",
        "config": {"overtime": True, "penalties": True},
    },
    {
        "slug": "rocketleague", "rule_type": "win_loss", "priority": 10, "is_active": True,
        "description": "Rocket League — win/loss by final score. Overtime until goal scored.",
        "config": {"overtime": True},
    },
    # Battle Royale — placement + kill points.
    {
        "slug": "pubgm", "rule_type": "placement_order", "priority": 10, "is_active": True,
        "description": "PUBG Mobile — placement points + kill points. Tournament organizer configures matrix via BRScoringMatrix.",
        "config": {
            "placement_points": {1: 15, 2: 12, 3: 10, 4: 8, 5: 6, 6: 4, 7: 2, 8: 1},
            "kill_points": 1,
            "note": "Default PMCO-style matrix. Override via BRScoringMatrix in TOC Settings.",
        },
    },
    {
        "slug": "freefire", "rule_type": "placement_order", "priority": 10, "is_active": True,
        "description": "FreeFire — placement + kill points. FFWS-style default matrix.",
        "config": {
            "placement_points": {1: 12, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1},
            "kill_points": 1,
            "note": "Default FFWS-style matrix. Override via BRScoringMatrix in TOC Settings.",
        },
    },
]

# ── Veto configurations ──────────────────────────────────────────────────────

VETO_CONFIGS = [
    # Valorant BO1 — standard competitive veto.
    {
        "game_slug": "valorant", "name": "BO1 Standard", "domain": "map",
        "time_per_action_seconds": 30, "auto_random_on_timeout": True,
        "pool": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset", "Abyss"],
        # Ban-Ban-Ban-Ban-Pick: side1 bans, side2 bans, side1 bans, side2 bans, side1 picks
        "sequence": [
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "pick", "count": 1},
        ],
    },
    # Valorant BO3 — standard competitive veto (picks = games 1 & 2; decider = remaining).
    {
        "game_slug": "valorant", "name": "BO3 Standard", "domain": "map",
        "time_per_action_seconds": 30, "auto_random_on_timeout": True,
        "pool": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset", "Abyss"],
        "sequence": [
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "pick", "count": 1},
            {"team": "B", "action": "pick", "count": 1},
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            # Decider (game 3) = remaining map after above.
        ],
    },
    # Valorant BO5 — 3 picks + 2 bans each + decider.
    # 🔷 conservative: BO5 format varies; this is a common VCT-style template.
    {
        "game_slug": "valorant", "name": "BO5 Standard", "domain": "map",
        "time_per_action_seconds": 30, "auto_random_on_timeout": True,
        "pool": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset", "Abyss"],
        "sequence": [
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "pick", "count": 1},  # game 1
            {"team": "B", "action": "pick", "count": 1},  # game 2
            {"team": "A", "action": "pick", "count": 1},  # game 3
            {"team": "B", "action": "pick", "count": 1},  # game 4
            # Decider (game 5) = remaining after bans.
        ],
    },
    # CS2 BO1.
    {
        "game_slug": "cs2", "name": "BO1 Standard", "domain": "map",
        "time_per_action_seconds": 30, "auto_random_on_timeout": True,
        "pool": ["Mirage", "Inferno", "Dust 2", "Nuke", "Ancient", "Anubis", "Vertigo"],
        "sequence": [
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "pick", "count": 1},
        ],
    },
    # CS2 BO3.
    {
        "game_slug": "cs2", "name": "BO3 Standard", "domain": "map",
        "time_per_action_seconds": 30, "auto_random_on_timeout": True,
        "pool": ["Mirage", "Inferno", "Dust 2", "Nuke", "Ancient", "Anubis", "Vertigo"],
        "sequence": [
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
            {"team": "A", "action": "pick", "count": 1},
            {"team": "B", "action": "pick", "count": 1},
            {"team": "A", "action": "ban",  "count": 1},
            {"team": "B", "action": "ban",  "count": 1},
        ],
    },
]


# ── Data functions ─────────────────────────────────────────────────────────────

def seed_maps(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMapPool = apps.get_model("games", "GameMapPool")
    for slug, maps in MAPS_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        for m in maps:
            GameMapPool.objects.get_or_create(
                game=game, map_code=m["code"],
                defaults={"map_name": m["name"], "is_active": m["active"],
                          "is_competitive": m["comp"], "order": m["order"]},
            )


def seed_lobby_options(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameTournamentConfig = apps.get_model("games", "GameTournamentConfig")
    for slug, options in LOBBY_OPTIONS_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        # Skip games already seeded by 0009_seed_lobby_options.
        cfg, _ = GameTournamentConfig.objects.get_or_create(game=game)
        extra = cfg.extra_config if isinstance(cfg.extra_config, dict) else {}
        existing = extra.get("lobby_options")
        if isinstance(existing, dict) and existing:
            continue  # admin may have customised — don't overwrite
        extra["lobby_options"] = options
        cfg.extra_config = extra
        cfg.save(update_fields=["extra_config", "updated_at"])


def seed_scoring_rules(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameScoringRule = apps.get_model("games", "GameScoringRule")
    for rule_data in SCORING_RULES:
        try:
            game = Game.objects.get(slug=rule_data["slug"])
        except Game.DoesNotExist:
            continue
        GameScoringRule.objects.get_or_create(
            game=game, rule_type=rule_data["rule_type"],
            defaults={
                "config":      rule_data["config"],
                "description": rule_data["description"],
                "is_active":   rule_data["is_active"],
                "priority":    rule_data["priority"],
            },
        )


def seed_veto_configs(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    VetoConfiguration = apps.get_model("games", "VetoConfiguration")
    for vc in VETO_CONFIGS:
        try:
            game = Game.objects.get(slug=vc["game_slug"])
        except Game.DoesNotExist:
            continue
        VetoConfiguration.objects.get_or_create(
            game=game, name=vc["name"],
            defaults={
                "domain":                  vc["domain"],
                "sequence":                vc["sequence"],
                "pool":                    vc.get("pool", []),
                "time_per_action_seconds": vc["time_per_action_seconds"],
                "auto_random_on_timeout":  vc["auto_random_on_timeout"],
                "is_active":               True,
            },
        )


def unseed_maps(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMapPool = apps.get_model("games", "GameMapPool")
    for slug, maps in MAPS_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        codes = [m["code"] for m in maps]
        GameMapPool.objects.filter(game=game, map_code__in=codes).delete()


def unseed_scoring_rules(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameScoringRule = apps.get_model("games", "GameScoringRule")
    for rule_data in SCORING_RULES:
        try:
            game = Game.objects.get(slug=rule_data["slug"])
        except Game.DoesNotExist:
            continue
        GameScoringRule.objects.filter(game=game, rule_type=rule_data["rule_type"]).delete()


def unseed_veto_configs(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    VetoConfiguration = apps.get_model("games", "VetoConfiguration")
    for vc in VETO_CONFIGS:
        try:
            game = Game.objects.get(slug=vc["game_slug"])
        except Game.DoesNotExist:
            continue
        VetoConfiguration.objects.filter(game=game, name=vc["name"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0009_seed_lobby_options"),
    ]

    operations = [
        migrations.RunPython(seed_maps,          reverse_code=unseed_maps),
        migrations.RunPython(seed_lobby_options, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(seed_scoring_rules, reverse_code=unseed_scoring_rules),
        migrations.RunPython(seed_veto_configs,  reverse_code=unseed_veto_configs),
    ]
