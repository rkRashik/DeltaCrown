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
    
    The TeamMembership model does NOT have a left_at or ended_at field.
    For REMOVED memberships, we have no reliable timestamp for when they left.
    
    Strategy:
    - ACTIVE/PENDING memberships: Return None (still active)
    - REMOVED memberships: Return None (we don't know when they left)
    
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
    
    # For REMOVED status, we don't have a reliable end date
    # The model doesn't track when someone was removed
    # We could use role_changed_at if it exists, but that's not reliable
    # Better to return None and display "Unknown" or omit the date
    
    # Try common explicit end date fields (defensive, in case model changes)
    for field_name in ['left_at', 'ended_at', 'removed_at', 'inactive_at']:
        end_date = getattr(tm, field_name, None)
        if end_date:
            logger.debug(f"Found end date in {field_name}: {end_date}")
            return end_date
    
    # No end date available
    return None


def build_career_context(user_profile, is_owner: bool = False) -> Dict:
    """
    Build comprehensive career context for profile Career tab.
    
    Args:
        user_profile: UserProfile instance
        is_owner: Whether viewer is the profile owner
    
    Returns:
        Dictionary with current_teams, team_history, career_timeline
    """
    from apps.teams.models import TeamMembership
    from apps.games.models import Game
    
    if not user_profile:
        return {
            'current_teams': [],
            'team_history': [],
            'career_timeline': [],
            'has_teams': False,
        }
    
    # Get game display names mapping
    games_map = {g.slug: g.display_name for g in Game.objects.all()}
    
    # 1. Current Teams (active memberships)
    current_memberships = TeamMembership.objects.filter(
        profile=user_profile,
        status=TeamMembership.Status.ACTIVE
    ).select_related('team').order_by('-joined_at')
    
    current_teams = []
    for tm in current_memberships:
        current_teams.append({
            'id': tm.team.id,
            'slug': tm.team.slug,
            'name': tm.team.name,
            'tag': tm.team.tag,
            'game': games_map.get(tm.team.game, tm.team.game),
            'game_slug': tm.team.game,
            'role': tm.get_role_display(),
            'role_code': tm.role,
            'logo_url': tm.team.logo.url if tm.team.logo else None,
            'joined_date': tm.joined_at,
            'joined_formatted': tm.joined_at.strftime('%b %Y') if tm.joined_at else 'Unknown',
            'is_captain': tm.role == TeamMembership.Role.CAPTAIN,
            'is_owner': tm.role == TeamMembership.Role.OWNER,
            'status': 'Active',
        })
    
    # 2. Team History (all memberships for timeline)
    all_memberships = TeamMembership.objects.filter(
        profile=user_profile
    ).select_related('team').order_by('-joined_at')
    
    team_history = []
    for tm in all_memberships:
        # Calculate duration
        start_date = getattr(tm, 'joined_at', None) or timezone.now()
        end_date = get_membership_end_date(tm)
        
        # Calculate duration string
        if end_date:
            try:
                duration_days = (end_date - start_date).days
                if duration_days < 30:
                    duration = f"{duration_days} days"
                elif duration_days < 365:
                    duration = f"{duration_days // 30} months"
                else:
                    duration = f"{duration_days // 365} years"
            except Exception as e:
                logger.warning(f"Error calculating duration: {e}")
                duration = "Unknown"
        else:
            # No end date - either active or we don't know when they left
            status = getattr(tm, 'status', 'ACTIVE')
            if status == 'ACTIVE':
                duration = "Present"
            else:
                # REMOVED but no end date - we don't know when they left
                duration = "Unknown"
        
        team_history.append({
            'id': tm.team.id,
            'slug': tm.team.slug,
            'name': tm.team.name,
            'tag': getattr(tm.team, 'tag', ''),
            'game': games_map.get(tm.team.game, tm.team.game),
            'game_slug': tm.team.game,
            'role': tm.get_role_display(),
            'role_code': tm.role,
            'logo_url': tm.team.logo.url if tm.team.logo else None,
            'joined_date': start_date,
            'left_date': end_date,
            'joined_formatted': start_date.strftime('%b %Y') if start_date else 'Unknown',
            'left_formatted': end_date.strftime('%b %Y') if end_date else ('Present' if getattr(tm, 'status', '') == 'ACTIVE' else 'Unknown'),
            'duration': duration,
            'is_current': getattr(tm, 'status', '') == 'ACTIVE',
            'status': 'Active' if getattr(tm, 'status', '') == 'ACTIVE' else 'Past',
        })
    
    # 3. Career Timeline (year-grouped for visual timeline)
    timeline = {}
    for entry in team_history:
        year = entry['joined_date'].year if entry['joined_date'] else timezone.now().year
        if year not in timeline:
            timeline[year] = []
        timeline[year].append(entry)
    
    # Sort years descending
    career_timeline = [
        {'year': year, 'entries': entries}
        for year, entries in sorted(timeline.items(), reverse=True)
    ]
    
    return {
        'current_teams': current_teams,
        'team_history': team_history,
        'career_timeline': career_timeline,
        'has_teams': len(team_history) > 0,
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
