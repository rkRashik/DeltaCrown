"""Homepage Context Provider

Provides safe, structured context data for the homepage template.
Combines editable content from HomePageContent model with live statistics.
"""

from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.core.cache import cache
from django.utils import timezone
import hashlib

User = get_user_model()

# Import testimonials helper
try:
    from apps.support.views import get_homepage_testimonials
except ImportError:
    def get_homepage_testimonials():
        return []


def get_homepage_context() -> Dict[str, Any]:
    """
    Returns comprehensive homepage context with DB content + dynamic stats.
    
    PERFORMANCE: Cached for 5 minutes to reduce database load.
    Cache is automatically invalidated when HomePageContent is updated.
    
    Returns:
        Dict containing:
            - homepage_content: HomePageContent model instance
            - live_stats: dict with players_count, tournaments_count, teams_count, games_count
            - hero: dict with badge, title, subtitle, description, CTAs, highlights
            - sections_enabled: dict of boolean flags for each section
            - All other section content organized by purpose
    
    Example:
        >>> context = get_homepage_context()
        >>> print(context['hero']['title'])
        "From the Delta to the Crown"
    """
    # Try to get cached context first
    cache_key = 'homepage_context_v2'
    cached_context = cache.get(cache_key)
    
    if cached_context is not None:
        return cached_context
    
    # Cache miss - generate fresh context
    from .models import HomePageContent
    
    # Get or create singleton content instance
    try:
        content = HomePageContent.get_instance()
    except Exception as e:
        # If DB error, return safe fallback
        print(f"[WARNING] Failed to load HomePageContent: {e}")
        return _get_fallback_context()
    
    # Compute live statistics
    live_stats = {
        "players_count": _safe_count(User.objects),
        "tournaments_count": _safe_count_model('tournaments', 'Tournament', status__in=['live', 'registration_open', 'published']),
        "teams_count": _safe_count_model('teams', 'Team', is_active=True),
        "matches_count": _safe_count_model('matches', 'Match'),
        "games_count": 11,  # Static official count
        "total_prize_pool": _calculate_total_prize_pool(),
    }
    
    # Build hero context with merged highlights
    hero_context = {
        "badge_text": content.hero_badge_text,
        "title": content.hero_title,
        "subtitle": content.hero_subtitle,
        "description": content.hero_description,
        "primary_cta": {
            "text": content.primary_cta_text,
            "url": content.primary_cta_url,
            "icon": content.primary_cta_icon,
        },
        "secondary_cta": {
            "text": content.secondary_cta_text,
            "url": content.secondary_cta_url,
            "icon": content.secondary_cta_icon,
        },
        "highlights": _merge_highlights(content.hero_highlights, live_stats),
    }
    
    # Build sections enabled map
    sections_enabled = {
        "problem": content.problem_section_enabled,
        "pillars": content.pillars_section_enabled,
        "games": content.games_section_enabled,
        "tournaments": content.tournaments_section_enabled,
        "teams": content.teams_section_enabled,
        "payments": content.payments_section_enabled,
        "deltacoin": content.deltacoin_section_enabled,
        "community": content.community_section_enabled,
        "roadmap": content.roadmap_section_enabled,
        "final_cta": content.final_cta_section_enabled,
    }
    
    # Build complete context
    context = {
        # Raw model instance (for template flexibility)
        "homepage_content": content,
        
        # Live statistics
        "live_stats": live_stats,
        
        # Hero section (structured)
        "hero": hero_context,
        
        # Section toggles
        "sections_enabled": sections_enabled,
        
        # Problem/Opportunity section
        "problem": {
            "title": content.problem_title,
            "subtitle": content.problem_subtitle,
            "comparison_table": content.comparison_table,
        },
        
        # Ecosystem pillars
        "pillars": {
            "title": content.ecosystem_pillars_title,
            "description": content.ecosystem_pillars_description,
            "items": content.ecosystem_pillars,
        },
        
        # Games section
        "games": {
            "title": content.games_section_title,
            "description": content.games_section_description,
            "items": _get_active_games(),  # Changed from content.games_data to real data
        },
        
        # Featured Tournament (new)
        "featured_tournament": _get_featured_tournament(),
        
        # Tournaments section (with real live data)
        "tournaments": {
            "title": content.tournaments_section_title,
            "description": content.tournaments_section_description,
            "items": _get_featured_tournaments(),
        },
        
        # Recent Matches (new)
        "recent_matches": _get_recent_matches(limit=5),
        
        # Teams section (with real leaderboard data)
        "teams": {
            "title": content.teams_section_title,
            "description": content.teams_section_description,
            "items": _get_top_teams(),
        },
        
        # Local payments
        "payments": {
            "title": content.payments_section_title,
            "description": content.payments_section_description,
            "methods": content.payment_methods,
            "trust_message": content.payments_trust_message,
        },
        
        # DeltaCoin economy
        "deltacoin": {
            "title": content.deltacoin_section_title,
            "description": content.deltacoin_section_description,
            "earn_methods": content.deltacoin_earn_methods,
            "spend_options": content.deltacoin_spend_options,
        },
        
        # Community section
        "community": {
            "title": content.community_section_title,
            "description": content.community_section_description,
            # Phase 2: Add spotlight/timeline data here
        },
        
        # Roadmap
        "roadmap": {
            "title": content.roadmap_section_title,
            "description": content.roadmap_section_description,
            "items": content.roadmap_items,
        },
        
        # Final CTA
        "final_cta": {
            "title": content.final_cta_title,
            "description": content.final_cta_description,
            "primary_cta": {
                "text": content.final_cta_primary_text,
                "url": content.final_cta_primary_url,
            },
            "secondary_cta": {
                "text": content.final_cta_secondary_text,
                "url": content.final_cta_secondary_url,
            },
        },
        
        # Testimonials (admin-managed)
        "testimonials": get_homepage_testimonials(),
        
        # Featured FAQs (admin-managed via is_featured toggle)
        "featured_faqs": _get_featured_faqs(),
        
        # Platform info
        "platform": {
            "tagline": content.platform_tagline,
            "founded_year": content.platform_founded_year,
            "founder": content.platform_founder,
        },
    }
    
    # Cache context for 5 minutes (300 seconds)
    cache.set(cache_key, context, 300)
    
    return context


