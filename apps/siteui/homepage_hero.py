"""Homepage hero context resolver.

Returns a dict that drives two homepage CTA areas:

  MAIN HERO (above the fold):
    eyebrow_primary / eyebrow_secondary
    subcopy
    primary_cta_label / primary_cta_url
    secondary_cta_label / secondary_cta_url
    hero_chips  (None → show generic guest trust bar)

  OUTRO / "YOUR LEGACY BEGINS HERE" (bottom CTA section):
    outro_primary_cta_label / outro_primary_cta_url
    outro_secondary_cta_label / outro_secondary_cta_url
    outro_subcopy

Called per-request from apps.siteui.views.home().  Never cached —
all DB checks use exists() / values_list() so they stay fast (~2–5 ms).

Priority ladder (highest → lowest):
  1. Guest                → Create account / Explore tournaments
  2. Incomplete profile   → Complete profile / Choose games
  3. Pending action       → Resolve action  / View operations
  4. Active match room    → View match room / My tournaments
  5. Active operations    → My operations  / Competitive hub
  6. No team              → Create a team  / Join tournaments
  7. Team manager         → Manage roster  / Find events
  8. Team, no active reg  → Find events    / Manage team
  9. Logged-in fallback   → My dashboard   / Enter arena
"""
from __future__ import annotations

from django.apps import apps as _apps


# ── Lazy model accessor ─────────────────────────────────────────────────────

def _m(app: str, model: str):
    """Return the model class or None — never raises."""
    try:
        return _apps.get_model(app, model)
    except Exception:
        return None


# ── Verified path constants ─────────────────────────────────────────────────
# Literal paths (not reverse()) to be import-safe and NoReverseMatch-immune.
# Verified against deltacrown/urls.py + each app's urls.py.

_U = {
    "signup":       "/account/signup/",           # account:signup
    "settings":     "/me/settings/",              # user_profile:settings
    "dashboard":    "/dashboard/",                 # dashboard:index
    "tournaments":  "/tournaments/",               # tournaments:list
    "open_tourn":   "/tournaments/?status=registration_open",
    "team_create":  "/teams/create/",              # organizations:team_create
    "teams":        "/teams/",                     # organizations:vnext_hub
    "arena":        "/arena/",                     # siteui:arena
    "competitive":  "/dashboard/competitive/",     # dashboard:competitive_hub
    "disputes":     "/dashboard/competitive/disputes/",  # dashboard:competitive_dispute_center
    "my_matches":   "/my/matches/",                # dashboard:my_matches
    "watch_live":   "/arena/",                     # watch-live routes to arena
}

# Management roles (verified against apps/organizations/choices.py).
# CAPTAIN is an alias for OWNER in that file; only OWNER and MANAGER grant
# tournament/roster management authority.
_MANAGER_ROLES = frozenset({"OWNER", "MANAGER"})

# Registration statuses that count as "active" participation.
# Verified against apps/tournaments/models/registration.py status constants.
_ACTIVE_REG_STATUSES = ("confirmed", "payment_submitted", "pending", "waitlisted")

# Match states that require immediate user action.
# Verified against apps/tournaments/models/match.py MatchState enum.
_PENDING_MATCH_STATES = ("check_in", "pending_result", "disputed")

# Match states that signal a live/upcoming competitive action.
_ACTIVE_MATCH_STATES = ("scheduled", "ready", "live")


# ── Public entry point ──────────────────────────────────────────────────────

def get_home_hero_context(user) -> dict:
    """Resolve hero + outro CTA state for *user* (authenticated or anonymous).

    Returns a single dict consumed by templates/home.html.
    Call once per request; do not call multiple times.
    """
    if not getattr(user, "is_authenticated", False):
        return _hero_guest()

    profile = getattr(user, "profile", None)

    if _is_profile_incomplete(user, profile):
        return _hero_onboarding(user)

    pending = _get_pending_action(user)
    if pending:
        return _hero_pending(user, pending)

    match_ctx = _get_active_match(user)
    if match_ctx:
        return _hero_active_match(user, match_ctx)

    if _has_ops(user):
        return _hero_ops(user)

    team_ctx = _get_team_info(user)
    if not team_ctx:
        return _hero_no_team(user)

    if team_ctx["is_manager"]:
        return _hero_team_manager(user, team_ctx)

    if _has_active_reg(user, team_ctx):
        return _hero_default(user)

    return _hero_team_ready(user, team_ctx)


