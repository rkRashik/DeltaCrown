from __future__ import annotations
from typing import Iterable, Optional
from django.contrib import admin, messages
from django.contrib.admin.sites import AlreadyRegistered
from django.apps import apps
from django.core.mail import send_mail
from django.utils import timezone

def _get_models():
    Registration = apps.get_model("tournaments", "Registration")
    PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
    Tournament = apps.get_model("tournaments", "Tournament")
    try:
        TournamentSettings = apps.get_model("tournaments", "TournamentSettings")
    except LookupError:
        TournamentSettings = None
    return Registration, PaymentVerification, Tournament, TournamentSettings

def _collect_receiving_numbers(tournament) -> str:
    _, _, _, TournamentSettings = _get_models()
    if not TournamentSettings or not tournament:
        return ""
    ts = TournamentSettings.objects.filter(tournament=tournament).first()
    if not ts:
        return ""
    parts = []
    for attr, label in [("bkash_number", "bKash"), ("nagad_number", "Nagad"), ("rocket_number", "Rocket")]:
        val = getattr(ts, attr, None)
        if val:
            parts.append(f"{label}: {val}")
    return " | ".join(parts)

def _find_email_from_registration(reg) -> str | None:
    # Try reg.profile.user.email
    profile = getattr(reg, "profile", None)
    user = getattr(profile, "user", None) or getattr(reg, "user", None)
    email = getattr(user, "email", None)
    if email:
        return email
    # Try team.captain.user.email
    team = getattr(reg, "team", None)
    captain = getattr(team, "captain", None) if team else None
    user2 = getattr(captain, "user", None) or getattr(getattr(captain, "userprofile", None), "user", None)
    email2 = getattr(user2, "email", None)
    return email2 or None

@admin.action(description="Email payment reminder to selected (PENDING) registrations")
def action_send_payment_reminders(modeladmin, request, queryset):
    Registration, PaymentVerification, Tournament, TournamentSettings = _get_models()
    sent = 0
    skipped = 0
    for reg in queryset.select_related():
        state = getattr(reg, "payment_state", None) or getattr(reg, "status", None) or getattr(reg, "state", None)
        state_val = str(state) if state is not None else ""
        if state_val not in {"PENDING", "PENDING_PAYMENT", "AWAITING_PAYMENT"}:
            skipped += 1
            continue
        email = _find_email_from_registration(reg)
        if not email:
            skipped += 1
            continue
        tournament = getattr(reg, "tournament", None)
        recv = _collect_receiving_numbers(tournament)
        lines = [
            f"Hello player,",
            "\nWe noticed you started registration but payment is still pending.",
            "\nPlease complete your payment using any of the organizer's numbers below:" if recv else "",
            recv,
            "\nOnce paid, reply with your Transaction ID inside the portal form.",
            f"\nTournament: {getattr(tournament, 'name', 'Unknown')}" if tournament else "",
            "\nThank you,\nDeltaCrown Team",
        ]
        body = "\n".join([ln for ln in lines if ln])
        try:
            send_mail(
                subject="Payment reminder — complete your DeltaCrown registration",
                message=body,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            sent += 1
        except Exception:
            skipped += 1
    modeladmin.message_user(request, f"Reminders sent: {sent}; skipped: {skipped}", level=messages.INFO)