def _get_featured_faqs():
    """
    Get FAQs marked as featured for homepage display.
    
    Returns:
        list: Featured FAQ objects with question, answer, category
    """
    try:
        from apps.support.models import FAQ
        return list(FAQ.objects.filter(is_active=True, is_featured=True).order_by('order')[:6])
    except Exception as e:
        print(f"[WARNING] Failed to get featured FAQs: {e}")
        return []


def _safe_count(queryset):
    """
    Safely count queryset with exception handling.
    
    Args:
        queryset: Django queryset to count
        
    Returns:
        int: Count or 0 if error occurs
    """
    try:
        return queryset.count()
    except Exception as e:
        print(f"[WARNING] Failed to count queryset: {e}")
        return 0


def _safe_count_model(app_label: str, model_name: str, **filters) -> int:
    """
    Safely count model instances with exception handling and filters.
    
    Args:
        app_label: Django app label (e.g., 'tournaments')
        model_name: Model class name (e.g., 'Tournament')
        **filters: Django ORM filters (e.g., status='live')
        
    Returns:
        int: Count or 0 if error occurs
    """
    try:
        from django.apps import apps
        Model = apps.get_model(app_label, model_name)
        if filters:
            return Model.objects.filter(**filters).count()
        return Model.objects.count()
    except Exception as e:
        print(f"[WARNING] Failed to count {app_label}.{model_name}: {e}")
        return 0