# ── DB probe helpers ────────────────────────────────────────────────────────

def _is_profile_incomplete(user, profile) -> bool:
    """True when the player identity appears genuinely unset.

    NOT incomplete if any of these is present:
      - UserProfile.display_name (non-empty)
      - UserProfile.avatar
      - At least one GameProfile with status='ACTIVE'
         (GameProfile.STATUS_ACTIVE = 'ACTIVE', verified in models_main.py)
    """
    if profile is None:
        return True
    if bool((getattr(profile, "display_name", "") or "").strip()):
        return False
    if bool(getattr(profile, "avatar", None)):
        return False
    try:
        GameProfile = _m("user_profile", "GameProfile")
        if GameProfile is not None:
            if GameProfile.objects.filter(user=user, status="ACTIVE").exists():
                return False
    except Exception:
        pass  # Model unavailable; don't block the page
    return True


def _get_team_ids_for_user(user) -> list[int]:
    """Return all team IDs the user is actively a member of (incl. created_by)."""
    ids: list[int] = []
    try:
        TM = _m("organizations", "TeamMembership")
        if TM is not None:
            ids = list(
                TM.objects.filter(user=user, status="ACTIVE")
                .values_list("team_id", flat=True)
            )
    except Exception:
        pass
    try:
        Team = _m("organizations", "Team")
        if Team is not None:
            created = list(
                Team.objects.filter(created_by=user).values_list("id", flat=True)
            )
            ids = list(set(ids + created))
    except Exception:
        pass
    return ids


def _get_pending_action(user) -> dict | None:
    """Return {url, label} for the most urgent pending action, or None.

    Checks (priority order):
      1. Match in check_in / pending_result / disputed for any of user's registrations
      2. Open dispute the user filed
         (DisputeRecord.opened_by_user + status open/under_review/escalated)
    """
    # ── 1. Pending match state ───────────────────────────────────────────────
    try:
        Match        = _m("tournaments", "Match")
        Registration = _m("tournaments", "Registration")
        if Match is not None and Registration is not None:
            team_ids = _get_team_ids_for_user(user)

            solo_t = list(
                Registration.objects.filter(
                    user=user, is_deleted=False,
                    status__in=_ACTIVE_REG_STATUSES,
                ).values_list("tournament_id", flat=True)
            )
            team_t: list[int] = []
            if team_ids:
                team_t = list(
                    Registration.objects.filter(
                        team_id__in=team_ids, is_deleted=False,
                        status__in=_ACTIVE_REG_STATUSES,
                    ).values_list("tournament_id", flat=True)
                )
            all_t = list(set(solo_t + team_t))
            if all_t:
                m = (
                    Match.objects.filter(
                        tournament_id__in=all_t,
                        is_deleted=False,
                        state__in=_PENDING_MATCH_STATES,
                    )
                    .select_related("tournament")
                    .only("state", "tournament__slug")
                    .order_by("scheduled_time")
                    .first()
                )
                if m and getattr(m, "tournament", None):
                    label_map = {
                        "check_in":       "check-in required",
                        "pending_result": "result submission",
                        "disputed":       "dispute active",
                    }
                    return {
                        "url":   f"/tournaments/{m.tournament.slug}/hub/",
                        "label": label_map.get(m.state, "action needed"),
                    }
    except Exception:
        pass

    # ── 2. Open dispute filed by this user ───────────────────────────────────
    try:
        DisputeRecord = _m("tournaments", "DisputeRecord")
        if DisputeRecord is None:
            DisputeRecord = _m("tournaments", "Dispute")
        if DisputeRecord is not None:
            if DisputeRecord.objects.filter(
                opened_by_user=user,
                status__in=("open", "under_review", "escalated"),
            ).exists():
                return {"url": _U["disputes"], "label": "dispute open"}
    except Exception:
        pass

    return None


