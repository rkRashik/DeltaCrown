"""
DeltaCrown Valorant Spring Showdown 2026 — Complete Tournament Seeder
=====================================================================

Seeds a fully-completed 16-team Valorant Double-Elimination tournament with
realistic Bangladeshi Gen-Z team/player names, full bracket (upper + lower),
match results with map scores, standings, config JSONB for TOC/Hub, prizes.

Creates:
  - 1 organizer user (reuses admin if exists)
  - 16 teams (5 players each = 80 player users)
  - 80 TeamMembership records
  - 1 Tournament (COMPLETED, double_elimination, Valorant)
    with full config JSONB (rules, streams, lobby, rosters)
  - 16 Registrations (CONFIRMED) + 16 Payments (VERIFIED)
  - 1 Bracket + 30 BracketNodes (UB + LB + GF)
  - 30 Matches (all COMPLETED with game_scores)
  - 1 TournamentResult (champion, runner-up, third)
  - 3 PrizeTransactions

Usage:
    python manage.py seed_spring_showdown
    python manage.py seed_spring_showdown --purge
    python manage.py seed_spring_showdown --purge --dry-run
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

TOURNAMENT_SLUG = "deltacrown-valorant-spring-2026"
TOURNAMENT_NAME = "DeltaCrown Valorant Spring Showdown 2026"
PASSWORD = "DeltaCrown2026!"
NOW = timezone.now()

VALORANT_MAPS = [
    "Ascent", "Bind", "Haven", "Split", "Icebox",
    "Breeze", "Lotus", "Sunset", "Pearl", "Abyss",
]

# ═══════════════════════════════════════════════════════════════════
# TEAM DATA — 16 Bangladeshi Gen-Z esports teams
# (name, tag, primary_color, accent_color)
# ═══════════════════════════════════════════════════════════════════

TEAMS_DATA = [
    # Seed 1–4 (top)
    ("Gulshan Snipers",      "GLS", "#FF4500", "#FFD700"),
    ("Mirpur Maniacs",       "MPM", "#1E90FF", "#00CED1"),
    ("Tejgaon Titans",       "TGT", "#9400D3", "#FF69B4"),
    ("Dhaka Drift",          "DKD", "#32CD32", "#ADFF2F"),
    # Seed 5–8
    ("Uttara Uprising",      "UTR", "#FF1493", "#FF6347"),
    ("Motijheel Monsters",   "MJM", "#DAA520", "#8B4513"),
    ("Banani Brawlers",      "BNB", "#FF69B4", "#FFC0CB"),
    ("Old Dhaka Ops",        "ODO", "#FF8C00", "#FFD700"),
    # Seed 9–12
    ("Bashundhara Beasts",   "BSB", "#4169E1", "#87CEEB"),
    ("Dhanmondi Demons",     "DMD", "#00BFFF", "#1E90FF"),
    ("Farmgate Phantoms",    "FGP", "#8B4513", "#D2691E"),
    ("Mohammadpur Mayhem",   "MPH", "#C0C0C0", "#708090"),
    # Seed 13–16
    ("Rampura Reapers",      "RMR", "#FF4500", "#DC143C"),
    ("Khilgaon Knights",     "KGK", "#DC143C", "#B22222"),
    ("Wari Warriors",        "WRW", "#9932CC", "#BA55D3"),
    ("Shyamoli Shadows",     "SMS", "#228B22", "#00FF00"),
]

# ═══════════════════════════════════════════════════════════════════
# PLAYER DATA — 5 per team
# ═══════════════════════════════════════════════════════════════════

PLAYERS_BY_TEAM = {
    "GLS": [
        ("gls_headhuntr",    "HeadHuntr",     "PLAYER", "Duelist"),
        ("gls_flashvai",     "FlashVai",      "PLAYER", "Initiator"),
        ("gls_smokeking",    "SmokeKing",     "PLAYER", "Controller"),
        ("gls_wallbhai",     "WallBhai",      "PLAYER", "Sentinel"),
        ("gls_brainboss",    "BrainBoss",     "PLAYER", "IGL"),
    ],
    "MPM": [
        ("mpm_flicklord",    "FlickLord",     "PLAYER", "Duelist"),
        ("mpm_dartmaster",   "DartMaster",    "PLAYER", "Initiator"),
        ("mpm_hazebhai",     "HazeBhai",      "PLAYER", "Controller"),
        ("mpm_anchormama",   "AnchorMama",    "PLAYER", "Sentinel"),
        ("mpm_calloutvai",   "CalloutVai",    "PLAYER", "IGL"),
    ],
    "TGT": [
        ("tgt_entryking",    "EntryKing",     "PLAYER", "Duelist"),
        ("tgt_infogatherer", "InfoGatherer",  "PLAYER", "Initiator"),
        ("tgt_viperpit",     "ViperPit",      "PLAYER", "Controller"),
        ("tgt_tripwire",     "TripWire",      "PLAYER", "Sentinel"),
        ("tgt_stratman",     "StratMan",       "PLAYER", "IGL"),
    ],
    "DKD": [
        ("dkd_rushmaster",   "RushMaster",    "PLAYER", "Duelist"),
        ("dkd_flashbang",    "FlashBang",     "PLAYER", "Initiator"),
        ("dkd_brimvai",      "BrimVai",       "PLAYER", "Controller"),
        ("dkd_sagewall",     "SageWall",      "PLAYER", "Sentinel"),
        ("dkd_driftcall",    "DriftCall",     "PLAYER", "IGL"),
    ],
    "UTR": [
        ("utr_jettdif",      "JettDif",       "PLAYER", "Duelist"),
        ("utr_sovadartt",    "SovaDartt",     "PLAYER", "Initiator"),
        ("utr_omenbhai",     "OmenBhai",      "PLAYER", "Controller"),
        ("utr_killjoybd",    "KilljoyBD",     "PLAYER", "Sentinel"),
        ("utr_risecall",     "RiseCall",      "PLAYER", "IGL"),
    ],
    "MJM": [
        ("mjm_onedeag",      "OneDeag",       "PLAYER", "Duelist"),
        ("mjm_fademaster",   "FadeMaster",    "PLAYER", "Initiator"),
        ("mjm_astraking",    "AstraKing",     "PLAYER", "Controller"),
        ("mjm_chamber_op",   "ChamberOP",     "PLAYER", "Sentinel"),
        ("mjm_motiigl",      "MotiIGL",       "PLAYER", "IGL"),
    ],
    "BNB": [
        ("bnb_razeblast",    "RazeBlast",     "PLAYER", "Duelist"),
        ("bnb_skyedif",      "SkyeDif",       "PLAYER", "Initiator"),
        ("bnb_harborbhai",   "HarborBhai",    "PLAYER", "Controller"),
        ("bnb_deadlockda",   "DeadlockDa",   "PLAYER", "Sentinel"),
        ("bnb_bananiigl",    "BananiIGL",     "PLAYER", "IGL"),
    ],
    "ODO": [
        ("odo_phoenixvai",   "PhoenixVai",    "PLAYER", "Duelist"),
        ("odo_breachbhai",   "BreachBhai",    "PLAYER", "Initiator"),
        ("odo_clovemix",     "CloveMix",      "PLAYER", "Controller"),
        ("odo_cypher_eye",   "CypherEye",     "PLAYER", "Sentinel"),
        ("odo_puran_igl",    "PuranIGL",      "PLAYER", "IGL"),
    ],
    "BSB": [
        ("bsb_neonrush",     "NeonRush",      "PLAYER", "Duelist"),
        ("bsb_kayovai",      "KayoVai",       "PLAYER", "Initiator"),
        ("bsb_brimstone_bd", "BrimstoneBD",   "PLAYER", "Controller"),
        ("bsb_lockdown",     "Lockdown",      "PLAYER", "Sentinel"),
        ("bsb_beastigl",     "BeastIGL",      "PLAYER", "IGL"),
    ],
    "DMD": [
        ("dmd_yorutrick",    "YoruTrick",     "PLAYER", "Duelist"),
        ("dmd_geckomama",    "GeckoMama",     "PLAYER", "Initiator"),
        ("dmd_clovehaze",    "CloveHaze",     "PLAYER", "Controller"),
        ("dmd_sageheal",     "SageHeal",      "PLAYER", "Sentinel"),
        ("dmd_lanevai",      "LaneVai",       "PLAYER", "IGL"),
    ],
    "FGP": [
        ("fgp_reynasip",     "ReynaSip",      "PLAYER", "Duelist"),
        ("fgp_sovadart",     "SovaDart",      "PLAYER", "Initiator"),
        ("fgp_vipercha",     "ViperCha",      "PLAYER", "Controller"),
        ("fgp_killjoykd",    "KilljoyKD",     "PLAYER", "Sentinel"),
        ("fgp_gateigl",      "GateIGL",       "PLAYER", "IGL"),
    ],
    "MPH": [
        ("mph_isomain",      "IsoMain",       "PLAYER", "Duelist"),
        ("mph_fadefish",      "FadeFish",      "PLAYER", "Initiator"),
        ("mph_omenriver",    "OmenRiver",     "PLAYER", "Controller"),
        ("mph_sagehilsa",    "SageHilsa",     "PLAYER", "Sentinel"),
        ("mph_mohaigl",      "MohaIGL",       "PLAYER", "IGL"),
    ],
    "RMR": [
        ("rmr_jettspice",    "JettSpice",     "PLAYER", "Duelist"),
        ("rmr_breachfire",   "BreachFire",    "PLAYER", "Initiator"),
        ("rmr_astramix",     "AstraMix",      "PLAYER", "Controller"),
        ("rmr_chamberjk",    "ChamberJK",     "PLAYER", "Sentinel"),
        ("rmr_rampuraigl",   "RampuraIGL",    "PLAYER", "IGL"),
    ],
    "KGK": [
        ("kgk_razeride",     "RazeRide",      "PLAYER", "Duelist"),
        ("kgk_kayohonk",     "KayoHonk",      "PLAYER", "Initiator"),
        ("kgk_brimbell",     "BrimBell",      "PLAYER", "Controller"),
        ("kgk_deadlockrd",   "DeadlockRD",    "PLAYER", "Sentinel"),
        ("kgk_knightigl",    "KnightIGL",     "PLAYER", "IGL"),
    ],
    "WRW": [
        ("wrw_neonnagad",    "NeonNagad",     "PLAYER", "Duelist"),
        ("wrw_skyesend",     "SkyeSend",      "PLAYER", "Initiator"),
        ("wrw_harborpay",    "HarborPay",     "PLAYER", "Controller"),
        ("wrw_cyphercash",   "CypherCash",    "PLAYER", "Sentinel"),
        ("wrw_warigl",       "WarIGL",        "PLAYER", "IGL"),
    ],
    "SMS": [
        ("sms_phoenixgg",    "PhoenixGG",     "PLAYER", "Duelist"),
        ("sms_fadeposh",     "FadePosh",      "PLAYER", "Initiator"),
        ("sms_viperelite",   "ViperElite",    "PLAYER", "Controller"),
        ("sms_sage_shyam",   "SageShyam",     "PLAYER", "Sentinel"),
        ("sms_shadowigl",    "ShadowIGL",     "PLAYER", "IGL"),
    ],
}


def _ms(map_name, s1, s2):
    """Helper: build one map score dict."""
    w = 1 if s1 > s2 else 2
    return {
        "map_name": map_name,
        "team1_rounds": s1,
        "team2_rounds": s2,
        "winner_side": w,
        "team1_stats": {
            "kills": int(s1 * 4.8 + random.randint(-3, 5)),
            "deaths": int(s2 * 4.8 + random.randint(-3, 5)),
            "assists": int(s1 * 1.6 + random.randint(-2, 4)),
        },
        "team2_stats": {
            "kills": int(s2 * 4.8 + random.randint(-3, 5)),
            "deaths": int(s1 * 4.8 + random.randint(-3, 5)),
            "assists": int(s2 * 1.6 + random.randint(-2, 4)),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# DOUBLE ELIMINATION BRACKET for 16 teams
#
# UB = Upper Bracket, LB = Lower Bracket, GF = Grand Final
# Seeding: 1v16, 8v9, 5v12, 4v13, 3v14, 6v11, 7v10, 2v15
#
# UPPER BRACKET:
#   UB-R1 (8 matches) → UB-QF (4) → UB-SF (2) → UB-Final (1)
# LOWER BRACKET:
#   LB-R1 (4 matches, UB-R1 losers paired) →
#   LB-R2 (4 matches, LB-R1 winners vs UB-QF losers) →
#   LB-R3 (2 matches) →
#   LB-R4 (2 matches, LB-R3 winners vs UB-SF losers) →
#   LB-R5 (1 match) →
#   LB-Final (1 match, LB-R5 winner vs UB-Final loser)
# GRAND FINAL:
#   GF (1 match, UB-Final winner vs LB-Final winner)
#
# Total: 8+4+2+1 + 4+4+2+2+1+1 + 1 = 30 matches
# ═══════════════════════════════════════════════════════════════════

# Match definition: (match_num, bracket_type, round_label,
#   p1_source, p2_source, winner_idx, best_of, map_scores)
# p1_source / p2_source are either:
#   - seed index (int) for first round, OR
#   - ("W", match_num) / ("L", match_num) for subsequent rounds

# We'll define results using team seed indices (0-based in TEAMS_DATA)

CHAMPION_IDX = 0      # Gulshan Snipers (seed 1)
RUNNER_UP_IDX = 2     # Tejgaon Titans (seed 3) — came from LB
THIRD_PLACE_IDX = 3   # Dhaka Drift (seed 4) — lost in LB Final

PRIZE_DISTRIBUTION = {
    CHAMPION_IDX: Decimal("10000.00"),
    RUNNER_UP_IDX: Decimal("6000.00"),
    THIRD_PLACE_IDX: Decimal("4000.00"),
}

# Pre-compute all match outcomes for the double-elim bracket.
# Format: list of tuples:
# (match_num, bracket_type, round_label, p1_idx, p2_idx, winner_idx, best_of, map_scores)

MATCH_RESULTS = [
    # ═══ UPPER BRACKET ROUND 1 (BO3) — 8 matches ═══
    # Standard seeding: 1v16, 8v9, 5v12, 4v13, 3v14, 6v11, 7v10, 2v15
    (1,  "main", "UB Round 1", 0, 15, 0,  3, [_ms("Ascent", 13, 5),  _ms("Bind", 13, 8)]),
    (2,  "main", "UB Round 1", 7,  8, 8,  3, [_ms("Haven", 10, 13),  _ms("Split", 13, 7), _ms("Icebox", 11, 13)]),
    (3,  "main", "UB Round 1", 4, 11, 4,  3, [_ms("Lotus", 13, 6),   _ms("Sunset", 13, 9)]),
    (4,  "main", "UB Round 1", 3, 12, 3,  3, [_ms("Pearl", 11, 13),  _ms("Ascent", 13, 4), _ms("Bind", 13, 10)]),
    (5,  "main", "UB Round 1", 2, 13, 2,  3, [_ms("Haven", 13, 7),   _ms("Split", 13, 8)]),
    (6,  "main", "UB Round 1", 5, 10, 5,  3, [_ms("Icebox", 13, 11), _ms("Lotus", 9, 13), _ms("Sunset", 13, 10)]),
    (7,  "main", "UB Round 1", 6,  9, 6,  3, [_ms("Pearl", 13, 7),   _ms("Ascent", 13, 10)]),
    (8,  "main", "UB Round 1", 1, 14, 1,  3, [_ms("Bind", 13, 3),    _ms("Haven", 13, 6)]),

    # UB-R1 Winners: 0(GLS), 8(BSB), 4(UTR), 3(DKD), 2(TGT), 5(MJM), 6(BNB), 1(MPM)
    # UB-R1 Losers:  15(SMS), 7(ODO), 11(MPH), 12(RMR), 13(KGK), 10(FGP), 9(DMD), 14(WRW)

    # ═══ UPPER BRACKET QUARTER-FINALS (BO3) — 4 matches ═══
    (9,  "main", "UB Quarter-Final", 0,  8, 0,  3, [_ms("Split", 11, 13), _ms("Ascent", 13, 7), _ms("Haven", 13, 9)]),
    (10, "main", "UB Quarter-Final", 4,  3, 3,  3, [_ms("Lotus", 13, 11), _ms("Bind", 10, 13), _ms("Sunset", 9, 13)]),
    (11, "main", "UB Quarter-Final", 2,  5, 2,  3, [_ms("Icebox", 13, 6), _ms("Ascent", 13, 9)]),
    (12, "main", "UB Quarter-Final", 6,  1, 1,  3, [_ms("Haven", 13, 11), _ms("Pearl", 5, 13), _ms("Split", 12, 14)]),

    # UB-QF Winners: 0(GLS), 3(DKD), 2(TGT), 1(MPM)
    # UB-QF Losers:  8(BSB), 4(UTR), 5(MJM), 6(BNB)

    # ═══ UPPER BRACKET SEMI-FINALS (BO3) — 2 matches ═══
    (13, "main", "UB Semi-Final",    0,  3, 0,  3, [_ms("Ascent", 13, 8),  _ms("Bind", 13, 11)]),
    (14, "main", "UB Semi-Final",    2,  1, 2,  3, [_ms("Haven", 13, 10),  _ms("Lotus", 9, 13), _ms("Split", 13, 11)]),

    # UB-SF Winners: 0(GLS), 2(TGT)
    # UB-SF Losers:  3(DKD), 1(MPM)

    # ═══ UPPER BRACKET FINAL (BO3) — 1 match ═══
    (15, "main", "UB Final",         0,  2, 0, 3, [_ms("Icebox", 13, 9),  _ms("Ascent", 11, 13), _ms("Haven", 13, 10)]),

    # UB Final Winner: 0(GLS) — goes to Grand Final from winners side
    # UB Final Loser:  2(TGT) — drops to LB Final

    # ═══ LOWER BRACKET ROUND 1 (BO3) — 4 matches ═══
    # UB-R1 losers paired: 15v7, 11v12, 13v10, 9v14
    (16, "losers", "LB Round 1", 15, 7,  7,  3, [_ms("Bind", 8, 13),   _ms("Ascent", 9, 13)]),
    (17, "losers", "LB Round 1", 11, 12, 12, 3, [_ms("Haven", 10, 13), _ms("Lotus", 13, 11), _ms("Split", 8, 13)]),
    (18, "losers", "LB Round 1", 13, 10, 10, 3, [_ms("Pearl", 9, 13),  _ms("Icebox", 7, 13)]),
    (19, "losers", "LB Round 1", 9, 14,  9,  3, [_ms("Sunset", 13, 8), _ms("Ascent", 13, 10)]),

    # LB-R1 Winners: 7(ODO), 12(RMR), 10(FGP), 9(DMD)

    # ═══ LOWER BRACKET ROUND 2 (BO3) — 4 matches ═══
    # LB-R1 winners vs UB-QF losers: 7v8, 12v4, 10v5, 9v6
    (20, "losers", "LB Round 2", 7,  8,  8,  3, [_ms("Haven", 9, 13),  _ms("Bind", 10, 13)]),
    (21, "losers", "LB Round 2", 12, 4,  4,  3, [_ms("Split", 13, 9),  _ms("Ascent", 7, 13), _ms("Lotus", 10, 13)]),
    (22, "losers", "LB Round 2", 10, 5,  5,  3, [_ms("Icebox", 11, 13), _ms("Sunset", 13, 11), _ms("Pearl", 10, 13)]),
    (23, "losers", "LB Round 2", 9,  6,  6,  3, [_ms("Haven", 13, 11), _ms("Bind", 7, 13),  _ms("Ascent", 9, 13)]),

    # LB-R2 Winners: 8(BSB), 4(UTR), 5(MJM), 6(BNB)

    # ═══ LOWER BRACKET ROUND 3 (BO3) — 2 matches ═══
    (24, "losers", "LB Round 3", 8,  4,  4,  3, [_ms("Lotus", 10, 13), _ms("Bind", 13, 11), _ms("Haven", 9, 13)]),
    (25, "losers", "LB Round 3", 5,  6,  5,  3, [_ms("Split", 13, 8),  _ms("Icebox", 13, 10)]),

    # LB-R3 Winners: 4(UTR), 5(MJM)

    # ═══ LOWER BRACKET ROUND 4 (BO3) — 2 matches ═══
    # LB-R3 winners vs UB-SF losers: 4v3, 5v1
    (26, "losers", "LB Round 4", 4,  3,  3, 3, [_ms("Ascent", 10, 13), _ms("Haven", 9, 13)]),
    (27, "losers", "LB Round 4", 5,  1,  1, 3, [_ms("Bind", 13, 11),  _ms("Lotus", 7, 13), _ms("Split", 10, 13)]),

    # LB-R4 Winners: 3(DKD), 1(MPM)

    # ═══ LOWER BRACKET ROUND 5 (BO3) — 1 match ═══
    (28, "losers", "LB Semi-Final", 3, 1, 3, 3, [_ms("Icebox", 13, 10), _ms("Ascent", 13, 11)]),

    # LB-R5 Winner: 3(DKD)

    # ═══ LOWER BRACKET FINAL (BO3) — 1 match ═══
    # LB-R5 winner (3, DKD) vs UB-Final loser (2, TGT)
    (29, "losers", "LB Final", 3, 2, 2, 3, [_ms("Haven", 13, 11), _ms("Bind", 9, 13), _ms("Split", 11, 13)]),

    # LB Final Winner: 2(TGT) — goes to Grand Final

    # ═══ GRAND FINAL (BO5) ═══
    # UB Final Winner (0, GLS) vs LB Final Winner (2, TGT)
    (30, "main", "Grand Final", 0, 2, 0, 5,
     [_ms("Ascent", 13, 9), _ms("Haven", 10, 13), _ms("Bind", 13, 8),
      _ms("Split", 13, 11)]),
    #  GLS wins 3-1 in Grand Final
]


# ═══════════════════════════════════════════════════════════════════
# TOURNAMENT CONFIG JSONB — feeds TOC APIs (rules, streams, lobby)
# ═══════════════════════════════════════════════════════════════════

TOURNAMENT_CONFIG = {
    "map_pool": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset"],
    "veto_format": "1-2-1-2-1-2",
    "third_place_match": False,
    "anti_cheat": "Vanguard",
    "rosters": {
        "locked": True,
        "lock_deadline": (NOW - timedelta(days=3)).isoformat(),
        "min_roster_size": 5,
        "max_roster_size": 7,
        "allow_subs": True,
        "max_subs": 2,
    },
    "streams": {
        "stations": [
            {
                "id": "station-1",
                "name": "DeltaCrown Main",
                "platform": "youtube",
                "url": "https://youtube.com/@DeltaCrownEsports/live",
                "status": "offline",
                "language": "Bangla",
                "assigned_to": None,
            },
            {
                "id": "station-2",
                "name": "DeltaCrown EN",
                "platform": "twitch",
                "url": "https://twitch.tv/deltacrown_en",
                "status": "offline",
                "language": "English",
                "assigned_to": None,
            },
        ],
        "vods": [
            {
                "id": "vod-1",
                "title": "Grand Final - GLS vs TGT",
                "url": "https://youtube.com/watch?v=example1",
                "match_id": 30,
                "thumbnail": "",
                "duration": "2:34:15",
                "created_at": NOW.isoformat(),
            },
            {
                "id": "vod-2",
                "title": "UB Final - GLS vs TGT",
                "url": "https://youtube.com/watch?v=example2",
                "match_id": 15,
                "thumbnail": "",
                "duration": "1:48:32",
                "created_at": NOW.isoformat(),
            },
        ],
        "overlay_api_key": "dc-overlay-spring-2026-xyz",
    },
    "lobby": {
        "auto_create": True,
        "default_region": "Mumbai",
        "spectator_slots_default": 2,
        "anticheat_required": True,
        "chat_enabled": True,
        "auto_close_minutes": 30,
        "servers": [
            {"id": "srv-1", "name": "Mumbai-1", "region": "Mumbai", "status": "online", "ip": "103.x.x.1"},
            {"id": "srv-2", "name": "Mumbai-2", "region": "Mumbai", "status": "online", "ip": "103.x.x.2"},
            {"id": "srv-3", "name": "Singapore-1", "region": "Singapore", "status": "online", "ip": "52.x.x.1"},
        ],
    },
    "rules_info": {
        "sections": [
            {
                "id": "sec-1",
                "title": "General Rules",
                "content": (
                    "All players must use Riot-verified Valorant accounts. "
                    "Teams must check in 30 minutes before their scheduled match. "
                    "All participants must be Bangladeshi residents."
                ),
                "order": 1,
                "updated_at": NOW.isoformat(),
            },
            {
                "id": "sec-2",
                "title": "Match Format",
                "content": (
                    "All matches are Best of 3 (BO3) except Grand Final which is Best of 5 (BO5). "
                    "Double Elimination bracket. Map veto format: 1-2-1-2-1-2 for BO3. "
                    "Standard Valorant overtime rules apply."
                ),
                "order": 2,
                "updated_at": NOW.isoformat(),
            },
            {
                "id": "sec-3",
                "title": "Anti-Cheat & Fair Play",
                "content": (
                    "Riot Vanguard is mandatory. Tournament admins will spectate random matches. "
                    "Any form of cheating results in permanent DQ. "
                    "BM/toxicity in match chat = warning, repeat offense = DQ."
                ),
                "order": 3,
                "updated_at": NOW.isoformat(),
            },
            {
                "id": "sec-4",
                "title": "Pauses & Technical Issues",
                "content": (
                    "Each team gets 2 tactical pauses per half (60 seconds each). "
                    "Technical pause limit: 10 minutes. If unresolved, admin will decide. "
                    "Disconnects: 5 min reconnect window."
                ),
                "order": 4,
                "updated_at": NOW.isoformat(),
            },
            {
                "id": "sec-5",
                "title": "Roster & Substitutions",
                "content": (
                    "Minimum 5 players, maximum 7 per team. "
                    "Substitutions allowed between maps (not mid-map). "
                    "Roster lock occurs 24 hours before tournament start."
                ),
                "order": 5,
                "updated_at": NOW.isoformat(),
            },
        ],
        "faq": [
            {"id": "faq-1", "question": "Can I use smurf accounts?", "answer": "No. Only your main Riot account is allowed.", "order": 1},
            {"id": "faq-2", "question": "What happens if my team is late?", "answer": "10-minute grace. After that, forfeit (0-2 loss).", "order": 2},
            {"id": "faq-3", "question": "How are prizes distributed?", "answer": "Via bKash/Nagad within 7 business days after tournament.", "order": 3},
            {"id": "faq-4", "question": "Is coaching allowed?", "answer": "Coaching is allowed only during timeouts, not during active rounds.", "order": 4},
        ],
        "prize_info": {
            "distribution": {"1st": "10,000 BDT", "2nd": "6,000 BDT", "3rd": "4,000 BDT"},
            "payment_method": "bKash / Nagad",
            "payment_schedule": "Within 7 business days",
            "notes": "Prize money sent to team captain's mobile wallet.",
        },
        "quick_reference": {
            "format": "Double Elimination",
            "checkin_time": "30 minutes before match",
            "match_format": "BO3 (BO5 Grand Final)",
            "map_pool": "Ascent, Bind, Haven, Split, Icebox, Lotus, Sunset",
            "special_rules": "Vanguard mandatory, 2 pauses per half",
            "contact": "tournaments@deltacrown.gg",
        },
        "versions": [
            {"version": "1.0", "changelog": "Initial rulebook published", "published_at": (NOW - timedelta(days=20)).isoformat(), "published_by": "admin"},
        ],
        "acknowledgements": {},
    },
}


class Command(BaseCommand):
    help = "Seed DeltaCrown Valorant Spring Showdown 2026 — 16-team DE tournament"

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true", help="Delete existing tournament data first")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")

    def handle(self, *args, **options):
        self.purge = options["purge"]
        self.dry_run = options["dry_run"]

        # Lazy imports
        from apps.games.models import Game
        from apps.organizations.models import Team, TeamMembership
        from apps.organizations.choices import (
            TeamStatus, MembershipStatus, MembershipRole, RosterSlot,
        )
        from apps.tournaments.models import (
            Tournament, Registration, Match, Bracket,
        )
        from apps.tournaments.models.bracket import BracketNode
        from apps.tournaments.models.registration import Payment
        from apps.tournaments.models.result import TournamentResult
        from apps.tournaments.models.prize import PrizeTransaction
        from apps.tournaments.models.payment_verification import PaymentVerification

        self.Game = Game
        self.Team = Team
        self.TeamMembership = TeamMembership
        self.TeamStatus = TeamStatus
        self.MembershipStatus = MembershipStatus
        self.MembershipRole = MembershipRole
        self.RosterSlot = RosterSlot
        self.Tournament = Tournament
        self.Registration = Registration
        self.Match = Match
        self.Bracket = Bracket
        self.BracketNode = BracketNode
        self.Payment = Payment
        self.PaymentVerification = PaymentVerification
        self.TournamentResult = TournamentResult
        self.PrizeTransaction = PrizeTransaction

        self._disconnect_signals()

        try:
            if self.purge:
                self._purge()

            if self.dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN - no data written"))
                return

            with transaction.atomic():
                organizer = self._get_or_create_organizer()
                game = self._get_or_create_game()
                teams, team_users = self._create_teams_and_players(game, organizer)
                tournament = self._create_tournament(organizer, game)
                registrations = self._create_registrations(tournament, teams, team_users, organizer)
                bracket = self._create_bracket(tournament)
                matches = self._create_matches(tournament, bracket, teams, registrations)
                self._create_bracket_nodes(bracket, matches, teams)
                self._create_result(tournament, registrations, organizer)
                self._create_prizes(tournament, registrations)
                self._create_player_stats(tournament, matches, teams, team_users)

            self.stdout.write(self.style.SUCCESS(
                f"\nSpring Showdown 2026 seeded successfully!"
                f"\n    Tournament: {tournament.name} (ID={tournament.id})"
                f"\n    Slug: {tournament.slug}"
                f"\n    Teams: {len(teams)}"
                f"\n    Matches: {len(matches)}"
                f"\n    Champion: {TEAMS_DATA[CHAMPION_IDX][0]}"
            ))
        finally:
            self._reconnect_signals()

    # ── Signal management ──
    def _disconnect_signals(self):
        try:
            from apps.user_profile.signals.activity_signals import (
                on_tournament_registration, on_match_completed,
            )
            from apps.tournaments.models import Registration, Match
            post_save.disconnect(on_tournament_registration, sender=Registration)
            post_save.disconnect(on_match_completed, sender=Match)

            # Disconnect user profile signals to avoid slow DB calls per user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            from apps.user_profile.signals.legacy_signals import ensure_profile
            post_save.disconnect(ensure_profile, sender=User)
            self.stdout.write("  User profile signal disconnected")

            self._signals_disconnected = True
            self.stdout.write("  Activity signals disconnected")
        except Exception as e:
            self._signals_disconnected = False
            self.stdout.write(self.style.WARNING(f"  Could not disconnect signals: {e}"))

    def _reconnect_signals(self):
        if not getattr(self, "_signals_disconnected", False):
            return
        try:
            from apps.user_profile.signals.activity_signals import (
                on_tournament_registration, on_match_completed,
            )
            from apps.tournaments.models import Registration, Match
            post_save.connect(on_tournament_registration, sender=Registration)
            post_save.connect(on_match_completed, sender=Match)

            from django.contrib.auth import get_user_model
            User = get_user_model()
            from apps.user_profile.signals.legacy_signals import ensure_profile
            post_save.connect(ensure_profile, sender=User)

            self.stdout.write("  All signals reconnected")
        except Exception:
            pass

    # ── Purge ──
    def _purge(self):
        self.stdout.write(self.style.WARNING("Purging existing data..."))

        # Purge THIS tournament + any old seeded tournaments
        # Use with_deleted() to also catch soft-deleted records
        slugs_to_purge = [
            TOURNAMENT_SLUG,
            "vct-champions-dhaka-2026",      # old seed
            "vct-champions-2026-bd",         # possible old slug
        ]

        # Get ALL tournaments (including soft-deleted) matching slugs
        try:
            tournaments = list(self.Tournament.objects.with_deleted().filter(slug__in=slugs_to_purge))
        except AttributeError:
            tournaments = list(self.Tournament.objects.filter(slug__in=slugs_to_purge))

        for t in tournaments:
            tid = t.id
            # Delete player stats first
            from apps.tournaments.models.match_player_stats import MatchPlayerStat, MatchMapPlayerStat
            MatchMapPlayerStat.objects.filter(match__tournament_id=tid).delete()
            MatchPlayerStat.objects.filter(match__tournament_id=tid).delete()
            self.PrizeTransaction.objects.filter(tournament_id=tid).delete()
            self.TournamentResult.objects.filter(tournament_id=tid).delete()
            self.BracketNode.objects.filter(bracket__tournament_id=tid).delete()
            self.Match.objects.filter(tournament_id=tid).delete()
            self.Bracket.objects.filter(tournament_id=tid).delete()
            self.PaymentVerification.objects.filter(registration__tournament_id=tid).delete()
            self.Payment.objects.filter(registration__tournament_id=tid).delete()
            self.Registration.objects.filter(tournament_id=tid).delete()
            # Hard delete (bypass soft delete)
            type(t).objects.with_deleted().filter(pk=tid).delete()
            self.stdout.write(f"  Deleted tournament ID={tid}")

        if not tournaments:
            self.stdout.write("  No existing tournaments found")

        # Delete seeded users (both old and new prefixes)
        prefixes = [td[1].lower() + "_" for td in TEAMS_DATA]
        # Also add old seed prefixes
        OLD_TAGS = ["bpc", "cch", "dkd", "mvc", "pmp", "kck", "msm", "afk",
                    "bbl", "sys", "cwc", "hlh", "jjk", "rkr", "nsn", "gwg"]
        for ot in OLD_TAGS:
            if ot + "_" not in prefixes:
                prefixes.append(ot + "_")
        for prefix in prefixes:
            users = User.objects.filter(username__startswith=prefix)
            c = users.count()
            if c:
                users.delete()
                self.stdout.write(f"  Deleted {c} users with prefix '{prefix}'")

        # Delete teams: both new tags and old tags (include soft-deleted)
        tags = [td[1] for td in TEAMS_DATA]
        old_team_tags = ["BPC", "CCH", "DKD", "MVC", "PMP", "KCK", "MSM", "AFK",
                         "BBL", "SYS", "CWC", "HLH", "JJK", "RKR", "NSN", "GWG"]
        all_tags = list(set(tags + old_team_tags))
        try:
            teams = self.Team.objects.with_deleted().filter(tag__in=all_tags)
        except AttributeError:
            teams = self.Team.objects.filter(tag__in=all_tags)
        if teams.exists():
            c = teams.count()
            self.TeamMembership.objects.filter(team__in=teams).delete()
            teams.delete()
            self.stdout.write(f"  Deleted {c} teams")

        self.stdout.write(self.style.SUCCESS("  Purge complete"))

    # ── Organizer ──
    def _get_or_create_organizer(self):
        user = User.objects.filter(is_superuser=True).first()
        if user:
            self.stdout.write(f"  Using existing superuser: {user.username}")
            return user
        user = User.objects.create_superuser(
            username="admin", email="admin@deltacrown.gg", password=PASSWORD,
        )
        self.stdout.write("  Created superuser: admin")
        return user

    # ── Game ──
    def _get_or_create_game(self):
        game = self.Game.objects.filter(slug="valorant").first()
        if game:
            self.stdout.write(f"  Found game: {game.name} (ID={game.id})")
            return game
        game = self.Game.objects.create(
            name="Valorant", slug="valorant",
            min_players_per_team=5, max_players_per_team=7, is_active=True,
        )
        self.stdout.write(f"  Created game: Valorant (ID={game.id})")
        return game

    # ── Teams & Players ──
    def _create_teams_and_players(self, game, organizer):
        self.stdout.write("\nCreating teams and players...")
        teams = []
        team_users = {}

        for idx, (name, tag, primary, accent) in enumerate(TEAMS_DATA):
            slug = slugify(name)

            # Lookup by tag+game_id (include soft-deleted to avoid slug conflicts)
            try:
                team = self.Team.objects.with_deleted().filter(tag=tag, game_id=game.id).first()
            except AttributeError:
                team = self.Team.objects.filter(tag=tag, game_id=game.id).first()
            if team:
                created = False
            else:
                # Also check by slug in case tag was changed
                try:
                    team = self.Team.objects.with_deleted().filter(slug=slug).first()
                except AttributeError:
                    team = self.Team.objects.filter(slug=slug).first()
                if team:
                    created = False
                else:
                    team = self.Team(
                        slug=slug, name=name, tag=tag, game_id=game.id,
                        region="Bangladesh", status=self.TeamStatus.ACTIVE,
                        created_by=organizer, primary_color=primary,
                        accent_color=accent,
                        description=f"{name} - Competitive Valorant squad from Dhaka, Bangladesh",
                        visibility="PUBLIC",
                    )
                    team.save()
                    created = True

            if not created:
                team.name = name
                team.tag = tag
                team.primary_color = primary
                team.accent_color = accent
                team.game_id = game.id
                # Restore if soft-deleted
                if getattr(team, 'is_deleted', False):
                    team.is_deleted = False
                team.status = self.TeamStatus.ACTIVE
                team.save(update_fields=["name", "tag", "primary_color", "accent_color", "game_id", "is_deleted", "status"])

            players_data = PLAYERS_BY_TEAM[tag]
            users = []

            for p_idx, (username, display, role, player_role) in enumerate(players_data):
                user, u_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": f"{username}@deltacrown.gg",
                        "first_name": display, "is_active": True,
                    },
                )
                if u_created:
                    user.set_password(PASSWORD)
                    user.save(update_fields=["password"])

                try:
                    from apps.user_profile.models_main import UserProfile
                    UserProfile.objects.get_or_create(
                        user=user,
                        defaults={"display_name": display, "region": "Bangladesh"},
                    )
                except Exception:
                    pass

                # ── Game Passport (GameProfile) ──
                try:
                    from apps.user_profile.models_main import GameProfile
                    _val_ranks = [
                        ("Immortal 3", 8), ("Immortal 2", 7), ("Immortal 1", 6),
                        ("Diamond 3", 5), ("Diamond 2", 4), ("Diamond 1", 3),
                        ("Platinum 3", 2), ("Platinum 2", 1),
                    ]
                    _rank_name, _rank_tier = _val_ranks[min(p_idx + (idx % 4), len(_val_ranks) - 1)]
                    _ign = display
                    _disc = f"#{tag}"
                    GameProfile.objects.get_or_create(
                        user=user, game=game,
                        defaults={
                            "game_display_name": game.display_name if hasattr(game, 'display_name') else game.name,
                            "ign": _ign,
                            "discriminator": _disc,
                            "in_game_name": f"{_ign}{_disc}",
                            "identity_key": f"{_ign.lower()}{_disc.lower()}",
                            "rank_name": _rank_name,
                            "rank_tier": _rank_tier,
                            "rank_points": random.randint(50, 450),
                            "peak_rank": "Immortal 3",
                            "main_role": player_role,
                            "region": "AP",
                            "visibility": "PUBLIC",
                            "status": "ACTIVE",
                        },
                    )
                except Exception:
                    pass

                users.append(user)

                is_captain = (p_idx == 4)
                self.TeamMembership.objects.get_or_create(
                    team=team, user=user,
                    defaults={
                        "status": self.MembershipStatus.ACTIVE,
                        "role": self.MembershipRole.OWNER if is_captain else self.MembershipRole.PLAYER,
                        "roster_slot": self.RosterSlot.STARTER,
                        "player_role": player_role,
                        "is_tournament_captain": is_captain,
                        "game_id": game.id,
                        "display_name": display,
                    },
                )

            teams.append(team)
            team_users[tag] = users
            verb = "Created" if created else "Found"
            self.stdout.write(f"  {verb} team {idx+1:2d}. {name} ({tag}) - {len(users)} players")

        return teams, team_users

    # ── Tournament ──
    def _create_tournament(self, organizer, game):
        self.stdout.write("\nCreating tournament...")

        base_date = NOW - timedelta(days=14)

        tournament, created = self.Tournament.objects.get_or_create(
            slug=TOURNAMENT_SLUG,
            defaults={
                "name": TOURNAMENT_NAME,
                "organizer": organizer,
                "game": game,
                "description": (
                    "<p>The biggest Valorant showdown this spring! "
                    "16 elite squads from across Dhaka compete for "
                    "20,000 BDT in prizes and the title of "
                    "<strong>DeltaCrown Spring Champion 2026</strong>.</p>"
                    "<p>Format: Double Elimination (BO3, Grand Final BO5)</p>"
                    "<p>All matches streamed live on YouTube and Twitch</p>"
                ),
                "format": "double_elimination",
                "participation_type": "team",
                "status": "completed",
                "platform": "pc",
                "mode": "online",
                "prize_pool": Decimal("20000.00"),
                "prize_currency": "BDT",
                "entry_fee_amount": Decimal("400.00"),
                "entry_fee_currency": "BDT",
                "has_entry_fee": True,
                "max_participants": 32,
                "min_participants": 16,
                "registration_start": base_date,
                "registration_end": base_date + timedelta(days=5),
                "tournament_start": base_date + timedelta(days=7),
                "tournament_end": base_date + timedelta(days=12),
                "rules_text": (
                    "<h3>DeltaCrown Valorant Spring Showdown 2026 — Official Rules</h3>"
                    "<p><strong>Version 1.0</strong> · Effective from tournament start</p>"
                    "<hr>"
                    "<h4>1. Eligibility &amp; Accounts</h4>"
                    "<ul>"
                    "<li>All players must use Riot-verified accounts in good standing.</li>"
                    "<li>Account sharing, boosting, or smurfing is strictly prohibited.</li>"
                    "<li>Players must have a valid DeltaCrown Game Passport (Valorant) linked before check-in.</li>"
                    "</ul>"
                    "<h4>2. Match Format</h4>"
                    "<ul>"
                    "<li><strong>Double Elimination</strong> bracket — 16 teams.</li>"
                    "<li>All matches are <strong>Best of 3 (BO3)</strong> except Grand Finals.</li>"
                    "<li>Grand Finals are <strong>Best of 5 (BO5)</strong>. Upper Bracket finalist has a 1-map advantage.</li>"
                    "</ul>"
                    "<h4>3. Map Veto</h4>"
                    "<ul>"
                    "<li>BO3: Ban-Ban-Pick-Pick-Ban-Ban-Decider (1-2-1-2-1-2).</li>"
                    "<li>BO5: Ban-Ban-Pick-Pick-Pick-Pick-Decider.</li>"
                    "<li>Higher seed (or UB finalist) picks side on the decider map.</li>"
                    "</ul>"
                    "<h4>4. In-Game Rules</h4>"
                    "<ul>"
                    "<li>Standard Valorant competitive overtime rules apply (win by 2).</li>"
                    "<li>Each team gets <strong>2 tactical pauses</strong> per half (60 seconds each).</li>"
                    "<li>Coaching is allowed during tactical pauses and halftime only.</li>"
                    "<li>Riot Vanguard anti-cheat must be active. Disabling it forfeits the match.</li>"
                    "</ul>"
                    "<h4>5. Conduct &amp; Penalties</h4>"
                    "<ul>"
                    "<li>Toxicity, BM, or unsportsmanlike behavior may result in warnings, map loss, or disqualification at admin discretion.</li>"
                    "<li>Stream sniping = automatic forfeit + potential tournament ban.</li>"
                    "<li>Bug abuse must be reported immediately; deliberate exploitation = map replay or DQ.</li>"
                    "</ul>"
                    "<h4>6. Scheduling &amp; No-Shows</h4>"
                    "<ul>"
                    "<li>Teams must check in within the scheduled window.</li>"
                    "<li>A team that is not ready within <strong>15 minutes</strong> of the scheduled time forfeits the match.</li>"
                    "<li>Reschedule requests must be submitted at least 2 hours before match time.</li>"
                    "</ul>"
                    "<p><em>All decisions by DeltaCrown tournament admins are final.</em></p>"
                ),
                "enable_check_in": True,
                "check_in_minutes_before": 120,
                "check_in_closes_minutes_before": 15,
                "stream_youtube_url": "https://youtube.com/@DeltaCrownEsports/live",
                "stream_twitch_url": "https://twitch.tv/deltacrown_en",
                "social_discord": "https://discord.gg/deltacrown",
                "social_youtube": "https://youtube.com/@DeltaCrownEsports",
                "contact_email": "tournaments@deltacrown.gg",
                "config": TOURNAMENT_CONFIG,
            },
        )

        if not created:
            tournament.status = "completed"
            tournament.name = TOURNAMENT_NAME
            tournament.config = TOURNAMENT_CONFIG
            tournament.save(update_fields=["status", "name", "config"])

        self.stdout.write(f"  Tournament: {tournament.name} (ID={tournament.id})")
        return tournament

    # ── Registrations & Payments ──
    def _create_registrations(self, tournament, teams, team_users, organizer):
        self.stdout.write("\nCreating registrations...")

        # Clean up any existing registrations for this tournament (idempotent)
        try:
            existing = self.Registration.objects.with_deleted().filter(tournament=tournament)
        except AttributeError:
            existing = self.Registration.objects.filter(tournament=tournament)
        if existing.exists():
            # Must delete protected references before registrations
            self.TournamentResult.objects.filter(tournament=tournament).delete()
            self.PrizeTransaction.objects.filter(tournament=tournament).delete()
            self.PaymentVerification.objects.filter(registration__tournament=tournament).delete()
            self.Payment.objects.filter(registration__tournament=tournament).delete()
            existing.delete()
            self.stdout.write("  Cleaned existing registrations")

        registrations = {}

        for idx, team in enumerate(teams):
            tag = TEAMS_DATA[idx][1]
            users = team_users[tag]

            lineup = []
            for p_idx, user in enumerate(users):
                pdata = PLAYERS_BY_TEAM[tag][p_idx]
                lineup.append({
                    "user_id": user.id,
                    "username": user.username,
                    "display_name": pdata[1],
                    "game_id": f"{pdata[1]}#BD{random.randint(1000, 9999)}",
                    "role": "PLAYER",
                    "player_role": pdata[3],
                    "roster_slot": "STARTER",
                    "is_igl": (p_idx == 4),
                })

            reg = self.Registration.objects.create(
                tournament=tournament,
                user=None,
                team_id=team.id,
                status=self.Registration.CONFIRMED,
                registration_data={
                    "team_name": team.name,
                    "team_tag": tag,
                    "contact_discord": f"{tag.lower()}@discord",
                },
                completion_percentage=Decimal("100.00"),
                current_step=3,
                checked_in=True,
                checked_in_at=tournament.tournament_start,
                slot_number=idx + 1,
                seed=idx + 1,
                lineup_snapshot=lineup,
                is_guest_team=False,
            )

            self.Payment.objects.create(
                registration=reg,
                payment_method="bkash",
                amount=Decimal("400.00"),
                transaction_id=f"BK{random.randint(100000000, 999999999)}",
                status="verified",
                verified_by=organizer,
                verified_at=tournament.registration_start + timedelta(days=idx % 4 + 1),
                admin_notes=f"Payment verified for {team.name}",
            )

            # PaymentVerification — used by TOC service
            txn_id = f"BK{random.randint(100000000, 999999999)}"
            pv, _ = self.PaymentVerification.objects.get_or_create(
                registration=reg,
                defaults={
                    "method": "bkash",
                    "payer_account_number": f"017{random.randint(10000000, 99999999)}",
                    "transaction_id": txn_id,
                    "amount_bdt": 400,
                    "note": f"Entry fee for {team.name}",
                    "status": "verified",
                    "verified_by": organizer,
                    "verified_at": tournament.registration_start + timedelta(days=idx % 4 + 1),
                    "last_action_reason": "Payment verified during registration",
                },
            )

            registrations[idx] = reg
            self.stdout.write(f"  Registered: {team.name} (seed {idx+1})")

        return registrations

    # ── Bracket ──
    def _create_bracket(self, tournament):
        self.stdout.write("\nCreating bracket...")

        # Clean up existing bracket data (idempotent)
        self.BracketNode.objects.filter(bracket__tournament=tournament).delete()
        self.Bracket.objects.filter(tournament=tournament).delete()

        bracket, _ = self.Bracket.objects.get_or_create(
            tournament=tournament,
            defaults={
                "format": "double-elimination",
                "total_rounds": 10,
                "total_matches": 30,
                "seeding_method": "ranked",
                "is_finalized": True,
                "bracket_structure": {
                    "format": "double-elimination",
                    "total_participants": 16,
                    "rounds": {
                        "upper": [
                            {"round": 1, "name": "UB Round 1", "matches": 8},
                            {"round": 2, "name": "UB Quarter-Finals", "matches": 4},
                            {"round": 3, "name": "UB Semi-Finals", "matches": 2},
                            {"round": 4, "name": "UB Final", "matches": 1},
                        ],
                        "lower": [
                            {"round": 1, "name": "LB Round 1", "matches": 4},
                            {"round": 2, "name": "LB Round 2", "matches": 4},
                            {"round": 3, "name": "LB Round 3", "matches": 2},
                            {"round": 4, "name": "LB Round 4", "matches": 2},
                            {"round": 5, "name": "LB Semi-Final", "matches": 1},
                            {"round": 6, "name": "LB Final", "matches": 1},
                        ],
                        "grand_final": [
                            {"round": 1, "name": "Grand Final", "matches": 1},
                        ],
                    },
                    "third_place_match": False,
                },
            },
        )

        self.stdout.write(f"  Bracket: {bracket.get_format_display()} (ID={bracket.id})")
        return bracket

    # ── Matches ──
    def _create_matches(self, tournament, bracket, teams, registrations):
        self.stdout.write("\nCreating matches...")

        # Clean up existing matches (idempotent)
        self.Match.objects.filter(tournament=tournament).delete()

        matches = {}

        for mr in MATCH_RESULTS:
            match_num, btype, round_label, p1_idx, p2_idx, winner_idx, best_of, map_scores = mr

            p1_team = teams[p1_idx]
            p2_team = teams[p2_idx]
            winner_team = teams[winner_idx]
            loser_idx = p2_idx if winner_idx == p1_idx else p1_idx
            loser_team = teams[loser_idx]

            p1_maps_won = sum(1 for ms in map_scores if ms["winner_side"] == 1)
            p2_maps_won = sum(1 for ms in map_scores if ms["winner_side"] == 2)

            # Schedule: spread across 5 days
            if match_num <= 8:
                day = 0
            elif match_num <= 12:
                day = 1
            elif match_num <= 15:
                day = 2
            elif match_num <= 23:
                day = 3
            elif match_num <= 29:
                day = 4
            else:
                day = 5

            hour = 10 + (match_num % 4) * 2
            scheduled = tournament.tournament_start + timedelta(days=day, hours=hour)

            lobby_info = {
                "server": "Mumbai-1",
                "password": f"DC-SS-M{match_num}",
                "custom_room_id": f"DCSM{match_num}",
                "best_of": best_of,
                "lobby_code": f"DCSS{match_num:03d}",
                "status": "closed",
                "region": "Mumbai",
                "chat": [
                    {"user": "admin", "msg": f"Lobby created for {round_label}", "ts": scheduled.isoformat()},
                    {"user": p1_team.name, "msg": "Ready!", "ts": (scheduled + timedelta(minutes=5)).isoformat()},
                    {"user": p2_team.name, "msg": "GLHF!", "ts": (scheduled + timedelta(minutes=6)).isoformat()},
                ],
            }

            # Compute a round_number for the match model
            # For DE: we use a simple sequential scheme
            # UB-R1=1, UB-QF=2, UB-SF=3, UB-F=4, LB-R1=5, LB-R2=6, LB-R3=7, LB-R4=8, LB-SF=9, LB-F=10, GF=11
            round_map = {
                "UB Round 1": 1, "UB Quarter-Final": 2, "UB Semi-Final": 3, "UB Final": 4,
                "LB Round 1": 5, "LB Round 2": 6, "LB Round 3": 7, "LB Round 4": 8,
                "LB Semi-Final": 9, "LB Final": 10, "Grand Final": 11,
            }
            round_number = round_map.get(round_label, match_num)

            match = self.Match.objects.create(
                tournament=tournament,
                bracket=bracket,
                round_number=round_number,
                match_number=match_num,
                participant1_id=p1_team.id,
                participant2_id=p2_team.id,
                participant1_name=p1_team.name,
                participant2_name=p2_team.name,
                state="completed",
                participant1_score=p1_maps_won,
                participant2_score=p2_maps_won,
                winner_id=winner_team.id,
                loser_id=loser_team.id,
                best_of=best_of,
                game_scores={
                    "format": f"valorant_bo{best_of}",
                    "best_of": best_of,
                    "maps": map_scores,
                },
                lobby_info=lobby_info,
                scheduled_time=scheduled,
                started_at=scheduled,
                completed_at=scheduled + timedelta(hours=1, minutes=random.randint(15, 50)),
                stream_url="https://youtube.com/@DeltaCrownEsports/live" if match_num >= 13 else "",
            )

            matches[match_num] = match
            w_tag = TEAMS_DATA[winner_idx][1]
            l_tag = TEAMS_DATA[loser_idx][1]
            w_score = p1_maps_won if winner_idx == p1_idx else p2_maps_won
            l_score = p2_maps_won if winner_idx == p1_idx else p1_maps_won
            self.stdout.write(
                f"  M{match_num:2d} [{round_label:20s}] {TEAMS_DATA[p1_idx][1]} vs {TEAMS_DATA[p2_idx][1]} "
                f"-> {w_tag} wins {w_score}-{l_score}"
            )

        return matches

    # ── Bracket Nodes ──
    def _create_bracket_nodes(self, bracket, matches, teams):
        self.stdout.write("\nCreating bracket nodes...")

        # Build node definitions for double elimination
        # We create nodes for all 30 matches
        # position = sequential 1..30
        # For UB: round_number = 1..4 (R1, QF, SF, Final)
        # For LB: round_number = 1..6 (R1, R2, R3, R4, SF, Final)
        # For GF: round_number = 1

        node_defs = []
        pos = 0

        # ═══ UPPER BRACKET ═══
        # UB R1: matches 1-8, round 1
        for i in range(1, 9):
            pos += 1
            node_defs.append((pos, "main", 1, i - 0, i))  # (position, btype, bn_round, match_in_round, match_num)

        # UB QF: matches 9-12, round 2
        for i in range(9, 13):
            pos += 1
            node_defs.append((pos, "main", 2, i - 8, i))

        # UB SF: matches 13-14, round 3
        for i in range(13, 15):
            pos += 1
            node_defs.append((pos, "main", 3, i - 12, i))

        # UB Final: match 15, round 4
        pos += 1
        node_defs.append((pos, "main", 4, 1, 15))

        # ═══ LOWER BRACKET ═══
        # LB R1: matches 16-19, round 1
        for i in range(16, 20):
            pos += 1
            node_defs.append((pos, "losers", 1, i - 15, i))

        # LB R2: matches 20-23, round 2
        for i in range(20, 24):
            pos += 1
            node_defs.append((pos, "losers", 2, i - 19, i))

        # LB R3: matches 24-25, round 3
        for i in range(24, 26):
            pos += 1
            node_defs.append((pos, "losers", 3, i - 23, i))

        # LB R4: matches 26-27, round 4
        for i in range(26, 28):
            pos += 1
            node_defs.append((pos, "losers", 4, i - 25, i))

        # LB SF: match 28, round 5
        pos += 1
        node_defs.append((pos, "losers", 5, 1, 28))

        # LB Final: match 29, round 6
        pos += 1
        node_defs.append((pos, "losers", 6, 1, 29))

        # ═══ GRAND FINAL ═══
        pos += 1
        node_defs.append((pos, "main", 5, 1, 30))

        # First pass: create nodes
        nodes = {}
        for npos, btype, bn_round, mir, mnum in node_defs:
            match = matches[mnum]
            node = self.BracketNode.objects.create(
                bracket=bracket,
                position=npos,
                round_number=bn_round,
                match_number_in_round=mir,
                match=match,
                participant1_id=match.participant1_id,
                participant1_name=match.participant1_name,
                participant2_id=match.participant2_id,
                participant2_name=match.participant2_name,
                winner_id=match.winner_id,
                is_bye=False,
                bracket_type=btype,
            )
            nodes[npos] = node

        # Second pass: link parent/child for upper bracket
        # UB R1 (1-8) → UB QF (9-12): 1,2→9  3,4→10  5,6→11  7,8→12
        for i in range(4):
            c1 = nodes[i * 2 + 1]
            c2 = nodes[i * 2 + 2]
            parent = nodes[9 + i]
            c1.parent_node = parent
            c1.parent_slot = 1
            c2.parent_node = parent
            c2.parent_slot = 2
            parent.child1_node = c1
            parent.child2_node = c2
            c1.save(update_fields=["parent_node", "parent_slot"])
            c2.save(update_fields=["parent_node", "parent_slot"])
            parent.save(update_fields=["child1_node", "child2_node"])

        # UB QF (9-12) → UB SF (13-14): 9,10→13  11,12→14
        for i in range(2):
            c1 = nodes[9 + i * 2]
            c2 = nodes[10 + i * 2]
            parent = nodes[13 + i]
            c1.parent_node = parent
            c1.parent_slot = 1
            c2.parent_node = parent
            c2.parent_slot = 2
            parent.child1_node = c1
            parent.child2_node = c2
            c1.save(update_fields=["parent_node", "parent_slot"])
            c2.save(update_fields=["parent_node", "parent_slot"])
            parent.save(update_fields=["child1_node", "child2_node"])

        # UB SF (13-14) → UB Final (15)
        c1, c2, parent = nodes[13], nodes[14], nodes[15]
        c1.parent_node = parent
        c1.parent_slot = 1
        c2.parent_node = parent
        c2.parent_slot = 2
        parent.child1_node = c1
        parent.child2_node = c2
        c1.save(update_fields=["parent_node", "parent_slot"])
        c2.save(update_fields=["parent_node", "parent_slot"])
        parent.save(update_fields=["child1_node", "child2_node"])

        # UB Final (15) → Grand Final (30)
        nodes[15].parent_node = nodes[30]
        nodes[15].parent_slot = 1
        nodes[30].child1_node = nodes[15]
        nodes[15].save(update_fields=["parent_node", "parent_slot"])

        # LB Final (29) → Grand Final (30)
        nodes[29].parent_node = nodes[30]
        nodes[29].parent_slot = 2
        nodes[30].child2_node = nodes[29]
        nodes[29].save(update_fields=["parent_node", "parent_slot"])
        nodes[30].save(update_fields=["child1_node", "child2_node"])

        self.stdout.write(f"  Created {len(nodes)} bracket nodes (UB + LB + GF)")

    # ── Tournament Result ──
    def _create_result(self, tournament, registrations, organizer):
        self.stdout.write("\nCreating tournament result...")

        # Clean existing (idempotent)
        self.TournamentResult.objects.filter(tournament=tournament).delete()

        winner_reg = registrations[CHAMPION_IDX]
        runner_reg = registrations[RUNNER_UP_IDX]
        third_reg = registrations[THIRD_PLACE_IDX]

        result, created = self.TournamentResult.objects.get_or_create(
            tournament=tournament,
            defaults={
                "winner": winner_reg,
                "runner_up": runner_reg,
                "third_place": third_reg,
                "determination_method": "normal",
                "rules_applied": {
                    "method": "double_elimination_bracket",
                    "grand_final_format": "BO5",
                    "third_place_match": False,
                },
                "requires_review": False,
                "created_by": organizer,
                "matches_played": 30,
                "series_score": {
                    "grand_final": {
                        str(winner_reg.team_id): 3,
                        str(runner_reg.team_id): 1,
                    },
                },
            },
        )

        champion_name = TEAMS_DATA[CHAMPION_IDX][0]
        self.stdout.write(f"  Champion: {champion_name} (Result ID={result.id})")

    # ── Prize Transactions ──
    def _create_prizes(self, tournament, registrations):
        self.stdout.write("\nCreating prize transactions...")

        # Clean existing (idempotent)
        self.PrizeTransaction.objects.filter(tournament=tournament).delete()

        placement_map = {
            CHAMPION_IDX: "1st",
            RUNNER_UP_IDX: "2nd",
            THIRD_PLACE_IDX: "3rd",
        }

        for team_idx, amount in PRIZE_DISTRIBUTION.items():
            reg = registrations[team_idx]
            team_name = TEAMS_DATA[team_idx][0]

            self.PrizeTransaction.objects.get_or_create(
                tournament=tournament,
                participant=reg,
                defaults={
                    "amount": amount,
                    "placement": placement_map[team_idx],
                    "status": "completed",
                    "notes": f"Prize for {team_name} - Spring Showdown 2026",
                },
            )
            self.stdout.write(f"  {amount:,.0f} BDT -> {team_name}")

    # ── Player Stats ──
    def _create_player_stats(self, tournament, matches, teams, team_users):
        """Generate realistic Valorant player stats for every match (bulk)."""
        from apps.tournaments.models.match_player_stats import MatchPlayerStat, MatchMapPlayerStat

        self.stdout.write("\nCreating player stats...")

        # Clean existing (idempotent)
        match_ids = [m.id for m in matches.values()]
        MatchMapPlayerStat.objects.filter(match_id__in=match_ids).delete()
        MatchPlayerStat.objects.filter(match_id__in=match_ids).delete()

        VALORANT_AGENTS = [
            "Jett", "Reyna", "Raze", "Phoenix", "Yoru", "Neon", "Iso",
            "Sova", "Breach", "Skye", "KAY/O", "Fade", "Gekko",
            "Omen", "Brimstone", "Astra", "Viper", "Harbor", "Clove",
            "Sage", "Cypher", "Killjoy", "Chamber", "Deadlock", "Vyse",
        ]

        map_stat_objs = []
        match_stat_objs = []

        for match_num, match_obj in matches.items():
            mr = MATCH_RESULTS[match_num - 1]
            _, btype, round_label, p1_idx, p2_idx, winner_idx, best_of, map_scores_data = mr

            for side, team_idx in [(1, p1_idx), (2, p2_idx)]:
                team = teams[team_idx]
                tag = TEAMS_DATA[team_idx][1]
                players = team_users.get(tag, [])
                if not players:
                    continue

                is_winning_team = (team_idx == winner_idx)

                for player_i, player_user in enumerate(players):
                    agent = random.choice(VALORANT_AGENTS)
                    total_kills = 0
                    total_deaths = 0
                    total_assists = 0
                    total_acs = Decimal('0')
                    total_adr = Decimal('0')
                    total_hs = Decimal('0')
                    total_fk = 0
                    total_fd = 0

                    for map_i, ms in enumerate(map_scores_data, start=1):
                        p1_rounds = ms["team1_rounds"]
                        p2_rounds = ms["team2_rounds"]
                        total_rounds = p1_rounds + p2_rounds
                        won_this_map = (ms["winner_side"] == side)

                        skill_factor = 1.0 + (player_i == 0) * 0.15
                        win_bonus = 1.1 if won_this_map else 0.9

                        map_kills = max(3, int(total_rounds * random.uniform(0.5, 1.1) * skill_factor * win_bonus))
                        map_deaths = max(3, int(total_rounds * random.uniform(0.45, 0.95) / win_bonus))
                        map_assists = max(1, int(total_rounds * random.uniform(0.15, 0.45)))
                        map_acs = Decimal(str(round(random.uniform(140, 340) * skill_factor * win_bonus, 1)))
                        map_adr = Decimal(str(round(random.uniform(110, 190) * skill_factor * win_bonus, 1)))
                        map_hs = Decimal(str(round(random.uniform(15, 42), 1)))
                        map_fk = max(0, int(random.uniform(0, 0.2) * total_rounds * skill_factor))
                        map_fd = max(0, int(random.uniform(0, 0.15) * total_rounds))

                        total_kills += map_kills
                        total_deaths += map_deaths
                        total_assists += map_assists
                        total_acs += map_acs
                        total_adr += map_adr
                        total_hs += map_hs
                        total_fk += map_fk
                        total_fd += map_fd

                        map_stat_objs.append(MatchMapPlayerStat(
                            match=match_obj,
                            player=player_user,
                            team_id=team.id,
                            map_number=map_i,
                            map_name=ms.get("map_name", ""),
                            agent=agent,
                            kills=map_kills,
                            deaths=map_deaths,
                            assists=map_assists,
                            acs=map_acs,
                            adr=map_adr,
                            headshot_pct=map_hs,
                            first_kills=map_fk,
                            first_deaths=map_fd,
                        ))

                    num_maps = len(map_scores_data)
                    avg_acs = (total_acs / num_maps).quantize(Decimal('0.1')) if num_maps else Decimal('0')
                    avg_adr = (total_adr / num_maps).quantize(Decimal('0.1')) if num_maps else Decimal('0')
                    avg_hs = (total_hs / num_maps).quantize(Decimal('0.1')) if num_maps else Decimal('0')
                    kd = (Decimal(str(total_kills)) / Decimal(str(max(total_deaths, 1)))).quantize(Decimal('0.01'))
                    clutches = random.randint(0, 3) if is_winning_team else random.randint(0, 1)
                    multi_kills = random.randint(0, 4)
                    plants = random.randint(0, num_maps * 3)
                    defuses = random.randint(0, num_maps * 2)
                    kast = Decimal(str(round(random.uniform(55, 85), 1)))

                    match_stat_objs.append(MatchPlayerStat(
                        match=match_obj,
                        player=player_user,
                        team_id=team.id,
                        agent=agent,
                        kills=total_kills,
                        deaths=total_deaths,
                        assists=total_assists,
                        acs=avg_acs,
                        adr=avg_adr,
                        headshot_pct=avg_hs,
                        first_kills=total_fk,
                        first_deaths=total_fd,
                        clutches=clutches,
                        multi_kills=multi_kills,
                        plants=plants,
                        defuses=defuses,
                        kd_ratio=kd,
                        kast_pct=kast,
                        is_mvp=(player_i == 0 and is_winning_team),
                    ))

        # Bulk create in batches for speed
        MatchMapPlayerStat.objects.bulk_create(map_stat_objs, batch_size=200)
        MatchPlayerStat.objects.bulk_create(match_stat_objs, batch_size=200)

        self.stdout.write(f"  Created {len(match_stat_objs)} MatchPlayerStat records")
        self.stdout.write(f"  Created {len(map_stat_objs)} MatchMapPlayerStat records")
