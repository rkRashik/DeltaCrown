# apps/teams/validators.py
"""
Validators for team and player management.

Provides comprehensive validation for roster management, role assignments,
and game-specific constraints.

CANONICAL VALIDATORS - Single source of truth for validation.
All forms, models, serializers, and views MUST use these validators.

Reference: MASTER_IMPLEMENTATION_BACKLOG.md - Task 1.3
"""
from django.core.exceptions import ValidationError
from typing import Optional, TYPE_CHECKING

from .constants import (
    # Name/Tag validation
    TEAM_NAME_MIN_LENGTH,
    TEAM_NAME_MAX_LENGTH,
    TEAM_NAME_PATTERN,
    TEAM_TAG_MIN_LENGTH,
    TEAM_TAG_MAX_LENGTH,
    TEAM_TAG_PATTERN,
    # Error messages
    ERROR_TEAM_NAME_REQUIRED,
    ERROR_TEAM_NAME_TOO_SHORT,
    ERROR_TEAM_NAME_TOO_LONG,
    ERROR_TEAM_NAME_INVALID_CHARS,
    ERROR_TEAM_NAME_EXISTS,
    ERROR_TEAM_TAG_REQUIRED,
    ERROR_TEAM_TAG_TOO_SHORT,
    ERROR_TEAM_TAG_TOO_LONG,
    ERROR_TEAM_TAG_INVALID_FORMAT,
    ERROR_TEAM_TAG_EXISTS,
    ERROR_ROSTER_FULL,
    # Status constants
    MEMBERSHIP_STATUS_ACTIVE,
    INVITE_STATUS_PENDING,
)
from .game_config import (
    get_game_config,
    get_max_roster_size,
    get_min_roster_size,
    validate_role_for_game,
)

if TYPE_CHECKING:
    from .models.base import BaseTeam, BasePlayerMembership


def validate_team_name(name: str, check_uniqueness: bool = False, exclude_id: Optional[int] = None) -> None:
    """
    THE canonical team name validator - use everywhere.
    
    Validates format, length, and optionally uniqueness.
    
    Args:
        name: Team name to validate
        check_uniqueness: Whether to check if name already exists
        exclude_id: Team ID to exclude from uniqueness check (for updates)
        
    Raises:
        ValidationError: If name is invalid
        
    Reference: MASTER_IMPLEMENTATION_BACKLOG.md - Task 1.3
    """
    if not name or not name.strip():
        raise ValidationError(ERROR_TEAM_NAME_REQUIRED)
    
    name = name.strip()
    
    if len(name) < TEAM_NAME_MIN_LENGTH:
        raise ValidationError(ERROR_TEAM_NAME_TOO_SHORT)
    
    if len(name) > TEAM_NAME_MAX_LENGTH:
        raise ValidationError(ERROR_TEAM_NAME_TOO_LONG)
    
    if not TEAM_NAME_PATTERN.match(name):
        raise ValidationError(ERROR_TEAM_NAME_INVALID_CHARS)
    
    # Optional uniqueness check
    if check_uniqueness:
        from .models._legacy import Team
        qs = Team.objects.filter(name__iexact=name)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        if qs.exists():
            raise ValidationError(ERROR_TEAM_NAME_EXISTS)


def validate_team_tag(tag: str, check_uniqueness: bool = False, exclude_id: Optional[int] = None) -> None:
    """
    THE canonical team tag validator - use everywhere.
    
    Validates format, length, and optionally uniqueness.
    
    Args:
        tag: Team tag to validate
        check_uniqueness: Whether to check if tag already exists
        exclude_id: Team ID to exclude from uniqueness check (for updates)
        
    Raises:
        ValidationError: If tag is invalid
        
    Reference: MASTER_IMPLEMENTATION_BACKLOG.md - Task 1.3
    """
    if not tag or not tag.strip():
        raise ValidationError(ERROR_TEAM_TAG_REQUIRED)
    
    tag = tag.strip().upper()
    
    if len(tag) < TEAM_TAG_MIN_LENGTH:
        raise ValidationError(ERROR_TEAM_TAG_TOO_SHORT)
    
    if len(tag) > TEAM_TAG_MAX_LENGTH:
        raise ValidationError(ERROR_TEAM_TAG_TOO_LONG)
    
    if not TEAM_TAG_PATTERN.match(tag):
        raise ValidationError(ERROR_TEAM_TAG_INVALID_FORMAT)
    
    # Optional uniqueness check
    if check_uniqueness:
        from .models._legacy import Team
        qs = Team.objects.filter(tag__iexact=tag)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        if qs.exists():
            raise ValidationError(ERROR_TEAM_TAG_EXISTS)


