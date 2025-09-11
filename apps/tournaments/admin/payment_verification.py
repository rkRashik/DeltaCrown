# apps/tournaments/admin/payment_verification.py
from __future__ import annotations

from django.contrib import admin, messages
from django.core.mail import send_mail
from django.utils.html import format_html

from ..models import PaymentVerification


def _from_profile(obj):
    return getattr(obj, "user", None) or obj


def _registrant_email(reg) -> str | None:
    uprof = getattr(reg, "user", None)
    team = getattr(reg, "team", None)
    if uprof:
        au = _from_profile(uprof)
        return getattr(au, "email", None)
    email = getattr(team, "contact_email", None) or getattr(team, "email", None)
    if not email:
        captain = getattr(team, "captain", None)
        if captain:
            au = _from_profile(captain)
            email = getattr(au, "email", None)
    return email


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
        "reject_reason",
        "created_at",
    )
    list_filter = ("status", "method", "verified_by")
    search_fields = (
        "registration__tournament__name",
        "registration__user__user__username",
        "registration__user__user__email",
        "registration__team__name",
        "transaction_id",
        "payer_account_number",
    )
    readonly_fields = ("created_at", "updated_at")

    # ensure actions are always discoverable
    actions = ["action_verify", "action_reject", "action_email_registrant"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "registration",
            "registration__tournament",
            "registration__user__user",
            "registration__team",
            "verified_by",
        )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj, "status", None) != PaymentVerification.Status.PENDING:
            ro.extend(["method", "payer_account_number", "transaction_id", "amount_bdt"])
        # dedupe
        seen, ordered = set(), []
        for f in ro:
            if f not in seen:
                seen.add(f); ordered.append(f)
        return tuple(ordered)

    @admin.display(description="Tournament")
    def tournament_col(self, pv: PaymentVerification):
        t = getattr(pv.registration, "tournament", None)
        return getattr(t, "name", None) or f"Tournament #{getattr(t, 'id', '')}"

    @admin.display(description="Registrant")
    def registrant_col(self, pv: PaymentVerification):
        reg = getattr(pv, "registration", None)
        user = getattr(reg, "user", None)
        team = getattr(reg, "team", None)
        if team:
            return format_html("<b>Team</b>: {}", getattr(team, "name", f"#{getattr(team, 'id', '')}"))
        if user:
            au = _from_profile(user)
            return format_html("<b>Player</b>: {}", getattr(au, "username", f"#{getattr(user, 'id', '')}"))
        return "–"

    # -------- actions --------
    @admin.action(description="Verify selected payments")
    def action_verify(self, request, queryset):
        count = skipped = 0
        for pv in queryset:
            # Skip already terminal states
            if pv.status in (PaymentVerification.Status.VERIFIED, PaymentVerification.Status.REJECTED):
                skipped += 1
                continue
            tx = getattr(pv, "transaction_id", None)
            if tx:
                dup = (
                    PaymentVerification.objects.filter(
                        transaction_id=tx, status=PaymentVerification.Status.VERIFIED
                    )
                    .exclude(pk=pv.pk)
                    .exists()
                )
                if dup:
                    skipped += 1
                    self.message_user(
                        request,
                        f"Skipped reg #{getattr(pv.registration, 'id', '')}: duplicate Transaction ID '{tx}' already verified.",
                        level=messages.WARNING,
                    )
                    continue
            pv.mark_verified(request.user, reason="Manual verify via admin")
            count += 1
        if count:
            self.message_user(request, f"Verified {count} payment(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped {skipped} duplicate(s).", level=messages.WARNING)

    @admin.action(description="Reject selected payments (no email)")
    def action_reject(self, request, queryset):
        count = skipped = 0
        for pv in queryset:
            if pv.status in (PaymentVerification.Status.VERIFIED, PaymentVerification.Status.REJECTED):
                skipped += 1
                continue
            pv.mark_rejected(request.user, reason="Manual reject via admin")
            count += 1
        if count:
            self.message_user(request, f"Rejected {count} payment(s).", level=messages.WARNING)
        if skipped:
            self.message_user(request, f"Skipped {skipped} already processed.", level=messages.WARNING)

    @admin.action(description="Email registrant(s) – payment received & pending manual verification")
    def action_email_registrant(self, request, queryset):
        sent = failed = 0
        for pv in queryset:
            reg = getattr(pv, "registration", None)
            email = _registrant_email(reg)
            if not email:
                failed += 1
                continue
            subject = f"[DeltaCrown] We received your payment – {self._tournament_name(pv)}"
            body = (
                "Hi,\n\n"
                "We received your payment details and your registration is in the manual verification queue.\n\n"
                f"• Method: {pv.method}\n"
                f"• Transaction ID: {pv.transaction_id or '—'}\n"
                f"• Payer Account: {pv.payer_account_number or '—'}\n"
                f"• Amount (BDT): {pv.amount_bdt or '—'}\n\n"
                "We'll notify you once the verification is complete.\n\n"
                "— DeltaCrown Finance"
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

    def _tournament_name(self, pv: PaymentVerification) -> str:
        t = getattr(pv.registration, "tournament", None)
        return getattr(t, "name", None) or f"Tournament #{getattr(t, 'id', '')}"
