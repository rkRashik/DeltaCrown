# apps/user_profile/admin.py
"""
Django Admin configuration for User Profile models.
Phase 3 Implementation - All new models registered.
UP-ADMIN-01: Professional platform-grade admin with audit-first safeguards.

⚠️ ADMIN ORGANIZATION:
- UserProfile: Registered in apps/user_profile/admin/users.py
- All other models: Registered in this file (admin.py)

This separation prevents duplicate registration conflicts.

📚 Documentation: docs/ADMIN_ORGANIZATION.md
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Q

from .models import (
    UserProfile,
    PrivacySettings,
    VerificationRecord,
    Badge,
    UserBadge,
    # Phase 3 Models
    SocialLink,
    GameProfile,
    Achievement,
    # Match - REMOVED: Placeholder admin, unregistered until tournament system writes data
    Certificate,
    # UP-M2 Models - REMOVED: Orphaned (UserActivity, UserProfileStats)
    # UP-M5 Models
    UserAuditEvent,
    # GP-0 Models
    GameProfileAlias,
    GameProfileConfig,
    # UP-PHASE6-C Models
    NotificationPreferences,
    WalletSettings,
    # P0 Media Models
    StreamConfig,
    HighlightClip,
    PinnedHighlight,
    # P0 Loadout Models
    HardwareGear,
    GameConfig,
    # P0 Trophy Showcase Models
    TrophyShowcaseConfig,
    # P0 Endorsement Models
    SkillEndorsement,
    EndorsementOpportunity,
    # P0 Bounty Models
    Bounty,
    BountyAcceptance,
    BountyProof,
    BountyDispute,
    # P0 Showcase Models
    ProfileShowcase,
    ProfileAboutItem,
)
from .services.audit import AuditService
from .services.tournament_stats import TournamentStatsService
from .services.economy_sync import sync_profile_by_user_id, get_balance_drift
from .admin.forms import UserProfileAdminForm, GameProfileAdminForm


# ============================================================================
# INLINE ADMINS
# ============================================================================

class PrivacySettingsInline(StackedInline):
    """Inline privacy settings editor"""
    model = PrivacySettings
    can_delete = False
    verbose_name = "Privacy Settings"
    verbose_name_plural = "Privacy Settings"
    fields = [
        ('show_real_name', 'show_phone', 'show_email'),
        ('show_age', 'show_gender', 'show_country'),
        ('show_game_ids', 'show_social_links'),
        ('show_match_history', 'show_teams', 'show_achievements'),
        ('allow_team_invites', 'allow_friend_requests', 'allow_direct_messages'),
    ]


class SocialLinkInline(TabularInline):
    """Inline social links editor"""
    model = SocialLink
    extra = 0
    fields = ['platform', 'url', 'handle', 'is_verified']
    readonly_fields = ['is_verified']


class GameProfileInline(TabularInline):
    """Inline game profiles editor - replaces JSON field"""
    model = GameProfile
    extra = 1
    fields = ['game', 'in_game_name', 'rank_name', 'main_role', 'matches_played', 'win_rate', 'updated_at']
    readonly_fields = ['updated_at']
    verbose_name = "Game Profile (Normalized)"
    verbose_name_plural = "Game Profiles (Normalized Model)"


class GameProfileAliasInline(TabularInline):
    """
    GP-0 Inline for identity change history
    
    Read-only inline showing all identity changes for a game passport.
    No add/delete - aliases are created by GamePassportService only.
    """
    model = GameProfileAlias
    extra = 0
    can_delete = False
    
    fields = [
        'old_in_game_name',
        'changed_at',
        'changed_by_user_display',
        'request_ip',
        'reason',
    ]
    
    readonly_fields = [
        'old_in_game_name',
        'changed_at',
        'changed_by_user_display',
        'request_ip',
        'reason',
    ]
    
    verbose_name = "Identity Change History"
    verbose_name_plural = "Identity Change History (Append-Only)"
    
    def changed_by_user_display(self, obj):
        """Display user link for changed_by_user_id"""
        if not obj.changed_by_user_id:
            return "System"
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=obj.changed_by_user_id)
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:auth_user_change', args=[user.id]),
                user.username
            )
        except User.DoesNotExist:
            return f"User #{obj.changed_by_user_id} (deleted)"
    changed_by_user_display.short_description = 'Changed By'
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding aliases via admin"""
        return False


class UserBadgeInline(TabularInline):
    """Inline user badges editor"""
    model = UserBadge
    extra = 0
    fields = ['badge', 'earned_at', 'is_pinned']
    readonly_fields = ['earned_at']


class NotificationPreferencesInline(StackedInline):
    """
    UP-PHASE6-C: Inline notification preferences editor
    
    Displays email and platform notification settings on UserProfile admin.
    """
    model = NotificationPreferences
    can_delete = False
    verbose_name = "Notification Preferences"
    verbose_name_plural = "Notification Preferences"
    
    fieldsets = [
        ('Email Notifications', {
            'fields': [
                'email_tournament_reminders',
                'email_match_results',
                'email_team_invites',
                'email_achievements',
                'email_platform_updates',
            ]
        }),
        ('Platform Notifications', {
            'fields': [
                'notify_tournament_start',
                'notify_team_messages',
                'notify_follows',
                'notify_achievements',
            ]
        }),
    ]


class WalletSettingsInline(StackedInline):
    """
    UP-PHASE6-C: Inline wallet settings editor
    
    Displays Bangladesh mobile banking settings and withdrawal preferences.
    """
    model = WalletSettings
    can_delete = False
    verbose_name = "Wallet Settings"
    verbose_name_plural = "Wallet Settings"
    
    fieldsets = [
        ('Mobile Banking', {
            'fields': [
                ('bkash_enabled', 'bkash_account'),
                ('nagad_enabled', 'nagad_account'),
                ('rocket_enabled', 'rocket_account'),
            ]
        }),
        ('Withdrawal Preferences', {
            'fields': [
                'auto_withdrawal_threshold',
                'auto_convert_to_usd',
            ]
        }),
    ]


# ============================================================================
# MAIN MODEL ADMINS  
# ============================================================================

# ⚠️ IMPORTANT: UserProfile admin is registered in apps/user_profile/admin/users.py
# DO NOT register UserProfile here to avoid conflicts with the main registration.
# All UserProfile fieldsets, list_display, and customizations should be done in:
#   → apps/user_profile/admin/users.py (UserProfileAdmin class)
#
# Admin URL: http://127.0.0.1:8000/admin/user_profile/userprofile/
# ============================================================================


@admin.register(PrivacySettings)
class PrivacySettingsAdmin(ModelAdmin):
    """Privacy settings standalone admin"""
    
    list_display = [
        'user_profile',
        'show_real_name',
        'show_phone',
        'show_email',
        'allow_team_invites',
        'allow_friend_requests',
    ]
    
    list_filter = [
        'show_real_name',
        'show_phone',
        'show_email',
        'allow_team_invites',
        'allow_friend_requests',
        'allow_direct_messages',
    ]
    
    search_fields = ['user_profile__display_name', 'user_profile__user__username']
    
    fieldsets = [
        ('Profile Visibility', {
            'fields': [
                'show_real_name',
                'show_phone',
                'show_email',
                'show_age',
                'show_gender',
                'show_country',
                'show_address',
            ]
        }),
        ('Gaming & Activity', {
            'fields': [
                'show_game_ids',
                'show_match_history',
                'show_teams',
                'show_achievements',
            ]
        }),
        ('Economy & Inventory', {
            'fields': [
                'show_inventory_value',
                'show_level_xp',
            ]
        }),
        ('Social', {
            'fields': ['show_social_links']
        }),
        ('Interaction Permissions', {
            'fields': [
                'allow_team_invites',
                'allow_friend_requests',
                'allow_direct_messages',
            ]
        }),
    ]


