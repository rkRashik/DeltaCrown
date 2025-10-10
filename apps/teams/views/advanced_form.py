# apps/teams/views/advanced_form.py
"""
Advanced Team Creation Form View
Integrates with the new frontend UI and REST API.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def create_team_advanced_view(request):
    """
    Render the advanced team creation form.
    
    This form provides a modern, step-by-step interface for creating teams
    with game-specific validation and real-time preview.
    """
    
    # Check if user already has teams in too many games (optional limit)
    # user_teams = request.user.profile.get_teams()
    # if user_teams.count() >= 5:
    #     messages.warning(request, "You already manage 5 teams. Consider leaving one before creating more.")
    
    context = {
        'user_profile_id': request.user.profile.id,
        'user_username': request.user.username,
        'user_email': request.user.email,
    }
    
    return render(request, 'teams/create_team_advanced.html', context)


@login_required
def team_creation_success(request, slug):
    """
    Success page after team creation.
    Redirects to team detail page with success message.
    """
    messages.success(
        request,
        f'🎉 Team created successfully! Welcome to your new team.'
    )
    return redirect('teams:detail', slug=slug)
