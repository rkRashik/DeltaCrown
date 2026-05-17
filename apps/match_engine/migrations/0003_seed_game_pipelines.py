"""
P6 — Seed GameMatchPipeline rows for all 14 active games.

Idempotent: uses get_or_create so safe to re-run.
Pipeline phases are sourced from apps.games.constants.GAME_ARCHETYPES —
callers use GameMatchPipeline.get_phase_order() which falls back to the
archetype default when phases=[] anyway, but explicit rows let admins
override per-game without touching constants.
"""

from django.db import migrations


PIPELINE_DATA = [
    # slug                 archetype           require_coin_toss  require_map_veto
    # ── Tactical FPS ─────────────────────────────────────────────────────────
    ("valorant",    "tactical_fps",  False, True),
    ("cs2",         "tactical_fps",  False, True),
    ("r6siege",     "tactical_fps",  False, True),
    ("codm",        "tactical_fps",  False, True),
    # ── MOBA ─────────────────────────────────────────────────────────────────
    ("dota2",       "moba",          True,  False),
    ("mlbb",        "moba",          True,  False),
    ("lol",         "moba",          True,  False),
    # ── Battle Royale ────────────────────────────────────────────────────────
    ("pubgm",       "battle_royale", False, False),
    ("freefire",    "battle_royale", False, False),
    ("apex",        "battle_royale", False, False),
    # ── Sports ───────────────────────────────────────────────────────────────
    ("ea-fc",       "sports",        False, False),
    ("efootball",   "sports",        False, False),
    ("rocketleague","sports",        False, False),
    # ── Shooter with map veto (Overwatch 2) ──────────────────────────────────
    ("ow2",         "tactical_fps",  False, True),
]

# Phase lists match GAME_ARCHETYPES in apps.games.constants — stored explicitly
# so admins can override per-game without editing constants.py.
ARCHETYPE_PHASES = {
    "tactical_fps":  ["coin_toss", "map_veto", "side_selection", "lobby_setup", "live", "results", "completed"],
    "moba":          ["coin_toss", "hero_draft", "side_selection", "lobby_setup", "live", "results", "completed"],
    "battle_royale": ["lobby_distribution", "server_assignment", "live", "matrix_results", "completed"],
    "sports":        ["direct_ready", "lobby_setup", "live", "results", "completed"],
}


def seed_pipelines(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMatchPipeline = apps.get_model("match_engine", "GameMatchPipeline")

    created = 0
    skipped = 0
    for slug, archetype, coin_toss, map_veto in PIPELINE_DATA:
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            continue
        phases = ARCHETYPE_PHASES.get(archetype, ARCHETYPE_PHASES["tactical_fps"])
        _, was_created = GameMatchPipeline.objects.get_or_create(
            game=game,
            defaults={
                "archetype": archetype,
                "phases": phases,
                "require_coin_toss": coin_toss,
                "require_map_veto": map_veto,
            },
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    print(f"GameMatchPipeline seeding: {created} created, {skipped} already existed.")


def unseed_pipelines(apps, schema_editor):
    """Reverse: remove rows seeded by this migration only (by slug list)."""
    Game = apps.get_model("games", "Game")
    GameMatchPipeline = apps.get_model("match_engine", "GameMatchPipeline")
    slugs = [row[0] for row in PIPELINE_DATA]
    GameMatchPipeline.objects.filter(game__slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("match_engine", "0002_matchchatmessage"),
        ("games", "0010_seed_game_data_expansion"),
    ]

    operations = [
        migrations.RunPython(seed_pipelines, reverse_code=unseed_pipelines),
    ]
