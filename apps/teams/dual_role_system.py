# apps/teams/dual_role_system.py
"""
Dual-Role System Utilities

This module provides helper functions for working with the dual-role system:
- Team Membership Role: Organizational status (Captain, Player, Sub, Manager, Coach)
- In-Game Role: Tactical function specific to the game (Duelist, IGL, AWPer, etc.)

The dual-role system allows proper separation of concerns:
- A "Substitute" can play as a "Duelist" when they enter the game
- A "Player" can be the "IGL" (In-Game Leader)
- Coaches and Managers don't have in-game roles
"""
from typing import List, Dict, Optional, Tuple
from django.core.exceptions import ValidationError

from .game_config import (
    get_game_config,
    get_available_roles,
    validate_role_for_game,
    get_role_description,
    GameRosterConfig,
)


# ═══════════════════════════════════════════════════════════════════════════
# ROLE VALIDATION AND RETRIEVAL
# ═══════════════════════════════════════════════════════════════════════════

def get_player_roles_for_game(game_code: str) -> List[Dict[str, str]]:
    """
    Get all available in-game roles for a specific game.
    
    Args:
        game_code: Game identifier (e.g., 'valorant', 'cs2')
        
    Returns:
        List of dictionaries with role info:
        [
            {'value': 'Duelist', 'label': 'Duelist', 'description': '...'},
            ...
        ]
    """
    try:
        config = get_game_config(game_code)
        roles = []
        
        for role in config.roles:
            roles.append({
                'value': role,
                'label': role,
                'description': config.role_descriptions.get(role, '')
            })
        
        return roles
    except KeyError:
        return []


