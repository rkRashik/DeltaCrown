# apps/tournaments/admin/tournaments.py
from __future__ import annotations

from typing import List, Tuple, Optional

from django.contrib import admin, messages
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe
from django.urls import reverse, NoReverseMatch

from ..models import Tournament
from ..models_registration_policy import TournamentRegistrationPolicy

# Optional inlines for one-to-one children
try:
    from .components import (
        EfootballConfigInline,
        ValorantConfigInline,
        TournamentSettingsInline,
        HasEntryFeeFilter,
    )
except Exception:  # pragma: no cover
    EfootballConfigInline = ValorantConfigInline = TournamentSettingsInline = None
    HasEntryFeeFilter = None


# ---------- helpers ----------

def _present_fields(model) -> set[str]:
    return {f.name for f in model._meta.get_fields()}


def _fields_if_exist(model, *names) -> List[str]:
    present = _present_fields(model)
    return [n for n in names if n in present]


def _mode_choices_for_game(game_value: str | None) -> List[Tuple[str, str]]:
    """
    Allowed registration modes by game.
    - Valorant: Team only
    - eFootball: Solo or Duo
    - Others: allow all (can tighten later)
    """
    if not game_value:
        return list(TournamentRegistrationPolicy.MODE_CHOICES)
    g = (game_value or "").strip().lower()
    if g == "valorant":
        return [(TournamentRegistrationPolicy.MODE_TEAM, "Team")]
    if g == "efootball":
        return [
            (TournamentRegistrationPolicy.MODE_SOLO, "Solo (1v1)"),
            (TournamentRegistrationPolicy.MODE_DUO, "Duo (2v2)"),
        ]
    return list(TournamentRegistrationPolicy.MODE_CHOICES)


class _DynamicFieldsInlineMixin:
    """Choose which columns to show based on real model fields."""
    _candidate_fields: List[str] = []

    def get_fields(self, request, obj=None):
        model_fields = {f.name for f in self.model._meta.get_fields()}
        fields = [f for f in self._candidate_fields if f in model_fields]
        if "id" in model_fields and "id" not in fields:
            fields.insert(0, "id")
        return fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RegistrationInline(_DynamicFieldsInlineMixin, admin.TabularInline):
    """Show who registered for THIS tournament."""
    extra = 0
    can_delete = False
    verbose_name_plural = "Registrations"
    model = None  # set in get_inline_instances
    _candidate_fields = [
        "user", "user_profile", "team",
        "payment_status", "payment",
        "created_at", "created", "created_on",
    ]


class MatchInline(_DynamicFieldsInlineMixin, admin.TabularInline):
    """Show matches for THIS tournament."""
    extra = 0
    can_delete = False
    verbose_name_plural = "Matches"
    model = None  # set in get_inline_instances
    _candidate_fields = [
        "round_number", "match_number",
        "team1", "team2",
        "scheduled_at", "result",
        "created_at", "updated_at",
    ]


# ---------- actions (optional bracket helpers) ----------

@admin.action(description="Generate bracket (single-elimination)")
def action_generate_bracket(modeladmin, request, queryset):
    """Calls apps.corelib.brackets.generate_bracket(tournament)."""
    from apps.corelib.brackets import generate_bracket  # same function as mgmt command
    done = 0
    for t in queryset:
        try:
            generate_bracket(t)
            done += 1
        except Exception as e:
            modeladmin.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
    modeladmin.message_user(request, f"Generated bracket for {done} tournament(s).")


