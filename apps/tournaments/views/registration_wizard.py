"""
Classic Registration Wizard - Production Implementation

5-Step Registration Flow:
1. Eligibility Check
2. Team/Solo Selection  
3. Basic Info (auto-filled from profile)
4. Custom Fields
5. Review & Submit

Wires beautiful demo templates (solo_step*.html, team_step*.html) to actual Registration model.

Source Documents:
- Documents/Planning/REGISTRATION_SYSTEM_PLANNING.md (Section 3: Step-by-Step Registration Flow)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (UI/UX Flows)
- Documents/MyAudit/Registation/GAP_ANALYSIS.md (Gap #2: Multi-Step Wizard)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from apps.tournaments.models import Tournament, Registration, Payment
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.payment_service import PaymentService


class RegistrationWizardView(LoginRequiredMixin, View):
    """
    3-Step Registration Wizard (Simplified from 5 steps)
    
    Solo Flow:
      Step 1: Player Info (auto-filled from profile)
      Step 2: Review & Terms
      Step 3: Payment Submission
      
    Team Flow:
      Step 1: Team Info + Captain Details
      Step 2: Review & Agreements
      Step 3: Payment Submission
    """
    
    def get_session_key(self, tournament_id, registration_type):
        """Get session key for wizard data"""
        return f'registration_wizard_{tournament_id}_{registration_type}'
    
    def get_wizard_data(self, request, tournament_id, registration_type):
        """Retrieve wizard data from session"""
        key = self.get_session_key(tournament_id, registration_type)
        return request.session.get(key, {})
    
    def save_wizard_data(self, request, tournament_id, registration_type, data):
        """Save wizard data to session"""
        key = self.get_session_key(tournament_id, registration_type)
        request.session[key] = data
        request.session.modified = True
    
    def clear_wizard_data(self, request, tournament_id, registration_type):
        """Clear wizard data from session"""
        key = self.get_session_key(tournament_id, registration_type)
        if key in request.session:
            del request.session[key]
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # ===== AUTHENTICATION CHECK =====
        if not request.user.is_authenticated:
            return render(request, 'tournaments/registration/errors/login_required.html', {
                'tournament': tournament,
            })
        
        # Determine registration type (solo or team)
        registration_type = request.GET.get('type', '')
        
        # Auto-detect registration type if not specified
        if not registration_type:
            if tournament.participation_type == Tournament.TEAM:
                registration_type = 'team'
            else:
                registration_type = 'solo'
        
        if registration_type not in ['solo', 'team']:
            registration_type = 'solo'
        
        # ===== TEAM TOURNAMENT CHECKS =====
        if registration_type == 'team' or tournament.participation_type == Tournament.TEAM:
            # Check if user is in a team
            user_teams = self._get_user_teams(request.user)
            
            if not user_teams:
                # User not in any team
                return render(request, 'tournaments/registration/errors/team_required.html', {
                    'tournament': tournament,
                })
            
            # Check if user has permission to register for tournaments
            can_register, team, user_role = self._check_tournament_registration_permission(request.user, tournament)
            
            if not can_register:
                # User doesn't have permission
                team_leaders = self._get_team_leaders(team)
                
                return render(request, 'tournaments/registration/errors/permission_required.html', {
                    'tournament': tournament,
                    'team': team,
                    'user_role': user_role,
                    'can_register': False,
                    'team_leaders': team_leaders,
                    'permission_request_sent': self._check_permission_request_sent(request.user, tournament, team),
                })
        
        # Redirect to correct view based on type
        if registration_type == 'solo':
            return self._handle_solo_registration_get(request, tournament)
        else:
            return self._handle_team_registration_get(request, tournament)
    
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Determine registration type
        registration_type = request.POST.get('type', 'solo')
        if registration_type not in ['solo', 'team']:
            registration_type = 'solo'
        
        # Route to correct handler
        if registration_type == 'solo':
            return self._handle_solo_registration_post(request, tournament)
        else:
            return self._handle_team_registration_post(request, tournament)
    
    # ===== SOLO REGISTRATION HANDLERS =====
    
    def _handle_solo_registration_get(self, request, tournament):
        """Handle GET requests for solo registration"""
        step = request.GET.get('step', '1')
        
        if step not in ['1', '2', '3']:
            step = '1'
        
        # Get wizard data
        wizard_data = self.get_wizard_data(request, tournament.id, 'solo')
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
            'registration_type': 'solo',
        }
        
        if step == '1':
            # Step 1: Player Information (Auto-filled)
            context['step_title'] = 'Player Information'
            context['step_description'] = 'Tell us about yourself'
            
            # Auto-fill from user profile if not already in session
            if not wizard_data:
                try:
                    auto_filled = self._auto_fill_solo_data(request.user, tournament)
                    wizard_data = auto_filled
                    self.save_wizard_data(request, tournament.id, 'solo', wizard_data)
                except Exception as e:
                    messages.warning(request, f"Could not auto-fill profile data: {e}")
                    wizard_data = {}
            
            context['player_data'] = wizard_data
            template = 'tournaments/registration_demo/solo_step1.html'
            
        elif step == '2':
            # Step 2: Review & Accept Terms
            context['step_title'] = 'Review & Accept Terms'
            context['step_description'] = 'Confirm your details'
            context['step_data'] = wizard_data
            template = 'tournaments/registration_demo/solo_step2.html'
            
        elif step == '3':
            # Step 3: Payment
            context['step_title'] = 'Payment'
            context['step_description'] = 'Complete your registration'
            context['entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else Decimal('0.00')
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            context['payment_methods'] = ['bkash', 'nagad', 'rocket']
            
            # Add DeltaCoin balance and affordability check
            if tournament.has_entry_fee:
                entry_fee = int(tournament.entry_fee_amount)
                deltacoin_check = PaymentService.can_use_deltacoin(request.user, entry_fee)
                
                context['deltacoin_balance'] = deltacoin_check['balance']
                context['deltacoin_can_afford'] = deltacoin_check['can_afford']
                context['deltacoin_shortfall'] = deltacoin_check['shortfall']
                
                # Add DeltaCoin to payment methods
                context['payment_methods'].append('deltacoin')
            
            template = 'tournaments/registration_demo/solo_step3.html'
        
        return render(request, template, context)
    
    def _handle_solo_registration_post(self, request, tournament):
        """Handle POST requests for solo registration"""
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Save player info
            player_data = {
                'full_name': request.POST.get('full_name', ''),
                'display_name': request.POST.get('display_name', ''),
                'age': request.POST.get('age', ''),
                'country': request.POST.get('country', ''),
                'riot_id': request.POST.get('riot_id', ''),
                'platform_server': request.POST.get('platform_server', ''),
                'rank': request.POST.get('rank', ''),
                'email': request.POST.get('email', ''),
                'phone': request.POST.get('phone', ''),
                'discord': request.POST.get('discord', ''),
                'preferred_contact': request.POST.get('preferred_contact', 'email'),
            }
            self.save_wizard_data(request, tournament.id, 'solo', player_data)
            return redirect(f'{request.path}?type=solo&step=2')
        
        elif step == '2':
            # Step 2: Terms accepted, proceed to payment
            terms_accepted = request.POST.get('accept_terms') == 'on'
            if not terms_accepted:
                messages.error(request, 'You must accept the terms and conditions to proceed.')
                return redirect(f'{request.path}?type=solo&step=2')
            
            # Save terms acceptance
            wizard_data = self.get_wizard_data(request, tournament.id, 'solo')
            wizard_data['terms_accepted'] = True
            wizard_data['terms_accepted_at'] = timezone.now().isoformat()
            self.save_wizard_data(request, tournament.id, 'solo', wizard_data)
            
            return redirect(f'{request.path}?type=solo&step=3')
        
        elif step == '3':
            # Step 3: Submit payment and create registration
            try:
                return self._process_solo_registration(request, tournament)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect(f'{request.path}?type=solo&step=3')
        
        return redirect(f'{request.path}?type=solo&step=1')
    
    # ===== TEAM REGISTRATION HANDLERS =====
    
    def _handle_team_registration_get(self, request, tournament):
        """Handle GET requests for team registration"""
        step = request.GET.get('step', '1')
        
        if step not in ['1', '2', '3']:
            step = '1'
        
        wizard_data = self.get_wizard_data(request, tournament.id, 'team')
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
            'registration_type': 'team',
        }
        
        if step == '1':
            context['step_title'] = 'Team Information'
            context['step_description'] = 'Enter your team details'
            context['team_data'] = wizard_data
            template = 'tournaments/registration_demo/team_step1.html'
            
        elif step == '2':
            context['step_title'] = 'Review & Agreements'
            context['step_description'] = 'Confirm team roster'
            context['step_data'] = wizard_data
            template = 'tournaments/registration_demo/team_step2.html'
            
        elif step == '3':
            context['step_title'] = 'Team Payment'
            context['step_description'] = 'Complete team registration'
            context['team_entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else Decimal('0.00')
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            context['payment_methods'] = ['bkash', 'nagad', 'rocket']
            
            # Add DeltaCoin balance and affordability check
            if tournament.has_entry_fee:
                entry_fee = int(tournament.entry_fee_amount)
                deltacoin_check = PaymentService.can_use_deltacoin(request.user, entry_fee)
                
                context['deltacoin_balance'] = deltacoin_check['balance']
                context['deltacoin_can_afford'] = deltacoin_check['can_afford']
                context['deltacoin_shortfall'] = deltacoin_check['shortfall']
                
                # Add DeltaCoin to payment methods
                context['payment_methods'].append('deltacoin')
            
            template = 'tournaments/registration_demo/team_step3.html'
        
        return render(request, template, context)
    
    def _handle_team_registration_post(self, request, tournament):
        """Handle POST requests for team registration"""
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Save team info
            team_data = {
                'team_name': request.POST.get('team_name', ''),
                'team_tag': request.POST.get('team_tag', ''),
                'captain_name': request.POST.get('captain_name', ''),
                'captain_game_id': request.POST.get('captain_game_id', ''),
                'captain_email': request.POST.get('captain_email', ''),
                'captain_phone': request.POST.get('captain_phone', ''),
                'captain_discord': request.POST.get('captain_discord', ''),
            }
            self.save_wizard_data(request, tournament.id, 'team', team_data)
            return redirect(f'{request.path}?type=team&step=2')
        
        elif step == '2':
            # Step 2: Terms & roster agreement
            terms_accepted = request.POST.get('accept_terms') == 'on'
            if not terms_accepted:
                messages.error(request, 'You must accept the terms and conditions to proceed.')
                return redirect(f'{request.path}?type=team&step=2')
            
            wizard_data = self.get_wizard_data(request, tournament.id, 'team')
            wizard_data['terms_accepted'] = True
            wizard_data['terms_accepted_at'] = timezone.now().isoformat()
            self.save_wizard_data(request, tournament.id, 'team', wizard_data)
            
            return redirect(f'{request.path}?type=team&step=3')
        
        elif step == '3':
            # Step 3: Submit payment and create team registration
            try:
                return self._process_team_registration(request, tournament)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect(f'{request.path}?type=team&step=3')
        
        return redirect(f'{request.path}?type=team&step=1')
    
    # ===== HELPER METHODS =====
    
    def _auto_fill_solo_data(self, user, tournament):
        """Auto-fill solo registration data from user profile"""
        auto_filled = {
            'full_name': user.get_full_name() or '',
            'display_name': user.username,
            'email': user.email,
        }
        
        # Try to get UserProfile data
        try:
            from apps.user_profile.models import UserProfile
            profile = UserProfile.objects.get(user=user)
            
            auto_filled.update({
                'phone': profile.phone or '',
                'country': profile.country or '',
                'discord': profile.discord_username or '',
                'riot_id': profile.riot_id or '',
                'pubg_mobile_id': profile.pubg_mobile_id or '',
                'mobile_legends_id': profile.mobile_legends_id or '',
                'free_fire_id': profile.free_fire_id or '',
                'cod_mobile_id': profile.cod_mobile_id or '',
                'valorant_id': profile.valorant_id or '',
            })
            
            # Map game-specific ID based on tournament game
            game_slug = tournament.game.slug if tournament.game else ''
            if game_slug == 'valorant':
                auto_filled['riot_id'] = profile.valorant_id or profile.riot_id or ''
            elif game_slug == 'pubg-mobile':
                auto_filled['riot_id'] = profile.pubg_mobile_id or ''
            elif game_slug == 'mobile-legends':
                auto_filled['riot_id'] = profile.mobile_legends_id or ''
            elif game_slug == 'free-fire':
                auto_filled['riot_id'] = profile.free_fire_id or ''
            elif game_slug == 'cod-mobile':
                auto_filled['riot_id'] = profile.cod_mobile_id or ''
                
        except Exception:
            # UserProfile not found or error - use defaults
            pass
        
        return auto_filled
    
    def _process_solo_registration(self, request, tournament):
        """Process solo registration submission"""
        # Get wizard data
        wizard_data = self.get_wizard_data(request, tournament.id, 'solo')
        
        if not wizard_data:
            raise ValidationError("Registration session expired. Please start over.")
        
        # Extract payment data
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        payment_proof = request.FILES.get('payment_proof')
        
        # Validate payment data
        if tournament.has_entry_fee:
            if not payment_method:
                raise ValidationError("Payment method is required")
            if payment_method in ['bkash', 'nagad', 'rocket'] and not transaction_id:
                raise ValidationError("Transaction ID is required")
        
        # Create registration using RegistrationService
        registration_data = {
            'game_id': wizard_data.get('riot_id', ''),
            'phone': wizard_data.get('phone', ''),
            'discord': wizard_data.get('discord', ''),
            'platform_server': wizard_data.get('platform_server', ''),
            'rank': wizard_data.get('rank', ''),
            'preferred_contact': wizard_data.get('preferred_contact', 'email'),
            'display_name': wizard_data.get('display_name', ''),
            'age': wizard_data.get('age', ''),
            'country': wizard_data.get('country', ''),
        }
        
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=request.user,
            team_id=None,
            registration_data=registration_data
        )
        
        # Submit payment if required
        if tournament.has_entry_fee:
            # Handle DeltaCoin payment separately (auto-verification)
            if payment_method == 'deltacoin':
                try:
                    # Process DeltaCoin payment (deducts from wallet and auto-verifies)
                    deltacoin_result = PaymentService.process_deltacoin_payment(
                        registration_id=registration.id,
                        user=request.user,
                        idempotency_key=f"reg-{registration.id}-dc-{request.user.id}"
                    )
                    
                    # Registration already confirmed by PaymentService
                    messages.success(
                        request,
                        f'✅ Payment successful! {deltacoin_result["amount"]} DC deducted. '
                        f'Your registration is confirmed!'
                    )
                    
                except ValidationError as e:
                    # Payment failed - delete registration and show error
                    registration.delete()
                    messages.error(request, str(e))
                    return redirect('tournaments:registration_wizard', slug=tournament.slug)
                
            else:
                # Traditional payment methods (bKash, Nagad, etc.) - requires manual verification
                payment = RegistrationService.submit_payment(
                    registration_id=registration.id,
                    payment_method=payment_method,
                    amount=tournament.entry_fee_amount,
                    transaction_id=transaction_id,
                    payment_proof=payment_proof
                )
                
                # Update registration status to payment_submitted
                registration.status = Registration.PAYMENT_SUBMITTED
                registration.save(update_fields=['status'])
                
                messages.success(
                    request,
                    f'Payment proof submitted! Your registration is pending verification.'
                )
        else:
            # No payment required - auto-confirm
            registration.status = Registration.CONFIRMED
            registration.save(update_fields=['status'])
        
        # Clear wizard data
        self.clear_wizard_data(request, tournament.id, 'solo')
        
        # Store success data for display
        request.session['registration_success'] = {
            'id': registration.id,
            'type': 'solo',
            'tournament_slug': tournament.slug,
            'player_name': wizard_data.get('display_name', request.user.username),
        }
        
        messages.success(request, f'Registration submitted successfully! ID: {registration.id}')
        return redirect('tournaments:registration_wizard_success', slug=tournament.slug)
    
    def _process_team_registration(self, request, tournament):
        """Process team registration submission"""
        wizard_data = self.get_wizard_data(request, tournament.id, 'team')
        
        if not wizard_data:
            raise ValidationError("Registration session expired. Please start over.")
        
        # Extract payment data
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        payment_proof = request.FILES.get('payment_proof')
        
        # Validate payment data
        if tournament.has_entry_fee:
            if not payment_method:
                raise ValidationError("Payment method is required")
            if payment_method in ['bkash', 'nagad', 'rocket'] and not transaction_id:
                raise ValidationError("Transaction ID is required")
        
        # TODO: Get actual team_id from team selection or creation
        # For now, we're creating placeholder team registration
        # This needs Team model integration
        
        registration_data = {
            'team_name': wizard_data.get('team_name', ''),
            'team_tag': wizard_data.get('team_tag', ''),
            'captain_name': wizard_data.get('captain_name', ''),
            'captain_game_id': wizard_data.get('captain_game_id', ''),
            'captain_email': wizard_data.get('captain_email', ''),
            'captain_phone': wizard_data.get('captain_phone', ''),
            'captain_discord': wizard_data.get('captain_discord', ''),
        }
        
        # NOTE: This is a simplified implementation
        # In production, you need to:
        # 1. Get or create Team from apps.teams
        # 2. Validate team roster size
        # 3. Check captain authority
        # 4. Pass team_id to register_participant
        
        # For now, create as user registration with team data in JSONB
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=request.user,
            team_id=None,  # TODO: Replace with actual team_id
            registration_data=registration_data
        )
        
        # Submit payment if required
        if tournament.has_entry_fee:
            # Handle DeltaCoin payment separately (auto-verification)
            if payment_method == 'deltacoin':
                try:
                    # Process DeltaCoin payment (deducts from wallet and auto-verifies)
                    deltacoin_result = PaymentService.process_deltacoin_payment(
                        registration_id=registration.id,
                        user=request.user,
                        idempotency_key=f"reg-{registration.id}-dc-team-{request.user.id}"
                    )
                    
                    # Registration already confirmed by PaymentService
                    messages.success(
                        request,
                        f'✅ Team payment successful! {deltacoin_result["amount"]} DC deducted. '
                        f'Your team registration is confirmed!'
                    )
                    
                except ValidationError as e:
                    # Payment failed - delete registration and show error
                    registration.delete()
                    messages.error(request, str(e))
                    return redirect('tournaments:registration_wizard', slug=tournament.slug)
                    
            else:
                # Traditional payment methods (bKash, Nagad, etc.) - requires manual verification
                payment = RegistrationService.submit_payment(
                    registration_id=registration.id,
                    payment_method=payment_method,
                    amount=tournament.entry_fee_amount,
                    transaction_id=transaction_id,
                    payment_proof=payment_proof
                )
                
                registration.status = Registration.PAYMENT_SUBMITTED
                registration.save(update_fields=['status'])
                
                messages.success(
                    request,
                    f'Team payment proof submitted! Registration pending verification.'
                )
        else:
            registration.status = Registration.CONFIRMED
            registration.save(update_fields=['status'])
        
        # Clear wizard data
        self.clear_wizard_data(request, tournament.id, 'team')
        
        # Store success data
        request.session['registration_success'] = {
            'id': registration.id,
            'type': 'team',
            'tournament_slug': tournament.slug,
            'team_name': wizard_data.get('team_name', 'Unknown Team'),
        }
        
        messages.success(request, f'Team registration submitted successfully! ID: {registration.id}')
        return redirect('tournaments:registration_wizard_success', slug=tournament.slug)
    
    # ===== HELPER METHODS FOR TEAM CHECKS =====
    
    def _get_user_teams(self, user):
        """Get all teams the user is a member of"""
        try:
            from apps.teams.models import TeamMembership
            memberships = TeamMembership.objects.filter(
                profile__user=user,
                status='active'
            ).select_related('team')
            return [m.team for m in memberships]
        except Exception:
            return []
    
    def _check_tournament_registration_permission(self, user, tournament):
        """
        Check if user has permission to register a team for tournaments.
        
        Returns:
            tuple: (can_register: bool, team: Team|None, user_role: str)
        """
        try:
            from apps.teams.models import TeamMembership
            
            # Get user's team memberships
            memberships = TeamMembership.objects.filter(
                profile__user=user,
                status='active'
            ).select_related('team')
            
            # Check each team for registration permission
            for membership in memberships:
                # Check if user has can_register_tournaments permission
                # Owner and Manager roles automatically have this permission
                if membership.can_register_tournaments:
                    return (True, membership.team, membership.role)
            
            # No permission found - return first team with user's role
            if memberships.exists():
                first = memberships.first()
                return (False, first.team, first.role)
            
            return (False, None, 'none')
            
        except Exception:
            return (False, None, 'error')
    
    def _get_team_leaders(self, team):
        """Get team owner and managers"""
        try:
            from apps.teams.models import TeamMembership
            
            leaders = TeamMembership.objects.filter(
                team=team,
                status='active',
                role__in=['owner', 'manager']
            ).select_related('profile__user')
            
            return leaders
        except Exception:
            return []
    
    def _check_permission_request_sent(self, user, tournament, team):
        """Check if user already sent a permission request"""
        # TODO: Implement permission request tracking
        # For now, return False
        return False


class RegistrationSuccessView(LoginRequiredMixin, View):
    """Success page after registration submission"""
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Get success data from session
        success_data = request.session.get('registration_success', {})
        
        if not success_data:
            messages.warning(request, 'No registration found.')
            return redirect('tournaments:detail', slug=slug)
        
        # Get registration
        try:
            registration = Registration.objects.get(id=success_data['id'])
        except Registration.DoesNotExist:
            messages.error(request, 'Registration not found.')
            return redirect('tournaments:detail', slug=slug)
        
        context = {
            'tournament': tournament,
            'registration': registration,
            'registration_type': success_data['type'],
            'registration_id': f'REG-{registration.id:06d}',
        }
        
        # Use appropriate template
        if success_data['type'] == 'team':
            template = 'tournaments/registration_demo/team_success.html'
        else:
            template = 'tournaments/registration_demo/solo_success.html'
        
        # Clear session data
        if 'registration_success' in request.session:
            del request.session['registration_success']
        
        return render(request, template, context)
