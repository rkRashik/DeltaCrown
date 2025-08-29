from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from .models import Tournament, Registration, Bracket, Match, TournamentSettings
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig
from .services.scheduling import auto_schedule_matches, clear_schedule


# --- Inlines: show exactly one game config per tournament (plus settings) ---
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


class TournamentSettingsInline(admin.StackedInline):
    model = TournamentSettings
    can_delete = False
    extra = 0
    fieldsets = (
        ("Core Toggles", {
            "fields": (
                "invite_only", "auto_check_in", "allow_substitutes",
                "custom_format_enabled", "automatic_scheduling_enabled",
            )
        }),
        ("Visibility & Region", {
            "fields": (
                "bracket_visibility", "region_lock",
                "check_in_open_mins", "check_in_close_mins",
            ),
        }),
        ("Rules & Media", {
            "fields": (
                "rules_pdf", "facebook_stream_url",
                "youtube_stream_url", "discord_link",
            ),
        }),
    )


# Optional extra filter for “has entry fee”
class HasEntryFeeFilter(admin.SimpleListFilter):
    title = "Has entry fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        val = self.value()
        # Try common fee field names: entry_fee_bdt (your code), entry_fee, fee
        if val == "yes":
            return (
                queryset.exclude(entry_fee_bdt__isnull=True).exclude(entry_fee_bdt=0)
                if "entry_fee_bdt" in [f.name for f in Tournament._meta.get_fields()]
                else queryset.exclude(entry_fee__isnull=True).exclude(entry_fee=0)
            )
        if val == "no":
            if "entry_fee_bdt" in [f.name for f in Tournament._meta.get_fields()]:
                return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
            return queryset.filter(entry_fee__isnull=True) | queryset.filter(entry_fee=0)
        return queryset


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    NOTE:
    Your model uses fields like start_at / end_at / slot_size / entry_fee_bdt.
    We expose safe accessors (methods) instead of hard-coding missing names like start_date/end_date.
    """
    list_display = ("name", "status", "starts", "ends", "slots", "fee", "pool")
    list_filter = ("status", HasEntryFeeFilter)
    search_fields = ("name", "slug")

    # We dynamically include settings + exactly one (or both if none) game config inline(s)
    def get_inlines(self, request, obj=None):
        if not obj:
            # On the "Add tournament" page, avoid inlines (parent not saved yet)
            return []
        inlines = [TournamentSettingsInline]

        econf = getattr(obj, "efootball_config", None)
        vconf = getattr(obj, "valorant_config", None)

        if econf and vconf:
            self.message_user(
                request,
                "Warning: both eFootball and Valorant configs exist. Please keep only one.",
                level=messages.WARNING,
            )
            inlines += [EfootballConfigInline, ValorantConfigInline]
            return inlines

        if econf:
            inlines.append(EfootballConfigInline)
            return inlines

        if vconf:
            inlines.append(ValorantConfigInline)
            return inlines

        # If none exists yet, show both so the admin can choose one to create.
        inlines += [EfootballConfigInline, ValorantConfigInline]
        return inlines

    # ---- Safe accessors for list_display ----
    @admin.display(ordering="start_at", description="Start")
    def starts(self, obj):
        # try start_at then start_date
        return getattr(obj, "start_at", None) or getattr(obj, "start_date", None) or "—"

    @admin.display(ordering="end_at", description="End")
    def ends(self, obj):
        # try end_at then end_date
        return getattr(obj, "end_at", None) or getattr(obj, "end_date", None) or "—"

    @admin.display(description="Slots")
    def slots(self, obj):
        # try slot_size, then slots, then max_slots
        return (
            getattr(obj, "slot_size", None)
            or getattr(obj, "slots", None)
            or getattr(obj, "max_slots", None)
            or "—"
        )

    @admin.display(description="Entry Fee")
    def fee(self, obj):
        # common names: entry_fee_bdt, entry_fee, fee
        for name in ("entry_fee_bdt", "entry_fee", "fee"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"

    @admin.display(description="Prize Pool")
    def pool(self, obj):
        # common names: prize_pool_bdt, prize_pool, pool
        for name in ("prize_pool_bdt", "prize_pool", "pool"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"


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


# Inject actions onto TournamentAdmin
TournamentAdmin.actions = [action_generate_bracket, action_lock_bracket]


# --- Match admin with “Set Winner” utility ---
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament", "round_no", "position",
        "participant_a_name", "participant_b_name",
        "score_a", "score_b",
        "winner_name", "set_winner_link",
        "state",
    )
    list_filter = ("tournament", "round_no", "state")
    search_fields = (
        "tournament__name",
        "user_a__display_name", "user_b__display_name",
        "team_a__name", "team_a__tag",
        "team_b__name", "team_b__tag",
    )

    def participant_a_name(self, obj):
        if obj.is_solo_match:
            return obj.user_a.display_name if obj.user_a else "—"
        return obj.team_a.tag if obj.team_a else "—"
    participant_a_name.short_description = "Side A"

    def participant_b_name(self, obj):
        if obj.is_solo_match:
            return obj.user_b.display_name if obj.user_b else "—"
        return obj.team_b.tag if obj.team_b else "—"
    participant_b_name.short_description = "Side B"

    def winner_name(self, obj):
        if obj.winner_user:
            return obj.winner_user.display_name
        if obj.winner_team:
            return obj.winner_team.tag
        return ""
    winner_name.short_description = "Winner"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:match_id>/set_winner/<str:who>/",
                self.admin_site.admin_view(self.set_winner_view),
                name="match_set_winner",
            ),
        ]
        return custom + urls

    def set_winner_link(self, obj):
        # If already has a winner, no links
        if obj.winner_user_id or obj.winner_team_id:
            return "—"
        links = []
        if obj.user_a_id or obj.team_a_id:
            label_a = obj.user_a.display_name if obj.is_solo_match else (obj.team_a.tag if obj.team_a else "A")
            links.append(f'<a href="{obj.id}/set_winner/a/">Set {label_a}</a>')
        if obj.user_b_id or obj.team_b_id:
            label_b = obj.user_b.display_name if obj.is_solo_match else (obj.team_b.tag if obj.team_b else "B")
            links.append(f'<a href="{obj.id}/set_winner/b/">Set {label_b}</a>')
        return format_html(" | ".join(links))
    set_winner_link.short_description = "Resolve"

    def set_winner_view(self, request, match_id, who):
        from apps.corelib.brackets import admin_set_winner
        m = Match.objects.get(id=match_id)
        try:
            admin_set_winner(m, who=who)
            self.message_user(request, "Winner set and progression applied.")
        except Exception as e:
            self.message_user(request, str(e), level=messages.ERROR)
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@admin.action(description="Auto-schedule matches (by round)")
def action_auto_schedule(modeladmin, request, queryset):
    total = 0
    for t in queryset:
        try:
            count = auto_schedule_matches(t)
            total += count
        except Exception as e:
            modeladmin.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
    modeladmin.message_user(request, f"Scheduled {total} match(es) across {queryset.count()} tournament(s).")

@admin.action(description="Clear scheduled times")
def action_clear_schedule(modeladmin, request, queryset):
    total = 0
    for t in queryset:
        total += clear_schedule(t)
    modeladmin.message_user(request, f"Cleared start times for {total} match(es).")

# attach to TournamentAdmin (keep existing actions too)
TournamentAdmin.actions = list(set(getattr(TournamentAdmin, "actions", []) + [
    action_auto_schedule, action_clear_schedule
]))
