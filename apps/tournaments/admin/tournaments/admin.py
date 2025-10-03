from __future__ import annotations

from typing import List

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.utils.safestring import mark_safe

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
    search_fields = ("name", "slug")
    readonly_fields = (
        "link_bracket",
        "link_settings",
        "link_valorant_config",
        "link_efootball_config",
        "link_export_bracket",
        "link_force_regenerate",
        "bracket_json_preview",
        "created_at",
        "updated_at",
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for COMPLETED tournaments (archived)."""
        readonly = list(super().get_readonly_fields(request, obj))
        
        # If tournament is COMPLETED, make everything readonly (archived)
        if obj and obj.status == 'COMPLETED':
            # Get all model fields except auto-generated ones
            all_fields = [f.name for f in obj._meta.fields if f.name not in ['id']]
            # Add any additional readonly fields we already have
            readonly = list(set(readonly + all_fields))
            
        return readonly
    
    def get_fields(self, request, obj=None):
        """For archived tournaments, return all fields to display."""
        if obj and obj.status == 'COMPLETED':
            # Return all model fields for display
            all_fields = [f.name for f in obj._meta.fields if f.name not in ['id']]
            # Add the readonly-only link fields
            link_fields = [
                "link_export_bracket", 
                "link_force_regenerate", 
                "bracket_json_preview"
            ]
            if hasattr(obj, "bracket"):
                link_fields.append("link_bracket")
            if hasattr(obj, "settings"):
                link_fields.append("link_settings")
            if hasattr(obj, "valorant_config"):
                link_fields.append("link_valorant_config")
            if hasattr(obj, "efootball_config"):
                link_fields.append("link_efootball_config")
            
            return all_fields + link_fields
        
        # For non-archived, return None to use default behavior (fieldsets)
        return None
    
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
                        '⚠️ This tournament is ARCHIVED (status: COMPLETED). '
                        'All data is read-only and preserved for records. '
                        'To create a similar tournament, use the "Clone/Copy" action from the list view.'
                    )
            except Exception:
                pass
        
        return super().changeform_view(request, object_id, form_url, extra_context)

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
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
        fields = _present_fields(Tournament)
        cols: List[str] = ["id", "name"]
        if "game" in fields:
            cols.append("game")
        cols.append("status_column")
        cols.append("bracket_status_column")
        for name in ("reg_open_at", "reg_close_at", "start_at", "end_at"):
            if name in fields:
                cols.append(name)
        cols.append("fee_column")
        # Add slot information if slot_size field exists
        if "slot_size" in fields:
            cols.append("slots_column")
        return tuple(cols)

    def get_list_filter(self, request):
        try:
            from ..components import HasEntryFeeFilter
        except Exception:
            HasEntryFeeFilter = None
        fields = _present_fields(Tournament)
        lf = [name for name in ("game", "status", "start_at", "end_at") if name in fields]
        if HasEntryFeeFilter:
            lf.append(HasEntryFeeFilter)
        return tuple(lf)

    def get_prepopulated_fields(self, request, obj=None):
        # No prepopulated fields for archived tournaments (all fields readonly)
        if obj and obj.status == 'COMPLETED':
            return {}
        return {"slug": ("name",)} if "slug" in _present_fields(Tournament) else {}

    def get_date_hierarchy(self, request):
        return "start_at" if "start_at" in _present_fields(Tournament) else None

    def get_fieldsets(self, request, obj=None):
        fsets = []
        
        # For archived (COMPLETED) tournaments, use a simplified readonly fieldset
        if obj and obj.status == 'COMPLETED':
            # Include all important fields as readonly
            all_fields = []
            
            # Basics
            basics = _fields_if_exist(Tournament, "name", "slug", "game", "short_description", "banner")
            if basics:
                all_fields.extend(basics)
            
            # Schedule & Status
            sched = _fields_if_exist(Tournament, "status", "start_at", "end_at", "reg_open_at", "reg_close_at", "slot_size")
            if sched:
                all_fields.extend(sched)
            
            # Finance
            finance = _fields_if_exist(Tournament, "entry_fee_bdt", "prize_pool_bdt")
            if finance:
                all_fields.extend(finance)
            
            # Metadata
            meta = _fields_if_exist(Tournament, "created_at", "updated_at", "groups_published")
            if meta:
                all_fields.extend(meta)
            
            # Links (always readonly anyway)
            links = ["link_export_bracket", "link_force_regenerate", "bracket_json_preview"]
            if hasattr(obj, "bracket"):
                links.append("link_bracket")
            if hasattr(obj, "settings"):
                links.append("link_settings")
            if hasattr(obj, "valorant_config"):
                links.append("link_valorant_config")
            if hasattr(obj, "efootball_config"):
                links.append("link_efootball_config")
            all_fields.extend(links)
            
            fsets.append((
                "🔒 Archived Tournament (Read-Only)", 
                {
                    "fields": tuple(all_fields),
                    "description": "This tournament is COMPLETED and archived. All fields are read-only."
                }
            ))
            return tuple(fsets)

        # Normal editable fieldsets for non-archived tournaments
        basics = _fields_if_exist(Tournament, "name", "slug", "game", "short_description")
        if basics:
            fsets.append(("Basics (required)", {"fields": tuple(basics), "description": "Required fields for every tournament."}))

        sched_rows = []
        # Add status field to schedule section
        status_field = _fields_if_exist(Tournament, "status")
        if status_field:
            sched_rows.append(tuple(status_field))
        
        pair1 = _fields_if_exist(Tournament, "start_at", "end_at")
        pair2 = _fields_if_exist(Tournament, "reg_open_at", "reg_close_at")
        if pair1:
            sched_rows.append(tuple(pair1))
        if pair2:
            sched_rows.append(tuple(pair2))
        # Add slot_size to schedule section
        slot_field = _fields_if_exist(Tournament, "slot_size")
        if slot_field:
            sched_rows.append(tuple(slot_field))
        if sched_rows:
            fsets.append(("Schedule & Status", {"fields": tuple(sched_rows), "description": "Tournament status, timing, and registration limits. COMPLETED tournaments are archived and read-only."}))

        entry = _fields_if_exist(Tournament, "entry_fee_bdt", "entry_fee", "bank_instructions")
        if entry:
            fsets.append(("Entry & Bank (optional)", {"fields": tuple(entry), "description": "Optional entry fee and payout helpers."}))

        links = ["link_export_bracket", "link_force_regenerate", "bracket_json_preview"]
        if obj is not None:
            if hasattr(obj, "bracket"):
                links.append("link_bracket")
            if hasattr(obj, "settings"):
                links.append("link_settings")
            if hasattr(obj, "valorant_config"):
                links.append("link_valorant_config")
            if hasattr(obj, "efootball_config"):
                links.append("link_efootball_config")
        fsets.append(("Advanced / Related (optional)", {"fields": tuple(links), "description": "Quick links to optional tools and related records."}))
        return tuple(fsets)

    def get_inline_instances(self, request, obj=None):
        instances = []

        # Add TournamentSchedule inline (Pilot Phase - Phase 0)
        instances.append(TournamentScheduleInline(self.model, self.admin_site))
        
        # Add TournamentCapacity inline (Phase 1)
        instances.append(TournamentCapacityInline(self.model, self.admin_site))

        try:
            from ..components import TournamentSettingsInline, ValorantConfigInline, EfootballConfigInline
        except Exception:
            TournamentSettingsInline = ValorantConfigInline = EfootballConfigInline = None

        if TournamentSettingsInline:
            instances.append(TournamentSettingsInline(self.model, self.admin_site))
        if ValorantConfigInline:
            instances.append(ValorantConfigInline(self.model, self.admin_site))
        if EfootballConfigInline:
            instances.append(EfootballConfigInline(self.model, self.admin_site))

        try:
            from ...models import Registration as _Registration
            class _RegInline(RegistrationInline):
                model = _Registration
            instances.append(_RegInline(self.model, self.admin_site))
        except Exception:
            pass

        instances.append(CompactMatchInline(self.model, self.admin_site))

        try:
            from apps.economy.admin import CoinPolicyInline
        except Exception:
            CoinPolicyInline = None
        if CoinPolicyInline:
            instances.append(CoinPolicyInline(self.model, self.admin_site))

        return instances

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