@admin.register(VerificationRecord)
class VerificationRecordAdmin(ModelAdmin):
    """KYC verification records admin"""
    
    list_display = [
        'user_profile',
        'status',
        'submitted_at',
        'reviewed_at',
        'reviewed_by',
    ]
    
    list_filter = [
        'status',
        'submitted_at',
        'reviewed_at',
    ]
    
    search_fields = [
        'user_profile__display_name',
        'user_profile__user__username',
        'verified_name',
        'id_number',
    ]
    
    readonly_fields = [
        'user_profile',
        'submitted_at',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = [
        ('User', {
            'fields': ['user_profile', 'status']
        }),
        ('Documents', {
            'fields': [
                'id_document_front',
                'id_document_back',
                'selfie_with_id',
            ]
        }),
        ('Verified Information', {
            'fields': [
                'verified_name',
                'verified_dob',
                'verified_nationality',
                'id_number',
            ]
        }),
        ('Review Process', {
            'fields': [
                'submitted_at',
                'reviewed_at',
                'reviewed_by',
                'rejection_reason',
            ]
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['approve_verification', 'reject_verification']
    
    def approve_verification(self, request, queryset):
        """Bulk approve KYC verifications"""
        count = 0
        for record in queryset.filter(status='pending'):
            try:
                record.approve(
                    reviewed_by=request.user,
                    verified_name=record.verified_name or "Name Required",
                    verified_dob=record.verified_dob,
                    verified_nationality=record.verified_nationality or "Nationality Required",
                )
                count += 1
            except Exception as e:
                self.message_user(request, f"Error approving {record}: {e}", level='error')
        
        self.message_user(request, f"Successfully approved {count} verification(s).")
    approve_verification.short_description = "✓ Approve selected verifications"
    
    def reject_verification(self, request, queryset):
        """Bulk reject KYC verifications"""
        count = 0
        for record in queryset.filter(status='pending'):
            record.reject(reviewed_by=request.user, reason="Rejected via bulk action")
            count += 1
        
        self.message_user(request, f"Successfully rejected {count} verification(s).")
    reject_verification.short_description = "✗ Reject selected verifications"


@admin.register(Badge)
class BadgeAdmin(ModelAdmin):
    """Badge system admin"""
    
    list_display = ['icon', 'name', 'rarity', 'category', 'xp_reward', 'is_active', 'is_hidden']
    list_filter = ['rarity', 'category', 'is_active', 'is_hidden']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ['name']}
    
    fieldsets = [
        ('Basic Info', {
            'fields': ['name', 'slug', 'description', 'icon', 'color']
        }),
        ('Classification', {
            'fields': ['rarity', 'category', 'order']
        }),
        ('Criteria & Rewards', {
            'fields': ['criteria', 'xp_reward']
        }),
        ('Settings', {
            'fields': ['is_active', 'is_hidden']
        }),
    ]


@admin.register(UserBadge)
class UserBadgeAdmin(ModelAdmin):
    """User badges admin"""
    
    list_display = ['user', 'badge', 'earned_at', 'is_pinned']
    list_filter = ['is_pinned', 'earned_at', 'badge__rarity']
    search_fields = ['user__username', 'badge__name']
    readonly_fields = ['earned_at']
    
    fieldsets = [
        ('Badge Award', {
            'fields': ['user', 'badge', 'earned_at', 'is_pinned']
        }),
        ('Progress & Context', {
            'fields': ['progress', 'context'],
            'classes': ['collapse']
        }),
    ]


# ============================================================================
# PHASE 3: NEW MODEL ADMINS
# ============================================================================

# @admin.register(SocialLink) - REMOVED: Orphaned model, no views use it
# class SocialLinkAdmin(ModelAdmin):
#     """Social links admin - ORPHANED, unregistered in Phase 5B"""
#     pass


# Phase 9A-30: GameProfile admin DISABLED - Use custom admin at /admin/game-passports/
# Old Django admin removed due to outdated code and confusing UI
# New custom admin provides modern interface with better UX

# @admin.register(GameProfile)
# class GameProfileAdmin(ModelAdmin):
#     """
#     Game Passport Admin (Phase 9A-14) - DISABLED
#     
#     This admin has been replaced with a custom interface at /admin/game-passports/
#     See apps/user_profile/views/game_passport_admin.py for the new implementation
#     """
#     pass

# Phase 9A-30: All GameProfile admin code commented out below
if False:  # Disabled - use custom admin instead
    
    form__ = GameProfileAdminForm  # Phase 9A-14: Schema-driven form with dynamic dropdowns
    
    list_display__ = [
        'user',
        'game',
        'in_game_name',
        'identity_key',
        'verification_status_badge',  # Phase 9A-29: Visual badge
        'cooldown_badge',  # Phase 9A-29: Cooldown status
        'lock_status_display',
        'visibility',
        'updated_at',
    ]
    
    list_filter = [
        'verification_status',  # Phase 9A-30: Prioritize verification workflow
        'game',
        ('locked_until', admin.EmptyFieldListFilter),  # Active locks
        'visibility',
        'status',
        'is_pinned',
        'is_lft',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__userprofile__public_id',  # GP-FE-MVP-01: Search by public_id
        'in_game_name',
        'identity_key',
        'game',
    ]
    
    readonly_fields = [
        'game_display_name',
        'identity_key',
        'locked_until_display',
        'lock_countdown_display',
        'verification_status_display',  # Phase 8B
        'created_at',
        'updated_at',
    ]
    
    actions = [
        'mark_as_verified',
        'mark_as_pending',
        'mark_as_flagged',
        'override_cooldown_action',
        'unlock_identity_changes',
        'pin_passports',
        'unpin_passports',
    ]
    
    fieldsets = [
        ('Identity & Account Linking', {
            'fields': [
                'user',
                'game',
                'game_display_name',
                'in_game_name',
                'identity_key',
                'region',
            ],
            'description': 'Core identity information linking DeltaCrown account to game profile'
        }),
        ('Visibility & Status', {
            'fields': [
                'visibility',
                'status',
                'is_lft',
            ]
        }),
        ('Featured & Ordering', {
            'fields': [
                'is_pinned',
                'pinned_order',
                'sort_order',
            ]
        }),
        ('Competitive Profile', {
            'fields': [
                'rank_name',
                'rank_image',
                'rank_points',
                'rank_tier',
                'peak_rank',
                'matches_played',
                'win_rate',
                'kd_ratio',
                'hours_played',
                'main_role',
            ],
            'classes': ['collapse'],
            'description': 'Competitive statistics and performance metrics'
        }),
        ('Extended Data (JSON)', {
            'fields': ['metadata'],
            'classes': ['collapse'],
            'description': 'Game-specific additional data (region codes, zone IDs, etc.)',
        }),
        ('Cooldown & Protection', {
            'fields': [
                'locked_until_display',
                'lock_countdown_display',
            ],
            'classes': ['collapse'],
            'description': 'Fair Play Protocol: prevents rapid identity changes'
        }),
        ('Verification & Integrity', {
            'fields': [
                'verification_status',
                'verification_status_display',
                'verification_notes',
                'verified_at',
                'verified_by',
            ],
            'classes': ['collapse'],
            'description': 'Staff verification workflow: PENDING → VERIFIED or FLAGGED'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [GameProfileAliasInline]
    
    def lock_status_display(self, obj):
        """Display lock status in list view"""
        if not obj.locked_until:
            return format_html('<span style="color: green;">✓ Unlocked</span>')
        
        if obj.is_identity_locked():
            from django.utils import timezone
            days_left = (obj.locked_until - timezone.now()).days
            return format_html(
                '<span style="color: red;">🔒 Locked ({} days)</span>',
                days_left
            )
        else:
            return format_html('<span style="color: orange;">⏱ Expired</span>')
    lock_status_display.short_description = 'Lock Status'
    
    def locked_until_display(self, obj):
        """Formatted locked_until for detail view"""
        if not obj.locked_until:
            return "Not locked"
        return obj.locked_until.strftime('%Y-%m-%d %H:%M:%S %Z')
    locked_until_display.short_description = 'Locked Until'
    
    def lock_countdown_display(self, obj):
        """Human-readable lock countdown"""
        if not obj.locked_until:
            return "Identity changes allowed"
        
        if obj.is_identity_locked():
            from django.utils import timezone
            delta = obj.locked_until - timezone.now()
            days = delta.days
            hours = delta.seconds // 3600
            return f"Locked for {days} days, {hours} hours"
        else:
            return "Lock expired (identity changes allowed)"
    lock_countdown_display.short_description = 'Lock Countdown'
    
    def save_model(self, request, obj, form, change):
        """
        Phase 9A-14: Auto-populate verification fields + identity change auditing
        
        - If verification_status changes to VERIFIED: auto-set verified_by and verified_at
        - If verification_status changes from VERIFIED to PENDING/FLAGGED: clear verified fields
        - Log identity changes with warning (bypasses cooldown)
        - Record audit event
        """
        from django.utils import timezone
        
        # Check verification status changes
        if change:
            try:
                old_obj = GameProfile.objects.get(pk=obj.pk)
                
                # Auto-populate verification fields when status changes
                if obj.verification_status != old_obj.verification_status:
                    if obj.verification_status == 'VERIFIED':
                        # Auto-set verified_by and verified_at
                        if not obj.verified_by:
                            obj.verified_by = request.user
                        if not obj.verified_at:
                            obj.verified_at = timezone.now()
                        
                        self.message_user(
                            request,
                            f"Passport verified! Auto-populated 'Verified by' → {request.user.username}, 'Verified at' → now",
                            level=messages.SUCCESS
                        )
                    elif old_obj.verification_status == 'VERIFIED':
                        # Reverting from VERIFIED: clear verification fields
                        obj.verified_by = None
                        obj.verified_at = None
                        
                        self.message_user(
                            request,
                            "Verification status changed from VERIFIED: cleared 'Verified by' and 'Verified at' fields",
                            level=messages.INFO
                        )
                
                # Check if identity changed
                if old_obj.in_game_name != obj.in_game_name:
                    # Identity changed via admin - log warning
                    self.message_user(
                        request,
                        "WARNING: Identity changed directly via admin (bypasses cooldown). "
                        "Use GamePassportService for proper audit trail.",
                        level=messages.WARNING
                    )
            except GameProfile.DoesNotExist:
                pass
        
        # Save normally
        super().save_model(request, obj, form, change)
        
        # Record audit event
        if change:
            AuditService.record_event(
                subject_user_id=obj.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.admin_edited',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=obj.id,
                metadata={
                    'game': obj.game,
                    'identity_key': obj.identity_key,
                    'edited_by_admin': request.user.username,
                    'verification_status': obj.verification_status,
                }
            )
    
    actions = ['unlock_identity_changes', 'pin_passports', 'unpin_passports', 'override_cooldown_action', 'mark_as_verified', 'mark_as_flagged']
    
    # Phase 9A-28: Cooldown override action
    def override_cooldown_action(self, request, queryset):
        """Admin action to override active cooldowns"""
        from apps.user_profile.models.cooldown import GamePassportCooldown
        from django.utils import timezone
        
        count = 0
        for passport in queryset:
            has_cooldown, cooldown = GamePassportCooldown.check_cooldown(
                passport.user, passport.game, cooldown_type='POST_DELETE'
            )
            if has_cooldown and cooldown:
                cooldown.override(
                    admin_user=request.user,
                    reason=f"Admin override by {request.user.username}"
                )
                count += 1
        
        self.message_user(
            request,
            f"Overridden cooldown for {count} passport(s)",
            level=messages.SUCCESS
        )
    override_cooldown_action.short_description = "Override active cooldowns (allows deletion)"
    
    def unlock_identity_changes(self, request, queryset):
        """Admin action to unlock identity changes"""
        count = queryset.update(locked_until=None)
        self.message_user(
            request,
            f"Unlocked {count} passport(s). Identity changes now allowed.",
            level=messages.SUCCESS
        )
        
        # Audit each unlock
        for passport in queryset:
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.admin_unlocked',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': passport.game,
                    'unlocked_by_admin': request.user.username,
                }
            )
    unlock_identity_changes.short_description = "Unlock identity changes (remove cooldown)"
    
    # Phase 9A-29: Enhanced display methods for list view
    def verification_status_badge(self, obj):
        """Compact visual badge for verification status"""
        if obj.verification_status == 'VERIFIED':
            return format_html(
                '<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">✓ VERIFIED</span>'
            )
        elif obj.verification_status == 'FLAGGED':
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">⚠ FLAGGED</span>'
            )
        return format_html(
            '<span style="background: #6b7280; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">PENDING</span>'
        )
    verification_status_badge.short_description = 'Verification'
    
    def cooldown_badge(self, obj):
        """Show cooldown status in list"""
        from apps.user_profile.models.cooldown import GamePassportCooldown
        
        has_cooldown, cooldown = GamePassportCooldown.check_cooldown(
            obj.user, obj.game, cooldown_type='POST_DELETE'
        )
        
        if has_cooldown and cooldown:
            days = cooldown.days_remaining()
            return format_html(
                '<span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">🔒 {days}d</span>',
                days=days
            )
        return format_html(
            '<span style="color: #10b981; font-size: 11px;">✓ None</span>'
        )
    cooldown_badge.short_description = 'Cooldown'
    
    # Phase 8B: Verification status actions and display
    def verification_status_display(self, obj):
        """Display verification status with color coding"""
        status_colors = {
            'PENDING': 'orange',
            'VERIFIED': 'green',
            'FLAGGED': 'red',
        }
        color = status_colors.get(obj.verification_status, 'gray')
        icon_map = {
            'PENDING': '⏳',
            'VERIFIED': '✓',
            'FLAGGED': '⚠',
        }
        icon = icon_map.get(obj.verification_status, '?')
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_verification_status_display()
        )
    verification_status_display.short_description = 'Verification Status'
    
    def mark_as_verified(self, request, queryset):
        """Admin action to mark passports as VERIFIED"""
        from django.utils import timezone
        count = queryset.update(
            verification_status='VERIFIED',
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(
            request,
            f"Marked {count} passport(s) as VERIFIED.",
            level=messages.SUCCESS
        )
        
        # Audit each verification
        for passport in queryset:
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.verified',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': str(passport.game),
                    'verified_by_admin': request.user.username,
                }
            )
    mark_as_verified.short_description = "✓ Mark as VERIFIED"
    
    def mark_as_pending(self, request, queryset):
        """Admin action to mark passports as PENDING"""
        count = queryset.update(
            verification_status='PENDING',
            verified_at=None,
            verified_by=None
        )
        self.message_user(
            request,
            f"Marked {count} passport(s) as PENDING verification.",
            level=messages.SUCCESS
        )
        
        # Audit each status change
        for passport in queryset:
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.verification_reset',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': str(passport.game),
                    'reset_by_admin': request.user.username,
                }
            )
    mark_as_pending.short_description = "⏳ Mark as PENDING"
    
    def mark_as_flagged(self, request, queryset):
        """Admin action to mark passports as FLAGGED"""
        count = queryset.update(
            verification_status='FLAGGED'
        )
        self.message_user(
            request,
            f"Marked {count} passport(s) as FLAGGED for review.",
            level=messages.WARNING
        )
        
        # Audit each flag
        for passport in queryset:
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.flagged',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': str(passport.game),
                    'flagged_by_admin': request.user.username,
                }
            )
    mark_as_flagged.short_description = "⚠ Mark as FLAGGED"
    
    def pin_passports(self, request, queryset):
        """Admin action to pin passports"""
        count = queryset.update(is_pinned=True)
        self.message_user(request, f"Pinned {count} passport(s).", level=messages.SUCCESS)
    pin_passports.short_description = "Pin passports"
    
    def unpin_passports(self, request, queryset):
        """Admin action to unpin passports"""
        count = queryset.update(is_pinned=False, pinned_order=None)
        self.message_user(request, f"Unpinned {count} passport(s).", level=messages.SUCCESS)
    unpin_passports.short_description = "Unpin passports"


