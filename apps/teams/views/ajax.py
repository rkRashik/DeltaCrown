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
    """Update team privacy settings via AJAX."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can edit privacy settings."}, status=403)
    
    try:
        team.is_public = request.POST.get('is_public') == 'on'
        team.allow_join_requests = request.POST.get('allow_join_requests') == 'on'
        team.show_statistics = request.POST.get('show_statistics') == 'on'
        team.save()
        return JsonResponse({"success": True})
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