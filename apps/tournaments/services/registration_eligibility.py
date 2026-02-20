"""
Registration Eligibility Service

Checks if a user is eligible to register for a tournament and provides
user-friendly messages and action items.
"""

from django.contrib.auth.models import User
from apps.tournaments.models import Tournament
from apps.organizations.models import Organization, Team, TeamMembership


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
        
        # Check 3: Tournament capacity — allow waitlist instead of blocking
        is_full = tournament.is_full()
        if is_full:
            # Don't block — user can join the waitlist
            pass
        
        # Check 4: For team tournaments, check team requirements
        if tournament.participation_type == 'team':
            result = RegistrationEligibilityService._check_team_eligibility(tournament, user)
            if not result.is_eligible:
                # Check for guest team fallback
                allows_guest = getattr(tournament, 'max_guest_teams', 0) and tournament.max_guest_teams > 0
                if allows_guest and result.action_type in ('create_or_join_team', 'contact_captain', 'request_permission', 'manage_roster'):
                    from apps.tournaments.models import Registration
                    current_guest_count = Registration.objects.filter(
                        tournament=tournament,
                        is_guest_team=True,
                        is_deleted=False,
                    ).exclude(
                        status__in=[Registration.CANCELLED, Registration.REJECTED]
                    ).count()
                    remaining = tournament.max_guest_teams - current_guest_count
                    if remaining > 0:
                        return EligibilityResult(
                            is_eligible=True,
                            reason=f"No eligible team found, but you can register as a guest team ({remaining} slot(s) available).",
                            action_type='guest_team',
                            action_url=f'/tournaments/{tournament.slug}/register/?guest=1',
                            action_label='Register as Guest Team'
                        )
                return result
        
        # If at capacity, return waitlist-eligible
        if is_full:
            return EligibilityResult(
                is_eligible=True,
                reason=f"This tournament is full ({tournament.max_participants} participants). You will be placed on the waitlist.",
                action_type='waitlist',
                action_url=f'/tournaments/{tournament.slug}/register/',
                action_label='Join Waitlist'
            )

        # Check 5: RegistrationRule auto-evaluation (P4-T05)
        rule_result = RegistrationEligibilityService._evaluate_registration_rules(tournament, user)
        if rule_result is not None:
            return rule_result

        # Solo tournaments / eligible team tournament — user is eligible
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
        
        # Get user's teams for this game (via membership)
        user_teams = Team.objects.filter(
            game_id=tournament.game_id,
            vnext_memberships__user=user,
            vnext_memberships__status='ACTIVE',
            status='ACTIVE'
        ).distinct()
        
        # Also include org teams where user is the CEO (even without membership)
        ceo_org_ids = Organization.objects.filter(ceo=user).values_list('id', flat=True)
        ceo_teams = Team.objects.filter(
            game_id=tournament.game_id,
            organization_id__in=ceo_org_ids,
            status='ACTIVE'
        ).exclude(id__in=user_teams.values_list('id', flat=True))
        
        all_teams = list(user_teams) + list(ceo_teams)
        
        # Check if user has any team for this game
        if not all_teams:
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
        
        # CEO teams are automatically permitted (org authority)
        for team in ceo_teams:
            permitted_teams.append((team, None))
        
        for team in user_teams:
            member = TeamMembership.objects.filter(
                team=team, user=user, status='ACTIVE'
            ).first()
            if not member:
                blocked_teams.append(team)
                continue
            # Check either by role OR by explicit register_tournaments permission
            # OR by being the CEO of the team's organization
            is_ceo = team.organization_id and team.organization_id in ceo_org_ids
            if member.role in permissive_roles or member.has_permission('register_tournaments') or is_ceo:
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
        def _active_count(t):
            return t.memberships.filter(status='ACTIVE').count()

        roster_ready = [team for team, _ in permitted_teams if _active_count(team) >= min_roster]
        if not roster_ready:
            # Use the first permitted team for messaging
            team = permitted_teams[0][0]
            current = _active_count(team)
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
        
        Returns list of teams where user has registration permission
        (by role, explicit register_tournaments permission, or org CEO status).
        """
        if not user.is_authenticated or tournament.participation_type != 'team':
            return Team.objects.none()
        
        # Get ALL active teams where user is an active member for this game
        user_teams = Team.objects.filter(
            game_id=tournament.game_id,
            vnext_memberships__user=user,
            vnext_memberships__status='ACTIVE',
            status='ACTIVE'
        ).distinct()
        
        # Also include org teams where user is CEO
        ceo_org_ids = Organization.objects.filter(ceo=user).values_list('id', flat=True)
        
        permissive_roles = [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER,
            TeamMembership.Role.CAPTAIN,
        ]
        
        eligible_ids = []
        
        # CEO gets access to all org teams for this game
        if ceo_org_ids:
            ceo_team_ids = Team.objects.filter(
                game_id=tournament.game_id,
                organization_id__in=ceo_org_ids,
                status='ACTIVE'
            ).values_list('id', flat=True)
            eligible_ids.extend(ceo_team_ids)
        
        for team in user_teams:
            if team.id in eligible_ids:
                continue  # already added via CEO
            member = TeamMembership.objects.filter(
                team=team, user=user, status='ACTIVE'
            ).first()
            if not member:
                continue
            if member.role in permissive_roles or member.has_permission('register_tournaments'):
                eligible_ids.append(team.id)
        
        return Team.objects.filter(id__in=eligible_ids)

    # ------------------------------------------------------------------ #
    # P4-T05: RegistrationRule Auto-Evaluation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _evaluate_registration_rules(tournament: Tournament, user) -> 'EligibilityResult | None':
        """
        Evaluate active RegistrationRules for this tournament against the user.

        Checks rules in priority order. If an AUTO_REJECT rule matches, the user
        is blocked with a clear error message. AUTO_APPROVE / FLAG_FOR_REVIEW
        return None (caller proceeds normally — the smart-reg wizard handles those
        at submission time).

        Returns:
            EligibilityResult if user is blocked by a rule, else None
        """
        from apps.tournaments.models.smart_registration import RegistrationRule

        rules = RegistrationRule.objects.filter(
            tournament=tournament,
            is_active=True,
        ).order_by('priority', 'id')

        if not rules.exists():
            return None

        # Build user context for rule evaluation
        user_data = RegistrationEligibilityService._build_user_rule_context(user)

        for rule in rules:
            if rule.rule_type != RegistrationRule.AUTO_REJECT:
                continue  # Only enforce rejection rules at eligibility gate

            matched = rule.evaluate(user_data, {})
            if matched:
                reason = rule.reason_template or f"You do not meet the requirement: {rule.name}"
                return EligibilityResult(
                    is_eligible=False,
                    reason=reason,
                    action_type='rule_blocked',
                    action_url='',
                    action_label='Requirement Not Met',
                )

        return None

    @staticmethod
    def _build_user_rule_context(user) -> dict:
        """
        Build a flat dict of user attributes for rule evaluation.

        Supported keys (matching RegistrationRule condition fields):
          - account_age_days: int
          - rank: str (from profile game_stats if available)
          - tournaments_played: int
          - email_verified: bool
        """
        from django.utils import timezone

        ctx: dict = {}

        # Account age
        if hasattr(user, 'date_joined') and user.date_joined:
            ctx['account_age_days'] = (timezone.now() - user.date_joined).days
        else:
            ctx['account_age_days'] = 0

        # Email verified
        ctx['email_verified'] = getattr(user, 'is_active', False)

        # Tournaments played (count of confirmed registrations)
        try:
            from apps.tournaments.models import Registration
            ctx['tournaments_played'] = Registration.objects.filter(
                user=user,
                status=Registration.CONFIRMED,
                is_deleted=False,
            ).count()
        except Exception:
            ctx['tournaments_played'] = 0

        # Rank (from user profile game_stats, if present)
        try:
            profile = getattr(user, 'profile', None)
            if profile:
                game_stats = getattr(profile, 'game_stats', None) or {}
                ctx['rank'] = game_stats.get('rank', '')
            else:
                ctx['rank'] = ''
        except Exception:
            ctx['rank'] = ''

        return ctx
