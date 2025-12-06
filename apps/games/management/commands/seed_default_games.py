"""
Management command to seed default game configurations.
Idempotent - safe to run multiple times.

Usage:
    python manage.py seed_default_games
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole
)


class Command(BaseCommand):
    help = 'Seed default game configurations for 9 supported games (December 2025 specs)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Seeding default games...'))
        
        with transaction.atomic():
            self._seed_valorant()
            self._seed_cs2()
            self._seed_pubg_mobile()
            self._seed_free_fire()
            self._seed_mobile_legends()
            self._seed_call_of_duty_mobile()
            self._seed_efootball()
            self._seed_fc_mobile()
            self._seed_fifa()
        
        self.stdout.write(self.style.SUCCESS('[SUCCESS] All 9 games seeded with configs and roles'))

    def _seed_valorant(self):
        """Valorant - 5v5 Tactical FPS"""
        game, created = Game.objects.update_or_create(
            slug='valorant',
            defaults={
                'name': 'Valorant',
                'display_name': 'VALORANT',
                'short_code': 'VAL',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC'],
                'developer': 'Riot Games',
                'publisher': 'Riot Games',
                'description': '5v5 character-based tactical FPS',
                'primary_color': '#ff4655',
                'secondary_color': '#0f1923',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 5,
                'max_team_size': 5,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 5,
                'max_roster_size': 7,
                'has_roles': True,
                'require_unique_roles': False,
                'allow_multi_role': True,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='riot_id',
            defaults={
                'display_name': 'Riot ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'PlayerName#TAG',
                'help_text': 'Your Riot ID in format: Name#TAG (e.g., Faker#KR1)',
                'validation_regex': r'^.{3,16}#[A-Z0-9]{3,5}$',
                'validation_error_message': 'Riot ID must be in format: Name#TAG',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'ROUNDS',
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'scoring_rules': {
                    'tiebreaker_fields': [
                        {'field': 'round_difference', 'order': 'desc'},
                        {'field': 'rounds_won', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 45,
                'allow_draws': False,
                'overtime_enabled': True,
            }
        )
        
        roles = [
            ('Duelist', 'DUE', 'DUE', '#ff4655', 0),
            ('Controller', 'CTRL', 'CTRL', '#3b82f6', 1),
            ('Initiator', 'INIT', 'INIT', '#f59e0b', 2),
            ('Sentinel', 'SENT', 'SENT', '#10b981', 3),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_cs2(self):
        """Counter-Strike 2 - 5v5 Tactical FPS"""
        game, created = Game.objects.update_or_create(
            slug='cs2',
            defaults={
                'name': 'Counter-Strike 2',
                'display_name': 'Counter-Strike 2',
                'short_code': 'CS2',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC'],
                'developer': 'Valve Corporation',
                'publisher': 'Valve Corporation',
                'description': '5v5 tactical FPS - successor to CS:GO',
                'primary_color': '#f79e1b',
                'secondary_color': '#191919',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 5,
                'max_team_size': 5,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 5,
                'max_roster_size': 7,
                'has_roles': True,
                'require_unique_roles': False,
                'allow_multi_role': True,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='steam_id',
            defaults={
                'display_name': 'Steam ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'Steam ID or Friend Code',
                'help_text': 'Your Steam ID or Friend Code',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'ROUNDS',
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'scoring_rules': {
                    'tiebreaker_fields': [
                        {'field': 'round_difference', 'order': 'desc'},
                        {'field': 'rounds_won', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 50,
                'allow_draws': False,
                'overtime_enabled': True,
            }
        )
        
        roles = [
            ('In-Game Leader (IGL)', 'IGL', 'IGL', '#f79e1b', 0),
            ('AWPer', 'AWP', 'AWP', '#dc2626', 1),
            ('Entry Fragger', 'ENTRY', 'ENTRY', '#f97316', 2),
            ('Rifler', 'RIFLE', 'RIFLE', '#3b82f6', 3),
            ('Support', 'SUPP', 'SUPP', '#10b981', 4),
            ('Lurker', 'LURK', 'LURK', '#8b5cf6', 5),
            ('Anchor', 'ANCHOR', 'ANCHOR', '#06b6d4', 6),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_pubg_mobile(self):
        """PUBG Mobile - 4-player squad Battle Royale"""
        game, created = Game.objects.update_or_create(
            slug='pubg-mobile',
            defaults={
                'name': 'PUBG Mobile',
                'display_name': 'PUBG MOBILE',
                'short_code': 'PUBGM',
                'category': 'BR',
                'game_type': 'BATTLE_ROYALE',
                'platforms': ['Mobile'],
                'developer': 'Tencent Games',
                'publisher': 'Krafton',
                'description': '4v4 squad-based Battle Royale',
                'primary_color': '#f7931e',
                'secondary_color': '#1a1a1a',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 4,
                'max_team_size': 4,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 4,
                'max_roster_size': 6,
                'has_roles': True,
                'require_unique_roles': False,
                'allow_multi_role': True,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'PUBG Mobile ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': '1234567890',
                'help_text': 'Your PUBG Mobile Player ID (numeric)',
                'validation_regex': r'^\d{8,12}$',
                'validation_error_message': 'PUBG Mobile ID must be 8-12 digits',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['SINGLE_MATCH', 'BO3', 'BO5'],
                'default_match_format': 'SINGLE_MATCH',
                'default_scoring_type': 'PLACEMENT_KILLS',
                'default_tiebreakers': ['total_kills', 'avg_placement'],
                'scoring_rules': {
                    'placement_points': {
                        '1': 10, '2': 6, '3': 5, '4': 4, '5': 3,
                        '6': 2, '7': 2, '8': 1, '9': 1, '10': 1
                    },
                    'kill_points': 1,
                    'tiebreaker_fields': [
                        {'field': 'total_kills', 'order': 'desc'},
                        {'field': 'average_placement', 'order': 'asc'}
                    ]
                },
                'default_match_duration_minutes': 35,
                'allow_draws': True,
                'overtime_enabled': False,
            }
        )
        
        roles = [
            ('IGL', 'IGL', 'IGL', '#f7931e', 0),
            ('Assaulter', 'ASL', 'ASL', '#dc2626', 1),
            ('Support', 'SUPP', 'SUPP', '#10b981', 2),
            ('Sniper', 'SNP', 'SNP', '#3b82f6', 3),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_free_fire(self):
        """Free Fire - 4-player squad Battle Royale"""
        game, created = Game.objects.update_or_create(
            slug='free-fire',
            defaults={
                'name': 'Free Fire',
                'display_name': 'Free Fire',
                'short_code': 'FF',
                'category': 'BR',
                'game_type': 'BATTLE_ROYALE',
                'platforms': ['Mobile'],
                'developer': '111 Dots Studio',
                'publisher': 'Garena',
                'description': '4v4 squad-based Battle Royale',
                'primary_color': '#ff3b3b',
                'secondary_color': '#0d0d0d',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 4,
                'max_team_size': 4,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 4,
                'max_roster_size': 6,
                'has_roles': True,
                'require_unique_roles': False,
                'allow_multi_role': True,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'Free Fire ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': '123456789',
                'help_text': 'Your Free Fire Player ID (numeric)',
                'validation_regex': r'^\d{8,12}$',
                'validation_error_message': 'Free Fire ID must be 8-12 digits',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['SINGLE_MATCH', 'BO3', 'BO5'],
                'default_match_format': 'SINGLE_MATCH',
                'default_scoring_type': 'PLACEMENT_KILLS',
                'default_tiebreakers': ['total_kills', 'avg_placement'],
                'scoring_rules': {
                    'placement_points': {
                        '1': 12, '2': 9, '3': 7, '4': 5, '5': 4,
                        '6': 3, '7': 2, '8': 2, '9': 1, '10': 1
                    },
                    'kill_points': 1,
                    'tiebreaker_fields': [
                        {'field': 'total_kills', 'order': 'desc'},
                        {'field': 'average_placement', 'order': 'asc'}
                    ]
                },
                'default_match_duration_minutes': 25,
                'allow_draws': True,
                'overtime_enabled': False,
            }
        )
        
        roles = [
            ('IGL', 'IGL', 'IGL', '#ff3b3b', 0),
            ('Rusher', 'RUSH', 'RUSH', '#dc2626', 1),
            ('Support', 'SUPP', 'SUPP', '#10b981', 2),
            ('Sniper', 'SNP', 'SNP', '#3b82f6', 3),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_mobile_legends(self):
        """Mobile Legends: Bang Bang - 5v5 MOBA"""
        game, created = Game.objects.update_or_create(
            slug='mobile-legends',
            defaults={
                'name': 'Mobile Legends: Bang Bang',
                'display_name': 'Mobile Legends',
                'short_code': 'MLBB',
                'category': 'MOBA',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['Mobile'],
                'developer': 'Moonton',
                'publisher': 'Moonton',
                'description': '5v5 MOBA with fast-paced action',
                'primary_color': '#4169e1',
                'secondary_color': '#191970',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 5,
                'max_team_size': 5,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 5,
                'max_roster_size': 7,
                'has_roles': True,
                'require_unique_roles': True,
                'allow_multi_role': False,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'MLBB ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': '123456789 (1234)',
                'help_text': 'Your Mobile Legends ID and Server ID',
                'validation_regex': r'^\d{6,12}\s*\(\d{4}\)$',
                'validation_error_message': 'Format: Player ID (Server ID)',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5', 'BO7'],
                'default_match_format': 'BO5',
                'default_scoring_type': 'WINS',
                'default_tiebreakers': ['head_to_head', 'game_time'],
                'scoring_rules': {
                    'tiebreaker_fields': [
                        {'field': 'head_to_head_wins', 'order': 'desc'},
                        {'field': 'total_game_time', 'order': 'asc'}
                    ]
                },
                'default_match_duration_minutes': 25,
                'allow_draws': False,
                'overtime_enabled': False,
            }
        )
        
        roles = [
            ('Gold Laner', 'GOLD', 'GOLD', '#f59e0b', 0),
            ('Exp Laner', 'EXP', 'EXP', '#dc2626', 1),
            ('Mid Laner', 'MID', 'MID', '#8b5cf6', 2),
            ('Jungler', 'JUNG', 'JUNG', '#10b981', 3),
            ('Roamer', 'ROAM', 'ROAM', '#3b82f6', 4),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_call_of_duty_mobile(self):
        """Call of Duty: Mobile - 5v5 Mobile FPS"""
        game, created = Game.objects.update_or_create(
            slug='call-of-duty-mobile',
            defaults={
                'name': 'Call of Duty: Mobile',
                'display_name': 'COD Mobile',
                'short_code': 'CODM',
                'category': 'FPS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['Mobile'],
                'developer': 'TiMi Studio Group',
                'publisher': 'Activision',
                'description': '5v5 fast-paced mobile FPS',
                'primary_color': '#ff6b00',
                'secondary_color': '#0a0a0a',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 5,
                'max_team_size': 5,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 5,
                'max_roster_size': 7,
                'has_roles': True,
                'require_unique_roles': False,
                'allow_multi_role': True,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'COD Mobile ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'PlayerName or UID',
                'help_text': 'Your Call of Duty Mobile username or UID',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO5',
                'default_scoring_type': 'ROUNDS',
                'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
                'scoring_rules': {
                    'tiebreaker_fields': [
                        {'field': 'round_difference', 'order': 'desc'},
                        {'field': 'rounds_won', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 30,
                'allow_draws': False,
                'overtime_enabled': True,
            }
        )
        
        roles = [
            ('Slayer', 'SLAY', 'SLAY', '#ff6b00', 0),
            ('Objective', 'OBJ', 'OBJ', '#10b981', 1),
            ('Support', 'SUPP', 'SUPP', '#3b82f6', 2),
            ('Anchor', 'ANCHOR', 'ANCHOR', '#8b5cf6', 3),
            ('Flex', 'FLEX', 'FLEX', '#f59e0b', 4),
        ]
        for role_name, code, icon, color, order in roles:
            GameRole.objects.update_or_create(
                game=game,
                role_name=role_name,
                defaults={
                    'role_code': code,
                    'icon': icon,
                    'color': color,
                    'order': order,
                    'is_competitive': True,
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_efootball(self):
        """eFootball - 11v11 Football Simulation"""
        game, created = Game.objects.update_or_create(
            slug='efootball',
            defaults={
                'name': 'eFootball',
                'display_name': 'eFootball',
                'short_code': 'EFB',
                'category': 'SPORTS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC', 'Console', 'Mobile'],
                'developer': 'Konami',
                'publisher': 'Konami',
                'description': '11v11 football simulation (formerly PES)',
                'primary_color': '#00a0e9',
                'secondary_color': '#002e5d',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 1,
                'max_team_size': 1,
                'min_substitutes': 0,
                'max_substitutes': 1,
                'min_roster_size': 1,
                'max_roster_size': 2,
                'has_roles': False,
                'require_unique_roles': False,
                'allow_multi_role': False,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'eFootball ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'Platform Username',
                'help_text': 'Your eFootball username on your platform',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'AGGREGATE',
                'default_tiebreakers': ['away_goals', 'extra_time', 'penalties'],
                'scoring_rules': {
                    'aggregate_scoring': True,
                    'away_goals_rule': True,
                    'tiebreaker_fields': [
                        {'field': 'away_goals', 'order': 'desc'},
                        {'field': 'total_goals', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 15,
                'allow_draws': True,
                'overtime_enabled': True,
            }
        )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_fc_mobile(self):
        """FC Mobile (EA Sports FC Mobile) - 11v11 Football"""
        game, created = Game.objects.update_or_create(
            slug='fc-mobile',
            defaults={
                'name': 'FC Mobile',
                'display_name': 'FC Mobile',
                'short_code': 'FCM',
                'category': 'SPORTS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['Mobile'],
                'developer': 'EA Sports',
                'publisher': 'Electronic Arts',
                'description': '11v11 football simulation for mobile',
                'primary_color': '#00d639',
                'secondary_color': '#001e28',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 1,
                'max_team_size': 1,
                'min_substitutes': 0,
                'max_substitutes': 1,
                'min_roster_size': 1,
                'max_roster_size': 2,
                'has_roles': False,
                'require_unique_roles': False,
                'allow_multi_role': False,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='game_id',
            defaults={
                'display_name': 'FC Mobile ID',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'EA Account Username',
                'help_text': 'Your EA Account username',
                'order': 0,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'AGGREGATE',
                'default_tiebreakers': ['away_goals', 'extra_time', 'penalties'],
                'scoring_rules': {
                    'aggregate_scoring': True,
                    'away_goals_rule': True,
                    'tiebreaker_fields': [
                        {'field': 'away_goals', 'order': 'desc'},
                        {'field': 'total_goals', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 12,
                'allow_draws': True,
                'overtime_enabled': True,
            }
        )
        
        self.stdout.write(f'  OK {game.display_name}')

    def _seed_fifa(self):
        """FIFA (EA Sports FC) - 11v11 Football Simulation"""
        game, created = Game.objects.update_or_create(
            slug='fifa',
            defaults={
                'name': 'FIFA',
                'display_name': 'EA Sports FC',
                'short_code': 'FC',
                'category': 'SPORTS',
                'game_type': 'TEAM_VS_TEAM',
                'platforms': ['PC', 'Console'],
                'developer': 'EA Sports',
                'publisher': 'Electronic Arts',
                'description': '11v11 football simulation (EA Sports FC 25)',
                'primary_color': '#00f86c',
                'secondary_color': '#001e28',
                'is_active': True,
            }
        )
        
        GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': 1,
                'max_team_size': 1,
                'min_substitutes': 0,
                'max_substitutes': 1,
                'min_roster_size': 1,
                'max_roster_size': 2,
                'has_roles': False,
                'require_unique_roles': False,
                'allow_multi_role': False,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='ea_account',
            defaults={
                'display_name': 'EA Account',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'EA Account Username',
                'help_text': 'Your EA Account username',
                'order': 0,
            }
        )
        
        GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name='platform',
            defaults={
                'display_name': 'Platform',
                'field_type': 'TEXT',
                'is_required': True,
                'placeholder': 'PlayStation/Xbox/PC',
                'help_text': 'Your gaming platform (PlayStation, Xbox, or PC)',
                'order': 1,
            }
        )
        
        GameTournamentConfig.objects.update_or_create(
            game=game,
            defaults={
                'available_match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'default_scoring_type': 'AGGREGATE',
                'default_tiebreakers': ['away_goals', 'extra_time', 'penalties'],
                'scoring_rules': {
                    'aggregate_scoring': True,
                    'away_goals_rule': True,
                    'tiebreaker_fields': [
                        {'field': 'away_goals', 'order': 'desc'},
                        {'field': 'total_goals', 'order': 'desc'}
                    ]
                },
                'default_match_duration_minutes': 15,
                'allow_draws': True,
                'overtime_enabled': True,
            }
        )
        
        self.stdout.write(f'  OK {game.display_name}')
