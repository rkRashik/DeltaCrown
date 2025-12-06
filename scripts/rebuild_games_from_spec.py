"""
Clean up and rebuild game database to match Game_Spec.md exactly.
Then add Rainbow Six Siege and Rocket League.

Run with:
    python scripts/rebuild_games_from_spec.py
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GameRosterConfig, GamePlayerIdentityConfig

# Games from Game_Spec.md EXACTLY
SPEC_GAMES = {
    'valorant': {
        'name': 'Valorant',
        'display_name': 'VALORANT',
        'short_code': 'VAL',
        'category': 'FPS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC'],
        'primary_color': '#ff4654',
        'secondary_color': '#0f1923',
        'description': 'A 5v5 character-based tactical FPS where precise gunplay meets unique agent abilities.',
        'developer': 'Riot Games',
        'publisher': 'Riot Games',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 7},
        'identity': {
            'field_name': 'riot_id',
            'display_name': 'Riot ID',
            'placeholder': 'PlayerName#TAG',
            'validation_regex': r'^[a-zA-Z0-9\s]{3,16}#[a-zA-Z0-9]{3,5}$',
            'help_text': 'Your Riot ID (e.g., PlayerName#TAG)'
        }
    },
    'counter-strike-2': {
        'name': 'Counter-Strike 2',
        'display_name': 'Counter-Strike 2',
        'short_code': 'CS2',
        'category': 'FPS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC'],
        'primary_color': '#f5a623',
        'secondary_color': '#1b2838',
        'description': 'The legendary tactical FPS reimagined on Source 2 engine with competitive 5v5 gameplay.',
        'developer': 'Valve Corporation',
        'publisher': 'Valve Corporation',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 7},
        'identity': {
            'field_name': 'steam_id',
            'display_name': 'Steam ID',
            'placeholder': '76561198000000000',
            'validation_regex': r'^765\d{14}$',
            'help_text': 'Your Steam ID64 (17 digits starting with 765)'
        }
    },
    'dota-2': {
        'name': 'Dota 2',
        'display_name': 'Dota 2',
        'short_code': 'DOTA2',
        'category': 'MOBA',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC'],
        'primary_color': '#c23c2a',
        'secondary_color': '#1b1b1b',
        'description': 'Competitive 5v5 MOBA with draft/ban phase and best-of-X tournament format.',
        'developer': 'Valve Corporation',
        'publisher': 'Valve Corporation',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 7},
        'identity': {
            'field_name': 'steam_id',
            'display_name': 'Steam ID',
            'placeholder': '76561198000000000',
            'validation_regex': r'^765\d{14}$',
            'help_text': 'Your Steam ID64 (17 digits starting with 765)'
        }
    },
    'efootball': {
        'name': 'eFootball',
        'display_name': 'eFootball™',
        'short_code': 'EFB',
        'category': 'SPORTS',
        'game_type': '1V1',
        'platforms': ['PC', 'Console', 'Mobile'],
        'primary_color': '#0051a5',
        'secondary_color': '#ffffff',
        'description': 'Cross-platform football simulation with 1v1 and 2v2 competitive matches.',
        'developer': 'Konami',
        'publisher': 'Konami',
        'is_featured': False,
        'roster': {'min_team_size': 1, 'max_team_size': 2},
        'identity': {
            'field_name': 'efootball_id',
            'display_name': 'Konami ID',
            'placeholder': 'YourKonamiID',
            'help_text': 'Your Konami ID username'
        }
    },
    'ea-sports-fc-26': {
        'name': 'EA Sports FC 26',
        'display_name': 'EA SPORTS FC 26',
        'short_code': 'FC26',
        'category': 'SPORTS',
        'game_type': '1V1',
        'platforms': ['PC', 'Console', 'Mobile'],  # From spec: "PC, Console, Mobile"
        'primary_color': '#00ff87',
        'secondary_color': '#000000',
        'description': 'The world\'s game - competitive 1v1 football with platform selection.',
        'developer': 'EA Sports',
        'publisher': 'Electronic Arts',
        'is_featured': True,
        'roster': {'min_team_size': 1, 'max_team_size': 1},
        'identity': {
            'field_name': 'ea_id',
            'display_name': 'EA ID',
            'placeholder': 'YourEAID / PSN / Xbox Gamertag',
            'help_text': 'Your EA ID, PSN, or Xbox Gamertag depending on platform'
        }
    },
    'mobile-legends': {
        'name': 'Mobile Legends: Bang Bang',
        'display_name': 'Mobile Legends: Bang Bang',
        'short_code': 'MLBB',
        'category': 'MOBA',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['Mobile'],
        'primary_color': '#4b69ff',
        'secondary_color': '#1a1f3a',
        'description': 'Mobile MOBA with 5v5 competitive matches and draft/ban phase.',
        'developer': 'Moonton',
        'publisher': 'Moonton',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 6},
        'identity': {
            'field_name': 'mlbb_id',
            'display_name': 'User ID + Zone ID',
            'placeholder': '123456789 (1234)',
            'validation_regex': r'^\d{7,10}\s*\(\d{4}\)$',
            'help_text': 'Your User ID + Zone ID (e.g., 123456789 (1234))'
        }
    },
    'call-of-duty-mobile': {
        'name': 'Call of Duty: Mobile',
        'display_name': 'Call of Duty®: Mobile',
        'short_code': 'CODM',
        'category': 'FPS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['Mobile'],
        'primary_color': '#ff6b00',
        'secondary_color': '#000000',
        'description': 'Mobile FPS with 5v5 competitive modes across Hardpoint, Search & Destroy, and more.',
        'developer': 'TiMi Studio Group',
        'publisher': 'Activision',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 6},
        'identity': {
            'field_name': 'codm_uid',
            'display_name': 'IGN / UID',
            'placeholder': '6812345678901234',
            'help_text': 'Your in-game UID or IGN'
        }
    },
    'free-fire': {
        'name': 'Free Fire',
        'display_name': 'Garena Free Fire',
        'short_code': 'FF',
        'category': 'BR',
        'game_type': 'BATTLE_ROYALE',
        'platforms': ['Mobile'],
        'primary_color': '#ff3b3b',
        'secondary_color': '#0e0e0e',
        'description': 'Mobile battle royale with 4-player squads and point-based tournament scoring.',
        'developer': 'Garena',
        'publisher': 'Garena',
        'is_featured': True,
        'roster': {'min_team_size': 4, 'max_team_size': 4},
        'identity': {
            'field_name': 'free_fire_id',
            'display_name': 'IGN / UID',
            'placeholder': '1234567890',
            'help_text': 'Your Free Fire UID or IGN'
        }
    },
    'pubg-mobile': {
        'name': 'PUBG Mobile',
        'display_name': 'PUBG MOBILE',
        'short_code': 'PUBGM',
        'category': 'BR',
        'game_type': 'BATTLE_ROYALE',
        'platforms': ['Mobile'],
        'primary_color': '#f2a900',
        'secondary_color': '#000000',
        'description': 'Mobile battle royale with 4-player squads, kills and placement-based scoring.',
        'developer': 'Tencent Games',
        'publisher': 'Tencent Games',
        'is_featured': True,
        'roster': {'min_team_size': 4, 'max_team_size': 4},
        'identity': {
            'field_name': 'pubg_mobile_id',
            'display_name': 'IGN / UID',
            'placeholder': '5123456789',
            'help_text': 'Your PUBG Mobile UID or IGN'
        }
    },
}

# Additional popular esports games
EXTRA_GAMES = {
    'rainbow-six-siege': {
        'name': 'Rainbow Six Siege',
        'display_name': 'Rainbow Six Siege',
        'short_code': 'R6',
        'category': 'FPS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC', 'Console'],
        'primary_color': '#0089ff',
        'secondary_color': '#131516',
        'description': 'Tactical 5v5 FPS with destructible environments and operator-based gameplay. #9 in esports prize money.',
        'developer': 'Ubisoft Montreal',
        'publisher': 'Ubisoft',
        'is_featured': True,
        'roster': {'min_team_size': 5, 'max_team_size': 7},
        'identity': {
            'field_name': 'ubisoft_username',
            'display_name': 'Ubisoft Username',
            'placeholder': 'YourUbisoftName',
            'help_text': 'Your Ubisoft Connect username'
        }
    },
    'rocket-league': {
        'name': 'Rocket League',
        'display_name': 'Rocket League',
        'short_code': 'RL',
        'category': 'SPORTS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC', 'Console'],
        'primary_color': '#0080ff',
        'secondary_color': '#1a1a1a',
        'description': 'Vehicular soccer with competitive 3v3 gameplay and official esports federation. #8 in esports prize money.',
        'developer': 'Psyonix',
        'publisher': 'Epic Games',
        'is_featured': True,
        'roster': {'min_team_size': 3, 'max_team_size': 5},
        'identity': {
            'field_name': 'epic_id',
            'display_name': 'Epic Games ID',
            'placeholder': 'YourEpicID',
            'help_text': 'Your Epic Games account name'
        }
    },
}

def update_or_create_game(slug, data):
    """Update existing game or create new one."""
    game, created = Game.objects.update_or_create(
        slug=slug,
        defaults={
            'name': data['name'],
            'display_name': data['display_name'],
            'short_code': data['short_code'],
            'category': data['category'],
            'game_type': data['game_type'],
            'platforms': data['platforms'],
            'primary_color': data['primary_color'],
            'secondary_color': data['secondary_color'],
            'description': data.get('description', ''),
            'developer': data.get('developer', ''),
            'publisher': data.get('publisher', ''),
            'is_active': True,
            'is_featured': data.get('is_featured', False),
        }
    )
    
    # Update roster config
    if 'roster' in data:
        roster_data = data['roster']
        roster_config, _ = GameRosterConfig.objects.update_or_create(
            game=game,
            defaults={
                'min_team_size': roster_data['min_team_size'],
                'max_team_size': roster_data['max_team_size'],
                'min_substitutes': 0,
                'max_substitutes': max(0, roster_data['max_team_size'] - roster_data['min_team_size']),
                'min_roster_size': roster_data['min_team_size'],
                'max_roster_size': roster_data['max_team_size'],
            }
        )
    
    # Update identity config
    if 'identity' in data:
        identity_data = data['identity']
        identity_config, _ = GamePlayerIdentityConfig.objects.update_or_create(
            game=game,
            field_name=identity_data['field_name'],
            defaults={
                'display_name': identity_data['display_name'],
                'placeholder': identity_data['placeholder'],
                'validation_regex': identity_data.get('validation_regex', ''),
                'help_text': identity_data.get('help_text', ''),
                'is_required': True,
                'field_type': 'TEXT',
                'order': 1,
            }
        )
    
    action = "✅ Created" if created else "🔄 Updated"
    return game, action

def main():
    print("🚀 Rebuilding games database from Game_Spec.md...")
    print("=" * 70)
    print()
    
    # Step 1: Delete games NOT in spec
    all_games = Game.objects.all()
    spec_slugs = list(SPEC_GAMES.keys()) + list(EXTRA_GAMES.keys())
    
    deleted_count = 0
    for game in all_games:
        if game.slug not in spec_slugs:
            print(f"🗑️  Deleting: {game.display_name} ({game.slug}) - Not in Game_Spec.md")
            game.delete()
            deleted_count += 1
    
    if deleted_count == 0:
        print("✅ No games to delete - all current games are in spec")
    print()
    
    # Step 2: Create/Update games from spec
    print("📝 Games from Game_Spec.md:")
    print("-" * 70)
    created_count = 0
    updated_count = 0
    
    for slug, game_data in SPEC_GAMES.items():
        game, action = update_or_create_game(slug, game_data)
        print(f"{action} {game.display_name} ({slug})")
        if "Created" in action:
            created_count += 1
        else:
            updated_count += 1
    
    print()
    print("⭐ Additional popular esports games:")
    print("-" * 70)
    
    for slug, game_data in EXTRA_GAMES.items():
        game, action = update_or_create_game(slug, game_data)
        print(f"{action} {game.display_name} ({slug})")
        if "Created" in action:
            created_count += 1
        else:
            updated_count += 1
    
    print()
    print("=" * 70)
    print(f"🎉 Rebuild complete!")
    print(f"   🗑️  Deleted: {deleted_count} games")
    print(f"   ✅ Created: {created_count} games")
    print(f"   🔄 Updated: {updated_count} games")
    print(f"   📊 Total active games: {Game.objects.filter(is_active=True).count()}")
    print()
    print("✨ All games (in order):")
    games = Game.objects.filter(is_active=True).order_by('name')
    for i, game in enumerate(games, 1):
        featured = "⭐" if game.is_featured else "  "
        platforms = ", ".join(game.platforms)
        print(f"{featured} {i}. {game.display_name} ({game.slug}) - {platforms}")

if __name__ == '__main__':
    main()
