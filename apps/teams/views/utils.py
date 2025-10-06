# apps/teams/views/utils.py
"""
Utility functions for team views.
Shared functions to improve code reusability and maintainability.
"""
from __future__ import annotations

from typing import Optional, Union, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import UserProfile

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from ..models import Team, TeamMembership

User = get_user_model()

# Game display name mapping
GAME_DISPLAY_NAMES = {
    'valorant': 'VALORANT',
    'codm': 'Call of Duty: Mobile',
    'mlbb': 'Mobile Legends: Bang Bang',
    'efootball': 'eFootball',
    'fc26': 'FC 26',
    'csgo': 'Counter-Strike 2',
    'freefire': 'Free Fire',
    'dota2': 'Dota 2',
    'lol': 'League of Legends',
    'pubg': 'PUBG Mobile',
    'rocket_league': 'Rocket League',
    'fortnite': 'Fortnite',
    'apex': 'Apex Legends',
    'overwatch': 'Overwatch 2',
    'fifa': 'FIFA 24'
}


def _ensure_profile(user) -> Optional[Any]:
    """
    Ensure user has a profile and return it.
    Returns None if profile doesn't exist or user is not authenticated.
    """
    if not user or not user.is_authenticated:
        return None
    
    try:
        if hasattr(user, 'profile'):
            return user.profile
        elif hasattr(user, 'userprofile'):
            return user.userprofile
        else:
            # Try to get profile from related models
            from apps.accounts.models import UserProfile
            try:
                return UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                return None
    except Exception:
        return None


def _get_profile(user) -> Optional[Any]:
    """Get user profile, similar to _ensure_profile but with different naming."""
    return _ensure_profile(user)


def _is_captain(profile: Any, team: Team) -> bool:
    """Check if profile is captain of the given team."""
    if not profile or not team:
        return False
    
    try:
        membership = TeamMembership.objects.filter(
            team=team,
            profile=profile,
            role='CAPTAIN',  # Use uppercase to match the model choice
            status='ACTIVE'
        ).first()
        return membership is not None
    except Exception:
        return False


def _get_game_display_name(game_code: str) -> str:
    """Get human-readable game display name from game code."""
    if not game_code:
        return 'Unknown Game'
    
    return GAME_DISPLAY_NAMES.get(game_code.lower(), game_code.title())


def _get_team_stats(team: Team) -> Dict[str, Any]:
    """Get basic team statistics."""
    try:
        active_members = team.memberships.filter(status='ACTIVE').count()
        return {
            'members_count': active_members,
            'total_matches': getattr(team, 'matches_played', 0),
            'wins': getattr(team, 'wins', 0),
            'losses': getattr(team, 'losses', 0),
            'win_rate': (getattr(team, 'wins', 0) / max(getattr(team, 'matches_played', 1), 1)) * 100,
            'points': getattr(team, 'points', 0),
            'rank': getattr(team, 'rank', 0)
        }
    except Exception:
        return {
            'members_count': 0,
            'total_matches': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'points': 0,
            'rank': 0
        }


def _format_team_data(team: Team, membership: Optional[TeamMembership] = None) -> Dict[str, Any]:
    """Format team data for API responses."""
    try:
        stats = _get_team_stats(team)
        
        return {
            'id': team.id,
            'name': team.name or f"Team {team.id}",
            'tag': getattr(team, 'tag', '') or '',
            'slug': getattr(team, 'slug', ''),
            'logo': team.logo.url if team.logo else None,
            'game': getattr(team, 'game', '') or '',
            'game_display': _get_game_display_name(getattr(team, 'game', '')),
            'description': getattr(team, 'description', '') or '',
            'is_public': getattr(team, 'is_public', True),
            'allow_join_requests': getattr(team, 'allow_join_requests', True),
            'url': team.get_absolute_url() if hasattr(team, 'get_absolute_url') else f'/teams/{team.slug}/' if hasattr(team, 'slug') and team.slug else '#',
            'manage_url': f'/teams/{team.slug}/manage/' if hasattr(team, 'slug') and team.slug else None,
            'created_at': team.created_at.isoformat() if hasattr(team, 'created_at') and team.created_at else None,
            'stats': stats,
            'membership': {
                'role': getattr(membership, 'role', 'member') if membership else None,
                'status': getattr(membership, 'status', 'active') if membership else None,
                'joined_at': membership.joined_at.isoformat() if membership and hasattr(membership, 'joined_at') and membership.joined_at else None,
            'can_manage': membership.role == 'CAPTAIN' if membership else False
            } if membership else None
        }
    except Exception:
        return {
            'id': team.id,
            'name': team.name or f"Team {team.id}",
            'tag': '',
            'slug': '',
            'logo': None,
            'game': '',
            'game_display': 'Unknown Game',
            'description': '',
            'is_public': True,
            'allow_join_requests': True,
            'url': '#',
            'manage_url': None,
            'created_at': None,
            'stats': _get_team_stats(team),
            'membership': None
        }