def _get_active_match(user) -> dict | None:
    """Return {url, name} for a live/upcoming match the user is part of."""
    try:
        Match        = _m("tournaments", "Match")
        Registration = _m("tournaments", "Registration")
        if Match is None or Registration is None:
            return None

        team_ids = _get_team_ids_for_user(user)
        solo_t = list(
            Registration.objects.filter(
                user=user, is_deleted=False, status="confirmed",
            ).values_list("tournament_id", flat=True)
        )
        team_t: list[int] = []
        if team_ids:
            team_t = list(
                Registration.objects.filter(
                    team_id__in=team_ids, is_deleted=False, status="confirmed",
                ).values_list("tournament_id", flat=True)
            )
        all_t = list(set(solo_t + team_t))
        if not all_t:
            return None

        m = (
            Match.objects.filter(
                tournament_id__in=all_t,
                is_deleted=False,
                state__in=_ACTIVE_MATCH_STATES,
            )
            .select_related("tournament")
            .only("tournament__slug", "tournament__name")
            .order_by("scheduled_time")
            .first()
        )
        if m and getattr(m, "tournament", None):
            return {"url": f"/tournaments/{m.tournament.slug}/hub/", "name": m.tournament.name}
    except Exception:
        pass
    return None


def _has_ops(user) -> bool:
    """True if user has any active competitive operations.

    Checks (each wrapped independently so a missing app never blocks):
      - ContractEnrollment (Missions): user=user, status='ACTIVE'
      - BountyClaim (Bounty):          claimed_by=user, status PENDING/VERIFIED
      - RoyaleEntry  (Dropzone):       user=user, status RESERVED/CONFIRMED
      - Challenge    (Showdown):       team is challenger/challenged, active states
    """
    # Missions ─────────────────────────────────────────────────────────────
    try:
        Enrollment = _m("contracts", "ContractEnrollment")
        if Enrollment is not None:
            if Enrollment.objects.filter(user=user, status="ACTIVE").exists():
                return True
    except Exception:
        pass

    # Bounty claims ────────────────────────────────────────────────────────
    # BountyClaim.claimed_by FK — verified in models/bounty.py line 338
    try:
        BountyClaim = _m("competition", "BountyClaim")
        if BountyClaim is not None:
            if BountyClaim.objects.filter(
                claimed_by=user, is_deleted=False,
                status__in=("PENDING", "VERIFIED"),
            ).exists():
                return True
    except Exception:
        pass

    # Dropzone (RoyaleEntry) ───────────────────────────────────────────────
    # RoyaleEntry.user FK — verified in apps/royale/models.py line 237
    # Active statuses RESERVED/CONFIRMED — verified line 212-215
    try:
        RoyaleEntry = _m("royale", "RoyaleEntry")
        if RoyaleEntry is not None:
            if RoyaleEntry.objects.filter(
                user=user, status__in=("RESERVED", "CONFIRMED"),
            ).exists():
                return True
    except Exception:
        pass

    # Showdown (Challenge) ─────────────────────────────────────────────────
    # Challenge has challenger_team/challenged_team FKs (no direct user FK).
    # Active statuses: ACCEPTED, IN_PROGRESS, PENDING_CONFIRMATION
    # (verified in models/challenge.py lines 73-77)
    try:
        Challenge = _m("competition", "Challenge")
        if Challenge is not None:
            team_ids = _get_team_ids_for_user(user)
            if team_ids:
                from django.db.models import Q
                if Challenge.objects.filter(
                    Q(challenger_team_id__in=team_ids) |
                    Q(challenged_team_id__in=team_ids),
                    status__in=("ACCEPTED", "IN_PROGRESS", "PENDING_CONFIRMATION"),
                    is_deleted=False,
                ).exists():
                    return True
    except Exception:
        pass

    return False


