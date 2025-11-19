"""
Team Setup View - Post-creation onboarding page
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.teams.models import Team, TeamMembership

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def team_setup_view(request, slug):
    """
    Post-creation team setup page with invitations and essential settings.
    
    This page is shown immediately after team creation to help users:
    - Invite team members via link or email
    - Configure essential privacy/security settings
    - Access quick links to complete setup
    
    Only accessible to team owners.
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Verify user is the team owner
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=request.user.profile,
            status='ACTIVE'
        )
        
        if membership.role != 'OWNER':
            messages.error(request, "Only the team owner can access the setup page.")
            return redirect('teams:detail', slug=team.slug)
            
    except TeamMembership.DoesNotExist:
        raise PermissionDenied("You are not a member of this team.")
    
    context = {
        'team': team,
        'membership': membership,
    }
    
    return render(request, 'teams/team_setup.html', context)


@login_required
@require_http_methods(["POST"])
def update_team_settings(request, slug):
    """
    Update team essential settings from the setup page.
    
    Handles:
    - visibility (PUBLIC/PRIVATE)
    - allow_join_requests (boolean)
    - is_recruiting (boolean)
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Verify user is the team owner or manager
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=request.user.profile,
            status='ACTIVE'
        )
        
        if membership.role not in ['OWNER', 'MANAGER']:
            messages.error(request, "You don't have permission to change team settings.")
            return redirect('teams:setup', slug=team.slug)
            
    except TeamMembership.DoesNotExist:
        raise PermissionDenied("You are not a member of this team.")
    
    # Update settings
    try:
        visibility = request.POST.get('visibility', 'PUBLIC')
        team.is_public = (visibility == 'PUBLIC')
        
        team.allow_join_requests = request.POST.get('allow_join_requests') == 'on'
        team.is_recruiting = request.POST.get('is_recruiting') == 'on'
        
        team.save(update_fields=['is_public', 'allow_join_requests', 'is_recruiting'])
        
        messages.success(request, "Team settings updated successfully!")
        logger.info(f"Team {team.slug} settings updated by {request.user.username}")
        
    except Exception as e:
        logger.error(f"Error updating team settings: {e}", exc_info=True)
        messages.error(request, "Failed to update team settings. Please try again.")
    
    return redirect('teams:setup', slug=team.slug)
