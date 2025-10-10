"""
Sponsorship Views
Handles sponsor display, inquiry submission, and click tracking
"""
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages as django_messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from apps.teams.models import Team
from apps.teams.models.sponsorship import (
    TeamSponsor,
    SponsorInquiry,
    TeamMerchItem,
    TeamPromotion,
)


class TeamSponsorsView(DetailView):
    """
    Display all sponsors for a team
    """
    model = Team
    template_name = 'teams/sponsors.html'
    context_object_name = 'team'
    slug_field = 'slug'
    slug_url_kwarg = 'team_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        
        # Get active sponsors grouped by tier
        active_sponsors = team.sponsors.filter(
            status='active',
            is_active=True
        ).order_by('display_order', '-sponsor_tier')
        
        context.update({
            'active_sponsors': active_sponsors,
            'platinum_sponsors': active_sponsors.filter(sponsor_tier='platinum'),
            'gold_sponsors': active_sponsors.filter(sponsor_tier='gold'),
            'silver_sponsors': active_sponsors.filter(sponsor_tier='silver'),
            'bronze_sponsors': active_sponsors.filter(sponsor_tier='bronze'),
            'partners': active_sponsors.filter(sponsor_tier='partner'),
            'has_sponsors': active_sponsors.exists(),
        })
        
        # Increment impressions for all sponsors
        for sponsor in active_sponsors:
            sponsor.increment_impressions()
        
        return context


