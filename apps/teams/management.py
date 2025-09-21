# apps/teams/management.py
"""
Team management utilities and helper functions.
"""
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any, List

from .models import Team, TeamMembership, TeamInvite


class TeamAnalytics:
    """Analytics and statistics for teams."""
    
    def __init__(self, team: Team):
        self.team = team
    
    def get_member_statistics(self) -> Dict[str, Any]:
        """Get team member statistics."""
        memberships = self.team.memberships.filter(status="ACTIVE")
        
        return {
            "total_members": memberships.count(),
            "active_members": memberships.filter(
                user__last_login__gte=timezone.now() - timedelta(days=30)
            ).count(),
            "captain": self.team.captain,
            "newest_member": memberships.order_by("-joined_at").first(),
            "longest_member": memberships.order_by("joined_at").first(),
        }
    
    def get_invitation_statistics(self) -> Dict[str, Any]:
        """Get invitation statistics."""
        invites = self.team.invites.all()
        
        return {
            "total_sent": invites.count(),
            "pending": invites.filter(status="PENDING").count(),
            "accepted": invites.filter(status="ACCEPTED").count(),
            "declined": invites.filter(status="DECLINED").count(),
            "expired": invites.filter(status="EXPIRED").count(),
            "acceptance_rate": self._calculate_acceptance_rate(invites),
        }
    
    def get_tournament_statistics(self) -> Dict[str, Any]:
        """Get tournament participation statistics."""
        # This would need to be implemented based on tournament model relationships
        return {
            "tournaments_participated": 0,  # Placeholder
            "wins": 0,  # Placeholder
            "losses": 0,  # Placeholder
            "win_rate": 0.0,  # Placeholder
        }
    
    def _calculate_acceptance_rate(self, invites) -> float:
        """Calculate invitation acceptance rate."""
        total_responded = invites.filter(status__in=["ACCEPTED", "DECLINED"]).count()
        if total_responded == 0:
            return 0.0
        accepted = invites.filter(status="ACCEPTED").count()
        return (accepted / total_responded) * 100


class TeamManagementService:
    """Service class for team management operations."""
    
    @staticmethod
    def bulk_invite_members(team: Team, usernames: List[str], inviter, message: str = "") -> Dict[str, Any]:
        """Send invitations to multiple users at once."""
        results = {
            "successful": [],
            "failed": [],
            "already_invited": [],
            "already_members": [],
        }
        
        for username in usernames:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                user = User.objects.get(username=username.strip())
                profile = user.userprofile
                
                # Check if already a member
                if TeamMembership.objects.filter(team=team, user=profile).exists():
                    results["already_members"].append(username)
                    continue
                
                # Check if already invited
                if TeamInvite.objects.filter(
                    team=team, 
                    invited_user=profile, 
                    status="PENDING"
                ).exists():
                    results["already_invited"].append(username)
                    continue
                
                # Create invitation
                invite = TeamInvite.objects.create(
                    team=team,
                    invited_user=profile,
                    invited_by=inviter.userprofile,
                    message=message,
                    status="PENDING"
                )
                results["successful"].append(username)
                
            except Exception as e:
                results["failed"].append({"username": username, "error": str(e)})
        
        return results
    
    @staticmethod
    def cleanup_expired_invites(team: Team = None) -> int:
        """Clean up expired invitations."""
        from django.conf import settings
        
        expiry_days = getattr(settings, 'TEAM_INVITE_EXPIRY_DAYS', 7)
        cutoff_date = timezone.now() - timedelta(days=expiry_days)
        
        query = TeamInvite.objects.filter(
            status="PENDING",
            created_at__lt=cutoff_date
        )
        
        if team:
            query = query.filter(team=team)
        
        expired_count = query.count()
        query.update(status="EXPIRED")
        
        return expired_count
    
    @staticmethod
    def transfer_team_ownership(team: Team, new_captain, current_captain) -> bool:
        """Transfer team ownership to a new captain."""
        try:
            # Verify new captain is a team member
            new_captain_membership = TeamMembership.objects.get(
                team=team,
                user=new_captain,
                status="ACTIVE"
            )
            
            # Update team captain
            team.captain = new_captain
            team.save()
            
            return True
            
        except TeamMembership.DoesNotExist:
            return False
    
    @staticmethod
    def get_team_activity_feed(team: Team, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent team activity for display."""
        activities = []
        
        # Recent invitations
        recent_invites = team.invites.order_by("-created_at")[:limit]
        for invite in recent_invites:
            activities.append({
                "type": "invitation",
                "action": f"sent invitation to {invite.invited_user.display_name}",
                "timestamp": invite.created_at,
                "user": invite.invited_by.display_name if invite.invited_by else "System",
            })
        
        # Recent member joins
        recent_joins = team.memberships.filter(status="ACTIVE").order_by("-joined_at")[:limit]
        for membership in recent_joins:
            activities.append({
                "type": "member_join",
                "action": f"{membership.user.display_name} joined the team",
                "timestamp": membership.joined_at,
                "user": membership.user.display_name,
            })
        
        # Sort by timestamp and return limited results
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]


def get_team_recommendations(user, game: str = None) -> List[Team]:
    """Get recommended teams for a user based on preferences and activity."""
    query = Team.objects.filter(is_recruiting=True, is_open=True)
    
    if game:
        query = query.filter(game=game)
    
    # Exclude teams user is already in
    user_teams = TeamMembership.objects.filter(
        user=user.userprofile,
        status="ACTIVE"
    ).values_list("team_id", flat=True)
    
    query = query.exclude(id__in=user_teams)
    
    # Order by activity level and member count
    return query.annotate(
        member_count=Count("memberships", filter=Q(memberships__status="ACTIVE"))
    ).filter(
        member_count__lt=10  # Not full teams
    ).order_by("-created_at")[:5]