@admin.register(GameProfileAlias)
class GameProfileAliasAdmin(ModelAdmin):
    """
    Game Passport Alias History Admin
    
    Read-only view of all identity changes for audit trail.
    Shows who changed what, when, and why.
    """
    
    list_display = [
        'game_profile',
        'old_in_game_name',
        'changed_at',
        'changed_by_display',
        'reason_display',
    ]
    
    list_filter = [
        'game_profile__game',
        'changed_at',
    ]
    
    search_fields = [
        'game_profile__user__username',
        'game_profile__in_game_name',
        'old_in_game_name',
        'reason',
    ]
    
    readonly_fields = [
        'game_profile',
        'old_in_game_name',
        'changed_at',
        'changed_by_user_id',
        'reason',
    ]
    
    fieldsets = [
        ('Identity Change', {
            'fields': [
                'game_profile',
                'old_in_game_name',
                'changed_at',
            ]
        }),
        ('Change Context', {
            'fields': [
                'changed_by_user_id',
                'reason',
            ]
        }),
    ]
    
    def changed_by_display(self, obj):
        """Show username if available"""
        if obj.changed_by_user_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=obj.changed_by_user_id)
                return format_html('<a href="{}">{}</a>',
                    reverse('admin:auth_user_change', args=[user.id]),
                    user.username
                )
            except:
                return f"User #{obj.changed_by_user_id}"
        return "System"
    changed_by_display.short_description = 'Changed By'
    
    def reason_display(self, obj):
        """Truncate long reasons"""
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return mark_safe('<span style="color: gray;">No reason provided</span>')
    reason_display.short_description = 'Reason'
    
    def has_add_permission(self, request):
        """Prevent manual creation - aliases created by GamePassportService"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing - alias history is immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup/GDPR"""
        return request.user.is_superuser