def validate_roster_capacity(
    team: 'BaseTeam',
    adding_count: int = 1,
    include_pending: bool = True
) -> None:
    """
    Validate that adding members won't exceed team capacity.
    
    Args:
        team: Team to check
        adding_count: Number of members being added
        include_pending: Whether to count pending invites
        
    Raises:
        ValidationError: If adding would exceed capacity
    """
    max_size = get_max_roster_size(team.game)
    current_count = team.get_memberships().filter(status=MEMBERSHIP_STATUS_ACTIVE).count()
    
    if include_pending:
        from .models._legacy import TeamInvite
        pending_count = TeamInvite.objects.filter(
            team=team,
            status=INVITE_STATUS_PENDING
        ).count()
        current_count += pending_count
    
    if current_count + adding_count > max_size:
        raise ValidationError(
            f"Adding {adding_count} member(s) would exceed team capacity "
            f"({current_count + adding_count}/{max_size})."
        )


def validate_minimum_roster(team: 'BaseTeam') -> None:
    """
    Validate team has minimum required members.
    
    Args:
        team: Team to check
        
    Raises:
        ValidationError: If team doesn't have enough members
    """
    min_size = get_min_roster_size(team.game)
    active_count = team.get_memberships().filter(status=MEMBERSHIP_STATUS_ACTIVE).count()
    
    if active_count < min_size:
        raise ValidationError(
            f"Team needs at least {min_size} active members "
            f"(currently has {active_count})."
        )


def validate_role_for_team(
    team: 'BaseTeam',
    role: str,
    membership_id: Optional[int] = None
) -> None:
    """
    Validate role is allowed for team's game.
    
    Args:
        team: Team the role is for
        role: Role to validate
        membership_id: ID of membership being updated (to exclude from uniqueness check)
        
    Raises:
        ValidationError: If role is invalid
    """
    if not validate_role_for_game(team.game, role):
        config = get_game_config(team.game)
        raise ValidationError(
            f"Invalid role '{role}' for {config.name}. "
            f"Valid roles: {', '.join(config.roles)}"
        )
    
    # For games requiring unique roles (like Dota2), check uniqueness
    config = get_game_config(team.game)
    if config.requires_unique_roles:
        query = team.get_memberships().filter(
            role=role,
            status=MEMBERSHIP_STATUS_ACTIVE,
            is_starter=True
        )
        
        if membership_id:
            query = query.exclude(id=membership_id)
        
        if query.exists():
            raise ValidationError(
                f"Role '{role}' is already taken by another starting player. "
                f"{config.name} requires unique roles."
            )


def validate_starters_count(
    team: 'BaseTeam',
    is_starter: bool,
    membership_id: Optional[int] = None
) -> None:
    """
    Validate adding a starter won't exceed maximum.
    
    Args:
        team: Team to check
        is_starter: Whether player is a starter
        membership_id: ID of membership being updated
        
    Raises:
        ValidationError: If too many starters
    """
    if not is_starter:
        return  # Substitutes don't need validation
    
    config = get_game_config(team.game)
    query = team.get_memberships().filter(
        status=MEMBERSHIP_STATUS_ACTIVE,
        is_starter=True
    )
    
    if membership_id:
        query = query.exclude(id=membership_id)
    
    starters_count = query.count()
    
    if starters_count >= config.max_starters:
        raise ValidationError(
            f"Team already has maximum starters ({config.max_starters}). "
            f"Player must be set as substitute."
        )


def validate_substitutes_count(
    team: 'BaseTeam',
    is_starter: bool,
    membership_id: Optional[int] = None
) -> None:
    """
    Validate adding a substitute won't exceed maximum.
    
    Args:
        team: Team to check
        is_starter: Whether player is a starter
        membership_id: ID of membership being updated
        
    Raises:
        ValidationError: If too many substitutes
    """
    if is_starter:
        return  # Starters don't need this validation
    
    config = get_game_config(team.game)
    query = team.get_memberships().filter(
        status=MEMBERSHIP_STATUS_ACTIVE,
        is_starter=False
    )
    
    if membership_id:
        query = query.exclude(id=membership_id)
    
    subs_count = query.count()
    
    if subs_count >= config.max_substitutes:
        raise ValidationError(
            f"Team already has maximum substitutes ({config.max_substitutes})."
        )


