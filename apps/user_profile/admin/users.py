# apps/user_profile/admin/users.py
"""User Profile Admin - MAIN Configuration.

⚠️ IMPORTANT: This file contains the OFFICIAL UserProfile admin registration.
DO NOT register UserProfile in apps/user_profile/admin.py to avoid conflicts.

All UserProfile fieldsets, list_display, filters, and customizations should be done here.

Admin URL: http://127.0.0.1:8000/admin/user_profile/userprofile/

Recent additions (2026-01-08):
- whatsapp: Separate WhatsApp number field
- secondary_email: Public/contact email (separate from account email)  
- secondary_email_verified: OTP verification status (readonly)
- preferred_contact_method: User's preferred way to be contacted
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone

from ..models import (
    UserProfile,
    SocialLink,
    PrivacySettings,
    KYCSubmission,
    Badge,
    UserBadge,
    # UP-M2 models
    UserActivity,
    UserProfileStats,
    # UP-M5 models
    UserAuditEvent,
    # P0 Feature Models
    StreamConfig,
    HighlightClip,
    PinnedHighlight,
    HardwareGear,
    GameConfig,
    ProfileShowcase,
    ProfileAboutItem,
    TrophyShowcaseConfig,
    SkillEndorsement,
    EndorsementOpportunity,
    Bounty,
    BountyAcceptance,
    BountyProof,
    BountyDispute,
)
from ..services.audit import AuditService
from ..services.tournament_stats import TournamentStatsService
from ..services.economy_sync import sync_profile_by_user_id, get_balance_drift
from .exports import export_userprofiles_csv


# ==============================================================================
# INLINE ADMINS - For Child/Technical Models
# ==============================================================================

class PinnedHighlightInline(admin.TabularInline):
    """Inline for users who pinned this clip."""
    model = PinnedHighlight
    extra = 0
    readonly_fields = ['user', 'pinned_at']
    fields = ['user', 'pinned_at']
    can_delete = False
    verbose_name = "Pinned By User"
    verbose_name_plural = "Users Who Pinned This Clip"
    
    def has_add_permission(self, request, obj=None):
        return False


class BountyAcceptanceInline(admin.TabularInline):
    """Inline for bounty acceptance record."""
    model = BountyAcceptance
    extra = 0
    readonly_fields = ['acceptor', 'accepted_at', 'ip_address', 'user_agent']
    fields = ['acceptor', 'accepted_at', 'ip_address']
    can_delete = False
    max_num = 1
    verbose_name = "Acceptance Record"
    verbose_name_plural = "Acceptance History"
    
    def has_add_permission(self, request, obj=None):
        return False


class BountyProofInline(admin.TabularInline):
    """Inline for proof submissions."""
    model = BountyProof
    extra = 0
    readonly_fields = ['submitted_by', 'claimed_winner', 'submitted_at']
    fields = ['submitted_by', 'claimed_winner', 'proof_type', 'proof_url', 'submitted_at']
    can_delete = False
    verbose_name = "Proof Submission"
    verbose_name_plural = "Proof Submissions"
    
    def has_add_permission(self, request, obj=None):
        return False


class BountyDisputeInline(admin.StackedInline):
    """Inline for dispute (if any)."""
    model = BountyDispute
    extra = 0
    readonly_fields = ['disputer', 'created_at', 'resolved_at']
    fields = ['disputer', 'reason', 'status', 'assigned_moderator', 'resolution', 'created_at', 'resolved_at']
    can_delete = False
    max_num = 1
    verbose_name = "Dispute"
    verbose_name_plural = "Dispute (if exists)"
    
    def has_add_permission(self, request, obj=None):
        return False


# UP.2 FIX PASS #4: SocialLink inline for UserProfile admin
class SocialLinkInline(admin.TabularInline):
    """Inline social links editor for Discord Link + other platforms"""
    model = SocialLink
    extra = 0
    fields = ['platform', 'url', 'handle', 'is_verified']
    readonly_fields = ['is_verified']
    verbose_name = "Social Link"
    verbose_name_plural = "Social Links (Discord, Twitter, YouTube, etc.)"


# ==============================================================================
# PRIMARY MODEL ADMINS
# ==============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "public_id", "kyc_status_badge", "coin_balance", "created_at")
    search_fields = ("user__username", "display_name", "user__email", "phone", "real_full_name", "public_id")
    list_filter = ("kyc_status", "region", "gender", "created_at")
    date_hierarchy = "created_at"
    actions = [export_userprofiles_csv]

    # UX + perf
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    
    readonly_fields = (
        "uuid", "slug", "public_id", "created_at", "updated_at", "kyc_verified_at",
        "secondary_email_verified",  # Only system can verify via OTP
        "deltacoin_balance",  # UP-PHASE11: Economy-owned (read-only)
        "lifetime_earnings",  # UP-PHASE11: Economy-owned (read-only)
        "social_links_summary",  # HOTFIX (Post-C2): Read-only display
        "edit_social_links_link",  # HOTFIX (Post-C2): Quick link to User admin
    )
    
    # UP.3 EXTENSION: Added autocomplete for primary_team and primary_game FKs
    autocomplete_fields = ("user", "primary_team", "primary_game")
    
    fieldsets = (
        ('User Account', {
            'fields': ('user', 'uuid', 'slug', 'public_id')
        }),
        ('Public Identity', {
            'fields': ('avatar', 'banner', 'display_name', 'bio', 'profile_story', 'competitive_goal', 'region'),
            'description': 'Profile story is the extended "About" section bio (separate from hero bio). Competitive goal is a short-term aspiration.'
        }),
        ('Legal Identity & KYC', {
            'fields': ('real_full_name', 'date_of_birth', 'nationality', 'kyc_status', 'kyc_verified_at'),
            'description': 'KYC-verified data is locked and cannot be changed by users.'
        }),
        ('Contact Information', {
            'fields': (
                'phone',
                'whatsapp', 
                'secondary_email',
                'secondary_email_verified',
                'preferred_contact_method',
                'country', 
                'city', 
                'postal_code', 
                'address'
            )
        }),
        ('Demographics & Identity', {
            'fields': ('gender', 'pronouns'),
            'description': 'Gender and pronouns for profile display.'
        }),
        ('Primary Game & Team', {
            'fields': ('primary_team', 'primary_game'),
            'description': 'User\'s main team and signature game. When primary_team is set, primary_game auto-syncs to team\'s game on save.'
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')
        }),
        ('Social Links (from SocialLink model)', {
            'fields': ('social_links_summary', 'edit_social_links_link'),
            'description': 'Social media links are stored in SocialLink model. View summary here, edit via User admin link below.'
        }),
        ('Gaming & Streaming', {
            'fields': ('stream_status', 'main_role', 'secondary_role', 'lft_status'),
            'description': 'Game Passports and profiles are managed via the dedicated Game Profile admin. Stream status is updated automatically. LFT status indicates team/scrims availability.',
            'classes': ('collapse',)
        }),
        ('Gamification', {
            'fields': ('level', 'xp', 'pinned_badges')
        }),
        ('💰 Economy & Wallet (Read-Only - Managed by Economy App)', {
            'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items'),
            'description': '⚠️ WARNING: These fields are READ-ONLY and managed automatically by the Economy app. Manual edits will be overwritten. Use Economy admin for transactions.',
            'classes': ('collapse',)
        }),
        ('System Data', {
            'fields': ('attributes', 'system_settings', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        try:
            return qs.select_related("user")
        except Exception:
            return qs

    def coin_balance(self, obj):
        wallet = getattr(obj, "dc_wallet", None)
        return wallet.cached_balance if wallet else 0
    coin_balance.short_description = "ΔC Coins"
    
    def kyc_status_badge(self, obj):
        """Display KYC status with color badge"""
        colors = {
            'unverified': 'gray',
            'pending': 'orange',
            'verified': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.kyc_status, 'gray')
        
        if obj.kyc_status == 'verified':
            icon = '✓'
        elif obj.kyc_status == 'pending':
            icon = '⏳'
        elif obj.kyc_status == 'rejected':
            icon = '✗'
        else:
            icon = '○'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_kyc_status_display()
        )
    kyc_status_badge.short_description = 'KYC Status'
    
    def social_links_summary(self, obj):
        """HOTFIX (Post-C2): Display read-only summary of social links from SocialLink model"""
        from apps.user_profile.models import SocialLink
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        
        links = SocialLink.objects.filter(user=obj.user).order_by('platform')
        
        if not links.exists():
            return mark_safe('<em style="color: gray;">No social links configured</em>')
        
        html_parts = ['<table style="border-collapse: collapse; width: 100%;">']
        html_parts.append('<tr style="background: #f0f0f0; font-weight: bold;">')
        html_parts.append('<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Platform</th>')
        html_parts.append('<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Handle</th>')
        html_parts.append('<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">URL</th>')
        html_parts.append('</tr>')
        
        for link in links:
            html_parts.append('<tr>')
            html_parts.append(f'<td style="padding: 8px; border: 1px solid #ddd;">{link.get_platform_display()}</td>')
            html_parts.append(f'<td style="padding: 8px; border: 1px solid #ddd;">{link.handle or "-"}</td>')
            
            if link.url:
                html_parts.append(f'<td style="padding: 8px; border: 1px solid #ddd;"><a href="{link.url}" target="_blank" style="color: #0066cc; text-decoration: none;">{link.url}</a></td>')
            else:
                html_parts.append('<td style="padding: 8px; border: 1px solid #ddd;">-</td>')
            
            html_parts.append('</tr>')
        
        html_parts.append('</table>')
        return mark_safe(''.join(html_parts))
    
    social_links_summary.short_description = 'Social Media Links'
    
    def edit_social_links_link(self, obj):
        """HOTFIX (Post-C2): Quick link to edit social links in User admin"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}" class="button" target="_blank" style="padding: 8px 12px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">📝 Edit Social Links (User Admin)</a>',
            url
        )
    
    edit_social_links_link.short_description = 'Quick Actions'