@admin.register(Achievement)
class AchievementAdmin(ModelAdmin):
    """Achievements admin"""
    
    list_display = ['user', 'emoji', 'name', 'rarity', 'earned_at']
    list_filter = ['rarity', 'earned_at']
    search_fields = ['user__username', 'name', 'description']
    readonly_fields = ['earned_at']
    
    fieldsets = [
        ('Achievement', {
            'fields': ['user', 'name', 'description', 'emoji', 'icon_url', 'rarity']
        }),
        ('Context', {
            'fields': ['earned_at', 'context'],
            'classes': ['collapse']
        }),
    ]


# @admin.register(Match) - REMOVED: Placeholder admin, unregistered until tournament system writes data
# Match model kept for future but admin hidden in Phase 5B
# class MatchAdmin(ModelAdmin):
#     pass


@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    """Certificates admin"""
    
    list_display = [
        'user',
        'title',
        'tournament_name',
        'issued_at',
        'verification_code',
        'is_verified',
    ]
    
    list_filter = ['is_verified', 'issued_at']
    search_fields = [
        'user__username',
        'title',
        'tournament_name',
        'verification_code',
    ]
    readonly_fields = ['verification_code', 'created_at']
    date_hierarchy = 'issued_at'
    
    fieldsets = [
        ('Certificate', {
            'fields': ['user', 'title', 'tournament_name', 'tournament_id']
        }),
        ('Images', {
            'fields': ['image', 'thumbnail_url']
        }),
        ('Verification', {
            'fields': ['issued_at', 'verification_code', 'is_verified']
        }),
        ('Metadata', {
            'fields': ['created_at', 'metadata'],
            'classes': ['collapse']
        }),
    ]


# ============================================================================
# UP-M2: ACTIVITY & STATS ADMINS
# ============================================================================

# @admin.register(UserActivity) - REMOVED: Orphaned model, no views write events
# UserActivity model exists but never used - unregistered in Phase 5B
# class UserActivityAdmin(ModelAdmin):
#     pass


# @admin.register(UserProfileStats) - REMOVED: Orphaned model, no views read stats
# UserProfileStats model exists but never queried by views - unregistered in Phase 5B
# class UserProfileStatsAdmin(ModelAdmin):
#     pass


# ============================================================================
# UP-M5: AUDIT TRAIL ADMIN
# ============================================================================

@admin.register(UserAuditEvent)
class UserAuditEventAdmin(ModelAdmin):
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


# ============================================================================
# GP-0 CONFIGURATION ADMIN
# ============================================================================

