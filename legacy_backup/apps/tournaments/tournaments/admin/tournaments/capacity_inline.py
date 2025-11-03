"""
Admin inline for TournamentCapacity.
Provides a clean inline editor for managing capacity configuration.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.tournaments.models.core import TournamentCapacity


class TournamentCapacityInline(admin.StackedInline):
    """Inline admin for Tournament Capacity and Registration Settings"""
    
    model = TournamentCapacity
    extra = 0
    max_num = 1
    can_delete = False
    
    verbose_name = "👥 Capacity & Registration"
    verbose_name_plural = "👥 Capacity & Registration"
    
    fieldsets = (
        ('Capacity Limits', {
            'fields': (
                ('slot_size', 'max_teams'),
                'capacity_status_display',
            ),
            'description': '🎯 Total slots available and maximum number of teams/participants'
        }),
        ('Team Size Requirements', {
            'fields': (
                ('min_team_size', 'max_team_size'),
            ),
            'description': '👤 Player count per team (e.g., 1 for solo, 5 for Valorant 5v5, 1-11 for eFootball)'
        }),
        ('Registration Settings', {
            'fields': (
                'registration_mode',
                'waitlist_enabled',
            ),
            'description': '⚙️ How teams can register and whether waitlist is enabled'
        }),
        ('Live Statistics', {
            'fields': (
                'current_registrations',
                'registration_progress_display',
            ),
            'description': '📊 Real-time registration tracking (auto-updated)',
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = (
        'capacity_status_display',
        'registration_progress_display',
    )
    
    def capacity_status_display(self, obj):
        """Display current capacity status with color-coded progress bar."""
        if not obj or not obj.pk:
            return format_html('<em style="color:#999;">Not created yet</em>')
        
        # Calculate progress
        progress = obj.registration_progress_percent
        current = obj.current_registrations
        total = obj.slot_size or obj.max_teams or 0
        
        # Color based on capacity
        if obj.is_full:
            color = '#dc3545'  # Red
            status_text = 'FULL'
            bar_color = '#dc3545'
        elif progress >= 90:
            color = '#fd7e14'  # Orange
            status_text = 'Almost Full'
            bar_color = '#fd7e14'
        elif progress >= 75:
            color = '#ffc107'  # Amber
            status_text = 'Filling Up'
            bar_color = '#ffc107'
        elif progress >= 50:
            color = '#17a2b8'  # Cyan
            status_text = 'Half Full'
            bar_color = '#17a2b8'
        elif progress > 0:
            color = '#28a745'  # Green
            status_text = 'Open'
            bar_color = '#28a745'
        else:
            color = '#6c757d'  # Gray
            status_text = 'Empty'
            bar_color = '#e9ecef'
        
        # Progress bar
        progress_bar = f'''
        <div style="margin: 10px 0;">
            <div style="width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; position: relative;">
                <div style="width: {progress}%; height: 100%; background: {bar_color}; transition: width 0.3s;"></div>
                <span style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); 
                             font-size: 11px; font-weight: bold; color: #333;">{progress}%</span>
            </div>
        </div>
        '''
        
        return format_html(
            '<div style="padding: 12px; background: #f8f9fa; border-left: 4px solid {}; border-radius: 4px;">'
            '<div style="margin-bottom: 8px;">'
            '<strong style="color: {}; font-size: 14px;">{}</strong> '
            '<span style="color: #6c757d; font-size: 13px;">({} of {} slots)</span>'
            '</div>'
            '{}'
            '<div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #6c757d;">'
            '<span>📊 {} registrations</span>'
            '<span>🎯 {} slots available</span>'
            '<span>📋 Mode: {}</span>'
            '</div>'
            '</div>',
            color,
            color, status_text, current, total,
            progress_bar,
            current,
            obj.available_slots,
            obj.get_registration_mode_display()
        )
    
    capacity_status_display.short_description = 'Live Capacity Status'
    
    def registration_progress_display(self, obj):
        """Display detailed registration progress."""
        if not obj or not obj.pk:
            return format_html('<em style="color:#999;">No data</em>')
        
        try:
            return format_html(
                '<div style="font-family: monospace; padding: 8px; background: #f8f9fa; border-radius: 4px;">'
                '<div>Current: <strong>{}</strong></div>'
                '<div>Available: <strong>{}</strong></div>'
                '<div>Capacity: <strong>{}</strong></div>'
                '<div>Progress: <strong>{}%</strong></div>'
                '<div>Status: <strong>{}</strong></div>'
                '</div>',
                obj.current_registrations,
                obj.available_slots,
                obj.get_capacity_display(),
                obj.registration_progress_percent,
                'FULL' if obj.is_full else 'OPEN'
            )
        except:
            return format_html('<em style="color:#999;">Error calculating progress</em>')
    
    registration_progress_display.short_description = 'Detailed Progress'
    
    def get_formset(self, request, obj=None, **kwargs):
        """Add help text to formset."""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Add inline help text
        help_texts = {
            'slot_size': 'Total number of participants/teams allowed. Leave blank for unlimited.',
            'max_teams': 'Maximum number of teams (for team tournaments). Usually same as slot_size.',
            'min_team_size': 'Minimum players per team (1 for solo, 2+ for teams).',
            'max_team_size': 'Maximum players per team (5 for Valorant, 11 for eFootball, etc.).',
            'registration_mode': 'Controls how teams can register.',
            'waitlist_enabled': 'Allow teams to join waitlist when tournament is full.',
        }
        
        for field, text in help_texts.items():
            if field in formset.form.base_fields:
                formset.form.base_fields[field].help_text = text
        
        return formset
    
    def has_add_permission(self, request, obj=None):
        """Only allow one capacity record per tournament."""
        if obj and hasattr(obj, 'capacity'):
            return False
        return super().has_add_permission(request, obj)
