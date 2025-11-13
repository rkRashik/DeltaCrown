# apps/tournaments/api/payments.py
from rest_framework import status, permissions, viewsets, decorators
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .serializers_payments import (
    PaymentSubmitProofSerializer,
    PaymentModerateSerializer,
    PaymentRefundSerializer,
    PaymentVerificationSerializer,
)
from ..models import PaymentVerification


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read for authenticated users, write only for registration owner."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Check if user owns the registration
        return getattr(obj.registration, "user_id", None) == request.user.id


class IsStaff(permissions.BasePermission):
    """Staff-only permission for moderation actions."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class PaymentVerificationViewSet(viewsets.GenericViewSet):
    """
    API endpoints for payment verification workflow.
    
    Supports idempotency via Idempotency-Key header.
    State machine: PENDING → VERIFIED/REJECTED, VERIFIED → REFUNDED
    """
    
    queryset = PaymentVerification.objects.select_related("registration")
    serializer_class = PaymentVerificationSerializer
    lookup_field = "id"
    
    def _apply_idempotency(self, request, pv, op_name):
        """
        Apply idempotency logic using Idempotency-Key header.
        
        Returns: (previous_result, is_replay)
        - If replay detected: (pv, True)
        - If new operation: (None, False)
        """
        key = request.headers.get("Idempotency-Key")
        if not key:
            return None, False
        
        # Simple implementation: store last key on the PV row
        # For production, consider a composite key: <pv_id>:<op_name>:<key>
        if pv.idempotency_key == key:
            # Replay detected - return existing state
            return pv, True
        
        # New operation - store the key
        pv.idempotency_key = key
        pv.save(update_fields=["idempotency_key", "updated_at"])
        return None, False
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="submit-proof",
        permission_classes=[IsOwnerOrReadOnly]
    )
    @transaction.atomic
    def submit_proof(self, request, id=None):
        """
        POST /payments/{id}/submit-proof/
        
        Allows registration owner to submit/update payment proof.
        Transitions REJECTED → PENDING (resubmit allowed).
        """
        pv = self.get_object()
        
        # Owner check via IsOwnerOrReadOnly permission
        self.check_object_permissions(request, pv)
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, pv, "submit_proof")
        if replay:
            data = PaymentVerificationSerializer(pv).data
            data["idempotent_replay"] = True
            return Response(data, status=status.HTTP_200_OK)
        
        # Validate state: must be PENDING or REJECTED
        if pv.status not in ("pending", "rejected"):
            return Response(
                {"detail": f"Cannot submit proof in status: {pv.status}"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate and update proof
        ser = PaymentSubmitProofSerializer(pv, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        pv = ser.save(status="pending")  # Force PENDING on resubmits
        
        data = PaymentVerificationSerializer(pv).data
        data["idempotent_replay"] = False
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="verify",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def verify(self, request, id=None):
        """
        POST /payments/{id}/verify/
        
        Staff verifies payment. Transitions PENDING → VERIFIED.
        Idempotent: replaying same key returns original response.
        """
        pv = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, pv, "verify")
        if replay:
            data = PaymentVerificationSerializer(pv).data
            data["idempotent_replay"] = True
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if pv.status != "pending":
            return Response(
                {"detail": f"Invalid state transition from {pv.status} to verified"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = PaymentModerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Optional: validate amount matches
        if ser.validated_data.get("amount_bdt") is not None:
            if ser.validated_data["amount_bdt"] != pv.amount_bdt:
                return Response(
                    {"detail": "Amount mismatch"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Transition to VERIFIED
        pv.status = "verified"
        pv.verified_at = timezone.now()
        pv.verified_by_id = request.user.id
        
        # Merge notes if provided
        if ser.validated_data.get("notes"):
            pv.notes = {**pv.notes, **ser.validated_data["notes"]}
        
        pv.save(update_fields=["status", "verified_at", "verified_by_id", "notes", "updated_at"])
        
        data = PaymentVerificationSerializer(pv).data
        data["idempotent_replay"] = False
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def reject(self, request, id=None):
        """
        POST /payments/{id}/reject/
        
        Staff rejects payment. Transitions PENDING → REJECTED.
        Allows REJECTED → REJECTED for idempotent replays.
        """
        pv = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, pv, "reject")
        if replay:
            data = PaymentVerificationSerializer(pv).data
            data["idempotent_replay"] = True
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation (allow REJECTED for idempotency)
        if pv.status not in ("pending", "rejected"):
            return Response(
                {"detail": f"Invalid state transition from {pv.status} to rejected"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = PaymentModerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Transition to REJECTED
        pv.status = "rejected"
        pv.rejected_at = timezone.now()
        pv.rejected_by_id = request.user.id
        
        # Store reason_code in notes
        reason_code = ser.validated_data.get("reason_code", "")
        notes = ser.validated_data.get("notes") or {}
        pv.notes = {**pv.notes, "reason_code": reason_code, **notes}
        pv.reject_reason = reason_code  # Backward compat
        
        pv.save(update_fields=["status", "rejected_at", "rejected_by_id", "notes", "reject_reason", "updated_at"])
        
        data = PaymentVerificationSerializer(pv).data
        data["idempotent_replay"] = False
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="refund",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def refund(self, request, id=None):
        """
        POST /payments/{id}/refund/
        
        Staff issues refund. Transitions VERIFIED → REFUNDED.
        Business rule: can only refund verified payments.
        """
        pv = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, pv, "refund")
        if replay:
            data = PaymentVerificationSerializer(pv).data
            data["idempotent_replay"] = True
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if pv.status != "verified":
            return Response(
                {"detail": f"Invalid state transition from {pv.status} to refunded"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = PaymentRefundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Validate refund amount <= original amount
        refund_amount = ser.validated_data["amount_bdt"]
        if refund_amount > pv.amount_bdt:
            return Response(
                {"detail": f"Refund amount ({refund_amount}) exceeds original amount ({pv.amount_bdt})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Transition to REFUNDED
        pv.status = "refunded"
        pv.refunded_at = timezone.now()
        pv.refunded_by_id = request.user.id
        
        # Store refund details in notes
        reason_code = ser.validated_data["reason_code"]
        notes = ser.validated_data.get("notes") or {}
        pv.notes = {
            **pv.notes,
            "refund_amount": refund_amount,
            "refund_reason_code": reason_code,
            **notes
        }
        
        pv.save(update_fields=["status", "refunded_at", "refunded_by_id", "notes", "updated_at"])
        
        data = PaymentVerificationSerializer(pv).data
        data["idempotent_replay"] = False
        return Response(data, status=status.HTTP_200_OK)
