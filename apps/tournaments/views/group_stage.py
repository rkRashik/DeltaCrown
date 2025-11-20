"""
Group Stage Views - FE-T-011, FE-T-012, FE-T-013

Implements:
- FE-T-011: Group Configuration Interface (Organizer)
- FE-T-012: Live Group Draw Interface (Organizer)
- FE-T-013: Group Standings Page (Public)

Sprint Implementation - November 20, 2025
Source: FRONTEND_TOURNAMENT_BACKLOG.md Section 2.5
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, Group, GroupStanding
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


class GroupConfigurationView(LoginRequiredMixin, View):
    """
    FE-T-011: Group Configuration Interface
    
    Organizer configures group stage settings:
    - Number of groups (2, 4, 8, 16)
    - Points system (win/draw/loss)
    - Advancement count
    - Match format
    """
    
    template_name = 'tournaments/organizer/groups/config.html'
    
    def get(self, request, slug):
        """Render group configuration form."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check organizer permission
        if not self._can_configure_groups(request.user, tournament):
            messages.error(request, "You don't have permission to configure groups")
            return redirect('tournaments:detail', slug=slug)
        
        # Check tournament format
        if tournament.format not in ['group-stage', 'group-playoff']:
            messages.error(request, "This tournament is not configured for group stage")
            return redirect('tournaments:organizer_hub', slug=slug)
        
        # Get existing groups if any
        existing_groups = Group.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('display_order')
        
        # Get participant count
        participant_count = tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        ).count()
        
        context = {
            'tournament': tournament,
            'existing_groups': existing_groups,
            'participant_count': participant_count,
            'has_groups': existing_groups.exists(),
            'is_finalized': existing_groups.filter(is_finalized=True).exists() if existing_groups else False,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug):
        """Process group configuration submission."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check permission
        if not self._can_configure_groups(request.user, tournament):
            messages.error(request, "You don't have permission to configure groups")
            return redirect('tournaments:detail', slug=slug)
        
        # Parse form data
        try:
            num_groups = int(request.POST.get('num_groups', 4))
            advancement_count = int(request.POST.get('advancement_count', 2))
            match_format = request.POST.get('match_format', 'round_robin')
            
            # Points system
            win_points = int(request.POST.get('win_points', 3))
            draw_points = int(request.POST.get('draw_points', 1))
            loss_points = int(request.POST.get('loss_points', 0))
            
            points_system = {
                'win': win_points,
                'draw': draw_points,
                'loss': loss_points
            }
            
            # Tiebreaker rules (will be applied game-specifically)
            tiebreaker_rules = ['head_to_head', 'goal_difference', 'goals_for', 'random']
            
            # Call service
            groups = GroupStageService.configure_groups(
                tournament_id=tournament.id,
                num_groups=num_groups,
                points_system=points_system,
                advancement_count=advancement_count,
                match_format=match_format,
                tiebreaker_rules=tiebreaker_rules
            )
            
            messages.success(
                request,
                f"Successfully configured {num_groups} groups. "
                f"Now proceed to draw participants into groups."
            )
            
            return redirect('tournaments:group_draw', slug=slug)
        
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('tournaments:group_config', slug=slug)
        except Exception as e:
            messages.error(request, f"Configuration failed: {str(e)}")
            return redirect('tournaments:group_config', slug=slug)
    
    def _can_configure_groups(self, user, tournament):
        """Check if user can configure groups."""
        if tournament.organizer == user:
            return True
        
        checker = StaffPermissionChecker(tournament, user)
        return checker.can_manage_bracket()


class GroupDrawView(LoginRequiredMixin, View):
    """
    FE-T-012: Live Group Draw Interface
    
    Organizer performs draw to assign participants to groups.
    Supports 3 draw methods:
    - Random: Fully random assignment
    - Seeded: Snake draft (1,2,3,4 then 4,3,2,1)
    - Manual: Drag and drop (future enhancement)
    """
    
    template_name = 'tournaments/organizer/groups/draw.html'
    
    def get(self, request, slug):
        """Render draw interface."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check permission
        if not self._can_perform_draw(request.user, tournament):
            messages.error(request, "You don't have permission to perform draw")
            return redirect('tournaments:detail', slug=slug)
        
        # Check if groups are configured
        groups = Group.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('display_order')
        
        if not groups.exists():
            messages.error(request, "Please configure groups first")
            return redirect('tournaments:group_config', slug=slug)
        
        # Check if already finalized
        if groups.filter(is_finalized=True).exists():
            messages.info(request, "Groups are already finalized")
            return redirect('tournaments:group_standings', slug=slug)
        
        # Get registrations
        registrations = tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        ).select_related('user', 'team').order_by('created_at')
        
        # Get existing standings (if draw was partially done)
        existing_standings = GroupStanding.objects.filter(
            group__tournament=tournament,
            group__is_deleted=False,
            is_deleted=False
        ).select_related('group', 'user', 'team')
        
        context = {
            'tournament': tournament,
            'groups': groups,
            'registrations': registrations,
            'existing_standings': existing_standings,
            'participant_count': registrations.count(),
            'groups_count': groups.count(),
            'is_partially_drawn': existing_standings.exists(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug):
        """Execute draw."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check permission
        if not self._can_perform_draw(request.user, tournament):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            draw_method = request.POST.get('draw_method', 'random')
            
            # Execute draw
            standings, draw_hash = GroupStageService.draw_groups(
                tournament_id=tournament.id,
                draw_method=draw_method,
            )
            
            messages.success(
                request,
                f"Draw completed! {len(standings)} participants assigned to groups. "
                f"Draw hash: {draw_hash[:16]}..."
            )
            
            return redirect('tournaments:group_standings', slug=slug)
        
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('tournaments:group_draw', slug=slug)
        except Exception as e:
            messages.error(request, f"Draw failed: {str(e)}")
            return redirect('tournaments:group_draw', slug=slug)
    
    def _can_perform_draw(self, user, tournament):
        """Check if user can perform draw."""
        if tournament.organizer == user:
            return True
        
        checker = StaffPermissionChecker(tournament, user)
        return checker.can_manage_bracket()


class GroupStandingsView(View):
    """
    FE-T-013: Group Standings Page (Public)
    
    Display standings for all groups with game-specific columns.
    Supports all 9 games.
    """
    
    template_name = 'tournaments/groups/standings.html'
    
    def get(self, request, slug):
        """Render group standings."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Get all groups
        groups = Group.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('display_order').prefetch_related(
            'standings__user',
            'standings__team'
        )
        
        if not groups.exists():
            messages.info(request, "Groups have not been configured yet")
            return redirect('tournaments:detail', slug=slug)
        
        # Calculate standings for each group
        groups_with_standings = []
        for group in groups:
            # Recalculate standings
            try:
                standings = GroupStageService.calculate_standings(
                    group_id=group.id,
                    game_slug=tournament.game.slug
                )
            except Exception:
                # Use existing standings if calculation fails
                standings = list(group.standings.filter(
                    is_deleted=False
                ).order_by('rank'))
            
            groups_with_standings.append({
                'group': group,
                'standings': standings,
            })
        
        # Determine which stat columns to show based on game
        game_slug = tournament.game.slug
        
        if game_slug in ['efootball', 'fc-mobile', 'fifa']:
            stat_columns = ['goals_for', 'goals_against', 'goal_difference']
            stat_labels = ['GF', 'GA', 'GD']
        elif game_slug in ['valorant', 'cs2']:
            stat_columns = ['rounds_won', 'rounds_lost', 'round_difference']
            stat_labels = ['RW', 'RL', 'RD']
        elif game_slug in ['pubg-mobile', 'free-fire']:
            stat_columns = ['total_kills', 'placement_points', 'average_placement']
            stat_labels = ['Kills', 'Placement Pts', 'Avg Place']
        elif game_slug == 'mobile-legends':
            stat_columns = ['total_kills', 'total_deaths', 'total_assists', 'kda_ratio']
            stat_labels = ['K', 'D', 'A', 'KDA']
        elif game_slug == 'call-of-duty-mobile':
            stat_columns = ['total_kills', 'total_deaths', 'total_score']
            stat_labels = ['Eliminations', 'Deaths', 'Score']
        else:
            # Default columns
            stat_columns = ['matches_won', 'matches_lost']
            stat_labels = ['W', 'L']
        
        context = {
            'tournament': tournament,
            'groups_with_standings': groups_with_standings,
            'stat_columns': stat_columns,
            'stat_labels': stat_labels,
            'game_name': tournament.game.name,
        }
        
        return render(request, self.template_name, context)
