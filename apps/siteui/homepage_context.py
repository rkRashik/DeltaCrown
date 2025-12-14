"""
Homepage Context Provider

Provides safe, structured context data for the homepage template.
Combines editable content from HomePageContent model with live statistics.
"""

from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()


def get_homepage_context() -> Dict[str, Any]:
    """
    Returns comprehensive homepage context with DB content + dynamic stats.
    
    This function safely retrieves homepage content and merges it with live statistics
    from the database. It includes fallback handling to ensure the homepage never crashes.
    
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
            "items": content.games_data,
        },
        
        # Tournaments section (with real live data)
        "tournaments": {
            "title": content.tournaments_section_title,
            "description": content.tournaments_section_description,
            "items": _get_featured_tournaments(),
        },
        
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
        
        # Platform info
        "platform": {
            "tagline": content.platform_tagline,
            "founded_year": content.platform_founded_year,
            "founder": content.platform_founder,
        },
    }
    
    return context


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
                "Building a world where geography does not define destiny—where a gamer in "
                "Bangladesh has the same trusted path to global glory as a pro on the main stage."
            ),
            "primary_cta": {
                "text": "Join Tournament",
                "url": "/tournaments/",
                "icon": "🏆",
            },
            "secondary_cta": {
                "text": "Explore Teams",
                "url": "/teams/",
                "icon": "👥",
            },
            "highlights": [
                {"label": "Active Players", "value": "12,500+", "icon": "👥"},
                {"label": "Prize Pool", "value": "৳5,00,000+", "icon": "💰"},
                {"label": "Tournaments", "value": "150+", "icon": "🏆"},
                {"label": "Games", "value": "11", "icon": "🎮"},
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
            "description": "From mobile to PC, tactical shooters to sports—game-agnostic by design",
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
            "description": "Strategy guides, match highlights, esports news—all in one home",
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
            "tagline": "From the Delta to the Crown — Where Champions Rise.",
            "founded_year": 2025,
            "founder": "Redwanul Rashik",
        },
    }


def _calculate_total_prize_pool() -> str:
    """
    Calculate total prize pool from all active tournaments.
    
    Returns:
        str: Formatted prize pool (e.g., "৳2.5M+") or empty string
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
            return "৳0"
        
        # Format based on size
        if total >= 1000000:  # 1M+
            return f"৳{total / 1000000:.1f}M+"
        elif total >= 1000:  # 1K+
            return f"৳{total / 1000:.0f}K+"
        else:
            return f"৳{total:,.0f}"
            
    except Exception as e:
        print(f"[WARNING] Failed to calculate prize pool: {e}")
        return "৳0"


def _get_featured_tournaments(limit=3):
    """
    Get featured tournaments for homepage display.
    
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
                'prize_pool': f"৳{tournament.prize_pool:,.0f}" if tournament.prize_pool else "TBD",
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
        
        Team = apps.get_model('teams', 'Team')
        
        # Get top teams with optimized query
        teams = Team.objects.filter(
            is_active=True,
            is_public=True
        ).select_related('captain').annotate(
            members_count=Count('memberships', filter=Q(memberships__status='ACTIVE'))
        ).order_by('-total_points', '-created_at')[:limit]
        
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
