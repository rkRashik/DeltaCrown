# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-structure
# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#rest-api-layer

"""
Tournament API - Permissions

Custom permission classes for tournament API endpoints.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Security)
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md (Role-based Access Control)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-005: Security Model)
"""

from rest_framework import permissions
from apps.tournaments.models.tournament import Tournament


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Allow write access only to tournament organizers.
    Read access allowed for authenticated users.
    
    Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 2
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for tournament organizer
        if hasattr(obj, 'tournament'):
            return obj.tournament.organizer == request.user
        elif hasattr(obj, 'organizer'):
            return obj.organizer == request.user
        
        return False


class IsOwnerOrOrganizer(permissions.BasePermission):
    """
    Allow access to registration owner or tournament organizer.
    
    Used for registration endpoints where both the participant and
    tournament organizer should have access.
    
    Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 2
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is the registration owner
        if obj.user == request.user:
            return True
        
        # Check if user is the tournament organizer
        if hasattr(obj, 'tournament') and obj.tournament.organizer == request.user:
            return True
        
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        return False


class IsPlayerOrSpectator(permissions.BasePermission):
    """
    Allow read-only access to players and spectators.
    Organizers and staff have full access.
    
    Source: PART_2.3_REALTIME_SECURITY.md Section 3
    """
    
    def has_object_permission(self, request, view, obj):
        # Organizers and staff have full access
        if hasattr(obj, 'tournament') and obj.tournament.organizer == request.user:
            return True
        if request.user.is_staff:
            return True
        
        # Players (registered participants) have read access
        if hasattr(obj, 'tournament'):
            is_participant = obj.tournament.registrations.filter(
                user=request.user,
                status__in=['pending', 'payment_submitted', 'confirmed']
            ).exists()
            
            if is_participant:
                # Read-only for safe methods
                return request.method in permissions.SAFE_METHODS
        
        # Default: no access
        return False


class IsOrganizerOrAdmin(permissions.BasePermission):
    """
    Allow access only to tournament organizers or admin users.
    
    Used for bracket generation, match management, and other
    tournament administration actions.
    
    Module: 4.1 - Bracket Generation API
    Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user is organizer or admin."""
        # Staff/superuser have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is tournament organizer
        if hasattr(obj, 'tournament'):
            # Object is related to tournament (e.g., Bracket, Match)
            return obj.tournament.organizer_id == request.user.id
        elif hasattr(obj, 'organizer'):
            # Object is tournament itself
            return obj.organizer_id == request.user.id
        
        return False


class IsMatchParticipant(permissions.BasePermission):
    """
    Allow access to match participants.
    
    Used for match detail views where participants need to see
    match information and perform actions (submit results, report disputes, etc.)
    
    Module: 4.3 - Match Management API (read access)
    Module: 4.4 - Result Submission API (write access for result operations)
    Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.3, 4.4
    """

    @staticmethod
    def _participant_ids(obj):
        return [
            getattr(obj, 'participant1_id', None),
            getattr(obj, 'participant2_id', None),
        ]

    @staticmethod
    def _team_from_direct_id(team_id):
        if not team_id:
            return None
        try:
            from apps.organizations.models import Team
            return Team.objects.filter(pk=team_id).first()
        except Exception:
            return None

    @staticmethod
    def _team_from_registration_id(registration_id, tournament):
        if not registration_id:
            return None
        try:
            from apps.tournaments.models import Registration
            qs = Registration.objects.filter(pk=registration_id, is_deleted=False)
            if tournament is not None:
                qs = qs.filter(tournament=tournament)
            registration = qs.first()
            return registration.team if registration else None
        except Exception:
            return None

    @classmethod
    def _user_can_act_for_team_participant(cls, user, obj, participant_id):
        try:
            from apps.organizations.services.team_authority import can_submit_team_result
        except Exception:
            return False
        tournament = getattr(obj, 'tournament', None)
        for team in (
            cls._team_from_direct_id(participant_id),
            cls._team_from_registration_id(participant_id, tournament),
        ):
            if team and can_submit_team_result(user, team, match=obj):
                return True
        return False

    @classmethod
    def _user_is_solo_participant(cls, user, obj, participant_id):
        if not participant_id:
            return False
        if participant_id == getattr(user, 'id', None):
            return True
        try:
            from apps.tournaments.models import Registration
            tournament = getattr(obj, 'tournament', None)
            qs = Registration.objects.filter(pk=participant_id, user=user, is_deleted=False)
            if tournament is not None:
                qs = qs.filter(tournament=tournament)
            return qs.exists()
        except Exception:
            return False
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is a participant in the match.
        
        Allows:
        - Tournament organizer (full access)
        - Staff/superuser (full access)
        - Match participants (full access for match-related operations)
        
        Note: For Module 4.4 result submission operations, participants
        can submit results, confirm results, and report disputes on their matches.
        """
        # Staff/superuser have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Tournament organizer has full access
        if hasattr(obj, 'tournament') and obj.tournament.organizer_id == request.user.id:
            return True
        
        tournament = getattr(obj, 'tournament', None)
        participation_type = getattr(tournament, 'participation_type', None)
        for participant_id in self._participant_ids(obj):
            if participation_type == 'team':
                if self._user_can_act_for_team_participant(request.user, obj, participant_id):
                    return True
            elif participation_type == 'solo':
                if self._user_is_solo_participant(request.user, obj, participant_id):
                    return True
            else:
                if (
                    self._user_can_act_for_team_participant(request.user, obj, participant_id)
                    or self._user_is_solo_participant(request.user, obj, participant_id)
                ):
                    return True
        
        return False
