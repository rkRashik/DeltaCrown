"""
Bulk Operations Views

Views for performing bulk actions on form responses.
"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from apps.tournaments.models import TournamentRegistrationForm
from apps.tournaments.services.bulk_operations import BulkResponseService


class BulkActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Perform bulk actions on form responses.
    
    Actions: approve, reject, delete, verify_payment, send_notification
    """
    
    def test_func(self):
        """Only allow tournament organizer"""
        form = self.get_tournament_form()
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        return get_object_or_404(
            TournamentRegistrationForm.objects.select_related('tournament'),
            tournament__slug=self.kwargs['tournament_slug']
        )
    
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        tournament_form = self.get_tournament_form()
        bulk_service = BulkResponseService(tournament_form)
        
        # Get action and response IDs
        action = request.POST.get('action')
        response_ids = request.POST.getlist('response_ids[]')
        
        if not response_ids:
            return JsonResponse({
                'success': False,
                'error': 'No responses selected'
            }, status=400)
        
        # Convert to integers
        try:
            response_ids = [int(id) for id in response_ids]
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid response IDs'
            }, status=400)
        
        # Execute action
        if action == 'approve':
            send_email = request.POST.get('send_email', 'true').lower() == 'true'
            custom_message = request.POST.get('custom_message')
            
            result = bulk_service.bulk_approve(
                response_ids,
                send_email=send_email,
                custom_message=custom_message
            )
            
            return JsonResponse({
                'success': True,
                'action': 'approve',
                'result': result
            })
        
        elif action == 'reject':
            send_email = request.POST.get('send_email', 'true').lower() == 'true'
            reason = request.POST.get('reason')
            
            result = bulk_service.bulk_reject(
                response_ids,
                reason=reason,
                send_email=send_email
            )
            
            return JsonResponse({
                'success': True,
                'action': 'reject',
                'result': result
            })
        
        elif action == 'delete':
            result = bulk_service.bulk_delete(response_ids)
            
            return JsonResponse({
                'success': True,
                'action': 'delete',
                'result': result
            })
        
        elif action == 'verify_payment':
            send_email = request.POST.get('send_email', 'true').lower() == 'true'
            verified = request.POST.get('verified', 'true').lower() == 'true'
            
            result = bulk_service.bulk_verify_payment(
                response_ids,
                verified=verified,
                send_email=send_email
            )
            
            return JsonResponse({
                'success': True,
                'action': 'verify_payment',
                'result': result
            })
        
        elif action == 'send_notification':
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            status_filter = request.POST.getlist('status_filter[]')
            
            if not subject or not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Subject and message are required'
                }, status=400)
            
            result = bulk_service.send_bulk_notification(
                response_ids,
                subject=subject,
                message=message,
                status_filter=status_filter if status_filter else None
            )
            
            return JsonResponse({
                'success': True,
                'action': 'send_notification',
                'result': result
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown action: {action}'
            }, status=400)


class BulkActionPreviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Preview the impact of a bulk action before executing.
    """
    
    def test_func(self):
        """Only allow tournament organizer"""
        form = self.get_tournament_form()
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        return get_object_or_404(
            TournamentRegistrationForm.objects.select_related('tournament'),
            tournament__slug=self.kwargs['tournament_slug']
        )
    
    def post(self, request, *args, **kwargs):
        tournament_form = self.get_tournament_form()
        bulk_service = BulkResponseService(tournament_form)
        
        # Get action and response IDs
        action = request.POST.get('action')
        response_ids = request.POST.getlist('response_ids[]')
        
        if not response_ids:
            return JsonResponse({
                'success': False,
                'error': 'No responses selected'
            }, status=400)
        
        # Convert to integers
        try:
            response_ids = [int(id) for id in response_ids]
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid response IDs'
            }, status=400)
        
        # Get preview
        preview = bulk_service.get_bulk_action_preview(response_ids, action)
        
        return JsonResponse({
            'success': True,
            'preview': preview
        })
