"""
Admin configuration for games app.
"""

import logging

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from apps.common.admin_mixins import SafeUploadMixin
from apps.common.media_urls import storage_file_exists
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole,
)
from apps.games.models.map_pool import GameMapPool
from apps.games.models.pipeline_template import GamePipelineTemplate
from apps.games.models.rules import VetoConfiguration
from apps.games.models.cleanup_candidate import MediaCleanupCandidate
from apps.games.models.maintenance_log import MaintenanceRunLog

logger = logging.getLogger(__name__)

_IMAGE_FIELDS = ("icon", "logo", "banner", "card_image")


class GameRosterConfigInline(StackedInline):
    model = GameRosterConfig
    extra = 0
    can_delete = False


class GameTournamentConfigInline(StackedInline):
    model = GameTournamentConfig
    extra = 0
    can_delete = False


class GamePlayerIdentityConfigInline(TabularInline):
    model = GamePlayerIdentityConfig
    extra = 1
    fields = ['field_name', 'display_name', 'is_required', 'validation_regex', 'order']


class GameRoleInline(TabularInline):
    model = GameRole
    extra = 1
    fields = ['role_name', 'role_code', 'icon', 'color', 'is_competitive', 'order']


class GameMapPoolInline(TabularInline):
    model = GameMapPool
    extra = 1
    fields = ['image_status_cell', 'image', 'map_name', 'map_code', 'is_active', 'is_competitive', 'order']
    readonly_fields = ['image_status_cell']
    classes = []

    def image_status_cell(self, obj):
        if not obj or not obj.pk:
            return mark_safe("<span style='color:#9ca3af;font-size:11px'>—</span>")
        name = getattr(obj.image, "name", "") or ""
        if not name:
            is_veto_game = obj.game.category in ("FPS",) if hasattr(obj, "game") else False
            if obj.is_active and obj.is_competitive and is_veto_game:
                return mark_safe(
                    "<span style='color:#f59e0b;font-size:11px' title='Active competitive map with no image — veto cards will show a placeholder.'>&#9888; no image</span>"
                )
            return mark_safe("<span style='color:#9ca3af;font-size:11px'>empty</span>")
        try:
            url = obj.image.url or ""
        except Exception:
            url = ""
        if url and url.startswith(("http", "/")):
            preview = format_html(
                "<img src='{}' style='height:32px;width:auto;border-radius:4px;object-fit:cover;vertical-align:middle' loading='lazy'>",
                url,
            )
        else:
            preview = mark_safe("")
        if storage_file_exists(obj.image):
            badge = mark_safe("<span style='color:#22c55e;font-size:10px'>&#10003;</span>")
        else:
            badge = mark_safe("<span style='color:#ef4444;font-size:10px'>&#10007; missing</span>")
        return format_html("{} {}", preview, badge)

    image_status_cell.short_description = "Preview / Status"