class SponsorInquiryView(View):
    """
    Handle sponsor inquiry form submission
    """
    
    def get(self, request, team_slug):
        """Display inquiry form"""
        team = get_object_or_404(Team, slug=team_slug)
        return render(request, 'teams/sponsor_inquiry.html', {
            'team': team,
            'tier_choices': TeamSponsor.TIER_CHOICES,
        })
    
    def post(self, request, team_slug):
        """Process inquiry submission"""
        team = get_object_or_404(Team, slug=team_slug)
        
        # Rate limiting check - max 3 inquiries per IP per day
        ip_address = self.get_client_ip(request)
        today_start = timezone.now().replace(hour=0, minute=0, second=0)
        recent_inquiries = SponsorInquiry.objects.filter(
            ip_address=ip_address,
            created_at__gte=today_start
        ).count()
        
        if recent_inquiries >= 3:
            return JsonResponse({
                'success': False,
                'error': 'Too many inquiries. Please try again tomorrow.'
            }, status=429)
        
        # Validate required fields
        required_fields = ['company_name', 'contact_name', 'contact_email', 'message']
        for field in required_fields:
            if not request.POST.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'{field.replace("_", " ").title()} is required.'
                }, status=400)
        
        # Create inquiry
        try:
            inquiry = SponsorInquiry.objects.create(
                team=team,
                company_name=request.POST.get('company_name'),
                contact_name=request.POST.get('contact_name'),
                contact_email=request.POST.get('contact_email'),
                contact_phone=request.POST.get('contact_phone', ''),
                website=request.POST.get('website', ''),
                interested_tier=request.POST.get('interested_tier', ''),
                budget_range=request.POST.get('budget_range', ''),
                message=request.POST.get('message'),
                industry=request.POST.get('industry', ''),
                company_size=request.POST.get('company_size', ''),
                previous_sponsorships=request.POST.get('previous_sponsorships', ''),
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            # Send notification to team admins (handled by service)
            from apps.teams.services.sponsorship import SponsorshipService
            SponsorshipService._notify_team_admins(inquiry)
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you! Your inquiry has been submitted. The team will contact you soon.'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            }, status=500)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SponsorClickTrackingView(View):
    """
    Track sponsor clicks and redirect to sponsor website
    """
    
    def get(self, request, sponsor_id):
        """Redirect to sponsor link and track click"""
        sponsor = get_object_or_404(TeamSponsor, id=sponsor_id, is_active=True)
        
        # Increment click counter
        sponsor.increment_clicks()
        
        # Redirect to sponsor website
        return HttpResponseRedirect(sponsor.sponsor_link)


class TeamMerchandiseView(DetailView):
    """
    Display team merchandise store
    """
    model = Team
    template_name = 'teams/merchandise.html'
    context_object_name = 'team'
    slug_field = 'slug'
    slug_url_kwarg = 'team_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        
        # Get active merchandise
        merchandise = team.merchandise.filter(is_active=True)
        
        # Filter by category if provided
        category = self.request.GET.get('category')
        if category:
            merchandise = merchandise.filter(category=category)
        
        # Sort by featured, then display order
        merchandise = merchandise.order_by('-is_featured', 'display_order', '-created_at')
        
        context.update({
            'merchandise': merchandise,
            'featured_items': merchandise.filter(is_featured=True)[:6],
            'categories': TeamMerchItem.CATEGORY_CHOICES,
            'selected_category': category,
        })
        
        # Increment views for all items
        for item in merchandise:
            item.increment_views()
        
        return context


class MerchItemDetailView(DetailView):
    """
    Display single merchandise item details
    """
    model = TeamMerchItem
    template_name = 'teams/merch_item_detail.html'
    context_object_name = 'item'
    pk_url_kwarg = 'item_id'
    
    def get_queryset(self):
        """Filter by team slug"""
        team_slug = self.kwargs.get('team_slug')
        return TeamMerchItem.objects.filter(
            team__slug=team_slug,
            is_active=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.object
        
        # Increment view counter
        item.increment_views()
        
        # Get related items from same team
        related_items = item.team.merchandise.filter(
            is_active=True
        ).exclude(id=item.id).order_by('-is_featured', '?')[:4]
        
        context.update({
            'team': item.team,
            'related_items': related_items,
        })
        
        return context


class MerchClickTrackingView(View):
    """
    Track merchandise clicks and redirect to external store
    """
    
    def get(self, request, item_id):
        """Redirect to external store and track click"""
        item = get_object_or_404(TeamMerchItem, id=item_id, is_active=True)
        
        # Increment click counter
        item.increment_clicks()
        
        # Redirect to external link or affiliate link
        redirect_url = item.affiliate_link or item.external_link
        if redirect_url:
            return HttpResponseRedirect(redirect_url)
        else:
            django_messages.error(request, 'Store link not available.')
            return redirect('teams:team_merchandise', team_slug=item.team.slug)


class FeaturedTeamsView(ListView):
    """
    Display featured/promoted teams on homepage
    """
    model = TeamPromotion
    template_name = 'teams/featured_teams.html'
    context_object_name = 'promotions'
    
    def get_queryset(self):
        """Get active featured homepage promotions"""
        return TeamPromotion.objects.filter(
            promotion_type='featured_homepage',
            is_active=True,
            status='active'
        ).select_related('team').order_by('-start_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Increment impressions for all promotions
        for promotion in context['promotions']:
            promotion.increment_impressions()
        
        return context


class TeamHubFeaturedView(ListView):
    """
    Display featured teams in team hub
    """
    model = TeamPromotion
    template_name = 'teams/hub_featured.html'
    context_object_name = 'promotions'
    
    def get_queryset(self):
        """Get active hub featured promotions"""
        return TeamPromotion.objects.filter(
            promotion_type='featured_hub',
            is_active=True,
            status='active'
        ).select_related('team').order_by('-start_at')[:6]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Increment impressions for all promotions
        for promotion in context['promotions']:
            promotion.increment_impressions()
        
        return context


class PromotionClickTrackingView(View):
    """
    Track promotion clicks and redirect to team page
    """
    
    def get(self, request, promotion_id):
        """Track click and redirect to team"""
        promotion = get_object_or_404(
            TeamPromotion, 
            id=promotion_id, 
            is_active=True
        )
        
        # Increment click counter
        promotion.increment_clicks()
        
        # Redirect to team profile
        return redirect('teams:team_detail', slug=promotion.team.slug)


class SponsorshipAPIView(View):
    """
    API endpoint for sponsorship operations
    """
    
    def post(self, request):
        """Handle various API actions"""
        action = request.POST.get('action')
        
        if action == 'track_sponsor_impression':
            return self._track_sponsor_impression(request)
        elif action == 'track_promotion_impression':
            return self._track_promotion_impression(request)
        elif action == 'get_sponsors':
            return self._get_team_sponsors(request)
        elif action == 'get_merchandise':
            return self._get_team_merchandise(request)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            }, status=400)
    
    def _track_sponsor_impression(self, request):
        """Track sponsor impression"""
        sponsor_id = request.POST.get('sponsor_id')
        if not sponsor_id:
            return JsonResponse({'success': False, 'error': 'Missing sponsor_id'}, status=400)
        
        try:
            sponsor = TeamSponsor.objects.get(id=sponsor_id, is_active=True)
            sponsor.increment_impressions()
            return JsonResponse({'success': True})
        except TeamSponsor.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sponsor not found'}, status=404)
    
    def _track_promotion_impression(self, request):
        """Track promotion impression"""
        promotion_id = request.POST.get('promotion_id')
        if not promotion_id:
            return JsonResponse({'success': False, 'error': 'Missing promotion_id'}, status=400)
        
        try:
            promotion = TeamPromotion.objects.get(id=promotion_id, is_active=True)
            promotion.increment_impressions()
            return JsonResponse({'success': True})
        except TeamPromotion.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Promotion not found'}, status=404)
    
    def _get_team_sponsors(self, request):
        """Get sponsors for a team"""
        team_slug = request.POST.get('team_slug')
        if not team_slug:
            return JsonResponse({'success': False, 'error': 'Missing team_slug'}, status=400)
        
        try:
            team = Team.objects.get(slug=team_slug)
            sponsors = team.sponsors.filter(status='active', is_active=True).values(
                'id',
                'sponsor_name',
                'sponsor_tier',
                'sponsor_logo_url',
                'sponsor_link'
            )
            return JsonResponse({
                'success': True,
                'sponsors': list(sponsors)
            })
        except Team.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Team not found'}, status=404)
    
    def _get_team_merchandise(self, request):
        """Get merchandise for a team"""
        team_slug = request.POST.get('team_slug')
        if not team_slug:
            return JsonResponse({'success': False, 'error': 'Missing team_slug'}, status=400)
        
        try:
            team = Team.objects.get(slug=team_slug)
            merchandise = team.merchandise.filter(is_active=True).values(
                'id',
                'title',
                'category',
                'price',
                'sale_price',
                'currency',
                'is_in_stock',
                'image_url'
            )
            return JsonResponse({
                'success': True,
                'merchandise': list(merchandise)
            })
        except Team.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Team not found'}, status=404)


class SponsorDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard for team admins to view sponsor analytics
    """
    template_name = 'teams/sponsor_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team_slug = self.kwargs.get('team_slug')
        team = get_object_or_404(Team, slug=team_slug)
        
        # Check if user is team admin/captain
        membership = team.members.filter(player__user=self.request.user).first()
        if not membership or membership.role not in ['captain', 'co_captain']:
            django_messages.error(self.request, 'You do not have permission to view this page.')
            return redirect('teams:team_detail', slug=team.slug)
        
        # Get sponsor statistics
        all_sponsors = team.sponsors.all()
        active_sponsors = all_sponsors.filter(status='active', is_active=True)
        pending_sponsors = all_sponsors.filter(status='pending')
        
        # Get merchandise statistics
        all_merch = team.merchandise.all()
        active_merch = all_merch.filter(is_active=True)
        
        # Get promotions
        all_promotions = team.promotions.all()
        active_promotions = all_promotions.filter(is_active=True)
        
        # Get recent inquiries
        recent_inquiries = team.sponsor_inquiries.filter(
            status='pending'
        ).order_by('-created_at')[:10]
        
        context.update({
            'team': team,
            'all_sponsors': all_sponsors,
            'active_sponsors': active_sponsors,
            'pending_sponsors': pending_sponsors,
            'all_merch': all_merch,
            'active_merch': active_merch,
            'all_promotions': all_promotions,
            'active_promotions': active_promotions,
            'recent_inquiries': recent_inquiries,
            'total_sponsor_clicks': sum(s.click_count for s in all_sponsors),
            'total_sponsor_impressions': sum(s.impression_count for s in all_sponsors),
            'total_merch_views': sum(m.view_count for m in all_merch),
            'total_merch_clicks': sum(m.click_count for m in all_merch),
        })
        
        return context


# Import render for template rendering
from django.shortcuts import render
