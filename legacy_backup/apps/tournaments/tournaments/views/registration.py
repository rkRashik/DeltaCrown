from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .helpers import (
    read_title,
    read_fee_amount,
    register_url,
    coin_policy_of,
)

# use existing models with fallbacks
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

def _get_model(app_label: str, name: str):
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

Team = _get_model("tournaments", "Team") or _get_model("teams", "Team")
TeamMembership = _get_model("tournaments", "TeamMembership") or _get_model("teams", "TeamMembership")
PaymentVerification = _get_model("tournaments", "PaymentVerification")

# import your existing forms if present
try:
    from .forms_registration import SoloRegistrationForm, TeamRegistrationForm
except Exception:
    SoloRegistrationForm = TeamRegistrationForm = None  # type: ignore


def _profile_initial(user) -> Dict[str, Any]:
    init: Dict[str, Any] = {}
    if not getattr(user, "is_authenticated", False):
        return init
    try:
        init["display_name"] = (getattr(user, "get_full_name", lambda: "")() or user.username or "").strip()
    except Exception:
        init["display_name"] = getattr(user, "username", "") or ""
    init["email"] = getattr(user, "email", "") or ""
    for app_label in ("accounts", "profiles", "users"):
        try:
            Profile = apps.get_model(app_label, "UserProfile")
            prof = Profile.objects.filter(user=user).first()
            if prof:
                phone = getattr(prof, "phone", None) or getattr(prof, "mobile", None)
                if phone:
                    init["payer_account_number"] = str(phone)  # matches forms' field
                    init["phone"] = str(phone)
                tname = getattr(prof, "team_name", None)
                if tname:
                    init["team_name"] = tname
                break
        except Exception:
            continue
    return init


def _is_team_event(t: Any) -> bool:
    for attr in ("is_team_event", "team_mode"):
        if hasattr(t, attr) and getattr(t, attr):
            return True
    for attr in ("team_size_min", "team_min", "min_team_size"):
        if hasattr(t, attr) and (getattr(t, attr) or 0) > 1:
            return True
    mode = (getattr(t, "mode", "") or "").lower()
    return mode in {"team","teams","squad","5v5","3v3","2v2"}


def _user_team(user) -> Tuple[Optional[Any], Optional[Any]]:
    if not Team or not TeamMembership or not getattr(user, "is_authenticated", False):
        return None, None
    try:
        mem = TeamMembership.objects.select_related("team").filter(user=user).first()
        return (mem.team if mem else None), mem
    except Exception:
        return getattr(user, "team", None), None


def _is_captain(membership: Optional[Any]) -> bool:
    if not membership:
        return False
    if hasattr(membership, "is_captain"):
        return bool(getattr(membership, "is_captain"))
    role = (getattr(membership, "role", "") or "").lower()
    return role in {"captain","cap","leader","owner"}


def _team_already_registered(t: Any, team: Any) -> bool:
    if not team:
        return False
    try:
        return Registration.objects.filter(tournament=t, team=team).exists()
    except Exception:
        pass
    try:
        members = TeamMembership.objects.filter(team=team).values_list("user_id", flat=True)
        return Registration.objects.filter(tournament=t, user_id__in=list(members)).exists()
    except Exception:
        return False