@admin.register(Game)
class GameAdmin(SafeUploadMixin, ModelAdmin):
    list_display = ['name', 'slug', 'category', 'game_type', 'is_active', 'is_featured']
    list_filter = ['category', 'game_type', 'is_active', 'is_featured']
    search_fields = ['name', 'slug', 'short_code']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'media_storage_diagnostic']
    actions = ['action_audit_media']

    class Media:
        css = {'all': ('admin/css/game_media_admin.css',)}

    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'display_name', 'slug', 'short_code', 'description']
        }),
        ('Classification', {
            'fields': ['category', 'game_type', 'platforms']
        }),
        ('Media & Branding', {
            'fields': [
                'media_storage_diagnostic',
                'icon', 'logo', 'banner', 'card_image',
                'primary_color', 'secondary_color', 'accent_color',
            ]
        }),
        ('Status', {
            'fields': ['is_active', 'is_featured', 'release_date']
        }),
        ('Metadata', {
            'fields': ['developer', 'publisher', 'official_website']
        }),
        ('Game ID Customisation', {
            'fields': ['game_id_label', 'game_id_placeholder'],
            'description': (
                'How the in-game identifier is labelled for this game '
                '(e.g. "Riot ID" for Valorant, "Steam ID" for CS2). '
                'Leave blank to use the default "Game ID".'
            ),
        }),
        ('System', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [
        GameRosterConfigInline,
        GameTournamentConfigInline,
        GamePlayerIdentityConfigInline,
        GameRoleInline,
        GameMapPoolInline,
    ]

    def media_storage_diagnostic(self, obj):
        """Readonly field: per-field image preview cards + storage status."""
        import os
        from django.conf import settings as dj_settings
        from django.core.files.storage import default_storage
        from django.templatetags.static import static

        try:
            backend_cls = type(default_storage).__name__
            is_cloudinary = "Cloudinary" in backend_cls
        except Exception:
            backend_cls = "unknown"
            is_cloudinary = False

        django_env = os.getenv("DJANGO_ENV", "development")
        is_production = (not dj_settings.DEBUG) or (django_env == "production")
        local_in_prod = (not is_cloudinary) and is_production

        # ── Backend badge ─────────────────────────────────────────────────
        if is_cloudinary:
            backend_html = mark_safe(
                "<span class='gma-backend-badge gma-backend-cloudinary'>"
                "<span class='material-symbols-outlined'>cloud</span>"
                "Active upload storage: Cloudinary</span>"
                "<div class='gma-banner gma-bok' style='margin-top:8px'>"
                "<span class='material-symbols-outlined'>cloud_done</span>"
                "<div>New uploads will be served from Cloudinary CDN on production. "
                "Replacing an image schedules the old file for cleanup after 48 h — go to "
                "<a href='/admin/maintenance/'>Operations Center</a> &rsaquo; Delete Eligible Media.</div>"
                "</div>"
            )
        elif local_in_prod:
            backend_html = mark_safe(
                "<span class='gma-backend-badge gma-backend-local'>"
                "<span class='material-symbols-outlined'>folder_open</span>"
                "Active upload storage: Local filesystem</span>"
                "<div class='gma-banner gma-bwarn' style='margin-top:8px'>"
                "<span class='material-symbols-outlined'>warning</span>"
                "<div><strong>Production using local storage.</strong> "
                "Files uploaded here will NOT appear on deltacrown.xyz. "
                "Set <code>CLOUDINARY_URL</code> in Render, then re-upload from the production admin.</div>"
                "</div>"
            )
        else:
            backend_html = mark_safe(
                "<span class='gma-backend-badge gma-backend-local'>"
                "<span class='material-symbols-outlined'>folder_open</span>"
                "Active upload storage: Local filesystem</span>"
                "<div class='gma-banner gma-bwarn' style='margin-top:8px'>"
                "<span class='material-symbols-outlined'>folder_open</span>"
                "<div>Local uploads exist only on this machine. "
                "For production images, upload from the live admin with Cloudinary configured.</div>"
                "</div>"
            )

        # ── Guide ────────────────────────────────────────────────────────
        guide_html = mark_safe(
            "<div class='gma-guide'>"
            "<strong>Safe image upload workflow:</strong>"
            "<ol><li>Upload fresh images using the fields below.</li>"
            "<li>Wait 48 h (old Cloudinary asset is retained during this window).</li>"
            "<li>Go to <a href='/admin/maintenance/'>Operations Center</a> &rsaquo; Delete Eligible Media.</li></ol>"
            "</div>"
        )

        # ── Per-field preview cards ───────────────────────────────────────
        cards = []
        for field_name in _IMAGE_FIELDS:
            field = getattr(obj, field_name, None)
            name = getattr(field, "name", "") or ""

            if not name:
                thumb_html = mark_safe(
                    "<div class='gma-thumb-placeholder'>"
                    "<span class='material-symbols-outlined'>image_not_supported</span>Empty</div>"
                )
                badges = mark_safe("<span class='gma-badge gb-empty'>Empty</span>")
                path_html = mark_safe("")
                url_html = mark_safe("")
            else:
                url = ""
                try:
                    url = field.url or ""
                except Exception:
                    url = ""

                # Thumbnail
                if url and url.startswith(("http", "/")):
                    thumb_html = format_html(
                        "<img src='{}' style='max-height:76px;max-width:100%;object-fit:contain;' "
                        "onerror=\"this.style.display='none';this.nextSibling.style.display='flex'\" loading='lazy'>"
                        "<div class='gma-thumb-placeholder' style='display:none'>"
                        "<span class='material-symbols-outlined'>broken_image</span>No preview</div>",
                        url,
                    )
                else:
                    thumb_html = mark_safe(
                        "<div class='gma-thumb-placeholder'>"
                        "<span class='material-symbols-outlined'>broken_image</span>No URL</div>"
                    )

                exists = storage_file_exists(field)
                if exists:
                    status_badge = mark_safe("<span class='gma-badge gb-ok'>&#10003; Available</span>")
                else:
                    status_badge = mark_safe("<span class='gma-badge gb-miss'>&#10007; Missing</span>")

                if "res.cloudinary.com" in url:
                    host_badge = mark_safe("<span class='gma-badge gb-cloud'>Cloudinary</span>")
                elif url.startswith("/media/") or (url.startswith("/") and "http" not in url):
                    warn_title = (
                        "Stale local ref — re-upload on production" if is_cloudinary else "Local /media/ file"
                    )
                    host_badge = format_html(
                        "<span class='gma-badge gb-local' title='{}'>{}</span>",
                        warn_title,
                        mark_safe("&#9888; Local"),
                    )
                else:
                    host_badge = mark_safe("<span class='gma-badge gb-empty'>?</span>")

                badges = format_html("{} {}", status_badge, host_badge)
                path_html = format_html(
                    "<div class='gma-path'>{}</div>", name[:70] + ("…" if len(name) > 70 else "")
                )
                url_display = url[:55] + ("…" if len(url) > 55 else "")
                url_html = format_html(
                    "<a class='gma-url-link' href='{}' target='_blank'>{}</a>", url, url_display
                ) if url.startswith(("http", "/")) else mark_safe("")

            cards.append(format_html(
                "<div class='gma-card'>"
                "<div class='gma-thumb-area'>{}</div>"
                "<div class='gma-card-body'>"
                "<div class='gma-field-name'>{}</div>"
                "<div class='gma-badges'>{}</div>"
                "{}{}"
                "</div></div>",
                thumb_html, field_name, badges, path_html, url_html,
            ))

        grid_html = format_html(
            "<div class='gma-grid'>{}</div>",
            mark_safe("".join(str(c) for c in cards)),
        )

        css_link = format_html(
            "<link rel='stylesheet' href='{}'>",
            static("admin/css/game_media_admin.css"),
        )

        return format_html(
            "{}<div class='gma-wrap'>{}{}{}</div>",
            css_link, backend_html, guide_html, grid_html,
        )

    media_storage_diagnostic.short_description = "Storage Status"

    @admin.action(description="Audit media storage for selected games")
    def action_audit_media(self, request, queryset):
        results = []
        for game in queryset:
            missing = []
            ok = []
            for field_name in _IMAGE_FIELDS:
                field = getattr(game, field_name, None)
                name = getattr(field, "name", "") or ""
                if not name:
                    continue
                if storage_file_exists(field):
                    ok.append(field_name)
                else:
                    missing.append(field_name)
            if missing:
                self.message_user(
                    request,
                    f"{game.name}: MISSING in storage — {', '.join(missing)}",
                    level=messages.WARNING,
                )
            else:
                self.message_user(
                    request,
                    f"{game.name}: all media files present ({', '.join(ok) or 'all empty'})",
                    level=messages.SUCCESS,
                )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Bust the cached active-games dict so is_active changes take effect immediately
        from django.core.cache import cache
        cache.delete('context_active_games')


@admin.register(GameRosterConfig)
class GameRosterConfigAdmin(ModelAdmin):
    list_display = ['game', 'max_team_size', 'max_substitutes', 'has_roles']
    list_filter = ['has_roles', 'allow_coaches', 'allow_analysts']
    search_fields = ['game__name']


@admin.register(GamePlayerIdentityConfig)
class GamePlayerIdentityConfigAdmin(ModelAdmin):
    list_display = ['game', 'field_name', 'display_name', 'is_required', 'order']
    list_filter = ['is_required', 'field_type']
    search_fields = ['game__name', 'field_name', 'display_name']
    ordering = ['game', 'order']


@admin.register(GameTournamentConfig)
class GameTournamentConfigAdmin(ModelAdmin):
    list_display = ['game', 'default_match_format', 'default_scoring_type', 'max_score', 'require_check_in', 'allow_draws']
    list_filter = ['default_match_format', 'default_scoring_type', 'require_check_in', 'allow_draws']
    search_fields = ['game__name']
    fieldsets = (
        ('Game', {'fields': ('game',)}),
        ('Match Settings', {'fields': ('available_match_formats', 'default_match_format', 'default_match_duration_minutes')}),
        ('Scoring', {'fields': ('default_scoring_type', 'scoring_rules', 'max_score', 'allow_draws', 'overtime_enabled')}),
        ('Tiebreakers', {'fields': ('default_tiebreakers',)}),
        ('Format Support', {'fields': ('supports_single_elimination', 'supports_double_elimination', 'supports_round_robin', 'supports_swiss', 'supports_group_stage')}),
        ('Check-in', {'fields': ('require_check_in', 'check_in_window_minutes')}),
        ('Credentials (Manual Input Schema)', {
            'fields': ('credential_schema',),
            'description': 'JSON array of credential fields for games without APIs. '
                         'Format: [{"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": true}]',
        }),
    )


@admin.register(GameRole)
class GameRoleAdmin(ModelAdmin):
    list_display = ['game', 'role_name', 'role_code', 'is_competitive', 'is_active', 'order']
    list_filter = ['game', 'is_competitive', 'is_active']
    search_fields = ['game__name', 'role_name', 'role_code']
    ordering = ['game', 'order', 'role_name']


# GameMatchPipeline admin now registered in apps.match_engine.admin (Phase 6)


@admin.register(GameMapPool)
class GameMapPoolAdmin(ModelAdmin):
    list_display = ['game', 'map_name', 'map_code', 'is_active', 'is_competitive', 'order']
    list_filter = ['game', 'is_active', 'is_competitive']
    list_editable = ['is_active', 'is_competitive', 'order']
    search_fields = ['game__name', 'map_name', 'map_code']
    ordering = ['game', 'order', 'map_name']


@admin.register(GamePipelineTemplate)
class GamePipelineTemplateAdmin(ModelAdmin):
    list_display = ['game', 'name', 'pipeline_mode', 'scoring_type', 'default_match_format', 'is_default', 'is_active']
    list_filter = ['game', 'pipeline_mode', 'scoring_type', 'is_default', 'is_active']
    list_editable = ['is_active', 'is_default']
    search_fields = ['game__name', 'name']
    fieldsets = (
        ('Game', {'fields': ('game', 'name', 'is_default', 'is_active')}),
        ('Pipeline', {'fields': ('pipeline_mode', 'scoring_type', 'default_match_format')}),
        ('Tiebreakers', {'fields': ('tiebreakers',)}),
        ('Manual Input Schema', {
            'fields': ('credential_schema',),
            'description': 'JSON array of credential fields for match setup. '
                         'This is the per-pipeline override; falls back to GameTournamentConfig.',
        }),
    )


@admin.register(VetoConfiguration)
class VetoConfigurationAdmin(ModelAdmin):
    list_display = ['game', 'name', 'domain', 'time_per_action_seconds', 'is_active']
    list_filter = ['domain', 'is_active']
    search_fields = ['game__name', 'name']


# ---------------------------------------------------------------------------
# MediaCleanupCandidate admin
# ---------------------------------------------------------------------------

@admin.register(MediaCleanupCandidate)
class MediaCleanupCandidateAdmin(ModelAdmin):
    list_display = [
        "file_name_short", "source_model", "source_field", "reason",
        "status", "eligible_after", "is_eligible_display",
    ]
    list_filter = ["status", "reason", "source_model", "storage_type"]
    search_fields = ["file_name", "source_model", "source_field"]
    readonly_fields = [
        "file_name", "storage_type", "source_model", "source_object_id",
        "source_field", "reason", "created_at", "eligible_after",
        "deleted_at", "error_message", "metadata",
    ]
    ordering = ["-created_at"]
    actions = ["action_delete_eligible", "action_mark_skipped", "action_rescan"]

    def has_add_permission(self, request):
        return False

    def file_name_short(self, obj):
        name = obj.file_name or ""
        # Show only the tail of the path to keep the column readable.
        tail = name.split("/")[-1] if "/" in name else name
        return format_html(
            "<span title='{}'>{}</span>", name, tail[:40] + ("…" if len(tail) > 40 else "")
        )
    file_name_short.short_description = "File"

    def is_eligible_display(self, obj):
        if obj.status != MediaCleanupCandidate.STATUS_PENDING:
            return mark_safe("<span style='color:#9ca3af'>—</span>")
        if obj.is_eligible:
            return mark_safe("<span style='color:#22c55e;font-weight:bold'>&#10003; ready</span>")
        return mark_safe("<span style='color:#f59e0b'>&#8987; waiting</span>")
    is_eligible_display.short_description = "Eligible?"

    @admin.action(description="Delete selected eligible media from Cloudinary (dry-run first)")
    def action_delete_eligible(self, request, queryset):
        from apps.games.services.media_cleanup_service import MediaCleanupService
        service = MediaCleanupService()
        # First a dry-run to report, then confirm with a second action or immediate apply
        pending_eligible = [c for c in queryset if c.is_eligible]
        if not pending_eligible:
            self.message_user(request, "No eligible (pending + past retention) candidates selected.", messages.WARNING)
            return
        # Apply deletion immediately — admin action is an intentional human gesture.
        deleted = skipped = failed = 0
        for candidate in pending_eligible:
            outcome = service._process_one(candidate, dry_run=False)
            if outcome == "deleted":
                deleted += 1
            elif outcome == "skipped":
                skipped += 1
            else:
                failed += 1
        self.message_user(
            request,
            f"Cleanup complete: deleted={deleted} skipped={skipped} failed={failed}",
            messages.SUCCESS if not failed else messages.WARNING,
        )

    @admin.action(description="Mark selected as skipped (suppress future deletion)")
    def action_mark_skipped(self, request, queryset):
        updated = queryset.filter(status=MediaCleanupCandidate.STATUS_PENDING).update(
            status=MediaCleanupCandidate.STATUS_SKIPPED,
            error_message="Manually skipped by admin.",
        )
        self.message_user(request, f"Marked {updated} candidate(s) as skipped.")

    @admin.action(description="Rescan: re-queue skipped candidates as pending")
    def action_rescan(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=MediaCleanupCandidate.STATUS_SKIPPED).update(
            status=MediaCleanupCandidate.STATUS_PENDING,
            error_message="",
            eligible_after=timezone.now(),
        )
        self.message_user(request, f"Re-queued {updated} candidate(s) as pending.")


# ---------------------------------------------------------------------------
# MaintenanceRunLog admin
# ---------------------------------------------------------------------------

@admin.register(MaintenanceRunLog)
class MaintenanceRunLogAdmin(ModelAdmin):
    list_display = ["created_at_display", "task_name", "status_badge", "actor", "duration_display", "summary_preview"]
    list_filter = ["status", "task_name", "created_at"]
    search_fields = ["task_name", "error_message"]
    readonly_fields = [
        "user", "task_name", "status", "started_at", "finished_at",
        "duration_ms", "summary_formatted", "error_message", "created_at",
        "operations_link",
    ]
    ordering = ["-created_at"]
    fieldsets = [
        ("Run Info", {"fields": ["task_name", "status", "user", "started_at", "finished_at", "duration_ms", "operations_link"]}),
        ("Result", {"fields": ["summary_formatted"]}),
        ("Error", {"fields": ["error_message"], "classes": ["collapse"]}),
        ("Meta", {"fields": ["created_at"], "classes": ["collapse"]}),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "—"
    created_at_display.short_description = "When"
    created_at_display.admin_order_field = "created_at"

    def status_badge(self, obj):
        colors = {"success": "#22c55e", "partial": "#f59e0b", "failed": "#ef4444"}
        icons = {"success": "&#10003;", "partial": "&#9888;", "failed": "&#10007;"}
        c = colors.get(obj.status, "#9ca3af")
        i = icons.get(obj.status, "?")
        return format_html(
            "<span style='color:{};font-weight:bold'>{} {}</span>", c, mark_safe(i), obj.status
        )
    status_badge.short_description = "Status"

    def actor(self, obj):
        return obj.user.username if obj.user else "—"
    actor.short_description = "By"

    def duration_display(self, obj):
        if obj.duration_ms is None:
            return "—"
        if obj.duration_ms < 1000:
            return f"{obj.duration_ms} ms"
        return f"{obj.duration_ms / 1000:.1f} s"
    duration_display.short_description = "Duration"

    def summary_preview(self, obj):
        if not obj.summary:
            return "—"
        parts = [f"{k}={v}" for k, v in list(obj.summary.items())[:4] if k not in ("missing_detail", "orphans_preview")]
        return mark_safe(f"<span style='font-size:11px;color:#9ca3af'>{', '.join(parts)}</span>")
    summary_preview.short_description = "Summary"

    def summary_formatted(self, obj):
        import json
        if not obj.summary:
            return mark_safe("<em>No summary data.</em>")
        try:
            pretty = json.dumps(obj.summary, indent=2, default=str)
            return format_html(
                "<pre style='font-size:11px;white-space:pre-wrap;word-break:break-all;"
                "background:#111827;color:#a5b4fc;padding:10px;border-radius:6px;max-height:300px;overflow:auto'>{}</pre>",
                pretty,
            )
        except Exception:
            return format_html("<code>{}</code>", str(obj.summary))
    summary_formatted.short_description = "Result Summary"

    def operations_link(self, obj):
        return format_html(
            "<a href='/admin/maintenance/' style='color:#6366f1'>&larr; Back to Operations Center</a>"
        )
    operations_link.short_description = "Operations"
