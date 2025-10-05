# apps/tournaments/admin/tournaments/schedule_inline.py
"""
Admin inline for TournamentSchedule model.
Handles all date/time related tournament fields.
"""
from django.contrib import admin
from django.utils.html import format_html
from apps.tournaments.models import TournamentSchedule


class TournamentScheduleInline(admin.StackedInline):
    """
    Inline admin for managing tournament schedule.
    Displays all schedule-related fields with real-time status indicators.
    """
    model = TournamentSchedule
    can_delete = False
    extra = 0
    max_num = 1
    
    verbose_name = "📅 Schedule & Timeline"
    verbose_name_plural = "📅 Schedule & Timeline"
    
    fieldsets = (
        ('Registration Period', {
            'fields': (
                ('reg_open_at', 'reg_close_at'),
                'registration_status_display',
            ),
            'description': '🕒 When participants can register for this tournament',
        }),
        ('Tournament Duration', {
            'fields': (
                ('start_at', 'end_at'),
                'tournament_status_display',
            ),
            'description': '🎮 When the tournament actually runs',
        }),
        ('Check-in Window', {
            'fields': (
                ('check_in_open_mins', 'check_in_close_mins'),
                'check_in_window_display',
            ),
            'description': '✅ Check-in window relative to tournament start time (e.g., open 30 mins before, close at start)',
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = (
        'registration_status_display',
        'tournament_status_display',
        'check_in_window_display',
    )
    
    def registration_status_display(self, obj):
        """Display human-readable registration status with color coding."""
        if not obj or not obj.pk:
            return format_html('<em style="color:#999;">Not configured yet</em>')
        
        status = obj.registration_status
        
        # Color and icon based on status
        if 'Open' in status or 'open' in status:
            color = '#28a745'  # Green
            icon = '✓'
            bg = '#d4edda'
        elif 'Closed' in status or 'closed' in status:
            color = '#dc3545'  # Red
            icon = '✗'
            bg = '#f8d7da'
        elif 'Not Started' in status:
            color = '#6c757d'  # Gray
            icon = '⧗'
            bg = '#e2e3e5'
        else:
            color = '#ffc107'  # Amber
            icon = '⧗'
            bg = '#fff3cd'
        
        return format_html(
            '<div style="padding: 8px 12px; background: {}; border-left: 4px solid {}; border-radius: 4px;">'
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span> '
            '<strong style="color: {};">{}</strong>'
            '</div>',
            bg, color, color, icon, color, status
        )
    registration_status_display.short_description = 'Current Status'
    
    def tournament_status_display(self, obj):
        """Display human-readable tournament status with color coding."""
        if not obj or not obj.pk:
            return format_html('<em style="color:#999;">Not configured yet</em>')
        
        status = obj.tournament_status
        
        # Color and icon based on status
        if 'Live' in status or 'Running' in status:
            color = '#28a745'  # Green
            icon = '●'
            bg = '#d4edda'
        elif 'Completed' in status or 'Ended' in status:
            color = '#6c757d'  # Gray
            icon = '✓'
            bg = '#e2e3e5'
        elif 'Not Started' in status or 'Upcoming' in status:
            color = '#0d6efd'  # Blue
            icon = '⧗'
            bg = '#cfe2ff'
        else:
            color = '#ffc107'  # Amber
            icon = '⧗'
            bg = '#fff3cd'
        
        return format_html(
            '<div style="padding: 8px 12px; background: {}; border-left: 4px solid {}; border-radius: 4px;">'
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span> '
            '<strong style="color: {};">{}</strong>'
            '</div>',
            bg, color, color, icon, color, status
        )
    tournament_status_display.short_description = 'Current Status'
    
    def check_in_window_display(self, obj):
        """Display formatted check-in window."""
        if not obj or not obj.pk:
            return format_html('<em style="color:#999;">Not configured</em>')
        
        try:
            text = obj.check_in_window_text
            return format_html(
                '<div style="padding: 6px 10px; background: #f8f9fa; border-radius: 4px; font-family: monospace;">'
                '{}'
                '</div>',
                text
            )
        except:
            return format_html('<em style="color:#999;">Error calculating window</em>')
    
    check_in_window_display.short_description = 'Check-in Window'
    
    def has_add_permission(self, request, obj=None):
        """Only allow one schedule per tournament."""
        if obj and hasattr(obj, 'schedule'):
            return False
        return super().has_add_permission(request, obj)
