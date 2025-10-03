"""
Admin inline for TournamentCapacity

Provides a clean inline editor for managing capacity configuration
directly from the Tournament admin page.

Author: DeltaCrown Development Team  
Date: October 3, 2025
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.tournaments.models.core import TournamentCapacity


class TournamentCapacityInline(admin.StackedInline):
    """Inline admin for Tournament Capacity"""
    
    model = TournamentCapacity
    extra = 0
    max_num = 1
    can_delete = False
    
    fieldsets = (
        ('Capacity Configuration', {
            'fields': ('slot_size', 'max_teams'),
            'description': 'Total slots and maximum number of teams allowed'
        }),
        ('Team Size Requirements', {
            'fields': ('min_team_size', 'max_team_size'),
            'description': 'Player count constraints per team (1 for solo, 5 for Valorant, etc.)'
        }),
        ('Registration Settings', {
            'fields': ('registration_mode', 'waitlist_enabled'),
            'description': 'How teams can register and waitlist options'
        }),
        ('Current Status', {
            'fields': ('current_registrations', 'capacity_status_display'),
            'description': 'Live registration tracking (auto-updated)'
        }),
    )
    
    readonly_fields = ('capacity_status_display',)
    
    def capacity_status_display(self, obj):
        """Display current capacity status with color coding"""
        if not obj or not obj.pk:
            return format_html('<em>Not created yet</em>')
        
        # Calculate progress
        progress = obj.registration_progress_percent
        
        # Color based on capacity
        if obj.is_full:
            color = '#dc3545'  # Red
            status = 'FULL'
        elif progress >= 75:
            color = '#ffc107'  # Amber
            status = 'Nearly Full'
        elif progress >= 50:
            color = '#17a2b8'  # Blue
            status = 'Half Full'
        else:
            color = '#28a745'  # Green
            status = 'Open'
        
        return format_html(
            '<div style="padding: 10px; background: #f8f9fa; border-left: 4px solid {};">'
            '<strong style="color: {};">{}</strong><br>'
            '<span>{}</span><br>'
            '<span style="font-size: 0.9em; color: #666;">{}% filled • {} slots remaining</span><br>'
            '<span style="font-size: 0.9em; color: #666;">Mode: {}</span>'
            '</div>',
            color,
            color,
            status,
            obj.get_capacity_display(),
            progress,
            obj.available_slots,
            obj.get_registration_mode_display()
        )
    
    capacity_status_display.short_description = 'Live Status'
    
    def get_formset(self, request, obj=None, **kwargs):
        """Customize formset with help text"""
        formset = super().get_formset(request, obj, **kwargs)
        return formset
