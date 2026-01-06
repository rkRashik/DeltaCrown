"""
Management command to seed comprehensive Game Player Identity Configs with 2026-accurate data.

THIS IS THE 2026-ACCURATE VERSION - Generated January 4, 2026
Data sources: Official game APIs, competitive rank structures, server lists

All rank/region/role/platform options are current as of January 2026.
DO NOT HARDCODE these in frontend - fetch from API GET /profile/api/games/

Usage:
    python manage.py seed_identity_configs_2026
    python manage.py seed_identity_configs_2026 --game valorant
    python manage.py seed_identity_configs_2026 --force  # Overwrite existing
"""

from django.core.management.base import BaseCommand
from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GamePassportSchema


class Command(BaseCommand):
    help = 'Seed comprehensive identity configs with 2026-accurate data (idempotent)'

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
            self.stdout.write(f'\n[SEED 2026] Seeding identity configs for {games.count()} active games...\n')
            for game in games:
                self.seed_game(game, force)
        
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] 2026-accurate identity config seeding complete!'))

    def seed_game(self, game, force=False):
        """Seed identity configs for a single game"""
        self.stdout.write(f'\n[GAME] {game.display_name} ({game.slug})')
        
        # Get game-specific schema
        schema = self.get_game_schema(game.slug)
        
        if not schema:
            self.stdout.write(self.style.WARNING(f'  [WARN] No schema defined for {game.slug} - skipping'))
            return
        
        # PHASE 9A-20: Delete stale fields not in schema (idempotency fix)
        if force:
            schema_field_names = [f['field_name'] for f in schema['fields']]
            stale_configs = GamePlayerIdentityConfig.objects.filter(game=game).exclude(field_name__in=schema_field_names)
            stale_count = stale_configs.count()
            if stale_count > 0:
                stale_fields = list(stale_configs.values_list('field_name', flat=True))
                stale_configs.delete()
                self.stdout.write(self.style.WARNING(f'  [CLEANUP] Deleted {stale_count} stale fields: {", ".join(stale_fields)}'))
        
        # Seed identity fields
        for order, field_config in enumerate(schema['fields'], start=1):
            field_name = field_config['field_name']
            
            # Check if exists
            existing = GamePlayerIdentityConfig.objects.filter(
                game=game,
                field_name=field_name
            ).first()
            
            if existing and not force:
                self.stdout.write(f'  [OK] {field_name} already exists')
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
            self.stdout.write(f'  {action} {identity_config.display_name}')
        
        # Seed GamePassportSchema for select field options
        passport_schema, created = GamePassportSchema.objects.get_or_create(game=game)
        
        if 'region_choices' in schema:
            passport_schema.region_choices = schema['region_choices']
        if 'rank_choices' in schema:
            passport_schema.rank_choices = schema['rank_choices']
        if 'role_choices' in schema:
            passport_schema.role_choices = schema['role_choices']
        if 'platform_choices' in schema:
            passport_schema.platform_choices = schema['platform_choices']
        if 'server_choices' in schema:
            passport_schema.server_choices = schema['server_choices']
        if 'mode_choices' in schema:
            passport_schema.mode_choices = schema['mode_choices']
        if 'premier_rating_choices' in schema:
            passport_schema.premier_rating_choices = schema['premier_rating_choices']
        if 'division_choices' in schema:
            passport_schema.division_choices = schema['division_choices']
        
        passport_schema.save()
        self.stdout.write(f'  [OK] Updated GamePassportSchema with 2026 dropdown options')

    def get_game_schema(self, slug):
        """
        2026-accurate game schemas with real rank/region/role/platform data.
        
        Data sourced from:
        - Official game APIs (VALORANT, CS2, Dota 2)
        - Competitive structures (Mobile games)
        - Cross-platform documentation (EA FC, Rainbow Six, Rocket League)
        
        LAST UPDATED: January 4, 2026
        """
        
        schemas = {
            ##############################################
            # 1. VALORANT
            ##############################################
            'valorant': {
                'fields': [
                    {
                        'field_name': 'riot_id',
                        'display_name': 'Riot ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^[a-zA-Z0-9 ]{3,16}#[a-zA-Z0-9]{3,5}$',
                        'validation_error_message': 'Format: Username#TAG (e.g., TenZ#1234)',
                        'placeholder': 'PlayerName#NA1',
                        'help_text': 'Your Riot ID with tagline (e.g., TenZ#1234)',
                        'min_length': 7,
                        'max_length': 22
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 'TenZ',
                        'help_text': 'Display name (auto-filled from Riot ID)',
                        'max_length': 16
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Region',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your primary server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Current competitive rank (Episode 10 Act 1)'
                    },
                    {
                        'field_name': 'peak_rank',
                        'display_name': 'Peak Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Highest competitive rank achieved'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary agent role'
                    }
                ],
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'LATAM', 'label': 'Latin America (North)'},
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'TR', 'label': 'Turkey'},
                    {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    {'value': 'KR', 'label': 'Korea'},
                    {'value': 'AP', 'label': 'Asia Pacific'},
                    {'value': 'OCE', 'label': 'Oceania'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'iron1', 'label': 'Iron 1'},
                    {'value': 'iron2', 'label': 'Iron 2'},
                    {'value': 'iron3', 'label': 'Iron 3'},
                    {'value': 'bronze1', 'label': 'Bronze 1'},
                    {'value': 'bronze2', 'label': 'Bronze 2'},
                    {'value': 'bronze3', 'label': 'Bronze 3'},
                    {'value': 'silver1', 'label': 'Silver 1'},
                    {'value': 'silver2', 'label': 'Silver 2'},
                    {'value': 'silver3', 'label': 'Silver 3'},
                    {'value': 'gold1', 'label': 'Gold 1'},
                    {'value': 'gold2', 'label': 'Gold 2'},
                    {'value': 'gold3', 'label': 'Gold 3'},
                    {'value': 'platinum1', 'label': 'Platinum 1'},
                    {'value': 'platinum2', 'label': 'Platinum 2'},
                    {'value': 'platinum3', 'label': 'Platinum 3'},
                    {'value': 'diamond1', 'label': 'Diamond 1'},
                    {'value': 'diamond2', 'label': 'Diamond 2'},
                    {'value': 'diamond3', 'label': 'Diamond 3'},
                    {'value': 'ascendant1', 'label': 'Ascendant 1'},
                    {'value': 'ascendant2', 'label': 'Ascendant 2'},
                    {'value': 'ascendant3', 'label': 'Ascendant 3'},
                    {'value': 'immortal1', 'label': 'Immortal 1'},
                    {'value': 'immortal2', 'label': 'Immortal 2'},
                    {'value': 'immortal3', 'label': 'Immortal 3'},
                    {'value': 'radiant', 'label': 'Radiant'}
                ],
                'role_choices': [
                    {'value': 'duelist', 'label': 'Duelist (Entry Fragger)'},
                    {'value': 'controller', 'label': 'Controller (Smoke/Vision)'},
                    {'value': 'initiator', 'label': 'Initiator (Info/Flash)'},
                    {'value': 'sentinel', 'label': 'Sentinel (Anchor/Trap)'}
                ]
            },
            
            ##############################################
            # 2. COUNTER-STRIKE 2
            ##############################################
            'cs2': {
                'fields': [
                    {
                        'field_name': 'steam_id',
                        'display_name': 'Steam ID64',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^7656119\d{10}$',
                        'validation_error_message': 'Must be 17-digit Steam ID64 (find at steamid.io)',
                        'placeholder': '76561198012345678',
                        'help_text': 'Your 17-digit Steam ID (find at steamid.io)',
                        'min_length': 17,
                        'max_length': 17
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 's1mple',
                        'help_text': 'Current Steam display name',
                        'max_length': 32
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Primary Region',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Main server region'
                    },
                    {
                        'field_name': 'premier_rating',
                        'display_name': 'Premier Rating',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'CS2 Premier competitive rating range'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary team role'
                    }
                ],
                'region_choices': [
                    {'value': 'EU_WEST', 'label': 'Europe West'},
                    {'value': 'EU_EAST', 'label': 'Europe East'},
                    {'value': 'NA_EAST', 'label': 'North America East'},
                    {'value': 'NA_WEST', 'label': 'North America West'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'OCEANIA', 'label': 'Oceania'},
                    {'value': 'AFRICA', 'label': 'Africa & Middle East'}
                ],
                'premier_rating_choices': [
                    {'value': '0-5000', 'label': 'Grey (Unranked)'},
                    {'value': '5000-10000', 'label': 'Blue (5,000 - 10,000)'},
                    {'value': '10000-15000', 'label': 'Purple (10,000 - 15,000)'},
                    {'value': '15000-20000', 'label': 'Pink (15,000 - 20,000)'},
                    {'value': '20000-25000', 'label': 'Red (20,000 - 25,000)'},
                    {'value': '25000-30000', 'label': 'Orange (25,000 - 30,000)'},
                    {'value': '30000+', 'label': 'Yellow (30,000+)'}
                ],
                'role_choices': [
                    {'value': 'entry', 'label': 'Entry Fragger'},
                    {'value': 'awp', 'label': 'AWPer/Sniper'},
                    {'value': 'support', 'label': 'Support/Trade'},
                    {'value': 'igl', 'label': 'In-Game Leader'},
                    {'value': 'lurk', 'label': 'Lurker'}
                ]
            },
            
            ##############################################
            # 3. DOTA 2
            ##############################################
            'dota2': {
                'fields': [
                    {
                        'field_name': 'steam_id',
                        'display_name': 'Steam ID64',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^7656119\d{10}$',
                        'validation_error_message': 'Must be 17-digit Steam ID64',
                        'placeholder': '76561198012345678',
                        'help_text': 'Your 17-digit Steam ID',
                        'min_length': 17,
                        'max_length': 17
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'is_immutable': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Primary Server',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Main server for ranked games'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Current MMR rank'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary position (1-5)'
                    }
                ],
                'server_choices': [
                    {'value': 'USE', 'label': 'US East'},
                    {'value': 'USW', 'label': 'US West'},
                    {'value': 'EUW', 'label': 'Europe West'},
                    {'value': 'EUE', 'label': 'Europe East'},
                    {'value': 'RU', 'label': 'Russia'},
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'CHINA', 'label': 'China (Perfect World)'},
                    {'value': 'AUS', 'label': 'Australia'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'JAPAN', 'label': 'Japan'},
                    {'value': 'DUBAI', 'label': 'Dubai'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'herald1', 'label': 'Herald 1'},
                    {'value': 'herald2', 'label': 'Herald 2'},
                    {'value': 'herald3', 'label': 'Herald 3'},
                    {'value': 'herald4', 'label': 'Herald 4'},
                    {'value': 'herald5', 'label': 'Herald 5'},
                    {'value': 'guardian1', 'label': 'Guardian 1'},
                    {'value': 'guardian2', 'label': 'Guardian 2'},
                    {'value': 'guardian3', 'label': 'Guardian 3'},
                    {'value': 'guardian4', 'label': 'Guardian 4'},
                    {'value': 'guardian5', 'label': 'Guardian 5'},
                    {'value': 'crusader1', 'label': 'Crusader 1'},
                    {'value': 'crusader2', 'label': 'Crusader 2'},
                    {'value': 'crusader3', 'label': 'Crusader 3'},
                    {'value': 'crusader4', 'label': 'Crusader 4'},
                    {'value': 'crusader5', 'label': 'Crusader 5'},
                    {'value': 'archon1', 'label': 'Archon 1'},
                    {'value': 'archon2', 'label': 'Archon 2'},
                    {'value': 'archon3', 'label': 'Archon 3'},
                    {'value': 'archon4', 'label': 'Archon 4'},
                    {'value': 'archon5', 'label': 'Archon 5'},
                    {'value': 'legend1', 'label': 'Legend 1'},
                    {'value': 'legend2', 'label': 'Legend 2'},
                    {'value': 'legend3', 'label': 'Legend 3'},
                    {'value': 'legend4', 'label': 'Legend 4'},
                    {'value': 'legend5', 'label': 'Legend 5'},
                    {'value': 'ancient1', 'label': 'Ancient 1'},
                    {'value': 'ancient2', 'label': 'Ancient 2'},
                    {'value': 'ancient3', 'label': 'Ancient 3'},
                    {'value': 'ancient4', 'label': 'Ancient 4'},
                    {'value': 'ancient5', 'label': 'Ancient 5'},
                    {'value': 'divine1', 'label': 'Divine 1'},
                    {'value': 'divine2', 'label': 'Divine 2'},
                    {'value': 'divine3', 'label': 'Divine 3'},
                    {'value': 'divine4', 'label': 'Divine 4'},
                    {'value': 'divine5', 'label': 'Divine 5'},
                    {'value': 'immortal', 'label': 'Immortal'}
                ],
                'role_choices': [
                    {'value': 'carry', 'label': 'Position 1 (Hard Carry)'},
                    {'value': 'mid', 'label': 'Position 2 (Mid Lane)'},
                    {'value': 'offlane', 'label': 'Position 3 (Offlane)'},
                    {'value': 'soft_support', 'label': 'Position 4 (Soft Support)'},
                    {'value': 'hard_support', 'label': 'Position 5 (Hard Support)'}
                ]
            },
            
            ##############################################
            # 4. MOBILE LEGENDS: BANG BANG
            # Phase 9A-15 Section D: Clarified user_id vs server_id labels and help text
            ##############################################
            'mlbb': {
                'fields': [
                    {
                        'field_name': 'game_id',
                        'display_name': 'Account ID (User ID)',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{8,12}$',
                        'validation_error_message': 'Must be 8-12 digit Account ID',
                        'placeholder': '123456789',
                        'help_text': 'Your MLBB Account ID: Tap profile icon → Copy User ID (8-12 digits)',
                        'min_length': 8,
                        'max_length': 12
                    },
                    {
                        'field_name': 'server_id',
                        'display_name': 'Server ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{4,6}$',
                        'validation_error_message': 'Must be 4-6 digit Server ID',
                        'placeholder': '12345',
                        'help_text': 'Your Server ID: Tap profile icon → shown next to User ID (4-6 digits)',
                        'min_length': 4,
                        'max_length': 6
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'help_text': 'Your current display name (can change)',
                        'max_length': 32
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Server Region',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Current ranked season rank'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary hero role'
                    }
                ],
                'server_choices': [
                    {'value': 'ID', 'label': 'Indonesia'},
                    {'value': 'MY', 'label': 'Malaysia'},
                    {'value': 'SG', 'label': 'Singapore'},
                    {'value': 'PH', 'label': 'Philippines'},
                    {'value': 'TH', 'label': 'Thailand'},
                    {'value': 'VN', 'label': 'Vietnam'},
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    {'value': 'IN', 'label': 'India'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'warrior1', 'label': 'Warrior I'},
                    {'value': 'warrior2', 'label': 'Warrior II'},
                    {'value': 'warrior3', 'label': 'Warrior III'},
                    {'value': 'elite1', 'label': 'Elite I'},
                    {'value': 'elite2', 'label': 'Elite II'},
                    {'value': 'elite3', 'label': 'Elite III'},
                    {'value': 'elite4', 'label': 'Elite IV'},
                    {'value': 'elite5', 'label': 'Elite V'},
                    {'value': 'master1', 'label': 'Master I'},
                    {'value': 'master2', 'label': 'Master II'},
                    {'value': 'master3', 'label': 'Master III'},
                    {'value': 'master4', 'label': 'Master IV'},
                    {'value': 'grandmaster1', 'label': 'Grandmaster I'},
                    {'value': 'grandmaster2', 'label': 'Grandmaster II'},
                    {'value': 'grandmaster3', 'label': 'Grandmaster III'},
                    {'value': 'grandmaster4', 'label': 'Grandmaster IV'},
                    {'value': 'grandmaster5', 'label': 'Grandmaster V'},
                    {'value': 'epic1', 'label': 'Epic I'},
                    {'value': 'epic2', 'label': 'Epic II'},
                    {'value': 'epic3', 'label': 'Epic III'},
                    {'value': 'epic4', 'label': 'Epic IV'},
                    {'value': 'epic5', 'label': 'Epic V'},
                    {'value': 'legend1', 'label': 'Legend I'},
                    {'value': 'legend2', 'label': 'Legend II'},
                    {'value': 'legend3', 'label': 'Legend III'},
                    {'value': 'legend4', 'label': 'Legend IV'},
                    {'value': 'legend5', 'label': 'Legend V'},
                    {'value': 'mythic1', 'label': 'Mythic I'},
                    {'value': 'mythic2', 'label': 'Mythic II'},
                    {'value': 'mythic3', 'label': 'Mythic III'},
                    {'value': 'mythic4', 'label': 'Mythic IV'},
                    {'value': 'mythic5', 'label': 'Mythic V'},
                    {'value': 'mythical_glory', 'label': 'Mythical Glory'},
                    {'value': 'mythical_honor', 'label': 'Mythical Honor'}
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
            
            ##############################################
            # 5. PUBG MOBILE
            ##############################################
            'pubgm': {
                'fields': [
                    {
                        'field_name': 'player_id',
                        'display_name': 'Character ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{9,12}$',
                        'validation_error_message': 'Must be 9-12 digit Character ID',
                        'placeholder': '5123456789',
                        'help_text': 'Your PUBG Mobile Character ID (found in profile)',
                        'min_length': 9,
                        'max_length': 12
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Server',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Highest rank across all modes'
                    },
                    {
                        'field_name': 'mode',
                        'display_name': 'Main Mode',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary game mode'
                    }
                ],
                'server_choices': [
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'EUROPE', 'label': 'Europe'},
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'ME', 'label': 'Middle East'}
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze'},
                    {'value': 'silver', 'label': 'Silver'},
                    {'value': 'gold', 'label': 'Gold'},
                    {'value': 'platinum', 'label': 'Platinum'},
                    {'value': 'diamond', 'label': 'Diamond'},
                    {'value': 'crown', 'label': 'Crown'},
                    {'value': 'ace', 'label': 'Ace'},
                    {'value': 'ace_master', 'label': 'Ace Master'},
                    {'value': 'ace_dominator', 'label': 'Ace Dominator'},
                    {'value': 'conqueror', 'label': 'Conqueror'}
                ],
                'mode_choices': [
                    {'value': 'tpp_squad', 'label': 'TPP Squad'},
                    {'value': 'tpp_duo', 'label': 'TPP Duo'},
                    {'value': 'tpp_solo', 'label': 'TPP Solo'},
                    {'value': 'fpp_squad', 'label': 'FPP Squad'},
                    {'value': 'fpp_duo', 'label': 'FPP Duo'},
                    {'value': 'fpp_solo', 'label': 'FPP Solo'}
                ]
            },
            
            ##############################################
            # 6. FREE FIRE
            ##############################################
            'freefire': {
                'fields': [
                    {
                        'field_name': 'player_id',
                        'display_name': 'Player ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^\d{9,12}$',
                        'validation_error_message': 'Must be 9-12 digit Player ID',
                        'placeholder': '1234567890',
                        'help_text': 'Your Free Fire Player ID',
                        'min_length': 9,
                        'max_length': 12
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'server',
                        'display_name': 'Server',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Current ranked season rank'
                    }
                ],
                'server_choices': [
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'ME', 'label': 'Middle East'},
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'SA', 'label': 'South Asia'},
                    {'value': 'EU', 'label': 'Europe'}
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze'},
                    {'value': 'silver', 'label': 'Silver'},
                    {'value': 'gold', 'label': 'Gold'},
                    {'value': 'platinum', 'label': 'Platinum'},
                    {'value': 'diamond', 'label': 'Diamond'},
                    {'value': 'heroic', 'label': 'Heroic'},
                    {'value': 'grandmaster', 'label': 'Grandmaster'}
                ]
            },
            
            ##############################################
            # 7. CALL OF DUTY: MOBILE
            ##############################################
            'codm': {
                'fields': [
                    {
                        'field_name': 'codm_uid',
                        'display_name': 'COD Mobile UID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'validation_regex': r'^6\d{9}$',
                        'validation_error_message': 'Must be 10-digit UID starting with 6',
                        'placeholder': '6000000000',
                        'help_text': 'Your COD Mobile UID (found in profile, starts with 6)',
                        'min_length': 10,
                        'max_length': 10
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Region',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your server region'
                    },
                    {
                        'field_name': 'rank_mp',
                        'display_name': 'MP Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Multiplayer ranked mode rank'
                    },
                    {
                        'field_name': 'rank_br',
                        'display_name': 'BR Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Battle Royale ranked mode rank'
                    },
                    {
                        'field_name': 'mode',
                        'display_name': 'Main Mode',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary competitive mode'
                    }
                ],
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'ME', 'label': 'Middle East'}
                ],
                'rank_choices': [
                    {'value': 'rookie', 'label': 'Rookie'},
                    {'value': 'veteran', 'label': 'Veteran'},
                    {'value': 'elite', 'label': 'Elite'},
                    {'value': 'pro', 'label': 'Pro'},
                    {'value': 'master', 'label': 'Master'},
                    {'value': 'grandmaster', 'label': 'Grand Master'},
                    {'value': 'legendary', 'label': 'Legendary'}
                ],
                'mode_choices': [
                    {'value': 'mp', 'label': 'Multiplayer (Ranked)'},
                    {'value': 'br', 'label': 'Battle Royale (Ranked)'}
                ]
            },
            
            ##############################################
            # 8. EA SPORTS FC 26
            ##############################################
            'ea-fc': {
                'fields': [
                    {
                        'field_name': 'ea_id',
                        'display_name': 'EA ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'placeholder': 'YourEAID',
                        'help_text': 'Your EA Account ID / Persona ID',
                        'max_length': 64
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'platform',
                        'display_name': 'Platform',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': True,
                        'help_text': 'Your gaming platform (cannot change)'
                    },
                    {
                        'field_name': 'division',
                        'display_name': 'Division',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'FUT Rivals division'
                    },
                    {
                        'field_name': 'mode',
                        'display_name': 'Main Mode',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary competitive mode'
                    }
                ],
                'platform_choices': [
                    {'value': 'playstation', 'label': 'PlayStation 5'},
                    {'value': 'xbox', 'label': 'Xbox Series X|S'},
                    {'value': 'pc', 'label': 'PC (Origin/Steam)'},
                    {'value': 'switch', 'label': 'Nintendo Switch'}
                ],
                'division_choices': [
                    {'value': 'div10', 'label': 'Division 10'},
                    {'value': 'div9', 'label': 'Division 9'},
                    {'value': 'div8', 'label': 'Division 8'},
                    {'value': 'div7', 'label': 'Division 7'},
                    {'value': 'div6', 'label': 'Division 6'},
                    {'value': 'div5', 'label': 'Division 5'},
                    {'value': 'div4', 'label': 'Division 4'},
                    {'value': 'div3', 'label': 'Division 3'},
                    {'value': 'div2', 'label': 'Division 2'},
                    {'value': 'div1', 'label': 'Division 1'},
                    {'value': 'elite', 'label': 'Elite Division'}
                ],
                'mode_choices': [
                    {'value': 'fut_rivals', 'label': 'FUT Rivals'},
                    {'value': 'fut_champions', 'label': 'FUT Champions'},
                    {'value': 'pro_clubs', 'label': 'Pro Clubs'},
                    {'value': 'volta', 'label': 'VOLTA Football'}
                ]
            },
            
            ##############################################
            # 9. eFOOTBALL 2026
            # Source: Konami Official eFootball 2026 documentation
            # Last updated: January 6, 2026 (Phase 9A-23: Fixed schema)
            # REQUIRED: konami_id + user_id ONLY
            # NOTE: IGN field removed (not applicable for eFootball identity system)
            ##############################################
            'efootball': {
                'fields': [
                    {
                        'field_name': 'konami_id',
                        'display_name': 'Konami ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'placeholder': 'exampleUser123',
                        'help_text': 'Find at my.konami.net → Personal Info → Konami ID (alphanumeric, case-sensitive)',
                        'max_length': 64
                    },
                    {
                        'field_name': 'user_id',
                        'display_name': 'User ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'placeholder': 'ABCD-123-456-789',
                        'help_text': 'In-game: Extras → User Information → User Personal Information → User ID',
                        'validation_regex': r'^[A-Z]{4}-\d{3}-\d{3}-\d{3}$',
                        'validation_error_message': 'Must be format: XXXX-XXX-XXX-XXX (e.g., ABCD-123-456-789)',
                        'max_length': 19
                    },
                    {
                        'field_name': 'username',
                        'display_name': 'Username',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'rkrashik',
                        'help_text': 'Your in-game username (optional)',
                        'max_length': 32
                    },
                    {
                        'field_name': 'division',
                        'display_name': 'Division',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Your current competitive division (optional)'
                    },
                    {
                        'field_name': 'team_name',
                        'display_name': 'Team Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'SIUU',
                        'help_text': 'Your custom team name (optional)',
                        'max_length': 32
                    },
                    {
                        'field_name': 'platform',
                        'display_name': 'Platform',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your gaming platform (required)'
                    }
                ],
                'platform_choices': [
                    {'value': 'playstation', 'label': 'PlayStation 5'},
                    {'value': 'xbox', 'label': 'Xbox Series X|S'},
                    {'value': 'pc', 'label': 'PC (Steam)'},
                    {'value': 'mobile', 'label': 'Mobile (iOS/Android)'}
                ],
                'division_choices': [
                    {'value': 'division1', 'label': 'Division 1'},
                    {'value': 'division2', 'label': 'Division 2'},
                    {'value': 'division3', 'label': 'Division 3'},
                    {'value': 'division4', 'label': 'Division 4'},
                    {'value': 'division5', 'label': 'Division 5'},
                    {'value': 'division6', 'label': 'Division 6'},
                    {'value': 'division7', 'label': 'Division 7'},
                    {'value': 'division8', 'label': 'Division 8'},
                    {'value': 'division9', 'label': 'Division 9'}
                ]
            },
            
            ##############################################
            # 10. RAINBOW SIX SIEGE
            ##############################################
            'r6siege': {
                'fields': [
                    {
                        'field_name': 'uplay_id',
                        'display_name': 'Ubisoft Connect ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'placeholder': 'YourUplayID',
                        'help_text': 'Your Ubisoft Connect username',
                        'max_length': 64
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'platform',
                        'display_name': 'Platform',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': True,
                        'help_text': 'Your gaming platform'
                    },
                    {
                        'field_name': 'region',
                        'display_name': 'Region',
                        'field_type': 'select',
                        'is_required': True,
                        'help_text': 'Your server region'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Current Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Current ranked season rank (Year 9)'
                    },
                    {
                        'field_name': 'role',
                        'display_name': 'Main Role',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary team role'
                    }
                ],
                'platform_choices': [
                    {'value': 'pc', 'label': 'PC (Ubisoft Connect)'},
                    {'value': 'playstation', 'label': 'PlayStation 5'},
                    {'value': 'xbox', 'label': 'Xbox Series X|S'}
                ],
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'LATAM', 'label': 'Latin America'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'copper5', 'label': 'Copper V'},
                    {'value': 'copper4', 'label': 'Copper IV'},
                    {'value': 'copper3', 'label': 'Copper III'},
                    {'value': 'copper2', 'label': 'Copper II'},
                    {'value': 'copper1', 'label': 'Copper I'},
                    {'value': 'bronze5', 'label': 'Bronze V'},
                    {'value': 'bronze4', 'label': 'Bronze IV'},
                    {'value': 'bronze3', 'label': 'Bronze III'},
                    {'value': 'bronze2', 'label': 'Bronze II'},
                    {'value': 'bronze1', 'label': 'Bronze I'},
                    {'value': 'silver5', 'label': 'Silver V'},
                    {'value': 'silver4', 'label': 'Silver IV'},
                    {'value': 'silver3', 'label': 'Silver III'},
                    {'value': 'silver2', 'label': 'Silver II'},
                    {'value': 'silver1', 'label': 'Silver I'},
                    {'value': 'gold3', 'label': 'Gold III'},
                    {'value': 'gold2', 'label': 'Gold II'},
                    {'value': 'gold1', 'label': 'Gold I'},
                    {'value': 'platinum3', 'label': 'Platinum III'},
                    {'value': 'platinum2', 'label': 'Platinum II'},
                    {'value': 'platinum1', 'label': 'Platinum I'},
                    {'value': 'emerald3', 'label': 'Emerald III'},
                    {'value': 'emerald2', 'label': 'Emerald II'},
                    {'value': 'emerald1', 'label': 'Emerald I'},
                    {'value': 'diamond3', 'label': 'Diamond III'},
                    {'value': 'diamond2', 'label': 'Diamond II'},
                    {'value': 'diamond1', 'label': 'Diamond I'},
                    {'value': 'champion', 'label': 'Champion'}
                ],
                'role_choices': [
                    {'value': 'entry', 'label': 'Entry Fragger'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'intel', 'label': 'Intel Gatherer'},
                    {'value': 'flex', 'label': 'Flex'}
                ]
            },
            
            ##############################################
            # 11. ROCKET LEAGUE
            ##############################################
            'rocketleague': {
                'fields': [
                    {
                        'field_name': 'epic_id',
                        'display_name': 'Epic Games ID',
                        'field_type': 'TEXT',
                        'is_required': True,
                        'is_immutable': True,
                        'placeholder': 'YourEpicID',
                        'help_text': 'Your Epic Games account name',
                        'max_length': 64
                    },
                    {
                        'field_name': 'ign',
                        'display_name': 'In-Game Name',
                        'field_type': 'TEXT',
                        'is_required': False,
                        'placeholder': 'PlayerName',
                        'max_length': 32
                    },
                    {
                        'field_name': 'platform',
                        'display_name': 'Platform',
                        'field_type': 'select',
                        'is_required': True,
                        'is_immutable': True,
                        'help_text': 'Your primary gaming platform'
                    },
                    {
                        'field_name': 'rank',
                        'display_name': 'Highest Rank',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Highest rank across all competitive modes'
                    },
                    {
                        'field_name': 'mode',
                        'display_name': 'Main Mode',
                        'field_type': 'select',
                        'is_required': False,
                        'help_text': 'Primary competitive mode'
                    }
                ],
                'platform_choices': [
                    {'value': 'epic', 'label': 'Epic Games'},
                    {'value': 'steam', 'label': 'Steam'},
                    {'value': 'playstation', 'label': 'PlayStation'},
                    {'value': 'xbox', 'label': 'Xbox'},
                    {'value': 'switch', 'label': 'Nintendo Switch'}
                ],
                'rank_choices': [
                    {'value': 'unranked', 'label': 'Unranked'},
                    {'value': 'bronze1', 'label': 'Bronze I'},
                    {'value': 'bronze2', 'label': 'Bronze II'},
                    {'value': 'bronze3', 'label': 'Bronze III'},
                    {'value': 'silver1', 'label': 'Silver I'},
                    {'value': 'silver2', 'label': 'Silver II'},
                    {'value': 'silver3', 'label': 'Silver III'},
                    {'value': 'gold1', 'label': 'Gold I'},
                    {'value': 'gold2', 'label': 'Gold II'},
                    {'value': 'gold3', 'label': 'Gold III'},
                    {'value': 'platinum1', 'label': 'Platinum I'},
                    {'value': 'platinum2', 'label': 'Platinum II'},
                    {'value': 'platinum3', 'label': 'Platinum III'},
                    {'value': 'diamond1', 'label': 'Diamond I'},
                    {'value': 'diamond2', 'label': 'Diamond II'},
                    {'value': 'diamond3', 'label': 'Diamond III'},
                    {'value': 'champion1', 'label': 'Champion I'},
                    {'value': 'champion2', 'label': 'Champion II'},
                    {'value': 'champion3', 'label': 'Champion III'},
                    {'value': 'grand_champion1', 'label': 'Grand Champion I'},
                    {'value': 'grand_champion2', 'label': 'Grand Champion II'},
                    {'value': 'grand_champion3', 'label': 'Grand Champion III'},
                    {'value': 'supersonic_legend', 'label': 'Supersonic Legend'}
                ],
                'mode_choices': [
                    {'value': '1v1', 'label': '1v1 Duel'},
                    {'value': '2v2', 'label': '2v2 Doubles'},
                    {'value': '3v3', 'label': '3v3 Standard'},
                    {'value': 'extra', 'label': 'Extra Modes (Rumble/Dropshot/Hoops/Snow Day)'}
                ]
            },
        }
        
        return schemas.get(slug)
