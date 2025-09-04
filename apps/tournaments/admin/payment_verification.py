# apps/tournaments/admin/payment_verification.py
from __future__ import annotations

from django.contrib import admin, messages
from django.core.mail import send_mail
from django.utils.html import format_html

from ..models import PaymentVerification


def _from_profile(obj):
    """If obj is a UserProfile, return underlying auth user; else return obj."""
    return getattr(obj, "user", None) or obj


def _registrant_email(reg) -> str | None:
    """
    Finds an email to contact the registrant.
    Supports schemas where Registration.user is a UserProfile.
    """
    # user or user_profile stored on reg.user
    user_or_profile = getattr(reg, "user", None)
    if user_or_profile:
        base_user = _from_profile(user_or_profile)
        email = getattr(base_user, "email", None)
        if email:
            return email

    # alternative field names
    profile = getattr(reg, "user_profile", None) or getattr(reg, "profile", None)
    if profile:
        base_user = _from_profile(profile)
        email = getattr(base_user, "email", None)
        if email:
            return email

    # team captain fallback
    team = getattr(reg, "team", None)
    if team:
        captain = getattr(team, "captain", None)
        captain = _from_profile(captain)
        email = getattr(captain, "email", None)
        if email:
            return email
    return None


# ensure THIS admin class is the one registered (replace earlier registrations)
try:
    admin.site.unregister(PaymentVerification)
except admin.sites.NotRegistered:
    pass


@admin.register(PaymentVerification)
class PaymentVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tournament_col",
        "registrant_col",
        "method",
        "payer_account_number",
        "transaction_id",
        "amount_bdt",
        "status",
        "verified_by",
        "verified_at",
        "created_at",
    )
    list_filter = ("status", "method", ("registration__tournament", admin.RelatedOnlyFieldListFilter))
    search_fields = ("transaction_id", "payer_account_number")
    autocomplete_fields = ("verified_by",)
    readonly_fields = ("created_at", "updated_at")

    actions = ("action_verify", "action_reject", "action_email_registrant")

    # -------- list columns --------
    def tournament_col(self, obj: PaymentVerification):
        t = getattr(obj.registration, "tournament", None)
        return getattr(t, "name", None) or getattr(t, "id", None)
    tournament_col.short_description = "Tournament"

    def registrant_col(self, obj: PaymentVerification):
        reg = obj.registration
        user_or_profile = getattr(reg, "user", None)
        label = None
        if user_or_profile:
            base_user = _from_profile(user_or_profile)
            label = getattr(base_user, "username", None) or getattr(base_user, "email", None)
        if not label:
            team = getattr(reg, "team", None)
            if team:
                label = getattr(team, "name", None)
        if not label:
            label = f"Reg #{getattr(reg, 'id', '')}"

        badge = format_html(
            '<span style="padding:2px 6px;border-radius:6px;background:#eee;font-size:11px;">{}</span>',
            obj.status,
        )
        return format_html("{} {}", label, badge)
    registrant_col.short_description = "Registrant"

    # -------- actions --------
    @admin.action(description="Verify selected payments")
    def action_verify(self, request, queryset):
        count = 0
        for pv in queryset:
            pv.mark_verified(request.user)
            count += 1
        self.message_user(request, f"Verified {count} payment(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected payments (no email)")
    def action_reject(self, request, queryset):
        count = 0
        for pv in queryset:
            pv.mark_rejected(request.user)
            count += 1
        self.message_user(request, f"Rejected {count} payment(s).", level=messages.WARNING)

    @admin.action(description="Email registrant (payment issue)")
    def action_email_registrant(self, request, queryset):
        sent = 0
        failed = 0
        for pv in queryset:
            reg = pv.registration
            email = _registrant_email(reg)
            if not email:
                failed += 1
                continue
            subject = f"Payment for {self._tournament_name(pv)}"
            body = (
                f"Hello,\n\n"
                f"We could not verify your payment for the tournament '{self._tournament_name(pv)}'.\n"
                f"Transaction ID: {pv.transaction_id or '(not provided)'}\n"
                f"Payer Account: {pv.payer_account_number or '(not provided)'}\n\n"
                f"Please reply with a valid transaction ID and a clear screenshot of the payment.\n\n"
                f"— Finance Team"
            )
            try:
                send_mail(subject, body, None, [email], fail_silently=False)
                sent += 1
            except Exception:
                failed += 1
        if sent:
            self.message_user(request, f"Emailed {sent} registrant(s).", level=messages.SUCCESS)
        if failed:
            self.message_user(request, f"Could not email {failed} registrant(s).", level=messages.ERROR)

    # -------- helpers --------
    def _tournament_name(self, pv: PaymentVerification) -> str:
        t = getattr(pv.registration, "tournament", None)
        return getattr(t, "name", None) or f"Tournament #{getattr(t, 'id', '')}"
