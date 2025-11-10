"""
Certificate Admin Interface

Module 5.3: Certificates & Achievement Proofs

Implements:
- PHASE_5_IMPLEMENTATION_PLAN.md#module-53-certificates--achievement-proofs (admin interface)
- 01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer-pattern (view-only admin)

This admin interface provides read-only access to certificate records.
Certificates are generated programmatically by CertificateService; admins can
view the audit trail but cannot manually create/edit/delete certificates through
the admin interface (except for revocation).

Security:
    View-only for certificate data. Mutations must go through CertificateService
    to ensure proper hash calculation, QR code generation, and file storage.
    Revocation is allowed via admin action for disputed results.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """
    View-only admin interface for certificate audit trail.
    
    Certificates are generated programmatically via CertificateService.
    This interface provides visibility for organizers and admins to:
    - Monitor certificate generation status
    - Track downloads and usage
    - Verify certificate authenticity
    - Revoke certificates for disputed results
    """
    
    # List Display
    list_display = [
        'id',
        'tournament_link',
        'participant_name_display',
        'certificate_type_badge',
        'placement',
        'generated_at',
        'download_count',
        'revoked_status',
        'verification_link',
    ]
    
    # Filters
    list_filter = [
        'certificate_type',
        'revoked_at',
        'generated_at',
    ]
    
    # Search
    search_fields = [
        'tournament__title',
        'tournament__slug',
        'participant__user__username',
        'participant__user__first_name',
        'participant__user__last_name',
        'verification_code',
    ]
    
    # Read-only fields (all fields except revocation)
    readonly_fields = [
        'id',
        'tournament',
        'participant',
        'certificate_type',
        'placement',
        'file_pdf_link',
        'file_image_link',
        'verification_code',
        'verification_url_display',
        'certificate_hash',
        'generated_at',
        'downloaded_at',
        'download_count',
        'revoked_at',
        'revoked_reason',
        'created_at',
        'updated_at',
    ]
    
    # Fieldsets
    fieldsets = (
        ('Certificate Details', {
            'fields': (
                'id',
                'tournament',
                'participant',
                'certificate_type',
                'placement',
            )
        }),
        ('Files', {
            'fields': (
                'file_pdf_link',
                'file_image_link',
            ),
            'description': 'Generated certificate files (PDF + PNG)'
        }),
        ('Verification', {
            'fields': (
                'verification_code',
                'verification_url_display',
                'certificate_hash',
            ),
            'description': 'QR code verification and tamper detection (SHA-256)'
        }),
        ('Usage Tracking', {
            'fields': (
                'download_count',
                'downloaded_at',
            )
        }),
        ('Revocation', {
            'fields': (
                'revoked_at',
                'revoked_reason',
            ),
            'classes': ('collapse',),
            'description': 'Revoke certificate if result is disputed or changed'
        }),
        ('Timestamps', {
            'fields': (
                'generated_at',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Ordering
    ordering = ['-generated_at', '-id']
    
    # Pagination
    list_per_page = 50
    
    # Permissions: View-only (no add/change/delete)
    def has_add_permission(self, request):
        """Disable add - certificates created by CertificateService only."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable edit - certificates are immutable audit records."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable delete - certificates are immutable audit records (use revocation)."""
        return False
    
    # Custom Display Methods
    
    def tournament_link(self, obj):
        """Link to tournament admin page."""
        if obj.tournament:
            url = f'/admin/tournaments/tournament/{obj.tournament.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
        return '-'
    tournament_link.short_description = 'Tournament'
    
    def participant_name_display(self, obj):
        """Display participant name (from Registration)."""
        return obj.get_participant_display_name()
    participant_name_display.short_description = 'Participant'
    participant_name_display.admin_order_field = 'participant__user__username'
    
    def certificate_type_badge(self, obj):
        """Display certificate type with color badge."""
        colors = {
            'winner': '#FFD700',       # Gold
            'runner_up': '#C0C0C0',    # Silver
            'third_place': '#CD7F32',  # Bronze
            'participant': '#6C757D',  # Gray
        }
        color = colors.get(obj.certificate_type, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_certificate_type_display()
        )
    certificate_type_badge.short_description = 'Type'
    certificate_type_badge.admin_order_field = 'certificate_type'
    
    def revoked_status(self, obj):
        """Display revocation status with icon."""
        if obj.is_revoked:
            return format_html(
                '<span style="color: #DC3545; font-weight: bold;">✗ REVOKED</span>'
            )
        return format_html(
            '<span style="color: #28A745;">✓ Active</span>'
        )
    revoked_status.short_description = 'Status'
    revoked_status.admin_order_field = 'revoked_at'
    
    def verification_link(self, obj):
        """Link to public verification endpoint."""
        url = obj.verification_url
        return format_html(
            '<a href="{}" target="_blank">Verify</a>',
            url
        )
    verification_link.short_description = 'Verify'
    
    def file_pdf_link(self, obj):
        """Link to download PDF file."""
        if obj.file_pdf:
            try:
                url = obj.file_pdf.url
                size_kb = obj.file_pdf.size / 1024
                return format_html(
                    '<a href="{}" target="_blank">Download PDF ({:.1f} KB)</a>',
                    url,
                    size_kb
                )
            except (ValueError, OSError):
                return 'File missing'
        return '-'
    file_pdf_link.short_description = 'PDF File'
    
    def file_image_link(self, obj):
        """Link to download image file with thumbnail."""
        if obj.file_image:
            try:
                url = obj.file_image.url
                size_kb = obj.file_image.size / 1024
                return format_html(
                    '<a href="{}" target="_blank"><img src="{}" style="max-width: 100px; max-height: 50px;"/> ({:.1f} KB)</a>',
                    url,
                    url,
                    size_kb
                )
            except (ValueError, OSError):
                return 'File missing'
        return '-'
    file_image_link.short_description = 'Image File'
    
    def verification_url_display(self, obj):
        """Display clickable verification URL."""
        url = obj.verification_url
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            url
        )
    verification_url_display.short_description = 'Verification URL'
    
    # Admin Actions
    
    actions = ['revoke_certificates']
    
    def revoke_certificates(self, request, queryset):
        """
        Admin action to revoke selected certificates.
        
        Use case: Result disputed and changed, certificate needs regeneration.
        """
        count = 0
        for certificate in queryset.filter(revoked_at__isnull=True):
            certificate.revoke(reason='Revoked by admin via bulk action')
            count += 1
        
        self.message_user(
            request,
            f'{count} certificate(s) revoked successfully. Regenerate new certificates via CertificateService.'
        )
    revoke_certificates.short_description = 'Revoke selected certificates'
