"""
Enum choices for organization and team models.

All enums use Django's TextChoices for database compatibility
and clean admin UI integration.
"""

from django.db import models


class TeamStatus(models.TextChoices):
    """
    Team lifecycle status.
    
    ACTIVE: Team can register for tournaments and play matches
    DELETED: Soft-deleted (preserves historical data)
    SUSPENDED: Temporarily banned from platform
    DISBANDED: Voluntarily dissolved by owner
    """
    ACTIVE = 'ACTIVE', 'Active'
    DELETED = 'DELETED', 'Deleted'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    DISBANDED = 'DISBANDED', 'Disbanded'


class MembershipStatus(models.TextChoices):
    """
    Team membership status.
    
    ACTIVE: Currently on roster
    INACTIVE: Left team (historical record)
    INVITED: Pending invitation acceptance
    SUSPENDED: Temporarily removed (disciplinary)
    """
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    INVITED = 'INVITED', 'Invited (Pending)'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class MembershipRole(models.TextChoices):
    """
    Organizational role within a team.
    
    Determines management permissions and responsibilities.
    Only PLAYER and SUBSTITUTE roles require Game Passports.
    
    OWNER: Full control (Independent Teams only)
    MANAGER: Day-to-day operations (roster, tournaments)
    COACH: View-only access, scrim scheduling
    PLAYER: Active roster member
    SUBSTITUTE: Bench player
    ANALYST: Staff (non-playing)
    SCOUT: Organization staff (view-only access)
    """
    OWNER = 'OWNER', 'Owner'
    MANAGER = 'MANAGER', 'Manager'
    COACH = 'COACH', 'Coach'
    PLAYER = 'PLAYER', 'Player'
    SUBSTITUTE = 'SUBSTITUTE', 'Substitute'
    ANALYST = 'ANALYST', 'Analyst'
    SCOUT = 'SCOUT', 'Scout'


class RosterSlot(models.TextChoices):
    """
    Physical roster slot assignment.
    
    Determines eligibility for tournament participation.
    
    STARTER: Active lineup (plays in matches)
    SUBSTITUTE: Bench player (can be substituted in)
    COACH: Non-playing staff
    ANALYST: Non-playing staff
    """
    STARTER = 'STARTER', 'Starter'
    SUBSTITUTE = 'SUBSTITUTE', 'Substitute'
    COACH = 'COACH', 'Coach (Non-playing)'
    ANALYST = 'ANALYST', 'Analyst (Non-playing)'


class RankingTier(models.TextChoices):
    """
    Crown Point ranking tiers.
    
    Tiers are calculated based on current CP thresholds:
    - CROWN: 80,000+ CP (Top 1% globally)
    - ASCENDANT: 40,000+ CP
    - DIAMOND: 15,000+ CP
    - PLATINUM: 5,000+ CP
    - GOLD: 1,500+ CP
    - SILVER: 500+ CP
    - BRONZE: 50+ CP
    - UNRANKED: <50 CP
    """
    UNRANKED = 'UNRANKED', 'Unranked'
    BRONZE = 'BRONZE', 'Bronze'
    SILVER = 'SILVER', 'Silver'
    GOLD = 'GOLD', 'Gold'
    PLATINUM = 'PLATINUM', 'Platinum'
    DIAMOND = 'DIAMOND', 'Diamond'
    ASCENDANT = 'ASCENDANT', 'Ascendant'
    CROWN = 'CROWN', 'Crown'


class ActivityActionType(models.TextChoices):
    """
    Audit log action types for team activity tracking.
    
    Used in TeamActivityLog to record all significant team events.
    """
    CREATE = 'CREATE', 'Team Created'
    UPDATE = 'UPDATE', 'Team Updated'
    DELETE = 'DELETE', 'Team Deleted'
    ROSTER_ADD = 'ROSTER_ADD', 'Member Added'
    ROSTER_REMOVE = 'ROSTER_REMOVE', 'Member Removed'
    ROSTER_UPDATE = 'ROSTER_UPDATE', 'Member Role Changed'
    MIGRATE = 'MIGRATE', 'Migrated to vNext'
    ACQUIRE = 'ACQUIRE', 'Acquired by Organization'
    TOURNAMENT_REGISTER = 'TOURNAMENT_REGISTER', 'Registered for Tournament'
    RANKING_UPDATE = 'RANKING_UPDATE', 'Ranking Changed'