def _get_team_info(user) -> dict | None:
    """Return team state dict or None if the user has no active team memberships."""
    try:
        TM   = _m("organizations", "TeamMembership")
        Team = _m("organizations", "Team")
        if TM is None:
            return None

        # MembershipStatus.ACTIVE = 'ACTIVE' (verified in choices.py)
        memberships = list(
            TM.objects.filter(user=user, status="ACTIVE")
            .select_related("team")
            .only("role", "team_id", "team__name", "team__slug")
        )

        if not memberships:
            if Team is not None:
                owned = Team.objects.filter(created_by=user).first()
                if owned:
                    return {
                        "team_ids":     [owned.id],
                        "is_manager":   True,
                        "primary_team": owned,
                        "team_url":     f"/teams/{owned.slug}/manage/",
                    }
            return None

        is_manager   = any(m.role in _MANAGER_ROLES for m in memberships)
        primary_team = memberships[0].team
        for m in memberships:
            if m.role in _MANAGER_ROLES:
                primary_team = m.team
                break

        return {
            "team_ids":     [m.team_id for m in memberships],
            "is_manager":   is_manager,
            "primary_team": primary_team,
            "team_url":     (
                f"/teams/{primary_team.slug}/manage/"
                if is_manager else f"/teams/{primary_team.slug}/"
            ),
        }
    except Exception:
        return None


def _has_active_reg(user, team_ctx: dict | None) -> bool:
    """True if user (solo or via team) has any active/pending registration."""
    try:
        Registration = _m("tournaments", "Registration")
        if Registration is None:
            return False
        if Registration.objects.filter(
            user=user, is_deleted=False, status__in=_ACTIVE_REG_STATUSES,
        ).exists():
            return True
        if team_ctx and team_ctx.get("team_ids"):
            if Registration.objects.filter(
                team_id__in=team_ctx["team_ids"],
                is_deleted=False,
                status__in=_ACTIVE_REG_STATUSES,
            ).exists():
                return True
    except Exception:
        pass
    return False


def _get_trust_chips(user, team_ctx: dict | None = None) -> list[dict] | None:
    """Build personalised trust chips for logged-in users.

    Uses UserProfile.xp and .level (verified fields, models_main.py line 218-219).
    No per-user Crown Points field exists in the current schema; XP/level is used.
    """
    chips: list[dict] = []
    try:
        from apps.user_profile.models import UserProfile
        p = UserProfile.objects.filter(user=user).only("xp", "level").first()
        if p:
            if (p.xp or 0) > 0:
                chips.append({"value": f"{p.xp:,}", "label": "XP"})
            else:
                chips.append({"value": f"Level {p.level or 1}", "label": ""})
    except Exception:
        pass

    if team_ctx and team_ctx.get("team_ids"):
        n = len(team_ctx["team_ids"])
        chips.append({"value": str(n), "label": f"team{'s' if n != 1 else ''}"})

    return chips if chips else None


# ── State output builders ───────────────────────────────────────────────────
# Each builder returns BOTH main-hero keys AND outro_* keys so the template
# can use hero_ctx for both sections without a second DB call.

def _hero_guest() -> dict:
    return dict(
        mode="guest",
        # ── Main hero ──────────────────────────────────────────────────────
        eyebrow_primary="Free to compete · zero entry wall",
        eyebrow_secondary="Season 3 · open registration",
        subcopy=(
            "Build your esports identity, join verified tournaments, form real teams, "
            "and climb a ranking system where every result matters."
        ),
        primary_cta_label="Create your account",
        primary_cta_url=_U["signup"],
        secondary_cta_label="Explore tournaments",
        secondary_cta_url=_U["open_tourn"],
        hero_chips=None,
        # ── Outro / "YOUR LEGACY BEGINS HERE" ─────────────────────────────
        outro_primary_cta_label="Create your account",
        outro_primary_cta_url=_U["signup"],
        outro_secondary_cta_label="Watch live",
        outro_secondary_cta_url=_U["watch_live"],
        outro_subcopy=None,
        rotation_items=None,  # guest — never rotate signup messaging
    )


