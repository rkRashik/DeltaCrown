"""
Tournament Registration Views
FE-T-004: Multi-Step Registration Wizard

Implements tournament registration workflow:
- Step 1: Eligibility check
- Step 2: Team selection (for team tournaments)
- Step 3: Custom fields
- Step 4: Payment (if has_entry_fee)
- Step 5: Review & confirm

Sprint 1 Implementation - November 15, 2025
Source: FRONTEND_TOURNAMENT_BACKLOG.md Section 1.4
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.registration_service import RegistrationService
from apps.teams.models import Team, TeamMembership


class TournamentRegistrationView(LoginRequiredMixin, View):
    """
    FE-T-004: Tournament Registration Wizard
    
    Multi-step form handling tournament registration.
    Steps adapt based on tournament configuration:
    - Team vs Solo
    - Custom fields
    - Payment required
    
    Session-based wizard state management.
    """
    
    template_name = 'tournaments/public/registration/wizard.html'
    
    def get(self, request, slug):
        """Render registration wizard with current step."""
        tournament = get_object_or_404(Tournament, slug=slug)
        user = request.user
        
        # Check if user is already registered
        if Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).exists():
            messages.info(request, "You're already registered for this tournament.")
            return redirect('tournaments:detail', slug=slug)
        
        # Get or initialize wizard state from session
        wizard_key = f'registration_wizard_{tournament.id}'
        wizard_data = request.session.get(wizard_key, {})
        
        # Determine current step (default: 1)
        current_step = int(request.GET.get('step', wizard_data.get('current_step', 1)))
        
        # Validate step sequence (can't skip ahead)
        max_completed_step = wizard_data.get('max_completed_step', 0)
        if current_step > max_completed_step + 1:
            current_step = max_completed_step + 1
        
        # Get step-specific context
        context = self._get_step_context(tournament, user, current_step, wizard_data)
        
        # Add common context
        context.update({
            'tournament': tournament,
            'current_step': current_step,
            'total_steps': self._calculate_total_steps(tournament),
            'wizard_data': wizard_data,
        })
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug):
        """Process step submission and advance wizard."""
        tournament = get_object_or_404(Tournament, slug=slug)
        user = request.user
        
        wizard_key = f'registration_wizard_{tournament.id}'
        wizard_data = request.session.get(wizard_key, {})
        
        current_step = int(request.POST.get('current_step', 1))
        action = request.POST.get('action', 'next')
        
        if action == 'back':
            # Go back one step - render previous step directly
            next_step = max(1, current_step - 1)
            wizard_data['current_step'] = next_step
            request.session[wizard_key] = wizard_data
            request.session.modified = True
            
            context = self._get_step_context(tournament, user, next_step, wizard_data)
            context.update({
                'tournament': tournament,
                'current_step': next_step,
                'total_steps': self._calculate_total_steps(tournament),
                'wizard_data': wizard_data,
            })
            return render(request, self.template_name, context)
        
        elif action == 'cancel':
            # Clear wizard data and return to tournament detail
            if wizard_key in request.session:
                del request.session[wizard_key]
            messages.info(request, "Registration cancelled.")
            return redirect('tournaments:detail', slug=slug)
        
        elif action == 'next' or action == 'submit':
            # Validate current step
            validation_result = self._validate_step(tournament, user, current_step, request.POST, wizard_data)
            
            if not validation_result['valid']:
                # Re-render current step with errors
                context = self._get_step_context(tournament, user, current_step, wizard_data)
                context.update({
                    'tournament': tournament,
                    'current_step': current_step,
                    'total_steps': self._calculate_total_steps(tournament),
                    'wizard_data': wizard_data,
                    'errors': validation_result['errors'],
                })
                return render(request, self.template_name, context)
            
            # Save step data to session
            wizard_data.update(validation_result['data'])
            wizard_data['current_step'] = current_step
            wizard_data['max_completed_step'] = max(
                wizard_data.get('max_completed_step', 0),
                current_step
            )
            request.session[wizard_key] = wizard_data
            request.session.modified = True
            
            # Determine next action
            total_steps = self._calculate_total_steps(tournament)
            
            if action == 'submit' or current_step >= total_steps:
                # Final step: submit registration
                return self._submit_registration(request, tournament, user, wizard_data)
            else:
                # Advance to next step and render it (no redirect - stay in POST flow)
                next_step = current_step + 1
                wizard_data['current_step'] = next_step
                request.session[wizard_key] = wizard_data
                request.session.modified = True
                
                # Render next step directly with 200 status
                context = self._get_step_context(tournament, user, next_step, wizard_data)
                context.update({
                    'tournament': tournament,
                    'current_step': next_step,
                    'total_steps': total_steps,
                    'wizard_data': wizard_data,
                })
                return render(request, self.template_name, context)
        
        # Default: stay on current step
        return redirect(f"{reverse('tournaments:register', kwargs={'slug': slug})}?step={current_step}")
    
    def _calculate_total_steps(self, tournament):
        """Calculate total wizard steps based on tournament configuration."""
        steps = 1  # Step 1: Eligibility (always shown)
        
        if tournament.participation_type == 'team':
            steps += 1  # Step 2: Team selection
        
        # Step 3: Custom fields (check if tournament has custom fields)
        # NOTE: This will be dynamic once custom_fields JSONField is populated
        # For now, we'll always show this step if tournament has entry requirements
        steps += 1  # Custom fields step
        
        if tournament.has_entry_fee:
            steps += 1  # Step 4: Payment
        
        steps += 1  # Final step: Review & Confirm
        
        return steps
    
    def _get_step_context(self, tournament, user, step, wizard_data):
        """Get context data for specific wizard step."""
        context = {}
        
        if step == 1:
            # Step 1: Eligibility check
            context['step_title'] = 'Eligibility Check'
            context['step_description'] = 'Verifying your eligibility for this tournament'
            
            # Run eligibility check
            try:
                RegistrationService.check_eligibility(
                    tournament=tournament,
                    user=user,
                    team_id=None  # Will be selected in next step if needed
                )
                context['eligible'] = True
                context['eligibility_message'] = 'You meet all requirements for this tournament.'
            except Exception as e:
                context['eligible'] = False
                context['eligibility_message'] = str(e)
        
        elif step == 2 and tournament.participation_type == 'team':
            # Step 2: Team selection
            context['step_title'] = 'Select Your Team'
            context['step_description'] = 'Choose which team to register for this tournament'
            
            # Get teams user has permission to register
            eligible_teams = Team.objects.filter(
                memberships__user=user,
                is_deleted=False
            ).filter(
                # User must be owner, manager, or have explicit permission
                memberships__user=user,
                memberships__is_deleted=False
            ).distinct()
            
            # Annotate with permission level
            teams_with_permissions = []
            for team in eligible_teams:
                membership = TeamMembership.objects.get(team=team, user=user, is_deleted=False)
                permission_label = 'Owner' if team.owner == user else membership.role.title()
                can_register = (
                    team.owner == user or
                    membership.role in ['manager', 'captain'] or
                    membership.can_register_tournaments
                )
                
                if can_register:
                    teams_with_permissions.append({
                        'team': team,
                        'permission_label': permission_label,
                        'can_register': True,
                    })
            
            context['eligible_teams'] = teams_with_permissions
            context['selected_team_id'] = wizard_data.get('team_id')
        
        elif step == 3 or (step == 2 and tournament.participation_type == 'solo'):
            # Step 3: Custom fields
            context['step_title'] = 'Additional Information'
            context['step_description'] = 'Please provide the following details'
            
            # TODO: Load dynamic custom fields from tournament.custom_fields JSONField
            # For now, show placeholder in-game ID field
            from apps.common.game_registry import get_game, normalize_slug
            canonical_slug = normalize_slug(tournament.game.slug)
            game_spec = get_game(canonical_slug)
            game_display_name = game_spec.display_name if game_spec else tournament.game.name
            custom_field_values = wizard_data.get('custom_fields', {})
            context['custom_fields'] = [
                {
                    'name': 'in_game_id',
                    'label': f'{game_display_name} In-Game ID',
                    'type': 'text',
                    'required': True,
                    'help_text': 'Your player ID or username in the game',
                    'current_value': custom_field_values.get('in_game_id', ''),
                }
            ]
        
        elif tournament.has_entry_fee:
            # Step 4: Payment (conditional)
            context['step_title'] = 'Payment Information'
            context['step_description'] = f'Entry fee: ৳{tournament.entry_fee_amount}'
            
            # Load configured payment methods from tournament
            from apps.tournaments.models import TournamentPaymentMethod
            configured_methods = TournamentPaymentMethod.objects.filter(
                tournament=tournament,
                is_active=True
            ).order_by('display_order')
            
            payment_methods = []
            for method in configured_methods:
                method_info = {
                    'value': method.method_type,
                    'label': method.get_method_type_display(),
                    'logo': None,  # Logo paths can be added to model later
                }
                
                # Add account details and instructions
                if method.method_type == 'bkash':
                    method_info['account'] = method.bkash_account_number
                    method_info['instructions'] = method.bkash_instructions or 'Send Money to the number above'
                elif method.method_type == 'nagad':
                    method_info['account'] = method.nagad_account_number
                    method_info['instructions'] = method.nagad_instructions or 'Send Money to the number above'
                elif method.method_type == 'rocket':
                    method_info['account'] = method.rocket_account_number
                    method_info['instructions'] = method.rocket_instructions or 'Send Money to the number above'
                elif method.method_type == 'bank_transfer':
                    method_info['account'] = f"{method.bank_name} - {method.bank_account_number}"
                    method_info['instructions'] = method.bank_instructions or 'Transfer to the account above'
                
                payment_methods.append(method_info)
            
            # Fallback if no methods configured
            if not payment_methods:
                payment_methods = [
                    {'value': 'bkash', 'label': 'bKash', 'logo': 'img/payment/bkash.png', 'account': 'Contact organizer', 'instructions': 'Please contact tournament organizer for payment details'},
                ]
            
            context['payment_methods'] = payment_methods
            context['selected_payment_method'] = wizard_data.get('payment_method')
        
        # Final step: Review & Confirm
        if step == self._calculate_total_steps(tournament):
            context['step_title'] = 'Review & Confirm'
            context['step_description'] = 'Please review your registration details'
            context['is_final_step'] = True
            
            # Build summary
            from apps.common.game_registry import get_game, normalize_slug
            canonical_slug = normalize_slug(tournament.game.slug)
            game_spec = get_game(canonical_slug)
            game_display_name = game_spec.display_name if game_spec else tournament.game.name
            context['summary'] = {
                'tournament_name': tournament.name,
                'game': game_display_name,
                'format': tournament.get_format_display(),
                'entry_fee': tournament.entry_fee_amount if tournament.has_entry_fee else 0,
                'team': wizard_data.get('team_name') if tournament.participation_type == 'team' else None,
                'custom_fields': wizard_data.get('custom_fields', {}),
                'payment_method': wizard_data.get('payment_method'),
            }
        
        return context
    
    def _validate_step(self, tournament, user, step, post_data, wizard_data):
        """Validate step data before advancing."""
        result = {'valid': True, 'errors': {}, 'data': {}}
        
        if step == 1:
            # Step 1: Eligibility check (no user input, auto-validated)
            pass
        
        elif step == 2 and tournament.participation_type == 'team':
            # Step 2: Team selection
            team_id = post_data.get('team_id')
            if not team_id:
                result['valid'] = False
                result['errors']['team_id'] = 'Please select a team'
            else:
                try:
                    team = Team.objects.get(id=team_id, is_deleted=False)
                    # Verify user has permission
                    membership = TeamMembership.objects.get(team=team, user=user, is_deleted=False)
                    can_register = (
                        team.owner == user or
                        membership.role in ['manager', 'captain'] or
                        membership.can_register_tournaments
                    )
                    
                    if not can_register:
                        result['valid'] = False
                        result['errors']['team_id'] = 'You don\'t have permission to register this team'
                    else:
                        result['data']['team_id'] = team_id
                        result['data']['team_name'] = team.name
                except Team.DoesNotExist:
                    result['valid'] = False
                    result['errors']['team_id'] = 'Invalid team selected'
        
        # Custom fields step (step number depends on tournament type)
        # For SOLO: step 2, for TEAM: step 3
        custom_fields_step = 2 if tournament.participation_type == 'solo' else 3
        if step == custom_fields_step:
            # Custom fields validation
            custom_fields = {}
            in_game_id = post_data.get('in_game_id', '').strip()
            
            if not in_game_id:
                result['valid'] = False
                result['errors']['in_game_id'] = 'In-game ID is required'
            else:
                custom_fields['in_game_id'] = in_game_id
            
            result['data']['custom_fields'] = custom_fields
        
        # Payment step (only if has_entry_fee, comes after custom fields)
        if tournament.has_entry_fee and step == custom_fields_step + 1:
            # Payment method selection
            payment_method = post_data.get('payment_method')
            if not payment_method:
                result['valid'] = False
                result['errors']['payment_method'] = 'Please select a payment method'
            else:
                result['data']['payment_method'] = payment_method
        
        # Final step: Review & confirm (always the last step)
        if step == self._calculate_total_steps(tournament):
            agreed = post_data.get('agree_terms')
            # 'on' or '1' or 'true' or True are all valid checkbox values
            if not agreed or agreed == 'false':
                result['valid'] = False
                result['errors']['agree_terms'] = 'You must agree to the tournament rules'
        
        return result
    
    def _submit_registration(self, request, tournament, user, wizard_data):
        """Submit final registration to backend using RegistrationService."""
        try:
            # Build registration data for service
            registration_data = {
                'custom_fields': wizard_data.get('custom_fields', {}),
            }
            
            # Use RegistrationService.register_participant() instead of direct model creation
            # This ensures all backend validation, business rules, and audit logging are applied
            registration = RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                team_id=wizard_data.get('team_id') if tournament.participation_type == 'team' else None,
                registration_data=registration_data
            )
            
            # Clear wizard session data
            wizard_key = f'registration_wizard_{tournament.id}'
            if wizard_key in request.session:
                del request.session[wizard_key]
            
            # Handle payment redirect if needed
            if tournament.has_entry_fee:
                messages.success(request, "Registration submitted! Please complete payment.")
                # TODO: Redirect to payment gateway (Module 3.1)
                # Payment integration will be completed in future sprint
                return redirect('tournaments:register_success', slug=tournament.slug)
            else:
                messages.success(request, "You're registered! Good luck in the tournament!")
                return redirect('tournaments:register_success', slug=tournament.slug)
        
        except ValidationError as e:
            # RegistrationService raises ValidationError for business rule violations
            messages.error(request, f"Registration failed: {str(e)}")
            return redirect('tournaments:register', slug=tournament.slug)
        except Exception as e:
            # Catch unexpected errors
            messages.error(request, f"Registration failed: {str(e)}")
            return redirect('tournaments:register', slug=tournament.slug)


class TournamentRegistrationSuccessView(LoginRequiredMixin, View):
    """
    FE-T-004: Registration Success Page
    
    Shown after successful registration.
    """
    
    template_name = 'tournaments/public/registration/success.html'
    
    def get(self, request, slug):
        """Render success confirmation."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Verify user has a registration
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=request.user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            messages.warning(request, "No registration found for this tournament.")
            return redirect('tournaments:detail', slug=slug)
        
        context = {
            'tournament': tournament,
            'registration': registration,
        }
        
        return render(request, self.template_name, context)
