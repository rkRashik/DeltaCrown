# apps/teams/views/advanced_form.py
"""
Advanced Team Creation Form View
Integrates with the new frontend UI and REST API.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def _legacy_create_team_advanced_view(request):
    """
    DEPRECATED: Render the advanced team creation form.
    Use apps.teams.views.create.team_create_view instead.
    
    This function is deprecated and will be removed in Phase 2.
    """
    import warnings
    warnings.warn(
        "create_team_advanced_view is deprecated. Use apps.teams.views.create.team_create_view instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Redirect to new implementation
    from apps.teams.views.create import team_create_view
    return team_create_view(request)


# Old function kept for backward compatibility - DO NOT USE
create_team_advanced_view = _legacy_create_team_advanced_view


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
