from __future__ import annotations
from django.contrib import admin, messages
from django.contrib.admin.sites import AlreadyRegistered
from django.apps import apps
from django.core.mail import send_mail
from django.utils import timezone
from django.db import models

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
    profile = getattr(reg, "profile", None)
    user = getattr(profile, "user", None) if profile else None
    user = user or getattr(reg, "user", None)
    if not user:
        team = getattr(reg, "team", None)
        captain = getattr(team, "captain", None) if team else None
        user = getattr(captain, "user", None) if captain else None
    email = getattr(user, "email", None) if user else None
    if email:
        return email
    try:
        for f in reg._meta.get_fields():
            if isinstance(f, (models.CharField, models.TextField)) and "email" in f.name.lower():
                val = getattr(reg, f.name, None)
                if val:
                    return val
    except Exception:
        pass
    return None

@admin.action(description="Email payment reminder to selected (PENDING) registrations")
def action_send_payment_reminders(modeladmin, request, queryset):
    sent = 0
    skipped = 0
    NON_PENDING = {"PAID", "APPROVED", "VERIFIED", "CONFIRMED", "CANCELLED", "REJECTED", "REFUNDED"}
    for reg in queryset:
        state = getattr(reg, "payment_state", None) or getattr(reg, "status", None) or getattr(reg, "state", None)
        if state is not None:
            try:
                state_val = str(state).upper()
            except Exception:
                state_val = ""
            if state_val in NON_PENDING:
                skipped += 1
                continue
        email = _find_email_from_registration(reg)
        if not email:
            skipped += 1
            continue
        tournament = getattr(reg, "tournament", None)
        recv = _collect_receiving_numbers(tournament)
        lines = [
            "Hello player,",
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

@admin.action(description="Mark selected registrations as PAID (use after manual verification)")
def action_mark_paid(modeladmin, request, queryset):
    updated = 0
    for reg in queryset:
        try:
            from apps.tournaments.services.registration import mark_registration_paid  # optional
            mark_registration_paid(reg)
            updated += 1
            continue
        except Exception:
            pass
        for attr in ("payment_state", "status", "state"):
            if hasattr(reg, attr):
                try:
                    setattr(reg, attr, "PAID")
                    reg.save(update_fields=[attr])
                    updated += 1
                    break
                except Exception:
                    continue
    modeladmin.message_user(request, f"Registrations marked PAID: {updated}", level=messages.SUCCESS)

@admin.action(description="Verify selected payments (set state=VERIFIED and stamp time)")
def action_verify_selected(modeladmin, request, queryset):
    count = 0
    for pv in queryset:
        for attr in ("state", "status"):
            if hasattr(pv, attr):
                setattr(pv, attr, "VERIFIED")
        if hasattr(pv, "verified_at") and not getattr(pv, "verified_at", None):
            pv.verified_at = timezone.now()
        try:
            pv.save()
            count += 1
        except Exception:
            continue
    modeladmin.message_user(request, f"Payments verified: {count}", level=messages.SUCCESS)

@admin.action(description="Reject selected payments (state=REJECTED)")
def action_reject_selected(modeladmin, request, queryset):
    count = 0
    for pv in queryset:
        for attr in ("state", "status"):
            if hasattr(pv, attr):
                setattr(pv, attr, "REJECTED")
        try:
            pv.save()
            count += 1
        except Exception:
            continue
    modeladmin.message_user(request, f"Payments rejected: {count}", level=messages.WARNING)

class _RegistrationAdmin(admin.ModelAdmin):
    list_display = ("id", "tournament", "created_at")
    list_filter = ("tournament",)
    date_hierarchy = "created_at"
    actions = [action_send_payment_reminders, action_mark_paid]

class _PaymentVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "registration", "transaction_id", "state", "verified_at")
    list_filter = ("state", "verified_at")
    search_fields = ("transaction_id", "registration__id")
    actions = [action_verify_selected, action_reject_selected]

def _safe_register(model_label: str, admin_cls):
    try:
        model = apps.get_model("tournaments", model_label)
        admin.site.register(model, admin_cls)
    except LookupError:
        return
    except AlreadyRegistered:
        try:
            reg = admin.site._registry[apps.get_model("tournaments", model_label)]
            existing = set(getattr(reg, "actions", []) or [])
            for act in admin_cls.actions:
                if act not in existing:
                    existing.add(act)
            reg.actions = list(existing)
        except Exception:
            pass

_safe_register("Registration", _RegistrationAdmin)
_safe_register("PaymentVerification", _PaymentVerificationAdmin)