def _hero_onboarding(user) -> dict:
    username = getattr(user, "username", "Player")
    return dict(
        mode="onboarding",
        eyebrow_primary=f"Welcome, {username}",
        eyebrow_secondary="Set up your player identity",
        subcopy=(
            "Welcome to DeltaCrown. Set up your player identity, choose your games, "
            "and take your first step toward verified competition."
        ),
        primary_cta_label="Complete profile",
        primary_cta_url=_U["settings"],
        secondary_cta_label="Choose games",
        secondary_cta_url=_U["settings"],
        hero_chips=[{"value": "New", "label": "profile"}],
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="Complete profile",
        outro_primary_cta_url=_U["settings"],
        outro_secondary_cta_label="Find tournaments",
        outro_secondary_cta_url=_U["open_tourn"],
        outro_subcopy=(
            "Your legacy is built one verified result at a time. "
            "Finish setting up your player identity and take your first competitive step."
        ),
        rotation_items=None,  # onboarding — keep directive, no rotation
    )


def _hero_pending(user, pending: dict) -> dict:
    action_label = pending.get("label", "action needed")
    return dict(
        mode="pending_action",
        eyebrow_primary="Action required",
        eyebrow_secondary=action_label.title(),
        subcopy=(
            "Action needed. Review your match room, submit proof, "
            "confirm results, or respond before the window closes."
        ),
        primary_cta_label="Resolve action",
        primary_cta_url=pending["url"],
        secondary_cta_label="View operations",
        secondary_cta_url=_U["competitive"],
        hero_chips=[{"value": "", "label": action_label}],
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="Resolve action",
        outro_primary_cta_url=pending["url"],
        outro_secondary_cta_label="My operations",
        outro_secondary_cta_url=_U["competitive"],
        outro_subcopy=(
            "Your legacy is built one verified result at a time. "
            "Finish the pending step and keep your run alive."
        ),
        rotation_items=None,  # pending action — never rotate; keep urgency clear
    )


def _hero_active_match(user, match_ctx: dict) -> dict:
    name       = match_ctx.get("name", "")
    short_name = (name[:22] + "…") if len(name) > 22 else name
    return dict(
        mode="active_match",
        eyebrow_primary="Action ready",
        eyebrow_secondary="Match room waiting",
        subcopy=(
            "Your next competitive action is live. Check your match room, "
            "confirm readiness, submit results, or continue your tournament run."
        ),
        primary_cta_label="View match room",
        primary_cta_url=match_ctx["url"],
        secondary_cta_label="My tournaments",
        secondary_cta_url=_U["my_matches"],
        hero_chips=[{"value": "", "label": short_name}] if short_name else None,
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="View match room",
        outro_primary_cta_url=match_ctx["url"],
        outro_secondary_cta_label="My tournaments",
        outro_secondary_cta_url=_U["my_matches"],
        outro_subcopy=(
            "Your next match is part of the record. "
            "Enter the match room, confirm readiness, and keep your run moving."
        ),
        rotation_items=[
            # Primary stays on the match room; only secondary rotates
            {
                "subcopy": "Your next competitive action is live. Check your match room, confirm readiness, submit results, or continue your tournament run.",
                "secondary_label": "My tournaments",
                "secondary_url": _U["my_matches"],
            },
            {
                "subcopy": "Every verified result extends your competitive record. Enter the match room and keep your run going.",
                "secondary_label": "My operations",
                "secondary_url": _U["competitive"],
            },
        ],
    )


