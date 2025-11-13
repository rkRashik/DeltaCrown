# apps/tournaments/api/matches.py
from rest_framework import status, permissions, viewsets, decorators
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .serializers_matches import (
    MatchSerializer,
    MatchStartSerializer,
    MatchConfirmResultSerializer,
    MatchSubmitResultSerializer,
    MatchDisputeSerializer,
    MatchResolveDisputeSerializer,
    MatchCancelSerializer,
)
from ..models import Match, Dispute


class IsParticipant(permissions.BasePermission):
    """Allow access only if user is a participant in the match."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user is participant1 or participant2 (via their ID)."""
        # For solo tournaments: participant_id = user.id
        # For team tournaments: participant_id = team.id (check if user is team captain/member)
        # Simplified: check if user.id matches participant IDs (solo case)
        # For team case, would need to query Team model
        return (
            obj.participant1_id == request.user.id or
            obj.participant2_id == request.user.id
        )


class IsStaff(permissions.BasePermission):
    """Staff-only permission for moderation actions."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for match lifecycle management.
    
    Supports idempotency via Idempotency-Key header.
    State machine: SCHEDULED → LIVE → PENDING_RESULT → COMPLETED
    
    Staff actions: start, confirm_result, resolve_dispute, cancel
    Participant actions: submit_result, dispute
    """
    
    queryset = Match.objects.select_related('tournament').all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter matches by tournament/round if provided."""
        qs = super().get_queryset()
        
        tournament_id = self.request.query_params.get('tournament')
        round_no = self.request.query_params.get('round')
        
        if tournament_id:
            qs = qs.filter(tournament_id=tournament_id)
        if round_no:
            qs = qs.filter(round_number=round_no)
        
        return qs
    
    def _apply_idempotency(self, request, match, op_name):
        """
        Apply idempotency logic using Idempotency-Key header.
        
        Returns: (previous_result, is_replay)
        """
        key = request.headers.get("Idempotency-Key")
        if not key:
            return None, False
        
        # Store idempotency key in lobby_info JSON field
        idem_data = match.lobby_info.get('idempotency', {})
        last_op = idem_data.get('last_op')
        last_key = idem_data.get('last_key')
        
        if last_op == op_name and last_key == key:
            # Replay detected
            return match, True
        
        # Store new operation
        match.lobby_info['idempotency'] = {
            'last_op': op_name,
            'last_key': key,
            'timestamp': timezone.now().isoformat()
        }
        match.save(update_fields=['lobby_info', 'updated_at'])
        return None, False
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="start",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def start(self, request, pk=None):
        """
        POST /matches/{id}/start/
        
        Staff starts match. Transitions SCHEDULED → LIVE.
        Idempotent.
        """
        match = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "start")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if match.state not in ('scheduled', 'ready'):
            return Response(
                {"detail": f"Invalid state transition from {match.state} to live"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Transition to LIVE
        match.state = 'live'
        match.started_at = timezone.now()
        match.save(update_fields=['state', 'started_at', 'updated_at'])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="submit-result",
        permission_classes=[IsParticipant]
    )
    @transaction.atomic
    def submit_result(self, request, pk=None):
        """
        POST /matches/{id}/submit-result/
        
        Participant submits result. Transitions LIVE → PENDING_RESULT.
        Requires: score, opponent_score
        """
        match = self.get_object()
        
        # Permission check (participant only)
        self.check_object_permissions(request, match)
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "submit_result")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if match.state != 'live':
            return Response(
                {"detail": f"Invalid state transition from {match.state} to pending_result"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = MatchSubmitResultSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Determine which side submitted
        if match.participant1_id == request.user.id:
            match.participant1_score = ser.validated_data['score']
            match.participant2_score = ser.validated_data['opponent_score']
        elif match.participant2_id == request.user.id:
            match.participant2_score = ser.validated_data['score']
            match.participant1_score = ser.validated_data['opponent_score']
        else:
            return Response(
                {"detail": "Not a participant in this match"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Store evidence if provided
        if ser.validated_data.get('evidence'):
            match.lobby_info['result_evidence'] = ser.validated_data['evidence']
        if ser.validated_data.get('notes'):
            match.lobby_info['result_notes'] = ser.validated_data['notes']
        
        # Transition to PENDING_RESULT
        match.state = 'pending_result'
        match.save(update_fields=[
            'state', 'participant1_score', 'participant2_score',
            'lobby_info', 'updated_at'
        ])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="confirm-result",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def confirm_result(self, request, pk=None):
        """
        POST /matches/{id}/confirm-result/
        
        Staff confirms result. Transitions PENDING_RESULT → COMPLETED.
        Sets winner_id/loser_id.
        """
        match = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "confirm_result")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if match.state != 'pending_result':
            return Response(
                {"detail": f"Invalid state transition from {match.state} to completed"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Determine winner/loser
        if match.participant1_score > match.participant2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        elif match.participant2_score > match.participant1_score:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        else:
            # Tie - handle based on game rules (for now, fail)
            return Response(
                {"detail": "Cannot confirm tie - game rules require a winner"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Transition to COMPLETED
        match.state = 'completed'
        match.completed_at = timezone.now()
        match.save(update_fields=[
            'state', 'winner_id', 'loser_id', 'completed_at', 'updated_at'
        ])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="dispute",
        permission_classes=[IsParticipant]
    )
    @transaction.atomic
    def dispute(self, request, pk=None):
        """
        POST /matches/{id}/dispute/
        
        Participant files dispute. Transitions PENDING_RESULT → DISPUTED.
        """
        match = self.get_object()
        
        # Permission check (participant only)
        self.check_object_permissions(request, match)
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "dispute")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation (can dispute from PENDING_RESULT or COMPLETED within window)
        if match.state not in ('pending_result', 'completed'):
            return Response(
                {"detail": f"Invalid state transition from {match.state} to disputed"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = MatchDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Create dispute record
        reason_map = {
            'SCORE_MISMATCH': 'score_mismatch',
            'NO_SHOW': 'no_show',
            'CHEATING': 'cheating',
            'TECHNICAL_ISSUE': 'technical_issue',
            'OTHER': 'other'
        }
        
        Dispute.objects.create(
            match=match,
            initiated_by_id=request.user.id,
            reason=reason_map.get(ser.validated_data['reason_code'], 'other'),
            description=str(ser.validated_data.get('notes', {})),
            evidence_video_url=ser.validated_data.get('evidence', ''),
            status='open'
        )
        
        # Transition to DISPUTED
        match.state = 'disputed'
        match.save(update_fields=['state', 'updated_at'])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="resolve-dispute",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def resolve_dispute(self, request, pk=None):
        """
        POST /matches/{id}/resolve-dispute/
        
        Staff resolves dispute. Transitions DISPUTED → COMPLETED.
        """
        match = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "resolve_dispute")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # State validation
        if match.state != 'disputed':
            return Response(
                {"detail": f"Invalid state transition from {match.state} to completed (resolve)"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate input
        ser = MatchResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        decision = ser.validated_data['decision']
        
        # Apply decision
        if decision == 'OVERRIDE':
            match.participant1_score = ser.validated_data['final_score_a']
            match.participant2_score = ser.validated_data['final_score_b']
            
            # Set winner/loser
            if match.participant1_score > match.participant2_score:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
        
        elif decision == 'ACCEPT_REPORTED':
            # Keep current scores, set winner/loser
            if match.participant1_score > match.participant2_score:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
        
        elif decision == 'REMATCH':
            # Reset to scheduled
            match.state = 'scheduled'
            match.participant1_score = 0
            match.participant2_score = 0
            match.save(update_fields=[
                'state', 'participant1_score', 'participant2_score', 'updated_at'
            ])
            
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": False}
            return Response(data, status=status.HTTP_200_OK)
        
        elif decision == 'DISQUALIFY':
            # Set to cancelled/forfeit
            match.state = 'cancelled'
            match.save(update_fields=['state', 'updated_at'])
            
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": False}
            return Response(data, status=status.HTTP_200_OK)
        
        # Update dispute records
        Dispute.objects.filter(match=match, status='open').update(
            status='resolved',
            resolved_by_id=request.user.id,
            resolved_at=timezone.now(),
            resolution_notes=str(ser.validated_data.get('notes', {}))
        )
        
        # Transition to COMPLETED
        match.state = 'completed'
        match.completed_at = timezone.now()
        match.save(update_fields=[
            'state', 'participant1_score', 'participant2_score',
            'winner_id', 'loser_id', 'completed_at', 'updated_at'
        ])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
    
    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        permission_classes=[IsStaff]
    )
    @transaction.atomic
    def cancel(self, request, pk=None):
        """
        POST /matches/{id}/cancel/
        
        Staff cancels match. Transitions ANY → CANCELLED.
        """
        match = self.get_object()
        
        # Idempotency check
        prev, replay = self._apply_idempotency(request, match, "cancel")
        if replay:
            data = MatchSerializer(match).data
            data["meta"] = {"idempotent_replay": True}
            return Response(data, status=status.HTTP_200_OK)
        
        # Validate input
        ser = MatchCancelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        # Store cancellation reason
        match.lobby_info['cancellation'] = {
            'reason_code': ser.validated_data['reason_code'],
            'notes': ser.validated_data.get('notes'),
            'cancelled_by': request.user.id,
            'cancelled_at': timezone.now().isoformat()
        }
        
        # Transition to CANCELLED
        match.state = 'cancelled'
        match.save(update_fields=['state', 'lobby_info', 'updated_at'])
        
        data = MatchSerializer(match).data
        data["meta"] = {"idempotent_replay": False}
        return Response(data, status=status.HTTP_200_OK)
