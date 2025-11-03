"""
Management command to seed game configurations for dynamic tournament registration.

Seeds all 8 supported games with their fields and role configurations:
- Valorant, CS2, Dota 2, MLBB, PUBG, Free Fire, eFootball, FC 26
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.tournaments.models import (
    GameConfiguration,
    GameFieldConfiguration,
    PlayerRoleConfiguration
)


class Command(BaseCommand):
    help = 'Seeds game configurations, fields, and roles for dynamic tournament registration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing game configurations before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting existing game configurations...'))
            GameConfiguration.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Existing data deleted'))

        self.stdout.write(self.style.SUCCESS('Starting game configuration seeding...'))
        
        # Seed all 8 games
        self.seed_valorant()
        self.seed_counter_strike_2()
        self.seed_dota_2()
        self.seed_mobile_legends()
        self.seed_pubg()
        self.seed_free_fire()
        self.seed_efootball()
        self.seed_fc26()
        
        self.stdout.write(self.style.SUCCESS('\n✓ All game configurations seeded successfully!'))
        self.stdout.write(self.style.SUCCESS(f'  Total games: {GameConfiguration.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Total fields: {GameFieldConfiguration.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Total roles: {PlayerRoleConfiguration.objects.count()}'))

    def seed_valorant(self):
        """Seed Valorant configuration (5+2 team)"""
        self.stdout.write('Seeding VALORANT...')
        
        game = GameConfiguration.objects.create(
            game_code='valorant',
            display_name='VALORANT',
            icon='valorant.png',
            team_size=5,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Riot Games tactical FPS'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='riot_id',
            field_label='Riot ID',
            field_type='text',
            is_required=True,
            validation_regex=r'^[a-zA-Z0-9\s]+#[a-zA-Z0-9]+$',
            validation_error_message='Riot ID must be in format: Username#TAG (e.g., Player#1234)',
            placeholder='Username#TAG',
            help_text='Your Riot ID in format: Username#TAG',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            placeholder='username#1234 or @username',
            help_text='Your Discord username for team communication',
            display_order=2
        )
        
        # Roles
        roles = [
            ('duelist', 'Duelist', 'DUE', False, 1),
            ('controller', 'Controller', 'CON', False, 2),
            ('initiator', 'Initiator', 'INI', False, 3),
            ('sentinel', 'Sentinel', 'SEN', False, 4),
            ('igl', 'In-Game Leader', 'IGL', True, 5),
        ]
        
        for role_code, role_name, abbr, is_unique, display_order in roles:
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=is_unique,
                is_required=False,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ VALORANT seeded'))

    def seed_counter_strike_2(self):
        """Seed Counter-Strike 2 configuration (5+2 team)"""
        self.stdout.write('Seeding Counter-Strike 2...')
        
        game = GameConfiguration.objects.create(
            game_code='cs2',
            display_name='Counter-Strike 2',
            icon='cs2.png',
            team_size=5,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Valve tactical FPS'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='steam_id',
            field_label='Steam ID',
            field_type='text',
            is_required=True,
            validation_regex=r'^\d{17}$',
            validation_error_message='Steam ID must be a 17-digit number',
            placeholder='76561198012345678',
            help_text='Your 17-digit Steam ID',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='steam_profile',
            field_label='Steam Profile URL',
            field_type='url',
            is_required=False,
            placeholder='https://steamcommunity.com/id/yourprofile',
            help_text='Link to your Steam profile (optional)',
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            placeholder='username#1234',
            display_order=3
        )
        
        # Roles
        roles = [
            ('igl', 'In-Game Leader', 'IGL', True, 1),
            ('entry', 'Entry Fragger', 'Entry', False, 2),
            ('awper', 'AWPer', 'AWP', False, 3),
            ('lurker', 'Lurker', 'Lurk', False, 4),
            ('support', 'Support', 'Sup', False, 5),
        ]
        
        for role_code, role_name, abbr, is_unique, display_order in roles:
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=is_unique,
                is_required=False,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Counter-Strike 2 seeded'))

    def seed_dota_2(self):
        """Seed Dota 2 configuration (5+2 team)"""
        self.stdout.write('Seeding Dota 2...')
        
        game = GameConfiguration.objects.create(
            game_code='dota2',
            display_name='Dota 2',
            icon='dota2.png',
            team_size=5,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Valve MOBA'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='steam_id',
            field_label='Steam ID',
            field_type='text',
            is_required=True,
            validation_regex=r'^\d{17}$',
            validation_error_message='Steam ID must be a 17-digit number',
            placeholder='76561198012345678',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='dota_friend_id',
            field_label='Dota 2 Friend ID',
            field_type='text',
            is_required=True,
            validation_regex=r'^\d{9,10}$',
            validation_error_message='Friend ID must be 9-10 digits',
            placeholder='123456789',
            help_text='Your Dota 2 Friend ID (found in-game)',
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            display_order=3
        )
        
        # Roles - Positions 1-5
        roles = [
            ('pos_1', 'Position 1 - Carry', 'Pos 1', 1),
            ('pos_2', 'Position 2 - Mid', 'Pos 2', 2),
            ('pos_3', 'Position 3 - Offlaner', 'Pos 3', 3),
            ('pos_4', 'Position 4 - Soft Support', 'Pos 4', 4),
            ('pos_5', 'Position 5 - Hard Support', 'Pos 5', 5),
        ]
        
        for role_code, role_name, abbr, display_order in roles:
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=True,  # Each position can only have one player
                is_required=False,
                max_per_team=1,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Dota 2 seeded'))

    def seed_mobile_legends(self):
        """Seed Mobile Legends: Bang Bang configuration (5+2 team)"""
        self.stdout.write('Seeding Mobile Legends: Bang Bang...')
        
        game = GameConfiguration.objects.create(
            game_code='mlbb',
            display_name='Mobile Legends: Bang Bang',
            icon='mlbb.png',
            team_size=5,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Moonton mobile MOBA'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='mlbb_user_id',
            field_label='MLBB User ID',
            field_type='number',
            is_required=True,
            validation_regex=r'^\d{6,12}$',
            validation_error_message='User ID must be 6-12 digits',
            placeholder='123456789',
            help_text='Your Mobile Legends User ID (found in-game profile)',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='in_game_name',
            field_label='In-Game Name',
            field_type='text',
            is_required=True,
            min_length=3,
            max_length=50,
            placeholder='YourGameName',
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            display_order=3
        )
        
        # Roles
        roles = [
            ('gold_laner', 'Gold Laner', 'Gold', 1),
            ('exp_laner', 'EXP Laner', 'EXP', 2),
            ('mid_laner', 'Mid Laner', 'Mid', 3),
            ('jungler', 'Jungler', 'Jung', 4),
            ('roamer', 'Roamer', 'Roam', 5),
        ]
        
        for role_code, role_name, abbr, display_order in roles:
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=False,
                is_required=False,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Mobile Legends: Bang Bang seeded'))

    def seed_pubg(self):
        """Seed PUBG configuration (4+2 team)"""
        self.stdout.write('Seeding PUBG...')
        
        game = GameConfiguration.objects.create(
            game_code='pubg',
            display_name='PUBG: Battlegrounds',
            icon='pubg.png',
            team_size=4,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Krafton battle royale'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='pubg_id',
            field_label='PUBG ID',
            field_type='text',
            is_required=True,
            min_length=3,
            max_length=50,
            placeholder='YourPUBGID',
            help_text='Your PUBG player ID',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='character_name',
            field_label='Character Name',
            field_type='text',
            is_required=True,
            placeholder='CharacterName',
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            display_order=3
        )
        
        # Roles
        roles = [
            ('igl', 'In-Game Leader', 'IGL', True, 1),
            ('assaulter', 'Assaulter', 'Assault', False, 2),
            ('support', 'Support', 'Support', False, 3),
            ('sniper', 'Sniper', 'Sniper', False, 4),
        ]
        
        for role_code, role_name, abbr, is_unique, display_order in roles:
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=is_unique,
                is_required=False,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ PUBG: Battlegrounds seeded'))

    def seed_free_fire(self):
        """Seed Free Fire configuration (4+2 team)"""
        self.stdout.write('Seeding Free Fire...')
        
        game = GameConfiguration.objects.create(
            game_code='freefire',
            display_name='Free Fire',
            icon='freefire.png',
            team_size=4,
            sub_count=2,
            is_solo=False,
            is_team=True,
            is_active=True,
            description='Garena battle royale'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='ff_uid',
            field_label='Free Fire UID',
            field_type='number',
            is_required=True,
            validation_regex=r'^\d{9,12}$',
            validation_error_message='UID must be 9-12 digits',
            placeholder='123456789',
            help_text='Your Free Fire Unique ID',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='in_game_name',
            field_label='In-Game Name',
            field_type='text',
            is_required=True,
            min_length=3,
            max_length=50,
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='discord_id',
            field_label='Discord ID',
            field_type='text',
            is_required=False,
            display_order=3
        )
        
        # Roles
        roles = [
            ('rusher', 'Rusher', 'Rush', 1),
            ('flanker', 'Flanker', 'Flank', 2),
            ('support', 'Support', 'Support', 3),
            ('shot_caller', 'Shot Caller', 'IGL', 4),
        ]
        
        for role_code, role_name, abbr, display_order in roles:
            is_unique = role_code == 'shot_caller'
            PlayerRoleConfiguration.objects.create(
                game=game,
                role_code=role_code,
                role_name=role_name,
                role_abbreviation=abbr,
                is_unique=is_unique,
                is_required=False,
                display_order=display_order
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Free Fire seeded'))

    def seed_efootball(self):
        """Seed eFootball configuration (1 solo OR 2+1 team)"""
        self.stdout.write('Seeding eFootball...')
        
        game = GameConfiguration.objects.create(
            game_code='efootball',
            display_name='eFootball',
            icon='efootball.png',
            team_size=2,
            sub_count=1,
            is_solo=True,
            is_team=True,
            is_active=True,
            description='Konami football simulation'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='efootball_user_id',
            field_label='eFootball User ID',
            field_type='text',
            is_required=True,
            validation_regex=r'^\d{8,12}$',
            validation_error_message='User ID must be 8-12 digits',
            placeholder='12345678',
            help_text='Your eFootball User ID',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='username',
            field_label='Username',
            field_type='text',
            is_required=True,
            min_length=3,
            max_length=50,
            display_order=2
        )
        
        # No specific roles for eFootball (skill-based)
        
        self.stdout.write(self.style.SUCCESS('  ✓ eFootball seeded'))

    def seed_fc26(self):
        """Seed FC 26 configuration (1 solo OR 1+1 team)"""
        self.stdout.write('Seeding FC 26...')
        
        game = GameConfiguration.objects.create(
            game_code='fc26',
            display_name='FC 26 (EA Sports)',
            icon='fc26.png',
            team_size=1,
            sub_count=1,
            is_solo=True,
            is_team=True,
            is_active=True,
            description='EA Sports football simulation'
        )
        
        # Fields
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='ea_id',
            field_label='EA ID / Origin ID',
            field_type='text',
            is_required=True,
            min_length=3,
            max_length=50,
            placeholder='YourEAID',
            help_text='Your EA/Origin account ID',
            display_order=1
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='fc26_username',
            field_label='FC 26 Username',
            field_type='text',
            is_required=True,
            display_order=2
        )
        
        GameFieldConfiguration.objects.create(
            game=game,
            field_name='platform',
            field_label='Platform',
            field_type='select',
            is_required=True,
            choices=[
                {'value': 'pc', 'label': 'PC (Origin/EA App)'},
                {'value': 'ps5', 'label': 'PlayStation 5'},
                {'value': 'ps4', 'label': 'PlayStation 4'},
                {'value': 'xbox_series', 'label': 'Xbox Series X|S'},
                {'value': 'xbox_one', 'label': 'Xbox One'},
            ],
            help_text='Select your gaming platform',
            display_order=3
        )
        
        # No specific roles for FC 26
        
        self.stdout.write(self.style.SUCCESS('  ✓ FC 26 seeded'))
