"""
Career Tab Service - Phase UP 5
Provides backend data for user profile Career Tab without touching other tabs.

Functions:
- get_passport_card_view(): Abstraction map for passport rendering (ALL games, one renderer)
- get_linked_games(): Returns ordered list of user's games (primary first)
- get_game_passport(): Returns GameProfile for specific game
- get_matches_played_count(): Counts COMPLETED + FORFEIT matches (SOLO + TEAM)
- get_team_ranking(): Gets user's team ranking with ELO and tier
- get_team_affiliation_history(): Returns team membership history
- get_achievements(): Returns tournament history with placements
- get_display_attributes(): Converts GameProfile to display-ready attributes
"""

from typing import List, Dict, Optional, Any, Callable
from django.db.models import Q, Count, Sum
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
import os

User = get_user_model()


# ============================================================
# GAME_DISPLAY_CONFIG - Single Source of Truth
# Follows Career Page Design.md exactly
# ============================================================

GAME_DISPLAY_CONFIG = {
    'valorant': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'Riot ID',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Region',
            'context_field': lambda p: getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Current Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {'show_id': False},
        },
        'attributes_sidebar': [
            {'label': 'Main Role', 'resolver': lambda p: p.main_role or getattr(p, 'metadata', {}).get('role') or '--', 'hide_if_empty': True},
            {'label': 'Peak Rank', 'resolver': lambda p: getattr(p, 'metadata', {}).get('peak_rank') or '--', 'hide_if_empty': True},
        ],
    },
    'cs2': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Region',
            'context_field': lambda p: getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Rating',
            'standing_field': lambda p: getattr(p, 'metadata', {}).get('premier_rating') or p.rank_name or 'Unranked',
            'privacy_rules': {'hide_steam_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Role', 'resolver': lambda p: p.main_role or '--', 'hide_if_empty': True},
            {'label': 'Steam Link', 'resolver': lambda p: getattr(p, 'metadata', {}).get('steam_link') or None, 'hide_if_empty': True},
        ],
    },
    'codm': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Region',
            'context_field': lambda p: getattr(p, 'region', None) or 'Global',
        },
        'standing': {
            'standing_label': 'Rank',
            'standing_field': lambda p: p.rank_name or getattr(p, 'metadata', {}).get('mp_rank') or 'Unranked',
            'privacy_rules': {'hide_uid': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Mode', 'resolver': lambda p: getattr(p, 'metadata', {}).get('main_mode') or '--', 'hide_if_empty': True},
            {'label': 'BR Rank', 'resolver': lambda p: getattr(p, 'metadata', {}).get('br_rank') or '--', 'hide_if_empty': True},
        ],
    },
    'dota2': {
        'category': 'tactician',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Server',
            'context_field': lambda p: getattr(p, 'server', None) or getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'MMR Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {'hide_steam_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Role', 'resolver': lambda p: p.main_role or '--', 'hide_if_empty': True},
            {'label': 'Steam Link', 'resolver': lambda p: getattr(p, 'metadata', {}).get('steam_link') or None, 'hide_if_empty': True},
        ],
    },
    'mlbb': {
        'category': 'tactician',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Region',
            'context_field': lambda p: getattr(p, 'server', None) or getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {'hide_account_id': True, 'hide_server_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Role', 'resolver': lambda p: p.main_role or '--', 'hide_if_empty': True},
        ],
    },
    'pubgm': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Server',
            'context_field': lambda p: getattr(p, 'server', None) or getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Current Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {'show_character_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Mode', 'resolver': lambda p: getattr(p, 'metadata', {}).get('main_mode') or '--', 'hide_if_empty': True},
            {'label': 'Character ID', 'resolver': lambda p: getattr(p, 'metadata', {}).get('character_id') or '--', 'hide_if_empty': False},
            {'label': 'Server', 'resolver': lambda p: getattr(p, 'server', None) or '--', 'hide_if_empty': True},
        ],
    },
    'freefire': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Server',
            'context_field': lambda p: getattr(p, 'server', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Current Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {'show_player_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Player ID', 'resolver': lambda p: getattr(p, 'metadata', {}).get('player_id') or '--', 'hide_if_empty': False},
            {'label': 'Server', 'resolver': lambda p: getattr(p, 'server', None) or '--', 'hide_if_empty': True},
            {'label': 'Rank', 'resolver': lambda p: p.rank_name or '--', 'hide_if_empty': True},
        ],
    },
    'efootball': {
        'category': 'athlete',
        'identity': {
            'primary_label': 'Username',
            'primary_field': lambda p: getattr(p, 'metadata', {}).get('username') or p.in_game_name or p.ign or 'N/A',
            'context_label': 'Platform',
            'context_field': lambda p: getattr(p, 'platform', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Division',
            'standing_field': lambda p: getattr(p, 'metadata', {}).get('division') or p.rank_name or 'Unranked',
            'privacy_rules': {'hide_konami_id': True, 'hide_user_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Team Name', 'resolver': lambda p: getattr(p, 'metadata', {}).get('team_name') or '--', 'hide_if_empty': True},
            {'label': 'Platform', 'resolver': lambda p: getattr(p, 'platform', None) or '--', 'hide_if_empty': True},
            {'label': 'Division', 'resolver': lambda p: getattr(p, 'metadata', {}).get('division') or '--', 'hide_if_empty': True},
        ],
    },
    'ea-fc': {
        'category': 'athlete',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Platform',
            'context_field': lambda p: getattr(p, 'platform', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Division',
            'standing_field': lambda p: getattr(p, 'metadata', {}).get('division') or p.rank_name or 'Unranked',
            'privacy_rules': {'hide_ea_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Mode', 'resolver': lambda p: getattr(p, 'metadata', {}).get('main_mode') or '--', 'hide_if_empty': True},
            {'label': 'Platform', 'resolver': lambda p: getattr(p, 'platform', None) or '--', 'hide_if_empty': True},
            {'label': 'Division', 'resolver': lambda p: getattr(p, 'metadata', {}).get('division') or '--', 'hide_if_empty': True},
        ],
    },
    'rocketleague': {
        'category': 'athlete',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Platform',
            'context_field': lambda p: getattr(p, 'platform', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Highest Rank',
            'standing_field': lambda p: getattr(p, 'metadata', {}).get('highest_rank') or p.rank_name or 'Unranked',
            'privacy_rules': {'hide_epic_id': True},
        },
        'attributes_sidebar': [
            {'label': 'Main Mode', 'resolver': lambda p: getattr(p, 'metadata', {}).get('main_mode') or '--', 'hide_if_empty': True},
            {'label': 'Platform', 'resolver': lambda p: getattr(p, 'platform', None) or '--', 'hide_if_empty': True},
            {'label': 'Rank', 'resolver': lambda p: getattr(p, 'metadata', {}).get('highest_rank') or '--', 'hide_if_empty': True},
        ],
    },
    'r6siege': {
        'category': 'shooter',
        'identity': {
            'primary_label': 'In-Game Name',
            'primary_field': lambda p: p.in_game_name or p.ign or 'N/A',
            'context_label': 'Region',
            'context_field': lambda p: getattr(p, 'region', None) or 'Not Set',
        },
        'standing': {
            'standing_label': 'Current Rank',
            'standing_field': lambda p: p.rank_name or 'Unranked',
            'privacy_rules': {},
        },
        'attributes_sidebar': [
            {'label': 'Main Role', 'resolver': lambda p: p.main_role or '--', 'hide_if_empty': True},
            {'label': 'Rank', 'resolver': lambda p: p.rank_name or '--', 'hide_if_empty': True},
        ],
    },
}


