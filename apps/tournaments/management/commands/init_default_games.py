"""
Django Management Command: Initialize Default Games
===================================================

Ensures the 9 canonical games for DeltaCrown platform exist in the database
with correct configuration, including related roster configs, tournament configs,
player identity configs, and game roles.

This command is idempotent and safe to run multiple times.

Usage:
    python manage.py init_default_games
    python manage.py init_default_games --dry-run
    python manage.py init_default_games --force-update

Architecture:
    Game model (apps.games.models.Game) — core game identity
    GameRosterConfig (OneToOne) — team size, subs, staff
    GameTournamentConfig (OneToOne) — formats, scoring, brackets
    GamePlayerIdentityConfig (FK) — per-game player ID fields
    GameRole (FK) — game-specific competitive roles

Canonical Games:
1. Valorant (valorant)
2. Counter-Strike 2 (cs2)
3. Dota 2 (dota2)
4. eFootball (efootball)
5. EA SPORTS FC (fc26)
6. Mobile Legends: Bang Bang (mlbb)
7. Call of Duty: Mobile (codm)
8. Free Fire (freefire)
9. PUBG Mobile (pubg)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.games.models import (
    Game,
    GameRosterConfig,
    GameTournamentConfig,
    GamePlayerIdentityConfig,
    GameRole,
)


class Command(BaseCommand):
    help = 'Initialize or update the 9 canonical default games for DeltaCrown platform'

    # ── Canonical game specifications ─────────────────────────────────
    # Each entry maps directly to Game model fields plus nested dicts
    # for related models (roster, tournament, identities, roles).
    CANONICAL_GAMES = [
        {
            # ── Game fields ──
            'slug': 'valorant',
            'name': 'VALORANT',
            'display_name': 'VALORANT',
            'short_code': 'VAL',
            'category': 'FPS',
            'game_type': 'TEAM_VS_TEAM',
            'platforms': ['PC'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'iron', 'label': 'Iron'},
                {'value': 'bronze', 'label': 'Bronze'},
                {'value': 'silver', 'label': 'Silver'},
                {'value': 'gold', 'label': 'Gold'},
                {'value': 'platinum', 'label': 'Platinum'},
                {'value': 'diamond', 'label': 'Diamond'},
                {'value': 'ascendant', 'label': 'Ascendant'},
                {'value': 'immortal', 'label': 'Immortal'},
                {'value': 'radiant', 'label': 'Radiant'},
            ],
            'primary_color': '#ff4655',
            'secondary_color': '#0f1923',
            'description': 'VALORANT is a free-to-play first-person tactical hero shooter developed by Riot Games.',
            'developer': 'Riot Games',
            'publisher': 'Riot Games',
            # ── Roster config ──
            'roster': {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 7,
            },
            # ── Tournament config ──
            'tournament': {
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'ROUNDS',
                'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': True,
                'supports_group_stage': True,
                'default_match_duration_minutes': 60,
                'allow_draws': False,
                'overtime_enabled': True,
                'min_team_size': 5, 'max_team_size': 7,
            },
            # ── Player identity fields ──
            'identities': [
                {
                    'field_name': 'riot_id',
                    'display_name': 'Riot ID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': 'PlayerName#TAG',
                    'validation_regex': r'^.+#.+$',
                    'validation_error_message': 'Must be in format Name#Tag',
                    'help_text': 'Your Riot ID (e.g., Player#1234)',
                },
            ],
            # ── Game roles ──
            'roles': [
                {'role_name': 'Duelist', 'role_code': 'DUE', 'icon': '🎯', 'color': '#ff4655', 'order': 1},
                {'role_name': 'Initiator', 'role_code': 'INI', 'icon': '⚡', 'color': '#00bfa5', 'order': 2},
                {'role_name': 'Controller', 'role_code': 'CTRL', 'icon': '🌫️', 'color': '#7c3aed', 'order': 3},
                {'role_name': 'Sentinel', 'role_code': 'SEN', 'icon': '🛡️', 'color': '#2196f3', 'order': 4},
            ],
        },
        {
            'slug': 'cs2',
            'name': 'Counter-Strike 2',
            'display_name': 'Counter-Strike 2',
            'short_code': 'CS2',
            'category': 'FPS',
            'game_type': 'TEAM_VS_TEAM',
            'platforms': ['PC'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'silver1', 'label': 'Silver I'},
                {'value': 'silver2', 'label': 'Silver II'},
                {'value': 'silver3', 'label': 'Silver III'},
                {'value': 'silver4', 'label': 'Silver IV'},
                {'value': 'sem', 'label': 'Silver Elite Master'},
                {'value': 'gn1', 'label': 'Gold Nova I'},
                {'value': 'gn2', 'label': 'Gold Nova II'},
                {'value': 'gn3', 'label': 'Gold Nova III'},
                {'value': 'gnm', 'label': 'Gold Nova Master'},
                {'value': 'mg1', 'label': 'Master Guardian I'},
                {'value': 'mg2', 'label': 'Master Guardian II'},
                {'value': 'mge', 'label': 'Master Guardian Elite'},
                {'value': 'dmg', 'label': 'Distinguished Master Guardian'},
                {'value': 'le', 'label': 'Legendary Eagle'},
                {'value': 'lem', 'label': 'Legendary Eagle Master'},
                {'value': 'smfc', 'label': 'Supreme Master First Class'},
                {'value': 'ge', 'label': 'Global Elite'},
            ],
            'primary_color': '#de9b35',
            'secondary_color': '#1b2838',
            'description': 'Counter-Strike 2 is the latest installment in the legendary tactical FPS series.',
            'developer': 'Valve',
            'publisher': 'Valve',
            'roster': {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 7,
            },
            'tournament': {
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'ROUNDS',
                'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': True,
                'supports_group_stage': True,
                'default_match_duration_minutes': 60,
                'allow_draws': False,
                'overtime_enabled': True,
                'min_team_size': 5, 'max_team_size': 7,
            },
            'identities': [
                {
                    'field_name': 'steam_id',
                    'display_name': 'Steam ID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': '76561198xxxxxxxxx',
                    'help_text': 'Your Steam ID (17-digit number or custom URL)',
                },
            ],
            'roles': [
                {'role_name': 'Entry Fragger', 'role_code': 'ENTRY', 'icon': '🎯', 'color': '#ff4655', 'order': 1},
                {'role_name': 'AWPer', 'role_code': 'AWP', 'icon': '🔭', 'color': '#de9b35', 'order': 2},
                {'role_name': 'Lurker', 'role_code': 'LURK', 'icon': '🕵️', 'color': '#7c3aed', 'order': 3},
                {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#2196f3', 'order': 4},
                {'role_name': 'In-Game Leader', 'role_code': 'IGL', 'icon': '📢', 'color': '#4caf50', 'order': 5},
            ],
        },
        {
            'slug': 'dota2',
            'name': 'Dota 2',
            'display_name': 'Dota 2',
            'short_code': 'DOTA',
            'category': 'MOBA',
            'game_type': 'TEAM_VS_TEAM',
            'platforms': ['PC'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'herald', 'label': 'Herald'},
                {'value': 'guardian', 'label': 'Guardian'},
                {'value': 'crusader', 'label': 'Crusader'},
                {'value': 'archon', 'label': 'Archon'},
                {'value': 'legend', 'label': 'Legend'},
                {'value': 'ancient', 'label': 'Ancient'},
                {'value': 'divine', 'label': 'Divine'},
                {'value': 'immortal', 'label': 'Immortal'},
            ],
            'primary_color': '#c23616',
            'secondary_color': '#1e272e',
            'description': 'Dota 2 is a multiplayer online battle arena (MOBA) game developed by Valve Corporation.',
            'developer': 'Valve',
            'publisher': 'Valve',
            'roster': {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 7,
            },
            'tournament': {
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'WIN_LOSS',
                'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'game_diff'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': True,
                'supports_group_stage': True,
                'default_match_duration_minutes': 60,
                'allow_draws': False,
                'overtime_enabled': False,
                'min_team_size': 5, 'max_team_size': 7,
            },
            'identities': [
                {
                    'field_name': 'steam_id',
                    'display_name': 'Steam ID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': '76561198xxxxxxxxx',
                    'help_text': 'Your Steam ID (17-digit number or custom URL)',
                },
            ],
            'roles': [
                {'role_name': 'Carry', 'role_code': 'CARRY', 'icon': '⚔️', 'color': '#ff4655', 'order': 1},
                {'role_name': 'Mid', 'role_code': 'MID', 'icon': '🎯', 'color': '#de9b35', 'order': 2},
                {'role_name': 'Offlane', 'role_code': 'OFF', 'icon': '🛡️', 'color': '#4caf50', 'order': 3},
                {'role_name': 'Soft Support', 'role_code': 'SUP4', 'icon': '💊', 'color': '#2196f3', 'order': 4},
                {'role_name': 'Hard Support', 'role_code': 'SUP5', 'icon': '🏥', 'color': '#7c3aed', 'order': 5},
            ],
        },
        {
            'slug': 'efootball',
            'name': 'eFootball',
            'display_name': 'eFootball 2025',
            'short_code': 'EFB',
            'category': 'SPORTS',
            'game_type': '1V1',
            'platforms': ['PC', 'Console', 'Mobile'],
            'has_servers': False,
            'has_rank_system': False,
            'available_ranks': [],
            'primary_color': '#005bac',
            'secondary_color': '#001f3f',
            'description': 'eFootball is a free-to-play football simulation game by Konami.',
            'developer': 'Konami',
            'publisher': 'Konami',
            'roster': {
                'min_team_size': 1, 'max_team_size': 1,
                'min_substitutes': 0, 'max_substitutes': 1,
                'min_roster_size': 1, 'max_roster_size': 2,
            },
            'tournament': {
                'available_match_formats': ['BO1', 'BO3'],
                'default_match_format': 'BO1',
                'default_scoring_type': 'GOALS',
                'scoring_rules': {'win_points': 3, 'draw_points': 1, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'goal_diff', 'goals_for'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 30,
                'allow_draws': True,
                'overtime_enabled': True,
                'min_team_size': 1, 'max_team_size': 2,
            },
            'identities': [
                {
                    'field_name': 'konami_id',
                    'display_name': 'Konami ID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': 'Your Konami ID',
                    'help_text': 'Your Konami ID from the game profile',
                },
            ],
            'roles': [],
        },
        {
            'slug': 'fc26',
            'name': 'EA SPORTS FC',
            'display_name': 'EA SPORTS FC 26',
            'short_code': 'FC26',
            'category': 'SPORTS',
            'game_type': '1V1',
            'platforms': ['PC', 'Console', 'Mobile'],
            'has_servers': False,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'div10', 'label': 'Division 10'},
                {'value': 'div5', 'label': 'Division 5'},
                {'value': 'div1', 'label': 'Division 1'},
                {'value': 'elite', 'label': 'Elite'},
            ],
            'primary_color': '#00c853',
            'secondary_color': '#1b2838',
            'description': 'EA SPORTS FC is the latest football simulation game from EA Sports.',
            'developer': 'EA Vancouver',
            'publisher': 'Electronic Arts',
            'roster': {
                'min_team_size': 1, 'max_team_size': 1,
                'min_substitutes': 0, 'max_substitutes': 1,
                'min_roster_size': 1, 'max_roster_size': 2,
            },
            'tournament': {
                'available_match_formats': ['BO1', 'BO3'],
                'default_match_format': 'BO1',
                'default_scoring_type': 'GOALS',
                'scoring_rules': {'win_points': 3, 'draw_points': 1, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'goal_diff', 'goals_for'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 30,
                'allow_draws': True,
                'overtime_enabled': True,
                'min_team_size': 1, 'max_team_size': 2,
            },
            'identities': [
                {
                    'field_name': 'ea_id',
                    'display_name': 'EA ID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': 'Your EA ID',
                    'help_text': 'Your EA account username',
                },
            ],
            'roles': [],
        },
        {
            'slug': 'mlbb',
            'name': 'Mobile Legends: Bang Bang',
            'display_name': 'Mobile Legends: Bang Bang',
            'short_code': 'MLBB',
            'category': 'MOBA',
            'game_type': 'TEAM_VS_TEAM',
            'platforms': ['Mobile'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'warrior', 'label': 'Warrior'},
                {'value': 'elite', 'label': 'Elite'},
                {'value': 'master', 'label': 'Master'},
                {'value': 'grandmaster', 'label': 'Grandmaster'},
                {'value': 'epic', 'label': 'Epic'},
                {'value': 'legend', 'label': 'Legend'},
                {'value': 'mythic', 'label': 'Mythic'},
                {'value': 'mythical_glory', 'label': 'Mythical Glory'},
                {'value': 'immortal', 'label': 'Immortal'},
            ],
            'primary_color': '#f39c12',
            'secondary_color': '#2c3e50',
            'description': 'Mobile Legends: Bang Bang is a mobile multiplayer online battle arena game.',
            'developer': 'Moonton',
            'publisher': 'Moonton',
            'roster': {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 7,
            },
            'tournament': {
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'WIN_LOSS',
                'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'game_diff'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 30,
                'allow_draws': False,
                'overtime_enabled': False,
                'min_team_size': 5, 'max_team_size': 7,
            },
            'identities': [
                {
                    'field_name': 'mlbb_id',
                    'display_name': 'MLBB Game ID',
                    'field_type': 'NUMBER',
                    'is_required': True,
                    'placeholder': '123456789',
                    'help_text': 'Your Mobile Legends numeric Game ID',
                },
                {
                    'field_name': 'mlbb_server',
                    'display_name': 'Server ID',
                    'field_type': 'NUMBER',
                    'is_required': True,
                    'placeholder': '1234',
                    'help_text': 'Your Mobile Legends Server ID',
                },
            ],
            'roles': [
                {'role_name': 'Tank', 'role_code': 'TNK', 'icon': '🛡️', 'color': '#3498db', 'order': 1},
                {'role_name': 'Fighter', 'role_code': 'FGT', 'icon': '⚔️', 'color': '#e74c3c', 'order': 2},
                {'role_name': 'Assassin', 'role_code': 'ASN', 'icon': '🗡️', 'color': '#9b59b6', 'order': 3},
                {'role_name': 'Mage', 'role_code': 'MAG', 'icon': '🔮', 'color': '#f39c12', 'order': 4},
                {'role_name': 'Marksman', 'role_code': 'MKS', 'icon': '🏹', 'color': '#2ecc71', 'order': 5},
                {'role_name': 'Support', 'role_code': 'SUP', 'icon': '💚', 'color': '#1abc9c', 'order': 6},
            ],
        },
        {
            'slug': 'codm',
            'name': 'Call of Duty: Mobile',
            'display_name': 'Call of Duty: Mobile',
            'short_code': 'CODM',
            'category': 'FPS',
            'game_type': 'TEAM_VS_TEAM',
            'platforms': ['Mobile'],
            'has_servers': False,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'rookie', 'label': 'Rookie'},
                {'value': 'veteran', 'label': 'Veteran'},
                {'value': 'elite', 'label': 'Elite'},
                {'value': 'pro', 'label': 'Pro'},
                {'value': 'master', 'label': 'Master'},
                {'value': 'grandmaster', 'label': 'Grand Master'},
                {'value': 'legendary', 'label': 'Legendary'},
            ],
            'primary_color': '#4caf50',
            'secondary_color': '#1b2631',
            'description': 'Call of Duty: Mobile brings the iconic FPS experience to mobile devices.',
            'developer': 'TiMi Studio Group',
            'publisher': 'Activision',
            'roster': {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 7,
            },
            'tournament': {
                'available_match_formats': ['BO3', 'BO5', 'BO7'],
                'default_match_format': 'BO5',
                'default_scoring_type': 'ROUNDS',
                'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'supports_single_elimination': True,
                'supports_double_elimination': True,
                'supports_round_robin': True,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 45,
                'allow_draws': False,
                'overtime_enabled': True,
                'extra_config': {
                    'modes_rotation': ['Hardpoint', 'Search and Destroy', 'Domination'],
                },
                'min_team_size': 5, 'max_team_size': 7,
            },
            'identities': [
                {
                    'field_name': 'codm_uid',
                    'display_name': 'CODM UID',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': 'Your CODM UID',
                    'help_text': 'Your Call of Duty: Mobile UID from player profile',
                },
            ],
            'roles': [
                {'role_name': 'Slayer', 'role_code': 'SLR', 'icon': '🎯', 'color': '#ff4655', 'order': 1},
                {'role_name': 'OBJ', 'role_code': 'OBJ', 'icon': '🏁', 'color': '#4caf50', 'order': 2},
                {'role_name': 'Anchor', 'role_code': 'ANC', 'icon': '⚓', 'color': '#2196f3', 'order': 3},
                {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#f39c12', 'order': 4},
                {'role_name': 'Flex', 'role_code': 'FLX', 'icon': '🔄', 'color': '#7c3aed', 'order': 5},
            ],
        },
        {
            'slug': 'freefire',
            'name': 'Free Fire',
            'display_name': 'Garena Free Fire',
            'short_code': 'FF',
            'category': 'BR',
            'game_type': 'BATTLE_ROYALE',
            'platforms': ['Mobile'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'bronze', 'label': 'Bronze'},
                {'value': 'silver', 'label': 'Silver'},
                {'value': 'gold', 'label': 'Gold'},
                {'value': 'platinum', 'label': 'Platinum'},
                {'value': 'diamond', 'label': 'Diamond'},
                {'value': 'heroic', 'label': 'Heroic'},
                {'value': 'grandmaster', 'label': 'Grandmaster'},
            ],
            'primary_color': '#ff6f00',
            'secondary_color': '#1a1a2e',
            'description': 'Free Fire is a mobile battle royale game with fast-paced action.',
            'developer': '111 Dots Studio',
            'publisher': 'Garena',
            'roster': {
                'min_team_size': 4, 'max_team_size': 4,
                'min_substitutes': 0, 'max_substitutes': 0,
                'min_roster_size': 4, 'max_roster_size': 4,
            },
            'tournament': {
                'available_match_formats': ['SINGLE', 'SERIES'],
                'default_match_format': 'SERIES',
                'default_scoring_type': 'PLACEMENT',
                'scoring_rules': {
                    'placement_points': {1: 12, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1, 11: 1, 12: 0},
                    'kill_points': 1,
                },
                'default_tiebreakers': ['total_points', 'total_kills', 'placements'],
                'supports_single_elimination': False,
                'supports_double_elimination': False,
                'supports_round_robin': False,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 25,
                'allow_draws': False,
                'overtime_enabled': False,
                'min_team_size': 4, 'max_team_size': 4,
            },
            'identities': [
                {
                    'field_name': 'freefire_uid',
                    'display_name': 'Free Fire UID',
                    'field_type': 'NUMBER',
                    'is_required': True,
                    'placeholder': '123456789',
                    'help_text': 'Your Free Fire numeric UID from player profile',
                },
            ],
            'roles': [],
        },
        {
            'slug': 'pubg',
            'name': 'PUBG Mobile',
            'display_name': 'PUBG MOBILE',
            'short_code': 'PUBGM',
            'category': 'BR',
            'game_type': 'BATTLE_ROYALE',
            'platforms': ['Mobile'],
            'has_servers': True,
            'has_rank_system': True,
            'available_ranks': [
                {'value': 'bronze', 'label': 'Bronze'},
                {'value': 'silver', 'label': 'Silver'},
                {'value': 'gold', 'label': 'Gold'},
                {'value': 'platinum', 'label': 'Platinum'},
                {'value': 'diamond', 'label': 'Diamond'},
                {'value': 'crown', 'label': 'Crown'},
                {'value': 'ace', 'label': 'Ace'},
                {'value': 'ace_master', 'label': 'Ace Master'},
                {'value': 'ace_dominator', 'label': 'Ace Dominator'},
                {'value': 'conqueror', 'label': 'Conqueror'},
            ],
            'primary_color': '#f5a623',
            'secondary_color': '#1a1a2e',
            'description': 'PUBG Mobile is a battle royale game where 100 players fight to be the last one standing.',
            'developer': 'LightSpeed & Quantum Studio',
            'publisher': 'Tencent Games',
            'roster': {
                'min_team_size': 4, 'max_team_size': 4,
                'min_substitutes': 0, 'max_substitutes': 0,
                'min_roster_size': 4, 'max_roster_size': 4,
            },
            'tournament': {
                'available_match_formats': ['SINGLE', 'SERIES'],
                'default_match_format': 'SERIES',
                'default_scoring_type': 'PLACEMENT',
                'scoring_rules': {
                    'placement_points': {1: 15, 2: 12, 3: 10, 4: 8, 5: 6, 6: 4, 7: 2, 8: 1},
                    'kill_points': 1,
                },
                'default_tiebreakers': ['total_points', 'total_kills', 'wwcd'],
                'supports_single_elimination': False,
                'supports_double_elimination': False,
                'supports_round_robin': False,
                'supports_swiss': False,
                'supports_group_stage': True,
                'default_match_duration_minutes': 30,
                'allow_draws': False,
                'overtime_enabled': False,
                'min_team_size': 4, 'max_team_size': 4,
            },
            'identities': [
                {
                    'field_name': 'pubg_uid',
                    'display_name': 'PUBG Mobile UID',
                    'field_type': 'NUMBER',
                    'is_required': True,
                    'placeholder': '5123456789',
                    'help_text': 'Your PUBG Mobile numeric Character ID',
                },
                {
                    'field_name': 'pubg_ign',
                    'display_name': 'In-Game Name',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'placeholder': 'YourIGN',
                    'help_text': 'Your PUBG Mobile in-game name',
                },
            ],
            'roles': [
                {'role_name': 'IGL', 'role_code': 'IGL', 'icon': '📢', 'color': '#4caf50', 'order': 1},
                {'role_name': 'Assaulter', 'role_code': 'AST', 'icon': '⚔️', 'color': '#ff4655', 'order': 2},
                {'role_name': 'Sniper', 'role_code': 'SNP', 'icon': '🔭', 'color': '#2196f3', 'order': 3},
                {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#f5a623', 'order': 4},
            ],
        },
    ]

    # Legacy slugs to watch for
    LEGACY_SLUGS = {
        'pubg-mobile': 'pubg',
        'pubgmobile': 'pubg',
        'fifa': 'fc26',
        'fifa26': 'fc26',
        'csgo': 'cs2',
        'counter-strike': 'cs2',
        'mobile-legends': 'mlbb',
        'call-of-duty-mobile': 'codm',
        'free-fire': 'freefire',
        'e-football': 'efootball',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update all fields even if game already exists',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force_update = options.get('force_update', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        self.stdout.write(self.style.SUCCESS('Initializing Default Games for DeltaCrown'))
        self.stdout.write('=' * 70)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for spec in self.CANONICAL_GAMES:
                slug = spec['slug']
                name = spec['name']

                try:
                    game = Game.objects.get(slug=slug)
                    # Game exists
                    if force_update:
                        if not dry_run:
                            self._update_game(game, spec)
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'  Updated: {name} ({slug})')
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(f'  Skipped: {name} ({slug}) - already exists')

                except Game.DoesNotExist:
                    # Check for name match with different slug (migration)
                    try:
                        game = Game.objects.get(name=name)
                        old_slug = game.slug
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Migrating: {name} from slug "{old_slug}" -> "{slug}"'
                            )
                        )
                        if not dry_run:
                            game.slug = slug
                            self._update_game(game, spec)
                        updated_count += 1

                    except Game.DoesNotExist:
                        # Create new game + all related models
                        if not dry_run:
                            self._create_game(spec)
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  Created: {name} ({slug})')
                        )

            # Check for legacy slugs
            self._check_legacy_slugs()

            if dry_run:
                self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were saved'))
                transaction.set_rollback(True)

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'  Created: {created_count} games')
        self.stdout.write(f'  Updated: {updated_count} games')
        self.stdout.write(f'  Skipped: {skipped_count} games (no changes needed)')
        self.stdout.write(f'  Total canonical games: {len(self.CANONICAL_GAMES)}')

        if created_count > 0 or updated_count > 0:
            self.stdout.write('\n' + self.style.SUCCESS('Game registry is now synchronized!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('  1. Upload game icons/logos via Django admin')
            self.stdout.write('  2. Review game-specific roles')
            self.stdout.write('  3. Customize colors per your theme')
        else:
            self.stdout.write('\n' + self.style.SUCCESS('All games are already up to date!'))

    # ── Private helpers ───────────────────────────────────────────────

    def _create_game(self, spec):
        """Create a Game and all related config models from spec."""
        game = Game.objects.create(
            slug=spec['slug'],
            name=spec['name'],
            display_name=spec.get('display_name', spec['name']),
            short_code=spec['short_code'],
            category=spec['category'],
            game_type=spec.get('game_type', 'TEAM_VS_TEAM'),
            platforms=spec.get('platforms', []),
            has_servers=spec.get('has_servers', False),
            has_rank_system=spec.get('has_rank_system', False),
            available_ranks=spec.get('available_ranks', []),
            primary_color=spec.get('primary_color', '#7c3aed'),
            secondary_color=spec.get('secondary_color', '#1e1b4b'),
            description=spec.get('description', ''),
            developer=spec.get('developer', ''),
            publisher=spec.get('publisher', ''),
            is_active=True,
        )

        # Roster config
        roster = spec.get('roster', {})
        if roster:
            GameRosterConfig.objects.create(
                game=game,
                min_team_size=roster.get('min_team_size', 1),
                max_team_size=roster.get('max_team_size', 5),
                min_substitutes=roster.get('min_substitutes', 0),
                max_substitutes=roster.get('max_substitutes', 2),
                min_roster_size=roster.get('min_roster_size', 1),
                max_roster_size=roster.get('max_roster_size', 10),
            )

        # Tournament config
        tc = spec.get('tournament', {})
        if tc:
            GameTournamentConfig.objects.create(
                game=game,
                available_match_formats=tc.get('available_match_formats', ['BO1', 'BO3']),
                default_match_format=tc.get('default_match_format', 'BO3'),
                default_scoring_type=tc.get('default_scoring_type', 'WIN_LOSS'),
                scoring_rules=tc.get('scoring_rules', {}),
                default_tiebreakers=tc.get('default_tiebreakers', []),
                supports_single_elimination=tc.get('supports_single_elimination', True),
                supports_double_elimination=tc.get('supports_double_elimination', True),
                supports_round_robin=tc.get('supports_round_robin', True),
                supports_swiss=tc.get('supports_swiss', False),
                supports_group_stage=tc.get('supports_group_stage', True),
                default_match_duration_minutes=tc.get('default_match_duration_minutes', 60),
                allow_draws=tc.get('allow_draws', False),
                overtime_enabled=tc.get('overtime_enabled', False),
                extra_config=tc.get('extra_config', {}),
                min_team_size=tc.get('min_team_size', 1),
                max_team_size=tc.get('max_team_size', 5),
            )

        # Player identity configs
        for identity in spec.get('identities', []):
            GamePlayerIdentityConfig.objects.create(
                game=game,
                field_name=identity['field_name'],
                display_name=identity['display_name'],
                field_type=identity.get('field_type', 'TEXT'),
                is_required=identity.get('is_required', True),
                placeholder=identity.get('placeholder', ''),
                help_text=identity.get('help_text', ''),
                validation_regex=identity.get('validation_regex', ''),
                validation_error_message=identity.get('validation_error_message', ''),
            )

        # Game roles
        for role in spec.get('roles', []):
            GameRole.objects.create(
                game=game,
                role_name=role['role_name'],
                role_code=role['role_code'],
                icon=role.get('icon', ''),
                color=role.get('color', ''),
                order=role.get('order', 0),
            )

        return game

    def _update_game(self, game, spec):
        """Update an existing Game and its related models."""
        # Update Game fields
        game.name = spec['name']
        game.display_name = spec.get('display_name', spec['name'])
        game.short_code = spec['short_code']
        game.category = spec['category']
        game.game_type = spec.get('game_type', 'TEAM_VS_TEAM')
        game.platforms = spec.get('platforms', [])
        game.has_servers = spec.get('has_servers', False)
        game.has_rank_system = spec.get('has_rank_system', False)
        game.available_ranks = spec.get('available_ranks', [])
        game.primary_color = spec.get('primary_color', '#7c3aed')
        game.secondary_color = spec.get('secondary_color', '#1e1b4b')
        if not game.description and spec.get('description'):
            game.description = spec['description']
        if spec.get('developer'):
            game.developer = spec['developer']
        if spec.get('publisher'):
            game.publisher = spec['publisher']
        game.save()

        # Update or create roster config
        roster = spec.get('roster', {})
        if roster:
            GameRosterConfig.objects.update_or_create(
                game=game,
                defaults={
                    'min_team_size': roster.get('min_team_size', 1),
                    'max_team_size': roster.get('max_team_size', 5),
                    'min_substitutes': roster.get('min_substitutes', 0),
                    'max_substitutes': roster.get('max_substitutes', 2),
                    'min_roster_size': roster.get('min_roster_size', 1),
                    'max_roster_size': roster.get('max_roster_size', 10),
                },
            )

        # Update or create tournament config
        tc = spec.get('tournament', {})
        if tc:
            GameTournamentConfig.objects.update_or_create(
                game=game,
                defaults={
                    'available_match_formats': tc.get('available_match_formats', ['BO1', 'BO3']),
                    'default_match_format': tc.get('default_match_format', 'BO3'),
                    'default_scoring_type': tc.get('default_scoring_type', 'WIN_LOSS'),
                    'scoring_rules': tc.get('scoring_rules', {}),
                    'default_tiebreakers': tc.get('default_tiebreakers', []),
                    'supports_single_elimination': tc.get('supports_single_elimination', True),
                    'supports_double_elimination': tc.get('supports_double_elimination', True),
                    'supports_round_robin': tc.get('supports_round_robin', True),
                    'supports_swiss': tc.get('supports_swiss', False),
                    'supports_group_stage': tc.get('supports_group_stage', True),
                    'default_match_duration_minutes': tc.get('default_match_duration_minutes', 60),
                    'allow_draws': tc.get('allow_draws', False),
                    'overtime_enabled': tc.get('overtime_enabled', False),
                    'extra_config': tc.get('extra_config', {}),
                    'min_team_size': tc.get('min_team_size', 1),
                    'max_team_size': tc.get('max_team_size', 5),
                },
            )

        # Sync identity configs (delete old, create new)
        identities = spec.get('identities', [])
        if identities:
            game.identity_configs.all().delete()
            for identity in identities:
                GamePlayerIdentityConfig.objects.create(
                    game=game,
                    field_name=identity['field_name'],
                    display_name=identity['display_name'],
                    field_type=identity.get('field_type', 'TEXT'),
                    is_required=identity.get('is_required', True),
                    placeholder=identity.get('placeholder', ''),
                    help_text=identity.get('help_text', ''),
                    validation_regex=identity.get('validation_regex', ''),
                    validation_error_message=identity.get('validation_error_message', ''),
                )

        # Sync roles (delete old, create new)
        roles = spec.get('roles', [])
        if roles:
            game.roles.all().delete()
            for role in roles:
                GameRole.objects.create(
                    game=game,
                    role_name=role['role_name'],
                    role_code=role['role_code'],
                    icon=role.get('icon', ''),
                    color=role.get('color', ''),
                    order=role.get('order', 0),
                )

    def _check_legacy_slugs(self):
        """Check for games with legacy slugs and suggest migration."""
        legacy_games = Game.objects.filter(slug__in=self.LEGACY_SLUGS.keys())

        if legacy_games.exists():
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.WARNING('LEGACY SLUGS DETECTED'))
            self.stdout.write('=' * 70)

            for game in legacy_games:
                canonical_slug = self.LEGACY_SLUGS.get(game.slug)
                self.stdout.write(
                    self.style.WARNING(
                        f'  Legacy slug "{game.slug}" -> Should migrate to "{canonical_slug}"'
                    )
                )
                self.stdout.write(f'     Game: {game.name} (ID: {game.id})')

            self.stdout.write('\nRecommendation:')
            self.stdout.write('  These legacy games should be migrated to canonical slugs.')
            self.stdout.write('  Use --force-update to overwrite, or update manually in admin.')
            self.stdout.write('  DO NOT delete them if they have associated tournaments!')
