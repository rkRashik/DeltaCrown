# apps/tournaments/services/registration.py
"""
DEPRECATED — Lightweight registration helpers for game-specific flows.

The canonical registration service is ``registration_service.py`` (RegistrationService).
These helpers remain only for backward-compatibility with Valorant team and
eFootball solo registration API views.  New code should use RegistrationService
directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings


def _get_model(app_label: str, model_name: str):
    """
    Safe model resolver: returns None if the app/model isn't installed.
    This prevents LookupError for optional integrations.
    """
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


# --------- PV helper ------------------------------------------------

def _update_pv_for_registration(reg, method: Optional[str], reference: Optional[str],
                                amount_bdt: Optional[float], payer_account_number: Optional[str]):
    """
    Populate/refresh the related PaymentVerification row for a registration.
    Idempotent: creates if missing, updates fields if present, leaves status PENDING.
    """
    PV = _get_model("tournaments", "PaymentVerification")
    if not PV:
        return
    pv = getattr(reg, "payment_verification", None)
    if pv is None:
        try:
            pv = PV.objects.create(registration=reg)
        except Exception:
            pv = PV.objects.filter(registration=reg).first()
            if not pv:
                return

    if method:
        try:
            valid = [c[0] for c in PV.Method.choices]
            if method not in valid and hasattr(PV.Method, "OTHER"):
                method = PV.Method.OTHER
        except Exception:
            pass
        pv.method = method

    if reference:
        pv.transaction_id = reference
    if payer_account_number:
        pv.payer_account_number = payer_account_number
    if amount_bdt is not None:
        try:
            pv.amount_bdt = int(amount_bdt)
        except Exception:
            pass
    pv.save()


# --------- input DTOs (API-stable) ---------------------------------

@dataclass
class TeamRegistrationInput:
    tournament_id: int
    team_id: int
    created_by_user_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_bdt: Optional[float] = None
    payer_account_number: Optional[str] = None


@dataclass
class SoloRegistrationInput:
    tournament_id: int
    user_id: int
    created_by_user_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_bdt: Optional[float] = None
    payer_account_number: Optional[str] = None


def _get_policy(tournament) -> Optional[object]:
    Policy = _get_model("tournaments", "TournamentRegistrationPolicy")
    if not Policy:
        return None
    return getattr(tournament, "registration_policy", None)


def _send_email_safe(subject: str, message: str, to: Iterable[str]):
    try:
        send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), list(to), fail_silently=True)
    except Exception:
        pass


def _check_slot_availability(tournament):
    """
    Validates that the tournament has available slots for new registrations.
    Raises ValidationError if tournament is full.
    """
    Registration = _get_model("tournaments", "Registration")
    if not Registration:
        return
    
    slot_size = getattr(tournament, "slot_size", None)
    if slot_size is None:
        return
    if slot_size <= 0:
        raise ValidationError("Registration is not allowed for this tournament.")
    
    current_registrations = Registration.objects.filter(tournament=tournament)
    confirmed_count = current_registrations.count()
    
    if confirmed_count >= slot_size:
        raise ValidationError(
            f"Tournament is full. Maximum slots: {slot_size}, "
            f"Current registrations: {confirmed_count}"
        )


def _maybe_create_payment(method: Optional[str], ref: Optional[str], amount_bdt: Optional[float], proof_file=None):
    """
    Legacy hook: if a separate Payment app is present, create a record.
    No-op when that app isn't installed.
    """
    Payment = _get_model("payment", "Payment")
    if not Payment:
        return None
    kwargs = {}
    if hasattr(Payment, "method") and method:
        kwargs["method"] = method
    if hasattr(Payment, "reference_number") and ref:
        kwargs["reference_number"] = ref
    if hasattr(Payment, "amount_bdt") and amount_bdt is not None:
        kwargs["amount_bdt"] = amount_bdt
    if hasattr(Payment, "proof_file") and proof_file is not None:
        kwargs["proof_file"] = proof_file
    return Payment.objects.create(**kwargs)


# --------- main flows -----------------------------------------------

@transaction.atomic
def register_valorant_team(data: TeamRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    Team = _get_model("organizations", "Team")
    if not (Tournament and Registration and Team):
        raise ValidationError("Required models are not available.")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    policy = _get_policy(tournament)
    if policy and policy.mode not in ("team", "duo"):
        raise ValidationError("This tournament is not configured for team registrations.")
    
    _check_slot_availability(tournament)

    team = Team.objects.get(pk=data.team_id)
    # Registration model uses team_id (IntegerField) not team (ForeignKey)
    reg = Registration.objects.create(tournament=tournament, team_id=team.id)

    payment = _maybe_create_payment(data.payment_method, data.payment_reference, data.amount_bdt)
    if payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
        reg.save(update_fields=["payment_id"])

    _update_pv_for_registration(
        reg,
        data.payment_method,
        data.payment_reference,
        data.amount_bdt,
        data.payer_account_number,
    )

    # best-effort email to captain if available
    captain_email = None
    User = _get_model("auth", "User")
    if User and getattr(team, "captain", None):
        captain_user = getattr(team.captain, "user", None) or team.captain
        captain_email = getattr(captain_user, "email", None)
    _send_email_safe(
        subject=f"[DeltaCrown] Team registration received â€“ {getattr(tournament, 'name', '')}",
        message="Your team registration has been received. Payment will be verified by admin.",
        to=[e for e in [captain_email] if e],
    )
    return reg


@transaction.atomic
def register_efootball_player(data: SoloRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    User = _get_model("accounts", "User")
    if not (Tournament and Registration and User):
        raise ValidationError("Required models are not available.")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    policy = _get_policy(tournament)
    if policy and policy.mode not in ("solo", "duo"):
        raise ValidationError("This tournament is not configured for solo/duo registrations.")
    
    _check_slot_availability(tournament)

    user = User.objects.get(pk=data.user_id)
    reg = Registration.objects.create(tournament=tournament, user=user)

    payment = _maybe_create_payment(data.payment_method, data.payment_reference, data.amount_bdt)
    if payment and hasattr(reg, "payment_id"):
        reg.payment_id = payment.pk
        reg.save(update_fields=["payment_id"])

    _update_pv_for_registration(
        reg,
        data.payment_method,
        data.payment_reference,
        data.amount_bdt,
        data.payer_account_number,
    )

    # best-effort email to registrant
    captain_email = getattr(user, "email", None)
    _send_email_safe(
        subject=f"[DeltaCrown] Registration received â€“ {getattr(tournament, 'name', '')}",
        message="Your registration has been received. Payment will be verified by admin.",
        to=[e for e in [captain_email] if e],
    )
    return reg
