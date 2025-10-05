from __future__ import annotations

from typing import List

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from ...models import Tournament

# idempotent unregister
try:
    admin.site.unregister(Tournament)
except NotRegistered:
    pass

from .inlines import (
    RegistrationInline,
    CompactMatchInline,
    _present_fields, _fields_if_exist,
)
from .schedule_inline import TournamentScheduleInline
from .capacity_inline import TournamentCapacityInline
from .mixins import AdminLinkMixin, ExportBracketMixin, ActionsMixin


@admin.register(Tournament)
class TournamentAdmin(AdminLinkMixin, ExportBracketMixin, ActionsMixin, admin.ModelAdmin):
    save_on_top = True
    search_fields = ("name", "slug", "organizer__user__username")
    list_filter = ("game", "status", "tournament_type", "format", "platform", "language")
    date_hierarchy = "created_at"
    
    readonly_fields = (
        "created_at",
        "updated_at",
        "link_bracket",
        "link_export_bracket",
        "link_force_regenerate",
        "bracket_json_preview",
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for COMPLETED tournaments (archived)."""
        readonly = list(super().get_readonly_fields(request, obj))
        
        # If tournament is COMPLETED, make everything readonly (archived)
        if obj and obj.status == 'COMPLETED':
            all_fields = [f.name for f in obj._meta.fields if f.name not in ['id']]
            readonly = list(set(readonly + all_fields))
            
        return readonly
    
    def get_prepopulated_fields(self, request, obj=None):
        """Auto-populate slug from name for new tournaments."""
        if obj and obj.status == 'COMPLETED':
            return {}
        return {"slug": ("name",)}
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of COMPLETED tournaments (archived)."""
        if obj and obj.status == 'COMPLETED':
            return False
        return super().has_delete_permission(request, obj)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Add archived status notice to change form."""
        extra_context = extra_context or {}
        
        if object_id:
            try:
                obj = self.get_object(request, object_id)
                if obj and obj.status == 'COMPLETED':
                    extra_context['is_archived'] = True
                    extra_context['archived_message'] = (
                        '🔒 This tournament is ARCHIVED (COMPLETED). '
                        'All data is read-only. Use "Clone Tournament" to create a new one.'
                    )
            except Exception:
                pass
        
        return super().changeform_view(request, object_id, form_url, extra_context)

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}
        js = ('admin/js/tournament_admin.js',)  # For dynamic field visibility

    def get_queryset(self, request):
        """Filter tournaments by game type based on user permissions."""
        qs = super().get_queryset(request).select_related('organizer', 'organizer__user')
        user = request.user
        
        if user.is_superuser:
            return qs
            
        group_names = set(user.groups.values_list("name", flat=True))
        if "Valorant Organizer" in group_names:
            return qs.filter(game=Tournament.Game.VALORANT)
        if "eFootball Organizer" in group_names:
            return qs.filter(game=Tournament.Game.EFOOTBALL)
            
        return qs

    def get_list_display(self, request):
        """Customize list display columns."""
        return (
            "id",
            "name",
            "game_badge",
            "status_badge",
            "tournament_type",
            "platform",
            "organizer_display",
            "participants_count",
            "created_at",
        )

    def get_fieldsets(self, request, obj=None):
        """Organized fieldsets with logical grouping."""
        
        # For archived (COMPLETED) tournaments, show simplified readonly view
        if obj and obj.status == 'COMPLETED':
            return (
                ('🔒 Archived Tournament (Read-Only)', {
                    'fields': (
                        'name', 'slug', 'game', 'status',
                        'tournament_type', 'format', 'platform',
                        'short_description', 'description',
                        'organizer', 'banner',
                        'region', 'language',
                        'groups_published',
                        'created_at', 'updated_at',
                    ),
                    'description': 'This tournament is COMPLETED and archived. All fields are read-only.'
                }),
                ('🔗 Related Records', {
                    'fields': (
                        'link_bracket',
                        'link_export_bracket',
                        'link_force_regenerate',
                        'bracket_json_preview',
                    ),
                    'classes': ('collapse',),
                }),
            )
        
        # Normal editable fieldsets for active tournaments
        fieldsets = [
            ('📋 Basic Information', {
                'fields': (
                    ('name', 'slug'),
                    ('game', 'status'),
                    'short_description',
                ),
                'description': 'Core tournament details. Name and game are required.'
            }),
            ('🎮 Tournament Configuration', {
                'fields': (
                    ('tournament_type', 'format'),
                    ('platform', 'region'),
                    'language',
                ),
                'description': 'Tournament format and setup.'
            }),
            ('👤 Organizer & Details', {
                'fields': (
                    'organizer',
                    'description',
                    'banner',
                ),
                'description': 'Tournament organizer and detailed information.'
            }),
            ('⚙️ Advanced Settings', {
                'fields': (
                    'groups_published',
                ),
                'classes': ('collapse',),
                'description': 'Advanced options for bracket visibility and publishing.'
            }),
        ]
        
        # Add deprecated fields section only if they have values
        if obj and self._has_deprecated_values(obj):
            fieldsets.append(
                ('⚠️ Legacy Fields (Deprecated)', {
                    'fields': (
                        'slot_size',
                        ('reg_open_at', 'reg_close_at'),
                        ('start_at', 'end_at'),
                        ('entry_fee_bdt', 'prize_pool_bdt'),
                    ),
                    'classes': ('collapse',),
                    'description': (
                        '⚠️ These fields are deprecated. '
                        'Use TournamentSchedule, TournamentCapacity, and TournamentFinance inlines instead.'
                    )
                })
            )
        
        # Add bracket tools section
        if obj:
            fieldsets.append(
                ('🔧 Bracket Tools', {
                    'fields': (
                        'link_bracket',
                        'link_export_bracket',
                        'link_force_regenerate',
                        'bracket_json_preview',
                    ),
                    'classes': ('collapse',),
                    'description': 'Bracket management and export tools.'
                })
            )
        
        # Add metadata
        fieldsets.append(
            ('📊 Metadata', {
                'fields': (
                    ('created_at', 'updated_at'),
                ),
                'classes': ('collapse',),
            })
        )
        
        return tuple(fieldsets)
    
    def _has_deprecated_values(self, obj):
        """Check if any deprecated fields have non-null values."""
        return any([
            obj.slot_size,
            obj.reg_open_at,
            obj.reg_close_at,
            obj.start_at,
            obj.end_at,
            obj.entry_fee_bdt,
            obj.prize_pool_bdt,
        ])

    def get_inline_instances(self, request, obj=None):
        """Configure inline editors based on tournament state."""
        instances = []

        # Core inlines - always show
        instances.append(TournamentScheduleInline(self.model, self.admin_site))
        instances.append(TournamentCapacityInline(self.model, self.admin_site))

        # Finance inline
        try:
            from ..components import TournamentFinanceInline
            instances.append(TournamentFinanceInline(self.model, self.admin_site))
        except ImportError:
            pass

        # Media & Rules inlines
        try:
            from ..components import TournamentMediaInline, TournamentRulesInline
            instances.append(TournamentMediaInline(self.model, self.admin_site))
            instances.append(TournamentRulesInline(self.model, self.admin_site))
        except ImportError:
            pass

        # Game-specific configuration inlines (show based on game type)
        if obj and obj.game:
            try:
                if obj.game == Tournament.Game.VALORANT:
                    from ..components import ValorantConfigInline
                    instances.append(ValorantConfigInline(self.model, self.admin_site))
                elif obj.game == Tournament.Game.EFOOTBALL:
                    from ..components import EfootballConfigInline
                    instances.append(EfootballConfigInline(self.model, self.admin_site))
            except ImportError:
                pass

        # Advanced settings inline (collapsed by default)
        try:
            from ..components import TournamentSettingsInline
            instances.append(TournamentSettingsInline(self.model, self.admin_site))
        except ImportError:
            pass

        # Registrations and Matches (read-only snapshots)
        try:
            from ...models import Registration as _Registration
            class _RegInline(RegistrationInline):
                model = _Registration
            instances.append(_RegInline(self.model, self.admin_site))
        except Exception:
            pass

        instances.append(CompactMatchInline(self.model, self.admin_site))

        # Economy integration
        try:
            from apps.economy.admin import CoinPolicyInline
            instances.append(CoinPolicyInline(self.model, self.admin_site))
        except ImportError:
            pass

        return instances

    # ==================== LIST DISPLAY METHODS ====================
    
    @admin.display(description="Game", ordering="game")
    def game_badge(self, obj):
        """Display game with color-coded badge."""
        game_colors = {
            "valorant": "#FA4454",
            "efootball": "#0057E7",
        }
        game_name = obj.get_game_display()
        color = game_colors.get(obj.game, "#6c757d")
        
        return format_html(
            '<span style="display:inline-block;padding:4px 10px;background:{};color:white;'
            'border-radius:4px;font-weight:bold;font-size:11px;text-transform:uppercase;">{}</span>',
            color, game_name
        )
    
    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        """Display tournament status with color coding."""
        status_colors = {
            "DRAFT": "#6c757d",      # Gray
            "PUBLISHED": "#0d6efd",  # Blue
            "RUNNING": "#198754",    # Green
            "COMPLETED": "#dc3545",  # Red
        }
        
        color = status_colors.get(obj.status, "#6c757d")
        
        return format_html(
            '<span style="display:inline-block;padding:4px 8px;background:{};color:white;'
            'border-radius:4px;font-weight:bold;font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    
    @admin.display(description="Organizer")
    def organizer_display(self, obj):
        """Display organizer name with link."""
        if not obj.organizer:
            return format_html('<em style="color:#999;">No organizer</em>')
        
        return format_html(
            '<a href="/admin/user_profile/userprofile/{}/change/">{}</a>',
            obj.organizer.pk,
            obj.organizer.user.username if obj.organizer.user else 'Unknown'
        )
    
    @admin.display(description="Participants")
    def participants_count(self, obj):
        """Display participant count."""
        try:
            count = obj.registrations.filter(status='APPROVED').count()
            return format_html('<strong>{}</strong>', count)
        except:
            return '—'

    @admin.display(description="Status")
    def status_column(self, obj: Tournament):
        """Display tournament status with color coding."""
        if not hasattr(obj, "status"):
            return "—"
        
        status = getattr(obj, "status", "DRAFT")
        
        # Color-coded status badges
        colors = {
            "DRAFT": "#6c757d",      # Gray
            "PUBLISHED": "#0d6efd",  # Blue
            "RUNNING": "#198754",    # Green
            "COMPLETED": "#dc3545", # Red
        }
        
        color = colors.get(status, "#6c757d")
        badge_html = f'<span style="display:inline-block;padding:4px 8px;background:{color};color:white;border-radius:4px;font-weight:bold;font-size:11px;">{status}</span>'
        
        return mark_safe(badge_html)

    @admin.display(description="Bracket")
    def bracket_status_column(self, obj: Tournament):
        b = getattr(obj, "bracket", None)
        if not b:
            return "—"
        return "Locked" if getattr(b, "is_locked", False) else "Unlocked"

    @admin.display(description="Entry Fee")
    def fee_column(self, obj: Tournament):
        if hasattr(obj, "entry_fee_bdt"):
            return getattr(obj, "entry_fee_bdt")
        if hasattr(obj, "entry_fee"):
            return getattr(obj, "entry_fee")
        return None

    @admin.display(description="Slots")
    def slots_column(self, obj: Tournament):
        try:
            return getattr(obj, "slots_text", None) or "No limit"
        except Exception:
            return "—"

    actions = (
        # Tournament management
        "action_clone_tournaments",
        # Status management actions
        "action_publish_tournaments",
        "action_start_tournaments",
        "action_complete_tournaments",
        "action_reset_to_draft",
        # Bracket actions
        "action_generate_bracket_safe",
        "action_force_regenerate_bracket",
        "action_lock_bracket",
        "action_unlock_bracket",
        # Scheduling actions
        "action_auto_schedule",
        "action_clear_schedule",
        # Coin award actions
        "action_award_participation",
        "action_award_placements",
    )
