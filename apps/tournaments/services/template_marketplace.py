"""
Template Library Service

Handles template discovery, search, filtering, and recommendations.
"""
from django.db.models import Q, Count, Avg, F, Case, When, IntegerField, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Optional
from apps.tournaments.models import RegistrationFormTemplate


class TemplateMarketplaceService:
    """
    Service for browsing and discovering registration form templates.
    
    Provides search, filtering, sorting, and recommendation features
    for the template marketplace.
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def browse_templates(
        self,
        game_id: Optional[int] = None,
        participation_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        featured_only: bool = False,
        min_rating: Optional[float] = None,
        sort_by: str = 'popular'
    ):
        """
        Browse templates with advanced filtering and sorting.
        
        Args:
            game_id: Filter by game
            participation_type: Filter by solo/team/mixed
            tags: Filter by tags (AND logic)
            search_query: Search in name and description
            featured_only: Show only featured templates
            min_rating: Minimum average rating
            sort_by: Sort order (popular, newest, highest_rated, most_used)
        
        Returns:
            QuerySet of templates with annotations
        """
        queryset = RegistrationFormTemplate.objects.filter(
            is_active=True
        ).select_related(
            'game'
        ).annotate(
            rating_count=Count('ratings'),
            avg_rating=Coalesce(Avg('ratings__rating'), 0.0),
            avg_ease_of_use=Coalesce(Avg('ratings__ease_of_use'), 0.0),
            avg_participant_experience=Coalesce(Avg('ratings__participant_experience'), 0.0),
            avg_data_quality=Coalesce(Avg('ratings__data_quality'), 0.0),
            recommend_percentage=Case(
                When(rating_count=0, then=0.0),
                default=100.0 * Count(
                    Case(When(ratings__would_recommend=True, then=1))
                ) / F('rating_count'),
                output_field=FloatField()
            )
        )
        
        # Filter by game
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        
        # Filter by participation type
        if participation_type:
            queryset = queryset.filter(participation_type=participation_type)
        
        # Filter by tags (AND logic - template must have ALL tags)
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        # Search query
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__icontains=[search_query])
            )
        
        # Featured only
        if featured_only:
            queryset = queryset.filter(is_featured=True)
        
        # Minimum rating
        if min_rating:
            queryset = queryset.filter(avg_rating__gte=min_rating)
        
        # Sorting
        sort_mapping = {
            'popular': '-usage_count',
            'newest': '-created_at',
            'highest_rated': '-avg_rating',
            'most_used': '-usage_count',
            'recently_updated': '-updated_at',
            'name': 'name',
        }
        
        order_by = sort_mapping.get(sort_by, '-usage_count')
        queryset = queryset.order_by(order_by, '-is_featured', '-created_at')
        
        return queryset
    
    def get_featured_templates(self, limit: int = 6):
        """
        Get featured templates for homepage/marketplace landing.
        
        Returns top-rated featured templates across different categories.
        """
        return self.browse_templates(
            featured_only=True,
            sort_by='highest_rated'
        )[:limit]
    
    def get_trending_templates(self, days: int = 30, limit: int = 10):
        """
        Get trending templates based on recent usage and ratings.
        
        Calculates a trending score based on:
        - Recent usage (last 30 days)
        - Recent ratings
        - Average rating
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        queryset = RegistrationFormTemplate.objects.filter(
            is_active=True
        ).annotate(
            recent_usage=Count(
                'tournament_forms',
                filter=Q(tournament_forms__created_at__gte=cutoff_date)
            ),
            recent_ratings=Count(
                'ratings',
                filter=Q(ratings__created_at__gte=cutoff_date)
            ),
            avg_rating=Coalesce(Avg('ratings__rating'), 0.0),
            trending_score=F('recent_usage') * 2 + F('recent_ratings') * 3 + F('avg_rating') * 10
        ).filter(
            trending_score__gt=0
        ).order_by('-trending_score')[:limit]
        
        return queryset
    
    def get_recommended_for_user(self, limit: int = 5):
        """
        Get personalized template recommendations for the current user.
        
        Based on:
        - User's previous tournament games
        - User's previous participation types
        - Popular templates in their categories
        """
        if not self.user or not self.user.is_authenticated:
            # Return popular templates for anonymous users
            return self.browse_templates(sort_by='popular')[:limit]
        
        # Get user's tournament history
        from apps.tournaments.models import Tournament
        
        user_tournaments = Tournament.objects.filter(
            organizer=self.user
        ).select_related('game')
        
        # Extract games and participation types
        user_games = set(t.game_id for t in user_tournaments if t.game_id)
        user_participation_types = set(
            t.participation_type for t in user_tournaments if t.participation_type
        )
        
        # Build recommendation query
        queryset = RegistrationFormTemplate.objects.filter(
            is_active=True
        ).annotate(
            avg_rating=Coalesce(Avg('ratings__rating'), 0.0),
            relevance_score=Case(
                # Higher score for matching game AND participation type
                When(
                    game_id__in=user_games,
                    participation_type__in=user_participation_types,
                    then=100
                ),
                # Medium score for matching game only
                When(game_id__in=user_games, then=50),
                # Lower score for matching participation type only
                When(participation_type__in=user_participation_types, then=30),
                # Default score
                default=0,
                output_field=IntegerField()
            ),
            final_score=F('relevance_score') + F('avg_rating') * 10 + F('usage_count') / 10
        ).order_by('-final_score', '-is_featured')[:limit]
        
        return queryset
    
    def get_similar_templates(self, template_id: int, limit: int = 4):
        """
        Find templates similar to a given template.
        
        Based on:
        - Same game
        - Same participation type
        - Overlapping tags
        """
        try:
            template = RegistrationFormTemplate.objects.get(id=template_id)
        except RegistrationFormTemplate.DoesNotExist:
            return RegistrationFormTemplate.objects.none()
        
        queryset = RegistrationFormTemplate.objects.filter(
            is_active=True
        ).exclude(
            id=template_id
        ).annotate(
            avg_rating=Coalesce(Avg('ratings__rating'), 0.0),
            similarity_score=Case(
                # Exact match on game and participation type
                When(
                    game_id=template.game_id,
                    participation_type=template.participation_type,
                    then=100
                ),
                # Match on game only
                When(game_id=template.game_id, then=60),
                # Match on participation type only
                When(participation_type=template.participation_type, then=40),
                default=0,
                output_field=IntegerField()
            )
        )
        
        # Boost score for overlapping tags
        if template.tags:
            for tag in template.tags:
                queryset = queryset.annotate(
                    **{f'has_tag_{tag}': Case(
                        When(tags__contains=[tag], then=10),
                        default=0,
                        output_field=IntegerField()
                    )}
                )
        
        queryset = queryset.order_by('-similarity_score', '-avg_rating', '-usage_count')[:limit]
        
        return queryset
    
    def get_template_statistics(self, template_id: int) -> Dict:
        """
        Get comprehensive statistics for a template.
        
        Returns:
            Dict with rating breakdown, usage stats, and trends
        """
        try:
            template = RegistrationFormTemplate.objects.annotate(
                rating_count=Count('ratings'),
                avg_rating=Coalesce(Avg('ratings__rating'), 0.0),
                avg_ease_of_use=Coalesce(Avg('ratings__ease_of_use'), 0.0),
                avg_participant_experience=Coalesce(Avg('ratings__participant_experience'), 0.0),
                avg_data_quality=Coalesce(Avg('ratings__data_quality'), 0.0),
                five_star=Count(Case(When(ratings__rating=5, then=1))),
                four_star=Count(Case(When(ratings__rating=4, then=1))),
                three_star=Count(Case(When(ratings__rating=3, then=1))),
                two_star=Count(Case(When(ratings__rating=2, then=1))),
                one_star=Count(Case(When(ratings__rating=1, then=1))),
                recommend_count=Count(Case(When(ratings__would_recommend=True, then=1))),
            ).get(id=template_id)
        except RegistrationFormTemplate.DoesNotExist:
            return {}
        
        # Calculate percentages for star distribution
        total_ratings = template.rating_count
        
        star_distribution = {}
        if total_ratings > 0:
            star_distribution = {
                5: {
                    'count': template.five_star,
                    'percentage': round((template.five_star / total_ratings) * 100, 1)
                },
                4: {
                    'count': template.four_star,
                    'percentage': round((template.four_star / total_ratings) * 100, 1)
                },
                3: {
                    'count': template.three_star,
                    'percentage': round((template.three_star / total_ratings) * 100, 1)
                },
                2: {
                    'count': template.two_star,
                    'percentage': round((template.two_star / total_ratings) * 100, 1)
                },
                1: {
                    'count': template.one_star,
                    'percentage': round((template.one_star / total_ratings) * 100, 1)
                },
            }
        
        # Calculate recommendation percentage
        recommend_percentage = 0
        if total_ratings > 0:
            recommend_percentage = round((template.recommend_count / total_ratings) * 100, 1)
        
        return {
            'template_id': template.id,
            'template_name': template.name,
            'total_ratings': total_ratings,
            'average_rating': round(template.avg_rating, 2),
            'star_distribution': star_distribution,
            'aspects': {
                'ease_of_use': round(template.avg_ease_of_use, 2),
                'participant_experience': round(template.avg_participant_experience, 2),
                'data_quality': round(template.avg_data_quality, 2),
            },
            'usage_count': template.usage_count,
            'recommendation_rate': recommend_percentage,
            'is_featured': template.is_featured,
            'created_at': template.created_at,
            'updated_at': template.updated_at,
        }
    
    def get_popular_tags(self, limit: int = 20) -> List[Dict]:
        """
        Get most popular tags across all templates.
        
        Returns list of tags with usage counts.
        """
        from django.contrib.postgres.aggregates import ArrayAgg
        
        # Get all active templates with tags
        templates = RegistrationFormTemplate.objects.filter(
            is_active=True,
            tags__isnull=False
        ).exclude(tags=[])
        
        # Flatten all tags and count occurrences
        tag_counts = {}
        for template in templates:
            for tag in template.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count and return top N
        sorted_tags = sorted(
            tag_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'tag': tag, 'count': count}
            for tag, count in sorted_tags
        ]
