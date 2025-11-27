"""
Dynamic Tournament Registration Views (Sprint 1 - Form Builder)
Uses FormRenderService to render multi-step registration forms
"""
from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse

from apps.tournaments.models import Tournament, TournamentRegistrationForm, FormResponse
from apps.tournaments.services.form_render_service import FormRenderService
from apps.tournaments.services.registration_autofill import RegistrationAutoFillService
from apps.tournaments.services.registration_eligibility import RegistrationEligibilityService


class DynamicRegistrationView(LoginRequiredMixin, View):
    """
    Dynamic registration view using FormRenderService
    Handles multi-step wizard, validation, and response submission
    """
    template_name = 'tournaments/form_builder/form_step.html'
    
    def get(self, request, tournament_slug):
        """Display registration form step"""
        tournament = get_object_or_404(Tournament, slug=tournament_slug)
        
        # Check eligibility first
        eligibility_result = RegistrationEligibilityService.check_eligibility(
            tournament, request.user
        )
        
        if not eligibility_result.is_eligible:
            # Render ineligibility page with glassmorphism UI
            context = {
                'tournament': tournament,
                'eligibility_result': eligibility_result
            }
            return render(request, 'tournaments/registration_ineligible.html', context)
        
        # Check if already registered
        existing_response = FormResponse.objects.filter(
            tournament=tournament,
            user=request.user,
            status__in=['submitted', 'approved']
        ).first()
        
        if existing_response:
            messages.info(request, "You have already registered for this tournament.")
            return redirect('tournaments:detail', slug=tournament_slug)
        
        # Get team if team tournament
        team = None
        if tournament.participation_type in ['team', 'both']:
            team_id = request.GET.get('team_id')
            if team_id:
                from apps.teams.models import Team
                team = Team.objects.filter(id=team_id).first()
        
        # Initialize form service
        form_service = FormRenderService(tournament)
        
        # Get auto-fill data
        autofill_data = RegistrationAutoFillService.get_autofill_data(
            user=request.user,
            tournament=tournament,
            team=team
        )
        
        # Calculate completion metrics
        completion_percentage = RegistrationAutoFillService.get_completion_percentage(autofill_data)
        missing_fields = RegistrationAutoFillService.get_missing_fields(autofill_data)
        update_prompts = RegistrationAutoFillService.get_update_prompts(autofill_data)
        
        # Track view (only first time)
        if 'registration_viewed' not in request.session:
            form_service.track_view()
            request.session['registration_viewed'] = True
        
        # Get current step
        step = int(request.GET.get('step', 1))
        total_steps = form_service._get_total_steps()
        
        # Validate step number
        if step < 1 or step > total_steps:
            step = 1
        
        # Get session data (from previous steps)
        session_key = f'registration_data_{tournament.id}'
        response_data = request.session.get(session_key, {})
        
        # Apply auto-fill data to response_data if empty
        if not response_data and step == 1:
            response_data = {}
            for field_name, field_data in autofill_data.items():
                if not field_data.missing and field_data.value:
                    response_data[field_name] = field_data.value
            request.session[session_key] = response_data
        
        # Track start (first step only)
        if step == 1 and not response_data:
            form_service.track_start()
        
        # Render form for current step
        form_html = form_service.render_form(step=step, response_data=response_data)
        
        context = {
            'tournament': tournament,
            'form_html': form_html,
            'step': step,
            'total_steps': total_steps,
            'progress_percentage': int((step / total_steps) * 100),
            'enable_autosave': form_service.form_config.enable_autosave,
            'form_title': f"Step {step}" if total_steps > 1 else "Registration Form",
            # Auto-fill context
            'autofill_data': autofill_data,
            'completion_percentage': completion_percentage,
            'missing_count': len(missing_fields),
            'update_prompts': update_prompts,
            'team': team
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, tournament_slug):
        """Handle form submission (step validation or final submission)"""
        tournament = get_object_or_404(Tournament, slug=tournament_slug)
        form_service = FormRenderService(tournament)
        
        # Get current step
        step = int(request.POST.get('step', request.GET.get('step', 1)))
        total_steps = form_service._get_total_steps()
        
        # Get session data
        session_key = f'registration_data_{tournament.id}'
        response_data = request.session.get(session_key, {})
        
        # Update response data with current step data
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'step', 'save_draft']:
                response_data[key] = value
        
        # Handle file uploads
        for key, file in request.FILES.items():
            # Save file and store path in response_data
            # TODO: Implement file upload handling with S3
            response_data[key] = file.name
        
        # Check if draft save
        if request.POST.get('save_draft'):
            # Save draft
            draft_response = form_service.save_draft(
                user=request.user,
                response_data=response_data,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Draft saved'})
            
            messages.success(request, "Draft saved successfully!")
            request.session[session_key] = response_data
            return redirect(f"{reverse('tournaments:register', args=[tournament_slug])}?step={step}")
        
        # Validate current step
        is_valid, errors = form_service.validate_step(step, response_data)
        
        if not is_valid:
            # Re-render form with errors
            form_html = form_service.render_form(step=step, response_data=response_data, errors=errors)
            
            context = {
                'tournament': tournament,
                'form_html': form_html,
                'step': step,
                'total_steps': total_steps,
                'progress_percentage': int((step / total_steps) * 100),
                'enable_autosave': form_service.form_config.enable_autosave,
                'form_title': f"Step {step}" if total_steps > 1 else "Registration Form",
                'errors': errors
            }
            
            return render(request, self.template_name, context)
        
        # Save to session
        request.session[session_key] = response_data
        
        # If not final step, go to next step
        if step < total_steps:
            next_step = step + 1
            return redirect(f"{reverse('tournaments:register', args=[tournament_slug])}?step={next_step}")
        
        # Final step - validate complete form and save
        is_valid, errors = form_service.validate_complete_form(response_data)
        
        if not is_valid:
            # Re-render final step with errors
            form_html = form_service.render_form(step=step, response_data=response_data, errors=errors)
            
            context = {
                'tournament': tournament,
                'form_html': form_html,
                'step': step,
                'total_steps': total_steps,
                'progress_percentage': 100,
                'enable_autosave': form_service.form_config.enable_autosave,
                'form_title': f"Step {step}" if total_steps > 1 else "Registration Form",
                'errors': errors
            }
            
            return render(request, self.template_name, context)
        
        # Save final response
        try:
            with transaction.atomic():
                form_response = form_service.save_response(
                    user=request.user,
                    response_data=response_data,
                    status='submitted',
                    team=None,  # TODO: Handle team registration
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
                
                # Mark as submitted
                form_response.mark_as_submitted()
                
                # Clear session data
                if session_key in request.session:
                    del request.session[session_key]
                if 'registration_viewed' in request.session:
                    del request.session['registration_viewed']
                
                messages.success(request, "Registration submitted successfully!")
                return redirect('tournaments:registration_success', 
                              tournament_slug=tournament_slug, 
                              response_id=form_response.id)
        
        except Exception as e:
            messages.error(request, f"Error submitting registration: {str(e)}")
            return redirect('tournaments:register', tournament_slug=tournament_slug)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RegistrationSuccessView(LoginRequiredMixin, View):
    """Success page after registration submission"""
    template_name = 'tournaments/form_builder/registration_success.html'
    
    def get(self, request, tournament_slug, response_id):
        """Display success page"""
        tournament = get_object_or_404(Tournament, slug=tournament_slug)
        form_response = get_object_or_404(
            FormResponse,
            id=response_id,
            tournament=tournament,
            user=request.user
        )
        
        context = {
            'tournament': tournament,
            'form_response': form_response,
            'requires_payment': tournament.entry_fee_amount > 0,
            'requires_approval': form_response.status in ['submitted', 'under_review']
        }
        
        return render(request, self.template_name, context)


class RegistrationDashboardView(LoginRequiredMixin, View):
    """View user's registration history"""
    template_name = 'tournaments/form_builder/registration_dashboard.html'
    
    def get(self, request):
        """Display user's registrations"""
        registrations = FormResponse.objects.filter(
            user=request.user
        ).select_related('tournament').order_by('-created_at')
        
        context = {
            'registrations': registrations,
            'draft_count': registrations.filter(status='draft').count(),
            'submitted_count': registrations.filter(status='submitted').count(),
            'approved_count': registrations.filter(status='approved').count()
        }
        
        return render(request, self.template_name, context)
