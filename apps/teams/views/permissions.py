"""
Team Permission Management Views

Allows team owners to manage granular permissions for team members.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.http import JsonResponse
from django.db import transaction

from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile


class TeamPermissionManagementView(LoginRequiredMixin, View):
    """
    View for team owners to manage member permissions.
    
    Only team owners can access this view and manage permissions.
    """
    
    PERMISSION_CATEGORIES = {
        'tournament': {
            'label': 'Tournament & Competition',
            'permissions': [
                ('can_register_tournaments', 'Register team for tournaments'),
                ('can_withdraw_tournaments', 'Withdraw from tournaments'),
                ('can_submit_match_results', 'Submit match results'),
            ]
        },
        'roster': {
            'label': 'Roster Management',
            'permissions': [
                ('can_invite_members', 'Invite new members'),
                ('can_remove_members', 'Remove/kick members'),
                ('can_manage_roles', 'Change member roles'),
                ('can_manage_permissions', 'Manage member permissions'),
            ]
        },
        'team': {
            'label': 'Team Profile & Settings',
            'permissions': [
                ('can_edit_team_profile', 'Edit team profile'),
                ('can_edit_team_settings', 'Modify team settings'),
                ('can_manage_social_links', 'Update social links'),
            ]
        },
        'content': {
            'label': 'Content & Community',
            'permissions': [
                ('can_create_posts', 'Create team posts'),
                ('can_manage_posts', 'Manage all posts'),
                ('can_manage_announcements', 'Manage announcements'),
            ]
        },
        'financial': {
            'label': 'Financial',
            'permissions': [
                ('can_manage_finances', 'Manage team finances'),
                ('can_view_financial_reports', 'View financial reports'),
            ]
        },
        'schedule': {
            'label': 'Schedule & Practice',
            'permissions': [
                ('can_schedule_practice', 'Schedule practice sessions'),
                ('can_manage_schedule', 'Manage team schedule'),
            ]
        },
    }
    
    def get(self, request, slug, member_id):
        """Show permission management form for a specific member."""
        team = get_object_or_404(Team, slug=slug)
        
        # Get current user's profile and membership
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            messages.error(request, "You need a profile to manage team permissions.")
            return redirect('teams:detail', slug=team.slug)
        
        user_membership = TeamMembership.objects.filter(
            team=team,
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        # Only team owner can manage permissions
        if not user_membership or user_membership.role != TeamMembership.Role.OWNER:
            messages.error(request, "Only team owners can manage member permissions.")
            return redirect('teams:detail', slug=team.slug)
        
        # Get the member whose permissions are being edited
        member = get_object_or_404(
            TeamMembership,
            id=member_id,
            team=team,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Cannot edit owner's permissions
        if member.role == TeamMembership.Role.OWNER:
            messages.error(request, "Cannot modify owner permissions. Owners have full access by default.")
            return redirect('teams:detail', slug=team.slug)
        
        # Get current permissions
        current_permissions = member.get_all_permissions()
        
        # Build permission categories with current state
        permission_categories_with_state = {}
        for category_key, category in self.PERMISSION_CATEGORIES.items():
            permissions_with_state = []
            for perm_key, perm_label in category['permissions']:
                permissions_with_state.append({
                    'key': perm_key,
                    'label': perm_label,
                    'enabled': current_permissions.get(perm_key, False)
                })
            permission_categories_with_state[category_key] = {
                'label': category['label'],
                'permissions': permissions_with_state
            }
        
        context = {
            'team': team,
            'member': member,
            'permission_categories': permission_categories_with_state,
        }
        
        return render(request, 'teams/permissions/manage.html', context)
    
    def post(self, request, slug, member_id):
        """Update member permissions."""
        team = get_object_or_404(Team, slug=slug)
        
        # Get current user's profile and membership
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            messages.error(request, "You need a profile to manage team permissions.")
            return redirect('teams:detail', slug=team.slug)
        
        user_membership = TeamMembership.objects.filter(
            team=team,
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        # Only team owner can manage permissions
        if not user_membership or user_membership.role != TeamMembership.Role.OWNER:
            messages.error(request, "Only team owners can manage member permissions.")
            return redirect('teams:detail', slug=team.slug)
        
        # Get the member whose permissions are being edited
        member = get_object_or_404(
            TeamMembership,
            id=member_id,
            team=team,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Cannot edit owner's permissions
        if member.role == TeamMembership.Role.OWNER:
            messages.error(request, "Cannot modify owner permissions.")
            return redirect('teams:detail', slug=team.slug)
        
        # Get all permission fields
        all_permissions = []
        for category in self.PERMISSION_CATEGORIES.values():
            all_permissions.extend([perm[0] for perm in category['permissions']])
        
        # Update permissions based on form data
        with transaction.atomic():
            for perm in all_permissions:
                # Permission is granted if checkbox is checked (present in POST)
                # Permission is revoked if checkbox is not checked (absent in POST)
                if perm in request.POST:
                    member.grant_permission(perm, save=False)
                else:
                    member.revoke_permission(perm, save=False)
            
            member.save()
        
        messages.success(
            request,
            f"Permissions updated for {member.profile.user.get_full_name() or member.profile.user.username}"
        )
        
        return redirect('teams:detail', slug=team.slug)


class TeamPermissionBulkUpdateView(LoginRequiredMixin, View):
    """
    AJAX endpoint for bulk permission updates.
    
    Allows updating a single permission for a member via AJAX.
    """
    
    def post(self, request, slug):
        """Toggle a single permission for a member."""
        team = get_object_or_404(Team, slug=slug)
        
        # Get current user's profile and membership
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return JsonResponse({'success': False, 'error': 'Profile not found'}, status=403)
        
        user_membership = TeamMembership.objects.filter(
            team=team,
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        # Only team owner can manage permissions
        if not user_membership or user_membership.role != TeamMembership.Role.OWNER:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Get parameters
        member_id = request.POST.get('member_id')
        permission = request.POST.get('permission')
        enabled = request.POST.get('enabled') == 'true'
        
        if not all([member_id, permission]):
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)
        
        # Get the member
        member = TeamMembership.objects.filter(
            id=member_id,
            team=team,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        if not member:
            return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)
        
        # Cannot edit owner's permissions
        if member.role == TeamMembership.Role.OWNER:
            return JsonResponse({'success': False, 'error': 'Cannot modify owner permissions'}, status=403)
        
        # Update permission
        if enabled:
            member.grant_permission(permission)
        else:
            member.revoke_permission(permission)
        
        return JsonResponse({
            'success': True,
            'permission': permission,
            'enabled': enabled,
            'member_id': member_id
        })


class TeamMemberListView(LoginRequiredMixin, View):
    """
    View to list all team members with their roles and permission summaries.
    
    Team owners/managers can see permission details.
    """
    
    def get(self, request, slug):
        """Show team member list with permission summaries."""
        team = get_object_or_404(Team, slug=slug)
        
        # Get current user's profile and membership
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            messages.error(request, "You need a profile to view team members.")
            return redirect('teams:detail', slug=team.slug)
        
        user_membership = TeamMembership.objects.filter(
            team=team,
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        # Check if user is at least a member
        if not user_membership:
            messages.error(request, "You are not a member of this team.")
            return redirect('teams:detail', slug=team.slug)
        
        # Get all active members
        members = TeamMembership.objects.filter(
            team=team,
            status=TeamMembership.Status.ACTIVE
        ).select_related('profile__user').order_by('role', '-joined_at')
        
        # Add permission summaries
        for member in members:
            member.permissions = member.get_all_permissions()
            member.permission_count = sum(1 for v in member.permissions.values() if v)
        
        # User can manage permissions if they are the owner
        can_manage_permissions = user_membership.role == TeamMembership.Role.OWNER
        
        context = {
            'team': team,
            'members': members,
            'can_manage_permissions': can_manage_permissions,
            'user_membership': user_membership,
        }
        
        return render(request, 'teams/permissions/member_list.html', context)
