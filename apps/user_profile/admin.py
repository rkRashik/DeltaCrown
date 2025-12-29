# apps/user_profile/admin.py
"""
Django Admin configuration for User Profile models.
Phase 3 Implementation - All new models registered.
UP-ADMIN-01: Professional platform-grade admin with audit-first safeguards.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q

from .models import (
    UserProfile,
    PrivacySettings,
    VerificationRecord,
    Badge,
    UserBadge,
    # Phase 3 Models
    # SocialLink - REMOVED: Orphaned model, no view usage
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
)
from .services.audit import AuditService
from .services.tournament_stats import TournamentStatsService
from .services.economy_sync import sync_profile_by_user_id, get_balance_drift
from .admin.forms import UserProfileAdminForm


# ============================================================================
# INLINE ADMINS
# ============================================================================

class PrivacySettingsInline(admin.StackedInline):
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


class SocialLinkInline(admin.TabularInline):
    """Inline social links editor"""
    model = SocialLink
    extra = 0
    fields = ['platform', 'url', 'handle', 'is_verified']
    readonly_fields = ['is_verified']


class GameProfileInline(admin.TabularInline):
    """Inline game profiles editor - replaces JSON field"""
    model = GameProfile
    extra = 1
    fields = ['game', 'in_game_name', 'rank_name', 'main_role', 'matches_played', 'win_rate', 'updated_at']
    readonly_fields = ['updated_at']
    verbose_name = "Game Profile (Normalized)"
    verbose_name_plural = "Game Profiles (Normalized Model)"


class GameProfileAliasInline(admin.TabularInline):
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


class UserBadgeInline(admin.TabularInline):
    """Inline user badges editor"""
    model = UserBadge
    extra = 0
    fields = ['badge', 'earned_at', 'is_pinned']
    readonly_fields = ['earned_at']


class NotificationPreferencesInline(admin.StackedInline):
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


class WalletSettingsInline(admin.StackedInline):
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

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Enhanced UserProfile admin with Phase 3 features + UP-M1 public_id"""
    
    form = UserProfileAdminForm
    
    list_display = [
        'display_name',
        'username_link',
        'public_id',
        'games_count',
        'games_summary',
        'level',
        'reputation_score',
        'kyc_badge',
        'region',
        'created_at',
    ]
    
    list_filter = [
        'kyc_status',
        'region',
        'stream_status',
        'created_at',
    ]
    
    search_fields = [
        'display_name',
        'user__username',
        'user__email',
        'real_full_name',
        'uuid',
        'public_id',
    ]
    
    readonly_fields = [
        'uuid',
        'user',
        'public_id',
        'age',
        'created_at',
        'updated_at',
        'kyc_verified_at',
        'deltacoin_balance',  # Economy-owned: updated by economy app only
        'lifetime_earnings',  # Economy-owned: updated by economy app only
    ]
    
    fieldsets = [
        ('User Account', {
            'fields': ['user', 'uuid', 'public_id', 'created_at', 'updated_at'],
            'description': 'System identifiers and registration metadata (read-only)'
        }),
        ('Public Identity', {
            'fields': ['display_name', 'slug', 'avatar', 'banner', 'bio', 'pronouns'],
            'description': 'Visible to all visitors on profile page'
        }),
        ('Legal Identity (KYC)', {
            'fields': [
                'real_full_name',
                'date_of_birth',
                'age',
                'nationality',
                'kyc_status',
                'kyc_verified_at',
            ],
            'classes': ['collapse'],
            'description': 'Verification data - immutable after KYC approval'
        }),
        ('Location', {
            'fields': ['country', 'region', 'city', 'postal_code', 'address'],
            'classes': ['collapse'],
            'description': 'Geographic data for tournaments and leaderboards'
        }),
        ('Demographics', {  # Renamed from 'Contact'
            'fields': ['phone', 'gender'],
            'classes': ['collapse'],
            'description': 'Optional demographic information'
        }),
        ('Emergency Contact', {
            'fields': [
                'emergency_contact_name',
                'emergency_contact_phone',
                'emergency_contact_relation',
            ],
            'classes': ['collapse'],
            'description': 'For LAN events and emergencies only'
        }),
        ('Social Links', {
            'fields': [
                'youtube_link',
                'twitch_link',
                'discord_id',
                'facebook',
                'instagram',
                'tiktok',
                'twitter',
                'stream_status',
            ],
            'classes': ['collapse'],
            'description': 'Connected platforms and streaming status'
        }),
        ('Platform Preferences', {
            'fields': [
                'preferred_language',
                'timezone_pref',
                'time_format',
                'theme_preference',
            ],
            'description': 'User interface and localization preferences (UP-PHASE6-C)'
        }),
        ('Competitive Career', {
            'fields': ['reputation_score', 'skill_rating'],
            'description': 'Competitive metrics and rankings'
        }),
        ('Gamification', {
            'fields': [
                'level',
                'xp',
                'pinned_badges',
                'inventory_items',
            ],
            'description': 'Progression system and rewards'
        }),
        ('Economy', {
            'fields': ['deltacoin_balance', 'lifetime_earnings'],
            'description': 'Financial data - balance is cached from economy app (read-only)'
        }),
    ]
    
    inlines = [
        # Core Settings (Always Edit)
        PrivacySettingsInline,
        NotificationPreferencesInline,
        WalletSettingsInline,
        
        # Competitive Data
        GameProfileInline,
        
        # Optional/Decorative
        UserBadgeInline,
    ]
    
    def username_link(self, obj):
        """Link to user admin"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    username_link.short_description = 'Username'
    
    def games_count(self, obj):
        """Display count of games from Game Passport table"""
        from apps.user_profile.services.game_passport_service import GamePassportService
        try:
            return GamePassportService.list_passports(user=obj.user).count()
        except Exception:
            return 0
    games_count.short_description = 'Passports'
    # Note: Sorting disabled - would require queryset annotation
    
    def games_summary(self, obj):
        """Display summary of games from Game Passport table (first 3 game names)"""
        from apps.user_profile.services.game_passport_service import GamePassportService
        try:
            passports = list(GamePassportService.list_passports(user=obj.user)[:4])
            if not passports:
                return mark_safe('<span style="color: gray;">No games</span>')
            
            # Extract game names
            games = [gp.game.upper() for gp in passports[:3]]
            
            # Format display
            if len(passports) > 3:
                summary = ', '.join(games) + f' +{len(passports) - 3} more'
            else:
                summary = ', '.join(games)
            
            return mark_safe(f'<span title="{len(passports)} games">{summary}</span>')
        except Exception:
            return mark_safe('<span style="color: gray;">Error</span>')
    games_summary.short_description = 'Game Passports'
    
    def kyc_badge(self, obj):
        """Display KYC status badge"""
        if obj.kyc_status == 'verified':
            return mark_safe('<span style="color: green;">✓ Verified</span>')
        elif obj.kyc_status == 'pending':
            return mark_safe('<span style="color: orange;">⏳ Pending</span>')
        elif obj.kyc_status == 'rejected':
            return mark_safe('<span style="color: red;">✗ Rejected</span>')
        return mark_safe('<span style="color: gray;">— Unverified</span>')
    kyc_badge.short_description = 'KYC Status'
    
    def save_model(self, request, obj, form, change):
        """
        Override save to record audit trail for game_profiles changes.
        
        DEPRECATED: game_profiles JSON field. Phase 4 removal.
        Admin edits to game profiles should go through GameProfile model admin.
        This is kept for backwards compatibility only.
        """
        if change:
            # Get original object from DB
            try:
                original = UserProfile.objects.get(pk=obj.pk)
                old_game_profiles = original.game_profiles
                new_game_profiles = obj.game_profiles
                
                # Check if game_profiles changed
                if old_game_profiles != new_game_profiles:
                    # Warn admin that JSON editing is deprecated
                    self.message_user(
                        request,
                        "⚠️ WARNING: Editing game_profiles JSON is deprecated. "
                        "Use GameProfile model admin instead. Phase 4 removal planned.",
                        messages.WARNING
                    )
                    
                    # Record audit event AFTER save
                    super().save_model(request, obj, form, change)
                    
                    # Create audit record
                    AuditService.record_change(
                        actor_user_id=request.user.id,
                        object_type='UserProfile',
                        object_id=obj.id,
                        action='update',
                        field_name='game_profiles',
                        old_value=old_game_profiles,
                        new_value=new_game_profiles,
                        metadata={
                            'source': 'django_admin',
                            'display_name': obj.display_name,
                            'username': obj.user.username,
                            'deprecated': True,  # Mark as deprecated write
                        }
                    )
                    return
            except UserProfile.DoesNotExist:
                pass
        
        # Default save
        super().save_model(request, obj, form, change)
    
    actions = ['normalize_game_profiles']
    
    def normalize_game_profiles(self, request, queryset):
        """Admin action to normalize/validate game profiles for selected users"""
        from apps.user_profile.admin.game_profiles_field import GameProfilesField
        
        field = GameProfilesField()
        success_count = 0
        error_count = 0
        
        for profile in queryset:
            try:
                # Validate and normalize
                normalized = field.to_python(profile.game_profiles)
                
                # Check if changes needed
                if normalized != profile.game_profiles:
                    old_value = profile.game_profiles
                    profile.game_profiles = normalized
                    profile.save(update_fields=['game_profiles'])
                    
                    # Record audit
                    AuditService.record_change(
                        actor_user_id=request.user.id,
                        object_type='UserProfile',
                        object_id=profile.id,
                        action='normalize',
                        field_name='game_profiles',
                        old_value=old_value,
                        new_value=normalized,
                        metadata={
                            'source': 'django_admin_action',
                            'action_name': 'normalize_game_profiles',
                        }
                    )
                    success_count += 1
                else:
                    # Already valid
                    success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Error normalizing {profile.display_name}: {e}",
                    messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully normalized {success_count} profile(s). Audit events recorded.",
                messages.SUCCESS
            )
        if error_count > 0:
            self.message_user(
                request,
                f"Failed to normalize {error_count} profile(s).",
                messages.WARNING
            )
    normalize_game_profiles.short_description = "Normalize/Validate Game Profiles"


@admin.register(PrivacySettings)
class PrivacySettingsAdmin(admin.ModelAdmin):
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
class VerificationRecordAdmin(admin.ModelAdmin):
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
class BadgeAdmin(admin.ModelAdmin):
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
class UserBadgeAdmin(admin.ModelAdmin):
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
# class SocialLinkAdmin(admin.ModelAdmin):
#     """Social links admin - ORPHANED, unregistered in Phase 5B"""
#     pass


@admin.register(GameProfile)
class GameProfileAdmin(admin.ModelAdmin):
    """
    GP-0 Game Passport Admin
    
    Fully operational admin for game passports with:
    - Identity change tracking
    - Cooldown enforcement
    - Pinning management
    - Privacy controls
    - Audit integration
    """
    
    list_display = [
        'user',
        'game',
        'in_game_name',
        'identity_key',
        'visibility',
        'is_lft',
        'is_pinned',
        'lock_status_display',
        'updated_at',
    ]
    
    list_filter = [
        'game',
        'visibility',
        'is_lft',
        'is_pinned',
        'status',
        ('locked_until', admin.EmptyFieldListFilter),  # GP-FE-MVP-01: Locked/unlocked filter
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
        'created_at',
        'updated_at',
    ]
    
    fieldsets = [
        ('Identity', {
            'fields': [
                'user',
                'game',
                'game_display_name',
                'in_game_name',
                'identity_key',
                'region',
            ]
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
        ('Rank & Stats', {
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
            'classes': ['collapse']
        }),
        ('Metadata (JSON)', {
            'fields': ['metadata'],
            'classes': ['collapse'],
            'description': 'Per-game extras (e.g., MLBB zone_id, region codes)',
        }),
        ('Lock Info', {
            'fields': [
                'locked_until_display',
                'lock_countdown_display',
            ],
            'classes': ['collapse']
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
        Ensure identity changes go through GamePassportService
        
        Note: Direct admin edits bypass cooldown. For production,
        consider making in_game_name readonly and requiring service layer.
        """
        # Check if identity changed
        if change:
            try:
                old_obj = GameProfile.objects.get(pk=obj.pk)
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
                }
            )
    
    actions = ['unlock_identity_changes', 'pin_passports', 'unpin_passports']
    
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
class GameProfileAliasAdmin(admin.ModelAdmin):
    """
    Game Passport Alias History Admin
    
    Read-only view of all identity changes for audit trail.
    Shows who changed what, when, and why.
    """
    
    list_display = [
        'game_profile',
        'old_name',
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
        'old_name',
        'reason',
    ]
    
    readonly_fields = [
        'game_profile',
        'old_name',
        'changed_at',
        'changed_by_user_id',
        'reason',
    ]
    
    fieldsets = [
        ('Identity Change', {
            'fields': [
                'game_profile',
                'old_name',
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
class AchievementAdmin(admin.ModelAdmin):
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
# class MatchAdmin(admin.ModelAdmin):
#     pass


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
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
# class UserActivityAdmin(admin.ModelAdmin):
#     pass


# @admin.register(UserProfileStats) - REMOVED: Orphaned model, no views read stats
# UserProfileStats model exists but never queried by views - unregistered in Phase 5B
# class UserProfileStatsAdmin(admin.ModelAdmin):
#     pass


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


# ============================================================================
# GP-0 CONFIGURATION ADMIN
# ============================================================================

@admin.register(GameProfileConfig)
class GameProfileConfigAdmin(admin.ModelAdmin):
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
class NotificationPreferencesAdmin(admin.ModelAdmin):
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
class WalletSettingsAdmin(admin.ModelAdmin):
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
