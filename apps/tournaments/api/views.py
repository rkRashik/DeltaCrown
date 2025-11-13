# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-views
# Implements: Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md#registration-api
# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#rest-api-layer

"""
Tournament API - ViewSets

DRF viewsets for tournament registration endpoints.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Views)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Registration API)
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md (Security & Permissions)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (API Standards)
"""

# Import registration viewset from registrations.py
from apps.tournaments.api.registrations import RegistrationViewSet

# Keep legacy imports for backward compatibility
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils import timezone
from apps.tournaments.models.registration import Registration


# All tournament API endpoints are now in separate modules
# RegistrationViewSet is in registrations.py
# (imported at top for backward compatibility)

# ============================================================================
# Payment API ViewSet (Module 3.2: Payment Processing)
# ============================================================================


class PaymentViewSet(viewsets.GenericViewSet):
    """
    ViewSet for payment proof submissions and verification.
    
    Endpoints:
    - GET /api/payments/{id}/ - Payment status retrieval
    - POST /api/registrations/{reg_id}/payments/submit-proof/ - Submit payment proof (multipart)
    - POST /api/payments/{id}/verify/ - Verify payment (organizer/admin only)
    - POST /api/payments/{id}/reject/ - Reject payment (organizer/admin only)
    - POST /api/payments/{id}/refund/ - Process refund (organizer/admin only)
    
    Permissions:
    - Authentication required for all endpoints
    - Submit proof: Owner or organizer
    - Verify/Reject/Refund: Organizer or admin only
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Queryset for payments.
        
        Users can see:
        - Their own payments (through their registrations)
        - Payments for tournaments they organize
        
        Staff can see all payments.
        """
        from apps.tournaments.models.registration import Payment
        
        user = self.request.user
        
        if user.is_staff:
            return Payment.objects.select_related(
                'registration__tournament',
                'registration__user'
            ).all()
        
        # Filter payments for user's registrations or organized tournaments
        return Payment.objects.select_related(
            'registration__tournament',
            'registration__user'
        ).filter(
            models.Q(registration__user=user) |
            models.Q(registration__tournament__organizer=user)
        )
    
    def retrieve(self, request, pk=None):
        """
        GET /api/payments/{id}/
        
        Retrieve payment status and details.
        
        Returns:
            200: Payment details
            403: Forbidden (not owner or organizer)
            404: Payment not found
        """
        from apps.tournaments.models.registration import Payment
        from apps.tournaments.api.serializers import PaymentStatusSerializer
        from django.db import models
        
        try:
            payment = self.get_queryset().get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PaymentStatusSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path=r'registrations/(?P<registration_id>\d+)/submit-proof', url_name='submit-proof')
    def submit_proof(self, request, registration_id=None):
        """
        POST /api/tournaments/payments/registrations/{registration_id}/submit-proof/
        
        Submit payment proof file (multipart/form-data).
        
        Request Body (multipart):
            - payment_proof: File (required, max 5MB, JPG/PNG/PDF)
            - reference_number: str (optional, e.g., bKash transaction ID)
            - notes: str (optional)
        
        Returns:
            200: Payment proof submitted successfully
            400: Validation errors
            403: Forbidden (not owner or organizer)
            404: Registration not found
        """
        from apps.tournaments.models.registration import Registration, Payment
        from apps.tournaments.api.serializers import PaymentProofSubmitSerializer, PaymentStatusSerializer
        from rest_framework.parsers import MultiPartParser, FormParser
        
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(pk=registration_id)
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission - must be owner or organizer
        if not (request.user == registration.user or 
                request.user == registration.tournament.organizer or
                request.user.is_staff):
            return Response(
                {'error': 'You do not have permission to submit proof for this registration'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input
        serializer = PaymentProofSubmitSerializer(
            data=request.data,
            context={'registration': registration, 'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Submit payment proof via service layer
        try:
            payment = RegistrationService.submit_payment_proof(
                registration_id=registration.id,
                payment_proof_file=serializer.validated_data['payment_proof'],
                reference_number=serializer.validated_data.get('reference_number', ''),
                notes=serializer.validated_data.get('notes', '')
            )
            
            # Broadcast payment proof submitted event
            self._broadcast_proof_submitted(payment)
            
            # Return updated payment status
            response_serializer = PaymentStatusSerializer(payment)
            return Response(
                {
                    'message': 'Payment proof submitted successfully',
                    'payment': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        POST /api/payments/{id}/verify/
        
        Verify payment proof (organizer/admin only).
        
        Request Body:
            - notes: str (optional)
        
        Returns:
            200: Payment verified successfully
            400: Validation errors
            403: Forbidden (not organizer/admin)
            404: Payment not found
        """
        from apps.tournaments.models.registration import Payment
        from apps.tournaments.api.serializers import PaymentVerifySerializer, PaymentStatusSerializer
        
        # Get payment
        try:
            payment = self.get_queryset().get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission - must be organizer or admin
        if not (request.user == payment.registration.tournament.organizer or request.user.is_staff):
            return Response(
                {'error': 'Only tournament organizers and admins can verify payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input
        serializer = PaymentVerifySerializer(
            data=request.data,
            context={'payment': payment, 'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify payment via service layer
        try:
            verified_payment = RegistrationService.verify_payment(
                payment_id=payment.id,
                verified_by=request.user,
                admin_notes=serializer.validated_data.get('admin_notes', '')
            )
            
            # Broadcast payment verified event
            self._broadcast_payment_verified(verified_payment)
            
            # Return updated payment status
            response_serializer = PaymentStatusSerializer(verified_payment)
            return Response(
                {
                    'message': 'Payment verified successfully',
                    'payment': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        POST /api/payments/{id}/reject/
        
        Reject payment proof (organizer/admin only).
        
        Request Body:
            - reason: str (required)
            - notes: str (optional)
        
        Returns:
            200: Payment rejected successfully
            400: Validation errors
            403: Forbidden (not organizer/admin)
            404: Payment not found
        """
        from apps.tournaments.models.registration import Payment
        from apps.tournaments.api.serializers import PaymentRejectSerializer, PaymentStatusSerializer
        
        # Get payment
        try:
            payment = self.get_queryset().get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission - must be organizer or admin
        if not (request.user == payment.registration.tournament.organizer or request.user.is_staff):
            return Response(
                {'error': 'Only tournament organizers and admins can reject payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input
        serializer = PaymentRejectSerializer(
            data=request.data,
            context={'payment': payment, 'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Reject payment via service layer
        try:
            rejected_payment = RegistrationService.reject_payment(
                payment_id=payment.id,
                rejected_by=request.user,
                reason=serializer.validated_data['admin_notes']
            )
            
            # Broadcast payment rejected event
            self._broadcast_payment_rejected(rejected_payment, serializer.validated_data['admin_notes'])
            
            # Return updated payment status
            response_serializer = PaymentStatusSerializer(rejected_payment)
            return Response(
                {
                    'message': 'Payment rejected',
                    'payment': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        POST /api/payments/{id}/refund/
        
        Process payment refund (organizer/admin only).
        
        Request Body:
            - reason: str (required)
            - refund_method: str (required: 'same', 'deltacoin', 'manual')
            - notes: str (optional)
        
        Returns:
            200: Refund processed successfully
            400: Validation errors
            403: Forbidden (not organizer/admin)
            404: Payment not found
        """
        from apps.tournaments.models.registration import Payment
        from apps.tournaments.api.serializers import PaymentRefundSerializer, PaymentStatusSerializer
        
        # Get payment
        try:
            payment = self.get_queryset().get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission - must be organizer or admin
        if not (request.user == payment.registration.tournament.organizer or request.user.is_staff):
            return Response(
                {'error': 'Only tournament organizers and admins can process refunds'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input
        serializer = PaymentRefundSerializer(
            data=request.data,
            context={'payment': payment, 'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Process refund via service layer
        try:
            refunded_payment = RegistrationService.refund_payment(
                payment_id=payment.id,
                refunded_by=request.user,
                reason=serializer.validated_data['admin_notes']
            )
            
            # Broadcast payment refunded event
            self._broadcast_payment_refunded(refunded_payment, serializer.validated_data['admin_notes'])
            
            # Return updated payment status
            response_serializer = PaymentStatusSerializer(refunded_payment)
            return Response(
                {
                    'message': 'Refund processed successfully',
                    'payment': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # =========================================================================
    # WebSocket Broadcast Helpers
    # =========================================================================
    
    def _broadcast_proof_submitted(self, payment):
        """
        Broadcast payment_proof_submitted event to WebSocket clients.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tournament_{payment.registration.tournament.id}",
                {
                    "type": "payment.proof_submitted",
                    "payment_id": payment.id,
                    "registration_id": payment.registration.id,
                    "tournament_id": payment.registration.tournament.id,
                    "status": payment.status,
                    "timestamp": payment.submitted_at.isoformat() if payment.submitted_at else timezone.now().isoformat(),
                }
            )
    
    def _broadcast_payment_verified(self, payment):
        """
        Broadcast payment_verified event to WebSocket clients.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tournament_{payment.registration.tournament.id}",
                {
                    "type": "payment.verified",
                    "payment_id": payment.id,
                    "registration_id": payment.registration.id,
                    "tournament_id": payment.registration.tournament.id,
                    "verified_by": payment.verified_by.username if payment.verified_by else None,
                    "timestamp": payment.verified_at.isoformat() if payment.verified_at else timezone.now().isoformat(),
                }
            )
    
    def _broadcast_payment_rejected(self, payment, reason):
        """
        Broadcast payment_rejected event to WebSocket clients.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tournament_{payment.registration.tournament.id}",
                {
                    "type": "payment.rejected",
                    "payment_id": payment.id,
                    "registration_id": payment.registration.id,
                    "tournament_id": payment.registration.tournament.id,
                    "reason": reason,
                    "timestamp": payment.verified_at.isoformat() if payment.verified_at else timezone.now().isoformat(),
                }
            )
    
    def _broadcast_payment_refunded(self, payment, reason):
        """
        Broadcast payment_refunded event to WebSocket clients.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tournament_{payment.registration.tournament.id}",
                {
                    "type": "payment.refunded",
                    "payment_id": payment.id,
                    "registration_id": payment.registration.id,
                    "tournament_id": payment.registration.tournament.id,
                    "reason": reason,
                    "timestamp": timezone.now().isoformat(),
                }
            )

