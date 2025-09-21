# apps/corepages/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

def about(request):
    return render(request, "pages/about.html", {})

def community(request):
    """Community Hub - Display recent team posts and activities"""
    try:
        from apps.teams.models.social import TeamPost
        from apps.teams.models._legacy import Team
        
        # Get public team posts for community feed
        posts = TeamPost.objects.filter(
            visibility='public'
        ).select_related(
            'author__user', 
            'team'
        ).prefetch_related(
            'likes',
            'comments__author__user',
            'media'
        ).order_by('-created_at')
        
        # Filter by game if requested
        game_filter = request.GET.get('game')
        if game_filter:
            posts = posts.filter(team__game=game_filter)
        
        # Search functionality
        search_query = request.GET.get('q')
        if search_query:
            posts = posts.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query) |
                Q(team__name__icontains=search_query)
            )
        
        # Pagination
        paginator = Paginator(posts, 10)
        page_number = request.GET.get('page')
        posts_page = paginator.get_page(page_number)
        
        # Get available games for filtering
        games = Team.objects.values_list('game', flat=True).distinct()
        
        # Recent teams for sidebar
        featured_teams = Team.objects.filter(
            is_active=True
        ).order_by('-created_at')[:5]
        
        context = {
            'posts': posts_page,
            'games': games,
            'current_game': game_filter,
            'search_query': search_query,
            'featured_teams': featured_teams,
        }
        
    except ImportError:
        # Fallback if teams social features aren't available
        context = {
            'posts': [],
            'games': [],
            'current_game': None,
            'search_query': None,
            'featured_teams': [],
        }
    
    return render(request, "pages/community.html", context)

@login_required
def notifications_index(request):
    # You can hydrate from your model later; render empty safely
    return render(request, "notifications/list.html", {"notifications": []})
