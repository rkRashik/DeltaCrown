# apps/tournaments/admin/tournaments.py
from __future__ import annotations

from typing import List, Tuple, Optional

from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe

# --- Idempotent registration guard (prevents AlreadyRegistered on re-imports)
from ..models import Tournament
try:
    admin.site.unregister(Tournament)
except NotRegistered:
    pass

# Local models
from ..models_registration_policy import TournamentRegistrationPolicy

# Optional inlines coming from components (if present in your project)
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

# Economy (coins) – keep imports optional/fault-tolerant
try:
    from apps.economy.admin import CoinPolicyInline
    from apps.economy import services as coin_services
    from apps.economy.models import DeltaCrownTransaction
except Exception:  # pragma: no cover
    CoinPolicyInline = None
    coin_services = None
    DeltaCrownTransaction = None


# ---------------- Helpers ----------------

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
    - Others: allow all (fallback to model definition)
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
    """Show who registered for THIS tournament (read-only)."""
    extra = 0
    can_delete = False
    verbose_name_plural = "Registrations"
    model = None  # set via dynamic subclass in get_inline_instances

    # keep this list short and safe; no auto_now/auto_now_add fields here
    _candidate_fields = ["user", "user_profile", "team", "payment_status"]

    def get_fields(self, request, obj=None):
        """
        Only include editable fields. Excludes auto_now/add and PKs (non-editable),
        which otherwise trigger FieldError in modelform_factory.
        """
        if not self.model:
            return []
        fields = []
        for name in self._candidate_fields:
            try:
                f = self.model._meta.get_field(name)
            except Exception:
                continue
            if getattr(f, "editable", True):
                fields.append(name)
        return fields

class MatchInline(_DynamicFieldsInlineMixin, admin.TabularInline):
    """Show matches for THIS tournament (read-only)."""
    extra = 0
    can_delete = False
    verbose_name_plural = "Matches"
    model = None  # set via dynamic subclass in get_inline_instances

    # exclude created_at/updated_at (non-editable)
    _candidate_fields = [
        "round_no", "position",
        "user_a", "user_b",
        "team_a", "team_b",
        "winner_user", "winner_team",
        "scheduled_at",
    ]

    def get_fields(self, request, obj=None):
        if not self.model:
            return []
        fields = []
        for name in self._candidate_fields:
            try:
                f = self.model._meta.get_field(name)
            except Exception:
                continue
            if getattr(f, "editable", True):
                fields.append(name)
        return fields


class TournamentRegistrationPolicyInline(admin.StackedInline):
    """
    One-to-one registration policy shown on ADD & CHANGE.
    The 'registration_mode' choices adapt to the Tournament.game.
    """
    model = TournamentRegistrationPolicy
    can_delete = False
    extra = 0
    fk_name = "tournament"

    def get_fields(self, request, obj=None):
        # Show only fields that actually exist on your model
        return _fields_if_exist(
            self.model,
            "registration_mode",
            "max_slots",
            "min_team_size",
            "max_team_size",
            "allow_substitutes",
            "notes",
        )

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Adapt registration_mode choices by game
        try:
            base_fields = formset.form.base_fields
            if "registration_mode" in base_fields:
                base_fields["registration_mode"].choices = _mode_choices_for_game(
                    getattr(obj, "game", None)
                )
        except Exception:
            pass
        return formset


