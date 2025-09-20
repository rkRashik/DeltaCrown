from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

# --- Local helpers you already have (names adjusted if different) ------------
# If your project uses other helper names, keep these shims here.
from .helpers import (
    read_title,        # -> str
    read_fee_amount,   # -> int or None
    register_url,      # -> str
    coin_policy_of,    # -> str or None (HTML)
)

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
# Optional/forgiving lookups
def _get_model(app_label: str, name: str):
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

Team = _get_model("tournaments", "Team") or _get_model("teams", "Team")
TeamMembership = _get_model("tournaments", "TeamMembership") or _get_model("teams", "TeamMembership")
PaymentVerification = _get_model("tournaments", "PaymentVerification")

# ------------------------------ Utilities ------------------------------------
def _profile_initial(user) -> Dict[str, Any]:
    init: Dict[str, Any] = {}
    if not getattr(user, "is_authenticated", False):
        return init

    # Name / email
    try:
        init["display_name"] = (getattr(user, "get_full_name", lambda: "")() or user.username or "").strip()
    except Exception:
        init["display_name"] = getattr(user, "username", "") or ""
    init["email"] = getattr(user, "email", "") or ""

    # Optional profile (phone, team name)
    for app_label in ("accounts", "profiles", "users"):
        try:
            Profile = apps.get_model(app_label, "UserProfile")
            prof = Profile.objects.filter(user=user).first()
            if prof:
                phone = getattr(prof, "phone", None) or getattr(prof, "mobile", None)
                if phone:
                    init["phone"] = str(phone)
                tname = getattr(prof, "team_name", None)
                if tname:
                    init["team_name"] = tname
                break
        except Exception:
            continue

    return init


def _is_team_event(t: Any) -> bool:
    # Flexible detection (use your own flags if available)
    for attr, truthy in (
        ("is_team_event", True),
        ("team_mode", True),
    ):
        if hasattr(t, attr) and getattr(t, attr):
            return True
    # Generic rule: team size > 1 or mode in a known set
    for attr in ("team_size_min", "team_min", "min_team_size"):
        if hasattr(t, attr) and (getattr(t, attr) or 0) > 1:
            return True
    mode = (getattr(t, "mode", "") or "").lower()
    return mode in {"team", "teams", "squad", "5v5", "3v3", "2v2"}


def _user_team(user) -> Tuple[Optional[Any], Optional[Any]]:
    """Returns (team, membership) if the user belongs to a team; otherwise (None, None)."""
    if not Team or not TeamMembership or not getattr(user, "is_authenticated", False):
        return None, None
    try:
        mem = TeamMembership.objects.select_related("team").filter(user=user).first()
        return (mem.team if mem else None), mem
    except Exception:
        # Fallback via reverse relation if present (user.team)
        team = getattr(user, "team", None)
        return team, None


def _is_captain(membership: Optional[Any]) -> bool:
    if not membership:
        return False
    # Common patterns: role field, is_captain boolean, or rank string
    if hasattr(membership, "is_captain"):
        return bool(getattr(membership, "is_captain"))
    role = (getattr(membership, "role", "") or "").lower()
    return role in {"captain", "cap", "leader", "owner"}


def _team_already_registered(t: Any, team: Any) -> bool:
    if not team:
        return False
    # Check registration record by team if your model has that field
    try:
        return Registration.objects.filter(tournament=t, team=team).exists()
    except Exception:
        # Fallback: any registration by any member of this team counts
        try:
            members = TeamMembership.objects.filter(team=team).values_list("user_id", flat=True)
            return Registration.objects.filter(tournament=t, user_id__in=list(members)).exists()
        except Exception:
            return False


