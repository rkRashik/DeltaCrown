"""
Registration Eligibility Service

Centralized service for checking if a user can register for a tournament.
Used by:
- Tournament detail page
- Tournament list cards
- Registration forms
- Template context processors

Ensures consistent eligibility logic across all views and templates.
"""

from typing import Dict, Optional, Tuple
from django.contrib.auth.models import User
from apps.tournaments.models import Tournament, Registration
from apps.organizations.models import Team, TeamMembership
from apps.user_profile.models import UserProfile


class RegistrationEligibilityService:
    """
    Service for checking tournament registration eligibility.
    
    Provides a single source of truth for registration eligibility checks.
    """
    
    @staticmethod
    def check_eligibility(tournament: Tournament, user: Optional[User]) -> Dict:
        """
        Check if a user can register for a tournament.
        
        Args:
            tournament: Tournament to check
            user: User attempting to register
            
        Returns:
            Dict with:
            - can_register (bool): Whether user can register
            - reason (str): Reason why they can't (if can_register=False)
            - status (str): Status code for UI logic
            - registration (Registration|None): Existing registration if any
            - action_url (str): URL for next action
            - action_label (str): Label for action button
        """
        # Default response
        result = {
            'can_register': False,
            'reason': '',
            'status': 'unknown',
            'registration': None,
            'action_url': '',
            'action_label': 'View Details',
        }
        
        # Check if user is authenticated
        if not user or not user.is_authenticated:
            result.update({
                'reason': 'You must be logged in to register.',
                'status': 'not_authenticated',
                'action_url': '/accounts/login/',
                'action_label': 'Login to Register',
            })
            return result
        
        # Check for existing registration (user-level for solo, or team-level for team tournaments)
        registration = Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).first()
        
        if registration:
            result.update({
                'reason': 'You are already registered for this tournament.',
                'status': 'already_registered',
                'registration': registration,
                'action_url': f'/tournaments/{tournament.slug}/lobby/',
                'action_label': 'Enter Lobby',
            })
            return result
        
        # For team tournaments, also check if user's team is registered (even if another member registered it)
        if tournament.participation_type == Tournament.TEAM:
            try:
                user_profile = UserProfile.objects.filter(user=user).first()
                if user_profile:
                    # Get all user's teams for this game
                    from apps.organizations.models import Team, TeamMembership
                    user_team_ids = TeamMembership.objects.filter(
                        user=user_profile.user,
                        status=TeamMembership.Status.ACTIVE
                    ).values_list('team_id', flat=True)
                    
                    # Check if any of user's teams are registered
                    team_registration = Registration.objects.filter(
                        tournament=tournament,
                        team_id__in=user_team_ids,
                        is_deleted=False
                    ).exclude(
                        status__in=[Registration.CANCELLED, Registration.REJECTED]
                    ).first()
                    
                    if team_registration:
                        result.update({
                            'reason': 'Your team is already registered for this tournament.',
                            'status': 'team_already_registered',
                            'registration': team_registration,
                            'action_url': f'/tournaments/{tournament.slug}/lobby/',
                            'action_label': 'Enter Lobby',
                        })
                        return result
            except Exception:
                pass  # Continue with other checks if team check fails
        
        # Check tournament status
        if tournament.status == Tournament.COMPLETED:
            result.update({
                'reason': 'This tournament has ended.',
                'status': 'completed',
                'action_url': f'/tournaments/{tournament.slug}/results/',
                'action_label': 'View Results',
            })
            return result
        
        if tournament.status == Tournament.CANCELLED:
            result.update({
                'reason': 'This tournament has been cancelled.',
                'status': 'cancelled',
                'action_url': f'/tournaments/{tournament.slug}/',
                'action_label': 'View Details',
            })
            return result
        
        if tournament.status not in [Tournament.REGISTRATION_OPEN, Tournament.PUBLISHED]:
            result.update({
                'reason': 'Registration is not currently open.',
                'status': 'registration_closed',
                'action_url': f'/tournaments/{tournament.slug}/',
                'action_label': 'View Details',
            })
            return result
        
        # Check if tournament is full
        if tournament.is_full():
            result.update({
                'reason': 'This tournament is full.',
                'status': 'full',
                'action_url': f'/tournaments/{tournament.slug}/',
                'action_label': 'View Details',
            })
            return result
        
        # Team tournament eligibility checks
        if tournament.participation_type == Tournament.TEAM:
            team_check = RegistrationEligibilityService._check_team_eligibility(
                tournament, user
            )
            
            if not team_check['eligible']:
                result.update({
                    'reason': team_check['reason'],
                    'status': team_check['status'],
                    'action_url': team_check.get('action_url', f'/tournaments/{tournament.slug}/'),
                    'action_label': team_check.get('action_label', 'View Details'),
                })
                return result
        
        # User is eligible to register
        result.update({
            'can_register': True,
            'reason': '',
            'status': 'eligible',
            'action_url': (
                f'/tournaments/{tournament.slug}/register/team/'
                if tournament.participation_type == Tournament.TEAM
                else f'/tournaments/{tournament.slug}/register/'
            ),
            'action_label': 'Register Now',
        })
        
        return result
    
    @staticmethod
    def _check_team_eligibility(tournament: Tournament, user: User) -> Dict:
        """
        Check team-specific eligibility for a tournament.
        
        Returns:
            Dict with eligible (bool), reason (str), status (str)
        """
        try:
            # Get user profile
            user_profile = UserProfile.objects.filter(user=user).first()
            if not user_profile:
                return {
                    'eligible': False,
                    'reason': 'You need to complete your profile before registering.',
                    'status': 'no_profile',
                    'action_url': '/profile/edit/',
                    'action_label': 'Complete Profile',
                }
            
            # Get user's teams for this game
            user_teams = Team.objects.filter(
                game_id=tournament.game_id,
                vnext_memberships__user=user_profile.user,
                vnext_memberships__status=TeamMembership.Status.ACTIVE,
                status='ACTIVE'
            ).distinct()
            
            if not user_teams.exists():
                return {
                    'eligible': False,
                    'reason': f'You need to join a {tournament.game.name} team to register.',
                    'status': 'no_team',
                    'action_url': '/teams/create/',
                    'action_label': 'Create Team',
                }
            
            # Check if user has permission to register any team
            can_register_team = False
            team_with_permission = None
            
            for team in user_teams:
                membership = TeamMembership.objects.filter(
                    team=team,
                    user=user_profile.user,
                    status=TeamMembership.Status.ACTIVE
                ).first()
                
                if membership and (
                    membership.role in [
                        TeamMembership.Role.OWNER,
                        TeamMembership.Role.MANAGER,
                        TeamMembership.Role.CAPTAIN
                    ]
                ):
                    can_register_team = True
                    team_with_permission = team
                    break
            
            if not can_register_team:
                return {
                    'eligible': False,
                    'reason': 'You don\'t have permission to register any of your teams.',
                    'status': 'no_permission',
                    'action_url': '/teams/',
                    'action_label': 'View Teams',
                }
            
            # Check if team is already registered
            team_registration = Registration.objects.filter(
                tournament=tournament,
                team_id=team_with_permission.id,
                is_deleted=False
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).first()
            
            if team_registration:
                return {
                    'eligible': False,
                    'reason': f'Your team "{team_with_permission.name}" is already registered.',
                    'status': 'team_already_registered',
                    'action_url': f'/tournaments/{tournament.slug}/lobby/',
                    'action_label': 'Enter Lobby',
                }
            
            # Check team roster size
            # ============================================================================
            # ADAPTER MIGRATION POINT (P3-T3): Roster validation now uses TeamAdapter
            # This routes to either legacy teams or vNext organizations based on flags
            # ============================================================================
            from apps.organizations.adapters.team_adapter import TeamAdapter
            
            try:
                adapter = TeamAdapter()
                validation_result = adapter.validate_roster(
                    team_id=team_with_permission.id,
                    tournament_id=tournament.id,
                    game_id=tournament.game.id if hasattr(tournament, 'game') else None,
                )
                
                # Adapter returns: {'is_valid': bool, 'errors': [], 'warnings': [], 'roster_data': {}}
                if not validation_result['is_valid']:
                    # Extract first error message
                    error_msg = validation_result['errors'][0] if validation_result['errors'] else 'Team roster does not meet requirements.'
                    return {
                        'eligible': False,
                        'reason': error_msg,
                        'status': 'roster_invalid',
                        'action_url': f'/teams/{team_with_permission.slug}/',
                        'action_label': 'Manage Team',
                    }
                
            except Exception as e:
                # Fallback to legacy validation if adapter fails (fail-safe)
                # This preserves existing behavior even if adapter has issues
                team_members = TeamMembership.objects.filter(
                    team=team_with_permission,
                    status=TeamMembership.Status.ACTIVE
                )
                
                min_team_size = getattr(tournament.game, 'min_team_size', 5)
                if team_members.count() < min_team_size:
                    return {
                        'eligible': False,
                        'reason': f'Your team needs at least {min_team_size} members.',
                        'status': 'roster_too_small',
                        'action_url': f'/teams/{team_with_permission.slug}/',
                        'action_label': 'Manage Team',
                    }
            
            return {'eligible': True, 'reason': '', 'status': 'eligible'}
            
        except Exception as e:
            return {
                'eligible': False,
                'reason': 'Error checking eligibility. Please try again.',
                'status': 'error',
            }
