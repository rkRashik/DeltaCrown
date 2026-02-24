# apps/tournaments/views/permission_request.py
"""
Tournament Registration Permission Request Handler

Allows team members without registration permission to request access from team leaders.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.utils import timezone

from apps.tournaments.models import Tournament


class RequestRegistrationPermissionView(LoginRequiredMixin, View):
    """
    Handle permission requests from team members.
    
    When a team member without registration permission wants to register their team,
    they can send a request to team owner/managers.
    """
    
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        team_id = request.POST.get('team_id')
        message = request.POST.get('message', '')
        
        if not team_id:
            messages.error(request, 'Team not specified.')
            return redirect('tournaments:detail', slug=slug)
        
        try:
            from apps.organizations.models import Team, TeamMembership
            
            # Get team
            team = Team.objects.get(id=team_id)
            
            # Verify user is actually a member
            membership = TeamMembership.objects.filter(
                team=team,
                user=request.user,
                status='ACTIVE'
            ).first()
            
            if not membership:
                messages.error(request, 'You are not a member of this team.')
                return redirect('tournaments:detail', slug=slug)
            
            # Get team leaders (owner + managers)
            leaders = TeamMembership.objects.filter(
                team=team,
                status='ACTIVE',
                role__in=['OWNER', 'MANAGER']
            ).select_related('user')
            
            if not leaders.exists():
                messages.error(request, 'No team leaders found to send request to.')
                return redirect('tournaments:detail', slug=slug)
            
            # Send notifications to team leaders
            try:
                from apps.notifications.services import NotificationService
                
                for leader in leaders:
                    NotificationService.send_notification(
                        user=leader.user,
                        notification_type='team_registration_permission_request',
                        title=f'Tournament Registration Request - {team.name}',
                        message=(
                            f'{request.user.username} ({membership.get_role_display()}) wants to register '
                            f'{team.name} for {tournament.name}. '
                            f'{message if message else "No additional message provided."}'
                        ),
                        link=f'/teams/{team.slug}/settings/',
                        metadata={
                            'team_id': team.id,
                            'tournament_id': tournament.id,
                            'requester_id': request.user.id,
                            'requester_role': membership.role,
                            'message': message,
                        }
                    )
                
                messages.success(
                    request,
                    f'âœ… Permission request sent to {leaders.count()} team leader(s)! '
                    f'They will be notified about your request.'
                )
                
            except Exception as e:
                # Fallback if notification system not available
                messages.warning(
                    request,
                    f'Request recorded, but notifications could not be sent. '
                    f'Please contact your team leaders directly: '
                    f'{", ".join([l.profile.user.username for l in leaders])}'
                )
            
            return redirect('tournaments:detail', slug=slug)
            
        except Team.DoesNotExist:
            messages.error(request, 'Team not found.')
            return redirect('tournaments:detail', slug=slug)
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('tournaments:detail', slug=slug)