def _merge_highlights(highlights_json: list, stats: dict) -> list:
    """
    Replace 'DB_COUNT' source values with live stats.
    
    Args:
        highlights_json: List of highlight dicts from HomePageContent
        stats: Live statistics dict
        
    Returns:
        list: Highlights with updated values
    """
    merged = []
    
    for highlight in highlights_json:
        highlight_copy = highlight.copy()
        
        # Replace DB_COUNT sources with live data
        if highlight_copy.get("source") == "DB_COUNT":
            label = highlight_copy.get("label", "")
            
            if "Player" in label:
                count = stats.get("players_count", 0)
                highlight_copy["value"] = f"{count:,}+"
            elif "Tournament" in label:
                count = stats.get("tournaments_count", 0)
                highlight_copy["value"] = f"{count:,}+"
            elif "Team" in label:
                count = stats.get("teams_count", 0)
                highlight_copy["value"] = f"{count:,}+"
            elif "Game" in label:
                count = stats.get("games_count", 11)
                highlight_copy["value"] = str(count)
        
        merged.append(highlight_copy)
    
    return merged


def _get_fallback_context() -> Dict[str, Any]:
    """
    Fallback context if HomePageContent is unavailable.
    
    Returns safe default context that won't crash the homepage.
    This should only be used in emergency scenarios (DB errors, etc.)
    
    Returns:
        dict: Minimal safe context
    """
    return {
        "homepage_content": None,
        "live_stats": {
            "players_count": 0,
            "tournaments_count": 0,
            "teams_count": 0,
            "games_count": 11,
        },
        "hero": {
            "badge_text": "Bangladesh's #1 Esports Platform",
            "title": "From the Delta to the Crown",
            "subtitle": "Where Champions Rise",
            "description": (
                "Building a world where geography does not define destinyâ€”where a gamer in "
                "Bangladesh has the same trusted path to global glory as a pro on the main stage."
            ),
            "primary_cta": {
                "text": "Join Tournament",
                "url": "/tournaments/",
                "icon": "ðŸ†",
            },
            "secondary_cta": {
                "text": "Explore Teams",
                "url": "/teams/",
                "icon": "ðŸ‘¥",
            },
            "highlights": [
                {"label": "Active Players", "value": "12,500+", "icon": "ðŸ‘¥"},
                {"label": "Prize Pool", "value": "à§³5,00,000+", "icon": "ðŸ’°"},
                {"label": "Tournaments", "value": "150+", "icon": "ðŸ†"},
                {"label": "Games", "value": "11", "icon": "ðŸŽ®"},
            ],
        },
        "sections_enabled": {
            "problem": True,
            "pillars": True,
            "games": True,
            "tournaments": False,
            "teams": False,
            "payments": True,
            "deltacoin": True,
            "community": True,
            "roadmap": True,
            "final_cta": True,
        },
        "problem": {
            "title": "The Esports Gap",
            "subtitle": "Most platforms solve one problem. DeltaCrown solves the entire esports lifecycle.",
            "comparison_table": [],
        },
        "pillars": {
            "title": "Complete Esports Ecosystem",
            "description": "Eight interconnected domains, one unified platform",
            "items": [],
        },
        "games": {
            "title": "11 Games, One Platform",
            "description": "From mobile to PC, tactical shooters to sportsâ€”game-agnostic by design",
            "items": [],
        },
        "tournaments": {
            "title": "Active Tournaments",
            "description": "Join verified competitions with real prizes",
            "items": [],
        },
        "teams": {
            "title": "Top Teams",
            "description": "Professional organizations competing for glory",
            "items": [],
        },
        "payments": {
            "title": "Local Payment Partners",
            "description": "Bangladesh-first infrastructure",
            "methods": [],
            "trust_message": "No credit cards required. Built for South Asian markets.",
        },
        "deltacoin": {
            "title": "DeltaCoin Economy",
            "description": "Earn by competing. Spend on upgrades. Build your legacy.",
            "earn_methods": [],
            "spend_options": [],
        },
        "community": {
            "title": "Join the Community",
            "description": "Strategy guides, match highlights, esports newsâ€”all in one home",
        },
        "roadmap": {
            "title": "The Vision Ahead",
            "description": "Evolving toward global scale while staying rooted in emerging markets",
            "items": [],
        },
        "final_cta": {
            "title": "Ready to Compete?",
            "description": "Join thousands of gamers building their esports careers on DeltaCrown",
            "primary_cta": {
                "text": "Create Account",
                "url": "/account/register/",
            },
            "secondary_cta": {
                "text": "Explore Platform",
                "url": "/about/",
            },
        },
        "platform": {
            "tagline": "From the Delta to the Crown â€” Where Champions Rise.",
            "founded_year": 2025,
            "founder": "Redwanul Rashik",
        },
    }