# ------------------------------ View -----------------------------------------
@login_required(login_url="/accounts/login/")
def register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Registration flow (auth-gated):

    SOLO:
      - Prefills from profile.
      - Organizer-defined fields (rendered by form or context).
      - Optional payment; PaymentVerification when fee > 0.

    TEAM:
      - If user already in a team:
          - If that team is already registered → show 'already registered' and link forward.
          - Else, captain can register team; non-captain sees a clear message.
      - If user not in a team:
          - Show Create Team fields; optional checkbox "save as new team".
          - On submit, create team + membership (and enforce single-team rule).
    """
    t = get_object_or_404(Tournament, slug=slug)
    title = read_title(t)
    entry_fee = read_fee_amount(t)
    reg_url = register_url(t)
    is_team_event = _is_team_event(t)

    # Build base context used by template
    team, membership = _user_team(request.user)
    user_is_captain = _is_captain(membership)
    team_registered = _team_already_registered(t, team) if team else False

    # Team creation allowed only if the user is not in any team currently
    allow_team_create = is_team_event and team is None

    if request.method == "POST":
        # Honeypot
        if (request.POST.get("website") or "").strip():
            # Silently drop
            return redirect(reg_url)

        # --------------- SOLO FLOW ------------------------------------------
        if not is_team_event:
            display_name = (request.POST.get("display_name") or "").strip()
            phone = (request.POST.get("phone") or "").strip()
            email = (request.POST.get("email") or "").strip()
            # Organizer-defined, dynamic fields arrive in POST; we don't enumerate here.

            if not display_name or not phone:
                messages.error(request, "Please provide your display name and contact number.")
                return redirect(reg_url)

            # Payment requirements
            method = (request.POST.get("method") or "").strip().lower() or None
            txn = (request.POST.get("txn") or "").strip() or None
            fee_positive = bool(entry_fee and entry_fee > 0)
            if fee_positive and (not method or not txn or len(txn) < 6):
                messages.error(request, "Please choose a payment method and enter your transaction ID.")
                return redirect(reg_url)

            with transaction.atomic():
                reg = Registration.objects.create(
                    tournament=t,
                    user=request.user,
                    display_name=display_name or request.user.get_username(),
                    phone=phone,
                    email=email or None,
                    status="submitted",
                )
                if fee_positive and PaymentVerification:
                    PaymentVerification.objects.create(
                        tournament=t,
                        registration=reg,
                        method=method,
                        payer_number=phone or None,
                        txid=txn or None,
                        amount=entry_fee or 0,
                        status="submitted",
                    )

            messages.success(request, "Registration submitted! We’ll verify and update your status soon.")
            try:
                return redirect("tournaments:registration_receipt", slug=t.slug)
            except Exception:
                return redirect(reg_url)

        # --------------- TEAM FLOW ------------------------------------------
        # If user already in a team
        if team:
            if team_registered:
                messages.info(request, "Already registered with your team.")
                return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))

            if not user_is_captain:
                messages.error(request, "Only the team captain can register the team for this tournament.")
                return redirect(reg_url)

            # Captain-led registration uses the team’s stored data
            method = (request.POST.get("method") or "").strip().lower() or None
            txn = (request.POST.get("txn") or "").strip() or None
            fee_positive = bool(entry_fee and entry_fee > 0)
            if fee_positive and (not method or not txn or len(txn) < 6):
                messages.error(request, "Please choose a payment method and enter your transaction ID.")
                return redirect(reg_url)

            with transaction.atomic():
                reg = Registration.objects.create(
                    tournament=t,
                    user=request.user,
                    team=team,  # if your model has this FK
                    status="submitted",
                )
                if fee_positive and PaymentVerification:
                    PaymentVerification.objects.create(
                        tournament=t,
                        registration=reg,
                        method=method,
                        payer_number=(request.POST.get("phone") or None),
                        txid=txn or None,
                        amount=entry_fee or 0,
                        status="submitted",
                    )

            messages.success(request, "Team registration submitted! We’ll verify and update your status soon.")
            return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))

        # Not in a team yet → optional create-team-on-submit
        if allow_team_create:
            save_as_team = (request.POST.get("save_as_team") == "1")
            team_name = (request.POST.get("team_name") or "").strip()
            team_logo = request.FILES.get("team_logo")  # optional

            if not team_name:
                messages.error(request, "Please provide a team name.")
                return redirect(reg_url)

            # Enforce one-team rule (safety check)
            t_existing, _m = _user_team(request.user)
            if t_existing:
                messages.error(request, "You already belong to a team.")
                return redirect(reg_url)

            method = (request.POST.get("method") or "").strip().lower() or None
            txn = (request.POST.get("txn") or "").strip() or None
            fee_positive = bool(entry_fee and entry_fee > 0)
            if fee_positive and (not method or not txn or len(txn) < 6):
                messages.error(request, "Please choose a payment method and enter your transaction ID.")
                return redirect(reg_url)

            with transaction.atomic():
                # Create team + membership (captain)
                created_team = None
                if save_as_team and Team and TeamMembership:
                    created_team = Team.objects.create(
                        name=team_name,
                        logo=team_logo if team_logo else None,
                        owner=request.user if hasattr(Team, "owner") else None,
                    )
                    TeamMembership.objects.create(
                        team=created_team,
                        user=request.user,
                        role="captain" if hasattr(TeamMembership, "role") else None,
                        is_captain=True if hasattr(TeamMembership, "is_captain") else False,
                    )

                reg = Registration.objects.create(
                    tournament=t,
                    user=request.user,
                    team=created_team if created_team else None,
                    team_name=None if created_team else team_name,  # in case your model stores text
                    status="submitted",
                )

                if fee_positive and PaymentVerification:
                    PaymentVerification.objects.create(
                        tournament=t,
                        registration=reg,
                        method=method,
                        payer_number=(request.POST.get("phone") or None),
                        txid=txn or None,
                        amount=entry_fee or 0,
                        status="submitted",
                    )

            messages.success(request, "Team created and registered! We’ll verify and update your status soon.")
            return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))

        # If we reached here, something wasn’t satisfied
        messages.error(request, "Unable to process team registration. Please try again.")
        return redirect(reg_url)

    # --- Payment config flattened for templates (avoid deep template lookups) ---
    sett = getattr(t, "settings", None)
    pay = {
        "bkash": getattr(sett, "bkash_receive_number", None) if sett else None,
        "nagad": getattr(sett, "nagad_receive_number", None) if sett else None,
        "rocket": getattr(sett, "rocket_receive_number", None) if sett else None,
        "bank": getattr(sett, "bank_instructions", None) if sett else None,
    }

    # ------------------------------ GET --------------------------------------
    ctx = {
        "t": t,
        "title": title,
        "entry_fee": entry_fee,
        "register_url": reg_url,
        "coin_policy": coin_policy_of(t),
        "initial": _profile_initial(request.user),
        # Flow flags
        "is_team_event": is_team_event,
        "team": team,
        "team_registered": team_registered,
        "user_is_captain": user_is_captain,
        "allow_team_create": allow_team_create,
        "pay": pay,
        # If you wire a Django Form with organizer-defined fields, pass it here:
        # "form": form,
    }
    return render(request, "tournaments/register.html", ctx)
