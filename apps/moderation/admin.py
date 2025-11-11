"""
Django Admin for Moderation App
"""
from django.contrib import admin
from apps.moderation.models import ModerationSanction, ModerationAudit, AbuseReport


@admin.register(ModerationSanction)
class ModerationSanctionAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject_profile_id', 'type', 'scope', 'scope_id', 'starts_at', 'ends_at', 'revoked_at', 'created_at']
    list_filter = ['type', 'scope', 'revoked_at']
    search_fields = ['subject_profile_id', 'reason_code']
    readonly_fields = ['created_at', 'revoked_at']
    date_hierarchy = 'created_at'


@admin.register(ModerationAudit)
class ModerationAuditAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'actor_id', 'subject_profile_id', 'ref_type', 'ref_id', 'created_at']
    list_filter = ['event', 'ref_type']
    search_fields = ['actor_id', 'subject_profile_id', 'ref_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        # Audit trail is append-only via service layer
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Never delete audit records
        return False


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter_profile_id', 'category', 'ref_type', 'ref_id', 'state', 'priority', 'created_at']
    list_filter = ['state', 'category', 'priority']
    search_fields = ['reporter_profile_id', 'subject_profile_id', 'ref_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
