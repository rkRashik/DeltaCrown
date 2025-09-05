# apps/tournaments/admin/matches.py
from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from ..models import Match


# Winner propagation helper (already in your codebase)
try:
    from apps.corelib.brackets import admin_set_winner
except Exception:  # pragma: no cover
    def admin_set_winner(*args, **kwargs):
        raise RuntimeError("Winner propagation helper not available")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """
    Match admin with quick winner controls, lock-aware safety, and N+1-safe list rendering.
    """
    list_display = (
        "tournament",
        "bracket_lock_badge",          # NEW: quick lock visibility
        "round_no",
        "position",
        "participant_a_name",
        "participant_b_name",
        "score_a",
        "score_b",
        "winner_name",
        "set_winner_link",
        "state",
    )
    list_filter = ("tournament", "round_no", "state")
    search_fields = (
        "tournament__name",
        "tournament__slug",
        "user_a__user__username",
        "user_b__user__username",
        "team_a__name",
        "team_b__name",
    )
    ordering = ("tournament", "round_no", "position")

    actions = ["action_set_winner_a", "action_set_winner_b"]

    # ------------ queryset & performance ------------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Pull common relations to avoid N+1 in list_display
        qs = qs.select_related(
            "tournament",
            "tournament__bracket",
            "user_a__user",
            "user_b__user",
            "team_a",
            "team_b",
            "winner_user__user",
            "winner_team",
        )
        return qs

    # ------------ lock-aware read-only safety ------------

    def _is_locked(self, obj: Match | None) -> bool:
        try:
            b = getattr(getattr(obj, "tournament", None), "bracket", None)
            return bool(getattr(b, "is_locked", False))
        except Exception:
            return False

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        # When locked, prevent editing scores and winners directly
        if obj and self._is_locked(obj):
            for name in ("score_a", "score_b", "winner_user", "winner_team"):
                if name not in ro:
                    ro.append(name)
        return tuple(ro)

    def has_change_permission(self, request, obj=None):
        # Keep change permission, but fields are read-only when locked.
        return super().has_change_permission(request, obj)

    # ------------ display helpers ------------

    @admin.display(description="Bracket")
    def bracket_lock_badge(self, obj: Match):
        locked = self._is_locked(obj)
        if locked:
            return format_html(
                '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;">Locked</span>'
            )
        return format_html(
            '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:9999px;">Unlocked</span>'
        )

    def participant_a_name(self, obj: Match):
        if obj.user_a_id:
            return (
                getattr(getattr(obj.user_a, "user", None), "username", None)
                or getattr(obj.user_a, "display_name", None)
                or f"User#{obj.user_a_id}"
            )
        if obj.team_a_id:
            return getattr(obj.team_a, "tag", None) or getattr(obj.team_a, "name", None) or f"Team#{obj.team_a_id}"
        return format_html('<span style="color:#999">—</span>')
    participant_a_name.short_description = "Side A"

    def participant_b_name(self, obj: Match):
        if obj.user_b_id:
            return (
                getattr(getattr(obj.user_b, "user", None), "username", None)
                or getattr(obj.user_b, "display_name", None)
                or f"User#{obj.user_b_id}"
            )
        if obj.team_b_id:
            return getattr(obj.team_b, "tag", None) or getattr(obj.team_b, "name", None) or f"Team#{obj.team_b_id}"
        return format_html('<span style="color:#999">—</span>')
    participant_b_name.short_description = "Side B"

    def winner_name(self, obj: Match):
        if obj.winner_user_id:
            return (
                getattr(getattr(obj.winner_user, "user", None), "username", None)
                or getattr(obj.winner_user, "display_name", None)
                or f"User#{obj.winner_user_id}"
            )
        if obj.winner_team_id:
            return getattr(obj.winner_team, "tag", None) or getattr(obj.winner_team, "name", None) or f"Team#{obj.winner_team_id}"
        return ""
    winner_name.short_description = "Winner"

    # ------------ per-row quick links ------------

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

    def set_winner_link(self, obj: Match):
        if obj.winner_user_id or obj.winner_team_id:
            return "—"
        # If locked, avoid offering buttons
        if self._is_locked(obj):
            return format_html('<span style="color:#999">Locked</span>')
        links = []
        if obj.user_a_id or obj.team_a_id:
            label_a = (
                getattr(getattr(obj.user_a, "user", None), "username", None)
                or getattr(obj.team_a, "tag", None)
                or "A"
            )
            url_a = reverse("admin:match_set_winner", kwargs={"match_id": obj.id, "who": "a"})
            links.append(f'<a href="{url_a}">Set {label_a}</a>')
        if obj.user_b_id or obj.team_b_id:
            label_b = (
                getattr(getattr(obj.user_b, "user", None), "username", None)
                or getattr(obj.team_b, "tag", None)
                or "B"
            )
            url_b = reverse("admin:match_set_winner", kwargs={"match_id": obj.id, "who": "b"})
            links.append(f'<a href="{url_b}">Set {label_b}</a>')
        return format_html(" | ".join(links))
    set_winner_link.short_description = "Resolve"

    def set_winner_view(self, request, match_id, who):
        m = Match.objects.get(id=match_id)
        if self._is_locked(m):
            self.message_user(request, "Bracket is locked; cannot set winner.", level=messages.WARNING)
            return redirect(request.META.get("HTTP_REFERER", "/admin/"))
        try:
            admin_set_winner(m, who=who)
            self.message_user(request, "Winner set and progression applied.")
        except Exception as e:
            self.message_user(request, str(e), level=messages.ERROR)
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    # ------------ bulk actions ------------

    @admin.action(description="Set winner → A")
    def action_set_winner_a(self, request, queryset):
        self._set_winner_bulk(request, queryset, "a")

    @admin.action(description="Set winner → B")
    def action_set_winner_b(self, request, queryset):
        self._set_winner_bulk(request, queryset, "b")

    def _set_winner_bulk(self, request, queryset, who: str):
        done = 0
        for m in queryset:
            if self._is_locked(m):
                self.message_user(request, f"Match #{m.id}: bracket locked; skipped.", level=messages.WARNING)
                continue
            try:
                admin_set_winner(m, who=who)
                done += 1
            except Exception as e:
                self.message_user(request, f"Match #{m.id}: {e}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Updated {done} match(es).", level=messages.SUCCESS)
