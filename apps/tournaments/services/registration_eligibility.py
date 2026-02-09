"""
Registration Eligibility Service

Checks if a user is eligible to register for a tournament and provides
user-friendly messages and action items.
"""

from django.contrib.auth.models import User
from apps.tournaments.models import Tournament
from apps.organizations.models import Team, TeamMembership


class EligibilityResult:
    """Result of eligibility check"""
    
    def __init__(self, is_eligible, reason='', action_type='', action_url='', action_label=''):
        self.is_eligible = is_eligible
        self.reason = reason
        self.action_type = action_type  # 'login', 'create_team', 'join_team', 'request_permission'
        self.action_url = action_url
        self.action_label = action_label
    
    def to_dict(self):
        return {
            'is_eligible': self.is_eligible,
            'reason': self.reason,
            'action_type': self.action_type,
            'action_url': self.action_url,
            'action_label': self.action_label,
        }


class RegistrationEligibilityService:
    """
    Service to check registration eligibility and provide actionable feedback.
    
    Checks:
    1. User is logged in
    2. For team tournaments: User has a team for that game
    3. For team tournaments: User has permission to register
    4. Registration is still open
    5. Tournament not at capacity
    """
    
    @staticmethod
    def check_eligibility(tournament: Tournament, user: User = None) -> EligibilityResult:
        """
        Check if user is eligible to register for tournament.
        
        Returns EligibilityResult with:
        - is_eligible: Boolean
        - reason: User-friendly message
        - action_type: Type of action needed
        - action_url: URL for the action
        - action_label: Button label for the action
        """
        
        # Check 1: User must be logged in
        if not user or not user.is_authenticated:
            return EligibilityResult(
                is_eligible=False,
                reason="You need to sign in to register for this tournament.",
                action_type='login',
                action_url=f'/accounts/login/?next=/tournaments/{tournament.slug}/',
                action_label='Sign In to Register'
            )
        
        # Check 2: Registration must be open
        if not tournament.is_registration_open():
            if tournament.has_registration_started():
                reason = "Registration for this tournament has closed."
            else:
                reason = f"Registration opens on {tournament.registration_start.strftime('%B %d, %Y at %I:%M %p')}."
            
            return EligibilityResult(
                is_eligible=False,
                reason=reason,
                action_type='wait',
                action_url='',
                action_label='Registration Closed'
            )
        
        # Check 3: Tournament must not be at capacity
        if tournament.is_full():
            return EligibilityResult(
                is_eligible=False,
                reason=f"This tournament is full ({tournament.max_participants} participants). You may join the waitlist.",
                action_type='waitlist',
                action_url=f'/tournaments/{tournament.slug}/waitlist/',
                action_label='Join Waitlist'
            )
        
        # Check 4: For team tournaments, check team requirements
        if tournament.participation_type == 'team':
            return RegistrationEligibilityService._check_team_eligibility(tournament, user)
        
        # Solo tournaments - user is eligible
        return EligibilityResult(
            is_eligible=True,
            reason='',
            action_type='',
            action_url='',
            action_label=''
        )
    
    @staticmethod
    def _check_team_eligibility(tournament: Tournament, user: User) -> EligibilityResult:
        """Check team-specific eligibility requirements including minimum roster size."""
        
        # Game-derived minimum roster size
        min_roster = getattr(tournament.game, 'min_team_size', 1) or 1
        
        # Get user's teams for this game
        user_teams = Team.objects.filter(
            game_id=tournament.game_id,
            vnext_memberships__user=user,
            status='ACTIVE'
        ).distinct()
        
        # Check if user has any team for this game
        if not user_teams.exists():
            return EligibilityResult(
                is_eligible=False,
                reason=f"You need to join a {tournament.game.name} team to register for this tournament.",
                action_type='create_or_join_team',
                action_url=f'/teams/create/?game={tournament.game.slug}',
                action_label='Create Team'
            )
        
        permissive_roles = [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER,
            TeamMembership.Role.CAPTAIN,  # legacy support
        ]
        
        # Build list of teams where user has permission
        permitted_teams = []
        blocked_teams = []
        for team in user_teams:
            member = TeamMembership.objects.filter(team=team, user=user).first()
            if not member:
                blocked_teams.append(team)
                continue
            if member.role in permissive_roles:
                permitted_teams.append((team, member))
            else:
                blocked_teams.append(team)
        
        if not permitted_teams:
            if len(blocked_teams) == 1:
                team = blocked_teams[0]
                return EligibilityResult(
                    is_eligible=False,
                    reason=f"You don't have permission to register team '{team.name}' for tournaments. Request permission from your team captain or manager.",
                    action_type='request_permission',
                    action_url=f'/tournaments/{tournament.slug}/request-permission/?team={team.id}',
                    action_label='Request Permission'
                )
            return EligibilityResult(
                is_eligible=False,
                reason="You don't have permission to register any of your teams for tournaments. Contact your team captain or manager.",
                action_type='contact_captain',
                action_url='',
                action_label='Contact Team Captain'
            )
        
        # Filter permitted teams by roster size
        roster_ready = [team for team, _ in permitted_teams if team.members_count >= min_roster]
        if not roster_ready:
            # Use the first permitted team for messaging
            team = permitted_teams[0][0]
            current = team.members_count
            # Build URL (slug preferred, fallback to pk)
            manage_url = team.get_absolute_url()
            return EligibilityResult(
                is_eligible=False,
                reason=(
                    f"Team '{team.name}' needs at least {min_roster} active members to register; current roster has {current}. "
                    f"Add members to meet the minimum requirement."
                ),
                action_type='manage_roster',
                action_url=manage_url,
                action_label='Manage Roster'
            )
        
        # At least one team meets permission + roster requirement
        return EligibilityResult(
            is_eligible=True,
            reason='',
            action_type='',
            action_url='',
            action_label=''
        )
    
    @staticmethod
    def get_eligible_teams(tournament: Tournament, user: User):
        """
        Get list of teams user can register for this tournament.
        
        Returns queryset of teams where user has registration permission.
        """
        if not user.is_authenticated or tournament.participation_type != 'team':
            return Team.objects.none()
        
        # Get teams where user is owner/manager
        eligible_teams = Team.objects.filter(
            game_id=tournament.game_id,
            vnext_memberships__user=user,
            vnext_memberships__role__in=['OWNER', 'MANAGER'],
            status='ACTIVE'
        ).distinct()
        
        return eligible_teams
