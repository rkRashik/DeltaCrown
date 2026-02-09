"""
Career Context Service
Provides team history, current teams, and career timeline data for profile pages.
Phase 4D: Modern esports portfolio view
"""
from typing import Dict, List, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def get_membership_end_date(tm):
    """
    Get the end date for a team membership.
    
    Phase 4F: Now uses tm.left_at field when available.
    
    The TeamMembership model now has a left_at field (added in Phase 4F).
    For REMOVED memberships, left_at is populated via:
    1. Signal when status changes to REMOVED (auto-populated)
    2. Backfill migration for existing data (from role_changed_at)
    3. Manual setting by admins
    
    Strategy:
    - Check tm.left_at first (primary source)
    - ACTIVE/PENDING memberships: Return None (still active)
    - REMOVED without left_at: Return None (will show "End date unavailable")
    
    Args:
        tm: TeamMembership instance
    
    Returns:
        datetime or None: End date if available, None otherwise
    """
    # Try to get status safely
    status = getattr(tm, 'status', None)
    
    # Active or pending memberships have no end date
    if status in ['ACTIVE', 'PENDING']:
        return None
    
    # Phase 4F: Use left_at field as primary source
    left_at = getattr(tm, 'left_at', None)
    if left_at:
        return left_at
    
    # For REMOVED status without left_at, we don't have a reliable end date
    # The model doesn't track when someone was removed (for old data before Phase 4F)
    # We already backfilled where possible, so if still NULL, it's truly unknown
    
    # Defensive: Try other fields (in case added later)
    for field_name in ['ended_at', 'removed_at', 'inactive_at']:
        end_date = getattr(tm, field_name, None)
        if end_date:
            logger.debug(f"Found end date in {field_name}: {end_date}")
            return end_date
    
    # No end date available
    return None


