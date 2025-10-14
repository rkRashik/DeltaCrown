# apps/teams/templatetags/dual_role_tags.py
"""
Template tags for the dual-role system.

Usage in templates:
    {% load dual_role_tags %}
    
    {{ membership|display_full_role }}
    {{ membership|role_badge_color:team.game }}
    {% if team.game|supports_player_roles %}...{% endif %}
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def display_full_role(membership):
    """
    Display full role combining membership and player role.
    
    Usage: {{ membership|display_full_role }}
    Returns: "Player (Duelist)" or "Substitute (AWPer)" or "Coach"
    """
    if hasattr(membership, 'display_full_role'):
        return membership.display_full_role
    return membership.get_role_display() if hasattr(membership, 'get_role_display') else str(membership.role)


@register.filter
def role_badge_color(role, game_code):
    """
    Get badge color for a role.
    
    Usage: {{ membership.player_role|role_badge_color:team.game }}
    Returns: CSS class like "bg-red-500"
    """
    from apps.teams.dual_role_system import get_role_badge_color
    return get_role_badge_color(role, game_code)


@register.filter
def supports_player_roles(game_code):
    """
    Check if a game supports player roles.
    
    Usage: {% if team.game|supports_player_roles %}...{% endif %}
    """
    from apps.teams.dual_role_system import game_supports_player_roles
    return game_supports_player_roles(game_code)


@register.filter
def get_player_roles(game_code):
    """
    Get available player roles for a game.
    
    Usage: {% for role in team.game|get_player_roles %}...{% endfor %}
    """
    from apps.teams.dual_role_system import get_player_roles_for_game
    return get_player_roles_for_game(game_code)


@register.filter
def can_have_player_role(membership):
    """
    Check if a membership can have a player role.
    
    Usage: {% if membership|can_have_player_role %}...{% endif %}
    """
    if hasattr(membership, 'is_player_or_sub'):
        return membership.is_player_or_sub
    return False


@register.simple_tag
def format_roster_display(team):
    """
    Format roster for display with role information.
    
    Usage: {% format_roster_display team as roster_data %}
    """
    from apps.teams.dual_role_system import format_roster_for_display
    return format_roster_for_display(team)


@register.inclusion_tag('teams/components/role_badge.html')
def role_badge(role, game_code=''):
    """
    Render a role badge component.
    
    Usage: {% role_badge membership.player_role team.game %}
    """
    from apps.teams.dual_role_system import get_role_badge_color
    
    return {
        'role': role,
        'color': get_role_badge_color(role, game_code) if role else 'bg-gray-400',
        'has_role': bool(role)
    }


@register.inclusion_tag('teams/components/member_card.html')
def member_card(membership, team):
    """
    Render a team member card with role information.
    
    Usage: {% member_card membership team %}
    """
    from apps.teams.dual_role_system import get_role_badge_color
    
    return {
        'membership': membership,
        'team': team,
        'display_role': membership.display_full_role if hasattr(membership, 'display_full_role') else membership.get_role_display(),
        'role_color': get_role_badge_color(membership.player_role, team.game) if membership.player_role else 'bg-gray-400',
    }


@register.filter
def validate_player_role(role, game_code):
    """
    Validate if a player role is valid for a game.
    
    Usage: {% if role|validate_player_role:game_code %}...{% endif %}
    Returns: Tuple of (is_valid, error_message)
    """
    from apps.teams.dual_role_system import validate_player_role
    is_valid, error = validate_player_role(game_code, role)
    return is_valid


@register.simple_tag
def get_roster_by_roles(team):
    """
    Get roster organized by in-game roles.
    
    Usage: {% get_roster_by_roles team as roster_by_role %}
    Returns: Dict mapping roles to members
    """
    from apps.teams.dual_role_system import get_roster_by_roles
    return get_roster_by_roles(team)
