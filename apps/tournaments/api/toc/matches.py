"""
TOC API Views — Sprint 6: Match Operations.

S6-B1  GET  matches/
S6-B2  POST matches/<id>/score/
S6-B3  POST matches/<id>/mark-live/
S6-B4  POST matches/<id>/pause/
S6-B5  POST matches/<id>/resume/
S6-B6  POST matches/<id>/force-complete/
S6-B7  POST matches/<id>/reschedule/
S6-B8  POST matches/<id>/forfeit/
S6-B9  POST matches/<id>/add-note/
S6-B10 GET  matches/<id>/media/  + POST matches/<id>/media/
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.matches_service import TOCMatchesService


class MatchListView(TOCBaseView):
    """S6-B1: Paginated match list with filters."""

    def get(self, request, slug):
        data = TOCMatchesService.get_matches(
            self.tournament,
            round_number=request.query_params.get('round'),
            state=request.query_params.get('state'),
            search=request.query_params.get('search'),
        )
        return Response({'matches': data})


class MatchScoreView(TOCBaseView):
    """S6-B2: Submit / override score."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.submit_score(
            match_id=pk,
            tournament=self.tournament,
            p1_score=int(request.data.get('participant1_score', 0)),
            p2_score=int(request.data.get('participant2_score', 0)),
            user_id=request.user.id,
        )
        return Response(data)


class MatchMarkLiveView(TOCBaseView):
    """S6-B3: Mark match as live."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.mark_live(pk, self.tournament)
        return Response(data)


class MatchPauseView(TOCBaseView):
    """S6-B4: Pause match (Match Medic)."""

    def post(self, request, slug, pk):
        try:
            data = TOCMatchesService.pause_match(pk, self.tournament)
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MatchResumeView(TOCBaseView):
    """S6-B5: Resume paused match."""

    def post(self, request, slug, pk):
        try:
            data = TOCMatchesService.resume_match(pk, self.tournament)
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MatchForceCompleteView(TOCBaseView):
    """S6-B6: Force-complete match."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.force_complete(pk, self.tournament, user_id=request.user.id)
        return Response(data)


class MatchRescheduleView(TOCBaseView):
    """S6-B7: Request reschedule."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.request_reschedule(
            match_id=pk,
            tournament=self.tournament,
            new_time=request.data.get('new_time'),
            reason=request.data.get('reason', ''),
            user_id=request.user.id,
        )
        return Response(data, status=status.HTTP_201_CREATED)


class MatchForfeitView(TOCBaseView):
    """S6-B8: Declare forfeit."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.forfeit_match(
            match_id=pk,
            tournament=self.tournament,
            forfeiter_id=int(request.data.get('forfeiter_id')),
            user_id=request.user.id,
        )
        return Response(data)


class MatchNoteView(TOCBaseView):
    """S6-B9: Add match note."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.add_note(
            match_id=pk,
            tournament=self.tournament,
            text=request.data.get('text', ''),
            user_id=request.user.id,
        )
        return Response(data)


class MatchMediaView(TOCBaseView):
    """S6-B10: List and upload match media."""

    def get(self, request, slug, pk):
        data = TOCMatchesService.get_media(pk, self.tournament)
        return Response({'media': data})

    def post(self, request, slug, pk):
        data = TOCMatchesService.upload_media(
            match_id=pk,
            tournament=self.tournament,
            media_type=request.data.get('media_type', 'screenshot'),
            url=request.data.get('url', ''),
            description=request.data.get('description', ''),
            is_evidence=request.data.get('is_evidence', False),
            user_id=request.user.id,
        )
        return Response(data, status=status.HTTP_201_CREATED)
