from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from ..models import Match
from ..services.scheduling import auto_schedule_matches, clear_schedule

from .utils import _path_exists, _safe_select_related, _safe_message
from .exports import export_tournaments_csv, export_disputes_csv, export_matches_csv
from .tournaments import TournamentAdmin, action_generate_bracket, action_lock_bracket
from .registrations import RegistrationAdmin, action_verify_payment, action_reject_payment


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

# Keep helpful labels for CSV actions
export_tournaments_csv.short_description = "Export selected tournaments to CSV"
export_disputes_csv.short_description = "Export selected disputes to CSV"  # type: ignore[attr-defined]
export_matches_csv.short_description = "Export selected matches to CSV"  # type: ignore[attr-defined]

# Conditionally attach to an existing Match admin or register a minimal one
MatchModel = None
try:
    from ..models import Match as _MatchModel
    MatchModel = _MatchModel
except Exception:
    MatchModel = None

if MatchModel is not None:
    existing = admin.site._registry.get(MatchModel)
    if existing:
        existing.actions = list(set((existing.actions or []) + [export_matches_csv]))
    else:
        @admin.register(MatchModel)
        class _MatchAdmin(admin.ModelAdmin):
            list_display = ("id",)
            actions = [export_matches_csv]

# ---- Attach the action to any existing Dispute admin, or register one if missing ----
DisputeModel = None
try:
    from ..models import Dispute as _DisputeModel
    DisputeModel = _DisputeModel
except Exception:
    try:
        from ..models import MatchDispute as _DisputeModel
        DisputeModel = _DisputeModel
    except Exception:
        DisputeModel = None

if DisputeModel is not None:
    existing = admin.site._registry.get(DisputeModel)
    if existing:
        existing.actions = list(set((existing.actions or []) + [export_disputes_csv]))
    else:
        @admin.register(DisputeModel)
        class _DisputeAdmin(admin.ModelAdmin):
            list_display = ("id",)
            actions = [export_disputes_csv]