def _hero_ops(user) -> dict:
    return dict(
        mode="operations",
        eyebrow_primary="Operations active",
        eyebrow_secondary="Showdown · Missions · Bounty · Dropzone",
        subcopy=(
            "Track your Showdowns, Missions, Bounties, and Dropzone entries "
            "from one operations feed built for serious competitors."
        ),
        primary_cta_label="My operations",
        primary_cta_url=_U["competitive"],
        secondary_cta_label="Enter arena",
        secondary_cta_url=_U["arena"],
        hero_chips=[{"value": "Active", "label": "operations"}],
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="My operations",
        outro_primary_cta_url=_U["competitive"],
        outro_secondary_cta_label="Competitive hub",
        outro_secondary_cta_url=_U["arena"],
        outro_subcopy=(
            "Your competitive operations are live. "
            "Track every Showdown, Mission, Bounty, and Dropzone entry from one place."
        ),
        rotation_items=[
            {
                "subcopy": "Track your Showdowns, Missions, Bounties, and Dropzone entries from one operations feed built for serious competitors.",
                "primary_label": "My operations", "primary_url": _U["competitive"],
                "secondary_label": "Enter arena", "secondary_url": _U["arena"],
            },
            {
                "subcopy": "Your competitive operations are live. Every resolved match and completed mission moves your ranking forward.",
                "primary_label": "My operations", "primary_url": _U["competitive"],
                "secondary_label": "View matches", "secondary_url": _U["my_matches"],
            },
            {
                "subcopy": "Escrow-backed, dispute-aware, and platform-managed — your operations run exactly as they should.",
                "primary_label": "My operations", "primary_url": _U["competitive"],
                "secondary_label": "Find tournaments", "secondary_url": _U["open_tourn"],
            },
        ],
    )


def _hero_no_team(user) -> dict:
    return dict(
        mode="no_team",
        eyebrow_primary="No team yet",
        eyebrow_secondary="Create your first roster",
        subcopy=(
            "You are one roster away from competition. Create a team, recruit players, "
            "or join tournaments that support solo registration."
        ),
        primary_cta_label="Create a team",
        primary_cta_url=_U["team_create"],
        secondary_cta_label="Join tournaments",
        secondary_cta_url=_U["open_tourn"],
        hero_chips=_get_trust_chips(user),
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="Create a team",
        outro_primary_cta_url=_U["team_create"],
        outro_secondary_cta_label="Join tournaments",
        outro_secondary_cta_url=_U["open_tourn"],
        outro_subcopy=(
            "Legacies are rarely built solo. "
            "Create your roster, recruit the right players, and step into verified competition."
        ),
        rotation_items=None,  # no team — keep the message clear and single
    )


def _hero_team_manager(user, team_ctx: dict) -> dict:
    team      = team_ctx.get("primary_team")
    team_name = getattr(team, "name", "your team") if team else "your team"
    n_teams   = len(team_ctx.get("team_ids", []))
    return dict(
        mode="team_manager",
        eyebrow_primary="Captain mode",
        eyebrow_secondary="Roster control active",
        subcopy=(
            "Command your roster from one place. Manage roles, join events, "
            "review match rooms, and keep your team competition-ready."
        ),
        primary_cta_label="Manage roster",
        primary_cta_url=team_ctx.get("team_url", _U["teams"]),
        secondary_cta_label="Find events",
        secondary_cta_url=_U["open_tourn"],
        hero_chips=_get_trust_chips(user, team_ctx) or [
            {"value": team_name[:20], "label": ""},
            {"value": str(n_teams), "label": f"team{'s' if n_teams != 1 else ''}"},
        ],
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="Manage roster",
        outro_primary_cta_url=team_ctx.get("team_url", _U["teams"]),
        outro_secondary_cta_label="Find events",
        outro_secondary_cta_url=_U["open_tourn"],
        outro_subcopy=(
            "Lead the roster, shape the run, "
            "and turn every match into lasting competitive history."
        ),
        rotation_items=[
            {
                "subcopy": "Command your roster from one place. Manage roles, join events, review match rooms, and keep your team competition-ready.",
                "primary_label": "Manage roster", "primary_url": team_ctx.get("team_url", _U["teams"]),
                "secondary_label": "Find events", "secondary_url": _U["open_tourn"],
            },
            {
                "subcopy": "Lead your squad from Team HQ — enter your next event and build a competitive record that lasts.",
                "primary_label": "Manage roster", "primary_url": team_ctx.get("team_url", _U["teams"]),
                "secondary_label": "View matches", "secondary_url": _U["my_matches"],
            },
            {
                "subcopy": "Your team is competition-ready. Register for the next open event and start building a verified record.",
                "primary_label": "Register tournament", "primary_url": _U["open_tourn"],
                "secondary_label": "Manage roster", "secondary_url": team_ctx.get("team_url", _U["teams"]),
            },
        ],
    )


