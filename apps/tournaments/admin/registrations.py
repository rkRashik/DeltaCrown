# apps/tournaments/admin/registrations.py
"""
Django Admin for Registration and RegistrationRequest models
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages

from ..models import Registration, RegistrationRequest


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    """Admin interface for tournament registrations"""
    
    list_display = (
        'id',
        'tournament_name',
        'participant_name',
        'participant_type',
        'status_badge',
        'payment_status_badge',
        'created_at',
    )
    
    list_filter = (
        'status',
        'payment_status',
        'tournament',
        'created_at',
    )
    
    search_fields = (
        'tournament__name',
        'user__display_name',
        'user__user__username',
        'team__name',
        'team__tag',
        'payment_reference',
    )
    
    readonly_fields = (
        'created_at',
        'payment_verified_at',
        'payment_verified_by',
    )
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Participant', {
            'fields': ('user', 'team'),
            'description': 'Either user (solo) OR team must be set, not both.'
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Payment Information', {
            'fields': (
                'payment_method',
                'payment_sender',
                'payment_reference',
                'payment_status',
            )
        }),
        ('Verification', {
            'fields': (
                'payment_verified_by',
                'payment_verified_at',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_payments', 'confirm_registrations', 'cancel_registrations']
    
    # ========== Display Methods ==========
    
    def tournament_name(self, obj):
        """Display tournament name"""
        if obj.tournament:
            return obj.tournament.name
        return '-'
    tournament_name.short_description = 'Tournament'
    tournament_name.admin_order_field = 'tournament__name'
    
    def participant_name(self, obj):
        """Display participant (user or team)"""
        if obj.user:
            display_name = getattr(obj.user, 'display_name', None)
            username = getattr(getattr(obj.user, 'user', None), 'username', None)
            return display_name or username or f'User #{obj.user.id}'
        elif obj.team:
            return obj.team.tag or obj.team.name or f'Team #{obj.team.id}'
        return '-'
    participant_name.short_description = 'Participant'
    
    def participant_type(self, obj):
        """Display participant type"""
        if obj.user:
            return '👤 Solo'
        elif obj.team:
            return '👥 Team'
        return '-'
    participant_type.short_description = 'Type'
    
    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            'PENDING': '#fef3c7',  # yellow
            'CONFIRMED': '#d1fae5',  # green
            'CANCELLED': '#fee2e2',  # red
        }
        bg_color = colors.get(obj.status, '#e5e7eb')
        
        text_colors = {
            'PENDING': '#92400e',
            'CONFIRMED': '#065f46',
            'CANCELLED': '#991b1b',
        }
        text_color = text_colors.get(obj.status, '#1f2937')
        
        return format_html(
            '<span style="background:{};color:{};padding:4px 12px;border-radius:9999px;font-weight:500;">{}</span>',
            bg_color,
            text_color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def payment_status_badge(self, obj):
        """Display colored payment status badge"""
        colors = {
            'pending': '#fef3c7',  # yellow
            'verified': '#d1fae5',  # green
            'rejected': '#fee2e2',  # red
        }
        bg_color = colors.get(obj.payment_status, '#e5e7eb')
        
        text_colors = {
            'pending': '#92400e',
            'verified': '#065f46',
            'rejected': '#991b1b',
        }
        text_color = text_colors.get(obj.payment_status, '#1f2937')
        
        return format_html(
            '<span style="background:{};color:{};padding:4px 12px;border-radius:9999px;font-weight:500;">{}</span>',
            bg_color,
            text_color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    payment_status_badge.admin_order_field = 'payment_status'
    
    # ========== Admin Actions ==========
    
    @admin.action(description='✅ Verify selected payments')
    def verify_payments(self, request, queryset):
        """Verify payments for selected registrations"""
        count = 0
        for reg in queryset:
            if reg.payment_status == 'pending':
                reg.payment_status = 'verified'
                reg.payment_verified_by = request.user
                reg.payment_verified_at = timezone.now()
                reg.save()
                count += 1
        
        self.message_user(
            request,
            f'Verified {count} payment(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='✅ Confirm selected registrations')
    def confirm_registrations(self, request, queryset):
        """Confirm selected registrations"""
        count = queryset.filter(status='PENDING').update(status='CONFIRMED')
        self.message_user(
            request,
            f'Confirmed {count} registration(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='❌ Cancel selected registrations')
    def cancel_registrations(self, request, queryset):
        """Cancel selected registrations"""
        count = queryset.exclude(status='CANCELLED').update(status='CANCELLED')
        self.message_user(
            request,
            f'Cancelled {count} registration(s).',
            messages.WARNING
        )


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    """Admin interface for registration requests from non-captain team members"""
    
    list_display = (
        'id',
        'requester_name',
        'tournament_name',
        'team_name',
        'captain_name',
        'status_badge',
        'created_at',
        'expires_at',
    )
    
    list_filter = (
        'status',
        'tournament',
        'created_at',
    )
    
    search_fields = (
        'requester__display_name',
        'requester__user__username',
        'tournament__name',
        'team__name',
        'team__tag',
        'captain__display_name',
        'captain__user__username',
    )
    
    readonly_fields = (
        'created_at',
        'responded_at',
    )
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'requester',
                'tournament',
                'team',
                'captain',
            )
        }),
        ('Request Details', {
            'fields': (
                'message',
                'status',
                'expires_at',
            )
        }),
        ('Response', {
            'fields': (
                'response_message',
                'responded_at',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    # ========== Display Methods ==========
    
    def requester_name(self, obj):
        """Display requester name"""
        if obj.requester:
            return obj.requester.display_name or getattr(obj.requester.user, 'username', f'User #{obj.requester.id}')
        return '-'
    requester_name.short_description = 'Requester'
    
    def tournament_name(self, obj):
        """Display tournament name"""
        if obj.tournament:
            return obj.tournament.name
        return '-'
    tournament_name.short_description = 'Tournament'
    
    def team_name(self, obj):
        """Display team name"""
        if obj.team:
            return obj.team.tag or obj.team.name or f'Team #{obj.team.id}'
        return '-'
    team_name.short_description = 'Team'
    
    def captain_name(self, obj):
        """Display captain name"""
        if obj.captain:
            return obj.captain.display_name or getattr(obj.captain.user, 'username', f'User #{obj.captain.id}')
        return '-'
    captain_name.short_description = 'Captain'
    
    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            'PENDING': '#fef3c7',  # yellow
            'APPROVED': '#d1fae5',  # green
            'REJECTED': '#fee2e2',  # red
            'EXPIRED': '#e5e7eb',  # gray
        }
        bg_color = colors.get(obj.status, '#e5e7eb')
        
        text_colors = {
            'PENDING': '#92400e',
            'APPROVED': '#065f46',
            'REJECTED': '#991b1b',
            'EXPIRED': '#6b7280',
        }
        text_color = text_colors.get(obj.status, '#1f2937')
        
        return format_html(
            '<span style="background:{};color:{};padding:4px 12px;border-radius:9999px;font-weight:500;">{}</span>',
            bg_color,
            text_color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    # ========== Admin Actions ==========
    
    @admin.action(description='✅ Approve selected requests')
    def approve_requests(self, request, queryset):
        """Approve selected registration requests"""
        count = 0
        for req in queryset.filter(status='PENDING'):
            req.status = 'APPROVED'
            req.responded_at = timezone.now()
            req.response_message = f'Approved by admin: {request.user.username}'
            req.save()
            count += 1
        
        self.message_user(
            request,
            f'Approved {count} request(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='❌ Reject selected requests')
    def reject_requests(self, request, queryset):
        """Reject selected registration requests"""
        count = 0
        for req in queryset.filter(status='PENDING'):
            req.status = 'REJECTED'
            req.responded_at = timezone.now()
            req.response_message = f'Rejected by admin: {request.user.username}'
            req.save()
            count += 1
        
        self.message_user(
            request,
            f'Rejected {count} request(s).',
            messages.WARNING
        )