def validate_unique_ign_in_team(
    team: 'BaseTeam',
    ign: str,
    membership_id: Optional[int] = None
) -> None:
    """
    Validate IGN is unique within team.
    
    Args:
        team: Team to check
        ign: In-game name to validate
        membership_id: ID of membership being updated
        
    Raises:
        ValidationError: If IGN is duplicate
    """
    if not ign or not ign.strip():
        return  # Empty IGN is allowed
    
    query = team.get_memberships().filter(
        in_game_name__iexact=ign.strip()
    )
    
    if membership_id:
        query = query.exclude(id=membership_id)
    
    if query.exists():
        raise ValidationError(
            f"IGN '{ign}' is already used by another team member."
        )


def validate_captain_is_member(team: 'BaseTeam', captain_profile) -> None:
    """
    Validate captain is an active team member.
    
    Args:
        team: Team to check
        captain_profile: UserProfile of proposed captain
        
    Raises:
        ValidationError: If captain is not an active member
    """
    if not team.pk:
        return  # Can't validate for unsaved teams
    
    is_member = team.get_memberships().filter(
        profile=captain_profile,
        status=MEMBERSHIP_STATUS_ACTIVE
    ).exists()
    
    if not is_member:
        raise ValidationError(
            "Captain must be an active member of the team."
        )


def validate_player_not_in_game_team(profile, game_code: str) -> None:
    """
    Validate player is not already in another team for this game.
    
    Args:
        profile: UserProfile to check
        game_code: Game identifier
        
    Raises:
        ValidationError: If player is already in a team
    """
    from .models.game_specific import GAME_MEMBERSHIP_MODELS
    
    if game_code not in GAME_MEMBERSHIP_MODELS:
        return  # Unknown game, skip validation
    
    membership_model = GAME_MEMBERSHIP_MODELS[game_code]
    
    existing = membership_model.objects.filter(
        profile=profile,
        status=MEMBERSHIP_STATUS_ACTIVE
    ).exists()
    
    if existing:
        game_name = get_game_config(game_code).name
        raise ValidationError(
            f"You are already in an active {game_name} team. "
            f"Leave your current team before joining another."
        )


def validate_tournament_roster_lock(team: 'BaseTeam') -> None:
    """
    Validate team roster can be modified (not locked by tournament).
    
    Args:
        team: Team to check
        
    Raises:
        ValidationError: If roster is locked
    """
    # Check if team is registered in active tournaments
    try:
        from django.apps import apps
        
        # Get Registration model via apps registry
        Registration = apps.get_model('tournaments', 'Registration')
        
        active_registrations = Registration.objects.filter(
            team=team,
            status__in=['APPROVED', 'CONFIRMED', 'CHECKED_IN']
        ).exists()
        
        if active_registrations:
            raise ValidationError(
                "Cannot modify roster while team is registered in an active tournament. "
                "Please contact tournament organizers."
            )
    except ImportError:
        pass  # Tournaments app not available
    except Exception:
        pass  # Fail gracefully


def validate_membership_data(
    membership: 'BasePlayerMembership',
    team: Optional['BaseTeam'] = None
) -> None:
    """
    Comprehensive validation for player membership.
    
    Args:
        membership: Membership to validate
        team: Team (if not set on membership yet)
        
    Raises:
        ValidationError: If validation fails
    """
    team = team or getattr(membership, 'team', None)
    if not team:
        raise ValidationError("Team is required for membership validation.")
    
    # Validate role
    if membership.role:
        validate_role_for_team(team, membership.role, membership.pk)
    
    # Validate secondary role
    if membership.secondary_role:
        validate_role_for_team(team, membership.secondary_role, membership.pk)
    
    # Validate IGN uniqueness
    if membership.in_game_name:
        validate_unique_ign_in_team(team, membership.in_game_name, membership.pk)
    
    # Validate roster capacity
    if membership.status == MEMBERSHIP_STATUS_ACTIVE and not membership.pk:
        validate_roster_capacity(team, adding_count=1, include_pending=False)
    
    # Validate starters/subs count
    if membership.status == MEMBERSHIP_STATUS_ACTIVE:
        if membership.is_starter:
            validate_starters_count(team, True, membership.pk)
        else:
            validate_substitutes_count(team, False, membership.pk)
    
    # Validate player not in another team for same game
    if membership.status == MEMBERSHIP_STATUS_ACTIVE and not membership.pk:
        validate_player_not_in_game_team(membership.profile, team.game)