@login_required(login_url="/accounts/login/")
def register(request: HttpRequest, slug: str) -> HttpResponse:
    t = get_object_or_404(Tournament, slug=slug)
    title = read_title(t)
    entry_fee = read_fee_amount(t)
    reg_url = register_url(t)
    is_team_event = _is_team_event(t)

    # organizer-configured payment availability
    sett = getattr(t, "settings", None)

    def _s(val):
        try:
            return str(val) if val is not None else None
        except Exception:
            return None

    pay = {
        "bkash": _s(getattr(sett, "bkash_receive_number", None)) if sett else None,
        "nagad": _s(getattr(sett, "nagad_receive_number", None)) if sett else None,
        "rocket": _s(getattr(sett, "rocket_receive_number", None)) if sett else None,
        "bank": _s(getattr(sett, "bank_instructions", None)) if sett else None,
    }

    team, membership = _user_team(request.user)
    user_is_captain = _is_captain(membership)
    team_registered = _team_already_registered(t, team) if team else False
    allow_team_create = is_team_event and team is None

    form = None

    if request.method == "POST":
        # Honeypot
        if (request.POST.get("website") or "").strip():
            return redirect(reg_url)

        fee_positive = bool(entry_fee and entry_fee > 0)

        # SOLO FLOW -------------------------------------------------------------
        if not is_team_event:
            # duplicate guard
            try:
                if Registration.objects.filter(tournament=t, user=request.user).exists():
                    messages.info(request, "You’re already registered for this tournament.")
                    return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))
            except Exception:
                pass

            if SoloRegistrationForm:
                form = SoloRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
                if form.is_valid():
                    with transaction.atomic():
                        result = form.save()  # service-layer handles domain creation
                        # Create PaymentVerification if fee > 0 (use form values)
                        if fee_positive and PaymentVerification:
                            PaymentVerification.objects.create(
                                tournament=t,
                                registration=None,  # link if your model has FK; else leave None
                                method=(form.cleaned_data.get("payment_method") or request.POST.get("payment_method") or None),
                                payer_number=(form.cleaned_data.get("payer_account_number") or request.POST.get("payer_account_number") or None),
                                txid=(form.cleaned_data.get("payment_reference") or request.POST.get("payment_reference") or None),
                                amount=entry_fee or 0,
                                status="submitted",
                            )
                    messages.success(request, "Registration submitted! We’ll verify and update your status soon.")
                    try:
                        return redirect("tournaments:registration_receipt", slug=t.slug)
                    except Exception:
                        return redirect(reg_url)
                # invalid -> fall through to render with errors
            else:
                # Fallback minimal path if forms aren’t available
                display_name = (request.POST.get("display_name") or "").strip()
                phone = (request.POST.get("phone") or "").strip()
                email = (request.POST.get("email") or "").strip()
                if not display_name or not phone:
                    messages.error(request, "Please provide your display name and contact number.")
                else:
                    method = (request.POST.get("payment_method") or "").strip().lower() or None
                    txn = (request.POST.get("payment_reference") or "").strip() or None
                    if fee_positive and (not method or not txn or len(txn) < 6):
                        messages.error(request, "Please choose a payment method and enter your transaction ID.")
                    else:
                        with transaction.atomic():
                            reg = Registration.objects.create(
                                tournament=t, user=request.user,
                                display_name=display_name, phone=phone, email=email or None,
                                status="submitted",
                            )
                            if fee_positive and PaymentVerification:
                                PaymentVerification.objects.create(
                                    tournament=t, registration=reg,
                                    method=method, payer_number=phone or None, txid=txn or None,
                                    amount=entry_fee or 0, status="submitted",
                                )
                        messages.success(request, "Registration submitted! We’ll verify and update your status soon.")
                        try:
                            return redirect("tournaments:registration_receipt", slug=t.slug)
                        except Exception:
                            return redirect(reg_url)

        # TEAM FLOW -------------------------------------------------------------
        if team:
            if team_registered:
                messages.info(request, "Already registered with your team.")
                return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))
            if not user_is_captain:
                messages.error(request, "Only the team captain can register the team for this tournament.")
                return redirect(reg_url)

            if TeamRegistrationForm:
                form = TeamRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
                # If the form has a 'team' field, default it to current team when missing
                if hasattr(form, "fields") and "team" in form.fields and "team" not in form.data and team:
                    form.fields["team"].initial = team
                if form.is_valid():
                    with transaction.atomic():
                        result = form.save()
                        if fee_positive and PaymentVerification:
                            PaymentVerification.objects.create(
                                tournament=t,
                                registration=None,
                                method=(form.cleaned_data.get("payment_method") or request.POST.get("payment_method") or None),
                                payer_number=(form.cleaned_data.get("payer_account_number") or request.POST.get("payer_account_number") or None),
                                txid=(form.cleaned_data.get("payment_reference") or request.POST.get("payment_reference") or None),
                                amount=entry_fee or 0,
                                status="submitted",
                            )
                    messages.success(request, "Team registration submitted! We’ll verify and update your status soon.")
                    return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))
                # invalid -> render with errors
            else:
                # fallback minimal team path not using forms
                method = (request.POST.get("payment_method") or "").strip().lower() or None
                txn = (request.POST.get("payment_reference") or "").strip() or None
                fee_positive = bool(entry_fee and entry_fee > 0)
                if fee_positive and (not method or not txn or len(txn) < 6):
                    messages.error(request, "Please choose a payment method and enter your transaction ID.")
                    return redirect(reg_url)
                with transaction.atomic():
                    reg = Registration.objects.create(tournament=t, user=request.user, team=team, status="submitted")
                    if fee_positive and PaymentVerification:
                        PaymentVerification.objects.create(
                            tournament=t, registration=reg, method=method,
                            payer_number=(request.POST.get("payer_account_number") or None),
                            txid=txn or None, amount=entry_fee or 0, status="submitted",
                        )
                messages.success(request, "Team registration submitted! We’ll verify and update your status soon.")
                return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))

        # Not in a team yet: create team + membership path
        if allow_team_create:
            team_name = (request.POST.get("team_name") or "").strip()
            team_logo = request.FILES.get("team_logo")
            save_as_team = (request.POST.get("save_as_team") == "1")
            fee_positive = bool(entry_fee and entry_fee > 0)
            method = (request.POST.get("payment_method") or "").strip().lower() or None
            txn = (request.POST.get("payment_reference") or "").strip() or None

            if not team_name:
                messages.error(request, "Please provide a team name.")
                return redirect(reg_url)

            t_existing, _m = _user_team(request.user)
            if t_existing:
                messages.error(request, "You already belong to a team.")
                return redirect(reg_url)

            if fee_positive and (not method or not txn or len(txn) < 6):
                messages.error(request, "Please choose a payment method and enter your transaction ID.")
                return redirect(reg_url)

            with transaction.atomic():
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
                    team_name=None if created_team else team_name,
                    status="submitted",
                )
                if fee_positive and PaymentVerification:
                    PaymentVerification.objects.create(
                        tournament=t,
                        registration=reg,
                        method=method,
                        payer_number=(request.POST.get("payer_account_number") or None),
                        txid=txn or None,
                        amount=entry_fee or 0,
                        status="submitted",
                    )
            messages.success(request, "Team created and registered! We’ll verify and update your status soon.")
            return redirect(reverse("tournaments:detail", kwargs={"slug": t.slug}))

        # Fall-through: render with errors if any form was bound but invalid

    else:
        # GET: instantiate suitable form when available
        if not is_team_event and SoloRegistrationForm:
            form = SoloRegistrationForm(tournament=t, request=request, initial=_profile_initial(request.user))
        elif is_team_event and team and TeamRegistrationForm:
            init = _profile_initial(request.user)
            # preselect team if form has field
            try:
                if "team" in TeamRegistrationForm.base_fields and team:
                    init.setdefault("team", team.id)
            except Exception:
                pass
            form = TeamRegistrationForm(tournament=t, request=request, initial=init)

    ctx = {
        "t": t,
        "title": title,
        "entry_fee": entry_fee,
        "register_url": reg_url,
        "coin_policy": coin_policy_of(t),
        "initial": _profile_initial(request.user),
        "is_team_event": is_team_event,
        "team": team,
        "team_registered": team_registered,
        "user_is_captain": user_is_captain,
        "allow_team_create": allow_team_create,
        "pay": pay,
        "form": form,
    }
    return render(request, "tournaments/register.html", ctx)