@admin.register(PrivacySettings)
class PrivacySettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'privacy_summary', 'interaction_summary', 'updated_at')
    search_fields = ('user_profile__user__username', 'user_profile__display_name')
    list_filter = ('allow_team_invites', 'allow_friend_requests', 'allow_direct_messages', 'created_at')
    date_hierarchy = 'created_at'
    
    list_select_related = ('user_profile', 'user_profile__user')
    autocomplete_fields = ('user_profile',)
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Profile', {
            'fields': ('user_profile',)
        }),
        ('Profile Visibility', {
            'fields': ('show_real_name', 'show_phone', 'show_email', 'show_age', 
                      'show_gender', 'show_country', 'show_address'),
            'description': 'Control what personal information is visible on public profile.'
        }),
        ('Gaming & Activity', {
            'fields': ('show_game_ids', 'show_match_history', 'show_teams', 'show_achievements'),
            'description': 'Control visibility of gaming-related information.'
        }),
        ('Economy & Inventory', {
            'fields': ('show_inventory_value', 'show_level_xp'),
            'description': 'Control visibility of economy and progression data.'
        }),
        ('Social', {
            'fields': ('show_social_links',),
            'description': 'Control visibility of social media links.'
        }),
        ('Interaction Permissions', {
            'fields': ('allow_team_invites', 'allow_friend_requests', 'allow_direct_messages'),
            'description': 'Control who can interact with this user.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def privacy_summary(self, obj):
        """Show count of visible fields"""
        visible_count = sum([
            obj.show_real_name, obj.show_phone, obj.show_email, obj.show_age,
            obj.show_gender, obj.show_country, obj.show_address, obj.show_game_ids,
            obj.show_match_history, obj.show_teams, obj.show_achievements,
            obj.show_inventory_value, obj.show_level_xp, obj.show_social_links
        ])
        return f"{visible_count}/14 fields visible"
    privacy_summary.short_description = 'Visibility'
    
    def interaction_summary(self, obj):
        """Show interaction permissions"""
        perms = []
        if obj.allow_team_invites:
            perms.append('Teams')
        if obj.allow_friend_requests:
            perms.append('Friends')
        if obj.allow_direct_messages:
            perms.append('DMs')
        return ', '.join(perms) if perms else 'All disabled'
    interaction_summary.short_description = 'Interactions'


@admin.register(KYCSubmission)
class KYCSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for modern KYC verification submissions"""
    
    list_display = ('id', 'user_profile_link', 'document_type', 'status_badge', 'submitted_at', 'reviewed_at', 'reviewed_by')
    search_fields = ('user_profile__user__username', 'user_profile__display_name')
    list_filter = ('status', 'document_type', 'submitted_at', 'reviewed_at')
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)
    
    list_select_related = ('user_profile', 'user_profile__user', 'reviewed_by')
    autocomplete_fields = ('user_profile', 'reviewed_by')
    
    readonly_fields = ('submitted_at', 'reviewed_at', 'document_preview', 'user_profile_info')
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('user_profile', 'user_profile_info', 'document_type', 'submitted_at')
        }),
        ('Uploaded Documents', {
            'fields': ('document_front', 'document_back', 'selfie_with_document', 'document_preview'),
            'description': 'User-uploaded KYC documents for verification.'
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'notes'),
            'description': 'Admin review details and status.'
        }),
    )
    
    actions = ['approve_submissions', 'reject_submissions']
    
    def user_profile_link(self, obj):
        """Link to user profile admin page"""
        url = reverse('admin:user_profile_userprofile_change', args=[obj.user_profile.id])
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.user_profile.display_name)
    user_profile_link.short_description = 'User'
    
    def user_profile_info(self, obj):
        """Display user profile information"""
        profile = obj.user_profile
        return format_html(
            '<strong>Username:</strong> {}<br>'
            '<strong>Email:</strong> {}<br>'
            '<strong>Full Name:</strong> {}<br>'
            '<strong>DOB:</strong> {}<br>'
            '<strong>Current KYC Status:</strong> {}',
            profile.user.username,
            profile.user.email,
            profile.real_full_name or 'Not set',
            profile.date_of_birth or 'Not set',
            profile.get_kyc_status_display()
        )
    user_profile_info.short_description = 'Profile Info'
    
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'rejected': '✗',
        }
        color = colors.get(obj.status, 'gray')
        icon = icons.get(obj.status, '○')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def document_preview(self, obj):
        """Show preview of uploaded documents"""
        html = []
        
        if obj.document_front:
            html.append(f'<div><strong>Front:</strong><br><img src="{obj.document_front.url}" style="max-width: 400px; max-height: 300px; border: 1px solid #ccc; padding: 5px;"></div>')
        
        if obj.document_back:
            html.append(f'<div style="margin-top: 15px;"><strong>Back:</strong><br><img src="{obj.document_back.url}" style="max-width: 400px; max-height: 300px; border: 1px solid #ccc; padding: 5px;"></div>')
        
        if obj.selfie_with_document:
            html.append(f'<div style="margin-top: 15px;"><strong>Selfie with Document:</strong><br><img src="{obj.selfie_with_document.url}" style="max-width: 400px; max-height: 300px; border: 1px solid #ccc; padding: 5px;"></div>')
        
        return mark_safe('<br>'.join(html)) if html else 'No documents uploaded'
    document_preview.short_description = 'Document Preview'
    
    def approve_submissions(self, request, queryset):
        """Admin action to approve KYC submissions"""
        from django.utils import timezone
        approved_count = 0
        
        for submission in queryset.filter(status='pending'):
            try:
                submission.status = 'approved'
                submission.reviewed_by = request.user
                submission.reviewed_at = timezone.now()
                submission.save()
                
                # Update user profile KYC status
                profile = submission.user_profile
                profile.kyc_status = 'verified'
                profile.kyc_verified_at = timezone.now()
                profile.save(update_fields=['kyc_status', 'kyc_verified_at'])
                
                approved_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Error approving {submission.user_profile}: {str(e)}',
                    level='error'
                )
        
        if approved_count:
            self.message_user(
                request,
                f'Successfully approved {approved_count} KYC submission(s)',
                level='success'
            )
    approve_submissions.short_description = 'Approve selected submissions'
    
    def reject_submissions(self, request, queryset):
        """Admin action to reject KYC submissions"""
        from django.utils import timezone
        rejected_count = 0
        
        for submission in queryset.filter(status='pending'):
            try:
                submission.status = 'rejected'
                submission.reviewed_by = request.user
                submission.reviewed_at = timezone.now()
                if not submission.rejection_reason:
                    submission.rejection_reason = 'Documents unclear or invalid. Please resubmit with clearer photos.'
                submission.save()
                
                # Update user profile KYC status
                profile = submission.user_profile
                profile.kyc_status = 'rejected'
                profile.save(update_fields=['kyc_status'])
                
                rejected_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Error rejecting {submission.user_profile}: {str(e)}',
                    level='error'
                )
        
        if rejected_count:
            self.message_user(
                request,
                f'Successfully rejected {rejected_count} KYC submission(s)',
                level='warning'
            )
    reject_submissions.short_description = 'Reject selected submissions'


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    """Admin interface for achievement badges"""
    
    list_display = ('badge_display', 'slug', 'category', 'rarity_badge', 'xp_reward', 'earned_count', 'is_active')
    list_filter = ('category', 'rarity', 'is_active', 'is_hidden', 'created_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('created_at', 'updated_at', 'earned_count')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Badge Identity', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Visual Design', {
            'fields': ('icon', 'color')
        }),
        ('Classification', {
            'fields': ('category', 'rarity', 'order')
        }),
        ('Earning Requirements', {
            'fields': ('criteria', 'xp_reward')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_hidden')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def badge_display(self, obj):
        """Display badge with icon"""
        return format_html(
            '<span style="font-size: 18px;">{}</span> {}',
            obj.icon,
            obj.name
        )
    badge_display.short_description = 'Badge'
    
    def rarity_badge(self, obj):
        """Colored rarity badge"""
        colors = {
            'common': '#95a5a6',
            'rare': '#3498db',
            'epic': '#9b59b6',
            'legendary': '#f39c12'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.rarity, '#95a5a6'),
            obj.get_rarity_display().upper()
        )
    rarity_badge.short_description = 'Rarity'
    
    def earned_count(self, obj):
        """Count of users who earned this badge"""
        count = obj.earned_by.count()
        if count == 0:
            return format_html('<span style="color: #95a5a6;">0 users</span>')
        return format_html(
            '<a href="{}?badge__id__exact={}">{} users</a>',
            reverse('admin:user_profile_userbadge_changelist'),
            obj.id,
            count
        )
    earned_count.short_description = 'Earned By'


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    """Admin interface for user badge ownership"""
    
    list_display = ('user_link', 'badge_display', 'earned_at', 'is_pinned', 'progress_display')
    list_filter = ('badge__category', 'badge__rarity', 'is_pinned', 'earned_at')
    search_fields = ('user__username', 'user__email', 'badge__name')
    readonly_fields = ('earned_at',)
    raw_id_fields = ('user', 'badge')
    date_hierarchy = 'earned_at'
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'badge', 'earned_at')
        }),
        ('Progress', {
            'fields': ('progress', 'context')
        }),
        ('Display', {
            'fields': ('is_pinned',)
        })
    )
    
    def user_link(self, obj):
        """Link to user profile"""
        try:
            # Use 'profile' related name instead of 'userprofile'
            profile = obj.user.profile
            url = reverse('admin:user_profile_userprofile_change', args=[profile.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.username
            )
        except Exception:
            # Fallback if profile doesn't exist
            return obj.user.username
    user_link.short_description = 'User'
    
    def badge_display(self, obj):
        """Display badge with icon"""
        return format_html(
            '<span style="font-size: 16px;">{}</span> {}',
            obj.badge.icon,
            obj.badge.name
        )
    badge_display.short_description = 'Badge'
    
    def progress_display(self, obj):
        """Show progress if available"""
        if not obj.progress:
            return '—'
        
        current = obj.progress.get('current', 0)
        required = obj.progress.get('required', 0)
        
        if required == 0:
            return format_html('<span style="color: #27ae60;">✓ Completed</span>')
        
        percentage = int((current / required) * 100)
        color = '#27ae60' if percentage == 100 else '#f39c12' if percentage >= 50 else '#e74c3c'
        
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            current,
            required,
            percentage
        )
    progress_display.short_description = 'Progress'


# ============================================================================
# UP-M2: ACTIVITY & STATS ADMINS
# ============================================================================

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity log admin - read-only audit trail"""
    
    list_display = [
        'user_link',
        'event_type',
        'created_at',
        'metadata_preview',
    ]
    
    list_filter = [
        'event_type',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'event_type',
    ]
    
    readonly_fields = [
        'user',
        'event_type',
        'metadata',
        'created_at',
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Activity Event', {
            'fields': ['user', 'event_type', 'created_at']
        }),
        ('Event Data', {
            'fields': ['metadata'],
        }),
    ]
    
    def user_link(self, obj):
        """Link to user profile admin"""
        try:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.user.profile.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        except Exception:
            return obj.user.username
    user_link.short_description = 'User'
    
    def metadata_preview(self, obj):
        """Show metadata preview"""
        if obj.metadata:
            preview = str(obj.metadata)[:50]
            return preview + '...' if len(str(obj.metadata)) > 50 else preview
        return '—'
    metadata_preview.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        """Prevent manual creation - activity is event-sourced"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - activity is immutable"""
        return False


