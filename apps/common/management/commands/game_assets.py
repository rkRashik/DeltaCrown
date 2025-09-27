"""
Management command to list and update game asset paths.

Usage:
    python manage.py game_assets --list
    python manage.py game_assets --check-missing
    python manage.py game_assets --update-path VALORANT logo "new/path/to/logo.jpg"
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.templatetags.static import static
import os
from apps.common.game_assets import GAMES, get_game_data, get_game_logo

class Command(BaseCommand):
    help = 'Manage game assets configuration and paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all games and their asset paths',
        )
        parser.add_argument(
            '--check-missing',
            action='store_true',
            help='Check for missing asset files',
        )
        parser.add_argument(
            '--update-path',
            nargs=3,
            metavar=('GAME', 'ASSET_TYPE', 'NEW_PATH'),
            help='Update asset path for a game (e.g., VALORANT logo "new/path.jpg")',
        )
        parser.add_argument(
            '--game',
            help='Filter by specific game code',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_games(options.get('game'))
        elif options['check_missing']:
            self.check_missing_assets(options.get('game'))
        elif options['update_path']:
            self.update_asset_path(*options['update_path'])
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: --list, --check-missing, or --update-path'))

    def list_games(self, game_filter=None):
        """List all games and their asset paths."""
        self.stdout.write(self.style.SUCCESS('Game Assets Configuration:'))
        self.stdout.write('=' * 50)
        
        games = GAMES
        if game_filter:
            games = {k: v for k, v in games.items() if k.upper() == game_filter.upper()}
            
        for game_code, game_data in games.items():
            self.stdout.write(f"\n{self.style.HTTP_INFO(game_code)} - {game_data['display_name']}")
            self.stdout.write(f"  Category: {game_data['category']}")
            self.stdout.write(f"  Platforms: {', '.join(game_data['platform'])}")
            self.stdout.write(f"  Colors: {game_data['color_primary']} / {game_data['color_secondary']}")
            self.stdout.write("  Assets:")
            self.stdout.write(f"    Logo:   {game_data['logo']}")
            self.stdout.write(f"    Card:   {game_data['card']}")
            self.stdout.write(f"    Icon:   {game_data['icon']}")
            self.stdout.write(f"    Banner: {game_data['banner']}")

    def check_missing_assets(self, game_filter=None):
        """Check for missing asset files."""
        self.stdout.write(self.style.SUCCESS('Checking for missing asset files:'))
        self.stdout.write('=' * 50)
        
        missing_count = 0
        games = GAMES
        if game_filter:
            games = {k: v for k, v in games.items() if k.upper() == game_filter.upper()}
            
        for game_code, game_data in games.items():
            self.stdout.write(f"\nChecking {self.style.HTTP_INFO(game_code)}:")
            
            for asset_type in ['logo', 'card', 'icon', 'banner']:
                asset_path = game_data[asset_type]
                full_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', asset_path)
                
                if os.path.exists(full_path):
                    self.stdout.write(f"  ✓ {asset_type}: {asset_path}")
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ {asset_type}: {asset_path} (MISSING)"))
                    missing_count += 1
        
        if missing_count == 0:
            self.stdout.write(self.style.SUCCESS(f"\n✓ All assets found!"))
        else:
            self.stdout.write(self.style.ERROR(f"\n⚠ {missing_count} assets are missing."))

    def update_asset_path(self, game_code, asset_type, new_path):
        """Update an asset path (note: this requires manual editing of game_assets.py)."""
        game_code = game_code.upper()
        
        if game_code not in GAMES:
            raise CommandError(f'Game "{game_code}" not found. Available games: {", ".join(GAMES.keys())}')
            
        if asset_type not in ['logo', 'card', 'icon', 'banner']:
            raise CommandError(f'Invalid asset type "{asset_type}". Valid types: logo, card, icon, banner')
        
        old_path = GAMES[game_code][asset_type]
        
        self.stdout.write(f"Game: {game_code}")
        self.stdout.write(f"Asset: {asset_type}")
        self.stdout.write(f"Old path: {old_path}")
        self.stdout.write(f"New path: {new_path}")
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.WARNING("To update this path, please edit:"))
        self.stdout.write(f"apps/common/game_assets.py")
        self.stdout.write(f"Change line for {game_code}['{asset_type}'] from:")
        self.stdout.write(f"  '{old_path}'")
        self.stdout.write(f"To:")
        self.stdout.write(f"  '{new_path}'")
        
    def get_asset_file_info(self, asset_path):
        """Get information about an asset file."""
        static_root = settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static')
        full_path = os.path.join(static_root, asset_path)
        
        info = {
            'path': asset_path,
            'full_path': full_path,
            'exists': os.path.exists(full_path),
            'url': static(asset_path)
        }
        
        if info['exists']:
            stat = os.stat(full_path)
            info['size'] = stat.st_size
            info['modified'] = stat.st_mtime
            
        return info