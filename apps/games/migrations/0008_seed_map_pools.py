"""
Data migration — seed initial map pools for the games we ship.

Naming + map_code values follow Riot/Valve official identifiers. ``image`` is
left blank intentionally — admins upload via the Game change-page inline
(``GameMapPoolInline``). Re-running this migration is safe; each row is
``get_or_create`` keyed on (game, map_code).

Per RP guidance, only seeds what we can verify; remaining games can be
populated by an admin via the Game change page or by extending this list
later.
"""

from django.db import migrations


VALORANT_MAPS = [
    # Active competitive pool (current Riot rotation). Order roughly by tournament prominence.
    {"code": "ascent",   "name": "Ascent",   "is_active": True,  "is_competitive": True,  "order": 1},
    {"code": "bind",     "name": "Bind",     "is_active": True,  "is_competitive": True,  "order": 2},
    {"code": "haven",    "name": "Haven",    "is_active": True,  "is_competitive": True,  "order": 3},
    {"code": "split",    "name": "Split",    "is_active": True,  "is_competitive": True,  "order": 4},
    {"code": "icebox",   "name": "Icebox",   "is_active": True,  "is_competitive": True,  "order": 5},
    {"code": "lotus",    "name": "Lotus",    "is_active": True,  "is_competitive": True,  "order": 6},
    {"code": "sunset",   "name": "Sunset",   "is_active": True,  "is_competitive": True,  "order": 7},
    {"code": "abyss",    "name": "Abyss",    "is_active": True,  "is_competitive": True,  "order": 8},
    # Rotated-out maps — left inactive so they can be re-enabled when Riot
    # rotates them back. Organisers can flip is_active per-tournament via
    # MapPoolEntry (tournament-level override).
    {"code": "breeze",   "name": "Breeze",   "is_active": False, "is_competitive": True,  "order": 9},
    {"code": "fracture", "name": "Fracture", "is_active": False, "is_competitive": True,  "order": 10},
    {"code": "pearl",    "name": "Pearl",    "is_active": False, "is_competitive": True,  "order": 11},
]

CS2_MAPS = [
    {"code": "de_mirage",   "name": "Mirage",   "is_active": True,  "is_competitive": True,  "order": 1},
    {"code": "de_inferno",  "name": "Inferno",  "is_active": True,  "is_competitive": True,  "order": 2},
    {"code": "de_dust2",    "name": "Dust 2",   "is_active": True,  "is_competitive": True,  "order": 3},
    {"code": "de_nuke",     "name": "Nuke",     "is_active": True,  "is_competitive": True,  "order": 4},
    {"code": "de_ancient",  "name": "Ancient",  "is_active": True,  "is_competitive": True,  "order": 5},
    {"code": "de_anubis",   "name": "Anubis",   "is_active": True,  "is_competitive": True,  "order": 6},
    {"code": "de_vertigo",  "name": "Vertigo",  "is_active": True,  "is_competitive": True,  "order": 7},
    {"code": "de_train",    "name": "Train",    "is_active": False, "is_competitive": True,  "order": 8},
    {"code": "de_overpass", "name": "Overpass", "is_active": False, "is_competitive": True,  "order": 9},
]

# Per-game seed groups — keyed on Game.slug (the canonical identifier).
SEED_BY_SLUG = {
    "valorant": VALORANT_MAPS,
    "cs2":      CS2_MAPS,
}


def seed_map_pools(apps, schema_editor):
    """Idempotently insert map pool rows for known games.

    Skips games that don't exist (different deploys may not have all games
    seeded). Skips rows that already exist (matched on game+map_code). Never
    overwrites existing rows — admins may have customised them.
    """
    Game = apps.get_model("games", "Game")
    GameMapPool = apps.get_model("games", "GameMapPool")

    for slug, maps in SEED_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        for entry in maps:
            GameMapPool.objects.get_or_create(
                game=game,
                map_code=entry["code"],
                defaults={
                    "map_name":       entry["name"],
                    "is_active":      entry["is_active"],
                    "is_competitive": entry["is_competitive"],
                    "order":          entry["order"],
                },
            )


def unseed_map_pools(apps, schema_editor):
    """Reverse — remove ONLY the rows whose (game, map_code) we seeded.

    Preserves admin-added rows. Safe to run after admins have uploaded
    images; this migration never seeded image data so we won't delete files.
    """
    Game = apps.get_model("games", "Game")
    GameMapPool = apps.get_model("games", "GameMapPool")

    for slug, maps in SEED_BY_SLUG.items():
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        codes = [entry["code"] for entry in maps]
        GameMapPool.objects.filter(game=game, map_code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0007_gametournamentconfig_credential_schema_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_map_pools, reverse_code=unseed_map_pools),
    ]
