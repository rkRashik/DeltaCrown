"""
Data migration — seed default lobby option lists (server regions, game modes)
into ``GameTournamentConfig.extra_config['lobby_options']`` for the games we
ship. Match-room UI reads these via ``resolve_lobby_options`` so participants
get proper select dropdowns instead of blank text fields.

Admins can edit these via the Django admin (GameTournamentConfig → extra_config
JSON). Re-runnable — only seeds if ``lobby_options`` key is missing or empty.
"""

from django.db import migrations


VALORANT_LOBBY_OPTIONS = {
    # Riot regional server hubs — codes match the values Riot exposes.
    "server_regions": [
        {"code": "ap-south",   "label": "Asia Pacific — South"},
        {"code": "ap-mumbai",  "label": "AP Mumbai"},
        {"code": "ap-sydney",  "label": "AP Sydney"},
        {"code": "ap-tokyo",   "label": "AP Tokyo"},
        {"code": "ap-seoul",   "label": "AP Seoul"},
        {"code": "eu-west",    "label": "EU West"},
        {"code": "eu-central", "label": "EU Central"},
        {"code": "na-east",    "label": "NA East"},
        {"code": "na-west",    "label": "NA West"},
        {"code": "br",         "label": "Brazil"},
        {"code": "latam",      "label": "Latin America"},
    ],
    # Competitive modes — Standard is the canonical match mode.
    "game_modes": [
        {"code": "standard",  "label": "Standard (Competitive)"},
        {"code": "swiftplay", "label": "Swiftplay"},
        {"code": "deathmatch","label": "Deathmatch"},
        {"code": "custom",    "label": "Custom Game"},
    ],
}

CS2_LOBBY_OPTIONS = {
    "server_regions": [
        {"code": "asia-singapore", "label": "Asia — Singapore"},
        {"code": "asia-mumbai",    "label": "Asia — Mumbai"},
        {"code": "asia-tokyo",     "label": "Asia — Tokyo"},
        {"code": "eu-west",        "label": "EU West"},
        {"code": "na-east",        "label": "NA East"},
        {"code": "na-west",        "label": "NA West"},
        {"code": "sa-brazil",      "label": "South America — Brazil"},
    ],
    "game_modes": [
        {"code": "competitive",  "label": "Competitive (5v5)"},
        {"code": "wingman",      "label": "Wingman (2v2)"},
        {"code": "premier",      "label": "Premier"},
        {"code": "custom",       "label": "Custom Match"},
    ],
}


SEED_BY_SLUG = {
    "valorant": VALORANT_LOBBY_OPTIONS,
    "cs2":      CS2_LOBBY_OPTIONS,
}


def seed_lobby_options(apps, schema_editor):
    """Idempotently seed lobby_options for known games.

    Only writes when ``extra_config['lobby_options']`` is missing or empty;
    never overwrites admin customisation.
    """
    Game = apps.get_model("games", "Game")
    GameTournamentConfig = apps.get_model("games", "GameTournamentConfig")

    for slug, options in SEED_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        cfg, _created = GameTournamentConfig.objects.get_or_create(game=game)
        extra = cfg.extra_config if isinstance(cfg.extra_config, dict) else {}
        existing = extra.get("lobby_options")
        if isinstance(existing, dict) and existing:
            # Don't overwrite admin-edited config.
            continue
        extra["lobby_options"] = options
        cfg.extra_config = extra
        cfg.save(update_fields=["extra_config", "updated_at"])


def unseed_lobby_options(apps, schema_editor):
    """Reverse — drop the lobby_options key (preserves other extra_config)."""
    Game = apps.get_model("games", "Game")
    GameTournamentConfig = apps.get_model("games", "GameTournamentConfig")

    for slug in SEED_BY_SLUG.keys():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        cfg = GameTournamentConfig.objects.filter(game=game).first()
        if not cfg or not isinstance(cfg.extra_config, dict):
            continue
        if "lobby_options" in cfg.extra_config:
            extra = dict(cfg.extra_config)
            extra.pop("lobby_options", None)
            cfg.extra_config = extra
            cfg.save(update_fields=["extra_config", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0008_seed_map_pools"),
    ]

    operations = [
        migrations.RunPython(seed_lobby_options, reverse_code=unseed_lobby_options),
    ]
