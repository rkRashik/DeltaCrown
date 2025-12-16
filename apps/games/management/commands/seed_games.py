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
                'identity': {
                    'field_name': 'riot_id',
                    'display_name': 'Riot ID',
                    'field_type': 'TEXT',
                    'placeholder': 'PlayerName#TAG',
                    'validation_regex': r'^.{3,16}#[a-zA-Z0-9]{3,5}$',
                    'help_text': 'Your Riot ID with tagline (e.g., TenZ#1234)',
                    'is_required': True,
                    'is_immutable': False,
                    'min_length': 5,
                    'max_length': 24,
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
                'identity': {
                    'field_name': 'steam_id',
                    'display_name': 'Steam ID',
                    'field_type': 'TEXT',
                    'placeholder': '76561198000000000',
                    'validation_regex': r'^765\d{14}$',
                    'help_text': 'Your 17-digit Steam ID64',
                    'is_required': True,
                    'is_immutable': False,
                    'min_length': 17,
                    'max_length': 17,
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
                'identity': {
                    'field_name': 'steam_id',
                    'display_name': 'Steam ID',
                    'field_type': 'TEXT',
                    'placeholder': '76561198000000000',
                    'validation_regex': r'^765\d{14}$',
                    'help_text': 'Your 17-digit Steam ID64',
                    'is_required': True,
                    'is_immutable': False,
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
                'identity': {
                    'field_name': 'ea_id',
                    'display_name': 'EA ID',
                    'field_type': 'TEXT',
                    'placeholder': 'YourEAID',
                    'help_text': 'Your EA Account ID',
                    'is_required': True,
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
                'identity': {
                    'field_name': 'efootball_id',
                    'display_name': 'eFootball ID',
                    'field_type': 'TEXT',
                    'placeholder': 'PlayerID',
                    'help_text': 'Your eFootball user ID',
                    'is_required': True,
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
                'identity': {
                    'field_name': 'pubgm_id',
                    'display_name': 'Character ID',
                    'field_type': 'NUMBER',
                    'placeholder': '5123456789',
                    'help_text': 'Your PUBG Mobile Character ID (found in profile)',
                    'is_required': True,
                    'min_length': 9,
                    'max_length': 12,
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
                'identity': {
                    'field_name': 'mlbb_id',
                    'display_name': 'Game ID',
                    'field_type': 'NUMBER',
                    'placeholder': '123456789',
                    'help_text': 'Your MLBB Game ID (found in profile)',
                    'is_required': True,
                    'min_length': 8,
                    'max_length': 12,
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
                'identity': {
                    'field_name': 'freefire_id',
                    'display_name': 'Player ID',
                    'field_type': 'NUMBER',
                    'placeholder': '1234567890',
                    'help_text': 'Your Free Fire Player ID',
                    'is_required': True,
                    'min_length': 9,
                    'max_length': 12,
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
                'identity': {
                    'field_name': 'codm_uid',
                    'display_name': 'UID',
                    'field_type': 'NUMBER',
                    'placeholder': '6000000000',
                    'help_text': 'Your COD Mobile UID (found in profile)',
                    'is_required': True,
                    'min_length': 10,
                    'max_length': 12,
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
                'identity': {
                    'field_name': 'epic_id',
                    'display_name': 'Epic Games ID',
                    'field_type': 'TEXT',
                    'placeholder': 'YourEpicID',
                    'help_text': 'Your Epic Games account name',
                    'is_required': True,
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
                'identity': {
                    'field_name': 'ubisoft_id',
                    'display_name': 'Ubisoft Username',
                    'field_type': 'TEXT',
                    'placeholder': 'YourUbisoftName',
                    'help_text': 'Your Ubisoft Connect username',
                    'is_required': True,
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

        # Create or update Player Identity Config
        if 'identity' in game_data:
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
