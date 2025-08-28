from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from .models import Tournament, Registration, Bracket, Match
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig

# --- Inlines: show exactly one game config per tournament ---
class EfootballConfigInline(admin.StackedInline):
    model = EfootballConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"

class ValorantConfigInline(admin.StackedInline):
    model = ValorantConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"

# Optional extra filter for “has entry fee”
class HasEntryFeeFilter(admin.SimpleListFilter):
    title = "Has entry fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(entry_fee_bdt__isnull=True).exclude(entry_fee_bdt=0)
        if val == "no":
            return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
        return queryset

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_at", "entry_fee_bdt")
    list_filter = ("status", HasEntryFeeFilter)
    search_fields = ("name", "slug")
    inlines = []  # inserted dynamically below

    def get_inlines(self, request, obj=None):
        """
        Dynamically attach exactly one inline based on which config exists.
        Enforces separation of concerns (only one game config per tournament).
        """
        if not obj:
            return []  # during "Add", no inline yet
        econf = getattr(obj, "efootball_config", None)
        vconf = getattr(obj, "valorant_config", None)
        if econf and vconf:
            self.message_user(
                request,
                "Warning: both eFootball and Valorant configs exist. Please keep only one.",
                level=messages.WARNING,
            )
            return [EfootballConfigInline, ValorantConfigInline]
        if econf:
            return [EfootballConfigInline]
        if vconf:
            return [ValorantConfigInline]
        # none exist yet—show both options; once created, only one should remain
        return [EfootballConfigInline, ValorantConfigInline]

# --- Registration admin with 'Verify payment' action ---
@admin.action(description="Verify payment for selected registrations")
def action_verify_payment(modeladmin, request, queryset):
    count = queryset.update(payment_status="verified", status="CONFIRMED")
    modeladmin.message_user(request, f"Verified payments for {count} registration(s).")

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user", "team", "payment_status", "status", "created_at")
    list_filter = ("payment_status", "status", "tournament")
    search_fields = ("payment_reference",)
    actions = [action_verify_payment]

# --- Tournament admin actions: Generate / Lock bracket ---
@admin.action(description="Generate bracket (idempotent)")
def action_generate_bracket(modeladmin, request, queryset):
    from apps.corelib.brackets import generate_bracket  # implemented as stub now; full in Part 6
    done = 0
    for t in queryset:
        try:
            generate_bracket(t)
            done += 1
        except Exception as e:
            modeladmin.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
    modeladmin.message_user(request, f"Generated/updated bracket for {done} tournament(s).")

@admin.action(description="Lock bracket")
def action_lock_bracket(modeladmin, request, queryset):
    for t in queryset:
        b = getattr(t, "bracket", None)
        if not b:
            b = Bracket.objects.create(tournament=t, is_locked=True)
        else:
            b.is_locked = True
            b.save(update_fields=["is_locked"])
    modeladmin.message_user(request, f"Locked {queryset.count()} bracket(s).")

# inject actions onto TournamentAdmin
TournamentAdmin.actions = [action_generate_bracket, action_lock_bracket]

# --- Match admin with “Set Winner” utility ---
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament", "round_no",
        "participant_a", "participant_b",
        "score_a", "score_b",
        "winner", "set_winner_link",
        "state",
    )
    list_filter = ("tournament", "round_no", "state")
    search_fields = ("participant_a", "participant_b")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:match_id>/set_winner/<str:who>/",
                 self.admin_site.admin_view(self.set_winner_view),
                 name="match_set_winner"),
        ]
        return custom + urls

    def set_winner_link(self, obj):
        if obj.winner:
            return obj.winner
        a = f'<a href="{obj.id}/set_winner/a/">Set {obj.participant_a}</a>'
        b = f'<a href="{obj.id}/set_winner/b/">Set {obj.participant_b}</a>'
        return format_html(f"{a} | {b}")
    set_winner_link.short_description = "Resolve"

    def set_winner_view(self, request, match_id, who):
        from apps.corelib.brackets import admin_set_winner  # stub now; finalize in Part 6
        m = Match.objects.get(id=match_id)
        try:
            admin_set_winner(m, who=who)
            self.message_user(request, "Winner set and progression applied.")
        except Exception as e:
            self.message_user(request, str(e), level=messages.ERROR)
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))
