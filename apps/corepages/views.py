# apps/corepages/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

def about(request):
    return render(request, "pages/about.html", {})

def community(request):
    """Community Hub - Display recent team posts and activities.

    NOTE: Legacy TeamPost model was removed (Phase B cleanup).
    This view now returns an empty feed until the new
    organizations-based community feed is built.
    """
    from apps.organizations.models import Team

    featured_teams = Team.objects.filter(
        is_active=True
    ).order_by('-created_at')[:5]

    context = {
        'posts': [],
        'games': [],
        'current_game': request.GET.get('game'),
        'search_query': request.GET.get('q'),
        'featured_teams': featured_teams,
    }
    return render(request, "pages/community.html", context)

@login_required
def notifications_index(request):
    # You can hydrate from your model later; render empty safely
    return render(request, "notifications/list.html", {"notifications": []})
