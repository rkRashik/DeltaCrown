# apps/user_profile/admin/game_passports.py
"""
Game Passport Admin Configuration

Admins for:
- GameProfile (Game Passport core model) - GP-1 with dynamic schema-driven form
- GameProfileAlias (Alias history)
- GameProfileConfig (Singleton configuration)
"""
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from django.utils.html import format_html
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator

from ..models import GameProfile, GameProfileAlias, GameProfileConfig
from ..services.audit import AuditService
from .forms import GameProfileAdminForm


# ============================================================================
# INLINE ADMINS
# ============================================================================

class GameProfileAliasInline(TabularInline):
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
class GameProfileAdmin(ModelAdmin):
    """
    GP-2D Game Passport Admin with Schema-Driven Dynamic Form
    
    Features:
    - Dynamic identity validation per game using GameChoiceConfig
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
        'verification_status_badge',
        'riot_puuid_short',
        'attempt_info',
        'visibility',
        'is_lft',
        'is_pinned',
        'lock_status_display',
        'updated_at',
    ]
    
    list_filter = [
        'verification_status',  # Phase 9A-30: Filter by verification status first
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
        'verification_status_badge',  # Phase 9A-30: Visual badge
        'verified_at',
        'verified_by',
        'locked_until_display',
        'lock_countdown_display',
        'edit_history_display',  # Phase 9A-30: Show edit history
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
            'description': 'Player identity information. Field labels and available options adapt based on selected game. Run: python manage.py seed_games'
        }),
        ('Visibility & Status', {
            'fields': [
                'visibility',
                'status',
                'is_lft',
                'verification_status',  # Phase 9A-30: Verification status
                'verified_at',
                'verified_by',
                'verification_notes',  # Phase 9A-30: Verification notes (not flagged_reason)
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
        ('Rank Information', {
            'fields': [
                'rank_name',
                'peak_rank',
                'rank_points',
                'rank_tier',
                'rank_image',
            ],
            'description': 'Current rank, peak rank, and ranking points. These fields are filled by users when linking their game passport.'
        }),
        ('Statistics & Role', {
            'fields': [
                'main_role',
                'matches_played',
                'win_rate',
                'kd_ratio',
                'hours_played',
            ],
            'description': 'Gameplay statistics and main role/position. Users provide this data during passport creation.'
        }),
        ('Additional Metadata', {
            'fields': [
                'metadata',
            ],
            'classes': ['collapse'],
            'description': 'JSON field for game-specific extra data beyond core identity and stats.'
        }),
        ('Timestamps & History', {
            'fields': ['created_at', 'updated_at', 'edit_history_display'],
            'description': 'Creation time, last edit time, and edit history from alias records.'
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
        from apps.user_profile.models import GameChoiceConfig
        from django.core.cache import cache
        import json
        
        extra_context = extra_context or {}
        
        # Try to get from cache first (GP-2E performance optimization)
        CACHE_KEY = 'gp_schema_matrix_v1'
        CACHE_TTL = 3600  # 1 hour
        
        schema_matrix_json = cache.get(CACHE_KEY)
        
        if not schema_matrix_json:
            # Cache miss - build from database
            schemas = GameChoiceConfig.objects.select_related('game').filter(
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
    
    def edit_history_display(self, obj):
        """Display edit history from alias records"""
        aliases = obj.aliases.all().order_by('-changed_at')[:5]  # Last 5 edits
        
        if not aliases.exists():
            return mark_safe('<span style="color: gray;">No edit history</span>')
        
        html = '<ul style="margin: 0; padding-left: 20px;">'
        for alias in aliases:
            html += f'<li><strong>{alias.changed_at.strftime("%Y-%m-%d %H:%M")}</strong>: '
            html += f'Changed from "{alias.old_in_game_name}" '
            if alias.reason:
                html += f'<br><em style="color: #666;">Reason: {alias.reason}</em>'
            html += '</li>'
        html += '</ul>'
        
        if obj.aliases.count() > 5:
            html += f'<p style="color: #666; margin-top: 5px;"><em>...and {obj.aliases.count() - 5} more edits</em></p>'
        
        return mark_safe(html)
    edit_history_display.short_description = 'Edit History (Last 5)'
    
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
    
    actions = [
        'verify_passports',
        'flag_passports',
        'reset_verification',
        'riot_verify_selected',
        'riot_retry_all_pending',
        'unlock_identity_changes',
        'pin_passports',
        'unpin_passports',
    ]
    
    # Phase 9A-30: Verification display method
    def verification_status_badge(self, obj):
        """Display verification status with colored badge"""
        status_colors = {
            'VERIFIED': '#28a745',  # Green
            'PENDING': '#ffc107',    # Yellow
            'FLAGGED': '#dc3545',    # Red
        }
        color = status_colors.get(obj.verification_status, '#6c757d')  # Default gray
        return format_html(
            '<span style="display: inline-block; padding: 4px 8px; '
            'background-color: {}; color: white; border-radius: 4px; '
            'font-size: 12px; font-weight: bold;">{}</span>',
            color,
            obj.verification_status
        )
    verification_status_badge.short_description = 'Verification'

    def riot_puuid_short(self, obj):
        """Show first 8 chars of Riot PUUID if verified."""
        provider = obj.provider_data if isinstance(obj.provider_data, dict) else {}
        riot = provider.get("riot") if isinstance(provider.get("riot"), dict) else {}
        puuid = str(riot.get("puuid") or "").strip()
        if puuid:
            return format_html('<span title="{}">{}&hellip;</span>', puuid, puuid[:8])
        return "—"
    riot_puuid_short.short_description = "PUUID"

    def attempt_info(self, obj):
        """Show attempt count and last attempt timestamp."""
        count = obj.verification_attempt_count or 0
        last = obj.last_verification_attempt_at
        if last:
            import datetime
            ago = (datetime.datetime.now(datetime.timezone.utc) - last).total_seconds()
            if ago < 3600:
                ago_str = f"{int(ago // 60)}m ago"
            elif ago < 86400:
                ago_str = f"{int(ago // 3600)}h ago"
            else:
                ago_str = last.strftime("%m-%d")
            return f"{count}× ({ago_str})"
        return f"{count}×" if count else "—"
    attempt_info.short_description = "Attempts"
    
    # Phase 9A-30: Verification actions
    def verify_passports(self, request, queryset):
        """Mark selected passports as verified"""
        from django.utils import timezone
        count = 0
        for passport in queryset:
            passport.verification_status = 'VERIFIED'
            passport.verified_at = timezone.now()
            passport.verified_by = request.user
            passport.verification_notes = ""  # Clear any flag/notes
            passport.save()
            count += 1
            
            # Audit the verification
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.verified',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': passport.game.slug if passport.game else 'unknown',
                    'verified_by_admin': request.user.username,
                }
            )
        self.message_user(request, f"Verified {count} passport(s).", level=messages.SUCCESS)
    verify_passports.short_description = "✅ Verify selected passports"
    
    def flag_passports(self, request, queryset):
        """Flag selected passports for review"""
        count = 0
        for passport in queryset:
            passport.verification_status = 'FLAGGED'
            passport.verification_notes = f"Flagged by admin {request.user.username}"  # Use verification_notes not flagged_reason
            passport.save()
            count += 1
            
            # Audit the flag
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.flagged',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': passport.game.slug if passport.game else 'unknown',
                    'flagged_by_admin': request.user.username,
                }
            )
        self.message_user(request, f"Flagged {count} passport(s) for review.", level=messages.WARNING)
    flag_passports.short_description = "⚠️ Flag selected passports"
    
    def reset_verification(self, request, queryset):
        """Reset verification status to PENDING"""
        count = 0
        for passport in queryset:
            passport.verification_status = 'PENDING'
            passport.verified_at = None
            passport.verified_by = None
            passport.verification_notes = ""  # Clear verification notes
            passport.save()
            count += 1
            
            # Audit the reset
            AuditService.record_event(
                subject_user_id=passport.user.id,
                actor_user_id=request.user.id,
                event_type='game_passport.verification_reset',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=passport.id,
                metadata={
                    'game': passport.game.slug if passport.game else 'unknown',
                    'reset_by_admin': request.user.username,
                }
            )
        self.message_user(request, f"Reset verification for {count} passport(s) to PENDING.", level=messages.INFO)
    reset_verification.short_description = "↻ Reset verification to PENDING"

    def riot_verify_selected(self, request, queryset):
        """
        Enqueue Riot API verification for selected Valorant passports.
        Skips already-verified passports. Useful after rotating RIOT_API_KEY.
        """
        from apps.games.tasks.riot_verification_tasks import verify_game_passport_task
        from apps.games.services.riot_verification_service import is_valorant_passport

        enqueued = 0
        skipped_verified = 0
        skipped_non_val = 0

        for passport in queryset.select_related("game"):
            game_slug = getattr(passport.game, "slug", "") if passport.game else ""
            if not is_valorant_passport(game_slug):
                skipped_non_val += 1
                continue
            if passport.verification_status == "VERIFIED":
                skipped_verified += 1
                continue
            try:
                verify_game_passport_task.delay(passport.id)
                enqueued += 1
            except Exception:
                # Celery not available — run inline
                from apps.games.services.riot_verification_service import _verify_inline
                _verify_inline(passport.id)
                enqueued += 1

        msg = f"Queued {enqueued} Valorant passport(s) for Riot verification."
        if skipped_verified:
            msg += f" {skipped_verified} already verified (skipped)."
        if skipped_non_val:
            msg += f" {skipped_non_val} non-Valorant (skipped)."
        self.message_user(request, msg, messages.INFO)
    riot_verify_selected.short_description = "🎮 Riot: Verify selected Valorant passports via API"

    def riot_retry_all_pending(self, request, queryset):
        """
        Enqueue retry for ALL pending/failed/unavailable Valorant passports globally.
        Ignores the queryset selection — runs across the full table.
        Use after rotating RIOT_API_KEY on Render.
        """
        try:
            from apps.games.tasks.riot_verification_tasks import retry_pending_riot_passports_task
            retry_pending_riot_passports_task.delay()
            self.message_user(
                request,
                "Bulk Riot re-verification task enqueued. All pending/failed Valorant passports will be retried.",
                messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(
                request,
                f"Could not enqueue bulk task ({exc}). If Celery is unavailable, use 'Retry selected' instead.",
                messages.WARNING,
            )
    riot_retry_all_pending.short_description = "🔄 Riot: Retry ALL pending Valorant verifications (use after API key rotation)"

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

    # ── Per-object Riot verification (P7-B) ─────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/verify-riot/",
                self.admin_site.admin_view(self.verify_riot_view),
                name="user_profile_gameprofile_verify_riot",
            ),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Inject Riot verification context + diagnostics into the change page."""
        extra_context = extra_context or {}
        try:
            from apps.games.services.riot_verification_service import (
                is_valorant_passport,
                _api_key,
                _region_base,
                _key_diagnostic,
            )
            obj = self.get_object(request, object_id)
            if obj is not None:
                game_slug = getattr(obj.game, "slug", "") if obj.game else ""
                extra_context["is_valorant_passport"] = is_valorant_passport(game_slug)
                extra_context["riot_verify_url"] = reverse(
                    "admin:user_profile_gameprofile_verify_riot",
                    args=[object_id],
                )
                extra_context["passport_verification_status"] = obj.verification_status
                extra_context["passport_verification_error"] = obj.verification_error or ""
                extra_context["passport_attempt_count"] = obj.verification_attempt_count or 0
                extra_context["passport_last_attempt"] = obj.last_verification_attempt_at

                # Diagnostic context — shown in admin only, never to users.
                key_present = bool(_api_key())
                provider = obj.provider_data if isinstance(obj.provider_data, dict) else {}
                riot_data = provider.get("riot") if isinstance(provider.get("riot"), dict) else {}
                extra_context["riot_diag"] = {
                    "key_configured": key_present,
                    "key_diag": _key_diagnostic(),
                    "region": _region_base(),
                    "last_http_status": riot_data.get("last_http_status"),
                    "last_code": riot_data.get("last_code"),
                    "last_admin_msg": riot_data.get("last_admin_msg", ""),
                    "last_error_body": riot_data.get("last_error_body", ""),
                    "puuid_prefix": (riot_data.get("puuid") or "")[:12] or "—",
                    # What Riot ID we would verify from current fields
                    "current_riot_id": (
                        f"{obj.ign}#{obj.discriminator}"
                        if obj.ign and obj.discriminator
                        else obj.in_game_name or "—"
                    ),
                }
        except Exception:
            pass
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    def verify_riot_view(self, request, object_id):
        """
        Per-object Riot verification — synchronous, POST only.
        URL: /admin/user_profile/gameprofile/<id>/verify-riot/
        Shows granular admin feedback messages per error code.
        """
        from apps.games.services.riot_verification_service import (
            apply_verification_result,
            is_valorant_passport,
            resolve_riot_id_parts,
            verify_riot_id,
            CODE_MISSING_KEY,
            CODE_INVALID_KEY_401,
            CODE_FORBIDDEN_403,
            CODE_NOT_FOUND_404,
            CODE_RATE_LIMITED_429,
            CODE_SERVER_5XX,
            CODE_TIMEOUT,
            CODE_URL_ERROR,
            CODE_BAD_FORMAT,
        )

        change_url = reverse("admin:user_profile_gameprofile_change", args=[object_id])

        if request.method != "POST":
            # Dead GET — just redirect, do not run verification.
            return HttpResponseRedirect(change_url)

        try:
            obj = GameProfile.objects.select_related("game").get(pk=object_id)
        except GameProfile.DoesNotExist:
            self.message_user(request, "Passport not found.", level=messages.ERROR)
            return HttpResponseRedirect(change_url)

        if not request.user.is_staff:
            self.message_user(request, "Permission denied.", level=messages.ERROR)
            return HttpResponseRedirect(change_url)

        game_slug = getattr(obj.game, "slug", "") if obj.game else ""
        if not is_valorant_passport(game_slug):
            self.message_user(
                request,
                f"Riot verification only applies to Valorant passports (this is '{game_slug or 'unknown'}').",
                level=messages.WARNING,
            )
            return HttpResponseRedirect(change_url)

        game_name, tag_line = resolve_riot_id_parts(obj)
        if not game_name or not tag_line:
            self.message_user(
                request,
                f"Cannot resolve Riot ID from this passport. "
                f"IGN='{obj.ign or '—'}', Discriminator='{obj.discriminator or '—'}', "
                f"in_game_name='{obj.in_game_name or '—'}'. "
                f"At least one of ign+discriminator or in_game_name='gameName#tagLine' must be set.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(change_url)

        result = verify_riot_id(game_name, tag_line)
        apply_verification_result(obj, result)

        code       = result.get("code", "")
        status     = result["status"]
        admin_msg  = result.get("admin_msg", "")
        riot_id    = f"{game_name}#{tag_line}"
        http_code  = result.get("http_status")
        http_label = f" (HTTP {http_code})" if http_code else ""

        if status == "VERIFIED":
            puuid = (result.get("puuid") or "")[:16]
            self.message_user(
                request,
                f"✅ '{riot_id}' verified. PUUID prefix: {puuid}{'…' if puuid else '(empty)'}",
                level=messages.SUCCESS,
            )

        elif code == CODE_NOT_FOUND_404:
            self.message_user(
                request,
                f"❌ Riot ID '{riot_id}' was not found on Riot servers{http_label}. "
                f"Passport marked FAILED — user can edit their Riot ID and resubmit.",
                level=messages.ERROR,
            )

        elif code == CODE_MISSING_KEY:
            self.message_user(
                request,
                "🔑 RIOT_API_KEY is not loaded in the running server process. "
                "Add or update RIOT_API_KEY in Render environment variables, then redeploy/restart the server before retrying.",
                level=messages.ERROR,
            )

        elif code == CODE_INVALID_KEY_401:
            self.message_user(
                request,
                "🔑 Riot API rejected the key with 401 Unauthorized. "
                "The RIOT_API_KEY is invalid or has expired. Update it in Render env vars and redeploy.",
                level=messages.ERROR,
            )

        elif code == CODE_FORBIDDEN_403:
            self.message_user(
                request,
                "🔑 Riot API returned 403 Forbidden. "
                "The key is loaded and reachable — Riot rejected access to the Account-V1 endpoint. "
                "Go to developer.riotgames.com → your application → enable the 'Account' product (Account-V1). "
                "For personal/dev keys this should already be available. "
                "For production keys, Account-V1 approval must be requested. "
                "Check the diagnostic panel below for the Riot response body.",
                level=messages.ERROR,
            )

        elif code == CODE_RATE_LIMITED_429:
            self.message_user(
                request,
                f"⏳ Riot API rate limit hit{http_label}. Wait a moment and retry.",
                level=messages.WARNING,
            )

        elif code == CODE_SERVER_5XX:
            self.message_user(
                request,
                f"⚠️ Riot servers returned an error{http_label}. This is a Riot-side outage — retry later.",
                level=messages.WARNING,
            )

        elif code == CODE_TIMEOUT:
            self.message_user(
                request,
                "⚠️ Riot API request timed out. Retry later or increase RIOT_API_TIMEOUT_SECONDS.",
                level=messages.WARNING,
            )

        elif code == CODE_URL_ERROR:
            self.message_user(
                request,
                f"⚠️ Network or URL error reaching Riot API. {admin_msg}",
                level=messages.WARNING,
            )

        else:
            # Fallback for any other API_UNAVAILABLE sub-code
            self.message_user(
                request,
                f"⚠️ Verification could not run{http_label}. {admin_msg or 'Check server logs for details.'}",
                level=messages.WARNING,
            )

        return HttpResponseRedirect(change_url)


# ============================================================================
# GAME PASSPORT ALIAS ADMIN
# ============================================================================

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


# ============================================================================
# GAME PASSPORT CONFIG ADMIN
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
        js = ('admin/admin_game_passport.js',)  # GP-2B: Dynamic field behavior
