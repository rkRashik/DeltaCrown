"""
Team Permission Request Views

Handles views for team members requesting permission from captains
to register teams for tournaments.
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from apps.tournaments.models import Tournament, TeamRegistrationPermissionRequest
from apps.organizations.models import Team, TeamMembership
from apps.tournaments.services.notification_service import TournamentNotificationService


@login_required
@require_http_methods(["POST"])
def request_permission(request, tournament_slug):
    """
    Request permission from team captain to register for tournament.
    """
    tournament = get_object_or_404(Tournament, slug=tournament_slug)
    team_id = request.POST.get('team_id')
    message = request.POST.get('message', '')
    
    if not team_id:
        messages.error(request, "Please select a team.")
        return redirect('tournaments:detail', slug=tournament_slug)
    
    team = get_object_or_404(Team, id=team_id)
    
    # Verify user is a member of the team
    membership = TeamMembership.objects.filter(
        team=team,
        user=request.user,
        is_active=True
    ).first()
    
    if not membership:
        messages.error(request, "You are not a member of this team.")
        return redirect('tournaments:detail', slug=tournament_slug)
    
    # Check if already requested
    existing_request = TeamRegistrationPermissionRequest.objects.filter(
        team=team,
        tournament=tournament,
        requester=request.user,
        status=TeamRegistrationPermissionRequest.STATUS_PENDING
    ).first()
    
    if existing_request:
        messages.info(request, "You have already requested permission for this tournament.")
        return redirect('tournaments:detail', slug=tournament_slug)
    
    # Create permission request
    permission_request = TeamRegistrationPermissionRequest.objects.create(
        team=team,
        tournament=tournament,
        requester=request.user,
        message=message
    )
    
    # Send notifications to team captains
    TournamentNotificationService.notify_permission_requested(permission_request)
    
    messages.success(
        request,
        f"Permission request sent to {team.name} captains. You'll be notified when they respond."
    )
    
    return redirect('tournaments:detail', slug=tournament_slug)


@login_required
@require_http_methods(["POST"])
def approve_permission(request, request_id):
    """
    Approve a permission request (captain/manager only).
    """
    permission_request = get_object_or_404(
        TeamRegistrationPermissionRequest,
        id=request_id,
        status=TeamRegistrationPermissionRequest.STATUS_PENDING
    )
    
    # Verify user is a captain/manager of the team
    membership = TeamMembership.objects.filter(
        team=permission_request.team,
        user=request.user,
        role__in=['captain', 'manager', 'admin'],
        is_active=True
    ).first()
    
    if not membership:
        return HttpResponseForbidden("Only team captains/managers can approve requests.")
    
    # Approve the request
    response_message = request.POST.get('message', '')
    permission_request.approve(request.user, response_message)
    
    messages.success(
        request,
        f"Permission approved for {permission_request.requester.username}. They can now register the team."
    )
    
    # Redirect to team permissions page or tournament page
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    
    return redirect('teams:detail', slug=permission_request.team.slug)


@login_required
@require_http_methods(["POST"])
def reject_permission(request, request_id):
    """
    Reject a permission request (captain/manager only).
    """
    permission_request = get_object_or_404(
        TeamRegistrationPermissionRequest,
        id=request_id,
        status=TeamRegistrationPermissionRequest.STATUS_PENDING
    )
    
    # Verify user is a captain/manager of the team
    membership = TeamMembership.objects.filter(
        team=permission_request.team,
        user=request.user,
        role__in=['captain', 'manager', 'admin'],
        is_active=True
    ).first()
    
    if not membership:
        return HttpResponseForbidden("Only team captains/managers can reject requests.")
    
    # Reject the request
    response_message = request.POST.get('message', '')
    permission_request.reject(request.user, response_message)
    
    messages.info(
        request,
        f"Permission rejected for {permission_request.requester.username}."
    )
    
    # Redirect to team permissions page or tournament page
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    
    return redirect('teams:detail', slug=permission_request.team.slug)


@login_required
@require_http_methods(["POST"])
def cancel_permission(request, request_id):
    """
    Cancel a permission request (requester only).
    """
    permission_request = get_object_or_404(
        TeamRegistrationPermissionRequest,
        id=request_id,
        requester=request.user,
        status=TeamRegistrationPermissionRequest.STATUS_PENDING
    )
    
    permission_request.cancel()
    
    messages.info(request, "Permission request cancelled.")
    
    # Redirect
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    
    return redirect('tournaments:detail', slug=permission_request.tournament.slug)


@login_required
def my_permission_requests(request):
    """
    View user's own permission requests.
    """
    # Requests made by user
    my_requests = TeamRegistrationPermissionRequest.objects.filter(
        requester=request.user
    ).select_related('team', 'tournament', 'responded_by').order_by('-created_at')
    
    # Requests pending for teams where user is captain
    my_teams = Team.objects.filter(
        members__user=request.user,
        members__role__in=['captain', 'manager', 'admin'],
        members__is_active=True
    )
    
    pending_requests = TeamRegistrationPermissionRequest.objects.filter(
        team__in=my_teams,
        status=TeamRegistrationPermissionRequest.STATUS_PENDING
    ).select_related('team', 'tournament', 'requester').order_by('-created_at')
    
    context = {
        'my_requests': my_requests,
        'pending_requests': pending_requests
    }
    
    return render(request, 'tournaments/permission_requests.html', context)


@login_required
def team_permission_requests(request, team_slug):
    """
    View permission requests for a specific team (captain/manager only).
    """
    team = get_object_or_404(Team, slug=team_slug)
    
    # Verify user is a captain/manager of the team
    membership = TeamMembership.objects.filter(
        team=team,
        user=request.user,
        role__in=['captain', 'manager', 'admin'],
        is_active=True
    ).first()
    
    if not membership:
        return HttpResponseForbidden("Only team captains/managers can view permission requests.")
    
    # Get all permission requests for this team
    requests = TeamRegistrationPermissionRequest.objects.filter(
        team=team
    ).select_related('tournament', 'requester', 'responded_by').order_by('-created_at')
    
    context = {
        'team': team,
        'requests': requests
    }
    
    return render(request, 'tournaments/team_permission_requests.html', context)