def _hero_team_ready(user, team_ctx: dict) -> dict:
    team_url = team_ctx.get("team_url", _U["teams"])
    return dict(
        mode="team_ready",
        eyebrow_primary="Team ready",
        eyebrow_secondary="Open events available",
        subcopy=(
            "Your team is ready for the next run. Register for open tournaments, "
            "manage your roster, and start building competitive history."
        ),
        primary_cta_label="Find events",
        primary_cta_url=_U["open_tourn"],
        secondary_cta_label="Manage team",
        secondary_cta_url=team_url,
        hero_chips=_get_trust_chips(user, team_ctx),
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="Register tournament",
        outro_primary_cta_url=_U["open_tourn"],
        outro_secondary_cta_label="Manage team",
        outro_secondary_cta_url=team_url,
        outro_subcopy=(
            "Your team is ready for the next run. "
            "Register for open tournaments, manage your roster, and start building competitive history."
        ),
        rotation_items=[
            {
                "subcopy": "Your team is ready for the next run. Register for open tournaments, manage your roster, and start building competitive history.",
                "primary_label": "Find events", "primary_url": _U["open_tourn"],
                "secondary_label": "Manage team", "secondary_url": team_url,
            },
            {
                "subcopy": "One registration away from your next competitive run. Open events are available now.",
                "primary_label": "Register tournament", "primary_url": _U["open_tourn"],
                "secondary_label": "View matches", "secondary_url": _U["my_matches"],
            },
            {
                "subcopy": "Your roster is competition-ready. Browse open tournaments and secure your next slot.",
                "primary_label": "Browse events", "primary_url": _U["open_tourn"],
                "secondary_label": "Manage team", "secondary_url": team_url,
            },
        ],
    )


def _hero_default(user) -> dict:
    username = getattr(user, "username", "Player")
    short    = username[:16]
    return dict(
        mode="default",
        eyebrow_primary=f"Welcome back, {short}",
        eyebrow_secondary="Climb toward The Crown",
        subcopy=(
            f"Welcome back, {short}. Your next competitive move is ready — "
            "manage your team, enter verified tournaments, and keep climbing toward The Crown."
        ),
        primary_cta_label="My dashboard",
        primary_cta_url=_U["dashboard"],
        secondary_cta_label="Enter arena",
        secondary_cta_url=_U["arena"],
        hero_chips=_get_trust_chips(user),
        # ── Outro ──────────────────────────────────────────────────────────
        outro_primary_cta_label="My dashboard",
        outro_primary_cta_url=_U["dashboard"],
        outro_secondary_cta_label="Enter arena",
        outro_secondary_cta_url=_U["arena"],
        outro_subcopy=(
            "Keep building your competitive identity. "
            "Manage your journey, enter the arena, and climb toward The Crown."
        ),
        rotation_items=[
            {
                "subcopy": f"Welcome back, {short}. Your next competitive move is ready — manage your team, enter verified tournaments, and keep climbing toward The Crown.",
                "primary_label": "My dashboard", "primary_url": _U["dashboard"],
                "secondary_label": "Enter arena", "secondary_url": _U["arena"],
            },
            {
                "subcopy": "Every verified match and completed operation builds your competitive standing. Keep stacking wins.",
                "primary_label": "Find tournaments", "primary_url": _U["open_tourn"],
                "secondary_label": "My operations", "secondary_url": _U["competitive"],
            },
            {
                "subcopy": "The ladder rewards consistency. Enter tournaments, complete operations, and keep climbing toward The Crown.",
                "primary_label": "My dashboard", "primary_url": _U["dashboard"],
                "secondary_label": "Find tournaments", "secondary_url": _U["open_tourn"],
            },
        ],
    )