@admin.register(UserProfileStats)
class UserProfileStatsAdmin(admin.ModelAdmin):
    """User profile stats admin - read-only derived data with recompute action"""
    
    list_display = [
        'user_link',
        'public_id_display',
        'deltacoin_balance_display',
        'tournaments_played',
        'tournaments_won',
        'matches_played',
        'matches_won',
        'teams_joined_display',
        'computed_at',
    ]
    
    list_filter = [
        'computed_at',
    ]
    
    search_fields = [
        'user_profile__user__username',
        'user_profile__user__email',
        'user_profile__public_id',
    ]
    
    readonly_fields = [
        'user_profile',
        'public_id_display',
        'deltacoin_balance_display',
        'lifetime_earnings_display',
        'tournaments_played',
        'tournaments_won',
        'tournaments_top3',
        'matches_played',
        'matches_won',
        'teams_joined_display',
        'current_team_display',
        'computed_at',
    ]
    
    fieldsets = [
        ('User', {
            'fields': ['user_profile', 'public_id_display']
        }),
        ('Economy Stats (Synced from Wallet)', {
            'fields': ['deltacoin_balance_display', 'lifetime_earnings_display'],
            'description': 'These fields are synced from DeltaCrownWallet. Use "Reconcile Economy" action to fix drift.',
        }),
        ('Tournament Stats (Derived)', {
            'fields': [
                'tournaments_played',
                'tournaments_won',
                'tournaments_top3',
            ],
            'description': 'Computed from Tournament, Registration, TournamentResult tables.',
        }),
        ('Match Stats (Derived)', {
            'fields': ['matches_played', 'matches_won'],
            'description': 'Computed from Match model.',
        }),
        ('Team Stats (Derived)', {
            'fields': ['teams_joined_display', 'current_team_display'],
            'description': 'Computed from team membership relations if available.',
        }),
        ('Metadata', {
            'fields': ['computed_at'],
        }),
    ]
    
    actions = ['recompute_stats', 'reconcile_economy']
    
    def user_link(self, obj):
        """Link to user profile admin"""
        try:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.user_profile.id])
            return format_html('<a href="{}">{}</a>', url, obj.user_profile.user.username)
        except Exception:
            return '—'
    user_link.short_description = 'User'
    
    def public_id_display(self, obj):
        """Show public_id from related UserProfile"""
        try:
            return obj.user_profile.public_id or '—'
        except Exception:
            return '—'
    public_id_display.short_description = 'Public ID'
    
    def deltacoin_balance_display(self, obj):
        """Show DeltaCoin balance from wallet (with fallback)"""
        try:
            # Try to get wallet via reverse relation
            wallet = getattr(obj.user_profile, 'dc_wallet', None)
            if wallet:
                return format_html(
                    '<span style="font-weight: bold; color: #f39c12;">ΔC {}</span>',
                    wallet.cached_balance
                )
            # Fallback: check if UserProfile has deltacoin_balance field
            balance = getattr(obj.user_profile, 'deltacoin_balance', None)
            if balance is not None:
                return format_html(
                    '<span style="font-weight: bold; color: #f39c12;">ΔC {}</span>',
                    balance
                )
            return '—'
        except Exception:
            return '—'
    deltacoin_balance_display.short_description = 'ΔC Balance'
    
    def lifetime_earnings_display(self, obj):
        """Show lifetime earnings from wallet (with fallback)"""
        try:
            # Try to get wallet via reverse relation
            wallet = getattr(obj.user_profile, 'dc_wallet', None)
            if wallet:
                return format_html(
                    '<span style="color: #27ae60;">ΔC {}</span>',
                    wallet.lifetime_earnings
                )
            # Fallback: check if UserProfile has lifetime_earnings field
            earnings = getattr(obj.user_profile, 'lifetime_earnings', None)
            if earnings is not None:
                return format_html(
                    '<span style="color: #27ae60;">ΔC {}</span>',
                    earnings
                )
            return '—'
        except Exception:
            return '—'
    lifetime_earnings_display.short_description = 'Lifetime Earnings'
    
    def teams_joined_display(self, obj):
        """Show number of teams joined (if membership relation exists)"""
        try:
            # Try to get team memberships count
            # Check if there's a membership relation on user
            user = obj.user_profile.user
            
            # Try various possible relation names
            for attr_name in ['membership_set', 'team_memberships', 'memberships']:
                if hasattr(user, attr_name):
                    count = getattr(user, attr_name).count()
                    if count > 0:
                        return format_html(
                            '<span style="font-weight: bold;">{} team(s)</span>',
                            count
                        )
                    return '0'
            
            # If no relation found, return placeholder
            return '—'
        except Exception:
            return '—'
    teams_joined_display.short_description = 'Teams Joined'
    
    def current_team_display(self, obj):
        """Show current active team (if membership relation exists)"""
        try:
            user = obj.user_profile.user
            
            # Try to find active membership
            for attr_name in ['membership_set', 'team_memberships', 'memberships']:
                if hasattr(user, attr_name):
                    # Try to get active membership
                    memberships = getattr(user, attr_name)
                    active = memberships.filter(is_active=True).first() if hasattr(memberships.model, 'is_active') else memberships.first()
                    
                    if active and hasattr(active, 'team'):
                        team_name = active.team.name if hasattr(active.team, 'name') else str(active.team)
                        return format_html(
                            '<span style="font-weight: bold; color: #3498db;">{}</span>',
                            team_name
                        )
            
            return '—'
        except Exception:
            return '—'
    current_team_display.short_description = 'Current Team'
    
    @admin.action(description='🔄 Recompute selected users\' stats (idempotent, safe)')
    def recompute_stats(self, request, queryset):
        """Recompute stats for selected users (calls tournament_stats service)"""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can recompute stats.", level=messages.ERROR)
            return
        
        count = 0
        errors = []
        
        for stats in queryset.select_related('user_profile__user'):
            try:
                # Call idempotent recompute service (takes user_id not user_profile)
                user_id = stats.user_profile.user.id
                TournamentStatsService.recompute_user_stats(user_id)
                
                # Record audit event
                AuditService.record_event(
                    subject_user_id=user_id,
                    event_type='stats_recomputed',
                    source_app='user_profile',
                    object_type='userprofilestats',
                    object_id=stats.id,
                    actor_user_id=request.user.id,
                    metadata={'trigger': 'admin_action'},
                )
                
                count += 1
            except Exception as e:
                errors.append(f"{stats.user_profile.user.username}: {e}")
        
        if errors:
            self.message_user(
                request,
                f"Recomputed {count} stats with {len(errors)} errors: {'; '.join(errors[:5])}",
                level=messages.WARNING
            )
        else:
            self.message_user(
                request,
                f"✅ Successfully recomputed stats for {count} user(s).",
                level=messages.SUCCESS
            )
    
    @admin.action(description='💰 Reconcile selected users\' economy (sync wallet → profile)')
    def reconcile_economy(self, request, queryset):
        """Reconcile economy for selected users (syncs wallet to profile)"""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can reconcile economy.", level=messages.ERROR)
            return
        
        count = 0
        drifts = []
        errors = []
        
        for stats in queryset.select_related('user_profile__user'):
            try:
                user_id = stats.user_profile.user.id
                
                # Check drift first
                drift = get_balance_drift(user_id=user_id)
                if drift != 0:
                    drifts.append(f"{stats.user_profile.user.username}: {drift:+d}")
                
                # Sync wallet to profile
                sync_profile_by_user_id(user_id)
                
                # Record audit event
                AuditService.record_event(
                    subject_user_id=user_id,
                    event_type='economy_sync',
                    source_app='user_profile',
                    object_type='userprofilestats',
                    object_id=stats.id,
                    actor_user_id=request.user.id,
                    metadata={'trigger': 'admin_action', 'drift_corrected': drift},
                )
                
                count += 1
            except Exception as e:
                errors.append(f"{stats.user_profile.user.username}: {e}")
        
        if errors:
            self.message_user(
                request,
                f"Reconciled {count} users with {len(errors)} errors: {'; '.join(errors[:5])}",
                level=messages.WARNING
            )
        elif drifts:
            self.message_user(
                request,
                f"✅ Reconciled {count} user(s). Drifts corrected: {'; '.join(drifts[:10])}",
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                f"✅ Reconciled {count} user(s). No drift detected.",
                level=messages.SUCCESS
            )
    
    def has_add_permission(self, request):
        """Prevent manual creation - stats are derived"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - stats should persist"""
        return False


