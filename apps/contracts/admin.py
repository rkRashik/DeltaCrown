from django.contrib import admin
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone

from .models import ContractEnrollment, ContractProofSubmission, ContractTemplate
from .services import ContractService


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Mission templates."""

    list_display = (
        "title", "game", "entry_fee_dc", "reward_dc", "goal_type",
        "enrollments_count", "duration_hours", "is_active",
        "valid_from", "valid_until",
    )
    list_filter = ("is_active", "game", "goal_type")
    search_fields = ("title", "description", "badge_slug")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Mission Template", {
            "fields": ("title", "description", "game", "is_active"),
        }),
        ("Entry & Reward", {
            "fields": ("entry_fee_dc", "reward_dc", "badge_slug"),
        }),
        ("Goal", {
            "fields": ("goal_type", "goal_spec"),
        }),
        ("Availability", {
            "fields": ("duration_hours", "valid_from", "valid_until"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_enrollments_count=Count("enrollments"))

    @admin.display(description="Enrollments")
    def enrollments_count(self, obj):
        return getattr(obj, "_enrollments_count", None) or obj.enrollments.count()


@admin.register(ContractEnrollment)
class ContractEnrollmentAdmin(admin.ModelAdmin):
    """Service-backed admin interface for Mission enrollments."""

    list_display = (
        "reference_code", "mission_title", "user", "game", "status",
        "entry_fee_dc", "reward_dc", "progress_summary",
        "escrow_state", "deadline_at", "resolved_at",
    )
    list_filter = ("status", "closure_reason", "template__game")
    search_fields = ("reference_code", "user__username", "user__email", "template__title")
    readonly_fields = (
        "reference_code", "user", "template", "status", "deadline_at",
        "enrolled_at", "resolved_at", "escrow_lock_txn",
        "reward_payout_txn", "closure_reason", "closure_note",
        "entry_fee_dc", "reward_dc", "game", "escrow_state",
    )
    raw_id_fields = ("user", "template", "escrow_lock_txn", "reward_payout_txn")
    date_hierarchy = "enrolled_at"
    actions = (
        "complete_selected_missions",
        "fail_selected_missions",
        "void_refund_selected_missions",
        "expire_overdue_missions",
        "record_manual_progress_review",
    )

    fieldsets = (
        ("Mission Enrollment", {
            "fields": ("reference_code", "user", "template", "status"),
        }),
        ("Mission Details", {
            "fields": ("game", "entry_fee_dc", "reward_dc", "deadline_at"),
        }),
        ("Progress", {
            "fields": ("progress",),
            "description": "Progress JSON is operational state. Use the manual progress action for review markers.",
        }),
        ("Escrow & Reward", {
            "fields": ("escrow_state", "escrow_lock_txn", "reward_payout_txn"),
            "classes": ("collapse",),
        }),
        ("Closure", {
            "fields": ("closure_reason", "closure_note", "resolved_at"),
        }),
        ("Timestamps", {
            "fields": ("enrolled_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Mission")
    def mission_title(self, obj):
        return obj.template.title

    @admin.display(description="Game")
    def game(self, obj):
        return obj.template.game

    @admin.display(description="Entry fee")
    def entry_fee_dc(self, obj):
        return obj.template.entry_fee_dc

    @admin.display(description="Reward")
    def reward_dc(self, obj):
        return obj.template.reward_dc

    @admin.display(description="Progress")
    def progress_summary(self, obj):
        progress = obj.progress or {}
        if not progress:
            return "No progress"
        return f"{len(progress)} field(s)"

    @admin.display(description="Escrow")
    def escrow_state(self, obj):
        if obj.reward_payout_txn_id:
            return "Reward paid"
        if obj.status == "VOIDED" and obj.escrow_lock_txn_id:
            return "Entry refunded"
        if obj.status in ("FAILED", "EXPIRED", "CANCELLED") and obj.escrow_lock_txn_id:
            return "Entry forfeited"
        if obj.escrow_lock_txn_id:
            return "Entry locked"
        if obj.template.entry_fee_dc:
            return "Missing lock"
        return "Free Mission"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user", "template", "template__game",
            "escrow_lock_txn", "reward_payout_txn",
        )

    def _run_enrollment_action(self, request, queryset, callback, success_label):
        success_count = 0
        error_count = 0
        for enrollment in queryset:
            try:
                callback(enrollment)
                success_count += 1
            except Exception as exc:
                error_count += 1
                self.message_user(
                    request,
                    f"{enrollment.reference_code}: {exc}",
                    level=messages.ERROR,
                )
        if success_count:
            self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
        if error_count:
            self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

    @admin.action(description="Complete selected Missions")
    def complete_selected_missions(self, request, queryset):
        self._run_enrollment_action(
            request,
            queryset,
            lambda e: ContractService.admin_complete(
                enrollment_id=e.pk,
                actor=request.user,
                note=f"Completed from Django admin by {request.user.username}.",
            ),
            "Completed Missions",
        )

    @admin.action(description="Fail selected Missions")
    def fail_selected_missions(self, request, queryset):
        self._run_enrollment_action(
            request,
            queryset,
            lambda e: ContractService.admin_fail(
                enrollment_id=e.pk,
                actor=request.user,
                note=f"Failed from Django admin by {request.user.username}.",
            ),
            "Failed Missions",
        )

    @admin.action(description="Void/refund selected Missions")
    def void_refund_selected_missions(self, request, queryset):
        self._run_enrollment_action(
            request,
            queryset,
            lambda e: ContractService.admin_void_refund(
                enrollment_id=e.pk,
                actor=request.user,
                note=f"Voided/refunded from Django admin by {request.user.username}.",
            ),
            "Voided/refunded Missions",
        )

    @admin.action(description="Expire selected overdue Missions")
    def expire_overdue_missions(self, request, queryset):
        self._run_enrollment_action(
            request,
            queryset.filter(deadline_at__lt=timezone.now()),
            lambda e: ContractService.admin_expire(
                enrollment_id=e.pk,
                actor=request.user,
                note=f"Expired from Django admin by {request.user.username}.",
            ),
            "Expired overdue Missions",
        )

    @admin.action(description="Record manual progress review")
    def record_manual_progress_review(self, request, queryset):
        self._run_enrollment_action(
            request,
            queryset,
            lambda e: ContractService.admin_record_progress(
                enrollment_id=e.pk,
                actor=request.user,
                note=f"Manual progress review recorded by {request.user.username}.",
            ),
            "Recorded manual progress reviews",
        )


@admin.register(ContractProofSubmission)
class ContractProofSubmissionAdmin(admin.ModelAdmin):
    """Review surface for Mission proof submissions."""

    list_display = (
        "enrollment_ref", "mission_title", "submitted_by", "status",
        "has_uploaded_file", "submitted_at", "reviewed_by", "reviewed_at",
    )
    list_filter = ("status", "enrollment__template__game")
    search_fields = (
        "enrollment__reference_code",
        "enrollment__template__title",
        "submitted_by__username",
        "proof_url",
    )
    readonly_fields = (
        "enrollment", "submitted_by", "proof_url", "proof_file", "notes", "status",
        "reviewed_by", "reviewed_at", "review_note", "submitted_at", "updated_at",
    )
    raw_id_fields = ("enrollment", "submitted_by", "reviewed_by")
    date_hierarchy = "submitted_at"
    actions = ("accept_selected_proofs", "reject_selected_proofs")

    fieldsets = (
        ("Proof", {
            "fields": ("enrollment", "submitted_by", "proof_url", "proof_file", "notes", "status"),
        }),
        ("Review", {
            "fields": ("reviewed_by", "reviewed_at", "review_note"),
            "description": "Reviewing proof does not complete the Mission or settle rewards.",
        }),
        ("Timestamps", {
            "fields": ("submitted_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "enrollment", "enrollment__template", "submitted_by", "reviewed_by",
        )

    @admin.display(description="Enrollment")
    def enrollment_ref(self, obj):
        return obj.enrollment.reference_code

    @admin.display(description="Mission")
    def mission_title(self, obj):
        return obj.enrollment.template.title

    @admin.display(description="File", boolean=True)
    def has_uploaded_file(self, obj):
        return bool(obj.proof_file)

    def _review_action(self, request, queryset, decision):
        success = 0
        failed = 0
        for proof in queryset:
            try:
                ContractService.review_proof(
                    proof_id=proof.pk,
                    actor=request.user,
                    decision=decision,
                    note=f"{decision.title()} from Django admin by {request.user.username}.",
                )
                success += 1
            except Exception as exc:
                failed += 1
                self.message_user(request, f"{proof.pk}: {exc}", level=messages.ERROR)
        if success:
            self.message_user(request, f"Reviewed proofs: {success}", level=messages.SUCCESS)
        if failed:
            self.message_user(request, f"Failed reviews: {failed}", level=messages.WARNING)

    @admin.action(description="Accept selected Mission proof")
    def accept_selected_proofs(self, request, queryset):
        self._review_action(request, queryset, "ACCEPTED")

    @admin.action(description="Reject selected Mission proof")
    def reject_selected_proofs(self, request, queryset):
        self._review_action(request, queryset, "REJECTED")
