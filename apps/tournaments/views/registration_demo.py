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


class SoloRegistrationDemoView(LoginRequiredMixin, View):
    """
    3-Step Solo Player Registration Demo
    Steps: 1) Player Info → 2) Review & Terms → 3) Payment
    """
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.GET.get('step', '1')
        
        # Validate step
        if step not in ['1', '2', '3']:
            step = '1'
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
        }
        
        # Step-specific context
        if step == '1':
            # Player Information Step
            context['step_title'] = 'Player Information'
            context['step_description'] = 'Tell us about yourself'
            template = 'tournaments/registration_demo/solo_step1.html'
            
        elif step == '2':
            # Review & Accept Terms Step
            context['step_title'] = 'Review & Accept Terms'
            context['step_description'] = 'Confirm your details'
            # Get data from session
            player_data = request.session.get(f'registration_demo_{tournament.id}_player', {})
            context['step_data'] = player_data  # Use step_data for consistency with templates
            template = 'tournaments/registration_demo/solo_step2.html'
            
        elif step == '3':
            # Payment Step
            context['step_title'] = 'Payment'
            context['step_description'] = 'Complete your registration'
            context['entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else 0
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            template = 'tournaments/registration_demo/solo_step3.html'
        
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
            request.session['demo_step_data'] = request.session.get(f'registration_demo_{tournament.id}_player', {})
            
            # Clear registration session
            if f'registration_demo_{tournament.id}_player' in request.session:
                del request.session[f'registration_demo_{tournament.id}_player']
            
            messages.success(request, 'Registration submitted successfully!')
            return redirect('tournaments:registration_demo_success', slug=tournament.slug)
        
        return redirect(f'{request.path}?step=1')


class TeamRegistrationDemoView(LoginRequiredMixin, View):
    """
    3-Step Team Registration Demo
    Steps: 1) Team Info → 2) Review & Agreements → 3) Payment
    """
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.GET.get('step', '1')
        
        if step not in ['1', '2', '3']:
            step = '1'
        
        context = {
            'tournament': tournament,
            'current_step': int(step),
            'total_steps': 3,
        }
        
        if step == '1':
            context['step_title'] = 'Team Information'
            context['step_description'] = 'Enter your team details'
            template = 'tournaments/registration_demo/team_step1.html'
            
        elif step == '2':
            context['step_title'] = 'Review & Agreements'
            context['step_description'] = 'Confirm team roster'
            team_data = request.session.get(f'registration_demo_{tournament.id}_team', {})
            context['step_data'] = team_data  # Use step_data for consistency with templates
            template = 'tournaments/registration_demo/team_step2.html'
            
        elif step == '3':
            # Payment Step
            context['step_title'] = 'Team Payment'
            context['step_description'] = 'Complete team registration'
            # For team tournaments, use entry_fee_amount (could be team-specific)
            context['team_entry_fee'] = tournament.entry_fee_amount if tournament.has_entry_fee else 0
            context['currency'] = tournament.entry_fee_currency if tournament.has_entry_fee else 'BDT'
            template = 'tournaments/registration_demo/team_step3.html'
        
        return render(request, template, context)
    
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Save team info to session
            team_data = {
                'team_name': request.POST.get('team_name', ''),
                'team_tag': request.POST.get('team_tag', ''),
                'captain_name': request.POST.get('captain_name', ''),
                'captain_game_id': request.POST.get('captain_game_id', ''),
                'captain_email': request.POST.get('captain_email', ''),
                'captain_phone': request.POST.get('captain_phone', ''),
                'captain_discord': request.POST.get('captain_discord', ''),
            }
            request.session[f'registration_demo_{tournament.id}_team'] = team_data
            return redirect(f'{request.path}?step=2')
        
        elif step == '2':
            return redirect(f'{request.path}?step=3')
        
        elif step == '3':
            # Store registration type before clearing session
            request.session['demo_registration_type'] = 'team'
            request.session['demo_step_data'] = request.session.get(f'registration_demo_{tournament.id}_team', {})
            
            # Clear registration session
            if f'registration_demo_{tournament.id}_team' in request.session:
                del request.session[f'registration_demo_{tournament.id}_team']
            
            messages.success(request, 'Team registration submitted successfully!')
            return redirect('tournaments:registration_demo_success', slug=tournament.slug)
        
        return redirect(f'{request.path}?step=1')


class RegistrationDemoSuccessView(LoginRequiredMixin, View):
    """Success page for demo registration (both solo and team)."""
    
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Get registration type from session
        registration_type = request.session.get('demo_registration_type', 'solo')
        
        # Get step data from session
        step_data = request.session.get('demo_step_data', {})
        
        context = {
            'tournament': tournament,
            'registration_type': registration_type,
            'step_data': step_data,
            'registration_id': 'DEMO-12345',  # Keep demo ID for display
        }
        
        # Clear session data after displaying success
        if 'demo_step_data' in request.session:
            del request.session['demo_step_data']
        if 'demo_registration_type' in request.session:
            del request.session['demo_registration_type']
        
        # Use appropriate template based on registration type
        if registration_type == 'team':
            return render(request, 'tournaments/registration_demo/team_success.html', context)
        else:
            return render(request, 'tournaments/registration_demo/solo_success.html', context)
