"""
Django admin interfaces for Tournament Registration and Payment models.

Source Documents:
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Admin UI for payment verification)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration & Payment Models)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (Django admin customization)

Provides admin customization for:
- Registration: Participant registration management with status filtering
- Payment: Payment verification and refund management
- Inline Payment within Registration admin

Architecture Decisions:
- ADR-001: Service Layer - Payment verification uses RegistrationService
- ADR-003: Soft Delete - Deleted registrations visible with filter
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from apps.tournaments.models import Registration, Payment
from apps.tournaments.services import RegistrationService


class PaymentInline(admin.StackedInline):
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
        """Display payment proof image if available."""
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width:200px;"/></a>',
                obj.payment_proof,
                obj.payment_proof
            )
        return "No proof uploaded"
    payment_proof_display.short_description = "Payment Proof"
    
    def has_add_permission(self, request, obj=None):
        """Payments are created through registration flow, not admin."""
        return False


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    """
    Admin interface for Registration model.
    
    Comprehensive registration management with filtering, search, and payment inline.
    """
    list_display = [
        'id', 'participant_display', 'tournament', 'status', 'registered_at',
        'has_payment', 'payment_status_display', 'checked_in', 'slot_number', 'seed'
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
    
    actions = ['bulk_confirm_registrations', 'bulk_cancel_registrations']
    
    def get_queryset(self, request):
        """Include soft-deleted registrations in admin."""
        # Use objects manager which includes soft-deleted items in admin
        return Registration.objects.select_related(
            'tournament', 'user', 'deleted_by'
        ).prefetch_related('payment')
    
    def participant_display(self, obj):
        """Display participant name (user or team)."""
        return obj.participant_identifier
    participant_display.short_description = "Participant"
    participant_display.admin_order_field = 'user__username'
    
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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin interface for Payment model.
    
    Payment verification and refund management with detailed filtering.
    """
    list_display = [
        'id', 'registration_participant', 'tournament_display', 'payment_method',
        'amount', 'status_display', 'submitted_at', 'verified_by', 'verified_at'
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
        'registration', 'payment_method', 'amount', 'transaction_id',
        'payment_proof_display', 'submitted_at', 'updated_at',
        'is_verified', 'is_pending_verification', 'can_be_verified'
    ]
    
    fieldsets = (
        ('Registration', {
            'fields': ('registration',)
        }),
        ('Payment Information', {
            'fields': (
                'payment_method', 'amount', 'transaction_id',
                'payment_proof_display', 'payment_proof'
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
    
    def status_display(self, obj):
        """Display payment status with color coding."""
        color_map = {
            'pending': 'gray',
            'submitted': 'orange',
            'verified': 'green',
            'rejected': 'red',
            'refunded': 'blue'
        }
        color = color_map.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def payment_proof_display(self, obj):
        """Display payment proof image if available."""
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:400px; max-height:400px;"/>'
                '</a>',
                obj.payment_proof,
                obj.payment_proof
            )
        return "No proof uploaded"
    payment_proof_display.short_description = "Payment Proof Image"
    
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
