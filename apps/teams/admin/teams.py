# apps/teams/admin/teams.py
from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.admin.sites import AlreadyRegistered
from django.db.models import QuerySet

from ..models import Team, TeamMembership, TeamInvite
from .exports import export_teams_csv
from .inlines import TeamMembershipInline, TeamInviteInline

# Optional imports: presets
_HAS_PRESETS = False
try:
    from ..models import (
        EfootballTeamPreset,
        ValorantTeamPreset,
        ValorantPlayerPreset,
    )
    _HAS_PRESETS = True
except Exception:
    # Admin must not crash if presets aren’t present
    pass


# -----------------------
# Helpers
# -----------------------
def _safe_register(model, admin_class) -> None:
    """Register a model admin if it isn't already registered."""
    try:
        admin.site.register(model, admin_class)
    except AlreadyRegistered:
        # Idempotent: ignore if registered elsewhere (e.g., on reload)
        pass
    except Exception:
        # Never block admin startup
        pass


# -----------------------
# Team admin (single source of truth)
# -----------------------
class TeamAdmin(admin.ModelAdmin):
    """
    Safe Team admin that avoids referencing fields that may not exist
    across legacy states and development branches.
    """
    list_display = ("id", "name", "tag", "game_display", "captain_display", "members_count")
    search_fields = ("name", "tag")
    inlines = [TeamMembershipInline, TeamInviteInline]
    actions = ["export_as_csv", "action_make_preset_from_team"]

    def get_queryset(self, request):
        # Keep it simple and portable across schema variants.
        return super().get_queryset(request)

    def members_count(self, obj: Team) -> int:
        return TeamMembership.objects.filter(team=obj).count()
    members_count.short_description = "Members"

    def game_display(self, obj: Team) -> str:
        # 'game' may be absent on some legacy rows; render blank gracefully.
        return getattr(obj, "game", "") or ""
    game_display.short_description = "Game"

    def captain_display(self, obj: Team) -> str:
        cap = getattr(obj, "captain", None)
        try:
            user = getattr(cap, "user", None)
            return getattr(user, "username", None) or (str(cap) if cap else "")
        except Exception:
            return str(cap) if cap else ""
    captain_display.short_description = "Captain"

    def export_as_csv(self, request, queryset: QuerySet[Team]):
        return export_teams_csv(self, request, queryset)

    # ---------- NEW: Create/Update Preset from Team ----------
    @admin.action(description="Create/Update Preset from Team")
    def action_make_preset_from_team(self, request, queryset: QuerySet[Team]):
        if not _HAS_PRESETS:
            self.message_user(
                request, "Presets models are not available.", level=messages.WARNING
            )
            return

        updated = 0
        errors = 0
        for team in queryset:
            try:
                owner_profile = getattr(team, "captain", None)
                if not owner_profile:
                    # fallback: first ACTIVE member as owner
                    mem = (
                        TeamMembership.objects
                        .filter(team=team, status="ACTIVE")
                        .select_related("profile")
                        .first()
                    )
                    owner_profile = getattr(mem, "profile", None)

                if not owner_profile:
                    continue  # skip teams with no owner we can attach to

                game = (getattr(team, "game", "") or "").lower()
                if game == "valorant":
                    vp, _ = ValorantTeamPreset.objects.get_or_create(
                        profile=owner_profile, name="My Valorant Team"
                    )
                    vp.team_name = getattr(team, "name", "") or ""
                    vp.team_tag = getattr(team, "tag", "") or ""
                    vp.region = getattr(team, "region", "") or ""
                    vp.save()
                    updated += 1
                elif game == "efootball":
                    ep, _ = EfootballTeamPreset.objects.get_or_create(
                        profile=owner_profile, name="My eFootball Team"
                    )
                    ep.team_name = getattr(team, "name", "") or ""
                    # logo snapshot only if you store it here; harmless if None
                    ep.team_logo = getattr(team, "logo", None)
                    ep.save()
                    updated += 1
                else:
                    # Unknown/blank game — ignore silently
                    continue
            except Exception:
                errors += 1
                continue

        if updated:
            self.message_user(
                request, f"Preset created/updated for {updated} team(s).", level=messages.SUCCESS
            )
        if errors:
            self.message_user(
                request, f"Skipped {errors} team(s) due to errors.", level=messages.WARNING
            )


_safe_register(Team, TeamAdmin)


# -----------------------
# TeamMembership admin
# -----------------------
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "profile", "role", "status", "joined_at")
    search_fields = ("team__name", "profile__user__username", "profile__user__email")
    list_filter = ("role", "status")
    autocomplete_fields = ("team", "profile")
    readonly_fields = ("joined_at",)

    @admin.action(description="Promote to Captain")
    def promote_to_captain(self, request, queryset: QuerySet):
        count = 0
        for mem in queryset.select_related("team", "profile"):
            try:
                promote = getattr(mem, "promote_to_captain", None)
                if callable(promote):
                    promote()
                    count += 1
            except Exception:
                continue
        self.message_user(request, f"Promoted {count} member(s) to Captain.", level=messages.SUCCESS)


_safe_register(TeamMembership, TeamMembershipAdmin)


# -----------------------
# TeamInvite admin
# -----------------------
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ("team", "inviter", "invited_user", "invited_email", "role", "status", "expires_at", "created_at")
    list_filter = ("status", "role", "team")
    search_fields = ("team__name", "invited_email", "invited_user__user__email", "token")
    autocomplete_fields = ("team", "inviter", "invited_user")
    readonly_fields = ("token", "created_at")


_safe_register(TeamInvite, TeamInviteAdmin)


# -----------------------
# Presets admin (optional, only if models are available)
# -----------------------
if _HAS_PRESETS:
    class EfootballTeamPresetAdmin(admin.ModelAdmin):
        list_display = ("id", "profile", "name", "team_name", "created_at")
        search_fields = ("name", "team_name", "profile__user__username")
        list_filter = ("created_at",)

    class ValorantPlayerPresetInline(admin.TabularInline):
        model = ValorantPlayerPreset
        extra = 1

    class ValorantTeamPresetAdmin(admin.ModelAdmin):
        list_display = ("id", "profile", "name", "team_name", "team_tag", "created_at")
        search_fields = ("name", "team_name", "team_tag", "profile__user__username")
        inlines = [ValorantPlayerPresetInline]

    _safe_register(EfootballTeamPreset, EfootballTeamPresetAdmin)
    _safe_register(ValorantTeamPreset, ValorantTeamPresetAdmin)
