from __future__ import annotations
import csv
from io import StringIO
from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm  # subclass this so 'action' field exists
from django.http import HttpResponse
from django.utils import timezone

# Inline for PaymentVerification inside Registration
class PaymentVerificationInline(admin.StackedInline):
    model = apps.get_model("tournaments", "PaymentVerification")
    extra = 0
    can_delete = False
    fields = ("transaction_id", "payer_phone", "state", "verified_at")
    readonly_fields = ()
    fk_name = "registration"  # expected name; Django will raise if different

class ManualVerifyActionForm(ActionForm):
    """Extend Django's ActionForm so we KEEP the required 'action' field,
    adding our custom inputs for the manual verify action."""
    txn = forms.CharField(label="Transaction ID", required=False)
    phone = forms.CharField(label="Payer phone", required=False)

def export_pending_csv(modeladmin, request, queryset):
    """Export selected registrations with pending-like state to CSV."""
    NON_PENDING = {"PAID", "APPROVED", "VERIFIED", "CONFIRMED", "CANCELLED", "REJECTED", "REFUNDED"}
    rows = [("id", "tournament", "state", "created_at")]
    for reg in queryset.select_related():
        state = getattr(reg, "payment_state", None) or getattr(reg, "status", None) or getattr(reg, "state", None)
        st = (str(state).upper() if state is not None else "UNKNOWN")
        if st in NON_PENDING:
            continue
        rows.append((reg.id,
                     getattr(getattr(reg, "tournament", None), "name", ""),
                     st,
                     getattr(reg, "created_at", "")))
    sio = StringIO()
    csv.writer(sio).writerows(rows)
    resp = HttpResponse(sio.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="pending_registrations.csv' + '"'
    return resp
export_pending_csv.short_description = "Export selected (pending-like) registrations to CSV"

def record_manual_payment(modeladmin, request, queryset):
    """Record a manual txn/phone and mark payments VERIFIED for selected registrations."""
    PV = apps.get_model("tournaments", "PaymentVerification")
    verified = 0
    txn = request.POST.get("txn") or ""
    phone = request.POST.get("phone") or ""
    now = timezone.now()
    for reg in queryset:
        pv, created = PV.objects.get_or_create(registration=reg, defaults={})
        if txn and hasattr(pv, "transaction_id"):
            pv.transaction_id = txn
        if phone and hasattr(pv, "payer_phone"):
            pv.payer_phone = phone
        for attr in ("state", "status"):
            if hasattr(pv, attr):
                setattr(pv, attr, "VERIFIED")
        if hasattr(pv, "verified_at"):
            pv.verified_at = now
        pv.save()
        verified += 1
    modeladmin.message_user(request, f"Manually verified {verified} registrations.", level=messages.SUCCESS)
record_manual_payment.short_description = "Record manual txn/phone and VERIFY"

def _augment_registration_admin():
    Registration = apps.get_model("tournaments", "Registration")
    if Registration not in admin.site._registry:
        return
    reg_admin = admin.site._registry[Registration]

    # Attach inline if not already present
    inlines = list(getattr(reg_admin, "inlines", []) or [])
    if PaymentVerificationInline not in inlines:
        inlines.append(PaymentVerificationInline)
        reg_admin.inlines = inlines

    # Attach actions (idempotent)
    actions = list(getattr(reg_admin, "actions", []) or [])
    for act in (export_pending_csv, record_manual_payment):
        if act not in actions:
            actions.append(act)
    reg_admin.actions = actions

    # Use the ActionForm subclass so 'action' field remains present
    reg_admin.action_form = ManualVerifyActionForm

# Execute augmentation at import time
try:
    _augment_registration_admin()
except Exception:
    pass
