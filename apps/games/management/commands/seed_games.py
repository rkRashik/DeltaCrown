"""
Django Management Command: seed_games
=====================================
Seeds 11 major esports titles with authentic December 2025 competitive data.

Usage:
    python manage.py seed_games
    python manage.py seed_games --force  # Force re-seed even if games exist
"""

from django.core.management.base import BaseCommand
from datetime import date
from apps.games.models import (
    Game,
    GameRosterConfig,
    GameRole,
    GamePlayerIdentityConfig,
    GameTournamentConfig
)
from apps.user_profile.models import GamePassportSchema


class Command(BaseCommand):
    help = 'Seed 11 major esports games for DeltaCrown platform (December 2025)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-seed even if games already exist',
        )

    def handle(self, *args, **options):
        force = options['force']

        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("DELTACROWN - GAME SEEDING (DECEMBER 2025)"))
        self.stdout.write("="*70)

        games_data = self.get_games_data()
        self.stdout.write(f"Total games to seed: {len(games_data)}")
        self.stdout.write("="*70)

        seeded_games = []

        for game_slug, game_data in games_data.items():
            try:
                game = self.seed_game(game_slug, game_data, force)
                seeded_games.append(game)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n✗ ERROR seeding {game_slug}: {e}"))
                import traceback
                traceback.print_exc()

        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("SEEDING COMPLETE"))
        self.stdout.write("="*70)
        self.stdout.write(f"✓ Successfully seeded {len(seeded_games)} games:")
        for game in seeded_games:
            featured = " ⭐" if game.is_featured else ""
            self.stdout.write(f"  • {game.display_name} ({game.short_code}){featured}")

        self.stdout.write("\n" + "="*70)
        self.stdout.write("Database Status:")
        self.stdout.write(f"  Total Games: {Game.objects.count()}")
        self.stdout.write(f"  Active Games: {Game.objects.filter(is_active=True).count()}")
        self.stdout.write(f"  Featured Games: {Game.objects.filter(is_featured=True).count()}")
        self.stdout.write(f"  Total Roles: {GameRole.objects.count()}")
        self.stdout.write(f"  Total Identity Configs: {GamePlayerIdentityConfig.objects.count()}")
        self.stdout.write("="*70 + "\n")

    def get_games_data(self):
        """Return the 11 games configuration data."""
        return {
            'valorant': {
                'name': 'Valorant',
                'display_name': 'VALORANT',
                'short_code': 'VAL',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC'],
                'primary_color': '#ff4654',
                'secondary_color': '#0f1923',
                'accent_color': '#ece8e1',
                'description': 'A 5v5 character-based tactical FPS where precise gunplay meets unique agent abilities. The premier VCT Champions 2025 showcased the highest level of competitive play with teams from around the globe.',
                'developer': 'Riot Games',
                'publisher': 'Riot Games',
                'official_website': 'https://playvalorant.com',
                'release_date': date(2020, 6, 2),
                'is_featured': True,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'require_unique_roles': False,
                    'allow_multi_role': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'AMER', 'name': 'Americas'},
                        {'code': 'EMEA', 'name': 'Europe, Middle East, Africa'},
                        {'code': 'PAC', 'name': 'Pacific'},
                        {'code': 'CN', 'name': 'China'},
                    ]
                },
                'roles': [
                    {'role_name': 'Duelist', 'role_code': 'DUE', 'icon': '⚔️', 'color': '#ff4654', 'order': 1, 'description': 'Entry fraggers focused on aggressive plays'},
                    {'role_name': 'Controller', 'role_code': 'CTRL', 'icon': '🌫️', 'color': '#7c3aed', 'order': 2, 'description': 'Map control and area denial specialists'},
                    {'role_name': 'Initiator', 'role_code': 'INIT', 'icon': '⚡', 'color': '#10b981', 'order': 3, 'description': 'Information gathering and setup utility'},
                    {'role_name': 'Sentinel', 'role_code': 'SENT', 'icon': '🛡️', 'color': '#3b82f6', 'order': 4, 'description': 'Defensive anchors and site holders'},
                ],
                'identity_fields': [
                    {'field_name': 'riot_id', 'display_name': 'Riot ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': False, 'validation_regex': r'^.{3,16}#[a-zA-Z0-9]{3,5}$', 'validation_error_message': 'Must be PlayerName#TAG format', 'placeholder': 'PlayerName#TAG', 'help_text': 'Your Riot ID with tagline (e.g., TenZ#1234)', 'min_length': 5, 'max_length': 24, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'help_text': 'Optional display name', 'max_length': 32, 'order': 2},
                    {'field_name': 'region', 'display_name': 'Primary Region', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your competitive region', 'order': 3},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Your current competitive rank', 'order': 4},
                    {'field_name': 'peak_rank', 'display_name': 'Peak Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Highest rank achieved', 'order': 5},
                    {'field_name': 'role', 'display_name': 'Main Role', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary agent role', 'order': 6},
                ],
                'dropdown_choices': {
                    'region_choices': [
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'EU', 'label': 'Europe'},
                        {'value': 'KR', 'label': 'Korea'},
                        {'value': 'BR', 'label': 'Brazil'},
                        {'value': 'LATAM', 'label': 'Latin America'},
                        {'value': 'AP', 'label': 'Asia Pacific'},
                    ],
                    'rank_choices': [
                        {'value': 'Iron_1', 'label': 'Iron 1', 'tier': 1},
                        {'value': 'Iron_2', 'label': 'Iron 2', 'tier': 2},
                        {'value': 'Iron_3', 'label': 'Iron 3', 'tier': 3},
                        {'value': 'Bronze_1', 'label': 'Bronze 1', 'tier': 4},
                        {'value': 'Bronze_2', 'label': 'Bronze 2', 'tier': 5},
                        {'value': 'Bronze_3', 'label': 'Bronze 3', 'tier': 6},
                        {'value': 'Silver_1', 'label': 'Silver 1', 'tier': 7},
                        {'value': 'Silver_2', 'label': 'Silver 2', 'tier': 8},
                        {'value': 'Silver_3', 'label': 'Silver 3', 'tier': 9},
                        {'value': 'Gold_1', 'label': 'Gold 1', 'tier': 10},
                        {'value': 'Gold_2', 'label': 'Gold 2', 'tier': 11},
                        {'value': 'Gold_3', 'label': 'Gold 3', 'tier': 12},
                        {'value': 'Platinum_1', 'label': 'Platinum 1', 'tier': 13},
                        {'value': 'Platinum_2', 'label': 'Platinum 2', 'tier': 14},
                        {'value': 'Platinum_3', 'label': 'Platinum 3', 'tier': 15},
                        {'value': 'Diamond_1', 'label': 'Diamond 1', 'tier': 16},
                        {'value': 'Diamond_2', 'label': 'Diamond 2', 'tier': 17},
                        {'value': 'Diamond_3', 'label': 'Diamond 3', 'tier': 18},
                        {'value': 'Ascendant_1', 'label': 'Ascendant 1', 'tier': 19},
                        {'value': 'Ascendant_2', 'label': 'Ascendant 2', 'tier': 20},
                        {'value': 'Ascendant_3', 'label': 'Ascendant 3', 'tier': 21},
                        {'value': 'Immortal_1', 'label': 'Immortal 1', 'tier': 22},
                        {'value': 'Immortal_2', 'label': 'Immortal 2', 'tier': 23},
                        {'value': 'Immortal_3', 'label': 'Immortal 3', 'tier': 24},
                        {'value': 'Radiant', 'label': 'Radiant', 'tier': 25},
                    ],
                    'role_choices': [
                        {'value': 'Duelist', 'label': 'Duelist'},
                        {'value': 'Controller', 'label': 'Controller'},
                        {'value': 'Initiator', 'label': 'Initiator'},
                        {'value': 'Sentinel', 'label': 'Sentinel'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3', 'BO5'],
                    'default_match_format': 'BO3',
                    'default_scoring_type': 'ROUNDS',
                    'scoring_rules': {
                        'rounds_to_win': 13,
                        'overtime_rounds': 2,
                        'max_overtime_rounds': 4,
                    },
                    'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                    'default_match_duration_minutes': 45,
                    'allow_draws': False,
                    'overtime_enabled': True,
                    'require_check_in': True,
                    'check_in_window_minutes': 30,
                }
            },

            'cs2': {
                'name': 'Counter-Strike 2',
                'display_name': 'Counter-Strike 2',
                'short_code': 'CS2',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC'],
                'primary_color': '#f5a623',
                'secondary_color': '#1b2838',
                'accent_color': '#ffd700',
                'description': 'The legendary tactical FPS reimagined on Source 2 engine. IEM Katowice 2025 and BLAST Premier 2025 showcased the highest tier of competitive CS.',
                'developer': 'Valve Corporation',
                'publisher': 'Valve Corporation',
                'official_website': 'https://counter-strike.net',
                'release_date': date(2023, 9, 27),
                'is_featured': True,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'require_unique_roles': False,
                    'allow_multi_role': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'EU', 'name': 'Europe'},
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'SA', 'name': 'South America'},
                        {'code': 'ASIA', 'name': 'Asia'},
                        {'code': 'OCE', 'name': 'Oceania'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                    ]
                },
                'roles': [
                    {'role_name': 'AWPer', 'role_code': 'AWP', 'icon': '🎯', 'color': '#f5a623', 'order': 1, 'description': 'Primary sniper and picks'},
                    {'role_name': 'Entry Fragger', 'role_code': 'ENTRY', 'icon': '⚔️', 'color': '#ff4654', 'order': 2, 'description': 'First in, creates openings'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#10b981', 'order': 3, 'description': 'Utility and trades'},
                    {'role_name': 'In-Game Leader', 'role_code': 'IGL', 'icon': '🧠', 'color': '#7c3aed', 'order': 4, 'description': 'Strategy caller'},
                    {'role_name': 'Lurker', 'role_code': 'LURK', 'icon': '👁️', 'color': '#6b7280', 'order': 5, 'description': 'Information and flanks'},
                ],
                'identity_fields': [
                    {'field_name': 'steam_id', 'display_name': 'Steam ID64', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^7656119\d{10}$', 'validation_error_message': 'Must be 17-digit Steam ID64', 'placeholder': '76561198012345678', 'help_text': 'Your 17-digit Steam ID', 'min_length': 17, 'max_length': 17, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'region', 'display_name': 'Primary Region', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your matchmaking region', 'order': 3},
                    {'field_name': 'premier_rating', 'display_name': 'Premier Rating', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'CS2 Premier rating', 'order': 4},
                    {'field_name': 'role', 'display_name': 'Main Role', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary in-game role', 'order': 5},
                ],
                'dropdown_choices': {
                    'region_choices': [
                        {'value': 'EU', 'label': 'Europe'},
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'SA', 'label': 'South America'},
                        {'value': 'ASIA', 'label': 'Asia'},
                        {'value': 'OCE', 'label': 'Oceania'},
                        {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    ],
                    'premier_rating_choices': [
                        {'value': '0-4999', 'label': '0-4,999', 'tier': 1},
                        {'value': '5000-9999', 'label': '5,000-9,999', 'tier': 2},
                        {'value': '10000-14999', 'label': '10,000-14,999', 'tier': 3},
                        {'value': '15000-19999', 'label': '15,000-19,999', 'tier': 4},
                        {'value': '20000-24999', 'label': '20,000-24,999', 'tier': 5},
                        {'value': '25000-29999', 'label': '25,000-29,999', 'tier': 6},
                        {'value': '30000+', 'label': '30,000+', 'tier': 7},
                    ],
                    'role_choices': [
                        {'value': 'AWPer', 'label': 'AWPer'},
                        {'value': 'Entry_Fragger', 'label': 'Entry Fragger'},
                        {'value': 'Support', 'label': 'Support'},
                        {'value': 'IGL', 'label': 'In-Game Leader'},
                        {'value': 'Lurker', 'label': 'Lurker'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3', 'BO5'],
                    'default_match_format': 'BO3',
                    'default_scoring_type': 'ROUNDS',
                    'scoring_rules': {
                        'rounds_to_win': 16,
                        'max_rounds': 30,
                        'overtime_rounds': 3,
                    },
                    'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                    'default_match_duration_minutes': 60,
                    'allow_draws': False,
                    'overtime_enabled': True,
                }
            },

            'dota2': {
                'name': 'Dota 2',
                'display_name': 'Dota 2',
                'short_code': 'DOTA',
                'category': 'MOBA',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC'],
                'primary_color': '#af1f23',
                'secondary_color': '#1b2838',
                'accent_color': '#c23c2a',
                'description': 'The premier 5v5 MOBA with deep strategic gameplay. The International 2025 featured a $40M+ prize pool, cementing its status as the pinnacle of competitive gaming.',
                'developer': 'Valve Corporation',
                'publisher': 'Valve Corporation',
                'official_website': 'https://dota2.com',
                'release_date': date(2013, 7, 9),
                'is_featured': True,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'require_unique_roles': True,
                    'allow_multi_role': False,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'WEU', 'name': 'Western Europe'},
                        {'code': 'EEU', 'name': 'Eastern Europe'},
                        {'code': 'CN', 'name': 'China'},
                        {'code': 'SEA', 'name': 'Southeast Asia'},
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'SA', 'name': 'South America'},
                    ]
                },
                'roles': [
                    {'role_name': 'Position 1 (Carry)', 'role_code': 'POS1', 'icon': '⚔️', 'color': '#ff4654', 'order': 1, 'description': 'Farm priority, late-game carry'},
                    {'role_name': 'Position 2 (Mid)', 'role_code': 'POS2', 'icon': '🔮', 'color': '#7c3aed', 'order': 2, 'description': 'Solo mid, tempo controller'},
                    {'role_name': 'Position 3 (Offlane)', 'role_code': 'POS3', 'icon': '🛡️', 'color': '#10b981', 'order': 3, 'description': 'Offlane, space creator'},
                    {'role_name': 'Position 4 (Soft Support)', 'role_code': 'POS4', 'icon': '⚡', 'color': '#3b82f6', 'order': 4, 'description': 'Roaming support, utility'},
                    {'role_name': 'Position 5 (Hard Support)', 'role_code': 'POS5', 'icon': '💚', 'color': '#059669', 'order': 5, 'description': 'Ward support, sacrifice'},
                ],
                'identity_fields': [
                    {'field_name': 'steam_id', 'display_name': 'Steam ID64', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^7656119\d{10}$', 'validation_error_message': 'Must be 17-digit Steam ID64', 'placeholder': '76561198012345678', 'help_text': 'Your 17-digit Steam ID', 'min_length': 17, 'max_length': 17, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'server', 'display_name': 'Primary Server', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Main server for ranked games', 'order': 3},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Current MMR rank', 'order': 4},
                    {'field_name': 'role', 'display_name': 'Main Role', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary position (1-5)', 'order': 5},
                ],
                'dropdown_choices': {
                    'server_choices': [
                        {'value': 'WEU', 'label': 'Western Europe'},
                        {'value': 'EEU', 'label': 'Eastern Europe'},
                        {'value': 'CN', 'label': 'China'},
                        {'value': 'SEA', 'label': 'Southeast Asia'},
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'SA', 'label': 'South America'},
                    ],
                    'rank_choices': [
                        {'value': 'Herald', 'label': 'Herald', 'tier': 1},
                        {'value': 'Guardian', 'label': 'Guardian', 'tier': 2},
                        {'value': 'Crusader', 'label': 'Crusader', 'tier': 3},
                        {'value': 'Archon', 'label': 'Archon', 'tier': 4},
                        {'value': 'Legend', 'label': 'Legend', 'tier': 5},
                        {'value': 'Ancient', 'label': 'Ancient', 'tier': 6},
                        {'value': 'Divine', 'label': 'Divine', 'tier': 7},
                        {'value': 'Immortal', 'label': 'Immortal', 'tier': 8},
                    ],
                    'role_choices': [
                        {'value': 'Position_1', 'label': 'Position 1 (Carry)'},
                        {'value': 'Position_2', 'label': 'Position 2 (Mid)'},
                        {'value': 'Position_3', 'label': 'Position 3 (Offlane)'},
                        {'value': 'Position_4', 'label': 'Position 4 (Soft Support)'},
                        {'value': 'Position_5', 'label': 'Position 5 (Hard Support)'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3', 'BO5'],
                    'default_match_format': 'BO3',
                    'default_scoring_type': 'WIN_LOSS',
                    'default_tiebreakers': ['head_to_head', 'time_rating'],
                    'default_match_duration_minutes': 45,
                    'allow_draws': False,
                }
            },

            'ea-fc': {
                'name': 'EA Sports FC 26',
                'display_name': 'EA SPORTS FC™ 26',
                'short_code': 'FC26',
                'category': 'SPORTS',
                'game_type': '1V1',
                'platforms': ['PC', 'Console', 'Mobile'],
                'primary_color': '#00a850',
                'secondary_color': '#001e3c',
                'accent_color': '#ffd700',
                'description': 'The next generation of football gaming. EA Sports FC Pro 2025 World Championship features the best 1v1 and 2v2 competitive players globally.',
                'developer': 'EA Vancouver',
                'publisher': 'Electronic Arts',
                'official_website': 'https://ea.com/games/ea-sports-fc',
                'release_date': date(2025, 9, 27),
                'is_featured': True,
                'roster': {
                    'min_team_size': 1,
                    'max_team_size': 2,
                    'min_roster_size': 1,
                    'max_roster_size': 3,
                    'min_substitutes': 0,
                    'max_substitutes': 1,
                    'has_roles': False,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'EU', 'name': 'Europe'},
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'ASIA', 'name': 'Asia'},
                        {'code': 'ME', 'name': 'Middle East'},
                    ]
                },
                'identity_fields': [
                    {'field_name': 'ea_id', 'display_name': 'EA ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'placeholder': 'YourEAID', 'help_text': 'Your EA Account ID / Persona ID', 'max_length': 64, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'platform', 'display_name': 'Platform', 'field_type': 'SELECT', 'is_required': True, 'is_immutable': True, 'help_text': 'Your gaming platform (cannot change)', 'order': 3},
                    {'field_name': 'division', 'display_name': 'Division', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'FUT Rivals division', 'order': 4},
                    {'field_name': 'mode', 'display_name': 'Main Mode', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary competitive mode', 'order': 5},
                ],
                'dropdown_choices': {
                    'platform_choices': [
                        {'value': 'PS5', 'label': 'PlayStation 5'},
                        {'value': 'PS4', 'label': 'PlayStation 4'},
                        {'value': 'XBOX_SERIES', 'label': 'Xbox Series X|S'},
                        {'value': 'XBOX_ONE', 'label': 'Xbox One'},
                        {'value': 'PC', 'label': 'PC (EA App / Steam)'},
                        {'value': 'SWITCH', 'label': 'Nintendo Switch'},
                    ],
                    'division_choices': [
                        {'value': 'Division_10', 'label': 'Division 10', 'tier': 1},
                        {'value': 'Division_9', 'label': 'Division 9', 'tier': 2},
                        {'value': 'Division_8', 'label': 'Division 8', 'tier': 3},
                        {'value': 'Division_7', 'label': 'Division 7', 'tier': 4},
                        {'value': 'Division_6', 'label': 'Division 6', 'tier': 5},
                        {'value': 'Division_5', 'label': 'Division 5', 'tier': 6},
                        {'value': 'Division_4', 'label': 'Division 4', 'tier': 7},
                        {'value': 'Division_3', 'label': 'Division 3', 'tier': 8},
                        {'value': 'Division_2', 'label': 'Division 2', 'tier': 9},
                        {'value': 'Division_1', 'label': 'Division 1', 'tier': 10},
                        {'value': 'Elite', 'label': 'Elite Division', 'tier': 11},
                    ],
                    'mode_choices': [
                        {'value': 'FUT_Champs', 'label': 'FUT Champions'},
                        {'value': 'FUT_Rivals', 'label': 'FUT Rivals'},
                        {'value': 'Pro_Clubs', 'label': 'Pro Clubs'},
                        {'value': 'Seasons', 'label': 'Seasons'},
                        {'value': 'Draft', 'label': 'Draft'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3'],
                    'default_match_format': 'BO1',
                    'default_scoring_type': 'GOALS',
                    'default_tiebreakers': ['goal_difference', 'goals_scored'],
                    'default_match_duration_minutes': 12,
                    'allow_draws': True,
                    'overtime_enabled': True,
                }
            },

            'efootball': {
                'name': 'eFootball',
                'display_name': 'eFootball™ 2026',
                'short_code': 'EFB',
                'category': 'SPORTS',
                'game_type': '1V1',
                'platforms': ['PC', 'Console', 'Mobile'],
                'primary_color': '#0051a5',
                'secondary_color': '#ffffff',
                'accent_color': '#00b0ff',
                'description': 'Free-to-play cross-platform football simulation. eFootball Championship Pro 2025 showcased elite 1v1 competitive gameplay.',
                'developer': 'Konami',
                'publisher': 'Konami',
                'official_website': 'https://efootball.konami.net',
                'release_date': date(2021, 9, 30),
                'is_featured': False,
                'roster': {
                    'min_team_size': 1,
                    'max_team_size': 1,
                    'min_roster_size': 1,
                    'max_roster_size': 2,
                    'has_roles': False,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'GLOBAL', 'name': 'Global'},
                    ]
                },
                'identity_fields': [
                    {'field_name': 'konami_id', 'display_name': 'Konami ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'placeholder': 'exampleUser123', 'help_text': 'Find at my.konami.net → Personal Info → Konami ID', 'max_length': 64, 'order': 1},
                    {'field_name': 'user_id', 'display_name': 'User ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'placeholder': 'ABCD-123-456-789', 'help_text': 'In-game: Extras → User Information → User Personal Information → User ID', 'validation_regex': r'^[A-Z]{4}-\d{3}-\d{3}-\d{3}$', 'validation_error_message': 'Must be format: XXXX-XXX-XXX-XXX', 'max_length': 19, 'order': 2},
                    {'field_name': 'username', 'display_name': 'Username', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'rkrashik', 'help_text': 'Your in-game username (optional)', 'max_length': 32, 'order': 3},
                    {'field_name': 'division', 'display_name': 'Division', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Your current competitive division', 'order': 4},
                    {'field_name': 'team_name', 'display_name': 'Team Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'SIUU', 'help_text': 'Your custom team name', 'max_length': 32, 'order': 5},
                    {'field_name': 'platform', 'display_name': 'Platform', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your gaming platform', 'order': 6},
                ],
                'dropdown_choices': {
                    'platform_choices': [
                        {'value': 'PS5', 'label': 'PlayStation 5'},
                        {'value': 'PS4', 'label': 'PlayStation 4'},
                        {'value': 'XBOX_SERIES', 'label': 'Xbox Series X|S'},
                        {'value': 'XBOX_ONE', 'label': 'Xbox One'},
                        {'value': 'PC', 'label': 'PC (Steam)'},
                        {'value': 'MOBILE', 'label': 'Mobile (iOS/Android)'},
                    ],
                    'division_choices': [
                        {'value': 'Division_9', 'label': 'Division 9', 'tier': 1},
                        {'value': 'Division_8', 'label': 'Division 8', 'tier': 2},
                        {'value': 'Division_7', 'label': 'Division 7', 'tier': 3},
                        {'value': 'Division_6', 'label': 'Division 6', 'tier': 4},
                        {'value': 'Division_5', 'label': 'Division 5', 'tier': 5},
                        {'value': 'Division_4', 'label': 'Division 4', 'tier': 6},
                        {'value': 'Division_3', 'label': 'Division 3', 'tier': 7},
                        {'value': 'Division_2', 'label': 'Division 2', 'tier': 8},
                        {'value': 'Division_1', 'label': 'Division 1', 'tier': 9},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3'],
                    'default_match_format': 'BO1',
                    'default_scoring_type': 'GOALS',
                    'default_tiebreakers': ['goal_difference', 'goals_scored'],
                    'default_match_duration_minutes': 10,
                    'allow_draws': True,
                }
            },

            'pubgm': {
                'name': 'PUBG Mobile',
                'display_name': 'PUBG MOBILE',
                'short_code': 'PUBGM',
                'category': 'BR',
                'game_type': 'BATTLE_ROYALE',
                'platforms': ['Mobile'],
                'primary_color': '#f59f00',
                'secondary_color': '#1a1919',
                'accent_color': '#ffb703',
                'description': 'The #1 mobile battle royale with 100-player matches. PMGC 2025 (PUBG Mobile Global Championship) featured the world\'s best squads competing for millions.',
                'developer': 'Tencent Games',
                'publisher': 'Krafton',
                'official_website': 'https://pubgmobile.com',
                'release_date': date(2018, 3, 19),
                'is_featured': True,
                'roster': {
                    'min_team_size': 4,
                    'max_team_size': 4,
                    'min_roster_size': 4,
                    'max_roster_size': 8,
                    'min_substitutes': 0,
                    'max_substitutes': 4,
                    'has_roles': True,
                    'require_unique_roles': False,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'SEA', 'name': 'Southeast Asia'},
                        {'code': 'SA', 'name': 'South Asia'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                        {'code': 'CN', 'name': 'China'},
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'EU', 'name': 'Europe'},
                    ]
                },
                'roles': [
                    {'role_name': 'IGL (In-Game Leader)', 'role_code': 'IGL', 'icon': '🧠', 'color': '#7c3aed', 'order': 1, 'description': 'Shot caller and strategist'},
                    {'role_name': 'Fragger', 'role_code': 'FRAG', 'icon': '⚔️', 'color': '#ff4654', 'order': 2, 'description': 'Aggressive entry and eliminations'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#10b981', 'order': 3, 'description': 'Utility and covering fire'},
                    {'role_name': 'Sniper', 'role_code': 'SNP', 'icon': '🎯', 'color': '#3b82f6', 'order': 4, 'description': 'Long-range picks'},
                ],
                'identity_fields': [
                    {'field_name': 'player_id', 'display_name': 'Character ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^\d{9,12}$', 'validation_error_message': 'Must be 9-12 digit Character ID', 'placeholder': '5123456789', 'help_text': 'Your PUBG Mobile Character ID', 'min_length': 9, 'max_length': 12, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'server', 'display_name': 'Server', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your server region', 'order': 3},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Current ranked season rank', 'order': 4},
                    {'field_name': 'peak_rank', 'display_name': 'Peak Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Highest rank across all modes', 'order': 5},
                    {'field_name': 'mode', 'display_name': 'Main Mode', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary game mode', 'order': 6},
                ],
                'dropdown_choices': {
                    'server_choices': [
                        {'value': 'SEA', 'label': 'Southeast Asia'},
                        {'value': 'SA', 'label': 'South Asia'},
                        {'value': 'MENA', 'label': 'Middle East & North Africa'},
                        {'value': 'CN', 'label': 'China'},
                        {'value': 'LATAM', 'label': 'Latin America'},
                        {'value': 'EU', 'label': 'Europe'},
                    ],
                    'rank_choices': [
                        {'value': 'Bronze', 'label': 'Bronze', 'tier': 1},
                        {'value': 'Silver', 'label': 'Silver', 'tier': 2},
                        {'value': 'Gold', 'label': 'Gold', 'tier': 3},
                        {'value': 'Platinum', 'label': 'Platinum', 'tier': 4},
                        {'value': 'Diamond', 'label': 'Diamond', 'tier': 5},
                        {'value': 'Crown', 'label': 'Crown', 'tier': 6},
                        {'value': 'Ace', 'label': 'Ace', 'tier': 7},
                        {'value': 'Conqueror', 'label': 'Conqueror', 'tier': 8},
                    ],
                    'mode_choices': [
                        {'value': 'TPP', 'label': 'TPP (Third Person)'},
                        {'value': 'FPP', 'label': 'FPP (First Person)'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['SINGLE'],
                    'default_match_format': 'SINGLE',
                    'default_scoring_type': 'PLACEMENT',
                    'scoring_rules': {
                        'placement_points': [10, 6, 5, 4, 3, 2, 1, 0],
                        'kill_points': 1,
                    },
                    'default_tiebreakers': ['total_points', 'total_kills', 'avg_placement'],
                    'default_match_duration_minutes': 30,
                }
            },

            'mlbb': {
                'name': 'Mobile Legends: Bang Bang',
                'display_name': 'Mobile Legends: Bang Bang',
                'short_code': 'MLBB',
                'category': 'MOBA',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['Mobile'],
                'primary_color': '#3b5998',
                'secondary_color': '#1c2d48',
                'accent_color': '#5271ff',
                'description': 'The #1 mobile MOBA with 5v5 fast-paced battles. M6 World Championship 2025 showcased elite teams from SEA, LATAM, and beyond.',
                'developer': 'Moonton',
                'publisher': 'Moonton',
                'official_website': 'https://m.mobilelegends.com',
                'release_date': date(2016, 7, 14),
                'is_featured': True,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'require_unique_roles': False,
                    'allow_multi_role': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'SEA', 'name': 'Southeast Asia'},
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                        {'code': 'SA', 'name': 'South Asia'},
                        {'code': 'NA', 'name': 'North America'},
                    ]
                },
                'roles': [
                    {'role_name': 'Tank', 'role_code': 'TANK', 'icon': '🛡️', 'color': '#64748b', 'order': 1, 'description': 'Frontline and crowd control'},
                    {'role_name': 'Fighter', 'role_code': 'FTR', 'icon': '⚔️', 'color': '#ff4654', 'order': 2, 'description': 'Durable damage dealers'},
                    {'role_name': 'Assassin', 'role_code': 'ASN', 'icon': '🗡️', 'color': '#7c3aed', 'order': 3, 'description': 'High burst and mobility'},
                    {'role_name': 'Mage', 'role_code': 'MAGE', 'icon': '🔮', 'color': '#3b82f6', 'order': 4, 'description': 'Magic damage dealers'},
                    {'role_name': 'Marksman', 'role_code': 'MM', 'icon': '🎯', 'color': '#f59e0b', 'order': 5, 'description': 'Ranged physical DPS'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '💚', 'color': '#10b981', 'order': 6, 'description': 'Healing and utility'},
                ],
                'identity_fields': [
                    {'field_name': 'game_id', 'display_name': 'Account ID (User ID)', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^\d{8,12}$', 'validation_error_message': 'Must be 8-12 digit Account ID', 'placeholder': '123456789', 'help_text': 'Your MLBB Account ID: Tap profile icon → Copy User ID', 'min_length': 8, 'max_length': 12, 'order': 1},
                    {'field_name': 'server_id', 'display_name': 'Server ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^\d{4,6}$', 'validation_error_message': 'Must be 4-6 digit Server ID', 'placeholder': '12345', 'help_text': 'Your Server ID: Tap profile icon → shown next to User ID', 'min_length': 4, 'max_length': 6, 'order': 2},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'help_text': 'Your current display name (can change)', 'max_length': 32, 'order': 3},
                    {'field_name': 'server', 'display_name': 'Server Region', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your server region', 'order': 4},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Current ranked season rank', 'order': 5},
                    {'field_name': 'role', 'display_name': 'Main Role', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary hero role', 'order': 6},
                ],
                'dropdown_choices': {
                    'server_choices': [
                        {'value': 'SEA', 'label': 'Southeast Asia'},
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'SA', 'label': 'South America'},
                        {'value': 'EU', 'label': 'Europe'},
                        {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    ],
                    'rank_choices': [
                        {'value': 'Warrior', 'label': 'Warrior', 'tier': 1},
                        {'value': 'Elite', 'label': 'Elite', 'tier': 2},
                        {'value': 'Master', 'label': 'Master', 'tier': 3},
                        {'value': 'Grandmaster', 'label': 'Grandmaster', 'tier': 4},
                        {'value': 'Epic', 'label': 'Epic', 'tier': 5},
                        {'value': 'Legend', 'label': 'Legend', 'tier': 6},
                        {'value': 'Mythic', 'label': 'Mythic', 'tier': 7},
                        {'value': 'Mythical_Glory', 'label': 'Mythical Glory', 'tier': 8},
                    ],
                    'role_choices': [
                        {'value': 'Tank', 'label': 'Tank'},
                        {'value': 'Fighter', 'label': 'Fighter'},
                        {'value': 'Assassin', 'label': 'Assassin'},
                        {'value': 'Mage', 'label': 'Mage'},
                        {'value': 'Marksman', 'label': 'Marksman'},
                        {'value': 'Support', 'label': 'Support'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3', 'BO5', 'BO7'],
                    'default_match_format': 'BO3',
                    'default_scoring_type': 'WIN_LOSS',
                    'default_tiebreakers': ['head_to_head', 'game_time'],
                    'default_match_duration_minutes': 20,
                }
            },

            'freefire': {
                'name': 'Free Fire',
                'display_name': 'Free Fire',
                'short_code': 'FF',
                'category': 'BR',
                'game_type': 'BATTLE_ROYALE',
                'platforms': ['Mobile'],
                'primary_color': '#ff5722',
                'secondary_color': '#212121',
                'accent_color': '#ff7043',
                'description': 'Fast-paced 50-player mobile battle royale. FFWS 2025 (Free Fire World Series) featured top squads competing globally.',
                'developer': 'Garena',
                'publisher': 'Garena',
                'official_website': 'https://ff.garena.com',
                'release_date': date(2017, 12, 4),
                'is_featured': False,
                'roster': {
                    'min_team_size': 4,
                    'max_team_size': 4,
                    'min_roster_size': 4,
                    'max_roster_size': 8,
                    'min_substitutes': 0,
                    'max_substitutes': 4,
                    'has_roles': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'SEA', 'name': 'Southeast Asia'},
                        {'code': 'SA', 'name': 'South Asia'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                    ]
                },
                'roles': [
                    {'role_name': 'Rusher', 'role_code': 'RUSH', 'icon': '⚡', 'color': '#ff4654', 'order': 1, 'description': 'Aggressive push'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#10b981', 'order': 2, 'description': 'Utility and backup'},
                    {'role_name': 'IGL', 'role_code': 'IGL', 'icon': '🧠', 'color': '#7c3aed', 'order': 3, 'description': 'In-game leader'},
                ],
                'identity_fields': [
                    {'field_name': 'player_id', 'display_name': 'Player ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^\d{9,12}$', 'validation_error_message': 'Must be 9-12 digit Player ID', 'placeholder': '1234567890', 'help_text': 'Your Free Fire Player ID', 'min_length': 9, 'max_length': 12, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'server', 'display_name': 'Server', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your server region', 'order': 3},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Current ranked season rank', 'order': 4},
                ],
                'dropdown_choices': {
                    'server_choices': [
                        {'value': 'SEA', 'label': 'Southeast Asia'},
                        {'value': 'LATAM', 'label': 'Latin America'},
                        {'value': 'MENA', 'label': 'Middle East & North Africa'},
                        {'value': 'IND', 'label': 'India'},
                    ],
                    'rank_choices': [
                        {'value': 'Bronze', 'label': 'Bronze', 'tier': 1},
                        {'value': 'Silver', 'label': 'Silver', 'tier': 2},
                        {'value': 'Gold', 'label': 'Gold', 'tier': 3},
                        {'value': 'Platinum', 'label': 'Platinum', 'tier': 4},
                        {'value': 'Diamond', 'label': 'Diamond', 'tier': 5},
                        {'value': 'Heroic', 'label': 'Heroic', 'tier': 6},
                        {'value': 'Grandmaster', 'label': 'Grandmaster', 'tier': 7},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['SINGLE'],
                    'default_match_format': 'SINGLE',
                    'default_scoring_type': 'PLACEMENT',
                    'default_tiebreakers': ['total_points', 'total_kills'],
                    'default_match_duration_minutes': 15,
                }
            },

            'codm': {
                'name': 'Call of Duty: Mobile',
                'display_name': 'Call of Duty®: Mobile',
                'short_code': 'CODM',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['Mobile'],
                'primary_color': '#000000',
                'secondary_color': '#ff6b00',
                'accent_color': '#00d9ff',
                'description': 'Premium mobile FPS with 5v5 competitive modes. CODM World Championship 2025 featured elite teams across multiple game modes.',
                'developer': 'TiMi Studios',
                'publisher': 'Activision',
                'official_website': 'https://callofduty.com/mobile',
                'release_date': date(2019, 10, 1),
                'is_featured': False,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'EU', 'name': 'Europe'},
                        {'code': 'SEA', 'name': 'Southeast Asia'},
                        {'code': 'SA', 'name': 'South Asia'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                    ]
                },
                'roles': [
                    {'role_name': 'Slayer', 'role_code': 'SLY', 'icon': '⚔️', 'color': '#ff4654', 'order': 1, 'description': 'High-kill fragger'},
                    {'role_name': 'Objective Player', 'role_code': 'OBJ', 'icon': '🎯', 'color': '#3b82f6', 'order': 2, 'description': 'Objective focused'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#10b981', 'order': 3, 'description': 'Team utility'},
                    {'role_name': 'Sniper', 'role_code': 'SNP', 'icon': '🎯', 'color': '#7c3aed', 'order': 4, 'description': 'Long-range picks'},
                ],
                'identity_fields': [
                    {'field_name': 'codm_uid', 'display_name': 'COD Mobile UID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'validation_regex': r'^6\d{9}$', 'validation_error_message': 'Must be 10-digit UID starting with 6', 'placeholder': '6000000000', 'help_text': 'Your COD Mobile UID (starts with 6)', 'min_length': 10, 'max_length': 10, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'region', 'display_name': 'Region', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your server region', 'order': 3},
                    {'field_name': 'rank_mp', 'display_name': 'MP Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Multiplayer ranked mode rank', 'order': 4},
                    {'field_name': 'rank_br', 'display_name': 'BR Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Battle Royale ranked mode rank', 'order': 5},
                    {'field_name': 'mode', 'display_name': 'Main Mode', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary competitive mode', 'order': 6},
                ],
                'dropdown_choices': {
                    'region_choices': [
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'EU', 'label': 'Europe'},
                        {'value': 'SEA', 'label': 'Southeast Asia'},
                        {'value': 'SA', 'label': 'South Asia'},
                        {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    ],
                    'rank_choices': [
                        {'value': 'Rookie', 'label': 'Rookie', 'tier': 1},
                        {'value': 'Veteran', 'label': 'Veteran', 'tier': 2},
                        {'value': 'Elite', 'label': 'Elite', 'tier': 3},
                        {'value': 'Pro', 'label': 'Pro', 'tier': 4},
                        {'value': 'Master', 'label': 'Master', 'tier': 5},
                        {'value': 'Grandmaster', 'label': 'Grandmaster', 'tier': 6},
                        {'value': 'Legendary', 'label': 'Legendary', 'tier': 7},
                    ],
                    'mode_choices': [
                        {'value': 'MP', 'label': 'Multiplayer'},
                        {'value': 'BR', 'label': 'Battle Royale'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3', 'BO5'],
                    'default_match_format': 'BO3',
                    'default_scoring_type': 'ROUNDS',
                    'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                    'default_match_duration_minutes': 30,
                }
            },

            'rocketleague': {
                'name': 'Rocket League',
                'display_name': 'Rocket League',
                'short_code': 'RL',
                'category': 'SPORTS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC', 'Console'],
                'primary_color': '#00b8fc',
                'secondary_color': '#0a0e27',
                'accent_color': '#ff8c00',
                'description': 'High-octane vehicular soccer. RLCS 2025 World Championship showcased the pinnacle of 3v3 competitive car-football.',
                'developer': 'Psyonix',
                'publisher': 'Epic Games',
                'official_website': 'https://rocketleague.com',
                'release_date': date(2015, 7, 7),
                'is_featured': True,
                'roster': {
                    'min_team_size': 3,
                    'max_team_size': 3,
                    'min_roster_size': 3,
                    'max_roster_size': 6,
                    'min_substitutes': 0,
                    'max_substitutes': 3,
                    'has_roles': False,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'EU', 'name': 'Europe'},
                        {'code': 'SAM', 'name': 'South America'},
                        {'code': 'OCE', 'name': 'Oceania'},
                        {'code': 'MENA', 'name': 'Middle East & North Africa'},
                        {'code': 'ASIA', 'name': 'Asia'},
                    ]
                },
                'identity_fields': [
                    {'field_name': 'epic_id', 'display_name': 'Epic Games ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'placeholder': 'YourEpicID', 'help_text': 'Your Epic Games account name', 'max_length': 64, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'platform', 'display_name': 'Platform', 'field_type': 'SELECT', 'is_required': True, 'is_immutable': True, 'help_text': 'Your primary gaming platform', 'order': 3},
                    {'field_name': 'rank', 'display_name': 'Highest Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Highest rank across all competitive modes', 'order': 4},
                    {'field_name': 'mode', 'display_name': 'Main Mode', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary competitive mode', 'order': 5},
                ],
                'dropdown_choices': {
                    'platform_choices': [
                        {'value': 'PC', 'label': 'PC (Epic Games)'},
                        {'value': 'PS5', 'label': 'PlayStation 5'},
                        {'value': 'PS4', 'label': 'PlayStation 4'},
                        {'value': 'XBOX_SERIES', 'label': 'Xbox Series X|S'},
                        {'value': 'XBOX_ONE', 'label': 'Xbox One'},
                        {'value': 'SWITCH', 'label': 'Nintendo Switch'},
                    ],
                    'rank_choices': [
                        {'value': 'Bronze_1', 'label': 'Bronze I', 'tier': 1},
                        {'value': 'Bronze_2', 'label': 'Bronze II', 'tier': 2},
                        {'value': 'Bronze_3', 'label': 'Bronze III', 'tier': 3},
                        {'value': 'Silver_1', 'label': 'Silver I', 'tier': 4},
                        {'value': 'Silver_2', 'label': 'Silver II', 'tier': 5},
                        {'value': 'Silver_3', 'label': 'Silver III', 'tier': 6},
                        {'value': 'Gold_1', 'label': 'Gold I', 'tier': 7},
                        {'value': 'Gold_2', 'label': 'Gold II', 'tier': 8},
                        {'value': 'Gold_3', 'label': 'Gold III', 'tier': 9},
                        {'value': 'Platinum_1', 'label': 'Platinum I', 'tier': 10},
                        {'value': 'Platinum_2', 'label': 'Platinum II', 'tier': 11},
                        {'value': 'Platinum_3', 'label': 'Platinum III', 'tier': 12},
                        {'value': 'Diamond_1', 'label': 'Diamond I', 'tier': 13},
                        {'value': 'Diamond_2', 'label': 'Diamond II', 'tier': 14},
                        {'value': 'Diamond_3', 'label': 'Diamond III', 'tier': 15},
                        {'value': 'Champion_1', 'label': 'Champion I', 'tier': 16},
                        {'value': 'Champion_2', 'label': 'Champion II', 'tier': 17},
                        {'value': 'Champion_3', 'label': 'Champion III', 'tier': 18},
                        {'value': 'Grand_Champion_1', 'label': 'Grand Champion I', 'tier': 19},
                        {'value': 'Grand_Champion_2', 'label': 'Grand Champion II', 'tier': 20},
                        {'value': 'Grand_Champion_3', 'label': 'Grand Champion III', 'tier': 21},
                        {'value': 'Supersonic_Legend', 'label': 'Supersonic Legend', 'tier': 22},
                    ],
                    'mode_choices': [
                        {'value': '1v1', 'label': '1v1 Duel'},
                        {'value': '2v2', 'label': '2v2 Doubles'},
                        {'value': '3v3', 'label': '3v3 Standard'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO3', 'BO5', 'BO7'],
                    'default_match_format': 'BO5',
                    'default_scoring_type': 'GOALS',
                    'default_tiebreakers': ['head_to_head', 'goal_difference'],
                    'default_match_duration_minutes': 10,
                }
            },

            'r6siege': {
                'name': 'Rainbow Six Siege',
                'display_name': 'Tom Clancy\'s Rainbow Six® Siege',
                'short_code': 'R6',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC', 'Console'],
                'primary_color': '#1f8fff',
                'secondary_color': '#0a0e27',
                'accent_color': '#f59e0b',
                'description': 'Tactical 5v5 FPS with destructible environments. Six Invitational 2025 featured the world\'s best tactical teams in high-stakes competition.',
                'developer': 'Ubisoft Montreal',
                'publisher': 'Ubisoft',
                'official_website': 'https://rainbow6.com',
                'release_date': date(2015, 12, 1),
                'is_featured': True,
                'roster': {
                    'min_team_size': 5,
                    'max_team_size': 5,
                    'min_roster_size': 5,
                    'max_roster_size': 10,
                    'min_substitutes': 0,
                    'max_substitutes': 5,
                    'has_roles': True,
                    'has_regions': True,
                    'available_regions': [
                        {'code': 'NA', 'name': 'North America'},
                        {'code': 'LATAM', 'name': 'Latin America'},
                        {'code': 'EU', 'name': 'Europe'},
                        {'code': 'APAC', 'name': 'Asia-Pacific'},
                    ]
                },
                'roles': [
                    {'role_name': 'Entry Fragger', 'role_code': 'ENTRY', 'icon': '⚔️', 'color': '#ff4654', 'order': 1, 'description': 'First in, aggressive plays'},
                    {'role_name': 'Support', 'role_code': 'SUP', 'icon': '🛡️', 'color': '#10b981', 'order': 2, 'description': 'Utility and intel'},
                    {'role_name': 'Flex', 'role_code': 'FLEX', 'icon': '🔄', 'color': '#7c3aed', 'order': 3, 'description': 'Adaptable roles'},
                    {'role_name': 'Hard Breach', 'role_code': 'BREACH', 'icon': '💥', 'color': '#f59e0b', 'order': 4, 'description': 'Wall destruction'},
                    {'role_name': 'IGL', 'role_code': 'IGL', 'icon': '🧠', 'color': '#3b82f6', 'order': 5, 'description': 'In-game leader'},
                ],
                'identity_fields': [
                    {'field_name': 'uplay_id', 'display_name': 'Ubisoft Connect ID', 'field_type': 'TEXT', 'is_required': True, 'is_immutable': True, 'placeholder': 'YourUplayID', 'help_text': 'Your Ubisoft Connect username', 'max_length': 64, 'order': 1},
                    {'field_name': 'ign', 'display_name': 'In-Game Name', 'field_type': 'TEXT', 'is_required': False, 'placeholder': 'PlayerName', 'max_length': 32, 'order': 2},
                    {'field_name': 'platform', 'display_name': 'Platform', 'field_type': 'SELECT', 'is_required': True, 'is_immutable': True, 'help_text': 'Your gaming platform', 'order': 3},
                    {'field_name': 'region', 'display_name': 'Region', 'field_type': 'SELECT', 'is_required': True, 'help_text': 'Your server region', 'order': 4},
                    {'field_name': 'rank', 'display_name': 'Current Rank', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Current ranked season rank (Year 9)', 'order': 5},
                    {'field_name': 'role', 'display_name': 'Main Role', 'field_type': 'SELECT', 'is_required': False, 'help_text': 'Primary team role', 'order': 6},
                ],
                'dropdown_choices': {
                    'platform_choices': [
                        {'value': 'PC', 'label': 'PC (Ubisoft Connect)'},
                        {'value': 'PS5', 'label': 'PlayStation 5'},
                        {'value': 'PS4', 'label': 'PlayStation 4'},
                        {'value': 'XBOX_SERIES', 'label': 'Xbox Series X|S'},
                        {'value': 'XBOX_ONE', 'label': 'Xbox One'},
                    ],
                    'region_choices': [
                        {'value': 'NA', 'label': 'North America'},
                        {'value': 'LATAM', 'label': 'Latin America'},
                        {'value': 'EU', 'label': 'Europe'},
                        {'value': 'APAC', 'label': 'Asia-Pacific'},
                    ],
                    'rank_choices': [
                        {'value': 'Copper_5', 'label': 'Copper V', 'tier': 1},
                        {'value': 'Copper_4', 'label': 'Copper IV', 'tier': 2},
                        {'value': 'Copper_3', 'label': 'Copper III', 'tier': 3},
                        {'value': 'Copper_2', 'label': 'Copper II', 'tier': 4},
                        {'value': 'Copper_1', 'label': 'Copper I', 'tier': 5},
                        {'value': 'Bronze_5', 'label': 'Bronze V', 'tier': 6},
                        {'value': 'Bronze_4', 'label': 'Bronze IV', 'tier': 7},
                        {'value': 'Bronze_3', 'label': 'Bronze III', 'tier': 8},
                        {'value': 'Bronze_2', 'label': 'Bronze II', 'tier': 9},
                        {'value': 'Bronze_1', 'label': 'Bronze I', 'tier': 10},
                        {'value': 'Silver_5', 'label': 'Silver V', 'tier': 11},
                        {'value': 'Silver_4', 'label': 'Silver IV', 'tier': 12},
                        {'value': 'Silver_3', 'label': 'Silver III', 'tier': 13},
                        {'value': 'Silver_2', 'label': 'Silver II', 'tier': 14},
                        {'value': 'Silver_1', 'label': 'Silver I', 'tier': 15},
                        {'value': 'Gold_5', 'label': 'Gold V', 'tier': 16},
                        {'value': 'Gold_4', 'label': 'Gold IV', 'tier': 17},
                        {'value': 'Gold_3', 'label': 'Gold III', 'tier': 18},
                        {'value': 'Gold_2', 'label': 'Gold II', 'tier': 19},
                        {'value': 'Gold_1', 'label': 'Gold I', 'tier': 20},
                        {'value': 'Platinum_5', 'label': 'Platinum V', 'tier': 21},
                        {'value': 'Platinum_4', 'label': 'Platinum IV', 'tier': 22},
                        {'value': 'Platinum_3', 'label': 'Platinum III', 'tier': 23},
                        {'value': 'Platinum_2', 'label': 'Platinum II', 'tier': 24},
                        {'value': 'Platinum_1', 'label': 'Platinum I', 'tier': 25},
                        {'value': 'Emerald_5', 'label': 'Emerald V', 'tier': 26},
                        {'value': 'Emerald_4', 'label': 'Emerald IV', 'tier': 27},
                        {'value': 'Emerald_3', 'label': 'Emerald III', 'tier': 28},
                        {'value': 'Emerald_2', 'label': 'Emerald II', 'tier': 29},
                        {'value': 'Emerald_1', 'label': 'Emerald I', 'tier': 30},
                        {'value': 'Diamond', 'label': 'Diamond', 'tier': 31},
                        {'value': 'Champion', 'label': 'Champion', 'tier': 32},
                    ],
                    'role_choices': [
                        {'value': 'Entry_Fragger', 'label': 'Entry Fragger'},
                        {'value': 'Support', 'label': 'Support'},
                        {'value': 'Flex', 'label': 'Flex'},
                        {'value': 'Hard_Breach', 'label': 'Hard Breach'},
                        {'value': 'IGL', 'label': 'In-Game Leader'},
                    ],
                },
                'tournament_config': {
                    'available_match_formats': ['BO1', 'BO3'],
                    'default_match_format': 'BO1',
                    'default_scoring_type': 'ROUNDS',
                    'scoring_rules': {
                        'rounds_to_win': 7,
                        'max_rounds': 15,
                    },
                    'default_match_duration_minutes': 45,
                    'overtime_enabled': True,
                    'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                }
            },
        }

    def seed_game(self, game_slug, game_data, force=False):
        """Seed a single game with all related configurations."""
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"Processing: {game_data['display_name']}")
        self.stdout.write(f"{'='*70}")

        # Create or update Game
        game, created = Game.objects.update_or_create(
            slug=game_slug,
            defaults={
                'name': game_data['name'],
                'display_name': game_data['display_name'],
                'short_code': game_data['short_code'],
                'category': game_data['category'],
                'game_type': game_data['game_type'],
                'platforms': game_data['platforms'],
                'primary_color': game_data['primary_color'],
                'secondary_color': game_data['secondary_color'],
                'accent_color': game_data.get('accent_color'),
                'description': game_data['description'],
                'developer': game_data['developer'],
                'publisher': game_data['publisher'],
                'official_website': game_data.get('official_website', ''),
                'release_date': game_data.get('release_date'),
                'is_active': True,
                'is_featured': game_data['is_featured'],
            }
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"✓ {action} Game: {game.display_name}"))

        # Create or update Roster Config
        if 'roster' in game_data:
            roster_data = game_data['roster']
            roster_config, r_created = GameRosterConfig.objects.update_or_create(
                game=game,
                defaults={
                    'min_team_size': roster_data.get('min_team_size', 5),
                    'max_team_size': roster_data.get('max_team_size', 5),
                    'min_roster_size': roster_data.get('min_roster_size', 5),
                    'max_roster_size': roster_data.get('max_roster_size', 10),
                    'min_substitutes': roster_data.get('min_substitutes', 0),
                    'max_substitutes': roster_data.get('max_substitutes', 5),
                    'allow_coaches': roster_data.get('allow_coaches', True),
                    'max_coaches': roster_data.get('max_coaches', 2),
                    'allow_analysts': roster_data.get('allow_analysts', True),
                    'max_analysts': roster_data.get('max_analysts', 1),
                    'allow_managers': roster_data.get('allow_managers', True),
                    'max_managers': roster_data.get('max_managers', 2),
                    'has_roles': roster_data.get('has_roles', False),
                    'require_unique_roles': roster_data.get('require_unique_roles', False),
                    'allow_multi_role': roster_data.get('allow_multi_role', True),
                    'has_regions': roster_data.get('has_regions', False),
                    'available_regions': roster_data.get('available_regions', []),
                }
            )
            r_action = "Created" if r_created else "Updated"
            self.stdout.write(f"✓ {r_action} Roster Config")

        # Create or update Roles
        if 'roles' in game_data:
            for role_data in game_data['roles']:
                role, role_created = GameRole.objects.update_or_create(
                    game=game,
                    role_name=role_data['role_name'],
                    defaults={
                        'role_code': role_data['role_code'],
                        'description': role_data.get('description', ''),
                        'icon': role_data.get('icon', ''),
                        'color': role_data.get('color', '#7c3aed'),
                        'order': role_data['order'],
                        'is_competitive': True,
                        'is_active': True,
                    }
                )
                action = "Created" if role_created else "Updated"
                self.stdout.write(f"  ✓ {action} Role: {role.role_name}")

        # Create or update Player Identity Config(s)
        if 'identity_fields' in game_data:
            # New format: array of identity fields
            canonical_field_names = set()
            for field_data in game_data['identity_fields']:
                canonical_field_names.add(field_data['field_name'])
                identity, id_created = GamePlayerIdentityConfig.objects.update_or_create(
                    game=game,
                    field_name=field_data['field_name'],
                    defaults={
                        'display_name': field_data['display_name'],
                        'field_type': field_data.get('field_type', 'TEXT'),
                        'is_required': field_data.get('is_required', True),
                        'is_immutable': field_data.get('is_immutable', False),
                        'validation_regex': field_data.get('validation_regex', ''),
                        'validation_error_message': field_data.get('validation_error_message', ''),
                        'min_length': field_data.get('min_length'),
                        'max_length': field_data.get('max_length'),
                        'placeholder': field_data.get('placeholder', ''),
                        'help_text': field_data.get('help_text', ''),
                        'order': field_data.get('order', 1),
                    }
                )
                id_action = "Created" if id_created else "Updated"
                self.stdout.write(f"  ✓ {id_action} Identity Field: {identity.display_name}")
            
            # Delete stale fields not in canonical list
            stale_fields = GamePlayerIdentityConfig.objects.filter(game=game).exclude(field_name__in=canonical_field_names)
            stale_count = stale_fields.count()
            if stale_count > 0:
                stale_fields.delete()
                self.stdout.write(f"  ✓ Deleted {stale_count} stale identity field(s)")
        elif 'identity' in game_data:
            # Old format: single identity field (backward compatibility)
            identity_data = game_data['identity']
            identity, id_created = GamePlayerIdentityConfig.objects.update_or_create(
                game=game,
                field_name=identity_data['field_name'],
                defaults={
                    'display_name': identity_data['display_name'],
                    'field_type': identity_data.get('field_type', 'TEXT'),
                    'is_required': identity_data.get('is_required', True),
                    'is_immutable': identity_data.get('is_immutable', False),
                    'validation_regex': identity_data.get('validation_regex', ''),
                    'validation_error_message': identity_data.get('validation_error_message', ''),
                    'min_length': identity_data.get('min_length'),
                    'max_length': identity_data.get('max_length'),
                    'placeholder': identity_data.get('placeholder', ''),
                    'help_text': identity_data.get('help_text', ''),
                    'order': 1,
                }
            )
            id_action = "Created" if id_created else "Updated"
            self.stdout.write(f"✓ {id_action} Player Identity: {identity.display_name}")

        # Create or update GamePassportSchema (dropdown options)
        if 'dropdown_choices' in game_data:
            choices_data = game_data['dropdown_choices']
            schema, schema_created = GamePassportSchema.objects.update_or_create(
                game=game,
                defaults={
                    'region_choices': choices_data.get('region_choices', []),
                    'rank_choices': choices_data.get('rank_choices', []),
                    'role_choices': choices_data.get('role_choices', []),
                    'platform_choices': choices_data.get('platform_choices', []),
                    'server_choices': choices_data.get('server_choices', []),
                    'mode_choices': choices_data.get('mode_choices', []),
                    'premier_rating_choices': choices_data.get('premier_rating_choices', []),
                    'division_choices': choices_data.get('division_choices', []),
                }
            )
            schema_action = "Created" if schema_created else "Updated"
            choice_types = [k.replace('_choices', '') for k in choices_data.keys()]
            self.stdout.write(f"✓ {schema_action} GamePassportSchema ({', '.join(choice_types)} options)")

        # Create or update Tournament Config
        if 'tournament_config' in game_data:
            tc_data = game_data['tournament_config']
            tournament_config, tc_created = GameTournamentConfig.objects.update_or_create(
                game=game,
                defaults={
                    'available_match_formats': tc_data.get('available_match_formats', ['BO1', 'BO3']),
                    'default_match_format': tc_data.get('default_match_format', 'BO1'),
                    'default_scoring_type': tc_data.get('default_scoring_type', 'WIN_LOSS'),
                    'scoring_rules': tc_data.get('scoring_rules', {}),
                    'default_tiebreakers': tc_data.get('default_tiebreakers', []),
                    'supports_single_elimination': tc_data.get('supports_single_elimination', True),
                    'supports_double_elimination': tc_data.get('supports_double_elimination', True),
                    'supports_round_robin': tc_data.get('supports_round_robin', True),
                    'supports_swiss': tc_data.get('supports_swiss', False),
                    'supports_group_stage': tc_data.get('supports_group_stage', True),
                    'default_match_duration_minutes': tc_data.get('default_match_duration_minutes', 60),
                    'allow_draws': tc_data.get('allow_draws', False),
                    'overtime_enabled': tc_data.get('overtime_enabled', False),
                    'require_check_in': tc_data.get('require_check_in', True),
                    'check_in_window_minutes': tc_data.get('check_in_window_minutes', 30),
                }
            )
            tc_action = "Created" if tc_created else "Updated"
            self.stdout.write(f"✓ {tc_action} Tournament Config")

        self.stdout.write(self.style.SUCCESS(f"✓ Completed: {game.display_name}"))
        return game
