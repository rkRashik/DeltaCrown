# apps/teams/api/views.py
"""
Team Management API Views (Module 3.3)

REST API endpoints following DRF best practices and Module 3.2 patterns.
Integrates TeamService, permissions, and WebSocket broadcasts.

Planning Reference: Documents/ExecutionPlan/Modules/MODULE_3.3_IMPLEMENTATION_PLAN.md

Traceability:
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#adr-008
"""
import logging

from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.teams.models._legacy import Team, TeamInvite
from apps.teams.services.team_service import TeamService
from apps.user_profile.models import UserProfile
from .serializers import (
    TeamListSerializer,
    TeamDetailSerializer,
    TeamCreateSerializer,
    TeamUpdateSerializer,
    TeamInviteSerializer,
    InvitePlayerSerializer,
    RespondInviteSerializer,
    TransferCaptainSerializer,
)
from .permissions import IsTeamCaptain, IsTeamMember, IsInvitedUser

logger = logging.getLogger(__name__)


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for team management.
    
    Endpoints:
    - GET /api/teams/ - List teams
    - POST /api/teams/ - Create team
    - GET /api/teams/{id}/ - Get team details
    - PATCH /api/teams/{id}/ - Update team (captain only)
    - DELETE /api/teams/{id}/ - Disband team (captain only)
    - POST /api/teams/{id}/invite/ - Invite player (captain only)
    - POST /api/teams/{id}/transfer-captain/ - Transfer captain (captain only)
    - POST /api/teams/{id}/leave/ - Leave team (member, not captain)
    - DELETE /api/teams/{id}/members/{user_id}/ - Remove member (captain only)
    """
    queryset = Team.objects.filter(is_active=True).select_related("captain").order_by("-created_at")
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return TeamListSerializer
        elif self.action == "create":
            return TeamCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return TeamUpdateSerializer
        elif self.action == "invite_player":
            return InvitePlayerSerializer
        elif self.action == "transfer_captain":
            return TransferCaptainSerializer
        return TeamDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        elif self.action == "create":
            return [IsAuthenticated()]
        elif self.action in ["update", "partial_update", "destroy", "invite_player", "transfer_captain"]:
            return [IsAuthenticated(), IsTeamCaptain()]
        elif self.action in ["leave", "remove_member"]:
            return [IsAuthenticated(), IsTeamMember()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """
        Create team (POST /api/teams/).
        
        Endpoint 1: Create Team
        - Captain = authenticated user
        - Auto-generates slug
        - Creates captain membership
        - Broadcasts team_created event
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get or create user's profile
            captain_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Create team via service
            team = TeamService.create_team(
                name=serializer.validated_data["name"],
                captain_profile=captain_profile,
                game=serializer.validated_data["game"],
                tag=serializer.validated_data.get("tag"),
                description=serializer.validated_data.get("description", ""),
                logo=serializer.validated_data.get("logo"),
                region=serializer.validated_data.get("region", ""),
            )
            
            # Broadcast WebSocket event
            self._broadcast_team_event(
                team_id=team.id,
                event_type="team.created",
                payload={
                    "team_id": team.id,
                    "team_name": team.name,
                    "captain_username": captain_profile.user.username,
                    "game": team.game,
                    "created_at": team.created_at.isoformat(),
                }
            )
            
            # Return created team
            response_serializer = TeamDetailSerializer(team)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Team creation failed: {e}", exc_info=True)
            return Response(
                {"error": "Team creation failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update team (PATCH /api/teams/{id}/).
        
        Endpoint 3: Update Team
        - Captain only
        - Allowed fields: description, logo, banner, socials
        """
        partial = kwargs.pop('partial', False)
        team = self.get_object()
        serializer = self.get_serializer(team, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get or create user profile
            updating_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Update via service
            updated_team = TeamService.update_team(
                team=team,
                updating_profile=updating_profile,
                **serializer.validated_data
            )
            
            response_serializer = TeamDetailSerializer(updated_team)
            return Response(response_serializer.data)
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Team update failed: {e}", exc_info=True)
            return Response(
                {"error": "Team update failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Disband team (DELETE /api/teams/{id}/).
        
        Endpoint 9: Disband Team
        - Captain only
        - Cannot disband with active tournament registrations
        - Soft delete (is_active=False)
        - Broadcasts team_disbanded event
        """
        team = self.get_object()
        
        try:
            # Get or create user profile
            disbanding_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Disband via service
            TeamService.disband_team(
                team=team,
                disbanding_profile=disbanding_profile
            )
            
            # Broadcast WebSocket event
            self._broadcast_team_event(
                team_id=team.id,
                event_type="team.disbanded",
                payload={
                    "team_id": team.id,
                    "team_name": team.name,
                    "disbanded_by": request.user.username,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Team disband failed: {e}", exc_info=True)
            return Response(
                {"error": "Team disband failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeamCaptain])
    def invite(self, request, pk=None):
        """
        Invite player (POST /api/teams/{id}/invite/).
        
        Endpoint 4: Invite Player
        - Captain only
        - Validates roster capacity
        - Prevents duplicate invites
        - Sets 72-hour expiration
        """
        team = self.get_object()
        serializer = InvitePlayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get invited user and profile
            invited_user = get_object_or_404(User, id=serializer.validated_data["invited_user_id"])
            invited_profile, _ = UserProfile.objects.get_or_create(user=invited_user)
            
            # Get inviter's profile
            invited_by_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Create invite via service
            invite = TeamService.invite_player(
                team=team,
                invited_profile=invited_profile,
                invited_by_profile=invited_by_profile,
                role=serializer.validated_data.get("role", "player")
            )
            
            response_serializer = TeamInviteSerializer(invite)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Player invite failed: {e}", exc_info=True)
            return Response(
                {"error": "Player invite failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], url_path="transfer-captain", permission_classes=[IsAuthenticated, IsTeamCaptain])
    def transfer_captain(self, request, pk=None):
        """
        Transfer captain (POST /api/teams/{id}/transfer-captain/).
        
        Endpoint 7: Transfer Captain
        - Captain only
        - New captain must be active member
        - Updates team.captain and memberships
        - Broadcasts captain_transferred event
        """
        team = self.get_object()
        serializer = TransferCaptainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get new captain's profile
            new_captain_user = get_object_or_404(User, id=serializer.validated_data["new_captain_id"])
            new_captain_profile, _ = UserProfile.objects.get_or_create(user=new_captain_user)
            
            # Get current captain's profile
            current_captain_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Transfer captain via service
            TeamService.transfer_captain(
                team=team,
                new_captain_profile=new_captain_profile,
                current_captain_profile=current_captain_profile
            )
            
            # Broadcast WebSocket event
            self._broadcast_team_event(
                team_id=team.id,
                event_type="team.captain_transferred",
                payload={
                    "team_id": team.id,
                    "team_name": team.name,
                    "old_captain": request.user.username,
                    "new_captain": new_captain_user.username,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            
            # Refresh team from DB
            team.refresh_from_db()
            response_serializer = TeamDetailSerializer(team)
            return Response({
                "message": "Captain role transferred successfully",
                "team": response_serializer.data,
                "new_captain": new_captain_user.username
            })
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Captain transfer failed: {e}", exc_info=True)
            return Response(
                {"error": "Captain transfer failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeamMember])
    def leave(self, request, pk=None):
        """
        Leave team (POST /api/teams/{id}/leave/).
        
        Endpoint 8: Leave Team
        - Team member (not captain)
        - Captain must transfer or disband first
        """
        team = self.get_object()
        
        try:
            # Get or create user profile
            leaving_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Leave team via service
            TeamService.leave_team(
                team=team,
                leaving_profile=leaving_profile
            )
            
            # Broadcast WebSocket event
            self._broadcast_team_event(
                team_id=team.id,
                event_type="team.member_left",
                payload={
                    "team_id": team.id,
                    "team_name": team.name,
                    "username": request.user.username,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            
            return Response({
                "message": f"You have left {team.name}"
            })
        
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Leave team failed: {e}", exc_info=True)
            return Response(
                {"error": "Leave team failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["delete"], url_path="members/(?P<user_id>[0-9]+)", permission_classes=[IsAuthenticated, IsTeamCaptain])
    def remove_member(self, request, pk=None, user_id=None):
        """
        Remove member (DELETE /api/teams/{id}/members/{user_id}/).
        
        Endpoint 6: Remove Member
        - Captain only
        - Cannot remove captain
        - Broadcasts member_removed event
        """
        team = self.get_object()
        
        try:
            # Get member's profile
            member_user = get_object_or_404(User, id=user_id)
            member_profile, _ = UserProfile.objects.get_or_create(user=member_user)
            
            # Get remover's profile
            removed_by_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            # Remove member via service
            TeamService.remove_member(
                team=team,
                member_profile=member_profile,
                removed_by_profile=removed_by_profile
            )
            
            # Broadcast WebSocket event
            self._broadcast_team_event(
                team_id=team.id,
                event_type="team.member_removed",
                payload={
                    "team_id": team.id,
                    "team_name": team.name,
                    "removed_user": member_user.username,
                    "removed_by": request.user.username,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Remove member failed: {e}", exc_info=True)
            return Response(
                {"error": "Remove member failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _broadcast_team_event(self, team_id: int, event_type: str, payload: dict):
        """
        Broadcast team event via WebSocket (Module 2.3 integration).
        
        Follows Module 3.2 payment broadcast pattern.
        Channel: team_{team_id}
        
        Args:
            team_id: Team ID
            event_type: Event type (team.created, team.member_joined, etc.)
            payload: Event payload
        """
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"team_{team_id}",
                    {
                        "type": event_type.replace(".", "_"),  # team.created -> team_created
                        "payload": payload
                    }
                )
                logger.info(f"[WS] Broadcast {event_type} to team_{team_id}")
        except Exception as e:
            logger.error(f"WebSocket broadcast failed: {e}", exc_info=True)


class TeamInviteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for team invitations.
    
    Endpoints:
    - GET /api/teams/invites/ - List user's invites
    - GET /api/teams/invites/{id}/ - Get invite details
    - POST /api/teams/invites/{id}/respond/ - Accept/decline invite
    """
    serializer_class = TeamInviteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return invites for authenticated user."""
        # Get or create user's profile
        user_profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        
        return TeamInvite.objects.filter(
            invited_user=user_profile,
            status="PENDING"
        ).select_related("team", "inviter").order_by("-created_at")
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsInvitedUser])
    def respond(self, request, pk=None):
        """
        Respond to invite (POST /api/teams/invites/{id}/respond/).
        
        Endpoint 5: Respond to Invite
        - Invited user only
        - Actions: accept, decline
        - Broadcasts member_joined on accept
        """
        invite = self.get_object()
        serializer = RespondInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data["action"]
        
        try:
            # Get or create user profile
            user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            
            if action_type == "accept":
                # Accept invite via service
                membership = TeamService.accept_invite(
                    invite=invite,
                    accepting_profile=user_profile
                )
                
                # Broadcast WebSocket event
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"team_{invite.team_id}",
                        {
                            "type": "team_member_joined",
                            "payload": {
                                "team_id": invite.team_id,
                                "team_name": invite.team.name,
                                "username": request.user.username,
                                "role": invite.role,
                                "timestamp": timezone.now().isoformat(),
                            }
                        }
                    )
                    logger.info(f"[WS] Broadcast team.member_joined to team_{invite.team_id}")
                
                return Response({
                    "message": f"Invite accepted. You are now a member of {invite.team.name}.",
                    "membership_id": membership.id
                })
            
            else:  # decline
                # Decline invite via service
                TeamService.decline_invite(
                    invite=invite,
                    declining_profile=user_profile
                )
                
                return Response({
                    "message": f"Invite from {invite.team.name} declined."
                })
        
        except (DjangoValidationError, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, DjangoPermissionDenied) else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Invite response failed: {e}", exc_info=True)
            return Response(
                {"error": "Invite response failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Import User model at bottom to avoid circular import
from django.contrib.auth import get_user_model
User = get_user_model()
