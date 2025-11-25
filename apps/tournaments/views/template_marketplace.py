"""
Template Library Views

Public-facing library for browsing and discovering registration form templates.
"""
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from apps.tournaments.models import RegistrationFormTemplate, TemplateRating
from apps.tournaments.services.template_marketplace import TemplateMarketplaceService
from apps.tournaments.services.form_render_service import FormTemplateService


class TemplateMarketplaceView(ListView):
    """
    Main library view for browsing registration form templates.
    
    Features:
    - Search and filter by game, participation type, tags
    - Sort by popularity, rating, newest
    - Featured templates section
    - Tag cloud
    """
    
    model = RegistrationFormTemplate
    template_name = 'tournaments/marketplace/browse.html'
    context_object_name = 'templates'
    paginate_by = 12
    
    def get_queryset(self):
        marketplace = TemplateMarketplaceService(user=self.request.user)
        
        # Get filter parameters
        game_id = self.request.GET.get('game')
        participation_type = self.request.GET.get('type')
        tags = self.request.GET.getlist('tags')
        search_query = self.request.GET.get('q')
        featured_only = self.request.GET.get('featured') == '1'
        min_rating = self.request.GET.get('min_rating')
        sort_by = self.request.GET.get('sort', 'popular')
        
        # Convert min_rating to float if provided
        if min_rating:
            try:
                min_rating = float(min_rating)
            except ValueError:
                min_rating = None
        
        return marketplace.browse_templates(
            game_id=game_id,
            participation_type=participation_type,
            tags=tags,
            search_query=search_query,
            featured_only=featured_only,
            min_rating=min_rating,
            sort_by=sort_by
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        marketplace = TemplateMarketplaceService(user=self.request.user)
        
        # Add featured templates
        context['featured_templates'] = marketplace.get_featured_templates(limit=6)
        
        # Add trending templates
        context['trending_templates'] = marketplace.get_trending_templates(limit=5)
        
        # Add popular tags
        context['popular_tags'] = marketplace.get_popular_tags(limit=20)
        
        # Add filter context
        context['current_filters'] = {
            'game': self.request.GET.get('game'),
            'type': self.request.GET.get('type'),
            'tags': self.request.GET.getlist('tags'),
            'q': self.request.GET.get('q'),
            'featured': self.request.GET.get('featured') == '1',
            'min_rating': self.request.GET.get('min_rating'),
            'sort': self.request.GET.get('sort', 'popular'),
        }
        
        # Add available games for filter dropdown
        from apps.tournaments.models import Game
        context['available_games'] = Game.objects.filter(is_active=True).order_by('name')
        
        # Add participation types
        context['participation_types'] = [
            {'value': 'solo', 'label': 'Solo'},
            {'value': 'team', 'label': 'Team'},
            {'value': 'mixed', 'label': 'Mixed'},
        ]
        
        return context


class TemplateDetailView(DetailView):
    """
    Detailed view of a single template.
    
    Shows:
    - Full template schema preview
    - Ratings and reviews
    - Statistics and analytics
    - Similar templates
    - Clone/use options
    """
    
    model = RegistrationFormTemplate
    template_name = 'tournaments/marketplace/template_detail.html'
    context_object_name = 'template'
    
    def get_object(self):
        return get_object_or_404(
            RegistrationFormTemplate.objects.filter(is_active=True),
            slug=self.kwargs['slug']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.object
        marketplace = TemplateMarketplaceService(user=self.request.user)
        
        # Get template statistics
        context['statistics'] = marketplace.get_template_statistics(template.id)
        
        # Get recent ratings
        context['recent_ratings'] = TemplateRating.objects.filter(
            template=template
        ).select_related('user', 'tournament').order_by('-created_at')[:10]
        
        # Get similar templates
        context['similar_templates'] = marketplace.get_similar_templates(
            template.id, limit=4
        )
        
        # Check if user has rated this template
        if self.request.user.is_authenticated:
            context['user_rating'] = TemplateRating.objects.filter(
                template=template,
                user=self.request.user
            ).first()
        
        # Get top rated reviews
        context['top_reviews'] = TemplateRating.objects.filter(
            template=template,
            review__isnull=False
        ).exclude(review='').order_by('-helpful_count', '-rating')[:5]
        
        return context


class CloneTemplateView(LoginRequiredMixin, DetailView):
    """
    Clone a template to user's account.
    
    Creates a copy of the template that the user can customize.
    """
    
    model = RegistrationFormTemplate
    
    def get_object(self):
        return get_object_or_404(
            RegistrationFormTemplate.objects.filter(is_active=True),
            slug=self.kwargs['slug']
        )
    
    def post(self, request, *args, **kwargs):
        template = self.get_object()
        
        # Clone the template
        cloned = template.duplicate(
            user=request.user,
            name_prefix=f"{template.name} (My Copy)"
        )
        
        messages.success(
            request,
            f'Template "{template.name}" cloned successfully! You can now customize it.'
        )
        
        # Redirect to admin edit page for the cloned template
        return redirect('admin:tournaments_registrationformtemplate_change', cloned.id)


class RateTemplateView(LoginRequiredMixin, CreateView):
    """
    Rate and review a template.
    
    Allows organizers to share their experience using a template.
    """
    
    model = TemplateRating
    template_name = 'tournaments/marketplace/rate_template.html'
    fields = [
        'rating', 'title', 'review',
        'ease_of_use', 'participant_experience', 'data_quality',
        'would_recommend'
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = get_object_or_404(
            RegistrationFormTemplate,
            slug=self.kwargs['slug']
        )
        return context
    
    def form_valid(self, form):
        template = get_object_or_404(
            RegistrationFormTemplate,
            slug=self.kwargs['slug']
        )
        
        # Check if user already rated this template
        existing_rating = TemplateRating.objects.filter(
            template=template,
            user=self.request.user
        ).first()
        
        if existing_rating:
            # Update existing rating
            for field in self.fields:
                setattr(existing_rating, field, form.cleaned_data[field])
            existing_rating.save()
            
            messages.success(self.request, 'Your rating has been updated!')
            return redirect('tournaments:template_detail', slug=template.slug)
        
        # Create new rating
        form.instance.template = template
        form.instance.user = self.request.user
        
        messages.success(self.request, 'Thank you for rating this template!')
        
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('tournaments:template_detail', kwargs={
            'slug': self.kwargs['slug']
        })


class MarkRatingHelpfulView(LoginRequiredMixin, DetailView):
    """
    Mark a rating as helpful.
    
    AJAX endpoint for voting on reviews.
    """
    
    model = TemplateRating
    
    def post(self, request, *args, **kwargs):
        rating = self.get_object()
        
        # Check if user already marked this helpful
        from apps.tournaments.models import RatingHelpful
        
        existing_vote = RatingHelpful.objects.filter(
            rating=rating,
            user=request.user
        ).first()
        
        if existing_vote:
            return JsonResponse({
                'success': False,
                'message': 'You already marked this review as helpful'
            })
        
        # Create helpful vote
        RatingHelpful.objects.create(
            rating=rating,
            user=request.user
        )
        
        # Increment helpful count
        rating.mark_helpful()
        
        return JsonResponse({
            'success': True,
            'helpful_count': rating.helpful_count,
            'message': 'Thank you for your feedback!'
        })