# ============================================================================
# UP-M5: AUDIT TRAIL ADMIN
# ============================================================================

@admin.register(UserAuditEvent)
class UserAuditEventAdmin(admin.ModelAdmin):
    """Audit event admin - completely immutable, read-only compliance log"""
    
    list_display = [
        'id',
        'subject_user_link',
        'event_type',
        'source_app',
        'object_ref',
        'actor_user_link',
        'created_at',
    ]
    
    list_filter = [
        'event_type',
        'source_app',
        'created_at',
    ]
    
    search_fields = [
        'subject_user__username',
        'subject_user__email',
        'actor_user__username',
        'actor_user__email',
        'object_type',
        'object_id',
        'idempotency_key',
    ]
    
    readonly_fields = [
        'subject_user',
        'actor_user',
        'event_type',
        'source_app',
        'object_type',
        'object_id',
        'before_snapshot',
        'after_snapshot',
        'metadata',
        'request_id',
        'idempotency_key',
        'ip_address',
        'user_agent',
        'created_at',
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Event Identity', {
            'fields': ['id', 'event_type', 'source_app', 'created_at']
        }),
        ('Users', {
            'fields': ['subject_user', 'actor_user']
        }),
        ('Object Reference', {
            'fields': ['object_type', 'object_id']
        }),
        ('Snapshots', {
            'fields': ['before_snapshot', 'after_snapshot'],
            'classes': ['collapse'],
            'description': 'Privacy-safe snapshots (PII redacted by AuditService)',
        }),
        ('Request Context', {
            'fields': ['request_id', 'idempotency_key', 'ip_address', 'user_agent'],
            'classes': ['collapse'],
        }),
        ('Additional Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse'],
        }),
    ]
    
    actions = ['export_audit_log']
    
    def subject_user_link(self, obj):
        """Link to subject user"""
        if obj.subject_user:
            url = reverse('admin:auth_user_change', args=[obj.subject_user.id])
            return format_html('<a href="{}">{}</a>', url, obj.subject_user.username)
        return '—'
    subject_user_link.short_description = 'Subject User'
    
    def actor_user_link(self, obj):
        """Link to actor user (who performed the action)"""
        if obj.actor_user:
            url = reverse('admin:auth_user_change', args=[obj.actor_user.id])
            return format_html('<a href="{}">{}</a>', url, obj.actor_user.username)
        return '(system)'
    actor_user_link.short_description = 'Actor'
    
    def object_ref(self, obj):
        """Show object reference"""
        return f"{obj.object_type}#{obj.object_id}"
    object_ref.short_description = 'Object'
    
    @admin.action(description='📥 Export selected audit events to JSONL')
    def export_audit_log(self, request, queryset):
        """Export selected audit events to JSONL file"""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can export audit logs.", level=messages.ERROR)
            return
        
        # Create temp file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(tempfile.gettempdir()) / f"audit_export_{timestamp}.jsonl"
        
        count = 0
        with open(output_path, 'w') as f:
            for event in queryset.select_related('subject_user', 'actor_user'):
                record = {
                    'id': event.id,
                    'subject_user_id': event.subject_user_id,
                    'subject_username': event.subject_user.username if event.subject_user else None,
                    'actor_user_id': event.actor_user_id,
                    'actor_username': event.actor_user.username if event.actor_user else None,
                    'event_type': event.event_type,
                    'source_app': event.source_app,
                    'object_type': event.object_type,
                    'object_id': event.object_id,
                    'before_snapshot': event.before_snapshot,
                    'after_snapshot': event.after_snapshot,
                    'metadata': event.metadata,
                    'created_at': event.created_at.isoformat(),
                }
                f.write(json.dumps(record) + '\n')
                count += 1
        
        self.message_user(
            request,
            f"✅ Exported {count} audit event(s) to: {output_path}",
            level=messages.SUCCESS
        )
    
    def has_add_permission(self, request):
        """Prevent manual creation - audit events are append-only via AuditService"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing - audit events are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - audit events are immutable"""
        return False