class CareerTabService:
    """Service layer for Career Tab data (isolated from other profile tabs)."""
    
    @staticmethod
    def resolve_game_assets(game) -> Dict[str, Optional[str]]:
        """
        Resolve game assets (logo, banner) with proper verification.
        
        Priority:
        1. Game model fields (logo, icon, banner, cover)
        2. Static files if they exist (verify with finders.find())
        3. None if nothing found
        
        Args:
            game: Game instance
        
        Returns:
            dict with keys: logo_url, banner_url (or None)
        """
        logo_url = None
        banner_url = None
        
        if not game:
            return {'logo_url': None, 'banner_url': None}
        
        # Logo resolution
        if game.logo:
            logo_url = game.logo.url
        elif game.icon:
            logo_url = game.icon.url
        else:
            # Check if static file exists
            static_logo = f"images/games/{game.slug}-logo.png"
            if finders.find(static_logo):
                logo_url = f"/static/{static_logo}"
        
        # Banner resolution
        if game.banner:
            banner_url = game.banner.url
        elif hasattr(game, 'cover') and game.cover:
            banner_url = game.cover.url
        else:
            # Check if static file exists
            static_banner = f"images/games/{game.slug}-banner.jpg"
            if finders.find(static_banner):
                banner_url = f"/static/{static_banner}"
            else:
                # Try .png extension
                static_banner_png = f"images/games/{game.slug}-banner.png"
                if finders.find(static_banner_png):
                    banner_url = f"/static/{static_banner_png}"
        
        return {
            'logo_url': logo_url,
            'banner_url': banner_url
        }
    
    @staticmethod
    def get_matches_played(user, game) -> int:
        """
        Calculate matches played from Tournament app participation.
        Uses Match and TeamTournamentRegistration models.
        
        Args:
            user: User instance
            game: Game instance or game_slug string
        
        Returns:
            int: Total matches played (0 if tournament ops not available)
        """
        try:
            from apps.matches.models import Match
            from apps.organizations.models import TeamMembership, Team
            from apps.games.models import Game
            
            game_slug = game.slug if hasattr(game, 'slug') else game
            
            # Count solo/duo matches where user participated
            solo_matches = Match.objects.filter(
                Q(player1__user=user) | Q(player2__user=user),
                game__slug=game_slug,
                status__in=['COMPLETED', 'FORFEIT']
            ).count()
            
            # Count team matches via team membership
            user_teams = Team.objects.filter(
                vnext_memberships__user=user,
                game_id__in=Game.objects.filter(slug=game_slug).values('id')
            ).values_list('id', flat=True)
            
            team_matches = Match.objects.filter(
                Q(team1__id__in=user_teams) | Q(team2__id__in=user_teams),
                game__slug=game_slug,
                status__in=['COMPLETED', 'FORFEIT']
            ).count()
            
            return solo_matches + team_matches
        except Exception:
            # If tournament system not fully implemented, return 0
            return 0
    
    @staticmethod
    def get_stat_tiles_data(passport, game, user) -> List[Dict[str, Any]]:
        """
        Generate stat tiles based on game category (shooter/tactician/athlete).
        
        Args:
            passport: GameProfile instance
            game: Game instance
            user: User instance
        
        Returns:
            List of 4 stat tile dicts with label, value, color_class
        """
        game_slug = game.slug if hasattr(game, 'slug') else str(game)
        config = GAME_DISPLAY_CONFIG.get(game_slug, {})
        category = config.get('category', 'shooter')
        
        metadata = getattr(passport, 'metadata', {}) or {}
        
        if category == 'shooter':
            # Shooter UI: K/D, Win Rate, Tournaments, Bounties Won
            kd = getattr(passport, 'kd_ratio', None) or metadata.get('kd_ratio') or '--'
            win_rate = getattr(passport, 'win_rate', None) or metadata.get('win_rate') or '--'
            
            # Count tournaments/achievements
            try:
                from apps.user_profile.models import Achievement
                tournaments = Achievement.objects.filter(
                    user=user,
                    game_slug=game_slug
                ).count()
            except:
                tournaments = 0
            
            # Count bounties won
            try:
                from apps.user_profile.models import Bounty
                from apps.user_profile.models.bounties import BountyStatus
                bounties_won = Bounty.objects.filter(
                    winner=user,
                    status=BountyStatus.COMPLETED,
                    game__slug=game_slug
                ).count()
            except:
                bounties_won = 0
            
            return [
                {'label': 'K/D', 'value': kd, 'color_class': 'game-red'},
                {'label': 'Win Rate', 'value': f"{win_rate}%" if isinstance(win_rate, (int, float)) else win_rate, 'color_class': 'game-blue'},
                {'label': 'Tournaments', 'value': tournaments, 'color_class': 'game-yellow'},
                {'label': 'Bounties Won', 'value': f"{bounties_won:,}" if bounties_won else '0', 'color_class': 'game-green'},
            ]
        
        elif category == 'tactician':
            # Tactician UI: KDA, GPM, Hero Pool, Tournaments
            kda = metadata.get('kda') or metadata.get('kd_ratio') or '--'
            gpm = metadata.get('gpm') or '--'
            hero_pool = metadata.get('hero_pool') or metadata.get('champion_pool') or '--'
            
            try:
                from apps.user_profile.models import Achievement
                tournaments = Achievement.objects.filter(user=user, game_slug=game_slug).count()
            except:
                tournaments = 0
            
            return [
                {'label': 'KDA', 'value': kda, 'color_class': 'game-purple'},
                {'label': 'GPM', 'value': gpm, 'color_class': 'game-blue'},
                {'label': 'Hero Pool', 'value': hero_pool, 'color_class': 'game-yellow'},
                {'label': 'Tournaments', 'value': tournaments, 'color_class': 'game-green'},
            ]
        
        elif category == 'athlete':
            # Athlete UI: Goals, Assists, Win Rate, Clean Sheets/Form
            goals = metadata.get('goals_scored') or metadata.get('goals') or 0
            assists = metadata.get('assists') or 0
            win_rate = metadata.get('win_rate') or getattr(passport, 'win_rate', None) or '--'
            clean_sheets = metadata.get('clean_sheets') or metadata.get('form') or '--'
            
            return [
                {'label': 'Goals', 'value': goals, 'color_class': 'game-green'},
                {'label': 'Assists', 'value': assists, 'color_class': 'game-blue'},
                {'label': 'Win Rate', 'value': f"{win_rate}%" if isinstance(win_rate, (int, float)) else win_rate, 'color_class': 'game-yellow'},
                {'label': 'Form', 'value': clean_sheets, 'color_class': 'game-red'},
            ]
        
        # Fallback: generic stats
        return [
            {'label': 'Matches', 'value': CareerTabService.get_matches_played(user, game), 'color_class': 'game-blue'},
            {'label': 'Rank', 'value': passport.rank_name or 'Unranked', 'color_class': 'game-yellow'},
            {'label': 'K/D', 'value': getattr(passport, 'kd_ratio', '--'), 'color_class': 'game-red'},
            {'label': 'Win Rate', 'value': getattr(passport, 'win_rate', '--'), 'color_class': 'game-green'},
        ]
    
    @staticmethod
    def get_passport_card_view(passport, game) -> Dict[str, Any]:
        """
        Generate passport card view data with game-specific abstraction.
        
        This is the SINGLE renderer for all games - no per-game templates needed.
        Maps game-specific fields to common display structure.
        
        Args:
            passport: GameProfile instance
            game: Game instance
        
        Returns:
            dict with keys: game, identity, standing, stats
        """
        from django.conf import settings
        
        if not passport or not game:
            return None
        
        # Game info with real media URLs + static fallback
        logo_url = None
        if game.logo:
            logo_url = game.logo.url
        elif game.icon:
            logo_url = game.icon.url
        else:
            # Fallback to static convention: /static/images/games/{slug}-logo.png
            logo_url = f"/static/images/games/{game.slug}-logo.png"
        
        bg_url = None
        if game.banner:
            bg_url = game.banner.url
        else:
            # Fallback to static convention: /static/images/games/{slug}-banner.jpg
            bg_url = f"/static/images/games/{game.slug}-banner.jpg"
        
        game_data = {
            'slug': game.slug,
            'name': game.display_name if hasattr(game, 'display_name') else game.name,
            'logo_url': logo_url,
            'bg_url': bg_url,
        }
        
        # Identity section - game-specific mapping
        identity = CareerTabService._map_identity_fields(passport, game)
        
        # Standing section with rank icon fallback
        rank_icon_url = None
        if hasattr(passport, 'rank_image') and getattr(passport, 'rank_image'):
            rank_icon_url = getattr(passport, 'rank_image').url
        elif passport.rank_tier and passport.rank_tier > 0:
            # Fallback to static rank icons: /static/images/ranks/{game}/{tier}.png
            rank_icon_url = f"/static/images/ranks/{game.slug}/tier-{passport.rank_tier}.png"
        
        standing = {
            'primary_label': 'Current Standing',
            'primary_value': passport.rank_name or 'Unranked',
            'rank_icon_url': rank_icon_url,
            'secondary_line': None  # Will be filled by team ranking if available
        }
        
        # Stats - computed separately
        stats = {
            'matches_played': 0,  # Filled by calling service
            'team_ranking': None  # Filled by calling service
        }
        
        return {
            'game': game_data,
            'identity': identity,
            'standing': standing,
            'stats': stats
        }
    
    @staticmethod
    def _map_identity_fields(passport, game) -> Dict[str, Any]:
        """
        Map GameProfile passport fields to display identity based on game type.
        
        Privacy rules:
        - DO NOT show UIDs, Character IDs, Konami IDs (private login credentials)
        - Show only public-facing identifiers
        
        Returns:
            dict with primary_label, primary_value, secondary_label, secondary_value, sub_id_label, sub_id_value
        """
        game_slug = game.slug.lower()
        
        # Valorant: Riot ID + Region
        if 'valorant' in game_slug or 'val' == game_slug:
            return {
                'primary_label': 'Riot ID',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Region',
                'secondary_value': getattr(passport, 'region', None) or 'Not Set',
                'sub_id_label': None,
                'sub_id_value': None
            }
        
        # PUBG: Show In-Game Name + Server + Character ID (public identifier)
        elif 'pubg' in game_slug:
            # Check metadata for character_id
            metadata = getattr(passport, 'metadata', {}) or {}
            character_id = metadata.get('character_id') or metadata.get('player_id')
            
            return {
                'primary_label': 'In-Game Name',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Server',
                'secondary_value': getattr(passport, 'server', None) or getattr(passport, 'region', None) or 'Not Set',
                'sub_id_label': 'Character ID' if character_id else None,
                'sub_id_value': character_id
            }
        
        # eFootball: Show Username + Platform (DO NOT show Konami ID or User ID)
        elif 'efootball' in game_slug or 'efoot' in game_slug or 'pes' in game_slug:
            platform = getattr(passport, 'platform', None) or 'Not Set'
            return {
                'primary_label': 'Username',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Platform',
                'secondary_value': platform,
                'sub_id_label': None,  # DO NOT show Konami ID (private)
                'sub_id_value': None
            }
        
        # Call of Duty Mobile: Hide UID, show In-Game Name + Region
        elif 'codm' in game_slug or 'call-of-duty' in game_slug:
            return {
                'primary_label': 'In-Game Name',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Region',
                'secondary_value': getattr(passport, 'region', None) or 'Not Set',
                'sub_id_label': None,  # Hide UID (private)
                'sub_id_value': None
            }
        
        # Free Fire: Show Player ID (public identifier)
        elif 'freefire' in game_slug or 'free-fire' in game_slug or 'ff' == game_slug:
            # Check metadata for player_id
            metadata = getattr(passport, 'metadata', {}) or {}
            player_id = metadata.get('player_id') or metadata.get('ff_id')
            
            return {
                'primary_label': 'In-Game Name',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Server',
                'secondary_value': getattr(passport, 'region', None) or 'Not Set',
                'sub_id_label': 'Player ID' if player_id else None,
                'sub_id_value': player_id
            }
        
        # Default fallback for other games
        else:
            return {
                'primary_label': 'In-Game Name',
                'primary_value': passport.in_game_name or passport.ign or 'N/A',
                'secondary_label': 'Region',
                'secondary_value': getattr(passport, 'region', None) or 'Not Set',
                'sub_id_label': None,
                'sub_id_value': None
            }
    
    @staticmethod
    def get_linked_games(user_profile) -> List[Dict[str, Any]]:
        """
        Get ordered list of user's linked games.
        
        PRIMARY GAME RESOLUTION (4-tier fallback):
        1. primary_team.game (if primary_team is set)
        2. user_profile.primary_game (FK)
        3. passport.is_primary flag
        4. First pinned/sorted passport
        
        Args:
            user_profile: UserProfile instance
        
        Returns:
            List of dicts with game data and passport:
            [
                {
                    'game': Game instance,
                    'game_slug': str,
                    'game_name': str,
                    'game_icon_url': str,
                    'passport': GameProfile instance,
                    'is_primary': bool,
                    'primary_source': str  # DEBUG: 'team', 'direct', 'flag', 'fallback'
                },
                ...
            ]
        """
        from apps.user_profile.models import GameProfile
        from apps.games.models import Game
        import logging
        
        logger = logging.getLogger(__name__)
        
        # === TYPE-SAFE GAME RESOLVER ===
        def resolve_game_obj(value) -> Optional[Game]:
            """
            Convert any value (Game instance, slug string, int pk) to Game instance.
            
            Args:
                value: Game instance, str slug, int pk, or None
            
            Returns:
                Game instance or None (never throws)
            """
            if value is None:
                return None
            
            # Already a Game instance
            if isinstance(value, Game):
                return value
            
            # String slug (most common for Team.game CharField)
            if isinstance(value, str):
                if not value.strip():
                    return None
                try:
                    game = Game.objects.filter(slug=value).first()
                    logger.debug(f"[Career] resolve_game_obj: slug '{value}' â†’ {game.slug if game else 'NOT_FOUND'}")
                    return game
                except Exception as e:
                    logger.warning(f"[Career] resolve_game_obj failed for slug '{value}': {e}")
                    return None
            
            # Integer PK
            if isinstance(value, int):
                try:
                    game = Game.objects.filter(pk=value).first()
                    logger.debug(f"[Career] resolve_game_obj: pk {value} â†’ {game.slug if game else 'NOT_FOUND'}")
                    return game
                except Exception as e:
                    logger.warning(f"[Career] resolve_game_obj failed for pk {value}: {e}")
                    return None
            
            # Unknown type
            logger.warning(f"[Career] resolve_game_obj: unknown type {type(value).__name__} for value: {value}")
            return None
        
        # Get all active public game profiles for user (OPTIMIZED: select_related game)
        passports_qs = GameProfile.objects.filter(
            user=user_profile.user,
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE
        ).select_related('game').order_by('-is_pinned', 'pinned_order', 'sort_order', '-updated_at')
        
        # === PRIMARY GAME RESOLUTION (4-tier fallback with type safety) ===
        primary_game = None
        primary_source = None
        primary_game_slug = None
        
        # 1. Try primary_team.game (HIGHEST PRIORITY)
        try:
            primary_team = getattr(user_profile, 'primary_team', None)
            if primary_team and hasattr(primary_team, 'game'):
                raw_value = primary_team.game
                logger.debug(f"[Career] primary_team.game raw type: {type(raw_value).__name__}, value: {raw_value}")
                primary_game = resolve_game_obj(raw_value)
                if primary_game:
                    primary_source = 'team'
                    primary_game_slug = primary_game.slug
                    logger.info(f"[Career] PRIMARY_RESOLUTION: by primary_team ({primary_team.name} â†’ {primary_game_slug})")
        except Exception as e:
            logger.warning(f"[Career] primary_team resolution failed: {e}")
        
        # 2. Fallback: user_profile.primary_game FK
        if not primary_game:
            try:
                raw_value = getattr(user_profile, 'primary_game', None)
                if raw_value:
                    logger.debug(f"[Career] primary_game FK raw type: {type(raw_value).__name__}, value: {raw_value}")
                    primary_game = resolve_game_obj(raw_value)
                    if primary_game:
                        primary_source = 'direct'
                        primary_game_slug = primary_game.slug
                        logger.info(f"[Career] PRIMARY_RESOLUTION: by primary_game FK ({primary_game_slug})")
            except Exception as e:
                logger.warning(f"[Career] primary_game FK resolution failed: {e}")
        
        # 3. Fallback: passport.is_primary flag
        if not primary_game:
            for passport in passports_qs:
                if getattr(passport, 'is_primary', False):
                    primary_game = passport.game
                    primary_source = 'flag'
                    primary_game_slug = primary_game.slug
                    logger.info(f"[Career] PRIMARY_RESOLUTION: by passport flag ({primary_game_slug})")
                    break
        
        # 4. Fallback: first pinned/sorted passport
        if not primary_game and passports_qs.exists():
            primary_game = passports_qs.first().game
            primary_source = 'fallback'
            primary_game_slug = primary_game.slug
            logger.info(f"[Career] PRIMARY_RESOLUTION: fallback to first passport ({primary_game_slug})")
        
        linked_games = []
        primary_passport = None
        
        # Find primary passport (TYPE-SAFE comparison)
        if primary_game:
            for passport in passports_qs:
                # Safe comparison: compare by slug (works even if primary_game has no .id)
                if passport.game.slug == primary_game_slug:
                    primary_passport = passport
                    break
        
        # Build ordered list: PRIMARY FIRST, then others
        if primary_passport:
            game = primary_passport.game
            linked_games.append({
                'game': game,
                'game_slug': game.slug,
                'game_name': game.display_name,
                'game_icon_url': game.icon.url if game.icon else f"/static/images/games/{game.slug}-logo.png",
                'passport': primary_passport,
                'is_primary': True,
                'primary_source': primary_source  # DEBUG field
            })
        
        # Add remaining passports
        for passport in passports_qs:
            if primary_passport and passport.id == primary_passport.id:
                continue
            
            game = passport.game
            linked_games.append({
                'game': game,
                'game_slug': game.slug,
                'game_name': game.display_name,
                'game_icon_url': game.icon.url if game.icon else f"/static/images/games/{game.slug}-logo.png",
                'passport': passport,
                'is_primary': False,
                'primary_source': None
            })
        
        return linked_games
    
    @staticmethod
    def get_game_passport(user_profile, game) -> Optional[Any]:
        """
        Get user's GameProfile (passport) for specific game.
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            GameProfile instance or None
        """
        from apps.user_profile.models import GameProfile
        
        try:
            return GameProfile.objects.get(
                user=user_profile.user,
                game=game,
                visibility=GameProfile.VISIBILITY_PUBLIC,
                status=GameProfile.STATUS_ACTIVE
            )
        except GameProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_matches_played_count(user_profile, game) -> int:
        """
        Count total matches played by user for specific game.
        
        Handles both SOLO and TEAM tournaments:
        - SOLO: Count matches where user is participant
        - TEAM: Count matches where user's active team is participant
        
        Only counts COMPLETED and FORFEIT states (finalized matches).
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            int: Total matches played (0 if match system not available)
        """
        try:
            from apps.tournaments.models import Match
            from apps.organizations.models import TeamMembership
            from apps.games.models import Game
        except ImportError:
            # Match model not available yet - return 0 safely
            return 0
        
        user = user_profile.user
        game_slug = game.slug
        
        # Count SOLO matches
        try:
            solo_matches = Match.objects.filter(
                Q(participant1_id=user.id) | Q(participant2_id=user.id),
                tournament__game__slug=game_slug,
                tournament__participation_type='solo',
                state__in=[Match.COMPLETED, Match.FORFEIT]
            ).count()
        except Exception:
            solo_matches = 0
        
        # Count TEAM matches
        team_matches = 0
        try:
            # Get user's active team for this game
            active_membership = TeamMembership.objects.filter(
                user=user,
                team__game_id__in=Game.objects.filter(slug=game_slug).values('id'),
                status='ACTIVE'
            ).select_related('team').first()
            
            if active_membership:
                team_id = active_membership.team.id
                team_matches = Match.objects.filter(
                    Q(participant1_id=team_id) | Q(participant2_id=team_id),
                    tournament__game__slug=game_slug,
                    tournament__participation_type='team',
                    state__in=[Match.COMPLETED, Match.FORFEIT]
                ).count()
        except Exception:
            team_matches = 0
        
        return solo_matches + team_matches
    
    @staticmethod
    def get_team_ranking(user_profile, game) -> Optional[Dict[str, Any]]:
        """
        Get user's current team ranking for specific game.
        
        Returns team data with ELO rating, tier, and rank position.
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            dict or None:
            {
                'team_id': int,
                'team_name': str,
                'team_tag': str,
                'team_slug': str,
                'rank': int or None (1 = top team),
                'elo_rating': int,
                'tier': str ('bronze', 'silver', 'gold', 'diamond', 'crown'),
                'wins': int,
                'losses': int,
                'games_played': int
            }
        """
        try:
            from apps.organizations.models import TeamMembership
            from apps.leaderboards.models import TeamRanking
            from apps.tournament_ops.dtos.analytics import TierBoundaries
        except ImportError:
            return None
        
        # Get user's active team for this game
        try:
            membership = TeamMembership.objects.filter(
                user=user_profile.user,
                team__game_id=game.id,
                status='ACTIVE'
            ).select_related('team').first()
        except Exception:
            return None
        
        if not membership:
            return None
        
        team = membership.team
        
        # Get team ranking
        try:
            ranking = TeamRanking.objects.get(team=team, game_slug=game.slug)
            
            # Calculate tier from ELO
            tier = TierBoundaries.calculate_tier(ranking.elo_rating)
            
            # Calculate rank if not set
            rank = ranking.rank
            if rank is None:
                rank = TeamRanking.objects.filter(
                    game_slug=game.slug,
                    elo_rating__gt=ranking.elo_rating
                ).count() + 1
            
            return {
                'team_id': team.id,
                'team_name': team.name,
                'team_tag': team.tag,
                'team_slug': team.slug,
                'rank': rank,
                'elo_rating': ranking.elo_rating,
                'tier': tier,
                'wins': ranking.wins,
                'losses': ranking.losses,
                'games_played': ranking.games_played,
            }
        except TeamRanking.DoesNotExist:
            # Team has no ranking yet - return default
            return {
                'team_id': team.id,
                'team_name': team.name,
                'team_tag': team.tag,
                'team_slug': team.slug,
                'rank': None,
                'elo_rating': 1200,  # Default ELO
                'tier': 'bronze',
                'wins': 0,
                'losses': 0,
                'games_played': 0,
            }
        except Exception:
            return None
    
    @staticmethod
    def get_team_affiliation_history(user_profile, game) -> List[Dict[str, Any]]:
        """
        Get user's team membership history for specific game.
        
        Returns both active and past team affiliations with role and duration.
        Uses TeamMembership model filtered by game.
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            List of dicts (JSON-safe):
            [
                {
                    'team_id': int,
                    'team_name': str,
                    'team_tag': str,
                    'team_slug': str,
                    'team_logo_url': str or None,
                    'team_url': str or None,  # URL to team profile page
                    'role': str ('Captain', 'Member', etc.),
                    'is_active': bool,
                    'joined_at': str (ISO format),
                    'left_at': str or None,
                    'duration_label': str ('Active' or 'Jan 2025 â€“ Mar 2025')
                },
                ...
            ]
        """
        try:
            from apps.organizations.models import TeamMembership
            from django.utils import timezone
            from django.urls import reverse
            from datetime import datetime
            import logging
            
            logger = logging.getLogger(__name__)
        except ImportError:
            return []
        
        try:
            # Query TeamMembership - filter by game via team.game field
            memberships = TeamMembership.objects.filter(
                user=user_profile.user,
                team__game_id=game.id
            ).select_related('team').order_by('-joined_at')
            
            history = []
            for membership in memberships:
                # Determine if active
                is_active = (membership.status == 'ACTIVE' and not membership.left_at)
                
                # Calculate duration label
                if is_active:
                    duration_label = 'Active'
                elif membership.left_at and membership.joined_at:
                    # Format: "Jan 2025 â€“ Mar 2025"
                    start = membership.joined_at.strftime('%b %Y')
                    end = membership.left_at.strftime('%b %Y')
                    duration_label = f"{start} â€“ {end}"
                elif membership.joined_at:
                    duration_label = f"Since {membership.joined_at.strftime('%b %Y')}"
                else:
                    duration_label = 'Unknown'
                
                # Get team logo URL
                team_logo_url = None
                if hasattr(membership.team, 'logo') and membership.team.logo:
                    try:
                        team_logo_url = membership.team.logo.url
                    except Exception:
                        team_logo_url = None
                
                # Build team URL (defensive with reverse)
                team_url = None
                team_slug = getattr(membership.team, 'slug', None)
                if team_slug:
                    try:
                        team_url = reverse('organizations:team_detail', kwargs={'team_slug': team_slug})
                    except Exception as e:
                        logger.debug(f"[Career] Could not build team URL for slug '{team_slug}': {e}")
                        team_url = None
                
                # Role display - use get_role_display() for nice labels
                role_raw = getattr(membership, 'role', 'PLAYER')
                role_display = membership.get_role_display() if hasattr(membership, 'get_role_display') else role_raw
                
                # Build status badge (Active, Past, etc.)
                status_badge = 'Active' if is_active else 'Past'
                
                history.append({
                    'team_id': membership.team.id,
                    'team_name': membership.team.name,
                    'team_tag': getattr(membership.team, 'tag', membership.team.name[:3].upper()),
                    'team_slug': team_slug or f"team-{membership.team.id}",
                    'team_logo_url': team_logo_url,
                    'team_url': team_url,  # URL to team profile page
                    'role': role_raw,  # Raw value (OWNER, PLAYER, etc.)
                    'team_role_label': role_display,  # Nice label (Owner/Captain, Player, etc.)
                    'status_badge': status_badge,
                    'is_active': is_active,
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
                    'left_at': membership.left_at.isoformat() if membership.left_at else None,
                    'duration_label': duration_label
                })
            
            return history
        except Exception as e:
            # Graceful fallback - don't crash Career Tab
            print(f"Error fetching team history: {e}")
            return []
    
    @staticmethod
    def get_achievements(user_profile, game) -> List[Dict[str, Any]]:
        """
        Get user's tournament achievements for specific game.
        
        Returns tournament placements with prizes and tier information.
        Uses Registration model to find user's participation.
        If tier missing, infers from is_official/is_featured flags.
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            List of dicts (JSON-safe, empty list if tournament ops incomplete):
            [
                {
                    'tournament_id': int,
                    'tournament_name': str,
                    'tournament_slug': str,
                    'tournament_tier': str ('OPEN', 'GOLD', 'DIAMOND', 'CROWN') or None,
                    'date': str (ISO format),
                    'placement': int or None (1, 2, 3, etc.),
                    'placement_label': str ('1st Place', 'Participated', etc.),
                    'team_name': str or None,
                    'result': str or None ('3 : 0', 'Win', 'Loss'),
                    'prize_amount': float or None,
                    'prize_currency': str ('USD', 'BDT', etc.) or None
                },
                ...
            ]
        """
        try:
            from apps.tournaments.models import Registration, Tournament
        except ImportError:
            # Tournament system not available - return empty
            return []
        
        try:
            # Get user's tournament registrations for this game
            registrations = Registration.objects.filter(
                user=user_profile.user,
                tournament__game__slug=game.slug,
                status__in=['confirmed', 'checked_in', 'completed']
            ).select_related('tournament').order_by('-tournament__tournament_start')[:50]  # Limit to recent 50 (team is optional, don't select_related)
            
            achievements = []
            for reg in registrations:
                tournament = reg.tournament
                
                # Infer tier if not in attributes
                tier = None
                if hasattr(tournament, 'attributes') and tournament.attributes:
                    tier = tournament.attributes.get('tier')
                if not tier:
                    # Fallback: infer from flags
                    if getattr(tournament, 'is_official', False):
                        tier = 'DIAMOND'
                    elif getattr(tournament, 'is_featured', False):
                        tier = 'GOLD'
                    else:
                        tier = 'OPEN'
                
                # Placement
                placement = getattr(reg, 'placement', None) or getattr(reg, 'final_standing', None)
                if placement:
                    if placement == 1:
                        placement_label = '1st Place'
                    elif placement == 2:
                        placement_label = '2nd Place'
                    elif placement == 3:
                        placement_label = '3rd Place'
                    else:
                        placement_label = f"{placement}th Place"
                else:
                    placement_label = 'Participated'
                
                # Team name
                team_name = None
                if reg.team:
                    team_name = reg.team.name
                elif reg.user:
                    team_name = reg.user.username
                
                # Result (score text or status)
                result = None
                if hasattr(reg, 'match_result') and reg.match_result:
                    result = reg.match_result  # e.g., "3 : 0"
                elif hasattr(reg, 'status') and reg.status:
                    result = reg.status.title()  # e.g., "Completed", "Forfeit"
                
                # Prize
                prize_amount = None
                prize_currency = None
                if hasattr(reg, 'prize_won') and reg.prize_won:
                    prize_amount = float(reg.prize_won)
                    prize_currency = getattr(tournament, 'prize_currency', 'USD')
                
                achievements.append({
                    'tournament_id': tournament.id,
                    'tournament_name': tournament.title if hasattr(tournament, 'title') else tournament.name,
                    'tournament_slug': tournament.slug,
                    'tournament_tier': tier,
                    'date': tournament.tournament_start.isoformat() if hasattr(tournament, 'tournament_start') and tournament.tournament_start else None,
                    'placement': placement,
                    'placement_label': placement_label,
                    'team_name': team_name,
                    'result': result,
                    'prize_amount': prize_amount,
                    'prize_currency': prize_currency
                })
            
            return achievements
        except Exception as e:
            # Graceful fallback - don't crash Career Tab
            print(f"Error fetching achievements: {e}")
            return []
    
    @staticmethod
    def get_display_attributes(passport) -> List[Dict[str, str]]:
        """
        Convert GameProfile to display-ready attribute list.
        
        Returns structured data for template rendering WITHOUT per-game HTML.
        
        Args:
            passport: GameProfile instance
        
        Returns:
            List of dicts:
            [
                {'label': 'IGN', 'value': 'Player#NA1'},
                {'label': 'Rank', 'value': 'Diamond 2'},
                {'label': 'Server', 'value': 'Singapore'},
                {'label': 'Play Hours', 'value': '2,405'},
                ...
            ]
        """
        if not passport:
            return []
        
        attributes = []
        
        # IGN (in_game_name or computed from ign+discriminator)
        if passport.in_game_name:
            attributes.append({'label': 'IGN', 'value': passport.in_game_name})
        elif passport.ign:
            ign_display = passport.ign
            if passport.discriminator:
                ign_display += passport.discriminator
            attributes.append({'label': 'IGN', 'value': ign_display})
        
        # Rank
        if passport.rank_name:
            attributes.append({'label': 'Rank', 'value': passport.rank_name})
        
        # Platform
        if passport.platform:
            attributes.append({'label': 'Platform', 'value': passport.platform})
        
        # Parse metadata for additional fields
        if hasattr(passport, 'metadata') and passport.metadata:
            metadata = passport.metadata
            
            # Server/Region
            if 'server' in metadata:
                attributes.append({'label': 'Server', 'value': metadata['server']})
            elif 'region' in metadata:
                attributes.append({'label': 'Region', 'value': metadata['region']})
            
            # Play hours
            if 'play_hours' in metadata:
                attributes.append({'label': 'Play Hours', 'value': f"{metadata['play_hours']:,}"})
            
            # Peak rank
            if 'peak_rank' in metadata and metadata['peak_rank']:
                attributes.append({'label': 'Peak Rank', 'value': metadata['peak_rank']})
        
        # Fallback: use passport.peak_rank if available
        if passport.peak_rank and not any(attr['label'] == 'Peak Rank' for attr in attributes):
            attributes.append({'label': 'Peak Rank', 'value': passport.peak_rank})
        
        return attributes
    
    @staticmethod
    def get_game_category(game) -> str:
        """
        Determine game category for stat tile rendering.
        
        Categories:
        - 'shooter': Valorant, CS2, PUBG, CoD, Free Fire, Apex
        - 'athlete': eFootball, FC 26, Rocket League
        - 'tactician': MLBB, Dota 2, LoL
        
        Args:
            game: Game instance
        
        Returns:
            str: 'shooter' | 'athlete' | 'tactician'
        """
        if not game:
            return 'shooter'  # default fallback
        
        game_slug = game.slug.lower()
        
        # Athlete category
        if game_slug in ['efootball', 'fc26', 'fifa', 'rocket-league', 'rocket_league']:
            return 'athlete'
        
        # Tactician category
        if game_slug in ['mlbb', 'dota2', 'dota-2', 'lol', 'league-of-legends']:
            return 'tactician'
        
        # Default to shooter (Valorant, CS2, PUBG, CoD, Free Fire, Apex, etc.)
        return 'shooter'
    
    @staticmethod
    def get_stat_tiles(passport, game, achievements, team_ranking) -> List[Dict[str, Any]]:
        """
        Generate 4 stat tiles based on game category.
        
        Shooter layout: K/D Ratio, Win Rate, Tournaments, Winnings
        Athlete layout: Goals Scored, Assists, Win Rate, Clean Sheets
        Tactician layout: KDA Ratio, GPM, Win Rate, Tournaments
        
        Args:
            passport: GameProfile instance
            game: Game instance
            achievements: List of achievement dicts
            team_ranking: Dict with team ranking data
        
        Returns:
            List of 4 dicts with keys: label, value, subtitle, color_class
        """
        category = CareerTabService.get_game_category(game)
        metadata = getattr(passport, 'metadata', {}) or {}
        
        if category == 'shooter':
            # K/D Ratio, Win Rate, Tournaments, Bounties Won
            kd_ratio = passport.kd_ratio or metadata.get('kd_ratio', 0) if passport else 0
            win_rate = passport.win_rate or metadata.get('win_rate', 0) if passport else 0
            tournaments_count = len(achievements) if achievements else 0
            
            # Count bounties won (TASK 3: Use FK, not username; works even if passport is None)
            bounties_won = 0
            try:
                from apps.user_profile.models import Bounty
                from apps.user_profile.models.bounties import BountyStatus
                
                # Get User from passport (passport.user_profile.user)
                if passport and hasattr(passport, 'user_profile') and passport.user_profile:
                    user = passport.user_profile.user
                    bounties_won = Bounty.objects.filter(
                        winner=user,
                        status=BountyStatus.COMPLETED,
                        game=game
                    ).count()
            except Exception as e:
                # Safe fallback, no error propagation
                bounties_won = 0
            
            return [
                {'label': 'K/D Ratio', 'value': f"{kd_ratio:.2f}" if kd_ratio else '--', 'subtitle': None, 'color_class': 'z-red'},
                {'label': 'Win Rate', 'value': f"{win_rate:.0f}%" if win_rate else '--', 'subtitle': None, 'color_class': 'z-cyan'},
                {'label': 'Tournaments', 'value': str(tournaments_count), 'subtitle': None, 'color_class': 'z-purple'},
                {'label': 'Bounties Won', 'value': f"{bounties_won:,}" if bounties_won else '0', 'subtitle': None, 'color_class': 'z-gold'},
            ]
        
        elif category == 'athlete':
            # Goals Scored, Assists, Win Rate, Clean Sheets
            goals = metadata.get('goals_scored', metadata.get('goals', 0))
            assists = metadata.get('assists', 0)
            win_rate = passport.win_rate or metadata.get('win_rate', 0)
            clean_sheets = metadata.get('clean_sheets', 0)
            
            return [
                {'label': 'Goals Scored', 'value': str(goals) if goals else '0', 'subtitle': None, 'color_class': 'z-green'},
                {'label': 'Assists', 'value': str(assists) if assists else '0', 'subtitle': None, 'color_class': 'z-cyan'},
                {'label': 'Win Rate', 'value': f"{win_rate:.0f}%" if win_rate else '--', 'subtitle': None, 'color_class': 'z-purple'},
                {'label': 'Clean Sheets', 'value': str(clean_sheets) if clean_sheets else '0', 'subtitle': None, 'color_class': 'z-gold'},
            ]
        
        else:  # tactician
            # KDA Ratio, GPM, Win Rate, Tournaments
            kda_ratio = metadata.get('kda_ratio', metadata.get('kda', 0))
            gpm = metadata.get('gpm', metadata.get('gold_per_min', 0))
            win_rate = passport.win_rate or metadata.get('win_rate', 0)
            tournaments_count = len(achievements) if achievements else 0
            
            return [
                {'label': 'KDA Ratio', 'value': f"{kda_ratio:.1f}" if kda_ratio else '--', 'subtitle': None, 'color_class': 'z-red'},
                {'label': 'GPM', 'value': str(int(gpm)) if gpm else '--', 'subtitle': 'Gold/Min', 'color_class': 'z-gold'},
                {'label': 'Win Rate', 'value': f"{win_rate:.0f}%" if win_rate else '--', 'subtitle': None, 'color_class': 'z-cyan'},
                {'label': 'Tournaments', 'value': str(tournaments_count), 'subtitle': None, 'color_class': 'z-purple'},
            ]
    
    @staticmethod
    def get_identity_meta_line(passport, game) -> str:
        """
        Generate identity meta line in format: "SINGAPORE â€¢ 2,405 HRS" or "PC â€¢ 142 MATCHES"
        
        Args:
            passport: GameProfile instance
            game: Game instance
        
        Returns:
            str: Formatted meta line
        """
        if not passport:
            return "NOT SET"
        
        metadata = getattr(passport, 'metadata', {}) or {}
        parts = []
        
        # Determine game category for region vs platform preference
        category = CareerTabService.get_game_category(game)
        
        # Region/Platform (uppercase)
        if category in ['athlete', 'tactician']:
            # Sports/MOBA prefer platform
            platform = passport.platform or metadata.get('platform')
            if platform:
                parts.append(platform.upper())
            else:
                region = metadata.get('region') or passport.region
                if region:
                    parts.append(region.upper())
        else:
            # Shooters prefer region
            region = metadata.get('region') or passport.region
            if region:
                parts.append(region.upper())
            elif passport.platform:
                parts.append(passport.platform.upper())
        
        # Hours or Matches
        hours = metadata.get('play_hours') or passport.hours_played
        matches = passport.matches_played
        
        if hours:
            parts.append(f"{hours:,} HRS")
        elif matches:
            parts.append(f"{matches:,} MATCHES")
        
        # Fallback if no data
        if not parts:
            return "NOT SET"
        
        return " â€¢ ".join(parts)
    
    @staticmethod
    def get_role_card(passport, game) -> Dict[str, Any]:
        """
        Generate role/attributes card data per game/passport.
        
        Returns:
            dict with keys: title, subtitle, icon_class, icon_color, border_color, gradient_color
        """
        if not passport:
            return None
        
        metadata = getattr(passport, 'metadata', {}) or {}
        category = CareerTabService.get_game_category(game)
        
        # Try to get role from main_role field or metadata (sports use 'position')
        if category == 'athlete':
            role = metadata.get('position') or passport.main_role or metadata.get('role')
        else:
            role = passport.main_role or metadata.get('role') or metadata.get('position')
        
        if not role:
            return None
        
        # Map roles to icons and colors based on category
        if category == 'shooter':
            role_map = {
                'entry': {'title': 'Entry Fragger', 'icon': 'fa-solid fa-crosshairs', 'color': 'z-red', 'border': 'z-red/30', 'gradient': 'z-red'},
                'controller': {'title': 'Controller', 'icon': 'fa-solid fa-shield-halved', 'color': 'z-purple', 'border': 'z-purple/30', 'gradient': 'z-purple'},
                'sentinel': {'title': 'Sentinel', 'icon': 'fa-solid fa-tower-observation', 'color': 'z-cyan', 'border': 'z-cyan/30', 'gradient': 'z-cyan'},
                'duelist': {'title': 'Duelist', 'icon': 'fa-solid fa-gun', 'color': 'z-red', 'border': 'z-red/30', 'gradient': 'z-red'},
                'support': {'title': 'Support', 'icon': 'fa-solid fa-heart', 'color': 'z-green', 'border': 'z-green/30', 'gradient': 'z-green'},
                'sniper': {'title': 'Sniper', 'icon': 'fa-solid fa-bullseye', 'color': 'z-gold', 'border': 'z-gold/30', 'gradient': 'z-gold'},
            }
            role_lower = role.lower()
            for key, config in role_map.items():
                if key in role_lower:
                    return {
                        'title': config['title'],
                        'subtitle': metadata.get('role_description', 'Specialist'),
                        'icon_class': config['icon'],
                        'icon_color': config['color'],
                        'border_color': config['border'],
                        'gradient_color': config['gradient'],
                    }
        
        elif category == 'athlete':
            role_map = {
                'striker': {'title': 'Striker (ST)', 'icon': 'fa-solid fa-shirt', 'color': 'z-gold', 'border': 'z-gold/30', 'gradient': 'z-gold'},
                'midfielder': {'title': 'Midfielder (CM)', 'icon': 'fa-solid fa-circle-dot', 'color': 'z-cyan', 'border': 'z-cyan/30', 'gradient': 'z-cyan'},
                'defender': {'title': 'Defender (CB)', 'icon': 'fa-solid fa-shield', 'color': 'z-purple', 'border': 'z-purple/30', 'gradient': 'z-purple'},
                'goalkeeper': {'title': 'Goalkeeper (GK)', 'icon': 'fa-solid fa-hands', 'color': 'z-green', 'border': 'z-green/30', 'gradient': 'z-green'},
            }
            role_lower = role.lower()
            for key, config in role_map.items():
                if key in role_lower:
                    return {
                        'title': config['title'],
                        'subtitle': metadata.get('role_description', 'Clinical Finisher'),
                        'icon_class': config['icon'],
                        'icon_color': config['color'],
                        'border_color': config['border'],
                        'gradient_color': config['gradient'],
                    }
        
        elif category == 'tactician':
            role_map = {
                'carry': {'title': 'Carry', 'icon': 'fa-solid fa-sword', 'color': 'z-red', 'border': 'z-red/30', 'gradient': 'z-red'},
                'mid': {'title': 'Mid', 'icon': 'fa-solid fa-wand-magic-sparkles', 'color': 'z-purple', 'border': 'z-purple/30', 'gradient': 'z-purple'},
                'offlane': {'title': 'Offlane', 'icon': 'fa-solid fa-shield-halved', 'color': 'z-cyan', 'border': 'z-cyan/30', 'gradient': 'z-cyan'},
                'support': {'title': 'Support', 'icon': 'fa-solid fa-heart', 'color': 'z-green', 'border': 'z-green/30', 'gradient': 'z-green'},
                'jungle': {'title': 'Jungler', 'icon': 'fa-solid fa-tree', 'color': 'z-gold', 'border': 'z-gold/30', 'gradient': 'z-gold'},
            }
            role_lower = role.lower()
            for key, config in role_map.items():
                if key in role_lower:
                    return {
                        'title': config['title'],
                        'subtitle': metadata.get('role_description', 'Specialist'),
                        'icon_class': config['icon'],
                        'icon_color': config['color'],
                        'border_color': config['border'],
                        'gradient_color': config['gradient'],
                    }
        
        # Generic fallback
        return {
            'title': role.title(),
            'subtitle': metadata.get('role_description', 'Player Role'),
            'icon_class': 'fa-solid fa-user',
            'icon_color': 'white',
            'border_color': 'white/10',
            'gradient_color': 'white',
        }
    
    @staticmethod
    def format_prize_amount(amount) -> str:
        """
        Format prize amount in compact notation: $12k, $1.5M, etc.
        
        Args:
            amount: int or float prize amount
        
        Returns:
            str: Formatted prize amount
        """
        if not amount or amount == 0:
            return "$0"
        
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}k"
        else:
            return f"${int(amount)}"