@admin.register(GameProfileConfig)
class GameProfileConfigAdmin(ModelAdmin):
    """
    GP-0 Game Passport Configuration (Singleton)
    
    Global settings for game passport system:
    - Identity change cooldown
    - Pinning limits
    - Regional requirements
    - Anti-abuse toggles
    
    Only ONE config row should exist (pk=1).
    """
    
    list_display = [
        'cooldown_display',
        'max_pinned_games',
        'allow_id_change',
        'require_region',
        'updated_at',
    ]
    
    fields = [
        'cooldown_days',
        'allow_id_change',
        'max_pinned_games',
        'require_region',
        'enable_ip_smurf_detection',
        'created_at',
        'updated_at',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def cooldown_display(self, obj):
        """Friendly cooldown display"""
        return f"{obj.cooldown_days} days"
    cooldown_display.short_description = 'Identity Change Cooldown'
    
    def has_add_permission(self, request):
        """Prevent creating new configs - singleton pattern"""
        # Allow add only if no config exists
        return not GameProfileConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting singleton config"""
        return False
    
    def get_queryset(self, request):
        """Ensure only singleton config is shown"""
        qs = super().get_queryset(request)
        return qs.filter(pk=1)  # Only show singleton
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to edit view if config exists"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        try:
            config = GameProfileConfig.get_config()
            # Redirect to edit view for singleton
            return HttpResponseRedirect(
                reverse('admin:user_profile_gameprofileconfig_change', args=[config.pk])
            )
        except Exception:
            # Config doesn't exist, show changelist (will have "Add" button)
            return super().changelist_view(request, extra_context)
    
    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }


# ============================================================================
# UP-PHASE6-C: Settings Redesign Models
# ============================================================================

@admin.register(NotificationPreferences)
class NotificationPreferencesAdmin(ModelAdmin):
    """
    Admin for NotificationPreferences model.
    
    Displays all email and platform notification preferences for users.
    Read-only view with link to user profile.
    """
    list_display = [
        'user_profile_link',
        'email_tournament_reminders',
        'email_match_results',
        'email_team_invites',
        'notify_tournament_start',
        'notify_team_messages',
        'updated_at',
    ]
    list_filter = [
        'email_tournament_reminders',
        'email_match_results',
        'email_team_invites',
        'email_achievements',
        'email_platform_updates',
        'notify_tournament_start',
        'notify_team_messages',
        'notify_follows',
        'notify_achievements',
    ]
    search_fields = ['user_profile__user__username', 'user_profile__display_name']
    readonly_fields = ['user_profile', 'created_at', 'updated_at']
    
    fieldsets = [
        ('User', {
            'fields': ['user_profile']
        }),
        ('Email Notifications', {
            'fields': [
                'email_tournament_reminders',
                'email_match_results',
                'email_team_invites',
                'email_achievements',
                'email_platform_updates',
            ]
        }),
        ('Platform Notifications', {
            'fields': [
                'notify_tournament_start',
                'notify_team_messages',
                'notify_follows',
                'notify_achievements',
            ]
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def user_profile_link(self, obj):
        """Link to user profile admin"""
        if obj.user_profile:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.user_profile.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user_profile)
        return '-'
    user_profile_link.short_description = 'User Profile'
    
    def has_add_permission(self, request):
        """Created automatically via UserProfile"""
        return False


@admin.register(WalletSettings)
class WalletSettingsAdmin(ModelAdmin):
    """
    Admin for WalletSettings model.
    
    Displays Bangladesh mobile banking settings and withdrawal preferences.
    Contains sensitive account numbers - restricted access recommended.
    
    SECURITY WARNING: Account numbers visible in list view.
    Restrict admin access to trusted staff only.
    """
    list_display = [
        'user_profile_link',
        'bkash_status',
        'nagad_status',
        'rocket_status',
        'auto_withdrawal_threshold',
        'updated_at',
    ]
    list_filter = [
        'bkash_enabled',
        'nagad_enabled',
        'rocket_enabled',
        'auto_convert_to_usd',
    ]
    search_fields = [
        'user_profile__user__username',
        'user_profile__display_name',
        'bkash_account',
        'nagad_account',
        'rocket_account',
    ]
    readonly_fields = ['user_profile', 'created_at', 'updated_at', 'enabled_methods_display']
    
    fieldsets = [
        ('User', {
            'fields': ['user_profile']
        }),
        ('bKash Settings', {
            'fields': ['bkash_enabled', 'bkash_account']
        }),
        ('Nagad Settings', {
            'fields': ['nagad_enabled', 'nagad_account']
        }),
        ('Rocket Settings', {
            'fields': ['rocket_enabled', 'rocket_account']
        }),
        ('Withdrawal Preferences', {
            'fields': [
                'auto_withdrawal_threshold',
                'auto_convert_to_usd',
                'enabled_methods_display',
            ]
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def user_profile_link(self, obj):
        """Link to user profile admin"""
        if obj.user_profile:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.user_profile.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user_profile)
        return '-'
    user_profile_link.short_description = 'User Profile'
    
    def bkash_status(self, obj):
        """Display bKash status with icon"""
        if obj.bkash_enabled and obj.bkash_account:
            return format_html('<span style="color: green;">✓ {}</span>', obj.bkash_account)
        return format_html('<span style="color: gray;">✗ Not configured</span>')
    bkash_status.short_description = 'bKash'
    
    def nagad_status(self, obj):
        """Display Nagad status with icon"""
        if obj.nagad_enabled and obj.nagad_account:
            return format_html('<span style="color: green;">✓ {}</span>', obj.nagad_account)
        return format_html('<span style="color: gray;">✗ Not configured</span>')
    nagad_status.short_description = 'Nagad'
    
    def rocket_status(self, obj):
        """Display Rocket status with icon"""
        if obj.rocket_enabled and obj.rocket_account:
            return format_html('<span style="color: green;">✓ {}</span>', obj.rocket_account)
        return format_html('<span style="color: gray;">✗ Not configured</span>')
    rocket_status.short_description = 'Rocket'
    
    def enabled_methods_display(self, obj):
        """Display list of enabled payment methods"""
        methods = obj.get_enabled_methods()
        if methods:
            return ', '.join(methods)
        return 'None'
    enabled_methods_display.short_description = 'Enabled Methods'
    
    def has_add_permission(self, request):
        """Created automatically via UserProfile"""
        return False


# ============================================================================
# P0 TROPHY SHOWCASE ADMIN - Equipped Cosmetics
# ============================================================================

@admin.register(TrophyShowcaseConfig)
class TrophyShowcaseConfigAdmin(ModelAdmin):
    """
    Admin for user's equipped cosmetics (borders, frames, pinned badges).
    
    Features:
    - List all showcase configs by user
    - Filter by border/frame
    - Search by username
    - View pinned badges with badge details
    - Validate unlocked cosmetics
    """
    list_display = [
        'user',
        'border',
        'frame',
        'pinned_count',
        'updated_at',
    ]
    list_filter = ['border', 'frame', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'pinned_badges_preview', 'validation_status']
    
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Equipped Cosmetics', {
            'fields': ['border', 'frame'],
            'description': 'Selected border and frame (must be unlocked by user).'
        }),
        ('Pinned Badges', {
            'fields': ['pinned_badge_ids', 'pinned_badges_preview'],
            'description': 'List of UserBadge IDs to display (max 5).'
        }),
        ('Validation', {
            'fields': ['validation_status'],
            'classes': ['collapse'],
            'description': 'Check if equipped cosmetics are unlocked.'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def pinned_count(self, obj):
        """Show number of pinned badges"""
        return len(obj.pinned_badge_ids)
    pinned_count.short_description = 'Pinned'
    
    def pinned_badges_preview(self, obj):
        """Show pinned badges with details"""
        if not obj.pinned_badge_ids:
            return 'No badges pinned'
        
        pinned = obj.get_pinned_badges()
        if not pinned:
            return 'No valid badges found'
        
        html_parts = []
        for ub in pinned:
            html_parts.append(
                f'<div style="margin: 5px 0; padding: 5px; border: 1px solid #ddd;">'
                f'{ub.badge.icon} <strong>{ub.badge.name}</strong><br>'
                f'Rarity: {ub.badge.get_rarity_display()}<br>'
                f'Earned: {ub.earned_at.strftime("%Y-%m-%d")}<br>'
                f'<a href="{reverse("admin:user_profile_userbadge_change", args=[ub.pk])}" target="_blank">View Badge</a>'
                f'</div>'
            )
        
        return format_html(''.join(html_parts))
    pinned_badges_preview.short_description = 'Pinned Badges'
    
    def validation_status(self, obj):
        """Validate equipped cosmetics against unlocks"""
        from apps.user_profile.services.trophy_showcase_service import (
            validate_showcase_config,
            get_unlocked_borders,
            get_unlocked_frames,
        )
        
        errors = validate_showcase_config(obj.user, obj)
        
        if not errors:
            return format_html('<span style="color: green;">✅ All cosmetics unlocked</span>')
        
        unlocked_borders = get_unlocked_borders(obj.user)
        unlocked_frames = get_unlocked_frames(obj.user)
        
        html_parts = [
            '<span style="color: red;">❌ Validation errors:</span><br>'
        ]
        
        for error in errors:
            html_parts.append(f'• {error}<br>')
        
        html_parts.append('<br><strong>Unlocked borders:</strong><br>')
        html_parts.append(', '.join(unlocked_borders) or 'None')
        
        html_parts.append('<br><br><strong>Unlocked frames:</strong><br>')
        html_parts.append(', '.join(unlocked_frames) or 'None')
        
        return format_html(''.join(html_parts))
    validation_status.short_description = 'Validation Status'
    
    def save_model(self, request, obj, form, change):
        """Validate before saving"""
        from apps.user_profile.services.trophy_showcase_service import validate_showcase_config
        
        try:
            errors = validate_showcase_config(obj.user, obj)
            if errors:
                messages.warning(
                    request,
                    f'Warning: Some cosmetics may not be unlocked: {", ".join(errors)}'
                )
            
            obj.full_clean()  # Triggers model.clean() validation
            super().save_model(request, obj, form, change)
            messages.success(request, f'Trophy showcase updated for {obj.user.username}')
        except Exception as e:
            messages.error(request, f'Validation failed: {str(e)}')
            raise


# ============================================================================
# P0 ENDORSEMENT ADMIN - Post-Match Skill Recognition
# ============================================================================

@admin.register(SkillEndorsement)
class SkillEndorsementAdmin(ModelAdmin):
    """
    Admin for post-match skill endorsements.
    
    Features:
    - List all endorsements with match/skill context
    - Filter by skill, flagged status, date
    - Search by endorser/receiver username
    - View match details and validation status
    - Flag endorsements for review (spam/manipulation detection)
    """
    list_display = [
        'id',
        'endorser_username',
        'receiver_username',
        'skill_name',
        'match_link',
        'tournament_name',
        'is_flagged',
        'created_at',
    ]
    list_filter = ['skill_name', 'is_flagged', 'created_at', 'match__tournament']
    search_fields = ['endorser__username', 'receiver__username', 'match__id']
    readonly_fields = [
        'match',
        'endorser',
        'receiver',
        'skill_name',
        'created_at',
        'ip_address',
        'user_agent',
        'match_context_display',
        'validation_status_display',
    ]
    
    fieldsets = [
        ('Endorsement Details', {
            'fields': ['endorser', 'receiver', 'skill_name', 'match'],
        }),
        ('Match Context', {
            'fields': ['match_context_display'],
            'description': 'Details about the match where this endorsement was earned.',
        }),
        ('Validation', {
            'fields': ['validation_status_display'],
            'description': 'Check if endorsement follows all permission rules.',
        }),
        ('Moderation', {
            'fields': ['is_flagged', 'flag_reason', 'reviewed_by', 'reviewed_at'],
            'classes': ['collapse'],
        }),
        ('Audit Trail', {
            'fields': ['created_at', 'ip_address', 'user_agent'],
            'classes': ['collapse'],
        }),
    ]
    
    def endorser_username(self, obj):
        """Show endorser username with profile link."""
        return obj.endorser.username
    endorser_username.short_description = 'Endorser'
    endorser_username.admin_order_field = 'endorser__username'
    
    def receiver_username(self, obj):
        """Show receiver username with profile link."""
        return obj.receiver.username
    receiver_username.short_description = 'Receiver'
    receiver_username.admin_order_field = 'receiver__username'
    
    def match_link(self, obj):
        """Show match ID as link."""
        if obj.match:
            url = reverse('admin:tournaments_match_change', args=[obj.match.pk])
            return format_html('<a href="{}" target="_blank">Match #{}</a>', url, obj.match_id)
        return '-'
    match_link.short_description = 'Match'
    
    def tournament_name(self, obj):
        """Show tournament name."""
        if obj.match and obj.match.tournament:
            return obj.match.tournament.name
        return '-'
    tournament_name.short_description = 'Tournament'
    tournament_name.admin_order_field = 'match__tournament__name'
    
    def match_context_display(self, obj):
        """Show match context details."""
        if not obj.match:
            return 'No match linked'
        
        context = obj.get_match_context()
        
        html_parts = [
            f'<strong>Match ID:</strong> {context["match_id"]}<br>',
            f'<strong>Tournament:</strong> {context["tournament_name"]}<br>',
            f'<strong>Round:</strong> {context["round_number"]}<br>',
            f'<strong>Match Number:</strong> {context["match_number"]}<br>',
            f'<strong>Completed At:</strong> {context["completed_at"].strftime("%Y-%m-%d %H:%M:%S") if context["completed_at"] else "Not set"}<br>',
        ]
        
        # Time window validation
        if obj.is_within_window:
            html_parts.append('<span style="color: green;">✅ Within 24-hour window</span>')
        else:
            html_parts.append('<span style="color: red;">❌ Outside 24-hour window</span>')
        
        return format_html(''.join(html_parts))
    match_context_display.short_description = 'Match Context'
    
    def validation_status_display(self, obj):
        """Validate endorsement against permission rules."""
        from apps.user_profile.services.endorsement_service import (
            is_match_participant,
            get_eligible_teammates,
        )
        
        errors = []
        
        # 1. Self-endorsement check
        if obj.endorser_id == obj.receiver_id:
            errors.append('❌ Self-endorsement (violates rules)')
        
        # 2. Match completion check
        if obj.match.state != 'completed':
            errors.append(f'❌ Match not completed (state: {obj.match.state})')
        
        # 3. Time window check
        if not obj.is_within_window:
            errors.append('❌ Outside 24-hour endorsement window')
        
        # 4. Participant verification
        is_participant, participant_error = is_match_participant(obj.endorser, obj.match)
        if not is_participant:
            errors.append(f'❌ Endorser not match participant: {participant_error}')
        
        # 5. Teammate verification (for team matches)
        if obj.match.tournament.registration_type == 'team':
            eligible_teammates = get_eligible_teammates(obj.endorser, obj.match)
            if obj.receiver not in eligible_teammates:
                errors.append('❌ Receiver not eligible teammate')
        
        if not errors:
            return format_html('<span style="color: green;">✅ All validation checks passed</span>')
        
        html_parts = ['<span style="color: red;">Validation errors:</span><br>']
        for error in errors:
            html_parts.append(f'{error}<br>')
        
        return format_html(''.join(html_parts))
    validation_status_display.short_description = 'Validation Status'
    
    def has_add_permission(self, request):
        """Disable manual creation (endorsements created via service only)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion (endorsements are immutable)."""
        return False
    
    def save_model(self, request, obj, form, change):
        """Allow flagging but prevent other modifications."""
        if change:
            # Only allow updating moderation fields
            allowed_fields = {'is_flagged', 'flag_reason', 'reviewed_by', 'reviewed_at'}
            changed_fields = set(form.changed_data)
            
            if not changed_fields.issubset(allowed_fields):
                messages.error(
                    request,
                    'Endorsements are immutable. Only moderation fields can be updated.'
                )
                return
            
            # Update reviewer info if flagging
            if 'is_flagged' in changed_fields and obj.is_flagged:
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        
        super().save_model(request, obj, form, change)


@admin.register(EndorsementOpportunity)
class EndorsementOpportunityAdmin(ModelAdmin):
    """
    Admin for endorsement opportunity tracking.
    
    Shows 24-hour windows for players to endorse teammates after match completion.
    Used for analytics and notification management.
    """
    list_display = [
        'id',
        'player_username',
        'match_link',
        'is_used',
        'is_expired_display',
        'time_remaining_display',
        'notified',
        'expires_at',
    ]
    list_filter = ['is_used', 'notified', 'expires_at']
    search_fields = ['player__username', 'match__id']
    readonly_fields = ['match', 'player', 'expires_at', 'is_used', 'used_at', 'created_at']
    
    fieldsets = [
        ('Opportunity Details', {
            'fields': ['match', 'player', 'expires_at'],
        }),
        ('Status', {
            'fields': ['is_used', 'used_at'],
        }),
        ('Notifications', {
            'fields': ['notified', 'notified_at'],
        }),
        ('Timestamps', {
            'fields': ['created_at'],
        }),
    ]
    
    def player_username(self, obj):
        """Show player username."""
        return obj.player.username
    player_username.short_description = 'Player'
    player_username.admin_order_field = 'player__username'
    
    def match_link(self, obj):
        """Show match ID as link."""
        if obj.match:
            url = reverse('admin:tournaments_match_change', args=[obj.match.pk])
            return format_html('<a href="{}" target="_blank">Match #{}</a>', url, obj.match_id)
        return '-'
    match_link.short_description = 'Match'
    
    def is_expired_display(self, obj):
        """Show expired status."""
        if obj.is_expired:
            return format_html('<span style="color: red;">❌ Expired</span>')
        return format_html('<span style="color: green;">✅ Active</span>')
    is_expired_display.short_description = 'Status'
    
    def time_remaining_display(self, obj):
        """Show time remaining until expiry."""
        if obj.is_expired:
            return '-'
        
        remaining = obj.time_remaining
        if not remaining:
            return '-'
        
        hours = remaining.total_seconds() / 3600
        return f'{hours:.1f} hours'
    time_remaining_display.short_description = 'Time Remaining'
    
    def has_add_permission(self, request):
        """Disable manual creation (opportunities created by system)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return True

# ============================================================================
# P0 BOUNTY SYSTEM ADMINS
# ============================================================================

@admin.register(Bounty)
class BountyAdmin(ModelAdmin):
    """
    Admin interface for Bounty challenges.
    
    Features:
    - Filter by status, game, disputed bounties
    - Search by title, creator, acceptor
    - Track escrow status and payouts
    - Admin actions to resolve disputes
    """
    
    list_display = [
        'id',
        'title',
        'creator_username',
        'acceptor_username',
        'game',
        'stake_amount',
        'status_badge',
        'winner_username',
        'created_at',
        'expires_at',
    ]
    
    list_filter = [
        'status',
        'game',
        'created_at',
        ('expires_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'title',
        'description',
        'creator__username',
        'acceptor__username',
        'id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'accepted_at',
        'started_at',
        'result_submitted_at',
        'completed_at',
        'payout_amount',
        'platform_fee',
        'escrow_status_display',
        'time_remaining_display',
        'dispute_info_display',
    ]
    
    fieldsets = [
        ('Challenge Info', {
            'fields': [
                'id',
                'title',
                'description',
                'game',
                'stake_amount',
            ]
        }),
        ('Participants', {
            'fields': [
                'creator',
                'acceptor',
                'target_user',
                'winner',
            ]
        }),
        ('Status', {
            'fields': [
                'status',
                'escrow_status_display',
                'time_remaining_display',
                'dispute_info_display',
            ]
        }),
        ('Financial', {
            'fields': [
                'payout_amount',
                'platform_fee',
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at',
                'accepted_at',
                'started_at',
                'result_submitted_at',
                'completed_at',
                'expires_at',
            ]
        }),
        ('Match Reference', {
            'fields': ['match'],
            'classes': ['collapse'],
        }),
        ('Metadata', {
            'fields': ['ip_address', 'user_agent'],
            'classes': ['collapse'],
        }),
    ]
    
    actions = ['mark_as_disputed', 'force_expire']
    
    def creator_username(self, obj):
        """Show creator username as link."""
        if obj.creator:
            url = reverse('admin:auth_user_change', args=[obj.creator.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.creator.username)
        return '-'
    creator_username.short_description = 'Creator'
    creator_username.admin_order_field = 'creator__username'
    
    def acceptor_username(self, obj):
        """Show acceptor username as link."""
        if obj.acceptor:
            url = reverse('admin:auth_user_change', args=[obj.acceptor.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.acceptor.username)
        return '-'
    acceptor_username.short_description = 'Acceptor'
    acceptor_username.admin_order_field = 'acceptor__username'
    
    def winner_username(self, obj):
        """Show winner username as link."""
        if obj.winner:
            url = reverse('admin:auth_user_change', args=[obj.winner.pk])
            return format_html('<a href="{}" target="_blank">🏆 {}</a>', url, obj.winner.username)
        return '-'
    winner_username.short_description = 'Winner'
    winner_username.admin_order_field = 'winner__username'
    
    def status_badge(self, obj):
        """Show status with color badge."""
        colors = {
            'open': '#4CAF50',
            'accepted': '#2196F3',
            'in_progress': '#FF9800',
            'pending_result': '#FFC107',
            'disputed': '#F44336',
            'completed': '#4CAF50',
            'expired': '#9E9E9E',
            'cancelled': '#9E9E9E',
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def escrow_status_display(self, obj):
        """Show escrow lock status."""
        if obj.status in ['open', 'accepted', 'in_progress', 'pending_result', 'disputed']:
            return format_html('<span style="color: orange;">🔒 Locked ({} DC)</span>', obj.stake_amount)
        elif obj.status == 'completed':
            return format_html('<span style="color: green;">✅ Released (paid {} DC to winner)</span>', obj.payout_amount or 0)
        else:
            return format_html('<span style="color: gray;">↩️ Refunded ({} DC)</span>', obj.stake_amount)
    escrow_status_display.short_description = 'Escrow Status'
    
    def time_remaining_display(self, obj):
        """Show time remaining until expiry (for OPEN bounties)."""
        if obj.status != 'open' or not obj.expires_at:
            return '-'
        
        remaining = obj.time_until_expiry
        if not remaining or remaining.total_seconds() <= 0:
            return format_html('<span style="color: red;">❌ Expired</span>')
        
        hours = remaining.total_seconds() / 3600
        if hours < 1:
            return format_html('<span style="color: red;">⚠️ {} mins</span>', int(remaining.total_seconds() / 60))
        elif hours < 12:
            return format_html('<span style="color: orange;">⚠️ {:.1f} hours</span>', hours)
        else:
            return format_html('<span style="color: green;">{:.1f} hours</span>', hours)
    time_remaining_display.short_description = 'Time Remaining'
    
    def dispute_info_display(self, obj):
        """Show dispute information if exists."""
        if not hasattr(obj, 'dispute'):
            return format_html('<span style="color: green;">✅ No dispute</span>')
        
        dispute = obj.dispute
        if dispute.is_resolved:
            return format_html(
                '<span style="color: blue;">✅ Resolved: {}</span>',
                dispute.get_status_display()
            )
        else:
            return format_html(
                '<span style="color: red;">⚠️ DISPUTED by {} - {}</span>',
                dispute.disputer.username,
                dispute.status
            )
    dispute_info_display.short_description = 'Dispute Status'
    
    def mark_as_disputed(self, request, queryset):
        """Admin action: Mark bounties for review (disputed)."""
        count = queryset.filter(status='pending_result').update(status='disputed')
        self.message_user(request, f'{count} bounties marked as disputed', messages.SUCCESS)
    mark_as_disputed.short_description = 'Mark as DISPUTED (manual review)'
    
    def force_expire(self, request, queryset):
        """Admin action: Force expire open bounties."""
        from apps.user_profile.services.bounty_service import expire_bounty
        
        count = 0
        for bounty in queryset.filter(status='open'):
            try:
                expire_bounty(bounty.id)
                count += 1
            except Exception as e:
                self.message_user(request, f'Failed to expire bounty {bounty.id}: {e}', messages.ERROR)
        
        self.message_user(request, f'{count} bounties expired', messages.SUCCESS)
    force_expire.short_description = 'Force expire OPEN bounties (refund)'


@admin.register(BountyAcceptance)
class BountyAcceptanceAdmin(ModelAdmin):
    """Admin interface for bounty acceptances."""
    
    list_display = [
        'bounty_id',
        'bounty_title',
        'acceptor_username',
        'accepted_at',
    ]
    
    readonly_fields = [
        'bounty',
        'acceptor',
        'accepted_at',
        'ip_address',
        'user_agent',
    ]
    
    def bounty_id(self, obj):
        """Show bounty ID as link."""
        url = reverse('admin:user_profile_bounty_change', args=[obj.bounty.pk])
        return format_html('<a href="{}" target="_blank">Bounty #{}</a>', url, obj.bounty.id)
    bounty_id.short_description = 'Bounty'
    
    def bounty_title(self, obj):
        """Show bounty title."""
        return obj.bounty.title
    bounty_title.short_description = 'Title'
    
    def acceptor_username(self, obj):
        """Show acceptor username."""
        return obj.acceptor.username
    acceptor_username.short_description = 'Acceptor'
    
    def has_add_permission(self, request):
        """Disable manual creation (created via service)."""
        return False


@admin.register(BountyProof)
class BountyProofAdmin(ModelAdmin):
    """Admin interface for bounty proof submissions."""
    
    list_display = [
        'id',
        'bounty_link',
        'submitted_by_username',
        'claimed_winner_username',
        'proof_type',
        'proof_url_link',
        'submitted_at',
    ]
    
    list_filter = [
        'proof_type',
        'submitted_at',
    ]
    
    search_fields = [
        'bounty__title',
        'submitted_by__username',
        'claimed_winner__username',
        'description',
    ]
    
    readonly_fields = [
        'bounty',
        'submitted_by',
        'claimed_winner',
        'submitted_at',
        'ip_address',
    ]
    
    fieldsets = [
        ('Bounty Info', {
            'fields': ['bounty']
        }),
        ('Submission', {
            'fields': [
                'submitted_by',
                'claimed_winner',
                'proof_type',
                'proof_url',
                'description',
            ]
        }),
        ('Metadata', {
            'fields': ['submitted_at', 'ip_address'],
        }),
    ]
    
    def bounty_link(self, obj):
        """Show bounty ID as link."""
        url = reverse('admin:user_profile_bounty_change', args=[obj.bounty.pk])
        return format_html('<a href="{}" target="_blank">Bounty #{}</a>', url, obj.bounty.id)
    bounty_link.short_description = 'Bounty'
    
    def submitted_by_username(self, obj):
        """Show submitter username."""
        return obj.submitted_by.username
    submitted_by_username.short_description = 'Submitted By'
    
    def claimed_winner_username(self, obj):
        """Show claimed winner username."""
        return format_html('🏆 {}', obj.claimed_winner.username)
    claimed_winner_username.short_description = 'Claimed Winner'
    
    def proof_url_link(self, obj):
        """Show proof URL as clickable link."""
        return format_html('<a href="{}" target="_blank">View Proof</a>', obj.proof_url)
    proof_url_link.short_description = 'Proof'
    
    def has_add_permission(self, request):
        """Disable manual creation (created via service)."""
        return False


@admin.register(BountyDispute)
class BountyDisputeAdmin(ModelAdmin):
    """
    Admin interface for bounty disputes.
    
    Features:
    - Filter by status, open disputes
    - Assign moderators
    - Resolve disputes with decision
    """
    
    list_display = [
        'bounty_id',
        'bounty_title',
        'disputer_username',
        'status_badge',
        'assigned_moderator_username',
        'created_at',
        'resolved_at',
    ]
    
    list_filter = [
        'status',
        'created_at',
        'resolved_at',
    ]
    
    search_fields = [
        'bounty__title',
        'disputer__username',
        'reason',
        'resolution',
    ]
    
    readonly_fields = [
        'bounty',
        'disputer',
        'created_at',
        'resolved_at',
    ]
    
    fieldsets = [
        ('Dispute Info', {
            'fields': [
                'bounty',
                'disputer',
                'reason',
                'created_at',
            ]
        }),
        ('Moderation', {
            'fields': [
                'status',
                'assigned_moderator',
                'moderator_notes',
                'resolution',
                'resolved_at',
            ]
        }),
    ]
    
    actions = ['assign_to_me', 'mark_under_review', 'mark_resolved', 'refund_creator', 'award_challenger']
    
    def bounty_id(self, obj):
        """Show bounty ID as link."""
        url = reverse('admin:user_profile_bounty_change', args=[obj.bounty.pk])
        return format_html('<a href="{}" target="_blank">#{}</a>', url, obj.bounty.id)
    bounty_id.short_description = 'Bounty ID'
    
    def bounty_title(self, obj):
        """Show bounty title."""
        return obj.bounty.title
    bounty_title.short_description = 'Bounty Title'
    
    def disputer_username(self, obj):
        """Show disputer username."""
        return obj.disputer.username
    disputer_username.short_description = 'Disputed By'
    
    def assigned_moderator_username(self, obj):
        """Show assigned moderator."""
        if obj.assigned_moderator:
            return obj.assigned_moderator.username
        return format_html('<span style="color: red;">⚠️ Unassigned</span>')
    assigned_moderator_username.short_description = 'Moderator'
    
    def status_badge(self, obj):
        """Show status with color badge."""
        colors = {
            'open': '#F44336',
            'under_review': '#FF9800',
            'resolved_confirm': '#4CAF50',
            'resolved_reverse': '#4CAF50',
            'resolved_void': '#9E9E9E',
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def assign_to_me(self, request, queryset):
        """Admin action: Assign selected disputes to me."""
        count = queryset.filter(assigned_moderator__isnull=True).update(
            assigned_moderator=request.user,
            status='under_review'
        )
        self.message_user(request, f'{count} disputes assigned to you', messages.SUCCESS)
    assign_to_me.short_description = 'Assign to me'
    
    def mark_under_review(self, request, queryset):
        """Admin action: Mark as under review."""
        count = queryset.filter(status='open').update(status='under_review')
        self.message_user(request, f'{count} disputes marked under review', messages.SUCCESS)
    mark_under_review.short_description = 'Mark as under review'
    
    def mark_resolved(self, request, queryset):
        """Admin action: Mark disputes as resolved (confirm original result)."""
        count = queryset.filter(status__in=['open', 'under_review']).update(
            status='resolved_confirm',
            resolved_at=timezone.now(),
            assigned_moderator=request.user
        )
        self.message_user(request, f'{count} disputes marked as resolved', messages.SUCCESS)
    mark_resolved.short_description = 'Mark as Resolved (Confirm Result)'
    
    def refund_creator(self, request, queryset):
        """Admin action: Resolve dispute and refund bounty creator."""
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
        """Admin action: Resolve dispute and award challenger."""
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
    
    def has_add_permission(self, request):
        """Disable manual creation (created via service)."""
        return False


# ==============================================================================
# MEDIA ADMINS - Phase 2B.4
# ==============================================================================

@admin.register(StreamConfig)
class StreamConfigAdmin(ModelAdmin):
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
    
    def has_add_permission(self, request):
        """Allow manual creation for testing."""
        return True


@admin.register(HighlightClip)
class HighlightClipAdmin(ModelAdmin):
    """Admin for user highlight clips (YouTube, Twitch, Medal.tv)."""
    
    list_display = ['user', 'title', 'platform', 'game', 'display_order', 'created_at']
    list_filter = ['platform', 'game', 'created_at']
    search_fields = ['user__username', 'title', 'video_id']
    readonly_fields = ['platform', 'video_id', 'embed_url', 'thumbnail_url', 'created_at', 'updated_at']
    
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
class PinnedHighlightAdmin(ModelAdmin):
    """Admin for pinned highlight clips (featured on profile)."""
    
    list_display = ['user', 'clip', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'clip__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Pinned Highlight', {
            'fields': ('user', 'clip')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Allow manual pinning."""
        return True


# ==============================================================================
# LOADOUT ADMINS - Phase 2B.4
# ==============================================================================

@admin.register(HardwareGear)
class HardwareGearAdmin(ModelAdmin):
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
class GameConfigAdmin(ModelAdmin):
    """Admin for per-game configuration settings (sensitivity, crosshair, keybinds)."""
    
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


# ==============================================================================
# SHOWCASE ADMINS - Phase 2B.4
# ==============================================================================

@admin.register(ProfileShowcase)
class ProfileShowcaseAdmin(ModelAdmin):
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
    
    def has_add_permission(self, request):
        """Allow manual creation."""
        return True


@admin.register(ProfileAboutItem)
class ProfileAboutItemAdmin(ModelAdmin):
    """Admin for profile About section items (Facebook-style)."""
    
    list_display = ['user_profile', 'item_type', 'visibility', 'display_order', 'created_at']
    list_filter = ['item_type', 'visibility', 'created_at']
    search_fields = ['user_profile__display_name', 'content_text']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Profile & Type', {
            'fields': ('user_profile', 'item_type')
        }),
        ('Content', {
            'fields': ('content_text', 'source_model', 'source_id')
        }),
        ('Display', {
            'fields': ('visibility', 'display_order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['user_profile', 'display_order']