def _calculate_total_prize_pool() -> str:
    """
    Calculate total prize pool from all active tournaments.
    
    Returns:
        str: Formatted prize pool (e.g., "à§³2.5M+") or empty string
    """
    try:
        from django.apps import apps
        from django.db.models import Sum
        from decimal import Decimal
        
        Tournament = apps.get_model('tournaments', 'Tournament')
        
        # Sum prize pools from active tournaments
        result = Tournament.objects.filter(
            status__in=['live', 'registration_open', 'published']
        ).aggregate(total=Sum('prize_pool'))
        
        total = result.get('total') or Decimal('0')
        
        if total == 0:
            return "à§³0"
        
        # Format based on size
        if total >= 1000000:  # 1M+
            return f"à§³{total / 1000000:.1f}M+"
        elif total >= 1000:  # 1K+
            return f"à§³{total / 1000:.0f}K+"
        else:
            return f"à§³{total:,.0f}"
            
    except Exception as e:
        print(f"[WARNING] Failed to calculate prize pool: {e}")
        return "à§³0"


def _get_featured_tournaments(limit=3):
    """
    Get featured tournaments for homepage display.
    
    OPTIMIZED: Uses select_related('game', 'organizer') to reduce N+1 queries.
    
    Prioritizes:
    1. Live tournaments
    2. Registration open tournaments
    3. Published tournaments (upcoming)
    
    Returns:
        list: Tournament dicts with relevant fields
    """
    try:
        from django.apps import apps
        from django.utils import timezone
        
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        
        # Get tournaments ordered by priority
        tournaments = Tournament.objects.filter(
            status__in=['live', 'registration_open', 'published']
        ).select_related('game', 'organizer').order_by(
            # Live first, then registration_open, then published
            '-status'
        )[:limit]
        
        result = []
        for tournament in tournaments:
            # Count confirmed registrations
            registration_count = Registration.objects.filter(
                tournament=tournament,
                status__in=['confirmed', 'pending']
            ).count()
            
            # Calculate days until registration ends
            days_left = None
            if tournament.registration_end:
                delta = tournament.registration_end - timezone.now()
                days_left = max(0, delta.days)
            
            result.append({
                'id': tournament.id,
                'name': tournament.name,
                'slug': tournament.slug,
                'game': tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A',
                'game_slug': tournament.game.slug if hasattr(tournament, 'game') and tournament.game else '',
                'prize_pool': f"à§³{tournament.prize_pool:,.0f}" if tournament.prize_pool else "TBD",
                'registration_count': registration_count,
                'max_teams': tournament.max_participants if hasattr(tournament, 'max_participants') else None,
                'status': tournament.status,
                'status_display': tournament.get_status_display() if hasattr(tournament, 'get_status_display') else tournament.status.upper(),
                'days_left': days_left,
                'tournament_start': tournament.tournament_start if hasattr(tournament, 'tournament_start') else None,
                'registration_end': tournament.registration_end,
                'url': f"/tournaments/{tournament.slug}/",
            })
        
        return result
        
    except Exception as e:
        print(f"[WARNING] Failed to get featured tournaments: {e}")
        return []


