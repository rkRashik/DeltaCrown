# apps/tournaments/services/registration.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings


def _get_model(app_label: str, model_name: str):
    return apps.get_model(app_label, model_name)


def _get_policy(tournament) -> Optional[object]:
    # TournamentRegistrationPolicy is optional; enforce if present
    Policy = _get_model("tournaments", "TournamentRegistrationPolicy")
    if not Policy:
        return None
    return getattr(tournament, "registration_policy", None)


def _maybe_create_payment(method: Optional[str], ref: Optional[str], amount_bdt: Optional[float], proof_file=None):
    Payment = _get_model("payment", "Payment")
    if not Payment:
        return None

    kwargs = {}
    if hasattr(Payment, "method") and method:
        kwargs["method"] = str(method).lower()
    if hasattr(Payment, "reference_number") and ref:
        kwargs["reference_number"] = ref
    if hasattr(Payment, "amount") and amount_bdt is not None:
        kwargs["amount"] = amount_bdt
    if hasattr(Payment, "status"):
        kwargs["status"] = "pending"
    if hasattr(Payment, "proof") and proof_file is not None:
        kwargs["proof"] = proof_file

    try:
        return Payment.objects.create(**kwargs)
    except Exception:
        return None


def _send_email_safe(subject: str, message: str, to: Iterable[str]):
    try:
        if getattr(settings, "EMAIL_BACKEND", None):
            send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), list(to), fail_silently=True)
    except Exception:
        pass


# --------- simple inputs (kept for compatibility) ---------

@dataclass
class TeamRegistrationInput:
    tournament_id: int
    team_id: int
    created_by_user_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_bdt: Optional[float] = None


@dataclass
class SoloRegistrationInput:
    tournament_id: int
    user_id: int
    created_by_user_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_bdt: Optional[float] = None