def validate_player_role(game_code: str, role: str) -> Tuple[bool, str]:
    """
    Validate if a player role is valid for a game.
    
    Args:
        game_code: Game identifier
        role: Role name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not role:
        return True, ""  # Empty role is valid (optional)
    
    if not game_code:
        return False, "Cannot set in-game role without a game specified"
    
    try:
        if validate_role_for_game(game_code, role):
            return True, ""
        else:
            config = get_game_config(game_code)
            available = ', '.join(config.roles)
            return False, f"'{role}' is not valid for {config.name}. Available: {available}"
    except KeyError:
        return False, f"Unknown game: {game_code}"


def game_supports_player_roles(game_code: str) -> bool:
    """
    Check if a game supports in-game tactical roles.
    
    Games like eFootball and FC 26 are primarily 1v1/2v2 and don't need
    tactical role selection.
    
    Args:
        game_code: Game identifier
        
    Returns:
        True if the game has meaningful tactical roles
    """
    # eFootball and FC 26 don't have meaningful tactical roles
    if game_code in ['efootball', 'fc26']:
        return False
    
    try:
        config = get_game_config(game_code)
        # If the game only has generic roles like "Player", it doesn't support roles
        if config.roles == ['Player'] or config.roles == ['Player', 'Co-op Partner']:
            return False
        return True
    except KeyError:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# MEMBERSHIP ROLE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def can_have_player_role(membership_role: str) -> bool:
    """
    Check if a team membership role can have an in-game player role.
    
    Only Players and Substitutes can have in-game roles.
    Captains, Managers, and Coaches are organizational roles.
    
    Args:
        membership_role: The team membership role (CAPTAIN, PLAYER, SUB, MANAGER)
        
    Returns:
        True if this membership type can have a player role
    """
    from .models._legacy import TeamMembership
    
    return membership_role in [
        TeamMembership.Role.PLAYER,
        TeamMembership.Role.SUB,
    ]


def get_membership_role_display(membership_role: str, player_role: Optional[str] = None) -> str:
    """
    Get a formatted display string for a membership combining both roles.
    
    Args:
        membership_role: The team membership role
        player_role: Optional in-game role
        
    Returns:
        Formatted string like "Player (Duelist)" or "Substitute" or "Coach"
    """
    from .models._legacy import TeamMembership
    
    # Get base membership role display
    role_dict = dict(TeamMembership.Role.choices)
    base_role = role_dict.get(membership_role, membership_role)
    
    # Add player role if applicable
    if player_role and can_have_player_role(membership_role):
        return f"{base_role} ({player_role})"
    
    return base_role


# ═══════════════════════════════════════════════════════════════════════════
# ROSTER COMPOSITION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_roster_by_roles(team) -> Dict[str, List]:
    """
    Organize team roster by in-game roles.
    
    Args:
        team: Team instance
        
    Returns:
        Dictionary mapping roles to list of members:
        {
            'Duelist': [membership1, membership2],
            'Controller': [membership3],
            'Unassigned': [membership4]
        }
    """
    from .models._legacy import TeamMembership
    
    roster_by_role = {}
    
    # Get all active players and subs
    members = team.memberships.filter(
        status=TeamMembership.Status.ACTIVE,
        role__in=[TeamMembership.Role.PLAYER, TeamMembership.Role.SUB]
    ).select_related('profile__user')
    
    for member in members:
        role = member.player_role if member.player_role else 'Unassigned'
        
        if role not in roster_by_role:
            roster_by_role[role] = []
        
        roster_by_role[role].append(member)
    
    return roster_by_role


def validate_roster_composition(team) -> Tuple[bool, List[str]]:
    """
    Validate if a team's roster composition meets game requirements.
    
    Checks:
    - Minimum number of players
    - Role requirements (e.g., Dota 2 needs unique positions)
    - Maximum roster size
    
    Args:
        team: Team instance
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    from .models._legacy import TeamMembership, TEAM_MAX_ROSTER
    
    errors = []
    
    if not team.game:
        return True, []  # No game specified, skip validation
    
    try:
        config = get_game_config(team.game)
    except KeyError:
        errors.append(f"Unknown game: {team.game}")
        return False, errors
    
    # Count active players and subs
    active_players = team.memberships.filter(
        status=TeamMembership.Status.ACTIVE,
        role=TeamMembership.Role.PLAYER
    ).count()
    
    active_subs = team.memberships.filter(
        status=TeamMembership.Status.ACTIVE,
        role=TeamMembership.Role.SUB
    ).count()
    
    # Check minimum starters
    if active_players < config.min_starters:
        errors.append(
            f"{config.name} requires at least {config.min_starters} active players. "
            f"You have {active_players}."
        )
    
    # Check maximum starters
    if active_players > config.max_starters:
        errors.append(
            f"{config.name} allows maximum {config.max_starters} active players. "
            f"You have {active_players}."
        )
    
    # Check maximum substitutes
    if active_subs > config.max_substitutes:
        errors.append(
            f"{config.name} allows maximum {config.max_substitutes} substitutes. "
            f"You have {active_subs}."
        )
    
    # Check total roster size
    total = active_players + active_subs
    max_total = config.max_starters + config.max_substitutes
    
    if total > min(TEAM_MAX_ROSTER, max_total):
        errors.append(
            f"Total roster size ({total}) exceeds maximum allowed ({max_total})."
        )
    
    # Check unique role requirements (e.g., Dota 2)
    if config.requires_unique_roles:
        player_roles = team.memberships.filter(
            status=TeamMembership.Status.ACTIVE,
            role=TeamMembership.Role.PLAYER
        ).exclude(player_role='').values_list('player_role', flat=True)
        
        role_counts = {}
        for role in player_roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        duplicates = [role for role, count in role_counts.items() if count > 1]
        if duplicates:
            errors.append(
                f"{config.name} requires unique roles. "
                f"Duplicate roles found: {', '.join(duplicates)}"
            )
    
    return len(errors) == 0, errors


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_role_badge_color(role: str, game_code: str) -> str:
    """
    Get CSS color class for role badge display.
    
    Args:
        role: In-game role name
        game_code: Game identifier
        
    Returns:
        Tailwind CSS color class (e.g., 'bg-red-500', 'bg-blue-500')
    """
    # Color mapping for common role types
    role_colors = {
        # Aggressive/Entry roles
        'Duelist': 'bg-red-500',
        'Entry Fragger': 'bg-red-500',
        'Rusher': 'bg-red-500',
        'Assaulter/Fragger': 'bg-red-500',
        'Slayer': 'bg-red-500',
        
        # Leadership roles
        'IGL': 'bg-yellow-500',
        'Shot Caller': 'bg-yellow-500',
        'IGL/Shot Caller': 'bg-yellow-500',
        
        # Support roles
        'Controller': 'bg-purple-500',
        'Support': 'bg-green-500',
        'Position 4 (Soft Support)': 'bg-green-500',
        'Position 5 (Hard Support)': 'bg-green-600',
        'Roamer': 'bg-green-500',
        
        # Defensive roles
        'Sentinel': 'bg-blue-500',
        'Anchor': 'bg-blue-500',
        
        # Utility roles
        'Initiator': 'bg-orange-500',
        'Lurker': 'bg-indigo-500',
        'Flanker': 'bg-indigo-500',
        
        # Specialist roles
        'AWPer': 'bg-pink-500',
        'Sniper/Scout': 'bg-pink-500',
        
        # Position-based (Dota 2)
        'Position 1 (Carry)': 'bg-red-600',
        'Position 2 (Mid)': 'bg-orange-500',
        'Position 3 (Offlane)': 'bg-blue-500',
        
        # MLBB specific
        'Gold Laner': 'bg-yellow-600',
        'EXP Laner': 'bg-blue-600',
        'Mid Laner': 'bg-purple-600',
        'Jungler': 'bg-green-600',
        
        # Generic/Flex
        'Flex': 'bg-gray-500',
        'Rifler': 'bg-gray-500',
        'Player': 'bg-gray-400',
    }
    
    return role_colors.get(role, 'bg-gray-500')


