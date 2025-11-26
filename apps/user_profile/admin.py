# apps/user_profile/admin.py
"""
Django Admin configuration for User Profile models.
Phase 3 Implementation - All new models registered.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

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
    Match,
    Certificate,
)


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
    """Inline game profiles editor"""
    model = GameProfile
    extra = 0
    fields = ['game', 'in_game_name', 'rank_name', 'matches_played', 'win_rate', 'is_verified']
    readonly_fields = ['is_verified', 'game_display_name']


class UserBadgeInline(admin.TabularInline):
    """Inline user badges editor"""
    model = UserBadge
    extra = 0
    fields = ['badge', 'earned_at', 'is_pinned']
    readonly_fields = ['earned_at']


# ============================================================================
# MAIN MODEL ADMINS
# ============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Enhanced UserProfile admin with Phase 3 features"""
    
    list_display = [
        'display_name',
        'username_link',
        'level',
        'reputation_score',
        'kyc_badge',
        'region',
        'created_at',
    ]
    
    list_filter = [
        'kyc_status',
        'region',
        'is_private',
        'stream_status',
        'created_at',
    ]
    
    search_fields = [
        'display_name',
        'user__username',
        'user__email',
        'real_full_name',
        'uuid',
    ]
    
    readonly_fields = [
        'uuid',
        'user',
        'age',
        'created_at',
        'updated_at',
        'kyc_verified_at',
    ]
    
    fieldsets = [
        ('User Account', {
            'fields': ['user', 'uuid', 'created_at', 'updated_at']
        }),
        ('Public Identity', {
            'fields': ['display_name', 'slug', 'avatar', 'banner', 'bio', 'pronouns']
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
            'classes': ['collapse']
        }),
        ('Location', {
            'fields': ['country', 'region', 'city', 'postal_code', 'address']
        }),
        ('Contact', {
            'fields': ['phone', 'gender'],
            'classes': ['collapse']
        }),
        ('Emergency Contact', {
            'fields': [
                'emergency_contact_name',
                'emergency_contact_phone',
                'emergency_contact_relation',
            ],
            'classes': ['collapse']
        }),
        ('Legacy Social Links', {
            'description': 'Note: New social links use SocialLink model (see inline below)',
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
            'classes': ['collapse']
        }),
        ('Legacy Game IDs', {
            'description': 'Note: New game profiles use GameProfile model (see inline below)',
            'fields': [
                'riot_id',
                'riot_tagline',
                'steam_id',
                'mlbb_id',
                'mlbb_server_id',
                'ea_id',
                'pubg_mobile_id',
                'free_fire_id',
                'codm_uid',
                'efootball_id',
            ],
            'classes': ['collapse']
        }),
        ('Competitive Career', {
            'fields': ['reputation_score', 'skill_rating']
        }),
        ('Gamification', {
            'fields': [
                'level',
                'xp',
                'pinned_badges',
                'inventory_items',
            ]
        }),
        ('Economy', {
            'fields': ['deltacoin_balance', 'lifetime_earnings']
        }),
        ('Privacy', {
            'fields': [
                'is_private',
                'show_email',
                'show_phone',
                'show_socials',
                'show_address',
                'show_age',
                'show_gender',
                'show_country',
                'show_real_name',
            ],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [
        PrivacySettingsInline,
        SocialLinkInline,
        GameProfileInline,
        UserBadgeInline,
    ]
    
    def username_link(self, obj):
        """Link to user admin"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    username_link.short_description = 'Username'
    
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

@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    """Social links admin"""
    
    list_display = ['user', 'platform', 'handle', 'url', 'is_verified', 'created_at']
    list_filter = ['platform', 'is_verified', 'created_at']
    search_fields = ['user__username', 'handle', 'url']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Social Link', {
            'fields': ['user', 'platform', 'url', 'handle']
        }),
        ('Verification', {
            'fields': ['is_verified']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(GameProfile)
class GameProfileAdmin(admin.ModelAdmin):
    """Game profiles admin"""
    
    list_display = [
        'user',
        'game',
        'in_game_name',
        'rank_name',
        'matches_played',
        'win_rate',
        'is_verified',
    ]
    
    list_filter = ['game', 'is_verified', 'created_at']
    search_fields = ['user__username', 'in_game_name', 'rank_name']
    readonly_fields = ['game_display_name', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Game Profile', {
            'fields': ['user', 'game', 'game_display_name', 'in_game_name']
        }),
        ('Rank', {
            'fields': ['rank_name', 'rank_image', 'rank_points', 'rank_tier', 'peak_rank']
        }),
        ('Statistics', {
            'fields': ['matches_played', 'win_rate', 'kd_ratio', 'hours_played']
        }),
        ('Role & Verification', {
            'fields': ['main_role', 'is_verified']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


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


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Match history admin"""
    
    list_display = [
        'user',
        'game_name',
        'result',
        'score',
        'kda',
        'played_at',
    ]
    
    list_filter = ['result', 'game_name', 'mode', 'played_at']
    search_fields = ['user__username', 'game_name']
    date_hierarchy = 'played_at'
    
    fieldsets = [
        ('Match Info', {
            'fields': ['user', 'game_name', 'mode', 'result', 'played_at']
        }),
        ('Stats', {
            'fields': ['score', 'kda', 'duration']
        }),
        ('Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse']
        }),
    ]


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
