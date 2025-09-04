# apps/tournaments/admin/registrations.py
from __future__ import annotations

from typing import List, Optional

from django.apps import apps as django_apps
from django.contrib import admin, messages
from django.db import transaction


# ---------- Model resolvers ----------

def _get_model(app_label: str, model_name: str):
    try:
        return django_apps.get_model(app_label, model_name)
    except Exception:
        return None


def _get_registration_model():
    # Try common names used in this project
    for name in ("Registration", "TournamentRegistration"):
        m = _get_model("tournaments", name)
        if m:
            return m
    return None


RegistrationModel = _get_registration_model()
PaymentModel = _get_model("payment", "Payment")


# ---------- Payment helpers ----------

def _set_payment_status(obj, status: str, request_user=None) -> bool:
    """
    Set payment status on a Registration object.
    If a Payment FK exists, set it there. Else fall back to local `payment_status`.
    Returns True if an update was performed.
    """
    updated = False

    # Prefer FK to Payment if present (payment or payment_id)
    payment = getattr(obj, "payment", None)
    if payment is None and hasattr(obj, "payment_id"):
        pid = getattr(obj, "payment_id", None)
        if pid and PaymentModel:
            try:
                payment = PaymentModel.objects.get(pk=pid)
            except Exception:
                payment = None

    if payment is not None:
        if hasattr(payment, "status"):
            payment.status = status
            updated = True
        if status.lower() == "verified":
            # Optionally stamp verifier/verified_at if fields exist
            if hasattr(payment, "verified_by") and request_user is not None:
                try:
                    payment.verified_by = request_user
                except Exception:
                    pass
            if hasattr(payment, "verified_at"):
                from django.utils import timezone
                try:
                    payment.verified_at = timezone.now()
                except Exception:
                    pass
        try:
            payment.save()
        except Exception:
            pass

    # Fall back to a local enum/string field on Registration (if it exists)
    if hasattr(obj, "payment_status"):
        try:
            setattr(obj, "payment_status", status)
            obj.save(update_fields=["payment_status"])
            updated = True
        except Exception:
            pass

    return updated


# ---------- Admin actions (names EXACTLY as base.py expects) ----------

@admin.action(description="Mark payment VERIFIED")
@transaction.atomic
def action_verify_payment(modeladmin, request, queryset):
    done = 0
    for reg in queryset:
        if _set_payment_status(reg, "verified", request_user=getattr(request, "user", None)):
            done += 1
    modeladmin.message_user(request, f"Marked {done} registration(s) payment VERIFIED.", level=messages.SUCCESS)


@admin.action(description="Mark payment REJECTED")
@transaction.atomic
def action_reject_payment(modeladmin, request, queryset):
    done = 0
    for reg in queryset:
        if _set_payment_status(reg, "rejected", request_user=getattr(request, "user", None)):
            done += 1
    modeladmin.message_user(request, f"Marked {done} registration(s) payment REJECTED.", level=messages.WARNING)


@admin.action(description="Mark payment PENDING")
@transaction.atomic
def action_mark_pending(modeladmin, request, queryset):
    done = 0
    for reg in queryset:
        if _set_payment_status(reg, "pending", request_user=getattr(request, "user", None)):
            done += 1
    modeladmin.message_user(request, f"Marked {done} registration(s) payment PENDING.", level=messages.INFO)


# ---------- Registration admin ----------

class RegistrationAdmin(admin.ModelAdmin):
    """
    Defensive Registration admin:
    - Works whether registrant is a Team or a User/UserProfile.
    - Avoids FieldError by only select_related() on existing relations.
    - Exposes payment moderation actions (pending/verified/rejected).
    """
    list_display = ("id", "tournament_name", "registrant", "payment_state", "created_ts")
    list_filter = ()
    search_fields = ("tournament__name",)
    actions = [action_mark_pending, action_verify_payment, action_reject_payment]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Follow only relations that exist on this model
        rels: List[str] = []
        try:
            get_field = self.model._meta.get_field
        except Exception:
            get_field = None

        for name in ("tournament", "team", "user", "user_profile", "payment"):
            try:
                if get_field:
                    get_field(name)
                    rels.append(name)
            except Exception:
                pass
        return qs.select_related(*rels) if rels else qs

    # ---- columns ----
    @admin.display(description="Tournament")
    def tournament_name(self, obj):
        t = getattr(obj, "tournament", None)
        return getattr(t, "name", "—")

    @admin.display(description="Registrant")
    def registrant(self, obj):
        # Team?
        if hasattr(obj, "team") and getattr(obj, "team", None):
            team = obj.team
            return f"Team: {getattr(team, 'name', getattr(team, 'id', '—'))}"
        # Direct user?
        if hasattr(obj, "user") and getattr(obj, "user", None):
            return f"User: {getattr(obj.user, 'username', obj.user_id)}"
        # UserProfile?
        if hasattr(obj, "user_profile") and getattr(obj, "user_profile", None):
            prof = obj.user_profile
            u = getattr(prof, "user", None)
            if u:
                return f"User: {getattr(u, 'username', getattr(u, 'id', '—'))}"
            return f"Profile: {getattr(prof, 'id', '—')}"
        return "—"

    @admin.display(description="Payment")
    def payment_state(self, obj):
        p = getattr(obj, "payment", None)
        if p is not None:
            return getattr(p, "status", "—")
        return getattr(obj, "payment_status", "—")

    @admin.display(description="Created")
    def created_ts(self, obj):
        for name in ("created_at", "created", "timestamp", "created_on"):
            if hasattr(obj, name):
                return getattr(obj, name)
        return "—"


# Inline only if model is resolved
if RegistrationModel:
    class RegistrationInline(admin.TabularInline):
        model = RegistrationModel
        extra = 0
else:
    class RegistrationInline:  # type: ignore
        pass


# Register admin programmatically (avoid decorator timing issues)
if RegistrationModel:
    try:
        admin.site.register(RegistrationModel, RegistrationAdmin)
    except admin.sites.AlreadyRegistered:
        pass


# Explicit exports for base.py imports
__all__ = [
    "RegistrationAdmin",
    "RegistrationInline",
    "action_verify_payment",
    "action_reject_payment",   # <-- exact name expected by base.py
    "action_mark_pending",
]