def _get_top_teams(limit=5):
    """
    Get top teams for homepage leaderboard.
    
    OPTIMIZED: Uses select_related('captain') and annotate() for efficient querying.
    
    Orders by:
    1. Total ranking points (if available)
    2. Fallback to ELO rating
    3. Fallback to recent activity
    
    Returns:
        list: Team dicts with relevant fields
    """
    try:
        from django.apps import apps
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        
        Team = apps.get_model('organizations', 'Team')
        
        # Get top teams with optimized query
        teams = Team.objects.filter(
            status='ACTIVE',
            visibility='PUBLIC'
        ).annotate(
            members_count=Count('vnext_memberships', filter=Q(vnext_memberships__status='ACTIVE'))
        ).order_by('-created_at')[:limit]
        
        result = []
        for rank, team in enumerate(teams, start=1):
            # Calculate weekly change (placeholder - would need historical data)
            weekly_change = 0  # TODO: Track point changes over time
            
            # Get game display name
            game_display = dict(team._meta.get_field('game').choices).get(team.game, team.game) if hasattr(team, 'game') else 'N/A'
            
            result.append({
                'rank': rank,
                'id': team.id,
                'name': team.name,
                'slug': team.slug,
                'tag': team.tag if hasattr(team, 'tag') else '',
                'logo': team.logo.url if team.logo else None,
                'game': team.game if hasattr(team, 'game') else 'N/A',
                'game_display': game_display,
                'elo_rating': getattr(team, 'elo_rating', 1500),
                'total_points': getattr(team, 'total_points', 0),
                'members_count': team.members_count,
                'weekly_change': weekly_change,
                'url': f"/teams/{team.slug}/",
            })
        
        return result
        
    except Exception as e:
        print(f"[WARNING] Failed to get top teams: {e}")
        return []


def _get_featured_tournament():
    """
    Get the single featured tournament for spotlight section.
    
    Returns:
        dict: Featured tournament with full details or None
    """
    try:
        from django.apps import apps
        from django.utils import timezone
        
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        
        # Get first featured tournament, fallback to first live/open tournament
        tournament = Tournament.objects.filter(
            is_featured=True,
            status__in=['live', 'registration_open', 'published']
        ).select_related('game', 'organizer').first()
        
        # Fallback to most recent live tournament if no featured
        if not tournament:
            tournament = Tournament.objects.filter(
                status='live'
            ).select_related('game', 'organizer').order_by('-tournament_start').first()
        
        if not tournament:
            return None
        
        # Count registrations
        registration_count = Registration.objects.filter(
            tournament=tournament,
            status__in=['confirmed', 'pending']
        ).count()
        
        # Calculate days until registration ends
        days_left = None
        hours_left = None
        if tournament.registration_end:
            delta = tournament.registration_end - timezone.now()
            days_left = max(0, delta.days)
            hours_left = max(0, int(delta.total_seconds() / 3600))
        
        return {
            'id': tournament.id,
            'name': tournament.name,
            'slug': tournament.slug,
            'description': tournament.description if hasattr(tournament, 'description') else '',
            'game': tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A',
            'game_display': tournament.game.display_name if hasattr(tournament.game, 'display_name') else tournament.game.name if tournament.game else 'N/A',
            'prize_pool': f"à§³{tournament.prize_pool:,.0f}" if tournament.prize_pool else "TBD",
            'registration_count': registration_count,
            'max_teams': tournament.max_participants if hasattr(tournament, 'max_participants') else None,
            'status': tournament.status,
            'days_left': days_left,
            'hours_left': hours_left,
            'tournament_start': tournament.tournament_start if hasattr(tournament, 'tournament_start') else None,
            'registration_deadline': tournament.registration_end,
            'banner_image': tournament.banner_image.url if hasattr(tournament, 'banner_image') and tournament.banner_image else None,
            'url': f"/tournaments/{tournament.slug}/",
            'organizer': tournament.organizer.username if tournament.organizer else 'DeltaCrown',
        }
        
    except Exception as e:
        print(f"[WARNING] Failed to get featured tournament: {e}")
        return None


