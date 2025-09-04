# apps/tournaments/admin/registrations.py
from __future__ import annotations

from typing import List

from django.apps import apps as django_apps
from django.contrib import admin, messages
from django.db import transaction


def _get_model(app_label: str, model_name: str):
    try:
        return django_apps.get_model(app_label, model_name)
    except Exception:
        return None


def _get_registration_model():
    for name in ("Registration", "TournamentRegistration"):
        m = _get_model("tournaments", name)
        if m:
            return m
    return None


RegistrationModel = _get_registration_model()
PaymentModel = _get_model("payment", "Payment")

# Snapshot models (may or may not exist)
EfootballSoloInfo = _get_model("game_efootball", "EfootballSoloInfo")
EfootballDuoInfo = _get_model("game_efootball", "EfootballDuoInfo")
ValorantTeamInfo = _get_model("game_valorant", "ValorantTeamInfo")
ValorantPlayer = _get_model("game_valorant", "ValorantPlayer")


# ---------- Inlines to show snapshots under a Registration ----------

if EfootballSoloInfo:
    class EfootballSoloInfoInline(admin.StackedInline):
        model = EfootballSoloInfo
        extra = 0
        can_delete = False
        readonly_fields = ()
else:
    class EfootballSoloInfoInline:  # type: ignore
        pass


if EfootballDuoInfo:
    class EfootballDuoInfoInline(admin.StackedInline):
        model = EfootballDuoInfo
        extra = 0
        can_delete = False
        readonly_fields = ()
else:
    class EfootballDuoInfoInline:  # type: ignore
        pass


if ValorantTeamInfo and ValorantPlayer:
    class ValorantPlayerInline(admin.TabularInline):
        model = ValorantPlayer
        extra = 0
        can_delete = False

    class ValorantTeamInfoInline(admin.StackedInline):
        model = ValorantTeamInfo
        extra = 0
        can_delete = False
else:
    class ValorantPlayerInline:  # type: ignore
        pass
    class ValorantTeamInfoInline:  # type: ignore
        pass


# ---------- Payment helpers & actions ----------

def _set_payment_status(obj, status: str, request_user=None) -> bool:
    updated = False
    payment = getattr(obj, "payment", None)
    if payment is None and hasattr(obj, "payment_id") and PaymentModel:
        pid = getattr(obj, "payment_id", None)
        if pid:
            try:
                payment = PaymentModel.objects.get(pk=pid)
            except Exception:
                payment = None

    if payment is not None:
        if hasattr(payment, "status"):
            payment.status = status
            updated = True
        if status.lower() == "verified":
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

    if hasattr(obj, "payment_status"):
        try:
            setattr(obj, "payment_status", status)
            obj.save(update_fields=["payment_status"])
            updated = True
        except Exception:
            pass
    return updated


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


# ---------- Registration admin (organized) ----------

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("id", "tournament_name", "registrant", "payment_state", "created_ts")
    list_filter = (
        ("tournament", admin.RelatedOnlyFieldListFilter),
        "created_at",
    )
    date_hierarchy = "created_at"
    search_fields = ("tournament__name",)
    actions = [action_mark_pending, action_verify_payment, action_reject_payment]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
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

    # columns
    @admin.display(description="Tournament")
    def tournament_name(self, obj):
        t = getattr(obj, "tournament", None)
        return getattr(t, "name", "—")

    @admin.display(description="Registrant")
    def registrant(self, obj):
        if hasattr(obj, "team") and getattr(obj, "team", None):
            team = obj.team
            return f"Team: {getattr(team, 'name', getattr(team, 'id', '—'))}"
        if hasattr(obj, "user") and getattr(obj, "user", None):
            return f"User: {getattr(obj.user, 'username', obj.user_id)}"
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


# Register Registration admin
if RegistrationModel:
    try:
        admin.site.register(RegistrationModel, RegistrationAdmin)
    except admin.sites.AlreadyRegistered:
        pass


__all__ = [
    "RegistrationAdmin",
    "action_verify_payment",
    "action_reject_payment",
    "action_mark_pending",
]
