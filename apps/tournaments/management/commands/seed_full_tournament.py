"""
DeltaCrown Comprehensive Seed Script
=====================================

Creates 100 users, 40 teams, 3 orgs, 15 tournaments across 8 games
following the seeding plan in docs/MyTesting/DeltaCrown Seeding Plan.md

Usage:
    python manage.py seed_full_tournament
    python manage.py seed_full_tournament --clear
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction, connection
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from decimal import Decimal
import random
import json

from apps.accounts.models import User
from apps.games.models import Game
from apps.organizations.models import Organization, Team, TeamMembership
from apps.organizations.choices import (
    TeamStatus, MembershipStatus, MembershipRole, RosterSlot,
)
from apps.user_profile.models_main import UserProfile, GameProfile
from apps.tournaments.models import (
    Tournament, Registration, Match, Group, GroupStanding, Bracket,
)
from apps.teams.models._legacy import Team as LegacyTeam
from apps.teams.mixins import legacy_write_bypass

try:
    from apps.tournaments.models.stage import TournamentStage
except ImportError:
    TournamentStage = None

PASSWORD = "DeltaCrown2025!"
NOW = timezone.now()


# ═══════════════════════════════════════════════════════════════════════
# USER DATA
# ═══════════════════════════════════════════════════════════════════════

USERS_A = [
    # (username, display_name, bio, city, [games])
    ("dc_shadow_strike", "Shadow.Strike", "Radiant peak. DM for scrims.", "Dhaka", ["Valorant", "CS2"]),
    ("dc_kryptek", "Kryptek_BD", "IGL for Team Eclipse.", "Dhaka", ["Valorant"]),
    ("dc_vortex", "V0rtex", "Duelist main. Grinding for national.", "Dhaka", ["Valorant"]),
    ("dc_aimgod_rafi", "AimGod_Rafi", "Global Elite since 2019.", "Dhaka", ["CS2"]),
    ("dc_zeus", "Z3US", "Support god.", "Dhaka", ["Valorant", "League of Legends"]),
    ("dc_hypernova", "Hyper.Nova", "Entry fragger.", "Chittagong", ["Valorant"]),
    ("dc_glitch", "Glitch.FPS", "Stream at twitch.tv/glitch", "Dhaka", ["CS2"]),
    ("dc_spectre", "Spectre_BD", "Sentinel main.", "Dhaka", ["Valorant"]),
    ("dc_phoenix_rise", "PhoenixRise", "Flash and entry.", "Sylhet", ["Valorant"]),
    ("dc_apex_hunter", "Apex.Hunter", "Diamond IV.", "Dhaka", ["Apex Legends"]),
    ("dc_frag_master", "FragMaster", "FPS veteran. 10K hours.", "Dhaka", ["CS2", "Valorant"]),
    ("dc_blade_runner", "BladeRunner", "Flex player.", "Rajshahi", ["Valorant"]),
    ("dc_nova_blast", "NovaBlast", "High KD ratio.", "Dhaka", ["Apex Legends"]),
    ("dc_cyber_wolf", "CyberWolf", "IGL. Clean comms.", "Dhaka", ["CS2"]),
    ("dc_rapid_fire", "RapidFire", "AWP specialist.", "Chittagong", ["CS2"]),
    ("dc_storm_break", "StormBreak", "Controller main.", "Dhaka", ["Valorant"]),
    ("dc_neon_rush", "NeonRush", "Aggressive entry.", "Dhaka", ["Valorant"]),
    ("dc_dark_matter", "DarkMatter", "Rifler. B-site anchor.", "Dhaka", ["CS2"]),
    ("dc_iron_sight", "IronSight", "Sniper specialist.", "Sylhet", ["CS2"]),
    ("dc_quantum", "Quantum.bd", "Flex.", "Dhaka", ["Valorant", "Apex Legends"]),
    ("dc_fury", "Fury_BD", "Berserker playstyle.", "Dhaka", ["League of Legends"]),
    ("dc_mystic_soul", "MysticSoul", "Support main.", "Khulna", ["League of Legends"]),
    ("dc_thunder", "Thunder.GG", "ADC main.", "Dhaka", ["League of Legends"]),
    ("dc_echo_wave", "EchoWave", "Mid laner.", "Dhaka", ["League of Legends"]),
    ("dc_celestial", "Celestial", "Jungle main.", "Dhaka", ["League of Legends", "Dota 2"]),
    ("dc_venom", "Venom_BD", "Offlaner.", "Chittagong", ["Dota 2"]),
    ("dc_phantom", "Phantom_X", "Pos 1 carry.", "Dhaka", ["Dota 2"]),
    ("dc_reaper", "Reaper.BD", "Pos 5 support.", "Dhaka", ["Dota 2"]),
    ("dc_omega", "Omega.GG", "Mid player.", "Dhaka", ["Dota 2"]),
    ("dc_nitro", "Nitro.Speed", "Grand Champ.", "Dhaka", ["Rocket League"]),
    ("dc_apex_pred", "ApexPredator", "Pred rank.", "Dhaka", ["Apex Legends"]),
    ("dc_sniper_king", "SniperKing", "Marksman.", "Comilla", ["Apex Legends"]),
    ("dc_turbo", "Turbo.RL", "Aerial specialist.", "Dhaka", ["Rocket League"]),
    ("dc_stellar", "Stellar_BD", "Consistent performer.", "Dhaka", ["Rocket League"]),
    ("dc_fc_master", "FC_Master", "Division 1.", "Dhaka", ["FC 25"]),
    ("dc_goal_king", "GoalKing", "90% win rate.", "Dhaka", ["FC 25"]),
    ("dc_striker", "Striker.BD", "Attacking playstyle.", "Chittagong", ["FC 25"]),
    ("dc_dribble", "Dribble_Pro", "Skill moves expert.", "Dhaka", ["FC 25"]),
    ("dc_ow_mercy", "MercyMain", "Support player.", "Dhaka", ["Overwatch 2"]),
    ("dc_ow_genji", "Genji.Blade", "DPS flex.", "Dhaka", ["Overwatch 2"]),
]

USERS_B = [
    ("dc_mama_lag", "Mama_Lag_Kore", "Lag er moddhe clutch.", "Chittagong", ["Valorant"]),
    ("dc_bhai_op", "Bhai_OP", "Study kom game beshi.", "Dhaka", ["Valorant"]),
    ("dc_kushtia_sniper", "Kushtia_Sniper", "Playing from village. Ping 200.", "Kushtia", ["CS2"]),
    ("dc_net_nai", "Net_Nai", "Broadband ar pera khabo na.", "Rajshahi", ["CS2"]),
    ("dc_bot_slayer", "Bot_Slayer", "Actually Iron 1.", "Dhaka", ["Valorant"]),
    ("dc_dhaka_king", "Dhaka_King", "Dhanmondi er pride.", "Dhaka", ["Valorant"]),
    ("dc_noob_hunter", "Noob_Hunter", "Ping high but spirits high.", "Sylhet", ["CS2"]),
    ("dc_lag_lord", "Lag_Lord", "WiFi r shathe juddhho.", "Barisal", ["Valorant"]),
    ("dc_bhai_clutch", "Bhai_Clutch", "1v5 everyday.", "Dhaka", ["CS2"]),
    ("dc_exam_kaal", "Exam_Kaal", "Poriksha ase but one more game.", "Dhaka", ["Valorant"]),
    ("dc_taka_nai", "Taka_Nai", "Free tournament only.", "Chittagong", ["Valorant"]),
    ("dc_net_slow", "Net_SlowBD", "Buffering champion.", "Mymensingh", ["CS2"]),
    ("dc_chai_break", "Chai_Break", "AFK for cha.", "Dhaka", ["Valorant"]),
    ("dc_study_later", "StudyLater", "One more round then study.", "Dhaka", ["League of Legends"]),
    ("dc_bronze_pride", "Bronze_Pride", "Bronze is a lifestyle.", "Dhaka", ["League of Legends"]),
    ("dc_carry_pls", "Carry_Pls", "Need carry from Iron.", "Chittagong", ["Valorant"]),
    ("dc_afk_alert", "AFK_Alert", "Mom called. BRB.", "Dhaka", ["CS2"]),
    ("dc_toxic_heal", "Toxic_Healer", "Support but toxic.", "Dhaka", ["League of Legends"]),
    ("dc_dhaka_bot", "Dhaka_Bot", "Playing for fun. No tilt.", "Dhaka", ["Valorant"]),
    ("dc_sylhet_snipe", "Sylhet_Snipe", "Sniper from the hills.", "Sylhet", ["CS2"]),
    ("dc_rocket_noob", "Rocket_Noob", "What a save!", "Dhaka", ["Rocket League"]),
    ("dc_goal_miss", "GoalMiss", "Always hit the post.", "Dhaka", ["FC 25"]),
    ("dc_offside_king", "Offside_King", "Timing is hard.", "Dhaka", ["FC 25"]),
    ("dc_tank_main", "TankMain", "Reinhardt one trick.", "Dhaka", ["Overwatch 2"]),
    ("dc_heal_pls", "Heal_Pls", "DPS queued as support.", "Chittagong", ["Overwatch 2"]),
    ("dc_mid_or_feed", "MidOrFeed", "Classic.", "Dhaka", ["Dota 2"]),
    ("dc_pudge_hook", "PudgeHook", "Hook accuracy 30%.", "Dhaka", ["Dota 2"]),
    ("dc_int_master", "IntMaster", "Die 15 times carry 1v9.", "Dhaka", ["League of Legends"]),
    ("dc_apex_noob", "Apex_Noob", "Drop Skull Town. Die. Repeat.", "Dhaka", ["Apex Legends"]),
    ("dc_pathfinder", "PathFinder_BD", "Grapple god.", "Chittagong", ["Apex Legends"]),
    ("dc_val_casual", "Val_Casual", "Unrated only.", "Dhaka", ["Valorant"]),
    ("dc_cs_silver", "CS_Silver", "Silver Elite Master. Peaked.", "Dhaka", ["CS2"]),
    ("dc_rl_bronze", "RL_Bronze", "Car go brr.", "Dhaka", ["Rocket League"]),
    ("dc_fc_draw", "FC_Draw", "Every game 1-1.", "Rajshahi", ["FC 25"]),
    ("dc_dota_sup", "Dota_Sup", "Ward duty.", "Dhaka", ["Dota 2"]),
    ("dc_apex_loot", "Apex_Loot", "Loot goblin. Never fights.", "Dhaka", ["Apex Legends"]),
    ("dc_val_iron", "Val_Iron", "Iron 1 and proud.", "Dhaka", ["Valorant"]),
    ("dc_cs_rush", "CS_RushB", "Rush B no stop.", "Dhaka", ["CS2"]),
    ("dc_ow_potato", "OW_Potato", "Aim like a potato.", "Dhaka", ["Overwatch 2"]),
    ("dc_rl_flip", "RL_Flip", "Front flip goal.", "Dhaka", ["Rocket League"]),
]

USERS_C = [
    ("dc_tanvir", "Tanvir.Gaming", "Pro player for Crimson Syndicate", "Dhaka", ["Valorant"]),
    ("dc_sakib", "Sakib_Plays", "IGL. Team captain.", "Dhaka", ["Valorant"]),
    ("dc_rifat", "Rifat.Official", "CS2 professional. 8K hours.", "Dhaka", ["CS2"]),
    ("dc_nabil", "Nabil_Esports", "Org owner. Titan Esports CEO.", "Dhaka", ["Valorant", "CS2"]),
    ("dc_arif", "Arif.Pro", "Competitive Dota 2.", "Dhaka", ["Dota 2"]),
    ("dc_farhan", "Farhan.GG", "LoL streamer. 50K followers.", "Dhaka", ["League of Legends"]),
    ("dc_siam", "Siam.Live", "Content creator.", "Chittagong", ["Valorant"]),
    ("dc_rashed", "Rashed.TTV", "Twitch partner.", "Dhaka", ["CS2"]),
    ("dc_karim", "Karim.Coach", "Ex-pro. Now coaching.", "Dhaka", ["Valorant", "CS2"]),
    ("dc_jamal", "Jamal.Caster", "Tournament caster and analyst.", "Dhaka", []),
    ("dc_hasan", "Hasan.FC", "FC25 content creator.", "Dhaka", ["FC 25"]),
    ("dc_imran", "Imran.RL", "Rocket League streamer.", "Dhaka", ["Rocket League"]),
    ("dc_zahid", "Zahid.OW", "Top 500 Overwatch.", "Dhaka", ["Overwatch 2"]),
    ("dc_mamun", "Mamun.Apex", "Apex predator. Content.", "Dhaka", ["Apex Legends"]),
    ("dc_robin", "Robin.Dota", "Dota 2 Immortal.", "Chittagong", ["Dota 2"]),
    ("dc_sumon", "Sumon.Pro", "Multi-game competitor.", "Dhaka", ["Valorant", "CS2", "League of Legends"]),
    ("dc_jubayer", "Jubayer.GG", "Rising talent.", "Dhaka", ["Valorant"]),
    ("dc_mahfuz", "Mahfuz.Coach", "Strategic analyst.", "Dhaka", ["CS2", "Dota 2"]),
    ("dc_shafiq", "Shafiq.Org", "Org operations.", "Dhaka", ["CS2"]),
    ("dc_omar", "Omar.Cast", "Commentator. Tournament host.", "Dhaka", []),
]

ALL_USERS = USERS_A + USERS_B + USERS_C

# ═══════════════════════════════════════════════════════════════════════
# TEAM DATA  (name, tag, game, org_slug_or_none, owner_username,
#              [(member_username, role, roster_slot, is_captain), ...])
# ═══════════════════════════════════════════════════════════════════════

TEAMS = [
    # --- Valorant ---
    ("Crimson Syndicate", "CRS", "Valorant", None, "dc_tanvir", [
        ("dc_vortex", "PLAYER", "STARTER", False),
        ("dc_spectre", "PLAYER", "STARTER", False),
        ("dc_blade_runner", "PLAYER", "STARTER", False),
        ("dc_frag_master", "PLAYER", "STARTER", False),
        ("dc_shadow_strike", "SUBSTITUTE", "SUBSTITUTE", False),
        ("dc_quantum", "SUBSTITUTE", "SUBSTITUTE", False),
    ]),
    ("Velocity X BD", "VXB", "Valorant", None, "dc_sakib", [
        ("dc_hypernova", "PLAYER", "STARTER", False),
        ("dc_kryptek", "PLAYER", "STARTER", False),
        ("dc_zeus", "PLAYER", "STARTER", False),
        ("dc_phoenix_rise", "PLAYER", "STARTER", False),
    ]),
    ("Dhaka Leviathans", "DLV", "Valorant", "titan-esports", "dc_nabil", [
        ("dc_storm_break", "PLAYER", "STARTER", True),
        ("dc_neon_rush", "PLAYER", "STARTER", False),
        ("dc_bhai_op", "PLAYER", "STARTER", False),
        ("dc_dhaka_king", "PLAYER", "STARTER", False),
        ("dc_mama_lag", "SUBSTITUTE", "SUBSTITUTE", False),
    ]),
    ("Titan Valorant", "TVL", "Valorant", "titan-esports", "dc_jubayer", [
        ("dc_siam", "PLAYER", "STARTER", False),
        ("dc_val_casual", "PLAYER", "STARTER", False),
        ("dc_lag_lord", "PLAYER", "STARTER", False),
        ("dc_chai_break", "PLAYER", "STARTER", False),
        ("dc_taka_nai", "SUBSTITUTE", "SUBSTITUTE", False),
    ]),
    ("Headhunterz", "HHZ", "Valorant", None, "dc_exam_kaal", [
        ("dc_bot_slayer", "PLAYER", "STARTER", False),
        ("dc_dhaka_bot", "PLAYER", "STARTER", False),
        ("dc_carry_pls", "PLAYER", "STARTER", False),
        ("dc_val_iron", "PLAYER", "STARTER", False),
    ]),
    ("AimBot Activated", "ABA", "Valorant", "crown-dynasty", "dc_sumon", [
        ("dc_mama_lag", "PLAYER_SKIP", None, False),  # Already on DLV
    ]),
    # --- CS2 ---
    ("Old School BD", "OSB", "CS2", None, "dc_rifat", [
        ("dc_aimgod_rafi", "PLAYER", "STARTER", False),
        ("dc_cyber_wolf", "PLAYER", "STARTER", False),
        ("dc_glitch", "PLAYER", "STARTER", False),
        ("dc_rapid_fire", "PLAYER", "STARTER", False),
        ("dc_shadow_strike", "SUBSTITUTE", "SUBSTITUTE", False),
    ]),
    ("Dust2 Demons", "D2D", "CS2", "eclipse-gaming", "dc_shafiq", [
        ("dc_dark_matter", "PLAYER", "STARTER", False),
        ("dc_iron_sight", "PLAYER", "STARTER", False),
        ("dc_rashed", "PLAYER", "STARTER", False),
        ("dc_mahfuz", "PLAYER", "STARTER", False),
    ]),
    ("Mirage Kings", "MRG", "CS2", None, "dc_kushtia_sniper", [
        ("dc_net_nai", "PLAYER", "STARTER", False),
        ("dc_noob_hunter", "PLAYER", "STARTER", False),
        ("dc_bhai_clutch", "PLAYER", "STARTER", False),
        ("dc_afk_alert", "PLAYER", "STARTER", False),
    ]),
    ("Global Elites", "GEL", "CS2", None, "dc_cs_silver", [
        ("dc_net_slow", "PLAYER", "STARTER", False),
        ("dc_sylhet_snipe", "PLAYER", "STARTER", False),
        ("dc_cs_rush", "PLAYER", "STARTER", False),
        ("dc_nabil", "PLAYER", "STARTER", False),
    ]),
    # --- LoL ---
    ("Fury Esports", "FRY", "League of Legends", "titan-esports", "dc_fury", [
        ("dc_farhan", "PLAYER", "STARTER", False),
        ("dc_thunder", "PLAYER", "STARTER", False),
        ("dc_echo_wave", "PLAYER", "STARTER", False),
        ("dc_celestial", "PLAYER", "STARTER", False),
    ]),
    ("Mystic Legion", "MYL", "League of Legends", None, "dc_mystic_soul", [
        ("dc_study_later", "PLAYER", "STARTER", False),
        ("dc_bronze_pride", "PLAYER", "STARTER", False),
        ("dc_toxic_heal", "PLAYER", "STARTER", False),
        ("dc_int_master", "PLAYER", "STARTER", False),
    ]),
    ("Echo Rift", "ECR", "League of Legends", None, "dc_sumon", [
        ("dc_zeus", "PLAYER", "STARTER", False),
    ]),
    # --- Dota 2 ---
    ("Ancient Defense", "ACD", "Dota 2", "eclipse-gaming", "dc_arif", [
        ("dc_phantom", "PLAYER", "STARTER", False),
        ("dc_reaper", "PLAYER", "STARTER", False),
        ("dc_omega", "PLAYER", "STARTER", False),
        ("dc_robin", "PLAYER", "STARTER", False),
    ]),
    ("Roshan Raiders", "RSR", "Dota 2", None, "dc_venom", [
        ("dc_celestial", "PLAYER", "STARTER", False),
        ("dc_mid_or_feed", "PLAYER", "STARTER", False),
        ("dc_pudge_hook", "PLAYER", "STARTER", False),
        ("dc_dota_sup", "PLAYER", "STARTER", False),
    ]),
    ("Ward Vision", "WRV", "Dota 2", None, "dc_reaper", [
        ("dc_mahfuz", "PLAYER", "STARTER", False),
    ]),
    # --- Apex ---
    ("Apex Predators BD", "APB", "Apex Legends", None, "dc_mamun", [
        ("dc_apex_pred", "PLAYER", "STARTER", False),
        ("dc_apex_hunter", "PLAYER", "STARTER", False),
    ]),
    ("Zone Survivors", "ZNS", "Apex Legends", None, "dc_sniper_king", [
        ("dc_pathfinder", "PLAYER", "STARTER", False),
        ("dc_nova_blast", "PLAYER", "STARTER", False),
    ]),
    ("Loot Goblins", "LTG", "Apex Legends", None, "dc_apex_loot", [
        ("dc_apex_noob", "PLAYER", "STARTER", False),
    ]),
    # --- Rocket League ---
    ("Nitro Speed", "NTS", "Rocket League", None, "dc_nitro", [
        ("dc_turbo", "PLAYER", "STARTER", False),
        ("dc_stellar", "PLAYER", "STARTER", False),
    ]),
    ("Flip Reset FC", "FRF", "Rocket League", None, "dc_imran", [
        ("dc_rl_bronze", "PLAYER", "STARTER", False),
        ("dc_rl_flip", "PLAYER", "STARTER", False),
    ]),
    ("Car Go Brr", "CGB", "Rocket League", None, "dc_rocket_noob", [
    ]),
    # --- Overwatch 2 ---
    ("Payload Pushers", "PLP", "Overwatch 2", None, "dc_zahid", [
        ("dc_ow_mercy", "PLAYER", "STARTER", False),
        ("dc_ow_genji", "PLAYER", "STARTER", False),
        ("dc_tank_main", "PLAYER", "STARTER", False),
        ("dc_heal_pls", "PLAYER", "STARTER", False),
    ]),
    ("Point Capture", "PTC", "Overwatch 2", None, "dc_ow_potato", [
    ]),
]

# ═══════════════════════════════════════════════════════════════════════
# GAME PASSPORT DATA
# ═══════════════════════════════════════════════════════════════════════

RANK_DATA = {
    "Valorant": {"ranks": ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"]},
    "CS2": {"ranks": ["Silver", "Gold Nova", "Master Guardian", "Distinguished Master Guardian", "Legendary Eagle", "Supreme Master", "Global Elite"]},
    "League of Legends": {"ranks": ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Master", "Grandmaster", "Challenger"]},
    "Dota 2": {"ranks": ["Herald", "Guardian", "Crusader", "Archon", "Legend", "Ancient", "Divine", "Immortal"]},
    "Apex Legends": {"ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Predator"]},
    "Overwatch 2": {"ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster", "Top 500"]},
    "Rocket League": {"ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion", "Grand Champion", "Supersonic Legend"]},
    "FC 25": {"ranks": ["Division 10", "Division 7", "Division 5", "Division 3", "Division 1", "Elite"]},
}


class Command(BaseCommand):
    help = "Seed 100 users, 40 teams, 3 orgs, 15 tournaments"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all seeded data first")

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        # Ensure games exist (ignore errors if games already exist with different slugs)
        try:
            call_command("init_default_games", verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"init_default_games had issues (likely pre-existing data): {e}"))
            self.stdout.write(self.style.WARNING("Continuing with existing games..."))

        # Create missing games that aren't in init_default_games
        self._ensure_extra_games()

        self.game_map = {}
        for g in Game.objects.all():
            self.game_map[g.display_name] = g
            self.game_map[g.name] = g
            self.game_map[g.slug] = g
            # Add common aliases
        # Manual aliases for convenience
        aliases = {
            "Valorant": "valorant", "CS2": "cs2", "LoL": "lol",
            "League of Legends": "lol",
            "FC 25": "ea-fc", "FC 26": "ea-fc", "FC26": "ea-fc",
            "EA Sports FC 26": "ea-fc", "EA Sports FC 25": "ea-fc",
            "Apex": "apex", "Apex Legends": "apex",
            "OW2": "ow2", "Overwatch 2": "ow2", "Overwatch": "ow2",
            "RL": "rocketleague", "Rocket League": "rocketleague",
        }
        for alias, slug in aliases.items():
            g = Game.objects.filter(slug=slug).first()
            if g and alias not in self.game_map:
                self.game_map[alias] = g

        self.user_map = {}   # username -> User
        self.team_map = {}   # team_name -> Team (vNext)
        self.org_map = {}    # org_slug -> Organization
        self.legacy_map = {}  # team_name -> LegacyTeam

        # Track which user is assigned to which game's team
        self.user_game_assignments = {}  # (username, game_display_name) -> team_name

        with transaction.atomic():
            # Fix deferred FK constraints
            with connection.cursor() as cur:
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

            self._create_users()
            self._create_game_passports()
            self._create_organizations()
            self._create_teams()
            self._create_completed_tournaments()
            self._create_live_tournaments()
            self._create_open_tournaments()

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeding complete: {len(self.user_map)} users, "
            f"{len(self.team_map)} teams, {len(self.org_map)} orgs, "
            f"{Tournament.objects.count()} tournaments"
        ))

    # ───────────────────────────────────────────────────────────────
    # EXTRA GAMES
    # ───────────────────────────────────────────────────────────────

    def _ensure_extra_games(self):
        """Create games not covered by init_default_games."""
        extras = [
            {"name": "League of Legends", "display_name": "League of Legends", "slug": "lol",
             "short_code": "LOL", "category": "MOBA", "game_type": "TEAM_VS_TEAM",
             "developer": "Riot Games", "publisher": "Riot Games",
             "primary_color": "#C8AA6E", "platforms": ["PC"]},
            {"name": "Apex Legends", "display_name": "Apex Legends", "slug": "apex",
             "short_code": "APEX", "category": "BR", "game_type": "BATTLE_ROYALE",
             "developer": "Respawn Entertainment", "publisher": "Electronic Arts",
             "primary_color": "#DA292A", "platforms": ["PC", "Console"]},
            {"name": "Overwatch 2", "display_name": "Overwatch 2", "slug": "ow2",
             "short_code": "OW2", "category": "FPS", "game_type": "TEAM_VS_TEAM",
             "developer": "Blizzard Entertainment", "publisher": "Blizzard Entertainment",
             "primary_color": "#FA9C1E", "platforms": ["PC", "Console"]},
            {"name": "Rocket League", "display_name": "Rocket League", "slug": "rl",
             "short_code": "RL", "category": "SPORTS", "game_type": "TEAM_VS_TEAM",
             "developer": "Psyonix", "publisher": "Epic Games",
             "primary_color": "#0C6EFC", "platforms": ["PC", "Console"]},
        ]
        for spec in extras:
            slug = spec.pop("slug")
            platforms = spec.pop("platforms", ["pc"])
            # Check by slug OR name to avoid duplicates
            if Game.objects.filter(Q(slug=slug) | Q(name=spec["name"])).exists():
                self.stdout.write(f"  Skipped game (already exists): {spec['name']}")
            else:
                Game.objects.create(slug=slug, platforms=platforms, **spec)
                self.stdout.write(f"  Created game: {spec['name']}")

    # ───────────────────────────────────────────────────────────────
    # CLEAR
    # ───────────────────────────────────────────────────────────────

    def _clear(self):
        self.stdout.write("Clearing seeded data...")
        usernames = [u[0] for u in ALL_USERS]
        # Delete tournaments by seeded organizer
        organizer = User.objects.filter(username="dc_omar").first()
        if organizer:
            Tournament.all_objects.filter(organizer=organizer).delete()
        # Also clean up orphaned tournaments
        for slug in [
            "valorant-invitational-s1", "cs2-masters-bd", "lol-rift-clash-s1",
            "rl-nitro-cup", "fc25-weekend-league-1", "radiant-rising-s2",
            "ancient-defense-cup", "apex-survival-series", "ow2-payload-push",
            "nitro-speed-cup-s2", "valorant-scrims-44", "cs2-comp-league-spring",
            "fc25-solo-championship", "lol-rift-clash-s2", "dota2-guardian-cup",
        ]:
            Tournament.all_objects.filter(slug=slug).delete()

        # Delete teams
        team_slugs = [slugify(t[0]) for t in TEAMS]
        Team.objects.filter(slug__in=team_slugs).delete()
        with legacy_write_bypass(reason="seed_clear"):
            LegacyTeam.objects.filter(slug__in=team_slugs).delete()

        # Delete orgs
        Organization.objects.filter(slug__in=["titan-esports", "eclipse-gaming", "crown-dynasty"]).delete()

        # Delete users
        User.objects.filter(username__in=usernames).delete()
        self.stdout.write(self.style.SUCCESS("  Cleared."))

    # ───────────────────────────────────────────────────────────────
    # USERS
    # ───────────────────────────────────────────────────────────────

    def _create_users(self):
        self.stdout.write("Creating 100 users...")
        for i, (username, display, bio, city, games) in enumerate(ALL_USERS, 1):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@deltacrown.gg",
                    "is_verified": True,
                }
            )
            if created:
                user.set_password(PASSWORD)
                user.save()

            # Update or create profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = display
            profile.bio = bio
            profile.country = "BD"
            profile.city = city
            profile.region = "BD"
            profile.slug = slugify(username)
            try:
                profile.save()
            except Exception:
                pass  # slug collision etc

            self.user_map[username] = user

        self.stdout.write(f"  {len(self.user_map)} users ready.")

    # ───────────────────────────────────────────────────────────────
    # GAME PASSPORTS
    # ───────────────────────────────────────────────────────────────

    def _create_game_passports(self):
        self.stdout.write("Creating game passports...")
        count = 0
        for username, display, bio, city, games in ALL_USERS:
            user = self.user_map.get(username)
            if not user:
                continue
            for game_name in games:
                game = self.game_map.get(game_name)
                if not game:
                    continue
                ranks = RANK_DATA.get(game_name, {}).get("ranks", [])
                rank = random.choice(ranks) if ranks else ""
                ign = display.replace(".", "_").replace(" ", "")
                disc = f"#BD{random.randint(10,99)}" if game_name in ["Valorant", "League of Legends", "Overwatch 2"] else ""

                gp, created = GameProfile.objects.get_or_create(
                    user=user,
                    game=game,
                    defaults={
                        "ign": ign,
                        "discriminator": disc,
                        "platform": "pc",
                        "rank_name": rank,
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f"  {count} game passports created.")

    # ───────────────────────────────────────────────────────────────
    # ORGANIZATIONS
    # ───────────────────────────────────────────────────────────────

    def _create_organizations(self):
        self.stdout.write("Creating organizations...")
        orgs_data = [
            ("Titan Esports", "titan-esports", "dc_nabil", "Bangladesh's premier esports organization."),
            ("Eclipse Gaming", "eclipse-gaming", "dc_shafiq", "Rising competitive org. Focus on tactical FPS and MOBA."),
            ("Crown Dynasty", "crown-dynasty", "dc_sumon", "Content + competition. Streaming-focused brand."),
        ]
        for name, slug, ceo_username, desc in orgs_data:
            ceo = self.user_map[ceo_username]
            org, _ = Organization.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "ceo": ceo, "description": desc, "is_verified": True},
            )
            self.org_map[slug] = org
        self.stdout.write(f"  {len(self.org_map)} organizations ready.")

    # ───────────────────────────────────────────────────────────────
    # TEAMS
    # ───────────────────────────────────────────────────────────────

    def _create_teams(self):
        self.stdout.write("Creating teams...")
        for team_data in TEAMS:
            name, tag, game_name, org_slug, owner_username, members = team_data
            game = self.game_map.get(game_name)
            if not game:
                self.stdout.write(self.style.WARNING(f"  Game '{game_name}' not found, skipping team {name}"))
                continue

            owner = self.user_map.get(owner_username)
            if not owner:
                continue

            org = self.org_map.get(org_slug) if org_slug else None
            team_slug = slugify(name)

            team, created = Team.objects.get_or_create(
                slug=team_slug,
                defaults={
                    "name": name,
                    "tag": tag,
                    "game_id": game.id,
                    "organization": org,
                    "created_by": owner,
                    "region": "BD",
                    "status": TeamStatus.ACTIVE,
                    "visibility": "PUBLIC",
                    "platform": "PC",
                    "is_recruiting": True,
                }
            )
            self.team_map[name] = team

            # Create legacy team for GroupStanding FK compat
            with legacy_write_bypass(reason="seed_legacy"):
                lt, _ = LegacyTeam.objects.get_or_create(
                    slug=team_slug,
                    defaults={
                        "name": name,
                        "tag": tag or name[:3].upper(),
                        "game": game.slug,
                        "region": "BD",
                    }
                )
                self.legacy_map[name] = lt

            # Owner membership
            self._add_membership(team, owner, game, "OWNER", "STARTER", True, org)

            # Other members
            for m_username, m_role, m_slot, m_capt in members:
                if m_role == "PLAYER_SKIP":
                    continue  # Skip constraint violations
                m_user = self.user_map.get(m_username)
                if not m_user:
                    continue

                # Check if user already on a team for this game
                key = (m_username, game_name)
                if key in self.user_game_assignments and org is None:
                    # Only enforce for independent teams
                    continue
                self._add_membership(team, m_user, game, m_role, m_slot, m_capt, org)
                self.user_game_assignments[key] = name

            # Mark owner assignment
            self.user_game_assignments[(owner_username, game_name)] = name

        self.stdout.write(f"  {len(self.team_map)} teams ready.")

    def _add_membership(self, team, user, game, role, slot, is_captain, org):
        """Add a team membership, skipping duplicates."""
        try:
            TeamMembership.objects.get_or_create(
                team=team,
                user=user,
                defaults={
                    "game_id": game.id,
                    "organization_id": org.id if org else None,
                    "status": MembershipStatus.ACTIVE,
                    "role": getattr(MembershipRole, role),
                    "roster_slot": getattr(RosterSlot, slot) if slot else None,
                    "is_tournament_captain": is_captain,
                }
            )
        except Exception as e:
            if "unique" not in str(e).lower() and "constraint" not in str(e).lower():
                self.stdout.write(self.style.WARNING(f"  Membership error {user.username} -> {team.name}: {e}"))

    # ───────────────────────────────────────────────────────────────
    # HELPER: Create tournament
    # ───────────────────────────────────────────────────────────────

    def _make_tournament(self, **kwargs):
        """Create or get a tournament by slug."""
        slug = kwargs.pop("slug")
        t, created = Tournament.objects.get_or_create(slug=slug, defaults=kwargs)
        if created:
            self.stdout.write(f"  Created tournament: {t.name}")
        return t

    def _register_team(self, tournament, team, status="confirmed", seed=None):
        """Register a team for a tournament (XOR: team_id only, no user)."""
        reg, _ = Registration.objects.get_or_create(
            tournament=tournament,
            team_id=team.id,
            defaults={
                "status": status,
                "seed": seed,
            }
        )
        return reg

    def _register_solo(self, tournament, user, status="confirmed", seed=None):
        reg, _ = Registration.objects.get_or_create(
            tournament=tournament,
            user=user,
            defaults={
                "status": status,
                "seed": seed,
            }
        )
        return reg

    def _make_match(self, tournament, p1_id, p2_id, round_num, state, score1=None, score2=None, winner_id=None, scheduled=None):
        """Create a match."""
        self._match_counter = getattr(self, '_match_counter', 0) + 1
        # Determine loser_id when winner is known
        loser_id = None
        if winner_id:
            loser_id = p2_id if winner_id == p1_id else p1_id
        m = Match.objects.create(
            tournament=tournament,
            participant1_id=p1_id,
            participant2_id=p2_id,
            round_number=round_num,
            match_number=self._match_counter,
            state=state,
            participant1_score=score1 or 0,
            participant2_score=score2 or 0,
            winner_id=winner_id,
            loser_id=loser_id,
            scheduled_time=scheduled or (NOW - timedelta(days=random.randint(1, 60))),
        )
        return m

    # ───────────────────────────────────────────────────────────────
    # COMPLETED TOURNAMENTS (T1–T5)
    # ───────────────────────────────────────────────────────────────

    def _create_completed_tournaments(self):
        self.stdout.write("Creating completed tournaments (T1-T5)...")
        organizer = self.user_map["dc_omar"]

        # T1: Valorant Invitational (Group Playoff)
        self._create_t1(organizer)
        # T2: CS2 Masters (Single Elim)
        self._create_t2(organizer)
        # T3: LoL Rift Clash (Single Elim)
        self._create_t3(organizer)
        # T4: RL Nitro Cup (Round Robin)
        self._create_t4(organizer)
        # T5: FC25 Weekend League (Solo SE)
        self._create_t5(organizer)

    def _create_t1(self, organizer):
        """T1: Valorant Invitational - Group Playoff, completed"""
        game = self.game_map["Valorant"]
        t = self._make_tournament(
            name="DeltaCrown Valorant Invitationals: Season 1",
            slug="valorant-invitational-s1",
            game=game, organizer=organizer,
            format="group_playoff", participation_type="team",
            platform="pc", mode="online",
            max_participants=12, min_participants=8,
            registration_start=NOW - timedelta(days=90),
            registration_end=NOW - timedelta(days=75),
            tournament_start=NOW - timedelta(days=70),
            tournament_end=NOW - timedelta(days=40),
            prize_pool=Decimal("50000.00"),
            status="completed", is_official=True, is_featured=True,
            description="The flagship Valorant tournament of Bangladesh. Top 12 teams battle for the crown.",
        )

        val_teams = ["Crimson Syndicate", "Velocity X BD", "Dhaka Leviathans",
                      "Titan Valorant", "Headhunterz", "AimBot Activated"]
        teams = [self.team_map[n] for n in val_teams if n in self.team_map]

        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)

        # Create bracket
        bracket, _ = Bracket.objects.get_or_create(
            tournament=t,
            defaults={
                "format": "group-stage",
                "bracket_structure": {"winner": val_teams[0] if val_teams else "TBD"},
            }
        )

        # Create some matches with results
        if len(teams) >= 2:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 13, 7, teams[0].id,
                             NOW - timedelta(days=50))
        if len(teams) >= 4:
            self._make_match(t, teams[2].id, teams[3].id, 1, "completed", 13, 11, teams[2].id,
                             NOW - timedelta(days=48))
        if len(teams) >= 2:
            # Grand Final
            self._make_match(t, teams[0].id, teams[1].id, 3, "completed", 3, 1, teams[0].id,
                             NOW - timedelta(days=40))

    def _create_t2(self, organizer):
        """T2: CS2 Masters - Single Elimination, completed"""
        game = self.game_map["CS2"]
        t = self._make_tournament(
            name="CS2 Masters: Bangladesh Edition",
            slug="cs2-masters-bd",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=80),
            registration_end=NOW - timedelta(days=70),
            tournament_start=NOW - timedelta(days=65),
            tournament_end=NOW - timedelta(days=45),
            prize_pool=Decimal("30000.00"),
            entry_fee_amount=Decimal("200.00"), has_entry_fee=True,
            status="completed", is_official=True,
            description="CS2 Masters: The best CS2 teams in Bangladesh compete.",
        )
        cs_teams = ["Old School BD", "Dust2 Demons", "Mirage Kings", "Global Elites"]
        teams = [self.team_map[n] for n in cs_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)

        Bracket.objects.get_or_create(tournament=t, defaults={
            "format": "single-elimination",
            "bracket_structure": {"winner": cs_teams[0]},
        })

        if len(teams) >= 4:
            self._make_match(t, teams[0].id, teams[3].id, 1, "completed", 16, 10, teams[0].id)
            self._make_match(t, teams[1].id, teams[2].id, 1, "completed", 16, 14, teams[1].id)
            self._make_match(t, teams[0].id, teams[1].id, 2, "completed", 16, 12, teams[0].id)

    def _create_t3(self, organizer):
        """T3: LoL Rift Clash - Single Elimination, completed"""
        game = self.game_map["League of Legends"]
        t = self._make_tournament(
            name="League of Legends Rift Clash: Season 1",
            slug="lol-rift-clash-s1",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=70),
            registration_end=NOW - timedelta(days=60),
            tournament_start=NOW - timedelta(days=55),
            tournament_end=NOW - timedelta(days=40),
            prize_pool=Decimal("20000.00"),
            status="completed",
            description="League of Legends Rift Clash Season 1.",
        )
        lol_teams = ["Fury Esports", "Mystic Legion", "Echo Rift"]
        teams = [self.team_map[n] for n in lol_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "single-elimination", "bracket_structure": {"winner": lol_teams[0]}})
        if len(teams) >= 2:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 3, 1, teams[0].id)

    def _create_t4(self, organizer):
        """T4: RL Nitro Cup - Round Robin, completed"""
        game = self.game_map["Rocket League"]
        t = self._make_tournament(
            name="Rocket League Nitro Cup",
            slug="rl-nitro-cup",
            game=game, organizer=organizer,
            format="round_robin", participation_type="team",
            platform="pc", mode="online",
            max_participants=4, min_participants=3,
            registration_start=NOW - timedelta(days=55),
            registration_end=NOW - timedelta(days=45),
            tournament_start=NOW - timedelta(days=42),
            tournament_end=NOW - timedelta(days=30),
            prize_pool=Decimal("10000.00"),
            status="completed",
            description="Rocket League Nitro Cup.",
        )
        rl_teams = ["Nitro Speed", "Flip Reset FC", "Car Go Brr"]
        teams = [self.team_map[n] for n in rl_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "round-robin", "bracket_structure": {"winner": rl_teams[0]}})
        if len(teams) >= 3:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 5, 2, teams[0].id)
            self._make_match(t, teams[0].id, teams[2].id, 1, "completed", 4, 1, teams[0].id)
            self._make_match(t, teams[1].id, teams[2].id, 1, "completed", 3, 2, teams[1].id)

    def _create_t5(self, organizer):
        """T5: FC25 Weekend League - Solo SE, completed"""
        game = self.game_map["FC 25"]
        t = self._make_tournament(
            name="FC 25 Weekend League #1",
            slug="fc25-weekend-league-1",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="solo",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=40),
            registration_end=NOW - timedelta(days=35),
            tournament_start=NOW - timedelta(days=33),
            tournament_end=NOW - timedelta(days=30),
            prize_pool=Decimal("5000.00"),
            status="completed",
            description="FC 25 Weekend League #1 - Solo.",
        )
        fc_players = ["dc_fc_master", "dc_goal_king", "dc_striker", "dc_dribble",
                       "dc_hasan", "dc_goal_miss", "dc_offside_king", "dc_fc_draw"]
        users = [self.user_map[u] for u in fc_players if u in self.user_map]
        for i, u in enumerate(users):
            self._register_solo(t, u, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "single-elimination", "bracket_structure": {"winner": "dc_fc_master"}})
        if len(users) >= 4:
            self._make_match(t, users[0].id, users[7].id if len(users) > 7 else users[3].id, 1, "completed", 3, 0, users[0].id)
            self._make_match(t, users[1].id, users[2].id, 1, "completed", 2, 1, users[1].id)
            self._make_match(t, users[0].id, users[1].id, 2, "completed", 4, 2, users[0].id)

    # ───────────────────────────────────────────────────────────────
    # LIVE TOURNAMENTS (T6–T10)
    # ───────────────────────────────────────────────────────────────

    def _create_live_tournaments(self):
        self.stdout.write("Creating live tournaments (T6-T10)...")
        organizer = self.user_map["dc_omar"]
        self._create_t6(organizer)
        self._create_t7(organizer)
        self._create_t8(organizer)
        self._create_t9(organizer)
        self._create_t10(organizer)

    def _create_t6(self, organizer):
        """T6: Radiant Rising S2 - Double Elim, live"""
        game = self.game_map["Valorant"]
        t = self._make_tournament(
            name="Radiant Rising: Season 2",
            slug="radiant-rising-s2",
            game=game, organizer=organizer,
            format="double_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=25),
            registration_end=NOW - timedelta(days=18),
            tournament_start=NOW - timedelta(days=14),
            prize_pool=Decimal("40000.00"),
            entry_fee_amount=Decimal("500.00"), has_entry_fee=True,
            status="live", is_featured=True,
            description="Radiant Rising Season 2. Double elimination bracket.",
        )
        val_teams = ["Crimson Syndicate", "Velocity X BD", "Dhaka Leviathans",
                      "Titan Valorant", "Headhunterz", "AimBot Activated"]
        teams = [self.team_map[n] for n in val_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "double-elimination", "bracket_structure": {}})
        # WB R1 matches (completed)
        if len(teams) >= 4:
            self._make_match(t, teams[0].id, teams[3].id, 1, "completed", 13, 8, teams[0].id, NOW - timedelta(days=10))
            self._make_match(t, teams[1].id, teams[2].id, 1, "completed", 13, 11, teams[1].id, NOW - timedelta(days=10))
        # WB R2 (1 completed, 1 scheduled)
        if len(teams) >= 2:
            self._make_match(t, teams[0].id, teams[1].id, 2, "completed", 13, 9, teams[0].id, NOW - timedelta(days=5))
        # LB matches scheduled
        if len(teams) >= 4:
            self._make_match(t, teams[2].id, teams[3].id, 2, "scheduled", scheduled=NOW + timedelta(days=2))

    def _create_t7(self, organizer):
        """T7: Ancient Defense Cup - Double Elim, live"""
        game = self.game_map["Dota 2"]
        t = self._make_tournament(
            name="Ancient Defense Cup",
            slug="ancient-defense-cup",
            game=game, organizer=organizer,
            format="double_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=20),
            registration_end=NOW - timedelta(days=14),
            tournament_start=NOW - timedelta(days=10),
            prize_pool=Decimal("25000.00"),
            status="live",
            description="Ancient Defense Cup. Dota 2 double elimination.",
        )
        dota_teams = ["Ancient Defense", "Roshan Raiders", "Ward Vision"]
        teams = [self.team_map[n] for n in dota_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "double-elimination", "bracket_structure": {}})
        if len(teams) >= 2:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 2, 0, teams[0].id, NOW - timedelta(days=7))
        if len(teams) >= 3:
            self._make_match(t, teams[1].id, teams[2].id, 2, "live", scheduled=NOW - timedelta(days=1))

    def _create_t8(self, organizer):
        """T8: Apex Survival Series - Round Robin, live"""
        game = self.game_map["Apex Legends"]
        t = self._make_tournament(
            name="Apex Legends Survival Series",
            slug="apex-survival-series",
            game=game, organizer=organizer,
            format="round_robin", participation_type="team",
            platform="pc", mode="online",
            max_participants=4, min_participants=3,
            registration_start=NOW - timedelta(days=18),
            registration_end=NOW - timedelta(days=12),
            tournament_start=NOW - timedelta(days=8),
            prize_pool=Decimal("15000.00"),
            status="live",
            description="Apex Legends Survival Series.",
        )
        apex_teams = ["Apex Predators BD", "Zone Survivors", "Loot Goblins"]
        teams = [self.team_map[n] for n in apex_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "round-robin", "bracket_structure": {}})
        if len(teams) >= 3:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 3, 1, teams[0].id, NOW - timedelta(days=5))
            self._make_match(t, teams[0].id, teams[2].id, 1, "completed", 3, 0, teams[0].id, NOW - timedelta(days=3))
            self._make_match(t, teams[1].id, teams[2].id, 1, "scheduled", scheduled=NOW + timedelta(days=1))

    def _create_t9(self, organizer):
        """T9: OW2 Payload Push - Single Elim, live"""
        game = self.game_map["Overwatch 2"]
        t = self._make_tournament(
            name="Overwatch 2 Payload Push",
            slug="ow2-payload-push",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=4, min_participants=2,
            registration_start=NOW - timedelta(days=15),
            registration_end=NOW - timedelta(days=10),
            tournament_start=NOW - timedelta(days=6),
            prize_pool=Decimal("12000.00"),
            status="live",
            description="Overwatch 2 Payload Push.",
        )
        ow_teams = ["Payload Pushers", "Point Capture"]
        teams = [self.team_map[n] for n in ow_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "single-elimination", "bracket_structure": {}})
        if len(teams) >= 2:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 3, 1, teams[0].id, NOW - timedelta(days=3))

    def _create_t10(self, organizer):
        """T10: Nitro Speed Cup S2 - Round Robin, live (all matches done, awaiting close)"""
        game = self.game_map["Rocket League"]
        t = self._make_tournament(
            name="Nitro Speed Cup: Season 2",
            slug="nitro-speed-cup-s2",
            game=game, organizer=organizer,
            format="round_robin", participation_type="team",
            platform="pc", mode="online",
            max_participants=4, min_participants=3,
            registration_start=NOW - timedelta(days=12),
            registration_end=NOW - timedelta(days=8),
            tournament_start=NOW - timedelta(days=5),
            prize_pool=Decimal("8000.00"),
            status="live",
            description="Nitro Speed Cup Season 2. All matches done, waiting for organizer to close.",
        )
        rl_teams = ["Nitro Speed", "Flip Reset FC", "Car Go Brr"]
        teams = [self.team_map[n] for n in rl_teams if n in self.team_map]
        for i, team in enumerate(teams):
            self._register_team(t, team, seed=i + 1)
        Bracket.objects.get_or_create(tournament=t, defaults={"format": "round-robin", "bracket_structure": {}})
        if len(teams) >= 3:
            self._make_match(t, teams[0].id, teams[1].id, 1, "completed", 5, 2, teams[0].id, NOW - timedelta(days=3))
            self._make_match(t, teams[0].id, teams[2].id, 1, "completed", 4, 1, teams[0].id, NOW - timedelta(days=2))
            self._make_match(t, teams[1].id, teams[2].id, 1, "completed", 3, 2, teams[1].id, NOW - timedelta(days=1))

    # ───────────────────────────────────────────────────────────────
    # OPEN REGISTRATION TOURNAMENTS (T11–T15)
    # ───────────────────────────────────────────────────────────────

    def _create_open_tournaments(self):
        self.stdout.write("Creating open registration tournaments (T11-T15)...")
        organizer = self.user_map["dc_omar"]
        self._create_t11(organizer)
        self._create_t12(organizer)
        self._create_t13(organizer)
        self._create_t14(organizer)
        self._create_t15(organizer)

    def _create_t11(self, organizer):
        """T11: Community Scrims #44 - Open, 8/16 registered"""
        game = self.game_map["Valorant"]
        t = self._make_tournament(
            name="Community Scrims #44 (Friday Night)",
            slug="valorant-scrims-44",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="team",
            platform="pc", mode="online",
            max_participants=16, min_participants=4,
            registration_start=NOW - timedelta(days=5),
            registration_end=NOW + timedelta(days=3),
            tournament_start=NOW + timedelta(days=5),
            prize_pool=Decimal("0.00"),
            status="registration_open",
            description="Weekly community scrims. Free entry. All skill levels welcome.",
        )
        # Register 8 teams (half full)
        val_teams = ["Crimson Syndicate", "Velocity X BD", "Dhaka Leviathans",
                      "Titan Valorant", "Headhunterz", "AimBot Activated"]
        for name in val_teams:
            if name in self.team_map:
                self._register_team(t, self.team_map[name])

    def _create_t12(self, organizer):
        """T12: CS2 Comp League - Open, 6/8 (almost full)"""
        game = self.game_map["CS2"]
        t = self._make_tournament(
            name="CS2 Competitive League: Spring 2026",
            slug="cs2-comp-league-spring",
            game=game, organizer=organizer,
            format="group_playoff", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=7),
            registration_end=NOW + timedelta(days=5),
            tournament_start=NOW + timedelta(days=10),
            prize_pool=Decimal("20000.00"),
            entry_fee_amount=Decimal("500.00"), has_entry_fee=True,
            status="registration_open",
            description="CS2 Competitive League Spring 2026. Almost full!",
        )
        cs_teams = ["Old School BD", "Dust2 Demons", "Mirage Kings", "Global Elites"]
        for i, name in enumerate(cs_teams):
            if name in self.team_map:
                # Mix of confirmed and payment pending
                status = "confirmed" if i < 3 else "payment_submitted"
                self._register_team(t, self.team_map[name], status=status)

    def _create_t13(self, organizer):
        """T13: FC25 Solo Championship - Open, empty"""
        game = self.game_map["FC 25"]
        t = self._make_tournament(
            name="FC 25 Solo Championship",
            slug="fc25-solo-championship",
            game=game, organizer=organizer,
            format="single_elimination", participation_type="solo",
            platform="pc", mode="online",
            max_participants=16, min_participants=4,
            registration_start=NOW - timedelta(days=2),
            registration_end=NOW + timedelta(days=7),
            tournament_start=NOW + timedelta(days=10),
            prize_pool=Decimal("10000.00"),
            entry_fee_amount=Decimal("50.00"), has_entry_fee=True,
            status="registration_open",
            description="FC 25 Solo Championship. Be the first to register!",
        )
        # No registrations — empty state test

    def _create_t14(self, organizer):
        """T14: LoL Rift Clash S2 - Open, mixed status registrations"""
        game = self.game_map["League of Legends"]
        t = self._make_tournament(
            name="LoL Rift Clash: Season 2",
            slug="lol-rift-clash-s2",
            game=game, organizer=organizer,
            format="round_robin", participation_type="team",
            platform="pc", mode="online",
            max_participants=6, min_participants=4,
            registration_start=NOW - timedelta(days=5),
            registration_end=NOW + timedelta(days=10),
            tournament_start=NOW + timedelta(days=14),
            prize_pool=Decimal("15000.00"),
            entry_fee_amount=Decimal("300.00"), has_entry_fee=True,
            status="registration_open",
            description="LoL Rift Clash Season 2. Payment verification in progress.",
        )
        lol_teams = ["Fury Esports", "Mystic Legion", "Echo Rift"]
        statuses = ["confirmed", "confirmed", "payment_submitted"]
        for name, st in zip(lol_teams, statuses):
            if name in self.team_map:
                self._register_team(t, self.team_map[name], status=st)

    def _create_t15(self, organizer):
        """T15: Dota 2 Guardian Cup - Swiss, half full"""
        game = self.game_map["Dota 2"]
        t = self._make_tournament(
            name="Dota 2 Guardian Cup",
            slug="dota2-guardian-cup",
            game=game, organizer=organizer,
            format="swiss", participation_type="team",
            platform="pc", mode="online",
            max_participants=8, min_participants=4,
            registration_start=NOW - timedelta(days=3),
            registration_end=NOW + timedelta(days=14),
            tournament_start=NOW + timedelta(days=18),
            prize_pool=Decimal("0.00"),
            status="registration_open",
            description="Dota 2 Guardian Cup. Swiss format. Free entry.",
        )
        dota_teams = ["Ancient Defense", "Roshan Raiders", "Ward Vision"]
        for name in dota_teams:
            if name in self.team_map:
                self._register_team(t, self.team_map[name])
