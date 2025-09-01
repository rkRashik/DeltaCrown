# apps/tournaments/admin/matches.py
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from ..models import Match
from ..services.scheduling import auto_schedule_matches, clear_schedule

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
        if getattr(obj, "winner_user", None):
            return obj.winner_user.display_name
        if getattr(obj, "winner_team", None):
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
