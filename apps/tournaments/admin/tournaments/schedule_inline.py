# apps/tournaments/admin/tournaments/schedule_inline.py
"""
Admin inline for TournamentSchedule model.
Part of the pilot phase refactoring.
"""
from django.contrib import admin
from django.utils.html import format_html
from apps.tournaments.models import TournamentSchedule


class TournamentScheduleInline(admin.StackedInline):
    """
    Inline admin for managing tournament schedule.
    Displays all schedule-related fields in a single section.
    """
    model = TournamentSchedule
    can_delete = False
    verbose_name = "Schedule (Dates & Times)"
    verbose_name_plural = "Schedule (Dates & Times)"
    
    fieldsets = (
        ('Registration Window', {
            'fields': (
                ('reg_open_at', 'reg_close_at'),
                'registration_status_display',
            ),
            'description': 'When participants can register for this tournament',
        }),
        ('Tournament Window', {
            'fields': (
                ('start_at', 'end_at'),
                'tournament_status_display',
            ),
            'description': 'When the tournament actually runs',
        }),
        ('Check-in Settings', {
            'fields': (
                ('check_in_open_mins', 'check_in_close_mins'),
                'check_in_window_display',
            ),
            'description': 'Check-in window relative to tournament start time',
        }),
    )
    
    readonly_fields = (
        'registration_status_display',
        'tournament_status_display',
        'check_in_window_display',
    )
    
    def registration_status_display(self, obj):
        """Display human-readable registration status."""
        if not obj or not obj.pk:
            return '-'
        
        status = obj.registration_status
        if 'Open' in status:
            color = 'green'
            icon = '✓'
        elif 'Closed' in status:
            color = 'red'
            icon = '✗'
        else:
            color = 'orange'
            icon = '⧗'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, status
        )
    registration_status_display.short_description = 'Current Status'
    
    def tournament_status_display(self, obj):
        """Display human-readable tournament status."""
        if not obj or not obj.pk:
            return '-'
        
        status = obj.tournament_status
        if 'Live' in status:
            color = 'green'
            icon = '●'
        elif 'Completed' in status:
            color = 'gray'
            icon = '✓'
        else:
            color = 'orange'
            icon = '⧗'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, status
        )
    tournament_status_display.short_description = 'Current Status'
    
    def check_in_window_display(self, obj):
        """Display formatted check-in window."""
        if not obj or not obj.pk:
            return '-'
        return obj.check_in_window_text
    check_in_window_display.short_description = 'Check-in Window'
    
    def has_add_permission(self, request, obj=None):
        """Only allow one schedule per tournament."""
        if obj and hasattr(obj, 'schedule'):
            return False
        return super().has_add_permission(request, obj)