def _validate_team_data(data: Dict[str, Any]) -> Dict[str, str]:
    """Validate team data and return errors if any."""
    errors = {}
    
    # Validate team name
    name = data.get('name', '').strip()
    if not name:
        errors['name'] = 'Team name is required.'
    elif len(name) < 3:
        errors['name'] = 'Team name must be at least 3 characters long.'
    elif len(name) > 50:
        errors['name'] = 'Team name must be less than 50 characters.'
    
    # Validate team tag
    tag = data.get('tag', '').strip()
    if tag and len(tag) > 10:
        errors['tag'] = 'Team tag must be less than 10 characters.'
    
    # Validate description
    description = data.get('description', '').strip()
    if description and len(description) > 500:
        errors['description'] = 'Description must be less than 500 characters.'
    
    return errors


def _calculate_team_rank_score(team: Team) -> float:
    """
    Calculate team ranking score based on multiple factors.
    Enhanced algorithm with better weighting and normalization.
    """
    try:
        # Base stats
        wins = float(getattr(team, 'wins', 0))
        losses = float(getattr(team, 'losses', 0))
        draws = float(getattr(team, 'draws', 0))
        total_matches = wins + losses + draws
        
        # Activity metrics
        members_count = float(team.memberships.filter(status='ACTIVE').count() if hasattr(team, 'memberships') else 1)
        
        # Performance calculations
        if total_matches > 0:
            win_rate = wins / total_matches
            loss_rate = losses / total_matches
            draw_rate = draws / total_matches
        else:
            win_rate = loss_rate = draw_rate = 0.0
        
        # Enhanced scoring algorithm
        base_score = 1000.0  # Starting base score
        
        # Win/Loss performance (40% weight)
        performance_score = (win_rate * 500) - (loss_rate * 200) + (draw_rate * 50)
        
        # Activity bonus (20% weight)
        activity_multiplier = min(1.0 + (total_matches / 100.0), 2.0)  # Cap at 2x
        activity_score = min(total_matches * 5, 200)  # Cap at 200 points
        
        # Team size factor (15% weight)
        size_factor = min(members_count / 5.0, 1.2)  # Optimal team size bonus
        size_score = size_factor * 100
        
        # Consistency bonus (15% weight) - rewards teams with balanced performance
        if total_matches >= 10:
            consistency_score = 50 * (1 - abs(win_rate - 0.6))  # Reward ~60% win rate
        else:
            consistency_score = 0
        
        # Recent activity bonus (10% weight)
        recent_activity = 0
        if hasattr(team, 'last_match_date') and team.last_match_date:
            from django.utils import timezone
            days_since_last_match = (timezone.now().date() - team.last_match_date).days
            if days_since_last_match <= 7:
                recent_activity = 50
            elif days_since_last_match <= 30:
                recent_activity = 25
        
        # Calculate final score
        final_score = (
            base_score +
            (performance_score * activity_multiplier) +
            activity_score +
            size_score +
            consistency_score +
            recent_activity
        )
        
        # Apply penalties for inactive teams
        if total_matches == 0:
            final_score *= 0.5
        elif members_count < 2:
            final_score *= 0.7
        
        return max(final_score, 0.0)  # Ensure non-negative score
        
    except Exception:
        return 1000.0  # Default score for teams with missing data