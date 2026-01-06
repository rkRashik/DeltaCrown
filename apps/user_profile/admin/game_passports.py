# apps/user_profile/admin/game_passports.py
"""
Game Passport Admin Configuration

Admins for:
- GameProfile (Game Passport core model) - GP-1 with dynamic schema-driven form
- GameProfileAlias (Alias history)
- GameProfileConfig (Singleton configuration)
"""
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..models import GameProfile, GameProfileAlias, GameProfileConfig
from ..services.audit import AuditService
from .forms import GameProfileAdminForm


# ============================================================================
# INLINE ADMINS
# ============================================================================

class GameProfileAliasInline(admin.TabularInline):
    """
    Inline display of alias history for a game passport.
    Read-only view of all identity changes.
    Phase 9A-10: Clean labels, defensive queryset loading.
    """
    model = GameProfileAlias
    extra = 0
    can_delete = False
    readonly_fields = [
        'old_in_game_name',
        'safe_old_ign',
        'safe_old_discriminator',
        'old_platform',
        'old_region',
        'changed_at',
        'changed_by_user_id',
        'reason'
    ]
    fields = [
        'old_in_game_name',
        'safe_old_ign',
        'safe_old_discriminator',
        'changed_at',
        'reason'
    ]
    
    def safe_old_ign(self, obj):
        """Display old_ign field"""
        return obj.old_ign or '—'
    safe_old_ign.short_description = 'Old IGN'
    
    def safe_old_discriminator(self, obj):
        """Display old_discriminator field"""
        return obj.old_discriminator or '—'
    safe_old_discriminator.short_description = 'Old Discriminator'
    
    def get_queryset(self, request):
        """
        Override queryset to avoid column issues.
        Phase 9A-9: Remove .only() to avoid ProgrammingError if columns missing.
        Migration 0051 should have added all columns, but safer to load all fields.
        """
        qs = super().get_queryset(request)
        # Don't use .only() - let Django load all fields to avoid column errors
        return qs
    
    def has_add_permission(self, request, obj=None):
        """Aliases created by GamePassportService only"""
        return False


# ============================================================================
# GAME PASSPORT ADMIN
# ============================================================================