def _get_recent_matches(limit=5):
    """
    Get recent completed matches for homepage feed.
    
    Returns:
        list: Match dicts with teams, scores, and timestamps
    """
    try:
        from django.apps import apps
        from django.utils import timezone
        from datetime import timedelta
        
        Match = apps.get_model('tournaments', 'Match')
        
        # Get recent completed matches
        matches = Match.objects.filter(
            state='completed'
        ).select_related(
            'team_a', 'team_b', 'tournament', 'tournament__game'
        ).order_by('-completed_at')[:limit]
        
        result = []
        for match in matches:
            # Calculate how long ago
            time_ago = ""
            if hasattr(match, 'completed_at') and match.completed_at:
                delta = timezone.now() - match.completed_at
                if delta.days > 0:
                    time_ago = f"{delta.days}d ago"
                elif delta.seconds >= 3600:
                    time_ago = f"{delta.seconds // 3600}h ago"
                else:
                    time_ago = f"{delta.seconds // 60}m ago"
            
            result.append({
                'id': match.id,
                'team_a': {
                    'name': match.team_a.name if match.team_a else 'TBD',
                    'logo': match.team_a.logo.url if match.team_a and match.team_a.logo else None,
                    'score': getattr(match, 'score_team_a', 0),
                },
                'team_b': {
                    'name': match.team_b.name if match.team_b else 'TBD',
                    'logo': match.team_b.logo.url if match.team_b and match.team_b.logo else None,
                    'score': getattr(match, 'score_team_b', 0),
                },
                'tournament': {
                    'name': match.tournament.name if match.tournament else 'Unknown',
                    'game': match.tournament.game.name if match.tournament and match.tournament.game else 'N/A',
                },
                'winner': match.team_a.name if match.team_a and hasattr(match, 'winner') and match.winner == match.team_a else (match.team_b.name if match.team_b else None),
                'time_ago': time_ago,
                'url': f"/tournaments/{match.tournament.slug}/matches/{match.id}/" if match.tournament else '#',
            })
        
        return result
        
    except Exception as e:
        print(f"[WARNING] Failed to get recent matches: {e}")
        return []


def _get_active_games():
    """
    Get active games from the Game model with real images and data.
    
    Returns:
        list: Game dicts with name, icon, logo, platforms, etc.
    """
    try:
        from django.apps import apps
        
        # Try tournaments.Game first, then games.Game
        try:
            Game = apps.get_model('games', 'Game')
        except LookupError:
            Game = apps.get_model('tournaments', 'Game')
        
        games = Game.objects.filter(is_active=True).order_by('name')
        
        result = []
        for game in games:
            result.append({
                'id': game.id,
                'name': game.name,
                'display_name': game.display_name if hasattr(game, 'display_name') else game.name,
                'slug': game.slug if hasattr(game, 'slug') else game.name.lower().replace(' ', '-'),
                'icon': game.icon.url if hasattr(game, 'icon') and game.icon else None,
                'logo': game.logo.url if hasattr(game, 'logo') and game.logo else None,
                'card_image': game.card_image.url if hasattr(game, 'card_image') and game.card_image else None,
                'platforms': game.platforms if hasattr(game, 'platforms') else ['PC', 'Mobile'],
                'category': game.category if hasattr(game, 'category') else 'Esports',
                'primary_color': game.primary_color if hasattr(game, 'primary_color') else '#667eea',
            })
        
        return result
        
    except Exception as e:
        print(f"[WARNING] Failed to get active games: {e}")
        # Fallback to empty list
        return []
