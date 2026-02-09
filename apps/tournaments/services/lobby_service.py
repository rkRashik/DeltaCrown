"""
Lobby Service - Business logic for tournament lobby and check-in

Source Documents:
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 2.1: FE-T-007)
- Documents/Planning/PART_4.3_CHECK_IN_FLOW.md

Responsibilities:
- Lobby creation and configuration
- Check-in management
- Roster display
- Announcements
- Auto-forfeit for no-shows
"""

from typing import List, Dict, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import (
    Tournament,
    Registration,
    TournamentLobby,
    CheckIn,
    LobbyAnnouncement,
)


class LobbyService:
    """Service for tournament lobby logic."""
    
    @staticmethod
    @transaction.atomic
    def create_lobby(
        tournament_id: int,
        check_in_window_minutes: int = 60,
        check_in_required: bool = True,
        auto_forfeit: bool = True,
        lobby_message: str = '',
    ) -> TournamentLobby:
        """
        Create tournament lobby.
        
        Args:
            tournament_id: Tournament ID
            check_in_window_minutes: How long before start time to open check-in
            check_in_required: Whether check-in is mandatory
            auto_forfeit: Whether to auto-forfeit no-shows
            lobby_message: Welcome message
        
        Returns:
            Created TournamentLobby
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Check if lobby already exists
        if hasattr(tournament, 'lobby'):
            lobby = tournament.lobby
            lobby.is_active = True
            lobby.save()
            return lobby
        
        # Calculate check-in times
        if tournament.start_time:
            check_in_opens_at = tournament.start_time - timedelta(minutes=check_in_window_minutes)
            check_in_closes_at = tournament.start_time
        else:
            check_in_opens_at = None
            check_in_closes_at = None
        
        lobby = TournamentLobby.objects.create(
            tournament=tournament,
            check_in_opens_at=check_in_opens_at,
            check_in_closes_at=check_in_closes_at,
            check_in_required=check_in_required,
            auto_forfeit_no_show=auto_forfeit,
            lobby_message=lobby_message,
            bracket_visibility='seeded_only',
            roster_visibility='full',
            is_active=True,
        )
        
        # Create CheckIn entries for all confirmed registrations
        registrations = tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        )
        
        for reg in registrations:
            CheckIn.objects.create(
                tournament=tournament,
                registration=reg,
                user=reg.user if tournament.participation_type == 'solo' else None,
                team=reg.team if tournament.participation_type == 'team' else None,
                is_checked_in=False,
            )
        
        return lobby
    
    @staticmethod
    @transaction.atomic
    def perform_check_in(
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None
    ) -> CheckIn:
        """
        Check in a participant.
        
        Args:
            tournament_id: Tournament ID
            user_id: User performing check-in
            team_id: Team ID (if team tournament)
        
        Returns:
            Updated CheckIn object
        
        Raises:
            ValidationError: If check-in fails
        """
        from apps.tournaments.models import Tournament
        from apps.accounts.models import User
        
        tournament = Tournament.objects.get(id=tournament_id)
        user = User.objects.get(id=user_id)
        
        # Check if lobby exists and check-in is open
        if not hasattr(tournament, 'lobby'):
            raise ValidationError("Tournament lobby not configured")
        
        lobby = tournament.lobby
        
        if not lobby.is_check_in_open:
            status = lobby.check_in_status
            if status == 'not_open':
                raise ValidationError("Check-in has not opened yet")
            elif status == 'closed':
                raise ValidationError("Check-in has closed")
            elif status == 'not_required':
                raise ValidationError("Check-in is not required for this tournament")
        
        # Find CheckIn record
        if team_id:
            check_in = CheckIn.objects.get(
                tournament=tournament,
                team_id=team_id,
                is_deleted=False
            )
            
            # Verify user has permission (team captain/owner)
            from apps.organizations.models import Team, TeamMembership
            team = Team.objects.get(id=team_id)
            
            if team.owner != user:
                membership = TeamMembership.objects.filter(
                    team=team,
                    user=user,
                    is_deleted=False
                ).first()
                
                if not membership or membership.role not in ['manager', 'captain']:
                    raise ValidationError("You don't have permission to check in this team")
        else:
            check_in = CheckIn.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        
        # Verify not already checked in
        if check_in.is_checked_in:
            raise ValidationError("Already checked in")
        
        # Verify not forfeited
        if check_in.is_forfeited:
            raise ValidationError("This registration has been forfeited")
        
        # Perform check-in
        check_in.perform_check_in(user)
        
        return check_in
    
    @staticmethod
    @transaction.atomic
    def auto_forfeit_no_shows(tournament_id: int) -> List[CheckIn]:
        """
        Auto-forfeit participants who didn't check in.
        
        Should be called when check-in closes.
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            List of forfeited CheckIn objects
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        if not hasattr(tournament, 'lobby'):
            return []
        
        lobby = tournament.lobby
        
        if not lobby.auto_forfeit_no_show:
            return []
        
        # Find participants who didn't check in
        no_shows = CheckIn.objects.filter(
            tournament=tournament,
            is_checked_in=False,
            is_forfeited=False,
            is_deleted=False
        )
        
        forfeited = []
        for check_in in no_shows:
            check_in.perform_forfeit(reason='Did not check in before deadline')
            forfeited.append(check_in)
        
        return forfeited
    
    @staticmethod
    def get_roster(tournament_id: int) -> Dict:
        """
        Get tournament roster with check-in status.
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            Dict with roster data
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        check_ins = CheckIn.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('user', 'team', 'registration')
        
        checked_in = []
        not_checked_in = []
        forfeited = []
        
        for check_in in check_ins:
            participant_data = {
                'id': check_in.id,
                'name': check_in.participant_name,
                'user_id': check_in.user_id,
                'team_id': check_in.team_id,
                'checked_in_at': check_in.checked_in_at,
                'seed': check_in.registration.seed if check_in.registration else None,
            }
            
            if check_in.is_forfeited:
                participant_data['forfeit_reason'] = check_in.forfeit_reason
                forfeited.append(participant_data)
            elif check_in.is_checked_in:
                checked_in.append(participant_data)
            else:
                not_checked_in.append(participant_data)
        
        return {
            'total': len(check_ins),
            'checked_in_count': len(checked_in),
            'not_checked_in_count': len(not_checked_in),
            'forfeited_count': len(forfeited),
            'checked_in': checked_in,
            'not_checked_in': not_checked_in,
            'forfeited': forfeited,
        }
    
    @staticmethod
    @transaction.atomic
    def post_announcement(
        tournament_id: int,
        user_id: int,
        title: str,
        message: str,
        announcement_type: str = 'info',
        is_pinned: bool = False,
        display_until: Optional[timezone.datetime] = None,
    ) -> LobbyAnnouncement:
        """
        Post announcement to lobby.
        
        Args:
            tournament_id: Tournament ID
            user_id: User posting (must be organizer)
            title: Announcement title
            message: Announcement message
            announcement_type: 'info', 'warning', 'urgent', 'success'
            is_pinned: Whether to pin announcement
            display_until: Auto-hide after this time
        
        Returns:
            Created LobbyAnnouncement
        
        Raises:
            ValidationError: If user lacks permission
        """
        from apps.tournaments.models import Tournament
        from apps.accounts.models import User
        
        tournament = Tournament.objects.get(id=tournament_id)
        user = User.objects.get(id=user_id)
        
        # Verify user is organizer
        if tournament.organizer != user:
            # Check if user is tournament staff with announcement permission
            from apps.tournaments.models import TournamentStaff
            staff = TournamentStaff.objects.filter(
                tournament=tournament,
                user=user,
                is_active=True
            ).first()
            
            if not staff or not staff.role.can_post_announcements:
                raise ValidationError("You don't have permission to post announcements")
        
        # Get lobby
        if not hasattr(tournament, 'lobby'):
            raise ValidationError("Tournament lobby not configured")
        
        lobby = tournament.lobby
        
        announcement = LobbyAnnouncement.objects.create(
            lobby=lobby,
            posted_by=user,
            title=title,
            message=message,
            announcement_type=announcement_type,
            is_pinned=is_pinned,
            display_until=display_until,
            is_visible=True,
        )
        
        # TODO: Send notifications to participants
        # This would integrate with apps.notifications module
        
        return announcement
    
    @staticmethod
    def get_announcements(tournament_id: int) -> List[LobbyAnnouncement]:
        """
        Get active lobby announcements.
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            List of visible announcements
        """
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        if not hasattr(tournament, 'lobby'):
            return []
        
        lobby = tournament.lobby
        
        now = timezone.now()
        
        announcements = LobbyAnnouncement.objects.filter(
            lobby=lobby,
            is_visible=True,
            is_deleted=False
        ).filter(
            Q(display_until__isnull=True) | Q(display_until__gt=now)
        ).select_related('posted_by').order_by('-is_pinned', '-created_at')
        
        return list(announcements)
