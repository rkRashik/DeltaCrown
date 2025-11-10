"""
Certificate API Views - Module 5.3

API endpoints for certificate download and verification.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-53
- Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md#sprint-6
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer

Module: apps.tournaments.api.certificate_views
Implements: phase_5:module_5_3:milestone_3
"""

import logging
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.tournaments.models import Certificate
from apps.tournaments.services.certificate_service import certificate_service
from apps.tournaments.api.certificate_serializers import (
    CertificateSerializer,
    VerificationSerializer,
)

logger = logging.getLogger(__name__)


# Custom permission for certificate download
class IsParticipantOrOrganizerOrAdmin:
    """
    Allow certificate download for:
    - Certificate owner (participant user)
    - Tournament organizer
    - Admin/staff users
    
    This is inline with the view since it's specific to certificates.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access this certificate."""
        # Staff/superuser have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Tournament organizer has access
        if obj.tournament.organizer_id == request.user.id:
            return True
        
        # Certificate owner (participant) has access
        if obj.participant.user_id == request.user.id:
            return True
        
        return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_certificate(request, pk):
    """
    Download certificate file (PDF or PNG).
    
    GET /api/tournaments/certificates/<id>/
    
    Permissions: Owner (participant), Organizer, or Admin
    
    Query Parameters:
        format: 'pdf' (default) or 'png'
    
    Response:
        - 200 OK: File download with appropriate headers
        - 401 Unauthorized: User not authenticated
        - 403 Forbidden: User not authorized to download this certificate
        - 404 Not Found: Certificate does not exist
    
    Headers:
        Content-Type: application/pdf or image/png
        Content-Disposition: attachment; filename="certificate-<code>.pdf"
        ETag: "<sha256-hash>"
        Cache-Control: private, max-age=300
    """
    # Get certificate
    try:
        certificate = Certificate.objects.select_related(
            'tournament', 'participant__user'
        ).get(pk=pk)
    except Certificate.DoesNotExist:
        return Response(
            {"detail": "Certificate not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions manually (since we're not using a viewset)
    permission_checker = IsParticipantOrOrganizerOrAdmin()
    if not permission_checker.has_object_permission(request, None, certificate):
        return Response(
            {"detail": "You do not have permission to download this certificate."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if certificate is revoked
    if certificate.is_revoked:
        return Response(
            {
                "detail": "This certificate has been revoked and cannot be downloaded.",
                "revoked": True,
                "revoked_reason": certificate.revoked_reason,
            },
            status=status.HTTP_410_GONE
        )
    
    # Get requested format (default: pdf)
    file_format = request.query_params.get('format', 'pdf').lower()
    
    if file_format == 'png':
        file_field = certificate.file_image
        content_type = 'image/png'
        extension = 'png'
    else:
        file_field = certificate.file_pdf
        content_type = 'application/pdf'
        extension = 'pdf'
    
    # Check if file exists
    if not file_field or not file_field.name:
        return Response(
            {"detail": f"Certificate {extension.upper()} file not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Open file
        file_field.open('rb')
        
        # Increment download counter (only on first download or if never downloaded)
        if not certificate.downloaded_at:
            certificate.downloaded_at = timezone.now()
            certificate.download_count = 1
        else:
            certificate.download_count += 1
        certificate.save(update_fields=['downloaded_at', 'download_count'])
        
        # Generate filename
        code_short = str(certificate.verification_code).split('-')[0]
        filename = f"certificate-{code_short}.{extension}"
        
        # Create response with file
        response = FileResponse(
            file_field,
            content_type=content_type,
        )
        
        # Set headers
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['ETag'] = f'"{certificate.certificate_hash}"'
        response['Cache-Control'] = 'private, max-age=300'
        
        logger.info(
            f"Certificate {certificate.id} downloaded by user {request.user.id} "
            f"(format: {extension}, download_count: {certificate.download_count})"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading certificate {certificate.id}: {e}")
        return Response(
            {"detail": "Error accessing certificate file."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def verify_certificate(request, code):
    """
    Verify certificate authenticity by verification code.
    
    GET /api/tournaments/certificates/verify/<uuid>/
    
    Permissions: AllowAny (public endpoint)
    
    Response (200 OK):
        {
            "valid": true/false,
            "certificate_id": 123,
            "tournament": "Tournament Name",
            "participant_display_name": "John Doe",
            "certificate_type": "Winner Certificate",
            "placement": "1",
            "generated_at": "2025-11-10T10:30:00Z",
            "revoked": false,
            "revoked_reason": null,
            "is_tampered": false,
            "verification_url": "https://deltacrown.com/api/..."
        }
    
    Response (404 Not Found):
        {
            "detail": "Certificate not found."
        }
    
    Notes:
        - No PII exposed (only display names)
        - valid=false if revoked or tampered
        - Status 200 even if invalid (details in body)
    """
    try:
        # Verify certificate using service
        verification_data = certificate_service.verify_certificate(code)
        
        # Serialize response
        serializer = VerificationSerializer(verification_data)
        
        # Return 200 even if invalid (details in body indicate validity)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except DjangoValidationError as e:
        # Certificate not found
        logger.info(f"Verification failed for code {code}: {str(e)}")
        return Response(
            {"detail": "Certificate not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error verifying certificate {code}: {e}")
        return Response(
            {"detail": "Error verifying certificate."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