@admin.register(GameProfile)
class GameProfileAdmin(admin.ModelAdmin):
    """
    GP-2D Game Passport Admin with Schema-Driven Dynamic Form
    
    Features:
    - Dynamic identity validation per game using GamePassportSchema
    - Game dropdown limited to passport-supported games
    - Dynamic JS for labels, hide/show, region dropdown (GP-2D)
    - Server-side validation with normalization
    - Identity change tracking with alias history
    - Cooldown enforcement
    - Pinning management
    - Privacy controls
    - Audit integration
    - Schema matrix injected via template (no hardcoded game logic)
    """
    
    form = GameProfileAdminForm  # GP-2D: Schema-driven form with region dropdown
    change_form_template = 'admin/user_profile/gameprofile/change_form.html'  # GP-2D: Custom template for schema injection
    
    class Media:
        js = ('js/admin_game_passport.js',)  # GP-2D: Dynamic form behavior
    
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
        ('locked_until', admin.EmptyFieldListFilter),  # Locked/unlocked filter
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__userprofile__public_id',  # Search by public_id
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
        ('Game & User', {
            'fields': [
                'user',
                'game',
                'game_display_name',
            ],
            'description': 'User and game association'
        }),
        ('Identity Fields', {
            'fields': [
                'ign',
                'discriminator',
                'platform',
                'region',
                'in_game_name',
                'identity_key',
            ],
            'description': 'Player identity information. Field labels and available options adapt based on selected game. Run seed_identity_configs_2026 command if dropdown options are missing.'
        }),
        ('Visibility & Status', {
            'fields': [
                'visibility',
                'status',
                'is_lft',
            ]
        }),
        ('Display Preferences', {
            'fields': [
                'is_pinned',
                'pinned_order',
            ]
        }),
        ('Fair Play Protocol (Identity Lock)', {
            'fields': [
                'locked_until',
                'locked_until_display',
                'lock_countdown_display',
            ],
            'description': '30-day identity lock prevents frequent changes to combat smurfing and identity abuse.'
        }),
        ('Competitive Fields', {
            'fields': [
                'rank_name',
                'rank_image',
                'metadata',
            ],
            'classes': ['collapse'],
            'description': 'Optional competitive information (rank, role, stats). metadata JSON stores game-specific fields beyond core identity.'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [GameProfileAliasInline]
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """
        GP-2D: Inject schema matrix JSON for dynamic admin form.
        GP-2E: Added caching for performance (TTL: 1 hour).
        
        Provides all game schemas with identity field configs, region choices,
        and rank choices. JavaScript uses this to adapt the form dynamically.
        """
        from apps.user_profile.models import GamePassportSchema
        from django.core.cache import cache
        import json
        
        extra_context = extra_context or {}
        
        # Try to get from cache first (GP-2E performance optimization)
        CACHE_KEY = 'gp_schema_matrix_v1'
        CACHE_TTL = 3600  # 1 hour
        
        schema_matrix_json = cache.get(CACHE_KEY)
        
        if not schema_matrix_json:
            # Cache miss - build from database
            schemas = GamePassportSchema.objects.select_related('game').filter(
                game__is_passport_supported=True
            ).order_by('game__slug')
            
            # Build schema matrix
            schema_matrix = {}
            for schema in schemas:
                game_slug = schema.game.slug
                schema_matrix[game_slug] = {
                    'game_slug': game_slug,
                    'game_name': schema.game.display_name,
                    # Region configuration
                    'region_choices': schema.region_choices,
                    'region_required': schema.region_required,
                    # Rank configuration (for future use)
                    'rank_choices': schema.rank_choices,
                    'rank_system': schema.rank_system,
                    # Identity field configuration (for label mapping)
                    'identity_fields': schema.identity_fields,
                    'identity_format': schema.identity_format,
                    # Platform-specific flag
                    'platform_specific': schema.platform_specific,
                }
            
            schema_matrix_json = json.dumps(schema_matrix)
            cache.set(CACHE_KEY, schema_matrix_json, CACHE_TTL)
        
        extra_context['schema_matrix'] = schema_matrix_json
        
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    def game_display_name(self, obj):
        """Friendly game name from Game model"""
        if obj.game:
            return obj.game.display_name
        return '(No game)'
    game_display_name.short_description = 'Game Title'
    
    def locked_until_display(self, obj):
        """Display lock expiration or 'Unlocked'"""
        if obj.locked_until:
            return format_html(
                '<span style="color: red;">🔒 Locked until {}</span>',
                obj.locked_until.strftime('%Y-%m-%d %H:%M UTC')
            )
        return mark_safe('<span style="color: green;">✓ Unlocked</span>')
    locked_until_display.short_description = 'Lock Status'
    
    def lock_countdown_display(self, obj):
        """Display remaining lock time"""
        if not obj.locked_until:
            return mark_safe('<span style="color: gray;">Not locked</span>')
        
        from django.utils import timezone
        remaining = obj.locked_until - timezone.now()
        
        if remaining.total_seconds() <= 0:
            return mark_safe('<span style="color: green;">Lock expired</span>')
        
        days = remaining.days
        hours = remaining.seconds // 3600
        
        if days > 0:
            return format_html(
                '<span style="color: orange;">{} days, {} hours remaining</span>',
                days, hours
            )
        else:
            return format_html(
                '<span style="color: orange;">{} hours remaining</span>',
                hours
            )
    lock_countdown_display.short_description = 'Lock Countdown'
    
    def lock_status_display(self, obj):
        """Display lock status for list view"""
        if not obj.locked_until:
            return '✓'
        
        from django.utils import timezone
        if obj.locked_until > timezone.now():
            remaining = obj.locked_until - timezone.now()
            days = remaining.days
            return f'🔒 ({days}d)' if days > 0 else f'🔒 (<1d)'
        return '✓'
    lock_status_display.short_description = 'Lock'
    
    def save_model(self, request, obj, form, change):
        """Record identity changes in alias history"""
        if change and 'in_game_name' in form.changed_data:
            # Get old value before save
            try:
                old_obj = GameProfile.objects.get(pk=obj.pk)
                old_name = old_obj.in_game_name
                
                # Save first
                super().save_model(request, obj, form, change)
                
                # Create alias record
                GameProfileAlias.objects.create(
                    game_profile=obj,
                    old_in_game_name=old_name,
                    changed_by_user_id=request.user.id,
                    reason=f"Changed by admin: {request.user.username}"
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
                    'game': obj.game.slug if obj.game else 'unknown',
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
                    'game': passport.game.slug if passport.game else 'unknown',
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


# ============================================================================
# GAME PASSPORT ALIAS ADMIN
# ============================================================================

@admin.register(GameProfileAlias)
class GameProfileAliasAdmin(admin.ModelAdmin):
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


# ============================================================================
# GAME PASSPORT CONFIG ADMIN
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
        js = ('admin/admin_game_passport.js',)  # GP-2B: Dynamic field behavior
