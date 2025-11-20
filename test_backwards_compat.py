"""Quick test for backwards compatibility"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.common.game_assets import GAMES, get_game_data, get_game_logo

print('Testing backwards compatibility...')
print(f'GAMES dict has {len(GAMES)} entries')

valo = get_game_data('VALORANT')
print(f'Valorant: {valo["display_name"]}')

logo = get_game_logo('cs2')
print(f'CS2 logo: {logo[:50]}...')

print('✓ Backwards compatibility working!')
