"""
Demo Registration Views - Showcase for New Form Builder System

This is a temporary demo implementation to showcase the new registration
experience while the full form builder system is being developed.

Once the dynamic form builder (Sprint 1-5) is complete, these views will be
replaced with the FormRenderService-based implementation.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from apps.tournaments.models import Tournament
from apps.tournaments.models.form_configuration import TournamentFormConfiguration


class SoloRegistrationDemoView(LoginRequiredMixin, View):
    """
    3-Step Solo Player Registration Demo
    Steps: 1) Player Info → 2) Review & Terms → 3) Payment
    """
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.GET.get('step', '1')
        
        # Get or create form configuration
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
        
        # Validate step
        if step not in ['1', '2', '3']:
            step = '1'
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
            'form_config': form_config,
            'user': request.user,
        }
        
        # Step-specific context
        if step == '1':
            # Player Information Step
            context['step_title'] = 'Player Information'
            context['step_description'] = 'Tell us about yourself'
            template = 'tournaments/registration_demo/solo_step1_new.html'
            
        elif step == '2':
            # Review & Accept Terms Step
            context['step_title'] = 'Review & Accept Terms'
            context['step_description'] = 'Confirm your details'
            # Get data from session
            player_data = request.session.get(f'registration_demo_{tournament.id}_player', {})
            context['registration_data'] = player_data  # Use registration_data for new templates
            template = 'tournaments/registration_demo/solo_step2_new.html'
            
        elif step == '3':
            # Payment Step
            context['step_title'] = 'Payment'
            context['step_description'] = 'Complete your registration'
            context['entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else 500
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            template = 'tournaments/registration_demo/solo_step3_simple.html'
        
        return render(request, template, context)
    
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Save player info to session
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
                'preferred_contact': request.POST.get('preferred_contact', ''),
            }
            request.session[f'registration_demo_{tournament.id}_player'] = player_data
            return redirect(f'{request.path}?step=2')
        
        elif step == '2':
            # Proceed to payment
            return redirect(f'{request.path}?step=3')
        
        elif step == '3':
            # Process payment (demo - just show success)
            # Store registration type before clearing session
            request.session['demo_registration_type'] = 'solo'
            request.session['registration_step_data'] = request.session.get(f'team_registration_{tournament.id}', {})
            
            # Clear registration session
            if f'registration_demo_{tournament.id}_player' in request.session:
                del request.session[f'registration_demo_{tournament.id}_player']
            
            messages.success(request, 'Registration submitted successfully!')
            return redirect('tournaments:registration_demo_success', slug=tournament.slug)
        
        return redirect(f'{request.path}?step=1')


class TeamRegistrationView(LoginRequiredMixin, View):
    """
    Professional Team Registration Wizard
    Steps: 1) Team Info → 2) Review & Agreements → 3) Payment
    """
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.GET.get('step', '1')
        
        # Get or create form configuration
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
        
        # CHECK: Already registered for this tournament?
        from apps.tournaments.models.registration import Registration
        
        # Check both user-level and team-level registrations
        existing_registration = Registration.objects.filter(
            tournament=tournament,
            user=request.user,
            is_deleted=False
        ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).first()
        
        # Also check if user's teams are registered
        if not existing_registration:
            try:
                from apps.user_profile.models import UserProfile
                user_profile = UserProfile.objects.filter(user=request.user).first()
                if user_profile:
                    from apps.teams.models import TeamMembership
                    user_team_ids = TeamMembership.objects.filter(
                        profile=user_profile,
                        status=TeamMembership.Status.ACTIVE
                    ).values_list('team_id', flat=True)
                    
                    existing_registration = Registration.objects.filter(
                        tournament=tournament,
                        team_id__in=user_team_ids,
                        is_deleted=False
                    ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).first()
            except Exception as e:
                import traceback
                print(f"Error checking team registrations: {e}")
                print(traceback.format_exc())
        
        if existing_registration:
            # Show already registered page with lobby access and verification status
            return render(request, 'tournaments/team_registration/already_registered.html', {
                'tournament': tournament,
                'registration': existing_registration,
                'form_config': form_config,
                'needs_verification': existing_registration.status in [Registration.PENDING, Registration.PAYMENT_SUBMITTED],
            })
        
        # ELIGIBILITY CHECK: User must have a team for this game
        user_team = None
        team_members = []
        eligibility_error = None
        error_type = None
        error_context = {}
        
        try:
            from apps.teams.models import Team, TeamMembership
            from apps.user_profile.models import UserProfile
            
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if not user_profile:
                eligibility_error = "You need to complete your user profile before registering for tournaments."
                error_type = 'no_profile'
                error_context = {
                    'error_title': 'Profile Required',
                }
            else:
                # Get user's teams for this game
                user_teams = Team.objects.filter(
                    game=tournament.game.slug,
                    memberships__profile=user_profile,
                    memberships__status=TeamMembership.Status.ACTIVE,
                    is_active=True
                ).distinct()
                
                if not user_teams.exists():
                    eligibility_error = f"You are not a member of any active {tournament.game.name} team. Please join or create a team to participate in this tournament."
                    error_type = 'no_team'
                    error_context = {
                        'error_title': 'No Team Found',
                    }
                else:
                    # Find first team where user has registration permission
                    user_team = None
                    user_membership = None
                    captain_name = None
                    
                    for team in user_teams:
                        membership = TeamMembership.objects.filter(
                            team=team, 
                            profile=user_profile,
                            status=TeamMembership.Status.ACTIVE
                        ).first()
                        
                        if membership and (membership.role in [
                            TeamMembership.Role.OWNER,
                            TeamMembership.Role.MANAGER, 
                            TeamMembership.Role.CAPTAIN
                        ] or membership.can_register_tournaments):
                            user_team = team
                            user_membership = membership
                            break
                        
                        # Track captain for error message
                        if not captain_name:
                            captain_membership = TeamMembership.objects.filter(
                                team=team,
                                role__in=[TeamMembership.Role.OWNER, TeamMembership.Role.CAPTAIN],
                                status=TeamMembership.Status.ACTIVE
                            ).first()
                            if captain_membership:
                                captain_name = captain_membership.profile.user.username
                    
                    if not user_team:
                        eligibility_error = "You don't have permission to register any of your teams for tournaments. Only team captains, managers, or members with explicit tournament registration permission can register."
                        error_type = 'no_permission'
                        error_context = {
                            'error_title': 'No Registration Permission',
                            'captain_name': captain_name,
                        }
                    else:
                        # CHECK: Team already registered by another member?
                        team_registration = Registration.objects.filter(
                            tournament=tournament,
                            team_id=user_team.id,
                            is_deleted=False
                        ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).first()
                        
                        if team_registration:
                            # Team already registered - show who registered it
                            return render(request, 'tournaments/team_registration/team_already_registered.html', {
                                'tournament': tournament,
                                'team': user_team,
                                'registration': team_registration,
                                'registered_by': team_registration.user,
                                'form_config': form_config,
                            })
                        
                        # Get active team members
                        team_members = TeamMembership.objects.filter(
                            team=user_team,
                            status=TeamMembership.Status.ACTIVE
                        ).select_related('profile__user').order_by('role', '-joined_at')
                        
                        # Check minimum roster size
                        min_team_size = getattr(tournament.game, 'min_team_size', 5)
                        current_count = team_members.count()
                        if current_count < min_team_size:
                            members_needed = min_team_size - current_count
                            eligibility_error = f"Your team '{user_team.name}' only has {current_count} active member{'s' if current_count != 1 else ''}, but this tournament requires a minimum of {min_team_size}. Please recruit {members_needed} more member{'s' if members_needed != 1 else ''} before registering."
                            error_type = 'roster_too_small'
                            error_context = {
                                'error_title': 'Roster Too Small',
                                'current_members': current_count,
                                'required_members': min_team_size,
                                'members_needed': members_needed,
                            }
        except Exception as e:
            import traceback
            print(f"Error loading team data: {e}")
            print(traceback.format_exc())
            eligibility_error = "An unexpected error occurred while checking your team eligibility. Please try again or contact support if the problem persists."
            error_type = 'system_error'
            error_context = {
                'error_title': 'System Error',
            }
        
        # If not eligible, show error page (regardless of step)
        if eligibility_error:
            return render(request, 'tournaments/team_registration/team_eligibility_error.html', {
                'tournament': tournament,
                'error_message': eligibility_error,
                'error_type': error_type,
                'user_team': user_team,
                **error_context,
            })
        
        if step not in ['1', '2', '3']:
            step = '1'
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
            'form_config': form_config,
            'user': request.user,
            'user_profile': user_profile,
        }
        
        if step == '1':
            context['step_title'] = 'Team Information'
            context['step_description'] = 'Confirm your team roster'
            context['user_team'] = user_team
            context['team_members'] = team_members
            template = 'tournaments/team_registration/team_step1_new.html'
            
        elif step == '2':
            context['step_title'] = 'Review & Agreements'
            context['step_description'] = 'Confirm team roster'
            team_data = request.session.get(f'team_registration_{tournament.id}', {})
            context['registration_data'] = team_data  # Use registration_data for new templates
            template = 'tournaments/team_registration/team_step2_new.html'
            
        elif step == '3':
            # Payment Step
            context['step_title'] = 'Team Payment'
            context['step_description'] = 'Complete team registration'
            # For team tournaments, use entry_fee_amount (could be team-specific)
            context['team_entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else 0
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            template = 'tournaments/team_registration/team_step3_new.html'
        
        return render(request, template, context)
    
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.POST.get('step', '1')
        
        # Get or create form configuration (needed for POST processing)
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
        
        if step == '1':
            # Find user's team (same logic as GET method)
            from apps.teams.models import Team, TeamMembership
            from apps.user_profile.models import UserProfile
            
            user_profile = UserProfile.objects.filter(user=request.user).first()
            user_team = None
            
            if user_profile:
                # Get user's teams for this game
                user_teams = Team.objects.filter(
                    game=tournament.game.slug,
                    memberships__profile=user_profile,
                    memberships__status=TeamMembership.Status.ACTIVE,
                    is_active=True
                ).distinct()
                
                # Find first team where user has registration permission
                for team in user_teams:
                    membership = TeamMembership.objects.filter(
                        team=team, 
                        profile=user_profile,
                        status=TeamMembership.Status.ACTIVE
                    ).first()
                    
                    if membership and (membership.role in [
                        TeamMembership.Role.OWNER,
                        TeamMembership.Role.MANAGER, 
                        TeamMembership.Role.CAPTAIN
                    ] or membership.can_register_tournaments):
                        user_team = team
                        break
            
            # Save team info to session
            team_data = {
                'team_id': user_team.id if user_team else None,
                'team_name': request.POST.get('team_name', ''),
                'team_tag': request.POST.get('team_tag', ''),
                'captain_full_name': request.POST.get('captain_full_name', ''),
                'captain_game_id': request.POST.get('captain_game_id', ''),
                'captain_email': request.POST.get('captain_email', ''),
                'captain_phone': request.POST.get('captain_phone', ''),
                'captain_discord': request.POST.get('captain_discord', ''),
            }
            
            # Add conditional fields
            if form_config.enable_captain_display_name_field:
                team_data['captain_display_name'] = request.POST.get('captain_display_name', '')
            
            # Add team conditional fields
            if form_config.enable_team_region_field:
                team_data['team_region'] = request.POST.get('team_region', '')
            
            if form_config.enable_team_logo_field and 'team_logo' in request.FILES:
                team_data['team_logo'] = request.FILES['team_logo']
            
            # Collect SELECTED roster data for tournament (esports-style selection)
            roster = []
            
            # Collect starting lineup
            starting_index = 1
            while True:
                player_id = request.POST.get(f'starting_{starting_index}_id')
                if not player_id:
                    break
                
                player_data = {
                    'member_id': player_id,
                    'full_name': request.POST.get(f'starting_{starting_index}_name', ''),
                    'display_name': request.POST.get(f'starting_{starting_index}_ign', ''),
                    'email': request.POST.get(f'starting_{starting_index}_email', ''),
                    'role': request.POST.get(f'starting_{starting_index}_role', 'Player'),
                    'position': 'starting',
                    'position_number': starting_index
                }
                
                roster.append(player_data)
                starting_index += 1
            
            # Collect substitutes
            substitute_index = 1
            while True:
                player_id = request.POST.get(f'substitute_{substitute_index}_id')
                if not player_id:
                    break
                
                player_data = {
                    'member_id': player_id,
                    'full_name': request.POST.get(f'substitute_{substitute_index}_name', ''),
                    'display_name': request.POST.get(f'substitute_{substitute_index}_ign', ''),
                    'email': request.POST.get(f'substitute_{substitute_index}_email', ''),
                    'role': 'Substitute',
                    'position': 'substitute',
                    'position_number': substitute_index
                }
                
                roster.append(player_data)
                substitute_index += 1
            
            team_data['roster'] = roster
            team_data['roster_count'] = {
                'starting': starting_index - 1,
                'substitutes': substitute_index - 1,
                'total': len(roster)
            }
            
            # Lock all selected members for this tournament
            from apps.teams.models import TeamMembership
            for player in roster:
                try:
                    membership = TeamMembership.objects.get(id=player['member_id'])
                    membership.lock_for_tournament(tournament.id, tournament.tournament_end or tournament.tournament_start)
                except TeamMembership.DoesNotExist:
                    pass
            
            request.session[f'team_registration_{tournament.id}'] = team_data
            return redirect(f'{request.path}?step=2')
        
        elif step == '2':
            # Check if tournament has entry fee
            if tournament.has_entry_fee and tournament.entry_fee_amount > 0:
                # Redirect to payment step
                return redirect(f'{request.path}?step=3')
            else:
                # No payment needed, complete registration directly
                # Store registration type before clearing session
                request.session['registration_type'] = 'team'
                
                # Add payment info for success page (no payment required)
                team_data['payment_method'] = 'No payment required'
                team_data['transaction_id'] = 'N/A'
                
                # Transform roster data for template compatibility
                roster = team_data.get('roster', [])
                
                # Map roster to individual player fields for template
                for player in roster:
                    if player.get('position') == 'starting':
                        position_num = player.get('position_number', 1)
                        if position_num == 1:
                            # Captain is already handled separately
                            continue
                        elif position_num == 2:
                            team_data['player2_ign'] = player.get('display_name', '')
                            team_data['player2_riot_id'] = player.get('full_name', '')  # Using full_name as riot_id equivalent
                        elif position_num == 3:
                            team_data['player3_ign'] = player.get('display_name', '')
                            team_data['player3_riot_id'] = player.get('full_name', '')
                        elif position_num == 4:
                            team_data['player4_ign'] = player.get('display_name', '')
                            team_data['player4_riot_id'] = player.get('full_name', '')
                        elif position_num == 5:
                            team_data['player5_ign'] = player.get('display_name', '')
                            team_data['player5_riot_id'] = player.get('full_name', '')
                    elif player.get('position') == 'substitute':
                        team_data['substitute_ign'] = player.get('display_name', '')
                        team_data['substitute_riot_id'] = player.get('full_name', '')
                
                request.session['registration_step_data'] = team_data
                
                # Create registration record
                from apps.tournaments.models.registration import Registration
                team_data = request.session.get(f'team_registration_{tournament.id}', {})
                
                # CHECK: Already registered for this tournament?
                existing_registration = Registration.objects.filter(
                    tournament=tournament,
                    user=request.user,
                    is_deleted=False
                ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).first()
                
                if existing_registration:
                    # User already registered - redirect to already registered page
                    messages.warning(request, 'You are already registered for this tournament.')
                    return redirect('tournaments:detail', slug=tournament.slug)
                
                Registration.objects.create(
                    tournament=tournament,
                    user=request.user,
                    team_id=team_data.get('team_id'),  # Get from session data
                    registration_data=team_data,
                    status=Registration.CONFIRMED,  # Auto-confirm if no payment needed
                    current_step=2,  # Review step completed
                    time_spent_seconds=0  # TODO: Track actual time spent in wizard
                )
                
                # Clear registration session
                if f'team_registration_{tournament.id}' in request.session:
                    del request.session[f'team_registration_{tournament.id}']
                
                messages.success(request, 'Team registration completed successfully!')
                return redirect('tournaments:registration_success', slug=tournament.slug)
        
        elif step == '3':
            # Process payment and create registration
            from apps.tournaments.models.registration import Registration, Payment
            from decimal import Decimal
            
            team_data = request.session.get(f'team_registration_{tournament.id}', {})
            
            # CHECK: Already registered for this tournament?
            existing_registration = Registration.objects.filter(
                tournament=tournament,
                user=request.user,
                is_deleted=False
            ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).first()
            
            if existing_registration:
                # User already registered - redirect to already registered page
                messages.warning(request, 'You are already registered for this tournament.')
                return redirect('tournaments:detail', slug=tournament.slug)
            
            # Create registration record
            registration = Registration.objects.create(
                tournament=tournament,
                user=None,  # Team registrations don't have a user - only team_id
                team_id=team_data.get('team_id'),  # Get from session data
                registration_data=team_data,
                status=Registration.PAYMENT_SUBMITTED,
                current_step=3,  # Payment step completed
                time_spent_seconds=0  # TODO: Track actual time spent in wizard
            )
            
            # Create payment record
            payment_method = request.POST.get('payment_method', 'bkash')
            
            if payment_method == 'deltacoin':
                # Handle DeltaCoin payment - auto-verify and debit wallet
                from apps.tournaments.services.registration_service import RegistrationService
                try:
                    payment, dc_transaction = RegistrationService.pay_with_deltacoin(
                        registration_id=registration.id,
                        user=request.user
                    )
                    # Update registration status to confirmed (already done in pay_with_deltacoin)
                    registration.refresh_from_db()
                except Exception as e:
                    messages.error(request, f'Payment failed: {str(e)}')
                    return redirect(f'{request.path}?step=3')
            else:
                # Handle manual payment methods (bKash, Nagad, etc.)
                Payment.objects.create(
                    registration=registration,
                    payment_method=payment_method,
                    amount=Decimal(str(tournament.entry_fee_amount)),
                    transaction_id=request.POST.get('transaction_id', ''),
                    payment_proof=payment_proof,
                    status='submitted'
                )
            
            # Add payment info to team_data for success page display
            team_data['payment_method'] = payment_method
            team_data['transaction_id'] = request.POST.get('transaction_id', '')
            
            # Transform roster data for template compatibility
            roster = team_data.get('roster', [])
            
            # Map roster to individual player fields for template
            for player in roster:
                if player.get('position') == 'starting':
                    position_num = player.get('position_number', 1)
                    if position_num == 1:
                        # Captain is already handled separately
                        continue
                    elif position_num == 2:
                        team_data['player2_ign'] = player.get('display_name', '')
                        team_data['player2_riot_id'] = player.get('full_name', '')  # Using full_name as riot_id equivalent
                    elif position_num == 3:
                        team_data['player3_ign'] = player.get('display_name', '')
                        team_data['player3_riot_id'] = player.get('full_name', '')
                    elif position_num == 4:
                        team_data['player4_ign'] = player.get('display_name', '')
                        team_data['player4_riot_id'] = player.get('full_name', '')
                    elif position_num == 5:
                        team_data['player5_ign'] = player.get('display_name', '')
                        team_data['player5_riot_id'] = player.get('full_name', '')
                elif player.get('position') == 'substitute':
                    team_data['substitute_ign'] = player.get('display_name', '')
                    team_data['substitute_riot_id'] = player.get('full_name', '')
            
            # Store registration type before clearing session
            request.session['registration_type'] = 'team'
            request.session['registration_step_data'] = team_data
            
            # Clear registration session
            if f'team_registration_{tournament.id}' in request.session:
                del request.session[f'team_registration_{tournament.id}']
            
            # Success message based on payment method
            if payment_method == 'deltacoin':
                messages.success(request, 'Team registration completed successfully! Your DeltaCoin payment has been processed and your team is now registered.')
            else:
                messages.success(request, 'Team registration submitted successfully! Payment is pending verification.')
            
            return redirect('tournaments:registration_success', slug=tournament.slug)
        
        return redirect(f'{request.path}?step=1')


class RegistrationSuccessView(LoginRequiredMixin, View):
    """Success page for tournament registration (both solo and team)."""
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Get registration type from session
        registration_type = request.session.get('registration_type', 'solo')
        
        # Get step data from session
        step_data = request.session.get('registration_step_data', {})
        
        context = {
            'tournament': tournament,
            'registration_type': registration_type,
            'step_data': step_data,
            'registration_id': 'REG-12345',  # Registration ID for display
        }
        
        # Clear session data after displaying success
        if 'registration_step_data' in request.session:
            del request.session['registration_step_data']
        if 'registration_type' in request.session:
            del request.session['registration_type']
        
        # Use appropriate template based on registration type
        if registration_type == 'team':
            return render(request, 'tournaments/team_registration/team_success.html', context)
        else:
            return render(request, 'tournaments/team_registration/solo_success.html', context)
