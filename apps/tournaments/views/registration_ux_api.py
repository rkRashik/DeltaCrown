"""
Registration UX API Views

API endpoints for auto-save, progress tracking, and field validation.
"""
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from apps.tournaments.models import TournamentRegistrationForm
from apps.tournaments.services.registration_ux import (
    RegistrationDraftService,
    RegistrationProgressService,
    FieldValidationService,
)


class SaveDraftAPIView(LoginRequiredMixin, View):
    """Auto-save registration draft"""
    
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        tournament_form = get_object_or_404(
            TournamentRegistrationForm,
            tournament__slug=self.kwargs['tournament_slug']
        )
        
        # Get form data from request
        import json
        try:
            form_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        
        # Check if should persist to DB
        persist_to_db = request.GET.get('persist', 'false').lower() == 'true'
        
        # Save draft
        draft_info = RegistrationDraftService.save_draft(
            user_id=request.user.id,
            tournament_form_id=tournament_form.id,
            form_data=form_data,
            persist_to_db=persist_to_db,
        )
        
        return JsonResponse({
            'success': True,
            'draft': draft_info,
        })


class GetDraftAPIView(LoginRequiredMixin, View):
    """Retrieve saved draft"""
    
    def get(self, request, *args, **kwargs):
        tournament_form = get_object_or_404(
            TournamentRegistrationForm,
            tournament__slug=self.kwargs['tournament_slug']
        )
        
        draft = RegistrationDraftService.get_draft(
            user_id=request.user.id,
            tournament_form_id=tournament_form.id,
        )
        
        if draft:
            return JsonResponse({
                'success': True,
                'draft': draft,
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No draft found'
            }, status=404)


class GetProgressAPIView(LoginRequiredMixin, View):
    """Get registration progress"""
    
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        tournament_form = get_object_or_404(
            TournamentRegistrationForm,
            tournament__slug=self.kwargs['tournament_slug']
        )
        
        # Get form data from request
        import json
        try:
            form_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        
        # Calculate progress
        progress = RegistrationProgressService.calculate_progress(
            tournament_form,
            form_data
        )
        
        return JsonResponse({
            'success': True,
            'progress': progress,
        })


class ValidateFieldAPIView(View):
    """Validate a single field in real-time"""
    
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        tournament_form = get_object_or_404(
            TournamentRegistrationForm,
            tournament__slug=self.kwargs['tournament_slug']
        )
        
        # Get field config and value
        import json
        try:
            data = json.loads(request.body)
            field_id = data.get('field_id')
            value = data.get('value')
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        
        if not field_id:
            return JsonResponse({
                'success': False,
                'error': 'field_id is required'
            }, status=400)
        
        # Find field config in form schema
        field_config = None
        for section in tournament_form.template.form_schema.get('sections', []):
            for field in section.get('fields', []):
                if field.get('id') == field_id:
                    field_config = field
                    break
            if field_config:
                break
        
        if not field_config:
            return JsonResponse({
                'success': False,
                'error': 'Field not found'
            }, status=404)
        
        # Validate field
        validation_result = FieldValidationService.validate_field(
            field_config,
            value
        )
        
        return JsonResponse({
            'success': True,
            'validation': validation_result,
        })
