# apps/teams/views/ajax.py
"""
AJAX endpoints for team management functionality.
Separated for better code organization and maintainability.
"""
from __future__ import annotations

import json
from typing import Dict, List, Any

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models import Team, TeamMembership
from .utils import _ensure_profile, _is_captain, _get_profile, _get_game_display_name

User = get_user_model()


@login_required
@require_http_methods(["GET"])
def my_teams_data(request) -> JsonResponse:
    """AJAX endpoint to get user's teams grouped by game."""
    profile = _ensure_profile(request.user)
    if not profile:
        return JsonResponse({"error": "User profile not found."}, status=400)
    
    try:
        # Get user's team memberships
        memberships = TeamMembership.objects.filter(
            profile=profile,
            status="ACTIVE"
        ).select_related("team").order_by("-joined_at")
        
        teams_data = []
        for membership in memberships:
            team = membership.team
            
            # Skip inactive teams
            if not getattr(team, 'is_active', True):
                continue
            
            team_data = {
                'id': team.id,
                'name': team.name or f"Team {team.id}",
                'tag': getattr(team, 'tag', '') or '',
                'logo': team.logo.url if team.logo else None,
                'game': getattr(team, 'game', '') or '',
                'game_display': _get_game_display_name(getattr(team, 'game', '')) or 'Unknown Game',
                'role': getattr(membership, 'role', 'member') or 'member',
                'members_count': team.memberships.filter(status='ACTIVE').count() if hasattr(team, 'memberships') else 1,
                'url': team.get_absolute_url() if hasattr(team, 'get_absolute_url') else f'/teams/{team.slug}/' if hasattr(team, 'slug') and team.slug else '#',
                'manage_url': f'/teams/{team.slug}/manage/' if hasattr(team, 'slug') and team.slug and membership.role == 'captain' else None,
                'can_manage': membership.role == 'captain',
                'joined_at': membership.joined_at.isoformat() if hasattr(membership, 'joined_at') and membership.joined_at else None,
                'status': getattr(membership, 'status', 'active') or 'active'
            }
            teams_data.append(team_data)
        
        # Group teams by game for better organization
        teams_by_game = {}
        for team in teams_data:
            game = team['game'] or 'other'
            if game not in teams_by_game:
                teams_by_game[game] = []
            teams_by_game[game].append(team)
        
        return JsonResponse({
            "success": True,
            "teams": teams_data,
            "teams_by_game": teams_by_game,
            "total_teams": len(teams_data)
        })
    
    except Exception as e:
        return JsonResponse({"error": f"Failed to load teams: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def my_invites_data(request) -> JsonResponse:
    """AJAX endpoint to get user's pending team invitations."""
    from django.apps import apps
    from django.utils import timezone
    
    profile = _ensure_profile(request.user)
    if not profile:
        return JsonResponse({"error": "User profile not found."}, status=400)
    
    try:
        TeamInvite = apps.get_model("teams", "TeamInvite")
        
        # Get pending invites
        invites = TeamInvite.objects.filter(
            invited_user=profile,
            status='PENDING',
            expires_at__gt=timezone.now()
        ).select_related('team', 'inviter').order_by('-created_at')
        
        invites_data = []
        for invite in invites:
            invites_data.append({
                'id': invite.id,
                'token': invite.token,
                'team': {
                    'id': invite.team.id,
                    'name': invite.team.name,
                    'tag': getattr(invite.team, 'tag', ''),
                    'logo': invite.team.logo.url if invite.team.logo else None,
                    'game': getattr(invite.team, 'game', ''),
                    'game_display': _get_game_display_name(getattr(invite.team, 'game', '')),
                    'url': invite.team.get_absolute_url() if hasattr(invite.team, 'get_absolute_url') else f'/teams/{invite.team.slug}/'
                },
                'inviter': {
                    'username': invite.inviter.user.username if hasattr(invite.inviter, 'user') else 'Unknown',
                    'display_name': getattr(invite.inviter, 'display_name', None) or (invite.inviter.user.username if hasattr(invite.inviter, 'user') else 'Unknown')
                },
                'role': getattr(invite, 'role', 'member'),
                'created_at': invite.created_at.isoformat() if hasattr(invite, 'created_at') else None,
                'expires_at': invite.expires_at.isoformat() if hasattr(invite, 'expires_at') else None,
                'accept_url': f'/teams/invites/{invite.token}/accept/',
                'decline_url': f'/teams/invites/{invite.token}/decline/'
            })
        
        return JsonResponse({
            "success": True,
            "invites": invites_data,
            "total_invites": len(invites_data)
        })
    
    except Exception as e:
        return JsonResponse({"error": f"Failed to load invites: {str(e)}"}, status=500)


@login_required
@require_http_methods(["POST"])
def update_team_info(request, slug: str) -> JsonResponse:
    """Update team basic information via AJAX."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can edit team information."}, status=403)
    
    try:
        team.name = request.POST.get('name', team.name)
        team.tag = request.POST.get('tag', team.tag)
        team.description = request.POST.get('description', team.description)
        team.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_team_privacy(request, slug: str) -> JsonResponse:
    """Update team privacy settings via AJAX - Enhanced for Phase 4."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can edit privacy settings."}, status=403)
    
    try:
        # Basic settings
        if 'is_public' in request.POST:
            team.is_public = request.POST.get('is_public') in ['on', 'true', True]
        if 'allow_join_requests' in request.POST:
            team.allow_join_requests = request.POST.get('allow_join_requests') in ['on', 'true', True]
        if 'show_statistics' in request.POST:
            team.show_statistics = request.POST.get('show_statistics') in ['on', 'true', True]
        
        # Enhanced Content Privacy
        if 'show_roster_publicly' in request.POST:
            team.show_roster_publicly = request.POST.get('show_roster_publicly') in ['on', 'true', True]
        if 'show_statistics_publicly' in request.POST:
            team.show_statistics_publicly = request.POST.get('show_statistics_publicly') in ['on', 'true', True]
        if 'show_tournaments_publicly' in request.POST:
            team.show_tournaments_publicly = request.POST.get('show_tournaments_publicly') in ['on', 'true', True]
        if 'show_achievements_publicly' in request.POST:
            team.show_achievements_publicly = request.POST.get('show_achievements_publicly') in ['on', 'true', True]
        
        # Member Permissions
        if 'members_can_post' in request.POST:
            team.members_can_post = request.POST.get('members_can_post') in ['on', 'true', True]
        if 'require_post_approval' in request.POST:
            team.require_post_approval = request.POST.get('require_post_approval') in ['on', 'true', True]
        if 'members_can_invite' in request.POST:
            team.members_can_invite = request.POST.get('members_can_invite') in ['on', 'true', True]
        
        # Join Settings
        if 'auto_accept_join_requests' in request.POST:
            team.auto_accept_join_requests = request.POST.get('auto_accept_join_requests') in ['on', 'true', True]
        if 'require_application_message' in request.POST:
            team.require_application_message = request.POST.get('require_application_message') in ['on', 'true', True]
        if 'min_rank_requirement' in request.POST:
            team.min_rank_requirement = request.POST.get('min_rank_requirement', '')
        
        # Display Settings
        if 'hide_member_stats' in request.POST:
            team.hide_member_stats = request.POST.get('hide_member_stats') in ['on', 'true', True]
        if 'hide_social_links' in request.POST:
            team.hide_social_links = request.POST.get('hide_social_links') in ['on', 'true', True]
        if 'show_captain_only' in request.POST:
            team.show_captain_only = request.POST.get('show_captain_only') in ['on', 'true', True]
        
        team.save()
        return JsonResponse({"success": True, "message": "Privacy settings updated successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kick_member(request, slug: str) -> JsonResponse:
    """Kick a team member via AJAX."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can kick members."}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        target_user = get_object_or_404(User, username=username)
        target_profile = _get_profile(target_user)
        
        if not target_profile:
            return JsonResponse({"error": "User profile not found."}, status=404)
        
        membership = get_object_or_404(TeamMembership, team=team, profile=target_profile)
        
        if membership.role == 'captain':
            return JsonResponse({"error": "Cannot kick team captain."}, status=400)
        
        membership.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def transfer_captaincy(request, slug: str) -> JsonResponse:
    """Transfer captaincy via AJAX."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can transfer captaincy."}, status=403)
    
    try:
        data = json.loads(request.body)
        new_captain_username = data.get('new_captain')
        
        new_captain_user = get_object_or_404(User, username=new_captain_username)
        new_captain_profile = _get_profile(new_captain_user)
        
        if not new_captain_profile:
            return JsonResponse({"error": "New captain profile not found."}, status=404)
        
        # Check if user is team member
        new_captain_membership = get_object_or_404(TeamMembership, team=team, profile=new_captain_profile)
        
        # Transfer captaincy
        current_captain_membership = TeamMembership.objects.get(team=team, profile=profile)
        current_captain_membership.role = 'member'
        current_captain_membership.save()
        
        new_captain_membership.role = 'captain'
        new_captain_membership.save()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def leave_team(request, slug: str) -> JsonResponse:
    """Leave team via AJAX."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    try:
        membership = get_object_or_404(TeamMembership, team=team, profile=profile)
        
        if membership.role == 'captain' and team.members.count() > 1:
            return JsonResponse({"error": "Transfer captaincy before leaving the team."}, status=400)
        elif membership.role == 'captain' and team.members.count() == 1:
            # Last member and captain, delete team
            team.delete()
        else:
            membership.delete()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)