"""
TOC Service Layer — Financial Operations (Payments Tab).

Sprint 4: S4-B1 through S4-B11
Payment verification, refunds, revenue analytics, prize distribution,
bounty management, KYC verification.

PRD: §4.1–§4.10 (Pillar 3 — Financial Operations)
"""

from __future__ import annotations

import csv
import io
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.tournaments.models.bounty import TournamentBounty
from apps.tournaments.models.kyc import KYCSubmission
from apps.tournaments.models.registration import Payment, Registration
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.registration_service import RegistrationService

logger = logging.getLogger(__name__)


class TOCPaymentsService:
    """
    High-level service for the Payments (Financial Operations) tab.

    All methods are @classmethod. Returns plain dicts.
    """

    PAGE_SIZE = 50

    # ──────────────────────────────────────────────────────────────
    # S4-B1: Paginated Payment List
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def get_payment_list(
        cls,
        tournament: Tournament,
        *,
        page: int = 1,
        status_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> Dict[str, Any]:
        """
        Return paginated, filtered payment list.

        Filters: status, method, search (team name, username, txn ID).
        """
        qs = Payment.objects.filter(
            registration__tournament=tournament,
            registration__is_deleted=False,
        ).select_related(
            "registration__user",
        ).order_by(ordering)

        if status_filter:
            qs = qs.filter(status=status_filter)

        if method_filter:
            qs = qs.filter(payment_method=method_filter)

        if search:
            qs = qs.filter(
                Q(registration__user__username__icontains=search)
                | Q(transaction_id__icontains=search)
                | Q(registration__registration_number__icontains=search)
            )

        total = qs.count()
        pages = max(1, (total + cls.PAGE_SIZE - 1) // cls.PAGE_SIZE)
        page = max(1, min(page, pages))
        offset = (page - 1) * cls.PAGE_SIZE

        results = []
        for p in qs[offset : offset + cls.PAGE_SIZE]:
            reg = p.registration
            results.append(cls._serialize_payment_row(p, reg))

        return {
            "results": results,
            "total": total,
            "page": page,
            "pages": pages,
            "page_size": cls.PAGE_SIZE,
        }

    # ──────────────────────────────────────────────────────────────
    # S4-B2: Verify Payment
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def verify_payment(
        cls,
        tournament: Tournament,
        payment_id: int,
        *,
        verified_by,
    ) -> Dict[str, Any]:
        """Verify a payment. Wraps RegistrationService.verify_payment()."""
        payment = Payment.objects.select_related("registration").get(
            id=payment_id,
            registration__tournament=tournament,
        )

        RegistrationService.verify_payment(
            registration_id=payment.registration_id,
            verified_by=verified_by,
        )

        payment.refresh_from_db()
        return cls._serialize_payment_row(payment, payment.registration)

    # ──────────────────────────────────────────────────────────────
    # S4-B3: Reject Payment
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def reject_payment(
        cls,
        tournament: Tournament,
        payment_id: int,
        *,
        rejected_by,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Reject a payment. Wraps RegistrationService.reject_payment()."""
        payment = Payment.objects.select_related("registration").get(
            id=payment_id,
            registration__tournament=tournament,
        )

        RegistrationService.reject_payment(
            registration_id=payment.registration_id,
            rejected_by=rejected_by,
            reason=reason,
        )

        payment.refresh_from_db()
        return cls._serialize_payment_row(payment, payment.registration)

    # ──────────────────────────────────────────────────────────────
    # S4-B4: Refund Payment
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def refund_payment(
        cls,
        tournament: Tournament,
        payment_id: int,
        *,
        refunded_by,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Process a refund. Wraps RegistrationService.refund_payment()."""
        payment = Payment.objects.select_related("registration").get(
            id=payment_id,
            registration__tournament=tournament,
        )

        RegistrationService.refund_payment(
            registration_id=payment.registration_id,
            refunded_by=refunded_by,
            reason=reason,
        )

        payment.refresh_from_db()
        return cls._serialize_payment_row(payment, payment.registration)

    # ──────────────────────────────────────────────────────────────
    # S4-B5: Bulk Verify
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def bulk_verify_payments(
        cls,
        tournament: Tournament,
        payment_ids: List[int],
        *,
        verified_by,
    ) -> Dict[str, Any]:
        """Bulk verify multiple payments."""
        processed = 0
        errors = []

        for pid in payment_ids:
            try:
                cls.verify_payment(tournament, pid, verified_by=verified_by)
                processed += 1
            except Exception as e:
                errors.append({"id": pid, "error": str(e)})

        return {
            "action": "bulk_verify",
            "processed": processed,
            "total_requested": len(payment_ids),
            "errors": errors,
        }

    # ──────────────────────────────────────────────────────────────
    # S4-B6: Revenue Summary
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def get_revenue_summary(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Revenue analytics for the payments tab.

        Returns stat cards: total collected, verified, pending, refunded,
        method breakdown, collection rate.
        """
        payments = Payment.objects.filter(
            registration__tournament=tournament,
            registration__is_deleted=False,
        )

        agg = payments.aggregate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
            verified_count=Count("id", filter=Q(status=Payment.VERIFIED)),
            verified_amount=Sum("amount", filter=Q(status=Payment.VERIFIED)),
            pending_count=Count("id", filter=Q(status__in=[Payment.PENDING, Payment.SUBMITTED])),
            pending_amount=Sum("amount", filter=Q(status__in=[Payment.PENDING, Payment.SUBMITTED])),
            rejected_count=Count("id", filter=Q(status=Payment.REJECTED)),
            refunded_count=Count("id", filter=Q(status=Payment.REFUNDED)),
            refunded_amount=Sum("amount", filter=Q(status=Payment.REFUNDED)),
            waived_count=Count("id", filter=Q(status=Payment.WAIVED)),
        )

        # Method breakdown
        method_breakdown = list(
            payments.values("payment_method")
            .annotate(
                count=Count("id"),
                total=Sum("amount"),
                verified=Count("id", filter=Q(status=Payment.VERIFIED)),
            )
            .order_by("-count")
        )

        total_confirmed = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).count()

        entry_fee = getattr(tournament, "entry_fee", None) or Decimal("0")
        expected_revenue = entry_fee * total_confirmed

        verified_amount = agg["verified_amount"] or Decimal("0")
        collection_rate = (
            round(float(verified_amount / expected_revenue * 100), 1)
            if expected_revenue > 0
            else 0
        )

        return {
            "total_payments": agg["total_count"] or 0,
            "total_amount": str(agg["total_amount"] or 0),
            "verified_count": agg["verified_count"] or 0,
            "verified_amount": str(verified_amount),
            "pending_count": agg["pending_count"] or 0,
            "pending_amount": str(agg["pending_amount"] or 0),
            "rejected_count": agg["rejected_count"] or 0,
            "refunded_count": agg["refunded_count"] or 0,
            "refunded_amount": str(agg["refunded_amount"] or 0),
            "waived_count": agg["waived_count"] or 0,
            "expected_revenue": str(expected_revenue),
            "collection_rate": collection_rate,
            "method_breakdown": [
                {
                    "method": m["payment_method"],
                    "count": m["count"],
                    "total": str(m["total"] or 0),
                    "verified": m["verified"],
                }
                for m in method_breakdown
            ],
        }

    # ──────────────────────────────────────────────────────────────
    # S4-B7: CSV Export
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def export_payments_csv(cls, tournament: Tournament) -> str:
        """Export all payments as CSV string."""
        payments = Payment.objects.filter(
            registration__tournament=tournament,
            registration__is_deleted=False,
        ).select_related("registration__user").order_by("-created_at")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Payment ID", "Registration #", "Participant", "Amount",
            "Method", "Transaction ID", "Status", "Verified By",
            "Verified At", "Created At",
        ])

        for p in payments:
            reg = p.registration
            writer.writerow([
                p.id,
                reg.registration_number or "",
                reg.user.username if reg.user else "",
                str(p.amount or ""),
                p.payment_method or "",
                p.transaction_id or "",
                p.status,
                p.verified_by.username if p.verified_by else "",
                p.verified_at.isoformat() if p.verified_at else "",
                p.created_at.isoformat() if p.created_at else "",
            ])

        return output.getvalue()

    # ──────────────────────────────────────────────────────────────
    # S4-B8: Prize Pool Breakdown
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def get_prize_pool(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Prize distribution breakdown for the tournament.

        Shows gross pool, deductions, net distributable, per-placement amounts.
        """
        prize_pool = getattr(tournament, "prize_pool", None) or Decimal("0")
        prize_distribution = getattr(tournament, "prize_distribution", None) or {}
        prize_currency = getattr(tournament, "prize_currency", "BDT")

        platform_fee_pct = getattr(tournament, "platform_fee_percentage", Decimal("0")) or Decimal("0")
        organizer_fee_pct = getattr(tournament, "organizer_fee_percentage", Decimal("0")) or Decimal("0")

        platform_cut = prize_pool * (platform_fee_pct / Decimal("100"))
        organizer_cut = (prize_pool - platform_cut) * (organizer_fee_pct / Decimal("100"))
        net_pool = prize_pool - platform_cut - organizer_cut

        # Bounty totals
        bounty_total = TournamentBounty.objects.filter(
            tournament=tournament,
            source=TournamentBounty.SOURCE_PRIZE_POOL,
        ).aggregate(total=Sum("prize_amount"))["total"] or Decimal("0")

        distributable = net_pool - bounty_total

        placements = []
        for place, pct_str in sorted(prize_distribution.items(), key=lambda x: int(x[0])):
            try:
                pct = Decimal(str(pct_str).replace("%", ""))
                amount = distributable * (pct / Decimal("100"))
                placements.append({
                    "place": int(place),
                    "percentage": str(pct),
                    "amount": str(amount.quantize(Decimal("0.01"))),
                })
            except (ValueError, ArithmeticError):
                pass

        return {
            "gross_prize_pool": str(prize_pool),
            "prize_currency": prize_currency,
            "platform_fee_pct": str(platform_fee_pct),
            "platform_cut": str(platform_cut.quantize(Decimal("0.01"))),
            "organizer_fee_pct": str(organizer_fee_pct),
            "organizer_cut": str(organizer_cut.quantize(Decimal("0.01"))),
            "net_pool": str(net_pool.quantize(Decimal("0.01"))),
            "bounty_allocation": str(bounty_total),
            "distributable_pool": str(distributable.quantize(Decimal("0.01"))),
            "placements": placements,
        }

    # ──────────────────────────────────────────────────────────────
    # S4-B9: Trigger Prize Distribution (placeholder)
    # ──────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def distribute_prizes(
        cls,
        tournament: Tournament,
        *,
        distributed_by,
    ) -> Dict[str, Any]:
        """
        Trigger prize distribution.

        This creates a preview; actual money movement requires
        the PrizeTransaction/PrizeClaim flow from existing services.
        """
        pool_data = cls.get_prize_pool(tournament)

        logger.info(
            "Prize distribution triggered for tournament %s by %s",
            tournament.slug, distributed_by.username,
        )

        return {
            "status": "preview",
            "message": "Prize distribution preview generated. Confirm to execute.",
            "pool": pool_data,
        }

    # ──────────────────────────────────────────────────────────────
    # S4-B10: Bounty CRUD
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def list_bounties(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """List all bounties for a tournament."""
        bounties = TournamentBounty.objects.filter(
            tournament=tournament,
        ).select_related("assigned_to").order_by("-created_at")

        return [cls._serialize_bounty(b) for b in bounties]

    @classmethod
    @transaction.atomic
    def create_bounty(
        cls,
        tournament: Tournament,
        *,
        name: str,
        description: str = "",
        bounty_type: str = "custom",
        prize_amount: Decimal,
        prize_currency: str = "BDT",
        source: str = "prize_pool",
        sponsor_name: str = "",
    ) -> Dict[str, Any]:
        """Create a new bounty."""
        bounty = TournamentBounty.objects.create(
            tournament=tournament,
            name=name,
            description=description,
            bounty_type=bounty_type,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            source=source,
            sponsor_name=sponsor_name,
        )
        return cls._serialize_bounty(bounty)

    @classmethod
    @transaction.atomic
    def update_bounty(
        cls,
        tournament: Tournament,
        bounty_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update bounty fields."""
        bounty = TournamentBounty.objects.get(
            id=bounty_id,
            tournament=tournament,
        )
        allowed_fields = [
            "name", "description", "bounty_type", "prize_amount",
            "prize_currency", "source", "sponsor_name",
        ]
        update_fields = []
        for field in allowed_fields:
            if field in kwargs:
                setattr(bounty, field, kwargs[field])
                update_fields.append(field)

        if update_fields:
            bounty.save(update_fields=update_fields)

        return cls._serialize_bounty(bounty)

    @classmethod
    @transaction.atomic
    def assign_bounty(
        cls,
        tournament: Tournament,
        bounty_id: str,
        *,
        user_id: int,
        registration_id: Optional[int] = None,
        assigned_by,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Assign a bounty to a winner."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        bounty = TournamentBounty.objects.get(
            id=bounty_id,
            tournament=tournament,
        )
        user = User.objects.get(id=user_id)

        registration = None
        if registration_id:
            registration = Registration.objects.get(id=registration_id)

        bounty.assign(user, registration=registration, assigned_by=assigned_by, reason=reason)

        logger.info(
            "Bounty '%s' assigned to %s (tournament %s)",
            bounty.name, user.username, tournament.slug,
        )

        return cls._serialize_bounty(bounty)

    @classmethod
    @transaction.atomic
    def delete_bounty(
        cls,
        tournament: Tournament,
        bounty_id: str,
    ) -> Dict[str, Any]:
        """Delete a bounty (only if not assigned)."""
        bounty = TournamentBounty.objects.get(
            id=bounty_id,
            tournament=tournament,
        )
        if bounty.is_assigned:
            raise ValidationError("Cannot delete an assigned bounty.")

        bounty.delete()
        return {"deleted": True, "id": str(bounty_id)}

    # ──────────────────────────────────────────────────────────────
    # S4-B11: KYC Endpoints
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def list_kyc_submissions(
        cls,
        tournament: Tournament,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List KYC submissions for review."""
        qs = KYCSubmission.objects.filter(
            tournament=tournament,
        ).select_related("user", "reviewer").order_by("-created_at")

        if status_filter:
            qs = qs.filter(status=status_filter)

        return [cls._serialize_kyc(k) for k in qs]

    @classmethod
    @transaction.atomic
    def review_kyc(
        cls,
        tournament: Tournament,
        kyc_id: str,
        *,
        action: str,  # 'approve', 'reject', 'flag'
        reviewer,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Approve, reject, or flag a KYC submission."""
        kyc = KYCSubmission.objects.get(
            id=kyc_id,
            tournament=tournament,
        )

        if action == "approve":
            kyc.approve(reviewer)
        elif action == "reject":
            kyc.reject(reviewer, reason)
        elif action == "flag":
            kyc.flag(reviewer)
        else:
            raise ValidationError(f"Invalid KYC action: {action}")

        return cls._serialize_kyc(kyc)

    # ──────────────────────────────────────────────────────────────
    # Private serializers
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _serialize_payment_row(cls, payment: Payment, reg: Registration) -> Dict[str, Any]:
        """Serialize a Payment to a dict for the payments grid."""
        proof_url = None
        try:
            if payment.payment_proof and hasattr(payment.payment_proof, "url"):
                proof_url = payment.payment_proof.url
        except (ValueError, AttributeError):
            pass

        # Try getting proof from PaymentVerification
        if not proof_url:
            try:
                pv = reg.payment_verification
                if pv and pv.proof_image and hasattr(pv.proof_image, "url"):
                    proof_url = pv.proof_image.url
            except (PaymentVerification.DoesNotExist, AttributeError):
                pass

        return {
            "id": payment.id,
            "registration_id": reg.id,
            "registration_number": reg.registration_number or "",
            "participant_name": reg.user.username if reg.user else "Unknown",
            "username": reg.user.username if reg.user else None,
            "amount": str(payment.amount or "0"),
            "method": payment.payment_method or "",
            "method_display": payment.get_payment_method_display() if hasattr(payment, "get_payment_method_display") else payment.payment_method or "",
            "transaction_id": payment.transaction_id or "",
            "status": payment.status,
            "status_display": payment.get_status_display() if hasattr(payment, "get_status_display") else payment.status,
            "proof_url": proof_url,
            "verified_by": payment.verified_by.username if payment.verified_by else None,
            "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
            "reject_reason": getattr(payment, "reject_reason", "") or "",
            "waived": getattr(payment, "waived", False),
            "waive_reason": getattr(payment, "waive_reason", "") or "",
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
        }

    @classmethod
    def _serialize_bounty(cls, b: TournamentBounty) -> Dict[str, Any]:
        """Serialize a TournamentBounty to a dict."""
        return {
            "id": str(b.id),
            "name": b.name,
            "description": b.description,
            "bounty_type": b.bounty_type,
            "bounty_type_display": b.get_bounty_type_display(),
            "prize_amount": str(b.prize_amount),
            "prize_currency": b.prize_currency,
            "source": b.source,
            "source_display": b.get_source_display(),
            "sponsor_name": b.sponsor_name,
            "is_assigned": b.is_assigned,
            "assigned_to": b.assigned_to.username if b.assigned_to else None,
            "assigned_to_id": b.assigned_to_id,
            "assigned_by": b.assigned_by.username if b.assigned_by else None,
            "assigned_at": b.assigned_at.isoformat() if b.assigned_at else None,
            "assignment_reason": b.assignment_reason,
            "claim_status": b.claim_status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }

    @classmethod
    def _serialize_kyc(cls, k: KYCSubmission) -> Dict[str, Any]:
        """Serialize a KYCSubmission to a dict."""
        doc_front_url = None
        try:
            if k.document_front and hasattr(k.document_front, "url"):
                doc_front_url = k.document_front.url
        except (ValueError, AttributeError):
            pass

        return {
            "id": str(k.id),
            "user_id": k.user_id,
            "username": k.user.username if k.user else None,
            "tournament_id": k.tournament_id,
            "document_type": k.document_type,
            "document_type_display": k.get_document_type_display(),
            "document_front_url": doc_front_url,
            "status": k.status,
            "status_display": k.get_status_display(),
            "reviewer": k.reviewer.username if k.reviewer else None,
            "reviewed_at": k.reviewed_at.isoformat() if k.reviewed_at else None,
            "rejection_reason": k.rejection_reason,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
