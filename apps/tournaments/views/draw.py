"""
Draw Director & Public Spectator Views

These views serve the standalone draw ceremony pages:
1. GroupDrawDirectorView — Organizer-only draw control panel
2. GroupDrawPublicView — Public spectator view for live draw broadcast
3. smart_group_presets — AJAX utility returning recommended group formats
"""
import json
import logging
import math

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.models.group import Group, GroupStage

logger = logging.getLogger(__name__)


def _mint_ws_token(user):
    """
    Generate a short-lived JWT access token for WebSocket auth.

    The browser's native WebSocket API does not support custom headers
    (Authorization: Bearer), so the token is appended as a ?token= query
    parameter.  The JWTAuthMiddleware in the ASGI layer parses it.
    """
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        return str(token)
    except Exception:
        logger.warning("Could not mint WS JWT for user %s", user, exc_info=True)
        return ""


class GroupDrawDirectorView(LoginRequiredMixin, TemplateView):
    """
    Organizer's Group Draw Director panel.
    URL: /tournaments/<slug>/draw/director/
    Requires login + organizer/staff permission.
    """
    template_name = "tournaments/draw_director.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        tournament = get_object_or_404(
            Tournament.objects.select_related("organizer"),
            slug=slug,
        )
        # Permission check: organizer or staff only
        user = self.request.user
        if tournament.organizer_id != user.id and not user.is_staff:
            raise Http404("Only the tournament organizer can access the Draw Director.")

        ctx["tournament"] = tournament
        ctx["tournament_id"] = tournament.id
        ctx["ws_url"] = f"/ws/tournament/{tournament.id}/group-draw/"
        ctx["ws_auth_token"] = _mint_ws_token(user)

        # ── Game branding for dynamic wizard theming ──
        game_theme = {"slug": "", "primary_color": "#00ffaa", "secondary_color": "#1e1b4b", "accent_color": "", "banner_url": ""}
        if tournament.game:
            g = tournament.game
            game_theme["slug"] = g.slug or ""
            game_theme["primary_color"] = g.primary_color or "#00ffaa"
            game_theme["secondary_color"] = g.secondary_color or "#1e1b4b"
            game_theme["accent_color"] = g.accent_color or ""
            if g.banner:
                try:
                    game_theme["banner_url"] = g.banner.url
                except Exception:
                    pass
        ctx["game_theme_json"] = json.dumps(game_theme)

        # ── Pre-load groups for empty-state grid ──
        groups = Group.objects.filter(
            tournament=tournament, is_deleted=False,
        ).order_by("display_order", "name")
        groups_data = []
        for g in groups:
            letter = g.name.split()[-1] if " " in g.name else g.name
            groups_data.append({
                "name": letter,
                "max_participants": g.max_participants,
            })
        ctx["groups_json"] = json.dumps(groups_data)

        # ── Pre-load confirmed participants for queue ──
        regs = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).select_related("user", "user__profile")
        participants = []
        for reg in regs:
            name = ""
            uid = None
            avatar_url = ""
            if reg.user:
                name = reg.user.username
                uid = reg.user.id
                try:
                    profile = getattr(reg.user, 'profile', None)
                    if profile:
                        avatar_url = profile.get_avatar_url() or ""
                except Exception:
                    pass
            elif reg.team_id:
                try:
                    from apps.organizations.models import Team
                    team = Team.objects.get(id=reg.team_id)
                    name = team.name
                    logo = team.get_effective_logo_url()
                    if hasattr(logo, 'url'):
                        avatar_url = logo.url
                    elif isinstance(logo, str):
                        avatar_url = logo
                except Exception:
                    name = f"Team {reg.team_id}"
                uid = reg.team_id
            else:
                name = f"Registration #{reg.registration_number}"
                uid = reg.id
            participants.append({
                "registration_id": reg.id,
                "user_id": uid,
                "name": name,
                "display_name": name,
                "avatar_url": avatar_url,
            })
        ctx["participants_json"] = json.dumps(participants)
        ctx["participant_count"] = len(participants)
        ctx["group_count"] = len(groups_data)

        # ── Tiebreaker info for config modal ──
        tiebreaker_rules = ["Points", "Head-to-Head", "Goal Difference", "Goals For"]
        try:
            gs = GroupStage.objects.filter(tournament=tournament).first()
            if gs and gs.config and gs.config.get("tiebreaker_rules"):
                tb_raw = gs.config["tiebreaker_rules"]
                tiebreaker_rules = [
                    r.replace("_", " ").title() for r in tb_raw
                ]
        except Exception:
            pass
        ctx["tiebreaker_rules_json"] = json.dumps(tiebreaker_rules)

        # ── Existing group architecture for pre-fill ──
        arch = {"num_groups": 0, "group_size": 4, "advancement_count": 2}
        if groups_data:
            arch["num_groups"] = len(groups_data)
            arch["group_size"] = groups_data[0]["max_participants"] if groups_data else 4
        try:
            gs_obj = GroupStage.objects.filter(tournament=tournament).first()
            if gs_obj:
                arch["advancement_count"] = gs_obj.advancement_count_per_group
        except Exception:
            pass
        ctx["group_arch_json"] = json.dumps(arch)

        return ctx


