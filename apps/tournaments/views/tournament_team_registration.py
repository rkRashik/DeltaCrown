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
        
        # ELIGIBILITY CHECK: User must have a team for this game
        user_team = None
        team_members = []
        eligibility_error = None
        
        try:
            from apps.teams.models import Team, TeamMembership
            from apps.user_profile.models import UserProfile
            
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if not user_profile:
                eligibility_error = "You need to create a profile first."
            else:
                # Get user's teams for this game
                user_teams = Team.objects.filter(
                    game=tournament.game.slug,
                    memberships__profile=user_profile,
                    memberships__status=TeamMembership.Status.ACTIVE,
                    is_active=True
                ).distinct()
                
                if not user_teams.exists():
                    eligibility_error = f"You need to join a {tournament.game.name} team to register for this tournament."
                else:
                    # Find first team where user has registration permission
                    user_team = None
                    user_membership = None
                    
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
                    
                    if not user_team:
                        eligibility_error = "You don't have permission to register any of your teams for tournaments. Contact your team captain or manager."
                    else:
                        # Get active team members
                        team_members = TeamMembership.objects.filter(
                            team=user_team,
                            status=TeamMembership.Status.ACTIVE
                        ).select_related('profile__user').order_by('role', '-joined_at')
                        
                        # Check minimum roster size
                        min_team_size = getattr(tournament.game, 'min_team_size', 5)
                        if team_members.count() < min_team_size:
                            eligibility_error = f"Your team needs at least {min_team_size} active members to register. Current: {team_members.count()}"
        except Exception as e:
            import traceback
            print(f"Error loading team data: {e}")
            print(traceback.format_exc())
            eligibility_error = "Error checking team eligibility. Please try again."
        
        # If not eligible, show error page
        if eligibility_error and step == '1':
            return render(request, 'tournaments/team_registration/team_eligibility_error.html', {
                'tournament': tournament,
                'error_message': eligibility_error,
                'user_team': user_team,
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
            # Save team info to session
            team_data = {
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
            
            # Collect roster data
            roster = []
            player_index = 1
            
            while True:
                player_name = request.POST.get(f'player_{player_index}_name')
                if player_name is None:
                    break
                
                player_data = {
                    'full_name': player_name,
                    'display_name': request.POST.get(f'player_{player_index}_ign', ''),
                }
                
                if form_config.enable_roster_emails_field:
                    player_data['email'] = request.POST.get(f'player_{player_index}_email', '')
                
                roster.append(player_data)
                player_index += 1
            
            team_data['roster'] = roster
            # If roster is empty, add dummy data for testing
            if not roster:
                roster = [
                    {'full_name': 'Test Player 1', 'display_name': 'TestPlayer1#VAL', 'email': 'test1@example.com'},
                    {'full_name': 'Test Player 2', 'display_name': 'TestPlayer2#VAL', 'email': 'test2@example.com'},
                ]
                team_data['roster'] = roster
            request.session[f'team_registration_{tournament.id}'] = team_data
            return redirect(f'{request.path}?step=2')
        
        elif step == '2':
            return redirect(f'{request.path}?step=3')
        
        elif step == '3':
            # Store registration type before clearing session
            request.session['registration_type'] = 'team'
            request.session['registration_step_data'] = request.session.get(f'registration_demo_{tournament.id}_team', {})
            
            # Clear registration session
            if f'team_registration_{tournament.id}' in request.session:
                del request.session[f'team_registration_{tournament.id}']
            
            messages.success(request, 'Team registration submitted successfully!')
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
