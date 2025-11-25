"""
Registration Management Dashboard

Comprehensive dashboard for tournament organizers to manage registrations.
Integrates all features: export, bulk actions, analytics, webhooks.
"""
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum, F
from django.http import JsonResponse
from django.views import View
from datetime import datetime, timedelta
from apps.tournaments.models import (
    TournamentRegistrationForm,
    FormResponse,
)
from apps.tournaments.services.form_analytics import FormAnalyticsService


class RegistrationManagementDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Main registration management dashboard.
    
    Features:
    - List all registrations with filters
    - Bulk selection and actions
    - Quick stats overview
    - Export and analytics links
    - Payment management
    """
    
    model = FormResponse
    template_name = 'tournaments/registration_dashboard/dashboard.html'
    context_object_name = 'responses'
    paginate_by = 25
    
    def test_func(self):
        """Only tournament organizer can access"""
        tournament_form = self.get_tournament_form()
        return (
            self.request.user == tournament_form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        if not hasattr(self, '_tournament_form'):
            self._tournament_form = get_object_or_404(
                TournamentRegistrationForm.objects.select_related('tournament', 'based_on_template'),
                tournament__slug=self.kwargs['tournament_slug']
            )
        return self._tournament_form
    
    def get_queryset(self):
        tournament_form = self.get_tournament_form()
        queryset = FormResponse.objects.filter(
            tournament_form=tournament_form
        ).select_related('user', 'team').order_by('-created_at')
        
        # Apply filters
        status = self.request.GET.getlist('status')
        if status:
            queryset = queryset.filter(status__in=status)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(team__name__icontains=search)
            )
        
        has_paid = self.request.GET.get('has_paid')
        if has_paid == 'true':
            queryset = queryset.filter(has_paid=True)
        elif has_paid == 'false':
            queryset = queryset.filter(has_paid=False)
        
        payment_verified = self.request.GET.get('payment_verified')
        if payment_verified == 'true':
            queryset = queryset.filter(payment_verified=True)
        elif payment_verified == 'false':
            queryset = queryset.filter(has_paid=True, payment_verified=False)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__gte=date_from_dt)
            except ValueError:
                pass
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__lte=date_to_dt)
            except ValueError:
                pass
        
        # Sorting
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = [
            'created_at', '-created_at',
            'submitted_at', '-submitted_at',
            'status', '-status',
            'user__username', '-user__username',
        ]
        if sort in valid_sorts:
            queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament_form = self.get_tournament_form()
        
        context['tournament'] = tournament_form.tournament
        context['tournament_form'] = tournament_form
        
        # Get overall stats
        all_responses = FormResponse.objects.filter(registration_form=tournament_form)
        
        context['stats'] = {
            'total': all_responses.count(),
            'drafts': all_responses.filter(status='draft').count(),
            'submitted': all_responses.filter(status='submitted').count(),
            'approved': all_responses.filter(status='approved').count(),
            'rejected': all_responses.filter(status='rejected').count(),
            'paid': all_responses.filter(has_paid=True).count(),
            'verified': all_responses.filter(payment_verified=True).count(),
            'pending_approval': all_responses.filter(status='submitted').count(),
            'pending_payment_verification': all_responses.filter(
                has_paid=True,
                payment_verified=False
            ).count(),
        }
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        context['recent_activity'] = {
            'new_registrations': all_responses.filter(created_at__gte=week_ago).count(),
            'new_submissions': all_responses.filter(
                status__in=['submitted', 'approved'],
                submitted_at__gte=week_ago
            ).count(),
            'new_payments': all_responses.filter(
                has_paid=True,
                updated_at__gte=week_ago
            ).count(),
        }
        
        # Get quick analytics
        analytics_service = FormAnalyticsService(tournament_form.id)
        context['quick_metrics'] = analytics_service.get_overview_metrics()
        
        # Current filters
        context['current_filters'] = {
            'status': self.request.GET.getlist('status'),
            'search': self.request.GET.get('search', ''),
            'has_paid': self.request.GET.get('has_paid', ''),
            'payment_verified': self.request.GET.get('payment_verified', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'sort': self.request.GET.get('sort', '-created_at'),
        }
        
        # Check if webhooks are configured
        context['has_webhooks'] = tournament_form.webhooks.filter(is_active=True).exists()
        
        return context


class ResponseDetailAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Get detailed information about a single response.
    
    Returns complete response data for modal/preview.
    """
    
    def test_func(self):
        response = self.get_response()
        return (
            self.request.user == response.registration_form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_response(self):
        if not hasattr(self, '_response'):
            self._response = get_object_or_404(
                FormResponse.objects.select_related(
                    'registration_form__tournament',
                    'registration_form__based_on_template',
                    'user',
                    'team'
                ),
                id=self.kwargs['response_id']
            )
        return self._response
    
    def get(self, request, *args, **kwargs):
        response = self.get_response()
        
        # Build detailed response data
        data = {
            'id': response.id,
            'status': response.status,
            'status_display': response.get_status_display(),
            'user': {
                'id': response.user.id if response.user else None,
                'username': response.user.username if response.user else None,
                'email': response.user.email if response.user else None,
            } if response.user else None,
            'team': {
                'id': response.team.id if response.team else None,
                'name': response.team.name if response.team else None,
            } if response.team else None,
            'has_paid': response.has_paid,
            'payment_verified': response.payment_verified,
            'payment_amount': float(response.payment_amount) if response.payment_amount else None,
            'payment_proof': response.payment_proof.url if response.payment_proof else None,
            'created_at': response.created_at.isoformat(),
            'updated_at': response.updated_at.isoformat(),
            'submitted_at': response.submitted_at.isoformat() if response.submitted_at else None,
            'form_data': response.response_data,
            'metadata': response.metadata,
        }
        
        # Add form schema for rendering
        data['form_schema'] = response.registration_form.form_schema
        
        return JsonResponse(data)


class QuickActionAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Quick actions on single response (approve, reject, verify payment).
    """
    
    def test_func(self):
        response = self.get_response()
        return (
            self.request.user == response.registration_form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_response(self):
        if not hasattr(self, '_response'):
            self._response = get_object_or_404(
                FormResponse.objects.select_related('registration_form__tournament'),
                id=self.kwargs['response_id']
            )
        return self._response
    
    def post(self, request, *args, **kwargs):
        response = self.get_response()
        action = request.POST.get('action')
        
        if action == 'approve':
            if response.status in ['draft', 'submitted']:
                response.status = 'approved'
                response.save()
                
                # Trigger webhook
                from apps.tournaments.models.webhooks import WebhookService
                WebhookService.on_response_approved(response)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Registration approved',
                    'new_status': response.get_status_display()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot approve registration in current status'
                }, status=400)
        
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            if response.status in ['draft', 'submitted', 'approved']:
                response.status = 'rejected'
                if reason:
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata['rejection_reason'] = reason
                response.save()
                
                # Trigger webhook
                from apps.tournaments.models.webhooks import WebhookService
                WebhookService.on_response_rejected(response, reason)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Registration rejected',
                    'new_status': response.get_status_display()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot reject registration in current status'
                }, status=400)
        
        elif action == 'verify_payment':
            if response.has_paid:
                response.payment_verified = True
                response.save()
                
                # Trigger webhook
                from apps.tournaments.models.webhooks import WebhookService
                WebhookService.on_payment_verified(response)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Payment verified'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Payment not marked as received'
                }, status=400)
        
        elif action == 'unverify_payment':
            response.payment_verified = False
            response.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment verification removed'
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown action: {action}'
            }, status=400)