# ---------------- Tournament Admin ----------------

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    Robust Tournament admin:
      - No static 'fields/fieldsets' pointing to missing columns.
      - Dynamic columns and fieldsets based on your actual schema.
      - Safe, dynamic inlines (policy, settings, per-game configs, registrations, matches, coin policy).
      - Admin actions for bracket helpers and coin awards.
    """
    save_on_top = True
    search_fields = ("name", "slug")

    # ----- list view -----

    def get_list_display(self, request):
        fields = _present_fields(Tournament)
        cols: List[str] = ["id", "name"]
        if "game" in fields:
            cols.append("game")
        cols.append("status_column")
        for name in ("reg_open_at", "reg_close_at", "start_at", "end_at"):
            if name in fields:
                cols.append(name)
        cols.append("fee_column")
        return tuple(cols)

    def get_list_filter(self, request):
        fields = _present_fields(Tournament)
        lf = [name for name in ("game", "status", "start_at", "end_at") if name in fields]
        if HasEntryFeeFilter:
            lf.append(HasEntryFeeFilter)
        return tuple(lf)

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)} if "slug" in _present_fields(Tournament) else {}

    def get_date_hierarchy(self, request):
        return "start_at" if "start_at" in _present_fields(Tournament) else None

    # ----- detail view -----

    def get_fieldsets(self, request, obj=None):
        fsets = []

        basics = _fields_if_exist(Tournament, "name", "slug", "game", "short_description")
        if basics:
            fsets.append(("Basics", {"fields": tuple(basics)}))

        sched_rows = []
        pair1 = _fields_if_exist(Tournament, "start_at", "end_at")
        pair2 = _fields_if_exist(Tournament, "reg_open_at", "reg_close_at")
        if pair1:
            sched_rows.append(tuple(pair1))
        if pair2:
            sched_rows.append(tuple(pair2))
        if sched_rows:
            fsets.append(("Schedule", {"fields": tuple(sched_rows)}))

        entry = _fields_if_exist(Tournament, "entry_fee_bdt", "entry_fee", "bank_instructions")
        if entry:
            fsets.append(("Entry & Bank", {
                "fields": tuple(entry),
                "description": "Payments are manually verified from Registration rows.",
            }))

        # Links to related objects (change view only)
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
                fsets.append(("Advanced / Related", {"fields": tuple(link_fields)}))

        return tuple(fsets)

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
        txt = f"Bracket #{b.pk}"
        return mark_safe(f'<a href="{url}">{txt}</a>') if url else txt

    @admin.display(description="Settings")
    def link_settings(self, obj: Tournament):
        s = getattr(obj, "settings", None)
        if not s:
            return "—"
        url = self._admin_change_url(s)
        txt = f"Settings #{s.pk}"
        return mark_safe(f'<a href="{url}">{txt}</a>') if url else txt

    @admin.display(description="Valorant Config")
    def link_valorant_config(self, obj: Tournament):
        v = getattr(obj, "valorant_config", None)
        if not v:
            return "—"
        url = self._admin_change_url(v)
        txt = f"ValorantConfig #{v.pk}"
        return mark_safe(f'<a href="{url}">{txt}</a>') if url else txt

    @admin.display(description="eFootball Config")
    def link_efootball_config(self, obj: Tournament):
        e = getattr(obj, "efootball_config", None)
        if not e:
            return "—"
        url = self._admin_change_url(e)
        txt = f"eFootballConfig #{e.pk}"
        return mark_safe(f'<a href="{url}">{txt}</a>') if url else txt

    # ----- inlines -----

    def get_inline_instances(self, request, obj=None):
        instances = []

        # 1) Registration policy (always first)
        instances.append(TournamentRegistrationPolicyInline(self.model, self.admin_site))

        # 2) TournamentSettings / Game configs (if present in your project)
        if TournamentSettingsInline:
            instances.append(TournamentSettingsInline(self.model, self.admin_site))
        if ValorantConfigInline:
            instances.append(ValorantConfigInline(self.model, self.admin_site))
        if EfootballConfigInline:
            instances.append(EfootballConfigInline(self.model, self.admin_site))

        # 3) Read-only related lists: Registrations
        try:
            from ..models import Registration as _Registration
            class _RegInline(RegistrationInline):
                model = _Registration
            instances.append(_RegInline(self.model, self.admin_site))
        except Exception:
            pass

        # 4) Read-only related lists: Matches
        try:
            from ..models import Match as _Match
            class _MatchInline(MatchInline):
                model = _Match
            instances.append(_MatchInline(self.model, self.admin_site))
        except Exception:
            pass

        # 5) Coin policy inline (optional app)
        if CoinPolicyInline:
            instances.append(CoinPolicyInline(self.model, self.admin_site))

        return instances

    # ----- list columns helpers -----

    @admin.display(description="Status")
    def status_column(self, obj: Tournament):
        # Prefer model field if it exists/has value
        if hasattr(obj, "status") and getattr(obj, "status"):
            return obj.status
        # Else infer from dates
        from django.utils import timezone
        now = timezone.now()
        if getattr(obj, "start_at", None) and getattr(obj, "end_at", None):
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

    # ----- actions (as methods on the class) -----

    @admin.action(description="Generate bracket (single-elimination)")
    def action_generate_bracket(self, request, queryset):
        done = 0
        for t in queryset:
            try:
                from apps.corelib.brackets import generate_bracket  # import lazily
                generate_bracket(t)
                done += 1
            except Exception as e:
                self.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
        self.message_user(request, f"Generated bracket for {done} tournament(s).", level=messages.SUCCESS)

    @admin.action(description="Lock bracket (prevent edits)")
    def action_lock_bracket(self, request, queryset):
        updated = 0
        for t in queryset:
            b = getattr(t, "bracket", None)
            if b:
                try:
                    b.is_locked = True
                    b.save(update_fields=["is_locked"])
                    updated += 1
                except Exception as e:
                    self.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
        self.message_user(request, f"Locked {updated} bracket(s).", level=messages.SUCCESS)

    @admin.action(description="Award Coins: Participation (verified regs)")
    def action_award_participation(self, request, queryset):
        if not coin_services or not DeltaCrownTransaction:
            self.message_user(request, "Economy app not installed.", level=messages.WARNING)
            return
        count = 0
        for t in queryset:
            regs = t.registration_set.all().select_related("payment_verification")
            for r in regs:
                pv = getattr(r, "payment_verification", None)
                if pv and getattr(pv, "status", "") == "verified":
                    tx = coin_services.award_participation_for_registration(r)
                    if tx:
                        count += 1 if isinstance(tx, DeltaCrownTransaction) else len(tx)
        self.message_user(request, f"Awarded participation coins to {count} wallet(s).", level=messages.SUCCESS)

    @admin.action(description="Award Coins: Placements (final + semis)")
    def action_award_placements(self, request, queryset):
        if not coin_services:
            self.message_user(request, "Economy app not installed.", level=messages.WARNING)
            return
        total = 0
        for t in queryset:
            try:
                awards = coin_services.award_placements(t)
                total += len(awards)
            except Exception as e:
                self.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
        self.message_user(request, f"Created {total} placement transaction(s).", level=messages.SUCCESS)

    actions = (
        "action_generate_bracket",
        "action_lock_bracket",
        "action_award_participation",
        "action_award_placements",
    )
