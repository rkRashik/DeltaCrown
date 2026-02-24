"""
TOC API — Financial Operations (Payments Tab) Views.

Sprint 4: S4-B1 through S4-B11
Payment list, verify/reject/refund, bulk verify, revenue summary,
CSV export, prize pool, bounty CRUD, KYC endpoints.

All views inherit TOCBaseView for tournament lookup + permission check.
"""

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.payments_service import TOCPaymentsService
from apps.tournaments.api.toc.serializers import (
    BountyAssignInputSerializer,
    BountyCreateInputSerializer,
    BulkPaymentVerifyInputSerializer,
    KYCReviewInputSerializer,
    PaymentRefundInputSerializer,
    PaymentRejectInputSerializer,
)


# ── S4-B1: Payment List ──────────────────────────────────────────


class PaymentListView(TOCBaseView):
    """GET /api/toc/<slug>/payments/"""

    def get(self, request, slug):
        page = int(request.query_params.get("page", 1))
        status_filter = request.query_params.get("status")
        method_filter = request.query_params.get("method")
        search = request.query_params.get("search")
        ordering = request.query_params.get("ordering", "-created_at")

        result = TOCPaymentsService.get_payment_list(
            self.tournament,
            page=page,
            status_filter=status_filter,
            method_filter=method_filter,
            search=search,
            ordering=ordering,
        )
        return Response(result)


# ── S4-B2: Verify Payment ────────────────────────────────────────


class PaymentVerifyView(TOCBaseView):
    """POST /api/toc/<slug>/payments/<pk>/verify/"""

    def post(self, request, slug, pk):
        try:
            result = TOCPaymentsService.verify_payment(
                self.tournament,
                payment_id=pk,
                verified_by=request.user,
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S4-B3: Reject Payment ────────────────────────────────────────


class PaymentRejectView(TOCBaseView):
    """POST /api/toc/<slug>/payments/<pk>/reject/"""

    def post(self, request, slug, pk):
        ser = PaymentRejectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCPaymentsService.reject_payment(
                self.tournament,
                payment_id=pk,
                rejected_by=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S4-B4: Refund Payment ────────────────────────────────────────


class PaymentRefundView(TOCBaseView):
    """POST /api/toc/<slug>/payments/<pk>/refund/"""

    def post(self, request, slug, pk):
        ser = PaymentRefundInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCPaymentsService.refund_payment(
                self.tournament,
                payment_id=pk,
                refunded_by=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S4-B5: Bulk Verify ───────────────────────────────────────────


class PaymentBulkVerifyView(TOCBaseView):
    """POST /api/toc/<slug>/payments/bulk-verify/"""

    def post(self, request, slug):
        ser = BulkPaymentVerifyInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        result = TOCPaymentsService.bulk_verify_payments(
            self.tournament,
            payment_ids=ser.validated_data["ids"],
            verified_by=request.user,
        )
        return Response(result)


# ── S4-B6: Revenue Summary ───────────────────────────────────────


class PaymentSummaryView(TOCBaseView):
    """GET /api/toc/<slug>/payments/summary/"""

    def get(self, request, slug):
        result = TOCPaymentsService.get_revenue_summary(self.tournament)
        return Response(result)


# ── S4-B7: CSV Export ─────────────────────────────────────────────


class PaymentExportView(TOCBaseView):
    """GET /api/toc/<slug>/payments/export/"""

    def get(self, request, slug):
        csv_data = TOCPaymentsService.export_payments_csv(self.tournament)
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="payments_{self.tournament.slug}.csv"'
        )
        return response


# ── S4-B8: Prize Pool ────────────────────────────────────────────


class PrizePoolView(TOCBaseView):
    """GET /api/toc/<slug>/prize-pool/"""

    def get(self, request, slug):
        result = TOCPaymentsService.get_prize_pool(self.tournament)
        return Response(result)


# ── S4-B9: Distribute Prizes ─────────────────────────────────────


class PrizeDistributeView(TOCBaseView):
    """POST /api/toc/<slug>/prize-pool/distribute/"""

    def post(self, request, slug):
        try:
            result = TOCPaymentsService.distribute_prizes(
                self.tournament,
                distributed_by=request.user,
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ── S4-B10: Bounty CRUD ──────────────────────────────────────────


class BountyListCreateView(TOCBaseView):
    """
    GET  /api/toc/<slug>/bounties/     — List bounties
    POST /api/toc/<slug>/bounties/     — Create bounty
    """

    def get(self, request, slug):
        results = TOCPaymentsService.list_bounties(self.tournament)
        return Response({"results": results, "total": len(results)})

    def post(self, request, slug):
        ser = BountyCreateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCPaymentsService.create_bounty(
                self.tournament, **ser.validated_data
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BountyDetailView(TOCBaseView):
    """
    PATCH  /api/toc/<slug>/bounties/<bounty_id>/  — Update bounty
    DELETE /api/toc/<slug>/bounties/<bounty_id>/  — Delete bounty
    """

    def patch(self, request, slug, bounty_id):
        try:
            result = TOCPaymentsService.update_bounty(
                self.tournament, bounty_id=bounty_id, **request.data
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, bounty_id):
        try:
            result = TOCPaymentsService.delete_bounty(self.tournament, bounty_id)
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BountyAssignView(TOCBaseView):
    """POST /api/toc/<slug>/bounties/<bounty_id>/assign/"""

    def post(self, request, slug, bounty_id):
        ser = BountyAssignInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCPaymentsService.assign_bounty(
                self.tournament,
                bounty_id=bounty_id,
                user_id=ser.validated_data["user_id"],
                registration_id=ser.validated_data.get("registration_id"),
                assigned_by=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S4-B11: KYC Endpoints ────────────────────────────────────────


class KYCListView(TOCBaseView):
    """GET /api/toc/<slug>/kyc/"""

    def get(self, request, slug):
        status_filter = request.query_params.get("status")
        results = TOCPaymentsService.list_kyc_submissions(
            self.tournament, status_filter=status_filter
        )
        return Response({"results": results, "total": len(results)})


class KYCReviewView(TOCBaseView):
    """POST /api/toc/<slug>/kyc/<kyc_id>/review/"""

    def post(self, request, slug, kyc_id):
        ser = KYCReviewInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCPaymentsService.review_kyc(
                self.tournament,
                kyc_id=kyc_id,
                action=ser.validated_data["action"],
                reviewer=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response(
                {"error": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
