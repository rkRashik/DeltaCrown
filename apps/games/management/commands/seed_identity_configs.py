"""
Management command to seed/update comprehensive Game Player Identity Configs.

This command ensures ALL active games have complete identity field configurations
with proper region/rank/role options. Idempotent - safe to run multiple times.

Usage:
    python manage.py seed_identity_configs
    python manage.py seed_identity_configs --game valorant
    python manage.py seed_identity_configs --force  # Overwrite existing
"""

from django.core.management.base import BaseCommand
from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GamePassportSchema


class Command(BaseCommand):
    help = 'Seed comprehensive identity configs for all games (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--game',
            type=str,
            help='Seed only specific game slug (e.g., valorant)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing configs'
        )

    def handle(self, *args, **options):
        game_slug = options.get('game')
        force = options.get('force', False)

        if game_slug:
            try:
                game = Game.objects.get(slug=game_slug, is_active=True)
                self.seed_game(game, force)
            except Game.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'[ERROR] Game not found: {game_slug}'))
                return
        else:
            games = Game.objects.filter(is_active=True)
            self.stdout.write(f'\n[SEED] Seeding identity configs for {games.count()} active games...\n')
            for game in games:
                self.seed_game(game, force)
        
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Identity config seeding complete!'))

    def seed_game(self, game, force=False):
        """Seed identity configs for a single game"""
        self.stdout.write(f'\n[GAME] {game.display_name} ({game.slug})')
        
        # Get game-specific schema
        schema = self.get_game_schema(game.slug)
        
        if not schema:
            self.stdout.write(self.style.WARNING(f'  [WARN] No schema defined for {game.slug} - skipping'))
            return
        
        # Seed identity fields
        for order, field_config in enumerate(schema['fields'], start=1):
            field_name = field_config['field_name']
            
            # Check if exists
            existing = GamePlayerIdentityConfig.objects.filter(
                game=game,
                field_name=field_name
            ).first()
            
            if existing and not force:
                self.stdout.write(f'  [OK] {field_name} already exists - skipping')
                continue
            
            # Create or update
            identity_config, created = GamePlayerIdentityConfig.objects.update_or_create(
                game=game,
                field_name=field_name,
                defaults={
                    'display_name': field_config['display_name'],
                    'field_type': field_config.get('field_type', 'TEXT'),
                    'is_required': field_config.get('is_required', False),
                    'is_immutable': field_config.get('is_immutable', False),
                    'validation_regex': field_config.get('validation_regex', ''),
                    'validation_error_message': field_config.get('validation_error_message', ''),
                    'min_length': field_config.get('min_length'),
                    'max_length': field_config.get('max_length'),
                    'placeholder': field_config.get('placeholder', ''),
                    'help_text': field_config.get('help_text', ''),
                    'order': order
                }
            )
            action = '[NEW]' if created else '[UPD]'
            self.stdout.write(f'  {action}: {identity_config.display_name}')
        
        # Seed GamePassportSchema for select field options
        if 'region_choices' in schema or 'rank_choices' in schema or 'role_choices' in schema:
            passport_schema, created = GamePassportSchema.objects.get_or_create(game=game)
            
            if 'region_choices' in schema:
                passport_schema.region_choices = schema['region_choices']
            if 'rank_choices' in schema:
                passport_schema.rank_choices = schema['rank_choices']
            if 'role_choices' in schema:
                passport_schema.role_choices = schema['role_choices']
            
            passport_schema.save()
            self.stdout.write(f'  [OK] Updated GamePassportSchema with dropdown options')

    def get_game_schema(self, slug):
        """
        Get comprehensive schema for each game.
        
        Schema includes:
        - Core identity fields (game-specific IDs)
        - IGN field
        - Competitive metadata (region, rank, role where applicable)
        - Platform (for cross-platform games)
        """
        
        schemas = {
            'valorant': {
                'fields': [
                    {
                        'field_name': 'riot_id',
                        'display_name': 'Riot ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^[a-zA-Z0-9 ]+#[a-zA-Z0-9]+$',
                        'validation_error_message': 'Format: Username#TAG (e.g., Viper#NA1)',
                        'placeholder': 'PlayerName#NA1',
                        'help_text': 'Your full Riot ID including tagline',
                        'min_length': 3,
                        'max_length': 32
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 'Viper',
                        'help_text': 'Your display name (auto-filled from Riot ID)',
                        'max_length': 16
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Region',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': False,
                        'help_text': 'Your game server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your current competitive rank'
                    },
                    {
                        'field_name': 'peak_rank',
                        'display_name': 'Peak Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your highest competitive rank achieved'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your primary role/agent class'
                    }
                ],
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'APAC', 'label': 'Asia Pacific'},
                    {'value': 'KR', 'label': 'Korea'},
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'LATAM', 'label': 'Latin America'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'iron', 'label': 'Iron'},
                    {'value': 'bronze', 'label': 'Bronze'},
                    {'value': 'silver', 'label': 'Silver'},
                    {'value': 'gold', 'label': 'Gold'},
                    {'value': 'platinum', 'label': 'Platinum'},
                    {'value': 'diamond', 'label': 'Diamond'},
                    {'value': 'ascendant', 'label': 'Ascendant'},
                    {'value': 'immortal', 'label': 'Immortal'},
                    {'value': 'radiant', 'label': 'Radiant'}
                ],
                'role_choices': [
                    {'value': 'duelist', 'label': 'Duelist'},
                    {'value': 'initiator', 'label': 'Initiator'},
                    {'value': 'controller', 'label': 'Controller'},
                    {'value': 'sentinel', 'label': 'Sentinel'},
                    {'value': 'flex', 'label': 'Flex'}
                ]
            },
            
            'pubgm': {
                'fields': [
                    {
                        'field_name': 'uid',
                        'display_name': 'Character ID (UID)',
                        'field_type': 'NUMBER',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{10,12}$',
                        'validation_error_message': 'UID must be 10-12 digits',
                        'placeholder': '5123456789',
                        'help_text': 'Your PUBG Mobile character numeric ID',
                        'min_length': 10,
                        'max_length': 12
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': False,
                        'placeholder': 'Mortal',
                        'help_text': 'Your PUBG Mobile display name',
                        'max_length': 16
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Server/Region',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': False,
                        'help_text': 'Your primary game server'
                    },
                    {
                        'field_name': 'tier',
                        'display_name': 'Current Tier',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your current ranked tier'
                    }
                ],
                'region_choices': [
                    {'value': 'asia', 'label': 'Asia'},
                    {'value': 'krjp', 'label': 'Korea/Japan'},
                    {'value': 'na', 'label': 'North America'},
                    {'value': 'sa', 'label': 'South America'},
                    {'value': 'eu', 'label': 'Europe'}
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze'},
                    {'value': 'silver', 'label': 'Silver'},
                    {'value': 'gold', 'label': 'Gold'},
                    {'value': 'platinum', 'label': 'Platinum'},
                    {'value': 'diamond', 'label': 'Diamond'},
                    {'value': 'crown', 'label': 'Crown'},
                    {'value': 'ace', 'label': 'Ace'},
                    {'value': 'conqueror', 'label': 'Conqueror'}
                ]
            },
            
            'efootball': {
                'fields': [
                    {
                        'field_name': 'owner_id',
                        'display_name': 'Owner ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{9}$',
                        'validation_error_message': 'Owner ID must be 9 digits',
                        'placeholder': '123456789',
                        'help_text': 'Your 9-digit eFootball Owner ID',
                        'min_length': 9,
                        'max_length': 9
                    },
                    {
                        'field_name': 'team_name',
                        'display_name': 'Team Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 'Delta FC',
                        'help_text': 'Your custom team name',
                        'max_length': 20
                    },
                    {
                        'field_name': 'platform',
                        'display_name': 'Platform',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': True,
                        'help_text': 'Your gaming platform'
                    }
                ],
                'region_choices': [
                    {'value': 'mobile', 'label': 'Mobile'},
                    {'value': 'playstation', 'label': 'PlayStation'},
                    {'value': 'xbox', 'label': 'Xbox'},
                    {'value': 'pc', 'label': 'PC/Steam'}
                ]
            },
            
            'cs2': {
                'fields': [
                    {
                        'field_name': 'steam_id',
                        'display_name': 'Steam ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{17}$|^STEAM_[0-5]:[01]:\d{1,10}$',
                        'validation_error_message': 'Must be 17-digit Steam ID or STEAM_X:Y:Z format',
                        'placeholder': '76561198000000000',
                        'help_text': 'Your Steam account ID (17 digits)',
                        'min_length': 17,
                        'max_length': 25
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 's1mple',
                        'help_text': 'Your CS2 display name',
                        'max_length': 32
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Region',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your primary matchmaking region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Premier Rating',
                        'field_type': 'NUMBER',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': '15000',
                        'help_text': 'Your CS2 Premier mode rating',
                        'max_length': 6
                    }
                ],
                'region_choices': [
                    {'value': 'na', 'label': 'North America'},
                    {'value': 'eu', 'label': 'Europe'},
                    {'value': 'asia', 'label': 'Asia'},
                    {'value': 'oceania', 'label': 'Oceania'},
                    {'value': 'sa', 'label': 'South America'}
                ]
            },
            
            'mlbb': {
                'fields': [
                    {
                        'field_name': 'user_id',
                        'display_name': 'User ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{8,12}\(\d{4}\)$',
                        'validation_error_message': 'Format: 12345678(1234)',
                        'placeholder': '12345678(1234)',
                        'help_text': 'Your MLBB User ID with server (e.g., 12345678(1234))',
                        'max_length': 20
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': False,
                        'placeholder': 'FrostDiamond',
                        'help_text': 'Your Mobile Legends display name',
                        'max_length': 16
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Server',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': False,
                        'help_text': 'Your game server'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your ranked tier'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'is_immutable': False,
                        'help_text': 'Your primary role'
                    }
                ],
                'region_choices': [
                    {'value': 'asia', 'label': 'Asia'},
                    {'value': 'sea', 'label': 'Southeast Asia'},
                    {'value': 'na', 'label': 'North America'},
                    {'value': 'latam', 'label': 'Latin America'},
                    {'value': 'eu', 'label': 'Europe'}
                ],
                'rank_choices': [
                    {'value': 'warrior', 'label': 'Warrior'},
                    {'value': 'elite', 'label': 'Elite'},
                    {'value': 'master', 'label': 'Master'},
                    {'value': 'grandmaster', 'label': 'Grandmaster'},
                    {'value': 'epic', 'label': 'Epic'},
                    {'value': 'legend', 'label': 'Legend'},
                    {'value': 'mythic', 'label': 'Mythic'},
                    {'value': 'mythical_glory', 'label': 'Mythical Glory'}
                ],
                'role_choices': [
                    {'value': 'tank', 'label': 'Tank'},
                    {'value': 'fighter', 'label': 'Fighter'},
                    {'value': 'assassin', 'label': 'Assassin'},
                    {'value': 'mage', 'label': 'Mage'},
                    {'value': 'marksman', 'label': 'Marksman'},
                    {'value': 'support', 'label': 'Support'}
                ]
            },
            
            # Remaining games with comprehensive schemas
            'freefire': self._get_br_game_schema('Free Fire', 'player_id', 'Player ID', '12345678'),
            'codm': self._get_fps_game_schema('COD Mobile', 'uid', 'UID', '1234567890'),
            'ea-fc': self._get_sports_game_schema('EA FC', 'user_id', 'User ID', '123456789'),
            'dota2': self._get_moba_game_schema('Dota 2', 'steam_id', 'Steam ID', '76561198000000000'),
            'r6siege': self._get_fps_game_schema('Rainbow Six Siege', 'uplay_id', 'Uplay ID', 'PlayerName'),
            'rocketleague': self._get_sports_game_schema('Rocket League', 'epic_id', 'Epic ID', 'PlayerName'),
        }
        
        return schemas.get(slug)
    
    def _get_br_game_schema(self, display_name, id_field, id_label, id_placeholder):
        """Generic BR game schema"""
        return {
            'fields': [
                {
                    'field_name': id_field,
                    'display_name': id_label,
                    'field_type': 'TEXT',
                    'is_required': True,
                    'is_immutable': True,
                    'placeholder': id_placeholder,
                    'help_text': f'Your {display_name} account ID',
                    'max_length': 20
                },
                {
                    'field_name': 'ign',
                    'display_name': 'In-Game Name',
                    'field_type': 'TEXT',
                    'is_required': True,
                    'is_immutable': False,
                    'placeholder': 'PlayerName',
                    'help_text': 'Your display name',
                    'max_length': 16
                },
                {
                    'field_name': 'region',
                    'display_name': 'Region/Server',
                    'field_type': 'select',
                    'is_required': True,
                    'is_immutable': False,
                    'help_text': 'Your game server'
                },
                {
                    'field_name': 'rank',
                    'display_name': 'Current Rank',
                    'field_type': 'select',
                    'is_required': False,
                    'is_immutable': False,
                    'help_text': 'Your ranked tier'
                }
            ],
            'region_choices': [
                {'value': 'na', 'label': 'North America'},
                {'value': 'eu', 'label': 'Europe'},
                {'value': 'asia', 'label': 'Asia'},
                {'value': 'latam', 'label': 'Latin America'}
            ],
            'rank_choices': [
                {'value': 'bronze', 'label': 'Bronze'},
                {'value': 'silver', 'label': 'Silver'},
                {'value': 'gold', 'label': 'Gold'},
                {'value': 'platinum', 'label': 'Platinum'},
                {'value': 'diamond', 'label': 'Diamond'},
                {'value': 'master', 'label': 'Master'},
                {'value': 'predator', 'label': 'Predator'}
            ]
        }
    
    def _get_fps_game_schema(self, display_name, id_field, id_label, id_placeholder):
        """Generic FPS game schema"""
        return self._get_br_game_schema(display_name, id_field, id_label, id_placeholder)
    
    def _get_moba_game_schema(self, display_name, id_field, id_label, id_placeholder):
        """Generic MOBA game schema"""
        schema = self._get_br_game_schema(display_name, id_field, id_label, id_placeholder)
        schema['fields'].append({
            'field_name': 'role',
            'display_name': 'Main Role',
            'field_type': 'select',
            'is_required': False,
            'is_immutable': False,
            'help_text': 'Your primary role'
        })
        schema['role_choices'] = [
            {'value': 'top', 'label': 'Top'},
            {'value': 'jungle', 'label': 'Jungle'},
            {'value': 'mid', 'label': 'Mid'},
            {'value': 'adc', 'label': 'ADC'},
            {'value': 'support', 'label': 'Support'}
        ]
        return schema
    
    def _get_sports_game_schema(self, display_name, id_field, id_label, id_placeholder):
        """Generic sports game schema"""
        return {
            'fields': [
                {
                    'field_name': id_field,
                    'display_name': id_label,
                    'field_type': 'TEXT',
                    'is_required': True,
                    'is_immutable': True,
                    'placeholder': id_placeholder,
                    'help_text': f'Your {display_name} account ID',
                    'max_length': 20
                },
                {
                    'field_name': 'team_name',
                    'display_name': 'Team Name',
                    'field_type': 'TEXT',
                    'is_required': False,
                    'is_immutable': False,
                    'placeholder': 'Delta FC',
                    'help_text': 'Your custom team name',
                    'max_length': 20
                },
                {
                    'field_name': 'platform',
                    'display_name': 'Platform',
                    'field_type': 'select',
                    'is_required': False,
                    'is_immutable': False,
                    'help_text': 'Your gaming platform'
                }
            ],
            'region_choices': [
                {'value': 'mobile', 'label': 'Mobile'},
                {'value': 'console', 'label': 'Console'},
                {'value': 'pc', 'label': 'PC'}
            ]
        }
    
    def _get_fighting_game_schema(self, display_name, id_field, id_label, id_placeholder):
        """Generic fighting game schema"""
        return {
            'fields': [
                {
                    'field_name': id_field,
                    'display_name': id_label,
                    'field_type': 'TEXT',
                    'is_required': True,
                    'is_immutable': True,
                    'placeholder': id_placeholder,
                    'help_text': f'Your {display_name} player ID',
                    'max_length': 32
                },
                {
                    'field_name': 'ign',
                    'display_name': 'In-Game Name',
                    'field_type': 'TEXT',
                    'is_required': False,
                    'is_immutable': False,
                    'placeholder': 'FighterName',
                    'help_text': 'Your display name',
                    'max_length': 16
                },
                {
                    'field_name': 'platform',
                    'display_name': 'Platform',
                    'field_type': 'select',
                    'is_required': True,
                    'is_immutable': False,
                    'help_text': 'Your gaming platform'
                },
                {
                    'field_name': 'main_character',
                    'display_name': 'Main Character',
                    'field_type': 'TEXT',
                    'is_required': False,
                    'is_immutable': False,
                    'placeholder': 'Jin',
                    'help_text': 'Your main fighter',
                    'max_length': 30
                }
            ],
            'region_choices': [
                {'value': 'playstation', 'label': 'PlayStation'},
                {'value': 'xbox', 'label': 'Xbox'},
                {'value': 'pc', 'label': 'PC/Steam'}
            ]
        }
