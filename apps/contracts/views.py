"""Missions API views."""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.economy.exceptions import InsufficientFunds

from .models import ContractEnrollment, ContractProofSubmission, ContractTemplate
from .serializers import (
    ContractEnrollmentSerializer,
    ContractProofSubmissionSerializer,
    ContractProofSubmitSerializer,
    ContractTemplateSerializer,
)
from .services import ContractService


logger = logging.getLogger(__name__)


class ContractTemplateListView(APIView):
    """``GET /api/v1/contracts/templates/`` — list active Mission catalog."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        game_id = request.query_params.get('game')
        qs = ContractTemplate.objects.filter(is_active=True).select_related('game')
        if game_id:
            qs = qs.filter(game_id=game_id)

        # Hide templates outside their valid_from/valid_until window.
        templates = [t for t in qs if t.is_currently_available]
        return Response(ContractTemplateSerializer(templates, many=True).data)


class ContractEnrollView(APIView):
    """``POST /api/v1/contracts/enroll/<id>/`` — pay entry fee + start Mission."""

    permission_classes = [IsAuthenticated]

    def post(self, request, template_id):
        template = get_object_or_404(
            ContractTemplate.objects.select_related('game'),
            pk=template_id,
        )
        try:
            enrollment = ContractService.enroll(
                user=request.user,
                template=template,
            )
        except InsufficientFunds as e:
            return Response(
                {'detail': str(e), 'code': 'INSUFFICIENT_FUNDS'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ContractEnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )


class ContractEnrollmentDetailView(APIView):
    """``GET /api/v1/contracts/enrollments/<id>/`` — single Mission enrollment state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, enrollment_id):
        enrollment = get_object_or_404(
            ContractEnrollment.objects.select_related('user', 'template', 'template__game'),
            pk=enrollment_id,
        )
        # Owner-only read access.
        if enrollment.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'detail': 'Not allowed.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(ContractEnrollmentSerializer(enrollment).data)


class ContractProofListCreateView(APIView):
    """``GET|POST /api/v1/contracts/enrollments/<id>/proofs/``."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, enrollment_id):
        enrollment = get_object_or_404(
            ContractEnrollment.objects.select_related('user'),
            pk=enrollment_id,
        )
        if enrollment.user_id != request.user.id and not request.user.is_staff:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        proofs = ContractProofSubmission.objects.filter(enrollment=enrollment).select_related(
            'enrollment', 'submitted_by', 'reviewed_by'
        )
        return Response(ContractProofSubmissionSerializer(proofs, many=True).data)

    def post(self, request, enrollment_id):
        serializer = ContractProofSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proof = ContractService.submit_proof(
                enrollment_id=enrollment_id,
                user=request.user,
                proof_url=serializer.validated_data.get('proof_url', ''),
                notes=serializer.validated_data.get('notes', ''),
                proof_file=serializer.validated_data.get('proof_file'),
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ContractProofSubmissionSerializer(proof).data,
            status=status.HTTP_201_CREATED,
        )


class MyEnrollmentsView(APIView):
    """``GET /api/v1/contracts/my/`` — list the current user's Mission enrollments."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = ContractEnrollment.objects.filter(user=request.user).select_related(
            'template', 'template__game'
        )
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return Response(
            ContractEnrollmentSerializer(qs[:50], many=True).data
        )
