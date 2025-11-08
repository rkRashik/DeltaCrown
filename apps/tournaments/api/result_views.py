"""
Module 4.4: Result Submission & Confirmation API

REST API endpoints for match result submission, confirmation, and dispute creation.
Delegates all business logic to MatchService (ADR-001: Service Layer Pattern).

Endpoints:
1. POST /api/tournaments/matches/{id}/submit-result/ - Submit match result
2. POST /api/tournaments/matches/{id}/confirm-result/ - Confirm match result  
3. POST /api/tournaments/matches/{id}/report-dispute/ - Create dispute

Architecture:
- ADR-001: Service Layer (delegates to MatchService)
- ADR-005: Security (JWT auth, role-based permissions, audit logging)
- ADR-007: WebSocket (inherited from MatchService broadcast functions)
- Module 2.4: Audit logging for sensitive operations

WebSocket Events (inherited from MatchService):
- score_updated: Broadcast on submit_result
- match_completed: Broadcast on confirm_result
- dispute_created: Broadcast on report_dispute (TODO: not yet implemented in MatchService)

Planning Documents:
- PART_2.2_SERVICES_INTEGRATION.md#section-6-match-service
- PART_3.1_DATABASE_DESIGN_ERD.md#section-6.2-matchresult-model
- PART_3.1_DATABASE_DESIGN_ERD.md#section-6.3-dispute-model
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tournaments.models.match import Match, Dispute
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.api.result_serializers import (
    ResultSubmissionSerializer,
    ResultConfirmationSerializer,
    DisputeReportSerializer,
    MatchResultSerializer
)
from apps.tournaments.api.permissions import IsOrganizerOrAdmin, IsMatchParticipant
from apps.tournaments.security.audit import audit_event, AuditAction

logger = logging.getLogger(__name__)


class ResultViewSet(viewsets.GenericViewSet):
    """
    ViewSet for match result submission, confirmation, and dispute creation.
    
    All endpoints delegate to MatchService for business logic.
    
    Permissions:
    - submit_result: IsAuthenticated + IsMatchParticipant (participants only)
    - confirm_result: IsAuthenticated + (IsMatchParticipant or IsOrganizerOrAdmin)
    - report_dispute: IsAuthenticated + IsMatchParticipant (participants only)
    """
    
    queryset = Match.objects.select_related('tournament', 'bracket').filter(is_deleted=False)
    serializer_class = MatchResultSerializer
    permission_classes = [IsAuthenticated]
    
    @action(
        detail=True,
        methods=['post'],
        url_path='submit-result',
        permission_classes=[IsAuthenticated, IsMatchParticipant]
    )
    def submit_result(self, request, pk=None):
        """
        Submit match result.
        
        Endpoint: POST /api/tournaments/matches/{id}/submit-result/
        
        Request Body:
        {
            "participant1_score": 13,
            "participant2_score": 10,
            "notes": "Close game, great match",
            "evidence_url": "https://example.com/screenshot.png"
        }
        
        Permissions:
        - Submitter must be a participant in the match
        - Match must be in LIVE or PENDING_RESULT state
        
        Side Effects:
        - Updates match.participant1_score, match.participant2_score
        - Transitions match.state to PENDING_RESULT
        - Sets match.winner_id, match.loser_id
        - Broadcasts score_updated WebSocket event (Module 2.3)
        - Creates audit log (Module 2.4)
        
        Response:
        {
            "id": 1,
            "state": "PENDING_RESULT",
            "participant1_score": 13,
            "participant2_score": 10,
            "winner_id": 10,
            "submitted_by": 10,
            "message": "Result submitted successfully"
        }
        
        Errors:
        - 400: Validation error (invalid state, negative scores, tie)
        - 403: Forbidden (not a participant)
        - 404: Match not found
        """
        match = self.get_object()
        serializer = ResultSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        participant1_score = serializer.validated_data['participant1_score']
        participant2_score = serializer.validated_data['participant2_score']
        notes = serializer.validated_data.get('notes', '')
        evidence_url = serializer.validated_data.get('evidence_url', '')
        
        # Delegate to MatchService
        try:
            updated_match = MatchService.submit_result(
                match=match,
                submitted_by_id=request.user.id,
                participant1_score=participant1_score,
                participant2_score=participant2_score,
                notes=notes,
                evidence_url=evidence_url
            )
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.RESULT_SUBMIT,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'bracket_id': match.bracket_id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'participant1_score': participant1_score,
                    'participant2_score': participant2_score,
                    'winner_id': updated_match.winner_id,
                    'submitted_by': request.user.id,
                    'notes': notes,
                    'evidence_url': evidence_url
                }
            )
            
            return Response({
                'id': updated_match.id,
                'state': updated_match.state,
                'participant1_score': updated_match.participant1_score,
                'participant2_score': updated_match.participant2_score,
                'winner_id': updated_match.winner_id,
                'loser_id': updated_match.loser_id,
                'submitted_by': request.user.id,
                'message': 'Result submitted successfully. Awaiting confirmation from opponent or organizer.'
            }, status=status.HTTP_200_OK)
            
        except (DjangoValidationError, DRFValidationError) as e:
            logger.error(
                f"Result submission failed for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            # Convert Django ValidationError to DRF ValidationError
            if isinstance(e, DjangoValidationError):
                raise DRFValidationError({'error': str(e)})
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error submitting result for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            raise DRFValidationError({'error': 'An unexpected error occurred during result submission.'})
    
    @action(
        detail=True,
        methods=['post'],
        url_path='confirm-result',
        permission_classes=[IsAuthenticated]  # Will check IsMatchParticipant OR IsOrganizerOrAdmin in view
    )
    def confirm_result(self, request, pk=None):
        """
        Confirm match result.
        
        Endpoint: POST /api/tournaments/matches/{id}/confirm-result/
        
        Request Body:
        {}  (no body required)
        
        Permissions:
        - Confirmer must be:
          1. The opponent participant (not the submitter), OR
          2. Tournament organizer, OR
          3. Staff/admin
        - Match must be in PENDING_RESULT state
        
        Side Effects:
        - Transitions match.state to COMPLETED
        - Sets match.completed_at timestamp
        - Calls BracketService.update_bracket_after_match() (Module 1.5)
        - Broadcasts match_completed WebSocket event (Module 2.3)
        - Creates audit log (Module 2.4)
        
        Response:
        {
            "id": 1,
            "state": "COMPLETED",
            "winner_id": 10,
            "winner_name": "Team Alpha",
            "loser_id": 20,
            "loser_name": "Team Bravo",
            "participant1_score": 13,
            "participant2_score": 10,
            "completed_at": "2025-11-15T19:45:00Z",
            "confirmed_by": 20,
            "message": "Result confirmed successfully"
        }
        
        Errors:
        - 400: Validation error (invalid state, no result to confirm)
        - 403: Forbidden (not opponent/organizer/admin)
        - 404: Match not found
        """
        match = self.get_object()
        
        # Custom permission check: participant OR organizer/admin
        is_organizer_or_admin = (
            request.user.is_staff or
            request.user.is_superuser or
            match.tournament.organizer_id == request.user.id
        )
        is_participant = request.user.id in [match.participant1_id, match.participant2_id]
        
        if not (is_organizer_or_admin or is_participant):
            return Response(
                {'error': 'Only match participants, tournament organizers, or admins can confirm results.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ResultConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Delegate to MatchService
        try:
            updated_match = MatchService.confirm_result(
                match=match,
                confirmed_by_id=request.user.id
            )
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.RESULT_CONFIRM,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'bracket_id': match.bracket_id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'winner_id': updated_match.winner_id,
                    'loser_id': updated_match.loser_id,
                    'participant1_score': updated_match.participant1_score,
                    'participant2_score': updated_match.participant2_score,
                    'confirmed_by': request.user.id,
                    'completed_at': updated_match.completed_at.isoformat() if updated_match.completed_at else None
                }
            )
            
            return Response({
                'id': updated_match.id,
                'state': updated_match.state,
                'winner_id': updated_match.winner_id,
                'winner_name': (updated_match.participant1_name if updated_match.winner_id == updated_match.participant1_id 
                              else updated_match.participant2_name),
                'loser_id': updated_match.loser_id,
                'loser_name': (updated_match.participant2_name if updated_match.loser_id == updated_match.participant2_id 
                             else updated_match.participant1_name),
                'participant1_score': updated_match.participant1_score,
                'participant2_score': updated_match.participant2_score,
                'completed_at': updated_match.completed_at.isoformat() if updated_match.completed_at else None,
                'confirmed_by': request.user.id,
                'message': 'Result confirmed successfully. Match completed.'
            }, status=status.HTTP_200_OK)
            
        except (DjangoValidationError, DRFValidationError) as e:
            logger.error(
                f"Result confirmation failed for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            # Convert Django ValidationError to DRF ValidationError
            if isinstance(e, DjangoValidationError):
                raise DRFValidationError({'error': str(e)})
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error confirming result for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            raise DRFValidationError({'error': 'An unexpected error occurred during result confirmation.'})
    
    @action(
        detail=True,
        methods=['post'],
        url_path='report-dispute',
        permission_classes=[IsAuthenticated, IsMatchParticipant]
    )
    def report_dispute(self, request, pk=None):
        """
        Report dispute for match result.
        
        Endpoint: POST /api/tournaments/matches/{id}/report-dispute/
        
        Request Body:
        {
            "reason": "score_mismatch",
            "description": "Opponent reported incorrect score. Actual score was 13-10, not 13-11.",
            "evidence_video_url": "https://youtube.com/watch?v=abc123"
        }
        
        Permissions:
        - Reporter must be a participant in the match
        - Match must be in PENDING_RESULT or COMPLETED state
        - No active dispute must exist for this match
        
        Side Effects:
        - Creates Dispute record
        - Transitions match.state to DISPUTED
        - TODO: Broadcasts dispute_created WebSocket event (Module 2.3 - not yet in MatchService)
        - Creates audit log (Module 2.4)
        
        Response:
        {
            "dispute_id": 10,
            "match_id": 1,
            "tournament_id": 123,
            "reason": "score_mismatch",
            "description": "Opponent reported incorrect score...",
            "initiated_by": 20,
            "status": "OPEN",
            "created_at": "2025-11-15T19:50:00Z",
            "message": "Dispute created successfully"
        }
        
        Errors:
        - 400: Validation error (invalid state, active dispute exists)
        - 403: Forbidden (not a participant)
        - 404: Match not found
        """
        match = self.get_object()
        serializer = DisputeReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        reason = serializer.validated_data['reason']
        description = serializer.validated_data['description']
        evidence_screenshot = serializer.validated_data.get('evidence_screenshot')
        evidence_video_url = serializer.validated_data.get('evidence_video_url', '')
        
        # Delegate to MatchService
        try:
            dispute = MatchService.report_dispute(
                match=match,
                initiated_by_id=request.user.id,
                reason=reason,
                description=description,
                evidence_screenshot=evidence_screenshot,
                evidence_video_url=evidence_video_url
            )
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.DISPUTE_CREATE,
                meta={
                    'dispute_id': dispute.id,
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'bracket_id': match.bracket_id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'reason': reason,
                    'description': description,
                    'initiated_by': request.user.id,
                    'evidence_video_url': evidence_video_url,
                    'status': dispute.status
                }
            )
            
            return Response({
                'dispute_id': dispute.id,
                'match_id': match.id,
                'tournament_id': match.tournament_id,
                'reason': dispute.reason,
                'description': dispute.description,
                'initiated_by': dispute.initiated_by_id,
                'status': dispute.status,
                'created_at': dispute.created_at.isoformat() if hasattr(dispute, 'created_at') else None,
                'message': 'Dispute created successfully. Tournament organizers will review and resolve.'
            }, status=status.HTTP_201_CREATED)
            
        except (DjangoValidationError, DRFValidationError) as e:
            logger.error(
                f"Dispute creation failed for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            # Convert Django ValidationError to DRF ValidationError
            if isinstance(e, DjangoValidationError):
                raise DRFValidationError({'error': str(e)})
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error creating dispute for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'user_id': request.user.id}
            )
            raise DRFValidationError({'error': 'An unexpected error occurred during dispute creation.'})
