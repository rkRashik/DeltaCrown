"""
TOC API — Participants Advanced Views.

Sprint 3: S3-B1 through S3-B8
Emergency Subs, Free Agent Pool, Waitlist, Guest Conversion, Fee Waivers.

All views inherit TOCBaseView for tournament lookup + permission check.
"""

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.participants_advanced_service import (
    TOCParticipantsAdvancedService,
)
from apps.tournaments.api.toc.serializers import (
    EmergencySubInputSerializer,
    EmergencySubRequestSerializer,
    EmergencySubReviewSerializer,
    FeeWaiverInputSerializer,
    FreeAgentAssignSerializer,
    FreeAgentSerializer,
    WaitlistEntrySerializer,
)


# ── S3-B1: Submit Emergency Sub ───────────────────────────────────


class EmergencySubSubmitView(TOCBaseView):
    """POST /api/toc/<slug>/participants/<pk>/emergency-sub/"""

    def post(self, request, slug, pk):
        ser = EmergencySubInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCParticipantsAdvancedService.submit_emergency_sub(
                self.tournament,
                registration_id=pk,
                requested_by=request.user,
                dropping_player_id=ser.validated_data["dropping_player_id"],
                substitute_player_id=ser.validated_data["substitute_player_id"],
                reason=ser.validated_data["reason"],
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B2: Approve / Deny Emergency Sub ──────────────────────────


class EmergencySubListView(TOCBaseView):
    """GET /api/toc/<slug>/emergency-subs/ — list all sub requests."""

    def get(self, request, slug):
        status_filter = request.query_params.get("status")
        try:
            results = TOCParticipantsAdvancedService.list_emergency_subs(
                self.tournament,
                status_filter=status_filter,
            )
            return Response({"results": results, "total": len(results)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmergencySubApproveView(TOCBaseView):
    """POST /api/toc/<slug>/emergency-subs/<sub_id>/approve/"""

    def post(self, request, slug, sub_id):
        ser = EmergencySubReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCParticipantsAdvancedService.approve_emergency_sub(
                self.tournament,
                sub_request_id=sub_id,
                reviewer=request.user,
                notes=ser.validated_data.get("notes", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmergencySubDenyView(TOCBaseView):
    """POST /api/toc/<slug>/emergency-subs/<sub_id>/deny/"""

    def post(self, request, slug, sub_id):
        ser = EmergencySubReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCParticipantsAdvancedService.deny_emergency_sub(
                self.tournament,
                sub_request_id=sub_id,
                reviewer=request.user,
                notes=ser.validated_data.get("notes", ""),
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B3: Free Agent Pool — List ────────────────────────────────


class FreeAgentListView(TOCBaseView):
    """GET /api/toc/<slug>/free-agents/"""

    def get(self, request, slug):
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        try:
            results = TOCParticipantsAdvancedService.list_free_agents(
                self.tournament,
                status_filter=status_filter,
                search=search,
            )
            return Response({"results": results, "total": len(results)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B4: Free Agent — Assign to Team ──────────────────────────


class FreeAgentAssignView(TOCBaseView):
    """POST /api/toc/<slug>/free-agents/<fa_id>/assign/"""

    def post(self, request, slug, fa_id):
        ser = FreeAgentAssignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCParticipantsAdvancedService.assign_free_agent(
                self.tournament,
                free_agent_id=fa_id,
                team_id=ser.validated_data["team_id"],
                assigned_by=request.user,
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B5: Manual Waitlist Promotion ─────────────────────────────


class WaitlistPromoteView(TOCBaseView):
    """POST /api/toc/<slug>/participants/<pk>/promote-waitlist/"""

    def post(self, request, slug, pk):
        try:
            result = TOCParticipantsAdvancedService.promote_waitlist(
                self.tournament,
                registration_id=pk,
                promoted_by=request.user,
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B6: Auto-Promote Waitlist ─────────────────────────────────


class WaitlistAutoPromoteView(TOCBaseView):
    """POST /api/toc/<slug>/participants/auto-promote/"""

    def post(self, request, slug):
        try:
            result = TOCParticipantsAdvancedService.auto_promote_waitlist(
                self.tournament,
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B7: Convert Guest Team ────────────────────────────────────


class ConvertGuestView(TOCBaseView):
    """POST /api/toc/<slug>/participants/<pk>/convert-guest/"""

    def post(self, request, slug, pk):
        try:
            result = TOCParticipantsAdvancedService.convert_guest_team(
                self.tournament,
                registration_id=pk,
                converted_by=request.user,
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── S3-B8: Fee Waiver ────────────────────────────────────────────


class FeeWaiverView(TOCBaseView):
    """POST /api/toc/<slug>/participants/<pk>/fee-waiver/"""

    def post(self, request, slug, pk):
        ser = FeeWaiverInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = TOCParticipantsAdvancedService.issue_fee_waiver(
                self.tournament,
                registration_id=pk,
                waived_by=request.user,
                reason=ser.validated_data["reason"],
            )
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── Waitlist List (helper endpoint for S3-F3 frontend) ───────────


class WaitlistListView(TOCBaseView):
    """GET /api/toc/<slug>/waitlist/"""

    def get(self, request, slug):
        try:
            results = TOCParticipantsAdvancedService.get_waitlist(self.tournament)
            return Response({"results": results, "total": len(results)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
