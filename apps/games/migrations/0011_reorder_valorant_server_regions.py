"""
P7 — Reorder Valorant server regions with APAC priority.

DeltaCrown's primary audience is South/Southeast Asia.
Mumbai and Singapore should appear first in the server selector.
"""

from django.db import migrations


VALORANT_SERVER_REGIONS = [
    {"code": "ap-mumbai",      "label": "Mumbai (APAC)"},
    {"code": "ap-singapore",   "label": "Singapore (APAC)"},
    {"code": "ap-tokyo",       "label": "Tokyo (APAC)"},
    {"code": "ap-hongkong",    "label": "Hong Kong (APAC)"},
    {"code": "ap-seoul",       "label": "Seoul (APAC)"},
    {"code": "ap-sydney",      "label": "Sydney (APAC)"},
    {"code": "ap-south",       "label": "Asia Pacific South"},
    {"code": "eu-west",        "label": "EU West"},
    {"code": "eu-central",     "label": "EU Central"},
    {"code": "na-east",        "label": "NA East"},
    {"code": "na-west",        "label": "NA West"},
    {"code": "br",             "label": "Brazil"},
    {"code": "latam",          "label": "Latin America"},
]


def update_valorant_servers(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameTournamentConfig = apps.get_model("games", "GameTournamentConfig")
    try:
        game = Game.objects.get(slug="valorant")
    except Game.DoesNotExist:
        return
    try:
        cfg = GameTournamentConfig.objects.get(game=game)
    except GameTournamentConfig.DoesNotExist:
        return
    extra = cfg.extra_config if isinstance(cfg.extra_config, dict) else {}
    lobby = extra.get("lobby_options", {})
    if not isinstance(lobby, dict):
        lobby = {}
    lobby["server_regions"] = VALORANT_SERVER_REGIONS
    extra["lobby_options"] = lobby
    cfg.extra_config = extra
    cfg.save(update_fields=["extra_config"])


def reverse_update(apps, schema_editor):
    pass  # Intentionally no-op; old order was arbitrary


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0010_seed_game_data_expansion"),
    ]

    operations = [
        migrations.RunPython(update_valorant_servers, reverse_code=reverse_update),
    ]