# ==============================================================================
# MEDIA ADMINS - Phase 2B.5
# ==============================================================================

@admin.register(StreamConfig)
class StreamConfigAdmin(admin.ModelAdmin):
    """Admin for user stream configurations (Twitch, YouTube, Facebook)."""
    
    list_display = ['user', 'platform', 'channel_id', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['user__username', 'channel_id', 'title']
    readonly_fields = ['platform', 'channel_id', 'embed_url', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User & Platform', {
            'fields': ('user', 'platform', 'channel_id')
        }),
        ('Stream Configuration', {
            'fields': ('stream_url', 'embed_url', 'title', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HighlightClip)
class HighlightClipAdmin(admin.ModelAdmin):
    """Admin for user highlight clips (YouTube, Twitch, Medal.tv)."""
    
    list_display = ['user', 'title', 'platform', 'game', 'display_order', 'created_at']
    list_filter = ['platform', 'game', 'created_at']
    search_fields = ['user__username', 'title', 'video_id']
    readonly_fields = ['platform', 'video_id', 'embed_url', 'thumbnail_url', 'created_at', 'updated_at']
    inlines = [PinnedHighlightInline]
    
    fieldsets = (
        ('User & Content', {
            'fields': ('user', 'title', 'game')
        }),
        ('Video Details', {
            'fields': ('clip_url', 'platform', 'video_id', 'embed_url', 'thumbnail_url')
        }),
        ('Display', {
            'fields': ('display_order',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['user', 'display_order']


@admin.register(PinnedHighlight)
class PinnedHighlightAdmin(admin.ModelAdmin):
    """Admin for pinned highlights. HIDDEN from sidebar - use HighlightClipAdmin inline."""
    
    list_display = ['user', 'clip', 'pinned_at']
    list_filter = ['pinned_at']
    search_fields = ['user__username', 'clip__title']
    readonly_fields = ['pinned_at']
    
    fieldsets = (
        ('Pinned Highlight', {
            'fields': ('user', 'clip')
        }),
        ('Metadata', {
            'fields': ('pinned_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_model_perms(self, request):
        """Hide from admin sidebar."""
        return {}


# ==============================================================================
# LOADOUT ADMINS - Phase 2B.5
# ==============================================================================

@admin.register(HardwareGear)
class HardwareGearAdmin(admin.ModelAdmin):
    """Admin for user hardware gear (mouse, keyboard, headset, monitor, mousepad)."""
    
    list_display = ['user', 'category', 'brand', 'model', 'is_public', 'updated_at']
    list_filter = ['category', 'is_public', 'brand', 'created_at']
    search_fields = ['user__username', 'brand', 'model']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Hardware', {
            'fields': ('user', 'category', 'brand', 'model')
        }),
        ('Specifications', {
            'fields': ('specs', 'purchase_url')
        }),
        ('Privacy', {
            'fields': ('is_public',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['user', 'category']


@admin.register(GameConfig)
class GameConfigAdmin(admin.ModelAdmin):
    """Admin for per-game configuration settings (sensitivity, crosshair, keybinds).
    
    HIDDEN FROM SIDEBAR - Per-user per-game configs, access via user search.
    """
    
    list_display = ['user', 'game', 'is_public', 'updated_at']
    list_filter = ['game', 'is_public', 'created_at']
    search_fields = ['user__username', 'game__name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Game', {
            'fields': ('user', 'game')
        }),
        ('Settings', {
            'fields': ('settings', 'notes')
        }),
        ('Privacy', {
            'fields': ('is_public',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['user', 'game']
    
    def has_module_permission(self, request):
        """Hide from admin sidebar - access via user/game search."""
        return False


# ==============================================================================
# SHOWCASE ADMINS - Phase 2B.5
# ==============================================================================

@admin.register(ProfileShowcase)
class ProfileShowcaseAdmin(admin.ModelAdmin):
    """Admin for profile showcase configuration (About section toggles)."""
    
    list_display = ['user_profile', 'featured_team_id', 'featured_passport_id', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user_profile__display_name', 'featured_team_role']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Profile', {
            'fields': ('user_profile',)
        }),
        ('Featured Content', {
            'fields': ('featured_team_id', 'featured_team_role', 'featured_passport_id')
        }),
        ('Section Configuration', {
            'fields': ('enabled_sections', 'section_order', 'highlights')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProfileAboutItem)
class ProfileAboutItemAdmin(admin.ModelAdmin):
    """Admin for profile About section items (Facebook-style).
    
    HIDDEN FROM SIDEBAR - User-curated items, access via ProfileShowcase or user search.
    """
    
    list_display = ['user_profile', 'item_type', 'visibility', 'order_index', 'created_at']
    list_filter = ['item_type', 'visibility', 'created_at']
    search_fields = ['user_profile__display_name', 'display_text']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Profile & Type', {
            'fields': ('user_profile', 'item_type')
        }),
        ('Content', {
            'fields': ('display_text', 'source_model', 'source_id', 'icon_emoji')
        }),
        ('Display', {
            'fields': ('visibility', 'order_index', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['user_profile', 'order_index']
    
    def has_module_permission(self, request):
        """Hide from admin sidebar - access via ProfileShowcase or user search."""
        return False


# ==============================================================================
# TROPHY/ENDORSEMENT/BOUNTY ADMINS - Phase 2B.5
# ==============================================================================

@admin.register(TrophyShowcaseConfig)
class TrophyShowcaseConfigAdmin(admin.ModelAdmin):
    """Admin for trophy showcase configuration."""
    
    list_display = ['user', 'border', 'frame', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Cosmetics', {
            'fields': ('border', 'frame', 'pinned_badges')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SkillEndorsement)
class SkillEndorsementAdmin(admin.ModelAdmin):
    """Admin for skill endorsements."""
    
    list_display = ['receiver', 'endorser', 'skill_name', 'is_flagged', 'created_at']
    list_filter = ['skill_name', 'is_flagged', 'created_at']
    search_fields = ['receiver__username', 'endorser__username', 'comment']
    readonly_fields = ['match', 'endorser', 'receiver', 'created_at']
    
    fieldsets = (
        ('Endorsement', {
            'fields': ('match', 'endorser', 'receiver', 'skill_name')
        }),
        ('Details', {
            'fields': ('comment', 'is_flagged', 'flag_reason')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EndorsementOpportunity)
class EndorsementOpportunityAdmin(admin.ModelAdmin):
    """Admin for endorsement opportunities. HIDDEN from sidebar - system-generated."""
    
    list_display = ['player', 'match', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'notified', 'created_at']
    search_fields = ['player__username']
    readonly_fields = ['match', 'player', 'expires_at', 'created_at']
    
    fieldsets = (
        ('Opportunity', {
            'fields': ('match', 'player', 'expires_at')
        }),
        ('Status', {
            'fields': ('is_used', 'used_at', 'notified', 'notified_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_model_perms(self, request):
        """Hide from admin sidebar - system-generated records."""
        return {}


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    """Admin for bounties with full lifecycle management."""
    
    list_display = ['id', 'title', 'creator', 'acceptor', 'status', 'stake_amount', 'created_at']
    list_filter = ['status', 'game', 'created_at']
    search_fields = ['title', 'creator__username', 'acceptor__username', 'description']
    readonly_fields = ['created_at', 'payout_amount', 'platform_fee']
    inlines = [BountyAcceptanceInline, BountyProofInline, BountyDisputeInline]
    
    fieldsets = (
        ('Bounty Details', {
            'fields': ('title', 'description', 'game', 'status')
        }),
        ('Participants', {
            'fields': ('creator', 'acceptor', 'target_user', 'winner')
        }),
        ('Financials', {
            'fields': ('stake_amount', 'payout_amount', 'platform_fee')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at', 'result_submitted_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BountyAcceptance)
class BountyAcceptanceAdmin(admin.ModelAdmin):
    """Admin for bounty acceptances. HIDDEN from sidebar - use BountyAdmin inline."""
    
    list_display = ['bounty', 'acceptor', 'accepted_at']
    list_filter = ['accepted_at']
    search_fields = ['bounty__title', 'acceptor__username']
    readonly_fields = ['bounty', 'acceptor', 'accepted_at', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Acceptance', {
            'fields': ('bounty', 'acceptor', 'accepted_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def get_model_perms(self, request):
        """Hide from admin sidebar."""
        return {}


@admin.register(BountyProof)
class BountyProofAdmin(admin.ModelAdmin):
    """Admin for bounty proof submissions. HIDDEN from sidebar - use BountyAdmin inline."""
    
    list_display = ['bounty', 'submitted_by', 'claimed_winner', 'proof_type', 'submitted_at']
    list_filter = ['proof_type', 'submitted_at']
    search_fields = ['bounty__title', 'submitted_by__username', 'description']
    readonly_fields = ['bounty', 'submitted_by', 'claimed_winner', 'submitted_at']
    
    fieldsets = (
        ('Proof', {
            'fields': ('bounty', 'submitted_by', 'claimed_winner', 'proof_type')
        }),
        ('Content', {
            'fields': ('proof_url', 'description')
        }),
        ('Metadata', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_model_perms(self, request):
        """Hide from admin sidebar."""
        return {}


@admin.register(BountyDispute)
class BountyDisputeAdmin(admin.ModelAdmin):
    """Admin for bounty disputes. HIDDEN from sidebar - use BountyAdmin inline."""
    
    list_display = ['bounty', 'disputer', 'status', 'assigned_moderator', 'created_at']
    list_filter = ['status', 'created_at', 'resolved_at']
    search_fields = ['bounty__title', 'disputer__username', 'reason']
    readonly_fields = ['bounty', 'disputer', 'created_at', 'resolved_at']
    actions = ['assign_to_me', 'mark_under_review', 'mark_resolved', 'refund_creator', 'award_challenger']
    
    fieldsets = (
        ('Dispute', {
            'fields': ('bounty', 'disputer', 'reason', 'status')
        }),
        ('Moderation', {
            'fields': ('assigned_moderator', 'resolution')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def assign_to_me(self, request, queryset):
        """Assign selected disputes to current moderator."""
        count = queryset.filter(assigned_moderator__isnull=True).update(
            assigned_moderator=request.user,
            status='under_review'
        )
        self.message_user(request, f'{count} disputes assigned to you', messages.SUCCESS)
    assign_to_me.short_description = 'Assign to me'
    
    def mark_under_review(self, request, queryset):
        """Mark disputes as under review."""
        count = queryset.filter(status='open').update(status='under_review')
        self.message_user(request, f'{count} disputes marked under review', messages.SUCCESS)
    mark_under_review.short_description = 'Mark as under review'
    
    def mark_resolved(self, request, queryset):
        """Mark disputes as resolved (confirm original result)."""
        count = queryset.filter(status__in=['open', 'under_review']).update(
            status='resolved_confirm',
            resolved_at=timezone.now(),
            assigned_moderator=request.user
        )
        self.message_user(request, f'{count} disputes marked as resolved', messages.SUCCESS)
    mark_resolved.short_description = 'Mark as Resolved (Confirm Result)'
    
    def refund_creator(self, request, queryset):
        """Resolve dispute and refund bounty creator."""
        count = queryset.filter(status__in=['open', 'under_review']).update(
            status='resolved_reverse',
            resolved_at=timezone.now(),
            assigned_moderator=request.user,
            resolution='Dispute resolved in favor of bounty creator. Stake refunded.'
        )
        self.message_user(
            request, 
            f'{count} disputes resolved - Creator refunded (requires manual wallet action)', 
            messages.WARNING
        )
    refund_creator.short_description = 'Refund Creator (Reverse Result)'
    
    def award_challenger(self, request, queryset):
        """Resolve dispute and award challenger."""
        count = queryset.filter(status__in=['open', 'under_review']).update(
            status='resolved_confirm',
            resolved_at=timezone.now(),
            assigned_moderator=request.user,
            resolution='Dispute reviewed - original result confirmed. Challenger awarded.'
        )
        self.message_user(
            request,
            f'{count} disputes resolved - Challenger awarded (requires manual wallet action)',
            messages.SUCCESS
        )
    award_challenger.short_description = 'Award Challenger (Confirm Result)'
    
    def get_model_perms(self, request):
        """Hide from admin sidebar."""
        return {}
