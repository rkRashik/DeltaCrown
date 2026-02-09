"""
Shared test factories for DeltaCrown tests.

Provides consistent, reusable factories for creating test data:
- Users (with required email addresses)
- Teams (independent and org-owned)
- Ranking snapshots (optional)
"""

from django.contrib.auth import get_user_model
from apps.organizations.models import Team, TeamMembership, TeamMembershipEvent
from apps.organizations.choices import TeamStatus, MembershipRole, MembershipStatus, MembershipEventType
from apps.games.models import Game

User = get_user_model()


def create_user(username, email=None, password='testpass123', **kwargs):
    """
    Create a user with required email field.
    
    Args:
        username: Unique username
        email: Email address (defaults to <username>@example.com)
        password: Password (default: 'testpass123')
        **kwargs: Additional user fields
    
    Returns:
        User instance
    """
    if email is None:
        email = f"{username}@example.com"
    
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        **kwargs
    )


def create_independent_team(name, creator, game_id=1, **kwargs):
    """
    Create an independent team (organization=None).
    
    Args:
        name: Team name
        creator: User who creates the team (becomes creator)
        game_id: Game ID (defaults to 1)
        **kwargs: Additional team fields (status, visibility, etc.)
    
    Returns:
        Tuple of (Team, TeamMembership) - team and creator's membership
    """
    # Set defaults
    kwargs.setdefault('status', TeamStatus.ACTIVE)
    kwargs.setdefault('visibility', 'PUBLIC')
    kwargs.setdefault('organization', None)
    kwargs.setdefault('region', 'NA')
    
    # Create team
    team = Team.objects.create(
        name=name,
        game_id=game_id,
        created_by=creator,
        **kwargs
    )
    
    # Create membership for creator
    membership = TeamMembership.objects.create(
        team=team,
        user=creator,
        role=MembershipRole.MANAGER,
        status=MembershipStatus.ACTIVE,
        game_id=game_id,
    )
    
    # Create JOINED event (append-only ledger)
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=creator,
        actor=creator,
        event_type=MembershipEventType.JOINED,
        new_role=MembershipRole.MANAGER,
        new_status=MembershipStatus.ACTIVE,
        metadata={'team_creation': True},
    )
    
    return team, membership


def create_org_team(name, creator, organization, game_id=1, **kwargs):
    """
    Create an organization-owned team.
    
    Args:
        name: Team name
        creator: User who creates the team
        organization: Organization that owns the team
        game_id: Game ID (defaults to 1)
        **kwargs: Additional team fields
    
    Returns:
        Tuple of (Team, TeamMembership) - team and creator's membership
    """
    # Set defaults
    kwargs.setdefault('status', TeamStatus.ACTIVE)
    kwargs.setdefault('visibility', 'PUBLIC')
    kwargs.setdefault('region', 'NA')
    kwargs['organization'] = organization
    
    # Create team
    team = Team.objects.create(
        name=name,
        game_id=game_id,
        created_by=creator,
        **kwargs
    )
    
    # Create membership for creator
    membership = TeamMembership.objects.create(
        team=team,
        user=creator,
        role=MembershipRole.MANAGER,
        status=MembershipStatus.ACTIVE,
        game_id=game_id,
    )
    
    # Create JOINED event (append-only ledger)
    TeamMembershipEvent.objects.create(
        membership=membership,
        team=team,
        user=creator,
        actor=creator,
        event_type=MembershipEventType.JOINED,
        new_role=MembershipRole.MANAGER,
        new_status=MembershipStatus.ACTIVE,
        metadata={'team_creation': True, 'organization_team': True},
    )
    
    return team, membership


def create_ranking_snapshot(team, score=0, tier='UNRANKED', rank=None):
    """
    Create a ranking snapshot for a team.
    
    Args:
        team: Team instance
        score: Global score (default: 0)
        tier: Global tier (default: 'UNRANKED')
        rank: Optional global rank
    
    Returns:
        TeamGlobalRankingSnapshot instance (if model exists)
    """
    try:
        from apps.organizations.models import TeamGlobalRankingSnapshot
        
        return TeamGlobalRankingSnapshot.objects.create(
            team=team,
            global_score=score,
            global_tier=tier,
            global_rank=rank
        )
    except ImportError:
        # Model doesn't exist, return None
        return None

