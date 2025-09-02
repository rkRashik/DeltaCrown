from django.contrib import admin
from django.utils import timezone

from ..models import Registration
from apps.notifications.models import Notification
from .utils import _safe_message

# ---- Registration admin actions: Verify / Reject ----
@admin.action(description="Verify payment for selected registrations")
def action_verify_payment(modeladmin, request, queryset):
    from apps.notifications.services import notify

    now = timezone.now()
    updated = 0
    for r in queryset.select_related("tournament", "user__user", "team__captain__user"):
        if r.payment_status == "verified":
            continue
        r.payment_status = "verified"
        r.payment_verified_at = now
        r.payment_verified_by = getattr(request, "user", None)
        # Auto-confirm if not already confirmed
        if r.status != "CONFIRMED":
            r.status = "CONFIRMED"
        r.save(update_fields=["payment_status", "payment_verified_at", "payment_verified_by", "status"])

        # Notify solo user or team captain
        recipient = r.user or (getattr(r.team, "captain", None))
        if recipient:
            notify(
                recipient, Notification.Type.PAYMENT_VERIFIED,
                title=f"Payment verified – {r.tournament.name}",
                body="Your payment was verified and your spot is confirmed.",
                url=f"/t/{r.tournament.slug}/",
                tournament=r.tournament,
                email_subject=f"[DeltaCrown] Payment verified – {r.tournament.name}",
                email_template="payment_verified",
                email_ctx={"t": r.tournament, "reg": r},
            )
        updated += 1

    _safe_message(modeladmin, request, f"Verified payments for {updated} registration(s).")


@admin.action(description="Reject payment for selected registrations")
def action_reject_payment(modeladmin, request, queryset):
    from apps.notifications.services import notify

    updated = 0
    for r in queryset.select_related("tournament", "user__user", "team__captain__user"):
        r.payment_status = "rejected"
        # keep status as-is (still PENDING) so user can fix and resubmit
        r.save(update_fields=["payment_status"])

        recipient = r.user or (getattr(r.team, "captain", None))
        if recipient:
            notify(
                recipient, Notification.Type.PAYMENT_REJECTED,
                title=f"Payment rejected – {r.tournament.name}",
                body="We couldn't verify your payment. Please check the reference and try again.",
                url=f"/t/{r.tournament.slug}/",
                tournament=r.tournament,
                email_subject=f"[DeltaCrown] Payment rejected – {r.tournament.name}",
                email_template="payment_rejected",
                email_ctx={"t": r.tournament, "reg": r},
            )
        updated += 1

    _safe_message(modeladmin, request, f"Rejected payments for {updated} registration(s).")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "tournament", "user", "team",
        "payment_method", "payment_sender", "payment_reference",
        "payment_status", "status",
        "payment_verified_by", "payment_verified_at",
        "created_at",
    )
    list_filter = ("payment_status", "payment_method", "status", "tournament")
    search_fields = ("payment_reference", "payment_sender")
    actions = [action_verify_payment, action_reject_payment]

    list_select_related = ("tournament", "user", "user__user")  # 'user' is a UserProfile FK

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        for rel in ("tournament", "user", "user__user", "team"):
            try:
                qs = qs.select_related(rel)
            except Exception:
                pass
        return qs

    # If you have raw_id_fields or autocomplete, keep them; otherwise:
    try:
        autocomplete_fields = ("tournament", "user", "team")  # align with models.Registration
    except Exception:
        pass


