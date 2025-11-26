# apps/user_profile/admin/users.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..models import UserProfile, PrivacySettings, VerificationRecord, Badge, UserBadge
from .exports import export_userprofiles_csv


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "kyc_status_badge", "coin_balance", "created_at")
    search_fields = ("user__username", "display_name", "user__email", "phone", "real_full_name")
    list_filter = ("kyc_status", "region", "gender", "created_at")
    date_hierarchy = "created_at"
    actions = [export_userprofiles_csv]

    # UX + perf
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    
    readonly_fields = ("uuid", "slug", "created_at", "updated_at", "kyc_verified_at")
    
    fieldsets = (
        ('User Account', {
            'fields': ('user', 'uuid', 'slug')
        }),
        ('Public Identity', {
            'fields': ('avatar', 'banner', 'display_name', 'bio', 'region')
        }),
        ('Legal Identity & KYC', {
            'fields': ('real_full_name', 'date_of_birth', 'nationality', 'kyc_status', 'kyc_verified_at'),
            'description': 'KYC-verified data is locked and cannot be changed by users.'
        }),
        ('Contact Information', {
            'fields': ('phone', 'country', 'city', 'postal_code', 'address')
        }),
        ('Demographics', {
            'fields': ('gender',)
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')
        }),
        ('Social Media', {
            'fields': ('facebook', 'instagram', 'tiktok', 'twitter', 'youtube_link', 'twitch_link', 'discord_id')
        }),
        ('Gaming', {
            'fields': ('stream_status',),
            'description': 'Game profiles are stored in game_profiles JSON field.'
        }),
        ('Gamification', {
            'fields': ('level', 'xp', 'pinned_badges')
        }),
        ('Economy', {
            'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items')
        }),
        ('Legacy Game IDs', {
            'fields': ('riot_id', 'riot_tagline', 'steam_id', 'efootball_id', 'mlbb_id', 
                      'mlbb_server_id', 'pubg_mobile_id', 'free_fire_id', 'ea_id', 'codm_uid'),
            'classes': ('collapse',),
            'description': 'Legacy fields - migrating to game_profiles JSON.'
        }),
        ('Legacy Privacy Flags', {
            'fields': ('is_private', 'show_email', 'show_phone', 'show_socials'),
            'classes': ('collapse',),
            'description': 'Legacy flags - use PrivacySettings model for granular control.'
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


@admin.register(VerificationRecord)
class VerificationRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile_link', 'status_badge', 'submitted_at', 'reviewed_at', 'reviewed_by')
    search_fields = ('user_profile__user__username', 'user_profile__display_name', 
                    'verified_name', 'id_number')
    list_filter = ('status', 'submitted_at', 'reviewed_at')
    date_hierarchy = 'submitted_at'
    
    list_select_related = ('user_profile', 'user_profile__user', 'reviewed_by')
    autocomplete_fields = ('user_profile', 'reviewed_by')
    
    readonly_fields = ('submitted_at', 'reviewed_at', 'document_preview')
    
    fieldsets = (
        ('User Profile', {
            'fields': ('user_profile',)
        }),
        ('Uploaded Documents', {
            'fields': ('id_document_front', 'id_document_back', 'selfie_with_id', 'document_preview'),
            'description': 'User-uploaded KYC documents for verification.'
        }),
        ('Verification Status', {
            'fields': ('status', 'submitted_at'),
            'description': 'Current verification status.'
        }),
        ('Verified Data', {
            'fields': ('verified_name', 'verified_dob', 'verified_nationality', 'id_number'),
            'description': 'Data extracted from ID documents (filled by admin during approval).'
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'rejection_reason'),
            'description': 'Admin review details.'
        }),
    )
    
    actions = ['approve_kyc', 'reject_kyc']
    
    def user_profile_link(self, obj):
        """Link to user profile admin page"""
        url = reverse('admin:user_profile_userprofile_change', args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', url, obj.user_profile)
    user_profile_link.short_description = 'User Profile'
    
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'unverified': 'gray',
            'pending': 'orange',
            'verified': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.status, 'gray')
        
        if obj.status == 'verified':
            icon = '✓'
        elif obj.status == 'pending':
            icon = '⏳'
        elif obj.status == 'rejected':
            icon = '✗'
        else:
            icon = '○'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def document_preview(self, obj):
        """Show preview of uploaded documents"""
        html = []
        
        if obj.id_document_front:
            html.append(f'<div><strong>ID Front:</strong><br><img src="{obj.id_document_front.url}" style="max-width: 300px; max-height: 200px;"></div>')
        
        if obj.id_document_back:
            html.append(f'<div style="margin-top: 10px;"><strong>ID Back:</strong><br><img src="{obj.id_document_back.url}" style="max-width: 300px; max-height: 200px;"></div>')
        
        if obj.selfie_with_id:
            html.append(f'<div style="margin-top: 10px;"><strong>Selfie with ID:</strong><br><img src="{obj.selfie_with_id.url}" style="max-width: 300px; max-height: 200px;"></div>')
        
        return mark_safe('<br>'.join(html)) if html else 'No documents uploaded'
    document_preview.short_description = 'Document Preview'
    
    def approve_kyc(self, request, queryset):
        """Admin action to approve KYC submissions"""
        approved_count = 0
        
        for record in queryset.filter(status='pending'):
            if not all([record.id_document_front, record.id_document_back, record.selfie_with_id]):
                self.message_user(
                    request,
                    f'Cannot approve {record.user_profile} - missing documents',
                    level='error'
                )
                continue
            
            # Note: In production, admin should fill verified_name, verified_dob, etc.
            # For now, we'll use profile data as fallback
            verified_name = record.verified_name or record.user_profile.real_full_name or 'Unknown'
            verified_dob = record.verified_dob or record.user_profile.date_of_birth
            verified_nationality = record.verified_nationality or record.user_profile.nationality or 'BD'
            id_number = record.id_number or 'N/A'
            
            try:
                record.approve(
                    reviewed_by=request.user,
                    verified_name=verified_name,
                    verified_dob=verified_dob,
                    verified_nationality=verified_nationality,
                    id_number=id_number
                )
                approved_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Error approving {record.user_profile}: {str(e)}',
                    level='error'
                )
        
        if approved_count:
            self.message_user(
                request,
                f'Successfully approved {approved_count} KYC submission(s)',
                level='success'
            )
    approve_kyc.short_description = 'Approve selected KYC submissions'
    
    def reject_kyc(self, request, queryset):
        """Admin action to reject KYC submissions"""
        rejected_count = 0
        
        for record in queryset.filter(status='pending'):
            try:
                # Default rejection reason
                reason = 'Documents unclear or invalid. Please resubmit with clearer photos.'
                record.reject(reviewed_by=request.user, reason=reason)
                rejected_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Error rejecting {record.user_profile}: {str(e)}',
                    level='error'
                )
        
        if rejected_count:
            self.message_user(
                request,
                f'Successfully rejected {rejected_count} KYC submission(s)',
                level='warning'
            )
    reject_kyc.short_description = 'Reject selected KYC submissions'


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


