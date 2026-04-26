"""
TOC Brackets & Competition Engine API Views — Sprint 5.

S5-B1  POST  brackets/generate/       — Generate bracket
S5-B2  POST  brackets/reset/          — Reset bracket
S5-B3  POST  brackets/publish/        — Publish bracket
S5-B4  PUT   brackets/seeds/          — Reorder seeding
S5-B5  GET   brackets/                — Current bracket state
S5-B6  POST  schedule/auto-generate/  — Auto-schedule
S5-B7  POST  schedule/bulk-shift/     — Bulk shift times
S5-B8  POST  schedule/add-break/      — Insert break
S5-B9  GET   schedule/                — Full schedule
S5-B10       groups/                  — Group stage CRUD
S5-B11       pipelines/               — Qualifier pipeline CRUD
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .base import TOCBaseView
from .cache_utils import bump_toc_scopes, toc_cache_key
from .brackets_service import GroupMatchGenerationError, TOCBracketsService
from .serializers import (
    AutoScheduleInputSerializer,
    BreakInsertInputSerializer,
    BulkShiftInputSerializer,
    GroupConfigInputSerializer,
    GroupDrawInputSerializer,
    GroupMatchGenerateInputSerializer,
    PipelineCreateInputSerializer,
    ScheduleReminderInputSerializer,
    SeedReorderInputSerializer,
)


# ── Bracket endpoints ──────────────────────────────────────────

def _is_finalized_tournament(tournament) -> bool:
    return str(getattr(tournament, 'status', '') or '').lower() in {'completed', 'archived'}


class BracketGetView(TOCBaseView):
    """S5-B5: GET /api/toc/<slug>/brackets/"""

    def get(self, request, slug):
        cache_key = toc_cache_key('brackets', self.tournament.id, 'bracket')
        use_cache = not _is_finalized_tournament(self.tournament)
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
        else:
            cache.delete(cache_key)

        data = TOCBracketsService.get_bracket(self.tournament)
        if use_cache:
            cache.set(cache_key, data, timeout=300)
        return Response(data)


class BracketGenerateView(TOCBaseView):
    """S5-B1: POST /api/toc/<slug>/brackets/generate/"""

    def post(self, request, slug):
        try:
            payload = request.data if isinstance(request.data, dict) else {}
            data = TOCBracketsService.generate_bracket(
                self.tournament, request.user, payload
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data, status=status.HTTP_201_CREATED)
        except (ValueError, Exception) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class BracketResetView(TOCBaseView):
    """S5-B2: POST /api/toc/<slug>/brackets/reset/"""

    def post(self, request, slug):
        data = TOCBracketsService.reset_bracket(self.tournament, request.user)
        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
        return Response(data)


class BracketBronzeCreateView(TOCBaseView):
    """POST /api/toc/<slug>/brackets/bronze/create/"""

    def post(self, request, slug):
        try:
            data = TOCBracketsService.create_bronze_match(
                self.tournament,
                request.user,
            )
            bump_toc_scopes(
                self.tournament.id,
                'brackets',
                'matches',
                'overview',
                'analytics',
                'standings',
                'prizes',
            )
            cache.delete(f'public_prize_overview_v1_{self.tournament.id}')
            cache.delete(f'public_prize_overview_v2_{self.tournament.id}')
            return Response(data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class BracketPublishView(TOCBaseView):
    """S5-B3: POST /api/toc/<slug>/brackets/publish/"""

    def post(self, request, slug):
        try:
            data = TOCBracketsService.publish_bracket(
                self.tournament, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class BracketSeedsView(TOCBaseView):
    """S5-B4: PUT /api/toc/<slug>/brackets/seeds/"""

    def put(self, request, slug):
        ser = SeedReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.reorder_seeds(
                self.tournament, ser.validated_data["seeds"], request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'participants', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ── Schedule endpoints ─────────────────────────────────────────

class ScheduleGetView(TOCBaseView):
    """S5-B9: GET /api/toc/<slug>/schedule/"""

    def get(self, request, slug):
        cache_key = toc_cache_key('brackets', self.tournament.id, 'schedule')
        use_cache = not _is_finalized_tournament(self.tournament)
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
        else:
            cache.delete(cache_key)

        data = TOCBracketsService.get_schedule(self.tournament)
        if use_cache:
            cache.set(cache_key, data, timeout=300)
        return Response(data)


class ScheduleExportICSView(TOCBaseView):
    """
    GET /api/toc/<slug>/schedule/export.ics
    Sprint 29A: Download tournament schedule as iCalendar (.ics) file.
    Each scheduled match becomes a VEVENT with participant names, round, and stream URL.
    """

    def get(self, request, slug):
        from django.http import HttpResponse
        from django.utils import timezone as tz
        import uuid

        tournament = self.tournament
        data = TOCBracketsService.get_schedule(tournament)

        # Build iCalendar
        now_stamp = tz.now().strftime('%Y%m%dT%H%M%SZ')
        t_name = tournament.name or tournament.slug
        base_url = request.build_absolute_uri(f'/tournaments/{slug}/')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//DeltaCrown//TOC Schedule//EN',
            f'X-WR-CALNAME:{_ics_escape(t_name)} Schedule',
            'X-WR-CALDESC:Tournament match schedule exported from DeltaCrown',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
        ]

        any_event = False
        for match in data.get('matches', []):
            scheduled_raw = match.get('scheduled_time')
            if not scheduled_raw:
                continue  # Skip unscheduled matches

            any_event = True
            p1 = match.get('participant1_name') or 'TBD'
            p2 = match.get('participant2_name') or 'TBD'
            rn = match.get('round_number') or 0
            mn = match.get('match_number') or 0
            state = match.get('state', 'scheduled')
            stream_url = match.get('stream_url') or ''
            group_name = match.get('group_name') or ''
            match_id = match.get('id', str(uuid.uuid4()))

            # Parse start time
            try:
                from datetime import datetime, timezone as dt_tz, timedelta
                # Handle both naive and aware ISO strings
                dt = datetime.fromisoformat(scheduled_raw.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=dt_tz.utc)
                dt_end = dt + timedelta(hours=1)
                dtstart = dt.strftime('%Y%m%dT%H%M%SZ')
                dtend = dt_end.strftime('%Y%m%dT%H%M%SZ')
            except Exception:
                continue

            round_label = f'R{rn}' if rn else 'Round'
            group_tag = f' [{_ics_escape(group_name)}]' if group_name else ''
            summary = f'{round_label} M{mn}{group_tag}: {_ics_escape(p1)} vs {_ics_escape(p2)}'

            desc_parts = [
                f'Tournament: {_ics_escape(t_name)}',
                f'Round {rn}, Match {mn}',
                f'Status: {state}',
            ]
            if group_name:
                desc_parts.append(f'Group: {_ics_escape(group_name)}')
            if stream_url:
                desc_parts.append(f'Stream: {stream_url}')
            description = '\\n'.join(desc_parts)

            uid = f'match-{match_id}@deltacrown'

            lines += [
                'BEGIN:VEVENT',
                f'UID:{uid}',
                f'DTSTAMP:{now_stamp}',
                f'DTSTART:{dtstart}',
                f'DTEND:{dtend}',
                f'SUMMARY:{summary}',
                f'DESCRIPTION:{description}',
                f'URL:{stream_url or base_url}',
                'END:VEVENT',
            ]

        if not any_event:
            # Add a single placeholder event so calendar apps don't reject the file
            lines += [
                'BEGIN:VEVENT',
                f'UID:no-schedule-{tournament.slug}@deltacrown',
                f'DTSTAMP:{now_stamp}',
                'DTSTART;VALUE=DATE:' + tz.now().strftime('%Y%m%d'),
                'SUMMARY:No scheduled matches yet',
                f'DESCRIPTION:Schedule for {_ics_escape(t_name)} has not been set.',
                'END:VEVENT',
            ]

        lines.append('END:VCALENDAR')

        ics_content = '\r\n'.join(lines) + '\r\n'
        filename = f"{tournament.slug}_schedule.ics"
        response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def _ics_escape(text: str) -> str:
    """Escape special characters for iCalendar text fields."""
    if not text:
        return ''
    return str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


class ScheduleAutoGenerateView(TOCBaseView):
    """S5-B6: POST /api/toc/<slug>/schedule/auto-generate/"""

    def post(self, request, slug):
        ser = AutoScheduleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.auto_schedule(
            self.tournament, ser.validated_data, request.user
        )
        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
        return Response(data)


class ScheduleSendRemindersView(TOCBaseView):
    """POST /api/toc/<slug>/schedule/send-reminders/"""

    def post(self, request, slug):
        ser = ScheduleReminderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.send_match_reminders(
                self.tournament,
                ser.validated_data,
                request.user,
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ScheduleParticipantRescheduleSettingsView(TOCBaseView):
    """GET/PUT /api/toc/<slug>/schedule/participant-rescheduling/"""

    def get(self, request, slug):
        data = TOCBracketsService.get_participant_reschedule_settings(self.tournament)
        return Response(data)

    def put(self, request, slug):
        try:
            data = TOCBracketsService.update_participant_reschedule_settings(
                self.tournament,
                request.data if isinstance(request.data, dict) else {},
                request.user,
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ScheduleBulkShiftView(TOCBaseView):
    """S5-B7: POST /api/toc/<slug>/schedule/bulk-shift/"""

    def post(self, request, slug):
        ser = BulkShiftInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.bulk_shift(
                self.tournament, ser.validated_data, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ScheduleAddBreakView(TOCBaseView):
    """S5-B8: POST /api/toc/<slug>/schedule/add-break/"""

    def post(self, request, slug):
        ser = BreakInsertInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.add_break(
            self.tournament, ser.validated_data, request.user
        )
        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
        return Response(data)


class ScheduleRescheduleMatchView(TOCBaseView):
    """S27-B1: POST /api/toc/<slug>/schedule/<pk>/reschedule/"""

    def post(self, request, slug, pk):
        try:
            data = TOCBracketsService.reschedule_match(
                self.tournament, pk, request.data, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ScheduleManualMatchView(TOCBaseView):
    """S27: POST /api/toc/<slug>/schedule/<pk>/manual/ — manually schedule a match."""

    def post(self, request, slug, pk):
        try:
            data = TOCBracketsService.manual_schedule_match(
                self.tournament, pk, request.data, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ── Group Stage endpoints ──────────────────────────────────────

class GroupStageView(TOCBaseView):
    """S5-B10: GET /api/toc/<slug>/groups/"""

    def get(self, request, slug):
        cache_key = toc_cache_key('brackets', self.tournament.id, 'groups')
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCBracketsService.get_groups(self.tournament)
        cache.set(cache_key, data, timeout=300)
        return Response(data)


class GroupConfigureView(TOCBaseView):
    """S5-B10: POST /api/toc/<slug>/groups/configure/"""

    def post(self, request, slug):
        ser = GroupConfigInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.configure_groups(
                self.tournament, ser.validated_data, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except (ValueError, Exception) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupDrawView(TOCBaseView):
    """S5-B10: POST /api/toc/<slug>/groups/draw/"""

    def post(self, request, slug):
        ser = GroupDrawInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.draw_groups(
                self.tournament, ser.validated_data, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupGenerateMatchesView(TOCBaseView):
    """Sprint 30: POST /api/toc/<slug>/groups/generate-matches/."""

    def post(self, request, slug):
        ser = GroupMatchGenerateInputSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.generate_group_matches(
                self.tournament,
                ser.validated_data,
                request.user,
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data, status=status.HTTP_201_CREATED)
        except GroupMatchGenerationError as e:
            payload = {
                "error": str(e),
                "code": e.code,
                "details": e.details,
            }
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            payload = {"error": str(e)}
            if hasattr(e, "message_dict") and isinstance(e.message_dict, dict):
                payload = {
                    "error": e.message_dict.get("error", [str(e)])[0] if isinstance(e.message_dict.get("error"), list) else e.message_dict.get("error", str(e)),
                    "details": e.message_dict,
                }
            elif hasattr(e, "messages") and isinstance(e.messages, list) and e.messages:
                payload = {
                    "error": str(e.messages[0]),
                    "details": e.messages,
                }
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupResetView(TOCBaseView):
    """Sprint 29: POST /api/toc/<slug>/groups/reset/"""

    def post(self, request, slug):
        try:
            data = TOCBracketsService.reset_groups(
                self.tournament, request.user
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupStandingsView(TOCBaseView):
    """S5-B10: GET /api/toc/<slug>/groups/standings/"""

    def get(self, request, slug):
        cache_key = toc_cache_key('brackets', self.tournament.id, 'group_standings')
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCBracketsService.get_group_standings(self.tournament)
        cache.set(cache_key, data, timeout=300)
        return Response(data)


# ── Qualifier Pipeline endpoints ───────────────────────────────

class PipelineListCreateView(TOCBaseView):
    """S5-B11: GET/POST /api/toc/<slug>/pipelines/"""

    def get(self, request, slug):
        cache_key = toc_cache_key('brackets', self.tournament.id, 'pipelines')
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCBracketsService.list_pipelines(self.tournament)
        cache.set(cache_key, data, timeout=300)
        return Response(data)

    def post(self, request, slug):
        ser = PipelineCreateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.create_pipeline(
            self.tournament, ser.validated_data, request.user
        )
        bump_toc_scopes(self.tournament.id, 'brackets', 'overview', 'analytics')
        return Response(data, status=status.HTTP_201_CREATED)


class PipelineDetailView(TOCBaseView):
    """S5-B11: PATCH/DELETE /api/toc/<slug>/pipelines/<id>/"""

    def patch(self, request, slug, pipeline_id):
        try:
            data = TOCBracketsService.update_pipeline(
                self.tournament, str(pipeline_id), request.data
            )
            bump_toc_scopes(self.tournament.id, 'brackets', 'overview', 'analytics')
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, slug, pipeline_id):
        TOCBracketsService.delete_pipeline(
            self.tournament, str(pipeline_id)
        )
        bump_toc_scopes(self.tournament.id, 'brackets', 'overview', 'analytics')
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------
# Swiss System endpoints
# ------------------------------------------------------------------

class SwissStandingsView(TOCBaseView):
    """GET /api/toc/{slug}/swiss/standings/ — Current Swiss standings."""

    def get(self, request, slug):
        from apps.tournaments.models.bracket import Bracket
        from apps.tournaments.services.swiss_service import SwissService

        cache_key = toc_cache_key('brackets', self.tournament.id, 'swiss_standings')
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            bracket = Bracket.objects.get(tournament=self.tournament, format=Bracket.SWISS)
        except Bracket.DoesNotExist:
            return Response({"error": "No Swiss bracket found for this tournament."}, status=status.HTTP_404_NOT_FOUND)
        standings = SwissService.get_standings(bracket)
        structure = bracket.bracket_structure or {}
        payload = {
            "bracket_id": bracket.id,
            "current_round": structure.get("current_round", 1),
            "total_rounds": bracket.total_rounds,
            "standings": standings,
        }
        cache.set(cache_key, payload, timeout=300)
        return Response(payload)


class SwissAdvanceRoundView(TOCBaseView):
    """POST /api/toc/{slug}/swiss/advance-round/ — Advance to next Swiss round."""

    def post(self, request, slug):
        from apps.tournaments.models.bracket import Bracket
        from apps.tournaments.services.swiss_service import SwissService
        from django.core.exceptions import ValidationError
        try:
            bracket = Bracket.objects.get(tournament=self.tournament, format=Bracket.SWISS)
        except Bracket.DoesNotExist:
            return Response({"error": "No Swiss bracket found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            bracket = SwissService.generate_next_round(bracket)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        structure = bracket.bracket_structure or {}
        standings = SwissService.get_standings(bracket)
        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics')
        return Response({
            "bracket_id": bracket.id,
            "current_round": structure.get("current_round", 1),
            "total_rounds": bracket.total_rounds,
            "standings": standings,
            "message": f"Advanced to Round {structure.get('current_round', '?')}",
        })
