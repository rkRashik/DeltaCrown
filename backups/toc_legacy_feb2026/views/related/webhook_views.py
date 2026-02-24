"""
Webhook Management Views

Admin interface for managing form webhooks.
"""
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views import View
from apps.tournaments.models import TournamentRegistrationForm
from apps.tournaments.models.webhooks import FormWebhook, WebhookDelivery


class WebhookListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all webhooks for a tournament form"""
    
    model = FormWebhook
    template_name = 'tournaments/webhooks/list.html'
    context_object_name = 'webhooks'
    paginate_by = 20
    
    def test_func(self):
        """Only tournament organizer can manage webhooks"""
        form = self.get_tournament_form()
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        if not hasattr(self, '_tournament_form'):
            self._tournament_form = get_object_or_404(
                TournamentRegistrationForm.objects.select_related('tournament'),
                tournament__slug=self.kwargs['tournament_slug']
            )
        return self._tournament_form
    
    def get_queryset(self):
        return FormWebhook.objects.filter(
            tournament_form=self.get_tournament_form()
        ).prefetch_related('deliveries')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tournament'] = self.get_tournament_form().tournament
        context['tournament_form'] = self.get_tournament_form()
        
        # Get recent deliveries for each webhook
        for webhook in context['webhooks']:
            webhook.recent_deliveries = webhook.deliveries.all()[:5]
        
        return context


class WebhookDeliveryHistoryView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View delivery history for a specific webhook"""
    
    model = WebhookDelivery
    template_name = 'tournaments/webhooks/delivery_history.html'
    context_object_name = 'deliveries'
    paginate_by = 50
    
    def test_func(self):
        webhook = self.get_webhook()
        return (
            self.request.user == webhook.tournament_form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_webhook(self):
        if not hasattr(self, '_webhook'):
            self._webhook = get_object_or_404(
                FormWebhook.objects.select_related('tournament_form__tournament'),
                id=self.kwargs['webhook_id']
            )
        return self._webhook
    
    def get_queryset(self):
        return WebhookDelivery.objects.filter(
            webhook=self.get_webhook()
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['webhook'] = self.get_webhook()
        context['tournament'] = self.get_webhook().tournament_form.tournament
        
        # Calculate success rate
        total = self.get_queryset().count()
        successful = self.get_queryset().filter(status='success').count()
        context['success_rate'] = (
            int((successful / total) * 100) if total > 0 else 0
        )
        context['total_deliveries'] = total
        context['successful_deliveries'] = successful
        
        return context


class TestWebhookView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Send a test webhook delivery"""
    
    def test_func(self):
        webhook = self.get_webhook()
        return (
            self.request.user == webhook.tournament_form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_webhook(self):
        return get_object_or_404(
            FormWebhook.objects.select_related('tournament_form__tournament'),
            id=self.kwargs['webhook_id']
        )
    
    def post(self, request, *args, **kwargs):
        webhook = self.get_webhook()
        
        # Send test event
        test_data = {
            'test': True,
            'tournament': {
                'id': webhook.tournament_form.tournament.id,
                'name': webhook.tournament_form.tournament.name,
            },
            'message': 'This is a test webhook delivery from DeltaCrown'
        }
        
        delivery = webhook.send('webhook.test', test_data)
        
        return JsonResponse({
            'success': delivery.status == 'success',
            'status': delivery.status,
            'status_code': delivery.status_code,
            'error': delivery.error_message if delivery.status == 'failed' else None,
        })