@transaction.atomic
def register_valorant_team(data: TeamRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    Team = _get_model("teams", "Team")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    policy = _get_policy(tournament)

    if policy and policy.mode not in ("team", "duo"):
        raise ValidationError("This tournament is not configured for team registrations.")

    team = Team.objects.get(pk=data.team_id)
    payment = _maybe_create_payment(data.payment_method, data.payment_reference, data.amount_bdt)

    reg = Registration(tournament=tournament)
    if hasattr(reg, "team"):
        reg.team = team
    for solo_name in ("user", "user_profile", "profile"):
        if hasattr(reg, solo_name):
            setattr(reg, solo_name, None)
    if hasattr(reg, "created_by_id") and data.created_by_user_id:
        reg.created_by_id = data.created_by_user_id
    if payment and hasattr(reg, "payment"):
        reg.payment = payment
    elif payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
    reg.full_clean()
    reg.save()
    return reg


@transaction.atomic
def register_efootball_player(data: SoloRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    User = _get_model("auth", "User")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    policy = _get_policy(tournament)
    if policy and policy.mode != "solo":
        raise ValidationError("This tournament is not configured for solo registrations.")

    user = User.objects.get(pk=data.user_id)
    payment = _maybe_create_payment(data.payment_method, data.payment_reference, data.amount_bdt)

    reg = Registration(tournament=tournament)
    if hasattr(reg, "user"):
        reg.user = user
    elif hasattr(reg, "user_profile"):
        UserProfile = _get_model("user_profile", "UserProfile")
        profile = UserProfile.objects.get(user=user)
        reg.user_profile = profile

    if hasattr(reg, "created_by_id") and data.created_by_user_id:
        reg.created_by_id = data.created_by_user_id
    if payment and hasattr(reg, "payment"):
        reg.payment = payment
    elif payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
    reg.full_clean()
    reg.save()
    return reg


# --------- detailed flows (policy-enforced) ---------

@transaction.atomic
def register_efootball_solo_detailed(*, tournament, user_id: Optional[int], solo_info: dict):
    Registration = _get_model("tournaments", "Registration")
    SoloInfo = _get_model("game_efootball", "EfootballSoloInfo")

    policy = _get_policy(tournament)
    if policy and policy.mode != "solo":
        raise ValidationError("This tournament is not configured for solo registrations.")

    payment = _maybe_create_payment(
        solo_info.get("payment_method"),
        solo_info.get("payment_reference"),
        solo_info.get("amount_bdt"),
    )

    reg = Registration(tournament=tournament)
    if user_id and hasattr(reg, "user"):
        reg.user_id = user_id
    elif user_id and hasattr(reg, "user_profile"):
        UserProfile = _get_model("user_profile", "UserProfile")
        prof = UserProfile.objects.filter(user_id=user_id).first()
        if prof:
            reg.user_profile = prof

    if payment and hasattr(reg, "payment"):
        reg.payment = payment
    elif payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk

    reg.full_clean()
    reg.save()

    SoloInfo.objects.create(
        registration=reg,
        full_name=solo_info["full_name"],
        ign=solo_info["ign"],
        email=solo_info["email"],
        phone=solo_info["phone"],
        personal_team_name=solo_info["personal_team_name"],
        team_strength=solo_info["team_strength"],
        team_logo=solo_info.get("team_logo"),
        agree_rules=solo_info["agree_rules"],
        agree_no_tools=solo_info["agree_no_tools"],
        agree_no_double=solo_info["agree_no_double"],
        payment_method=solo_info.get("payment_method") or "",
        payment_reference=solo_info.get("payment_reference") or "",
        amount_bdt=solo_info.get("amount_bdt"),
    )

    _send_email_safe(
        subject=f"[DeltaCrown] Solo registration received – {getattr(tournament, 'name', '')}",
        message="Your registration has been received. Payment will be verified by admin within 24h.",
        to=[solo_info["email"]],
    )
    return reg


@transaction.atomic
def register_efootball_duo_detailed(*, tournament, user_id: Optional[int], duo_info: dict, files):
    Registration = _get_model("tournaments", "Registration")
    DuoInfo = _get_model("game_efootball", "EfootballDuoInfo")
    Team = _get_model("teams", "Team")
    TeamMembership = _get_model("teams", "TeamMembership")
    User = _get_model("auth", "User")

    policy = _get_policy(tournament)
    if policy and policy.mode not in ("duo", "team"):
        raise ValidationError("This tournament is not configured for duo/team registrations.")

    # Team size enforcement for 2v2
    if policy and (policy.team_size_min or policy.team_size_max):
        # duo is exactly 2
        if policy.team_size_min and policy.team_size_min > 2:
            raise ValidationError("Tournament policy minimum team size exceeds duo size (2).")
        if policy.team_size_max and policy.team_size_max < 2:
            raise ValidationError("Tournament policy maximum team size less than duo size (2).")

    payment = _maybe_create_payment(
        duo_info.get("payment_method"),
        duo_info.get("payment_reference"),
        duo_info.get("amount_bdt"),
        proof_file=files.get("payment_proof") if files else None,
    )

    reg = Registration(tournament=tournament)
    for solo_name in ("user", "user_profile", "profile"):
        if hasattr(reg, solo_name):
            setattr(reg, solo_name, None)
    if payment and hasattr(reg, "payment"):
        reg.payment = payment
    elif payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
    reg.full_clean()
    reg.save()

    DuoInfo.objects.create(
        registration=reg,
        team_name=duo_info["team_name"],
        team_logo=duo_info.get("team_logo"),
        captain_full_name=duo_info["captain_full_name"],
        captain_ign=duo_info["captain_ign"],
        captain_email=duo_info["captain_email"],
        captain_phone=duo_info["captain_phone"],
        mate_full_name=duo_info["mate_full_name"],
        mate_ign=duo_info["mate_ign"],
        mate_email=duo_info["mate_email"],
        mate_phone=duo_info["mate_phone"],
        agree_consent=duo_info["agree_consent"],
        agree_rules=duo_info["agree_rules"],
        agree_no_tools=duo_info["agree_no_tools"],
        agree_no_multi_team=duo_info["agree_no_multi_team"],
        payment_method=duo_info["payment_method"],
        payment_reference=duo_info["payment_reference"],
        amount_bdt=duo_info.get("amount_bdt"),
        payment_proof=files.get("payment_proof") if files else None,
    )

    # Optional: create a Team and link members if your Team/TeamMembership exist
    created_team = None
    if Team:
        kwargs = {"name": duo_info["team_name"]}
        if hasattr(Team, "game"):
            kwargs["game"] = "eFootball"
        if hasattr(Team, "logo") and duo_info.get("team_logo"):
            kwargs["logo"] = duo_info["team_logo"]
        try:
            created_team = Team.objects.create(**kwargs)
        except Exception:
            created_team = None

    if created_team and hasattr(reg, "team"):
        reg.team = created_team
        reg.save(update_fields=["team"])

    if TeamMembership and created_team and User:
        cap_user = User.objects.filter(email=duo_info["captain_email"]).first()
        mate_user = User.objects.filter(email=duo_info["mate_email"]).first()
        for u in (cap_user, mate_user):
            if not u:
                continue
            try:
                TeamMembership.objects.get_or_create(team=created_team, user=u)
            except Exception:
                pass

    _send_email_safe(
        subject=f"[DeltaCrown] 2v2 registration received – {getattr(tournament, 'name', '')}",
        message=f"Team {duo_info['team_name']} has been registered. Payment will be verified by admin.",
        to=[duo_info["captain_email"], duo_info["mate_email"]],
    )
    return reg


@transaction.atomic
def register_valorant_team_detailed(*, tournament, user_id: Optional[int], team_info: dict, files):
    TeamInfo = _get_model("game_valorant", "ValorantTeamInfo")
    Player = _get_model("game_valorant", "ValorantPlayer")
    Registration = _get_model("tournaments", "Registration")

    policy = _get_policy(tournament)
    if policy and policy.mode not in ("team", "duo"):
        raise ValidationError("This tournament is not configured for team registrations.")

    # Count roster for policy enforcement
    players = team_info.get("players") or []
    if policy and policy.team_size_min and len(players) < policy.team_size_min:
        raise ValidationError(f"Roster has {len(players)} players; minimum is {policy.team_size_min}.")
    if policy and policy.team_size_max and len(players) > policy.team_size_max:
        raise ValidationError(f"Roster has {len(players)} players; maximum is {policy.team_size_max}.")

    payment = _maybe_create_payment(
        team_info.get("payment_method"),
        team_info.get("payment_reference"),
        team_info.get("amount_bdt"),
        proof_file=files.get("payment_proof") if files else None,
    )

    reg = Registration(tournament=tournament)
    for solo_name in ("user", "user_profile", "profile"):
        if hasattr(reg, solo_name):
            setattr(reg, solo_name, None)
    if payment and hasattr(reg, "payment"):
        reg.payment = payment
    elif payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
    reg.full_clean()
    reg.save()

    info = TeamInfo.objects.create(
        registration=reg,
        team_name=team_info["team_name"],
        team_tag=team_info["team_tag"],
        team_logo=team_info.get("team_logo"),
        region=team_info["region"],
        agree_captain_consent=team_info["agree_captain_consent"],
        agree_rules=team_info["agree_rules"],
        agree_no_cheat=team_info["agree_no_cheat"],
        agree_enforcement=team_info["agree_enforcement"],
        payment_method=team_info["payment_method"],
        payment_reference=team_info["payment_reference"],
        amount_bdt=team_info.get("amount_bdt"),
        payment_proof=files.get("payment_proof") if files else None,
    )

    for p in players:
        Player.objects.create(
            team_info=info,
            full_name=p["full_name"],
            riot_id=p["riot_id"],
            riot_tagline=p["riot_tagline"],
            discord=p["discord"],
            role=p["role"],
        )

    captain_email = None
    if user_id:
        User = _get_model("auth", "User")
        if User:
            u = User.objects.filter(pk=user_id).first()
            captain_email = getattr(u, "email", None)
    _send_email_safe(
        subject=f"[DeltaCrown] Team registration received – {getattr(tournament, 'name', '')}",
        message="Your team registration has been received. Payment will be verified by admin.",
        to=[e for e in [captain_email] if e],
    )
    return reg
