# apps/teams/admin/teams.py
from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.admin.sites import AlreadyRegistered
from django.db.models import QuerySet
from django import forms

from ..models import Team, TeamMembership, TeamInvite
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
# Team Form with Custom Widgets
# -----------------------
class TeamAdminForm(forms.ModelForm):
    """Custom form for Team admin with points calculator widgets."""
    
    class Meta:
        model = Team
        fields = '__all__'
        widgets = {
            'total_points': forms.NumberInput(attrs={'readonly': True}),
            'adjust_points': forms.NumberInput(attrs={
                'placeholder': 'Enter points to add or subtract'
            }),
        }

# -----------------------
# Team admin (single source of truth)
# -----------------------
class TeamAdmin(admin.ModelAdmin):
    """
    Enhanced Team admin with points management and responsive design.
    """
    form = TeamAdminForm
    list_display = ("id", "name", "tag", "game_display", "total_points_display", "captain_display", "members_count")
    list_filter = ("game", "is_verified", "is_featured", "is_active")
    search_fields = ("name", "tag", "region")
    inlines = [TeamMembershipInline, TeamInviteInline]
    actions = ["action_make_preset_from_team", "recalculate_points"]
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "tag", "description", "logo", "game", "region"),
            "classes": ("wide",)
        }),
        ("Team Achievement Points", {
            "fields": ("total_points", "adjust_points"),
            "classes": ("wide", "team-points-section"),
            "description": "Manage team ranking points. Total Points is automatically calculated. Use Adjust Points with Add/Minus buttons to manually modify points."
        }),
        ("Team Management", {
            "fields": ("captain", "is_active", "allow_join_requests"),
            "classes": ("collapse",)
        }),
        ("Social & Media", {
            "fields": ("banner_image", "roster_image", "twitter", "instagram", "discord", "youtube", "twitch", "linktree"),
            "classes": ("collapse", "wide")
        }),
        ("Team Settings", {
            "fields": ("is_verified", "is_featured", "is_public", "show_statistics", "allow_posts", "allow_followers", "posts_require_approval"),
            "classes": ("collapse",)
        }),
        ("Advanced", {
            "fields": ("slug", "primary_game", "banner", "created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        # Keep it simple and portable across schema variants.
        return super().get_queryset(request)

    def members_count(self, obj: Team) -> int:
        return TeamMembership.objects.filter(team=obj).count()
    members_count.short_description = "Members"

    def game_display(self, obj: Team) -> str:
        # 'game' may be absent on some legacy rows; render blank gracefully.
        game = getattr(obj, "game", "") or ""
        if game:
            # Use centralized game assets system
            from apps.common.game_assets import get_game_data
            try:
                game_data = get_game_data(game.upper())
                if game_data:
                    return f"� {game_data['display_name']}"
            except (KeyError, AttributeError):
                pass
            return f"🎮 {game.title()}"
        return ""
    game_display.short_description = "Game"

    def captain_display(self, obj: Team) -> str:
        cap = getattr(obj, "captain", None)
        try:
            user = getattr(cap, "user", None)
            return getattr(user, "username", None) or (str(cap) if cap else "")
        except Exception:
            return str(cap) if cap else ""
    captain_display.short_description = "Captain"
    
    def total_points_display(self, obj: Team) -> str:
        """Display total points with formatting."""
        total = getattr(obj, "total_points", 0)
        if total >= 1000:
            return f"{total:,.0f} pts"
        return f"{total} pts"
    total_points_display.short_description = "Points"
    total_points_display.admin_order_field = "total_points"


    
    @admin.action(description="Recalculate team points")
    def recalculate_points(self, request, queryset: QuerySet[Team]):
        """Recalculate points for selected teams based on achievements."""
        updated_count = 0
        
        for team in queryset:
            try:
                # Get team achievements and calculate points
                # This is a placeholder - you would integrate with your ranking system
                old_total = getattr(team, 'total_points', 0)
                
                # For now, just ensure adjust_points is applied to total_points
                adjust = getattr(team, 'adjust_points', 0)
                new_total = max(0, adjust)  # Base points + adjustments
                
                if old_total != new_total:
                    team.total_points = new_total
                    team.save(update_fields=['total_points'])
                    updated_count += 1
                    
            except Exception as e:
                self.message_user(
                    request,
                    f"Error updating {team.name}: {str(e)}",
                    level=messages.ERROR
                )
                continue
        
        if updated_count > 0:
            self.message_user(
                request,
                f"Successfully recalculated points for {updated_count} team(s).",
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "No teams required point updates.",
                level=messages.INFO
            )

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
