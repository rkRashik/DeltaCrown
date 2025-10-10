"""
Task 10: Optimized query utilities to prevent N+1 queries
"""
from django.db.models import Prefetch, Count, Q, F
from django.utils import timezone


class TeamQueryOptimizer:
    """
    Centralized query optimization for Team model to prevent N+1 queries.
    Use these methods in views and APIs for consistent performance.
    """
    
    @staticmethod
    def get_teams_with_related():
        """
        Get teams with commonly accessed related objects prefetched.
        Use this for list views (team hub, leaderboard, search results).
        """
        from apps.teams.models import Team
        
        return Team.objects.select_related(
            'captain',
            'captain__user',
        ).prefetch_related(
            'members',
            'members__profile',
            'members__profile__user',
        )
    
    @staticmethod
    def get_team_detail_optimized(slug):
        """
        Get single team with all related data for team detail page.
        Optimized for team profile views with social features.
        """
        from apps.teams.models import Team
        
        return Team.objects.select_related(
            'captain',
            'captain__user',
        ).prefetch_related(
            # Roster members
            Prefetch(
                'members',
                queryset=Team.members.rel.related_model.objects.select_related(
                    'profile',
                    'profile__user'
                ).filter(status='active').order_by('role', 'joined_at')
            ),
            # Recent posts
            Prefetch(
                'posts',
                queryset=Team.posts.rel.related_model.objects.select_related(
                    'author',
                    'author__user'
                ).filter(status='published').order_by('-created_at')[:10]
            ),
            # Active sponsors
            Prefetch(
                'sponsors',
                queryset=Team.sponsors.rel.related_model.objects.filter(
                    status='approved',
                    end_date__gte=timezone.now().date()
                ).order_by('-tier', '-start_date')
            ),
            # Recent achievements
            Prefetch(
                'achievements',
                queryset=Team.achievements.rel.related_model.objects.order_by('-earned_at')[:5]
            ),
        ).annotate(
            followers_total=Count('followers', distinct=True),
            posts_total=Count('posts', filter=Q(posts__status='published'), distinct=True),
            active_members_count=Count('members', filter=Q(members__status='active'), distinct=True),
        ).get(slug=slug)
    
    @staticmethod
    def get_leaderboard_optimized(game=None, limit=100):
        """
        Get optimized leaderboard query with pagination support.
        Use for leaderboard pages and ranking displays.
        """
        from apps.teams.models import Team
        
        queryset = Team.objects.select_related(
            'captain',
            'captain__user',
        ).annotate(
            members_count=Count('members', filter=Q(members__status='active'), distinct=True),
            recent_wins=Count('tournament_participations', filter=Q(
                tournament_participations__placement__lte=3,
                tournament_participations__tournament__end_date__gte=timezone.now() - timezone.timedelta(days=90)
            ), distinct=True)
        )
        
        if game:
            queryset = queryset.filter(game=game)
        
        return queryset.order_by('-total_points', 'name')[:limit]
    
    @staticmethod
    def get_team_roster_optimized(team):
        """
        Get optimized roster query for roster management views.
        """
        from apps.teams.models import TeamMembership
        
        return TeamMembership.objects.filter(
            team=team
        ).select_related(
            'profile',
            'profile__user',
        ).order_by(
            'role',  # Captain first, then players, then subs
            'joined_at'
        )
    
    @staticmethod
    def get_pending_invites_optimized(team):
        """
        Get pending invites with related data.
        """
        from apps.teams.models import TeamInvite
        
        return TeamInvite.objects.filter(
            team=team,
            status='pending',
            expires_at__gt=timezone.now()
        ).select_related(
            'inviter',
            'inviter__user',
            'invited_user',
        ).order_by('-created_at')
    
    @staticmethod
    def get_user_teams_optimized(user):
        """
        Get all teams a user is part of, with role information.
        """
        from apps.teams.models import Team, TeamMembership
        
        return Team.objects.filter(
            members__profile__user=user,
            members__status='active'
        ).select_related(
            'captain',
            'captain__user',
        ).prefetch_related(
            Prefetch(
                'members',
                queryset=TeamMembership.objects.filter(
                    profile__user=user,
                    status='active'
                ).select_related('profile'),
                to_attr='user_membership'
            )
        ).distinct()
    
    @staticmethod
    def get_team_followers_optimized(team, limit=50):
        """
        Get team followers with user data.
        """
        from apps.teams.models import TeamFollow
        
        return TeamFollow.objects.filter(
            team=team
        ).select_related(
            'user',
            'user__profile',
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_team_posts_optimized(team, status='published', limit=20):
        """
        Get team posts with author data and engagement metrics.
        """
        from apps.teams.models import TeamPost
        
        queryset = TeamPost.objects.filter(team=team)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related(
            'author',
            'author__user',
        ).annotate(
            likes_count=Count('likes', distinct=True),
            comments_count=Count('comments', distinct=True),
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def search_teams_optimized(query, game=None, limit=20):
        """
        Search teams with optimized query.
        """
        from apps.teams.models import Team
        from django.db.models import Q
        
        queryset = Team.objects.select_related(
            'captain',
            'captain__user',
        ).annotate(
            members_count=Count('members', filter=Q(members__status='active'), distinct=True),
        )
        
        # Search by name or tag
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(tag__icontains=query)
            )
        
        if game:
            queryset = queryset.filter(game=game)
        
        return queryset.order_by('-is_verified', '-followers_count', 'name')[:limit]


class TeamCacheKeys:
    """
    Centralized cache key generation for teams.
    Consistent naming prevents cache key conflicts.
    """
    
    @staticmethod
    def team_detail(slug):
        return f"team:detail:{slug}"
    
    @staticmethod
    def team_roster(team_id):
        return f"team:roster:{team_id}"
    
    @staticmethod
    def team_followers(team_id, page=1):
        return f"team:followers:{team_id}:page:{page}"
    
    @staticmethod
    def team_posts(team_id, page=1):
        return f"team:posts:{team_id}:page:{page}"
    
    @staticmethod
    def leaderboard(game=None, page=1):
        game_key = game or 'all'
        return f"leaderboard:{game_key}:page:{page}"
    
    @staticmethod
    def team_achievements(team_id):
        return f"team:achievements:{team_id}"
    
    @staticmethod
    def team_sponsors(team_id):
        return f"team:sponsors:{team_id}"
    
    @staticmethod
    def user_teams(user_id):
        return f"user:teams:{user_id}"
    
    @staticmethod
    def invalidate_team(team_id):
        """
        Return list of all cache keys to invalidate when team changes.
        """
        return [
            f"team:detail:*",
            f"team:roster:{team_id}",
            f"team:followers:{team_id}:*",
            f"team:posts:{team_id}:*",
            f"team:achievements:{team_id}",
            f"team:sponsors:{team_id}",
            f"leaderboard:*",
        ]


class TeamQueryFilters:
    """
    Common query filters for teams.
    """
    
    @staticmethod
    def active_teams():
        """Get only active teams (have captain and members)."""
        return Q(captain__isnull=False) & Q(members__isnull=False)
    
    @staticmethod
    def verified_teams():
        """Get only verified teams."""
        return Q(is_verified=True)
    
    @staticmethod
    def featured_teams():
        """Get featured teams."""
        return Q(is_featured=True)
    
    @staticmethod
    def recruiting_teams():
        """Get teams that are actively recruiting."""
        return Q(is_recruiting=True) & Q(captain__isnull=False)
    
    @staticmethod
    def game_teams(game):
        """Get teams for specific game."""
        return Q(game=game)
    
    @staticmethod
    def has_open_slots(max_roster=8):
        """Get teams with open roster slots."""
        from django.db.models import Count
        return Q(members__status='active').annotate(
            active_count=Count('members')
        ).filter(active_count__lt=max_roster)