class GroupDrawPublicView(TemplateView):
    """
    Public spectator view for the live group draw broadcast.
    URL: /tournaments/<slug>/draw/live/
    No login required — anyone can watch the draw.
    """
    template_name = "tournaments/draw_spectator.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        tournament = get_object_or_404(Tournament, slug=slug)
        ctx["tournament"] = tournament
        ctx["tournament_id"] = tournament.id
        ctx["ws_url"] = f"/ws/tournament/{tournament.id}/group-draw/"
        return ctx


# ================================================================== #
#  Smart Group Presets Utility
# ================================================================== #

def compute_group_presets(player_count):
    """Return 2-3 mathematically sound group configurations for a given player count.

    Each preset is a dict: {label, num_groups, group_size, advancement_count, description}
    """
    if player_count < 4:
        return []

    presets = []

    # ── Champions League style: 8 groups of 4, top 2 advance ──
    if player_count >= 16 and player_count % 4 == 0:
        n = player_count // 4
        presets.append({
            "label": f"Champions League ({n}×4)",
            "num_groups": n,
            "group_size": 4,
            "advancement_count": 2,
            "description": f"{n} groups of 4, top 2 advance → {n * 2} qualify",
        })

    # ── Balanced 3-per-group ──
    if player_count >= 9 and player_count % 3 == 0:
        n = player_count // 3
        adv = min(2, 2)  # top 2 from groups of 3
        presets.append({
            "label": f"Triple Groups ({n}×3)",
            "num_groups": n,
            "group_size": 3,
            "advancement_count": min(2, 2),
            "description": f"{n} groups of 3, top {adv} advance → {n * adv} qualify",
        })

    # ── Larger groups: 5 or 6 per group ──
    for sz in (6, 5):
        if player_count >= sz * 2 and player_count % sz == 0:
            n = player_count // sz
            adv = 2 if sz <= 5 else 3
            if not any(p["group_size"] == sz for p in presets):
                presets.append({
                    "label": f"Deep Groups ({n}×{sz})",
                    "num_groups": n,
                    "group_size": sz,
                    "advancement_count": adv,
                    "description": f"{n} groups of {sz}, top {adv} advance → {n * adv} qualify",
                })

    # ── Fallback: closest power-of-2 friendly format ──
    if len(presets) < 2:
        # Try groups of 4 with partial fill
        g4 = math.ceil(player_count / 4)
        if g4 >= 2:
            presets.append({
                "label": f"Standard ({g4}×4)",
                "num_groups": g4,
                "group_size": 4,
                "advancement_count": 2,
                "description": f"{g4} groups of 4 (some may have 3), top 2 advance → {g4 * 2} qualify",
            })

    # ── Two-group split for small counts ──
    if player_count <= 12 and player_count >= 4:
        sz = math.ceil(player_count / 2)
        if sz >= 2 and not any(p["num_groups"] == 2 and p["group_size"] == sz for p in presets):
            adv = max(1, sz // 2)
            presets.append({
                "label": f"Dual Groups (2×{sz})",
                "num_groups": 2,
                "group_size": sz,
                "advancement_count": adv,
                "description": f"2 groups of {sz}, top {adv} advance → {2 * adv} qualify",
            })

    # Limit to 3 and deduplicate
    seen = set()
    unique = []
    for p in presets:
        key = (p["num_groups"], p["group_size"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique[:3]


def smart_group_presets(request, slug):
    """AJAX endpoint returning recommended group formats for a tournament."""
    tournament = get_object_or_404(Tournament, slug=slug)
    count = Registration.objects.filter(
        tournament=tournament,
        status=Registration.CONFIRMED,
        is_deleted=False,
    ).count()
    presets = compute_group_presets(count)
    return JsonResponse({"player_count": count, "presets": presets})