def format_roster_for_display(team) -> List[Dict]:
    """
    Format team roster for template display with proper role organization.
    
    Args:
        team: Team instance
        
    Returns:
        List of member dictionaries with formatted role information
    """
    from .models._legacy import TeamMembership
    
    members_data = []
    
    # Get all active members
    members = team.memberships.filter(
        status=TeamMembership.Status.ACTIVE
    ).select_related('profile__user').order_by('role', '-joined_at')
    
    for member in members:
        member_dict = {
            'id': member.id,
            'profile': member.profile,
            'username': member.profile.user.username,
            'membership_role': member.get_role_display(),
            'player_role': member.player_role,
            'display_role': member.display_full_role,
            'is_captain': member.role == TeamMembership.Role.CAPTAIN,
            'can_have_player_role': member.is_player_or_sub,
            'role_badge_color': get_role_badge_color(member.player_role, team.game) if member.player_role else 'bg-gray-400',
            'joined_at': member.joined_at,
        }
        
        members_data.append(member_dict)
    
    return members_data


# ═══════════════════════════════════════════════════════════════════════════
# API RESPONSE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def serialize_member_with_roles(membership) -> Dict:
    """
    Serialize a TeamMembership instance with both role types for API responses.
    
    Args:
        membership: TeamMembership instance
        
    Returns:
        Dictionary with full member and role information
    """
    return {
        'id': membership.id,
        'user': {
            'id': membership.profile.user.id,
            'username': membership.profile.user.username,
            'display_name': getattr(membership.profile, 'display_name', membership.profile.user.username),
            'avatar_url': membership.profile.avatar.url if membership.profile.avatar else None,
        },
        'membership_role': {
            'value': membership.role,
            'display': membership.get_role_display(),
        },
        'player_role': {
            'value': membership.player_role,
            'display': membership.get_player_role_display(),
            'description': membership.get_role_description(),
        },
        'display_full_role': membership.display_full_role,
        'is_captain': membership.role == membership.Role.CAPTAIN,
        'is_player_or_sub': membership.is_player_or_sub,
        'status': membership.status,
        'joined_at': membership.joined_at.isoformat(),
    }
