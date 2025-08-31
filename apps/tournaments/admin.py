from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from .models import Tournament, Registration, Bracket, Match, TournamentSettings
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig
from .services.scheduling import auto_schedule_matches, clear_schedule

from django.template.response import TemplateResponse
from django.urls import path
from .services.analytics import tournament_stats
from apps.notifications.models import Notification
from django.http import HttpResponse
import csv

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
        ("Payments (Manual)", {
            "fields": (
                "bkash_receive_number",
                "nagad_receive_number",
                "rocket_receive_number",
                "bank_instructions",
            )
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
    list_display = ("name", "status", "starts", "ends", "slots", "fee", "pool", "analytics_link")
    list_filter = ("status", HasEntryFeeFilter)
    search_fields = ("name", "slug")

    def analytics_link(self, obj):
        return format_html('<a href="{}">Analytics</a>', f"./{obj.pk}/analytics/")
    analytics_link.short_description = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:pk>/analytics/", self.admin_site.admin_view(self.analytics_view), name="tournament_analytics"),
        ]
        return custom + urls

    def analytics_view(self, request, pk):
        obj = self.get_object(request, pk)
        if not self.has_view_permission(request, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        stats = tournament_stats(obj)
        ctx = {
            **self.admin_site.each_context(request),
            "title": f"Analytics — {obj.name}",
            "tournament": obj,
            "stats": stats,
        }
        return TemplateResponse(request, "admin/tournaments/tournament/analytics.html", ctx)


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


def _safe_message(modeladmin, request, msg, level=None):
    try:
        modeladmin.message_user(request, msg, level=level)
    except Exception:
        # In tests (SimpleNamespace request) or without MessageMiddleware, ignore
        pass


# ---- Registration admin actions: Verify / Reject ----
@admin.action(description="Verify payment for selected registrations")
def action_verify_payment(modeladmin, request, queryset):
    from apps.notifications.services import notify

    now = timezone.now()
    updated = 0
    for r in queryset.select_related("tournament", "user__user", "team__captain__user"):
        if r.payment_status == "verified":
            continue
        r.payment_status = "verified"
        r.payment_verified_at = now
        r.payment_verified_by = getattr(request, "user", None)
        # Auto-confirm if not already confirmed
        if r.status != "CONFIRMED":
            r.status = "CONFIRMED"
        r.save(update_fields=["payment_status", "payment_verified_at", "payment_verified_by", "status"])

        # Notify solo user or team captain
        recipient = r.user or (getattr(r.team, "captain", None))
        if recipient:
            notify(
                recipient, Notification.Type.PAYMENT_VERIFIED,
                title=f"Payment verified – {r.tournament.name}",
                body="Your payment was verified and your spot is confirmed.",
                url=f"/t/{r.tournament.slug}/",
                tournament=r.tournament,
                email_subject=f"[DeltaCrown] Payment verified – {r.tournament.name}",
                email_template="payment_verified",
                email_ctx={"t": r.tournament, "reg": r},
            )
        updated += 1

    _safe_message(modeladmin, request, f"Verified payments for {updated} registration(s).")

@admin.action(description="Reject payment for selected registrations")
def action_reject_payment(modeladmin, request, queryset):
    from apps.notifications.services import notify

    updated = 0
    for r in queryset.select_related("tournament", "user__user", "team__captain__user"):
        r.payment_status = "rejected"
        # keep status as-is (still PENDING) so user can fix and resubmit
        r.save(update_fields=["payment_status"])

        recipient = r.user or (getattr(r.team, "captain", None))
        if recipient:
            notify(
                recipient, Notification.Type.PAYMENT_REJECTED,
                title=f"Payment rejected – {r.tournament.name}",
                body="We couldn't verify your payment. Please check the reference and try again.",
                url=f"/t/{r.tournament.slug}/",
                tournament=r.tournament,
                email_subject=f"[DeltaCrown] Payment rejected – {r.tournament.name}",
                email_template="payment_rejected",
                email_ctx={"t": r.tournament, "reg": r},
            )
        updated += 1

    _safe_message(modeladmin, request, f"Rejected payments for {updated} registration(s).")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "tournament", "user", "team",
        "payment_method", "payment_sender", "payment_reference",
        "payment_status", "status",
        "payment_verified_by", "payment_verified_at",
        "created_at",
    )
    list_filter = ("payment_status", "payment_method", "status", "tournament")
    search_fields = ("payment_reference", "payment_sender")
    actions = [action_verify_payment, action_reject_payment]


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



def export_tournaments_csv(modeladmin, request, queryset):
    """
    Export selected Tournaments as CSV.
    Fields chosen to be stable and useful for ops/review.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"tournaments-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "name",
        "slug",
        "status",
        "slot_size",
        "reg_open_at",
        "reg_close_at",
        "start_at",
        "end_at",
    ])

    for t in queryset.order_by("id"):
        writer.writerow([
            t.id,
            t.name,
            t.slug,
            getattr(t, "status", ""),
            getattr(t, "slot_size", ""),
            getattr(t, "reg_open_at", "") or "",
            getattr(t, "reg_close_at", "") or "",
            getattr(t, "start_at", "") or "",
            getattr(t, "end_at", "") or "",
        ])

    return response


export_tournaments_csv.short_description = "Export selected tournaments to CSV"