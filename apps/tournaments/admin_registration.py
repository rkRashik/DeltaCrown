"""
Django admin interfaces for Tournament Registration and Payment models.

âš ï¸ LEGACY: This Django admin customization is DEPRECATED as of Phase 7, Epic 7.6.
The new Smart Registration System (Phase 5) and Organizer Console (Phase 7) provide superior UX.

This file is retained ONLY for:
1. Emergency administrative access (super admin use only)
2. Backward compatibility
3. Data inspection/debugging (not end-user workflows)

SCHEDULED FOR REMOVAL: Phase 8+
REPLACEMENT: Smart Registration UI (Phase 5) + Organizer Console (Phase 7)

Source Documents:
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Admin UI for payment verification)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration & Payment Models)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Django admin customization)

Provides admin customization for:
- Registration: Participant registration management with status filtering
- Payment: Payment verification and refund management
- Inline Payment within Registration admin

Architecture Decisions:
- ADR-001: Service Layer - Payment verification uses RegistrationService
- ADR-003: Soft Delete - Deleted registrations visible with filter
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import display
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from apps.tournaments.models import Registration, Payment
from apps.tournaments.services import RegistrationService


class PaymentInline(StackedInline):
    """
    Inline editor for Payment within Registration admin.
    
    Allows admins to view and verify payments directly in registration edit page.
    """
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = [
        'payment_method', 'amount', 'transaction_id', 'payment_proof_display',
        'status', 'submitted_at', 'verified_by', 'verified_at', 'admin_notes'
    ]
    fields = [
        'payment_method', 'amount', 'transaction_id', 'payment_proof_display',
        'status', 'admin_notes', 'verified_by', 'verified_at', 'submitted_at'
    ]
    
    def payment_proof_display(self, obj):
        """Display payment proof file if available (Module 3.2)."""
        if not obj.payment_proof:
            return format_html('<span style="color: gray;">No proof uploaded</span>')
        
        try:
            file_url = obj.payment_proof.url
            
            if obj.file_type == 'PDF':
                return format_html(
                    '<a href="{}" target="_blank">ðŸ“„ View PDF</a>',
                    file_url
                )
            else:  # IMAGE
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width:200px; border: 1px solid #ddd;"/>'
                    '</a>',
                    file_url,
                    file_url
                )
        except ValueError:
            return format_html('<span style="color: red;">File not found</span>')
    payment_proof_display.short_description = "Payment Proof"
    
    def has_add_permission(self, request, obj=None):
        """Payments are created through registration flow, not admin."""
        return False


@admin.register(Registration)
class RegistrationAdmin(ModelAdmin):
    """
    Admin interface for Registration model.
    
    Comprehensive registration management with filtering, search, and payment inline.
    """
    list_display = [
        'id', 'team_name_display', 'captain_display', 'status', 'tournament', 'registered_at',
        'has_payment', 'payment_status_display', 'transaction_id_display', 'slot_number', 'seed'
    ]
    list_filter = [
        'status', 'checked_in', 'tournament__status', 'tournament__game',
        'is_deleted', 'registered_at'
    ]
    search_fields = [
        'tournament__name', 'user__username', 'user__email',
        'registration_data__game_id', 'registration_data__phone'
    ]
    readonly_fields = [
        'tournament', 'user', 'team_id', 'registered_at', 'created_at', 'updated_at',
        'deleted_at', 'deleted_by', 'participant_identifier', 'has_payment',
        'is_confirmed', 'is_pending_payment'
    ]
    inlines = [PaymentInline]
    
    fieldsets = (
        ('Registration Information', {
            'fields': (
                'tournament', 'user', 'team_id', 'participant_identifier',
                'status', 'registered_at'
            )
        }),
        ('Registration Data (JSONB)', {
            'fields': ('registration_data',),
            'description': 'Structured data including game ID, contact info, and custom fields'
        }),
        ('Check-In', {
            'fields': ('checked_in', 'checked_in_at')
        }),
        ('Bracket Position', {
            'fields': ('slot_number', 'seed'),
            'description': 'Bracket slot and seeding assignment'
        }),
        ('Status Indicators (Read Only)', {
            'fields': ('has_payment', 'is_confirmed', 'is_pending_payment'),
            'classes': ('collapse',)
        }),
        ('Soft Delete (Read Only)', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps (Read Only)', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['bulk_confirm_registrations', 'bulk_reject_registrations', 'bulk_cancel_registrations', 'export_registrations_csv']
    
    def get_queryset(self, request):
        """Include soft-deleted registrations in admin."""
        # Use objects manager which includes soft-deleted items in admin
        return Registration.objects.select_related(
            'tournament', 'user', 'deleted_by'
        ).prefetch_related('payment')
    
    list_per_page = 25

    def participant_display(self, obj):
        """Display participant name (user or team)."""
        return obj.participant_identifier
    participant_display.short_description = "Participant"
    participant_display.admin_order_field = 'user__username'
    
    def team_name_display(self, obj):
        """Display team name if it's a team registration."""
        if obj.team_id:
            # Read from cached prefetch (registration_data JSON) to avoid per-row queries
            data = obj.registration_data or {}
            team_name = data.get('team_name') or data.get('team', {}).get('name') if isinstance(data, dict) else None
            if team_name:
                return team_name
            # Fallback: the team_id reference
            return f"Team #{obj.team_id}"
        return "-"
    team_name_display.short_description = "Team Name"
    
    def captain_display(self, obj):
        """Display captain name from registration_data to avoid per-row queries."""
        if obj.team_id:
            data = obj.registration_data or {}
            if isinstance(data, dict):
                captain_name = data.get('captain_name') or data.get('captain', {}).get('name') or data.get('captain_username')
                if captain_name:
                    return captain_name
            # Fallback to the registering user
            return obj.user.username if obj.user_id else "-"
        return "-"
    captain_display.short_description = "Captain"
    
    def payment_status_display(self, obj):
        """Display payment status with color coding."""
        if not obj.has_payment:
            return format_html(
                '<span style="color: gray;">No Payment</span>'
            )
        
        payment = obj.payment
        color_map = {
            'pending': 'gray',
            'submitted': 'orange',
            'verified': 'green',
            'rejected': 'red',
            'refunded': 'blue'
        }
        color = color_map.get(payment.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            payment.get_status_display()
        )
    payment_status_display.short_description = "Payment Status"
    
    def transaction_id_display(self, obj):
        """Display transaction ID if payment exists."""
        if obj.has_payment:
            return obj.payment.transaction_id or "-"
        return "-"
    transaction_id_display.short_description = "Trnx ID"
    
    def bulk_confirm_registrations(self, request, queryset):
        """
        Bulk action to confirm multiple registrations (admin only).
        
        Only confirms registrations with verified payments.
        """
        confirmed_count = 0
        for registration in queryset:
            if registration.has_payment and registration.payment.is_verified:
                if registration.status != Registration.CONFIRMED:
                    registration.status = Registration.CONFIRMED
                    registration.save(update_fields=['status'])
                    confirmed_count += 1
        
        self.message_user(
            request,
            f"Successfully confirmed {confirmed_count} registration(s) with verified payments."
        )
    bulk_confirm_registrations.short_description = "Confirm selected registrations (with verified payments)"
    
    def bulk_cancel_registrations(self, request, queryset):
        """
        Bulk action to cancel multiple registrations.
        
        Uses RegistrationService to properly handle cancellation and refunds.
        """
        cancelled_count = 0
        for registration in queryset:
            try:
                RegistrationService.cancel_registration(
                    registration_id=registration.id,
                    user=request.user,
                    reason=f"Bulk cancellation by {request.user.username}"
                )
                cancelled_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to cancel registration {registration.id}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f"Successfully cancelled {cancelled_count} registration(s)."
        )
    bulk_cancel_registrations.short_description = "Cancel selected registrations"

    def bulk_reject_registrations(self, request, queryset):
        """Bulk reject registrations (e.g. ineligible, duplicate, fraudulent)."""
        rejected_count = 0
        for registration in queryset.exclude(status__in=[Registration.CONFIRMED, 'cancelled']):
            registration.status = 'rejected'
            registration.save(update_fields=['status'])
            rejected_count += 1
        self.message_user(request, f"Rejected {rejected_count} registration(s).")
    bulk_reject_registrations.short_description = "Reject selected registrations"

    def export_registrations_csv(self, request, queryset):
        """Export selected registrations as a CSV download."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="registrations_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Tournament', 'Username', 'Email', 'Team ID',
            'Status', 'Game ID', 'Phone', 'Registered At',
        ])
        for reg in queryset.select_related('tournament', 'user'):
            data = reg.registration_data or {}
            writer.writerow([
                reg.id,
                str(reg.tournament) if reg.tournament else '',
                reg.user.username if reg.user_id else '',
                reg.user.email if reg.user_id else '',
                reg.team_id or '',
                reg.status,
                data.get('game_id', ''),
                data.get('phone', ''),
                reg.registered_at.strftime('%Y-%m-%d %H:%M') if reg.registered_at else '',
            ])
        return response
    export_registrations_csv.short_description = "Export selected as CSV"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    """
    Admin interface for Payment model.
    
    Payment verification and refund management with detailed filtering.
    """
    list_per_page = 25
    list_display = [
        'id', 'registration_participant', 'tournament_display', 'payment_method',
        'amount', 'reference_number', 'status_display', 'submitted_at', 'verified_by', 'verified_at'
    ]
    list_filter = [
        'status', 'payment_method', 'submitted_at', 'verified_at',
        'registration__tournament__status'
    ]
    search_fields = [
        'registration__tournament__name', 'registration__user__username',
        'transaction_id', 'admin_notes'
    ]
    readonly_fields = [
        'registration', 'payment_method', 'amount', 'transaction_id', 'reference_number',
        'payment_proof_display', 'file_type', 'submitted_at', 'updated_at',
        'is_verified', 'is_pending_verification', 'can_be_verified'
    ]
    
    fieldsets = (
        ('Registration', {
            'fields': ('registration',)
        }),
        ('Payment Information', {
            'fields': (
                'payment_method', 'amount', 'transaction_id', 'reference_number',
                'payment_proof_display', 'payment_proof', 'file_type'
            )
        }),
        ('Verification', {
            'fields': (
                'status', 'admin_notes', 'verified_by', 'verified_at',
                'can_be_verified'
            )
        }),
        ('Status Indicators (Read Only)', {
            'fields': ('is_verified', 'is_pending_verification'),
            'classes': ('collapse',)
        }),
        ('Timestamps (Read Only)', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_payments', 'reject_payments', 'refund_payments']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return Payment.objects.select_related(
            'registration__tournament', 'registration__user', 'verified_by'
        )
    
    def registration_participant(self, obj):
        """Display registration participant."""
        return obj.registration.participant_identifier
    registration_participant.short_description = "Participant"
    
    def tournament_display(self, obj):
        """Display tournament name with link."""
        url = reverse('admin:tournaments_tournament_change', args=[obj.registration.tournament.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.registration.tournament.name
        )
    tournament_display.short_description = "Tournament"
    tournament_display.admin_order_field = 'registration__tournament__name'
    
    @display(
        description='Status',
        ordering='status',
        label={
            'pending': 'warning',
            'submitted': 'warning',
            'verified': 'success',
            'rejected': 'danger',
            'refunded': 'info',
        },
    )
    def status_display(self, obj):
        """Display payment status with Unfold color badge."""
        return obj.status
    
    def payment_proof_display(self, obj):
        """Display payment proof file if available (Module 3.2: enhanced with file type handling)."""
        if not obj.payment_proof:
            return format_html('<span style="color: gray;">No proof uploaded</span>')
        
        try:
            file_url = obj.payment_proof.url
            
            # Display based on file type
            if obj.file_type == 'PDF':
                return format_html(
                    '<a href="{}" target="_blank" class="button">'
                    '<svg width="16" height="16" style="vertical-align: middle; margin-right: 4px;"><use href="#icon-pdf"/></svg>'
                    'View PDF Document'
                    '</a>',
                    file_url
                )
            else:  # IMAGE
                return format_html(
                    '<a href="{}" target="_blank" data-lightbox="payment-proof">'
                    '<img src="{}" style="max-width:400px; max-height:400px; border: 1px solid #ddd; border-radius: 4px;"/>'
                    '</a>'
                    '<br><small style="color: #666;">Click to view full size</small>',
                    file_url,
                    file_url
                )
        except ValueError:
            return format_html('<span style="color: red;">File not found</span>')
    payment_proof_display.short_description = "Payment Proof"
    
    def verify_payments(self, request, queryset):
        """
        Bulk action to verify multiple payments.
        
        Uses RegistrationService to properly handle verification.
        """
        verified_count = 0
        for payment in queryset.filter(status=Payment.SUBMITTED):
            try:
                RegistrationService.verify_payment(
                    payment_id=payment.id,
                    verified_by=request.user,
                    admin_notes=f"Bulk verification by {request.user.username}"
                )
                verified_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to verify payment {payment.id}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f"Successfully verified {verified_count} payment(s)."
        )
    verify_payments.short_description = "Verify selected payments"
    
    def reject_payments(self, request, queryset):
        """
        Bulk action to reject multiple payments.
        
        Uses RegistrationService to properly handle rejection.
        """
        rejected_count = 0
        for payment in queryset.filter(status=Payment.SUBMITTED):
            try:
                RegistrationService.reject_payment(
                    payment_id=payment.id,
                    rejected_by=request.user,
                    reason=f"Bulk rejection by {request.user.username}"
                )
                rejected_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to reject payment {payment.id}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f"Successfully rejected {rejected_count} payment(s)."
        )
    reject_payments.short_description = "Reject selected payments"
    
    def refund_payments(self, request, queryset):
        """
        Bulk action to refund multiple payments.
        
        Uses RegistrationService to properly handle refunds.
        """
        refunded_count = 0
        for payment in queryset.filter(status=Payment.VERIFIED):
            try:
                RegistrationService.refund_payment(
                    payment_id=payment.id,
                    refunded_by=request.user,
                    reason=f"Bulk refund by {request.user.username}"
                )
                refunded_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to refund payment {payment.id}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f"Successfully refunded {refunded_count} payment(s)."
        )
    refund_payments.short_description = "Refund selected payments"
    
    def has_add_permission(self, request):
        """Payments are created through registration flow, not admin."""
        return False