@admin.action(description="Lock bracket (prevent edits)")
def action_lock_bracket(modeladmin, request, queryset):
    try:
        from ..models import Bracket
    except Exception:
        modeladmin.message_user(request, "No Bracket model found.", level=messages.WARNING)
        return
    updated = 0
    for t in queryset:
        b = getattr(t, "bracket", None)
        if b:
            b.is_locked = True
            b.save(update_fields=["is_locked"])
            updated += 1
    modeladmin.message_user(request, f"Locked {updated} bracket(s).")


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    - No class-level 'fields'/'fieldsets'/'exclude' that can point at missing fields.
    - Everything adapts to your actual Tournament schema.
    - Shows Registration Policy inline on add/change.
    - Shows per-tournament Registrations & Matches as read-only inlines.
    """
    save_on_top = True
    search_fields = ("name", "slug")

    def get_list_display(self, request):
        fields = _present_fields(Tournament)
        cols: List[str] = ["id", "name"]
        if "game" in fields:
            cols.append("game")
        cols.append("status_column")
        if "reg_open_at" in fields:
            cols.append("reg_open_at")
        if "reg_close_at" in fields:
            cols.append("reg_close_at")
        if "start_at" in fields:
            cols.append("start_at")
        if "end_at" in fields:
            cols.append("end_at")
        # works whether you have entry_fee_bdt or entry_fee
        cols.append("fee_column")
        return tuple(cols)

    def get_list_filter(self, request):
        fields = _present_fields(Tournament)
        lf = []
        for name in ("game", "status", "start_at", "end_at"):
            if name in fields:
                lf.append(name)
        # Optional "Has entry fee" filter if present
        if HasEntryFeeFilter:
            lf.append(HasEntryFeeFilter)
        return tuple(lf)

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)} if "slug" in _present_fields(Tournament) else {}

    def get_date_hierarchy(self, request):
        return "start_at" if "start_at" in _present_fields(Tournament) else None

    # Dynamic fieldsets: compute from fields that actually exist on your model.
    def get_fieldsets(self, request, obj=None):
        f = []
        basics = _fields_if_exist(Tournament, "name", "slug", "game", "short_description")
        if basics:
            f.append(("Basics", {"fields": tuple(basics)}))

        sched_rows = []
        pair1 = _fields_if_exist(Tournament, "start_at", "end_at")
        pair2 = _fields_if_exist(Tournament, "reg_open_at", "reg_close_at")
        if pair1:
            sched_rows.append(tuple(pair1))
        if pair2:
            sched_rows.append(tuple(pair2))
        if sched_rows:
            f.append(("Schedule", {"fields": tuple(sched_rows)}))

        entry = _fields_if_exist(Tournament, "entry_fee_bdt", "entry_fee", "bank_instructions")
        if entry:
            f.append(("Entry & Bank", {
                "fields": tuple(entry),
                "description": "Payments are manually verified from Registration rows.",
            }))

        # SHOW LINKS ONLY ON CHANGE VIEW.
        # Do NOT put reverse one-to-one relations in fields — they'll 500 on the ADD view.
        if obj is not None:
            link_fields = []
            if hasattr(obj, "bracket"):
                link_fields.append("link_bracket")
            if hasattr(obj, "settings"):
                link_fields.append("link_settings")
            if hasattr(obj, "valorant_config"):
                link_fields.append("link_valorant_config")
            if hasattr(obj, "efootball_config"):
                link_fields.append("link_efootball_config")
            if link_fields:
                f.append(("Advanced / Related", {"fields": tuple(link_fields)}))

        return tuple(f)

    # Read-only link presenters
    readonly_fields = ("link_bracket", "link_settings", "link_valorant_config", "link_efootball_config")

    def _admin_change_url(self, obj) -> Optional[str]:
        try:
            return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
        except NoReverseMatch:
            return None

    @admin.display(description="Bracket")
    def link_bracket(self, obj: Tournament):
        b = getattr(obj, "bracket", None)
        if not b:
            return "—"
        url = self._admin_change_url(b)
        text = f"Bracket #{b.pk}"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text

    @admin.display(description="Settings")
    def link_settings(self, obj: Tournament):
        s = getattr(obj, "settings", None)
        if not s:
            return "—"
        url = self._admin_change_url(s)
        text = f"Settings #{s.pk}"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text

    @admin.display(description="Valorant Config")
    def link_valorant_config(self, obj: Tournament):
        v = getattr(obj, "valorant_config", None)
        if not v:
            return "—"
        url = self._admin_change_url(v)
        text = f"ValorantConfig #{v.pk}"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text

    @admin.display(description="eFootball Config")
    def link_efootball_config(self, obj: Tournament):
        e = getattr(obj, "efootball_config", None)
        if not e:
            return "—"
        url = self._admin_change_url(e)
        text = f"eFootballConfig #{e.pk}"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text

    # Policy inline appears on ADD & CHANGE
    inlines = []

    def get_inline_instances(self, request, obj=None):
        instances = super().get_inline_instances(request, obj)

        # Attach Registration inline using your real model at runtime
        try:
            from ..models import Registration as _Registration
            reg_inline = RegistrationInline(self.model, self.admin_site)
            reg_inline.model = _Registration
            instances.append(reg_inline)
        except Exception:
            pass

        # Attach Match inline using your real model at runtime
        try:
            from ..models import Match as _Match
            match_inline = MatchInline(self.model, self.admin_site)
            match_inline.model = _Match
            instances.append(match_inline)
        except Exception:
            pass

        # Attach one-to-one config/settings inlines (optional)
        if TournamentSettingsInline:
            instances.append(TournamentSettingsInline(self.model, self.admin_site))
        if ValorantConfigInline:
            instances.append(ValorantConfigInline(self.model, self.admin_site))
        if EfootballConfigInline:
            instances.append(EfootballConfigInline(self.model, self.admin_site))

        # Registration policy inline: adapt choices to game
        try:
            from .tournaments import TournamentRegistrationPolicyInline  # type: ignore
        except Exception:
            TournamentRegistrationPolicyInline = None  # noqa: N806
        if TournamentRegistrationPolicyInline:
            instances.insert(0, TournamentRegistrationPolicyInline(self.model, self.admin_site))

        return instances

    # ----- helpers for list columns -----

    @admin.display(description="Status")
    def status_column(self, obj: Tournament):
        # Show computed current status when not using a dedicated field
        if hasattr(obj, "status") and obj.status:
            return obj.status
        # else guess from dates
        from django.utils import timezone
        now = timezone.now()
        if obj.start_at and obj.end_at:
            if obj.start_at <= now <= obj.end_at:
                return "RUNNING"
            if obj.end_at < now:
                return "COMPLETED"
        return "—"

    @admin.display(description="Entry Fee")
    def fee_column(self, obj: Tournament):
        if hasattr(obj, "entry_fee_bdt"):
            return getattr(obj, "entry_fee_bdt")
        if hasattr(obj, "entry_fee"):
            return getattr(obj, "entry_fee")
        return None

    # local actions (your base.py may also add scheduling actions)
    actions = [action_generate_bracket, action_lock_bracket]