def build_career_context(user_profile, is_owner: bool = False) -> Dict:
    """
    Build comprehensive career context for profile Career tab.
    Phase 4G: Restructured to group teams by game (one team per game).
    Phase 4H: Refined for duplicate prevention and smart empty states.
    
    Platform Rule: Users can have max ONE active team per game.
    - If multiple ACTIVE memberships exist for same game (data anomaly), 
      only the most recent is used as current_team.
    - Others are included in history only.
    
    Args:
        user_profile: UserProfile instance
        is_owner: Whether viewer is the profile owner
    
    Returns:
        Dictionary with career_by_game (game-wise sections)
    """
    from apps.organizations.models import TeamMembership
    from apps.games.models import Game
    from apps.user_profile.utils import get_game_icon_url
    
    if not user_profile:
        return {
            'career_by_game': [],
            'has_teams': False,
        }
    
    # Get all games with display info (single query, dual lookup)
    all_games = list(Game.objects.all())
    games = {g.slug: g for g in all_games}          # slug -> Game
    games_by_id = {g.id: g for g in all_games}      # int pk -> Game
    
    # Get all memberships (exclude PENDING from timeline)
    all_memberships = TeamMembership.objects.filter(
        user=user_profile.user
    ).exclude(
        status=TeamMembership.Status.PENDING
    ).select_related('team').order_by('-joined_at')
    
    # Group memberships by game
    career_by_game = {}
    for tm in all_memberships:
        # Resolve game slug via pre-fetched dict (avoids N+1 from team.game property)
        game_obj = games_by_id.get(tm.team.game_id)
        game_slug = game_obj.slug if game_obj else str(tm.team.game_id)
        status = getattr(tm, 'status', 'ACTIVE')
        
        # Initialize game section if needed
        if game_slug not in career_by_game:
            career_by_game[game_slug] = {
                'game_slug': game_slug,
                'game_name': game_obj.display_name if game_obj else game_slug.title(),
                'game_icon': get_game_icon_url(game_slug),
                'current_team': None,
                'history': [],
            }
        
        # Calculate duration
        start_date = getattr(tm, 'joined_at', None) or timezone.now()
        end_date = get_membership_end_date(tm)
        
        # Calculate duration string based on status
        if status == 'ACTIVE':
            duration = "Present"
            left_formatted = "Present"
        elif status == 'REMOVED':
            if end_date:
                try:
                    duration_days = (end_date - start_date).days
                    if duration_days < 30:
                        duration = f"{duration_days} days"
                    elif duration_days < 365:
                        duration = f"{duration_days // 30} months"
                    else:
                        duration = f"{duration_days // 365} years"
                    left_formatted = end_date.strftime('%b %Y')
                except Exception as e:
                    logger.warning(f"Error calculating duration: {e}")
                    duration = "Unknown duration"
                    left_formatted = "End date unavailable"
            else:
                duration = "Unknown duration"
                left_formatted = "End date unavailable"
        else:
            duration = "Unknown"
            left_formatted = "Unknown"
        
        team_data = {
            'id': tm.team.id,
            'slug': tm.team.slug,
            'name': tm.team.name,
            'tag': getattr(tm.team, 'tag', ''),
            'role': tm.get_role_display(),
            'role_code': tm.role,
            'logo_url': tm.team.logo.url if tm.team.logo else None,
            'joined_date': start_date,
            'left_date': end_date,
            'joined_formatted': start_date.strftime('%b %Y') if start_date else 'Unknown',
            'left_formatted': left_formatted,
            'duration': duration,
            'is_current': status == 'ACTIVE',
            'is_former': status == 'REMOVED',
            'status': status,
            'status_display': 'Active' if status == 'ACTIVE' else 'Former',
        }
        
        # Set current team or add to history
        if status == 'ACTIVE':
            # Only one active team per game (platform enforces this)
            career_by_game[game_slug]['current_team'] = team_data
        
        # Add to history (includes current team)
        career_by_game[game_slug]['history'].append(team_data)
    
    # Sort games: primary game first (most recent activity), then alphabetical
    def game_sort_key(item):
        game_slug, data = item
        # Get most recent activity timestamp
        latest_timestamp = 0
        if data['current_team']:
            latest_timestamp = data['current_team']['joined_date'].timestamp()
        elif data['history']:
            latest_timestamp = max(
                (h['joined_date'].timestamp() if h['joined_date'] else 0)
                for h in data['history']
            )
        # Sort: most recent first, then alphabetical
        return (-latest_timestamp, data['game_name'])
    
    career_by_game_list = [
        data for _, data in sorted(career_by_game.items(), key=game_sort_key)
    ]
    
    return {
        'career_by_game': career_by_game_list,
        'has_teams': len(career_by_game_list) > 0,
    }


def get_game_passports_for_career(user, limit: int = 3) -> List[Dict]:
    """
    Get game passports formatted for Career tab preview.
    Shows top N passports (pinned first, then by rank/level).
    
    Args:
        user: User instance
        limit: Maximum number of passports to return
    
    Returns:
        List of passport dicts with game icon, IGN, rank
    """
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.utils import get_game_icon_url
    
    try:
        all_passports = GamePassportService.get_all_passports(user=user)
        
        # Sort: pinned first, then by verification status, then by updated date
        sorted_passports = sorted(
            all_passports,
            key=lambda p: (
                not p.is_pinned,  # Pinned first (False < True)
                p.verification_status != 'VERIFIED',  # Verified first
                -p.updated_at.timestamp() if p.updated_at else 0  # Recent first
            )
        )
        
        # Take top N
        top_passports = sorted_passports[:limit]
        
        # Format for template
        passports_data = []
        for passport in top_passports:
            passports_data.append({
                'id': passport.id,
                'game': passport.game_display_name,
                'game_slug': passport.game.slug if passport.game else 'unknown',
                'game_icon': get_game_icon_url(passport.game.slug if passport.game else 'unknown'),
                'ign': passport.in_game_name,
                'rank': passport.rank or 'Unranked',
                'is_verified': passport.verification_status == 'VERIFIED',
                'is_pinned': passport.is_pinned,
            })
        
        return passports_data
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load passports for career preview: {e}")
        return []
