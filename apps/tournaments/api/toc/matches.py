"""
TOC API Views — Sprint 6: Match Operations + Sprint 9: Verification.

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
S9-B1  GET  matches/<id>/detail/
S9-B2  POST matches/<id>/verify/
"""

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes, toc_cache_key
from apps.tournaments.api.toc.matches_service import TOCMatchesService


def _is_finalized_tournament(tournament) -> bool:
    return str(getattr(tournament, 'status', '') or '').lower() in {'completed', 'archived'}


class MatchListView(TOCBaseView):
    """S6-B1: Paginated match list with filters."""

    def get(self, request, slug):
        round_raw = request.query_params.get('round')
        round_number = None
        if round_raw not in (None, ''):
            try:
                round_number = int(round_raw)
            except (TypeError, ValueError):
                round_number = None

        page_raw = request.query_params.get('page')
        page = 1
        if page_raw not in (None, ''):
            try:
                page = int(page_raw)
            except (TypeError, ValueError):
                page = 1

        page_size_raw = request.query_params.get('page_size')
        page_size = 60
        if page_size_raw not in (None, ''):
            try:
                page_size = int(page_size_raw)
            except (TypeError, ValueError):
                page_size = 60

        cache_bucket = int(timezone.now().timestamp() // 8)
        query_sig = request.META.get('QUERY_STRING', '')
        cache_key = toc_cache_key('matches', self.tournament.id, cache_bucket, query_sig)
        use_cache = not _is_finalized_tournament(self.tournament)
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
        else:
            cache.delete(cache_key)

        result = TOCMatchesService.get_matches(
            self.tournament,
            round_number=round_number,
            state=request.query_params.get('state'),
            search=request.query_params.get('search'),
            group=request.query_params.get('group'),
            stage=request.query_params.get('stage'),
            page=page,
            page_size=page_size,
        )
        if use_cache:
            cache.set(cache_key, result, timeout=12)
        return Response(result)


class MatchScoreView(TOCBaseView):
    """S6-B2: Submit / override score."""

    def post(self, request, slug, pk):
        try:
            p1_score = int(request.data.get('participant1_score', 0))
            p2_score = int(request.data.get('participant2_score', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'participant1_score and participant2_score must be integers'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if p1_score < 0 or p2_score < 0:
            return Response({'error': 'Scores must be non-negative'}, status=status.HTTP_400_BAD_REQUEST)

        winner_side = None
        winner_side_raw = request.data.get('winner_side', None)
        if winner_side_raw not in (None, ''):
            token = str(winner_side_raw).strip().lower()
            if token in {'1', 'a', 'p1', 'participant1', 'left', 'team1'}:
                winner_side = 1
            elif token in {'2', 'b', 'p2', 'participant2', 'right', 'team2'}:
                winner_side = 2
            elif token in {'draw', 'tie', 'd'}:
                winner_side = 'draw'
            else:
                return Response(
                    {'error': 'winner_side must be one of: a, b, 1, 2, draw'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        football_stats = request.data.get('football_stats')
        if football_stats is not None and not isinstance(football_stats, dict):
            return Response(
                {'error': 'football_stats must be an object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = TOCMatchesService.submit_score(
                match_id=pk,
                tournament=self.tournament,
                p1_score=p1_score,
                p2_score=p2_score,
                user_id=request.user.id,
                winner_side=winner_side,
                football_stats=football_stats,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        bump_toc_scopes(self.tournament.id, 'matches', 'brackets', 'overview', 'analytics')
        return Response(data)


class MatchMarkLiveView(TOCBaseView):
    """S6-B3: Mark match as live."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.mark_live(pk, self.tournament)
        bump_toc_scopes(self.tournament.id, 'matches', 'overview', 'analytics')
        return Response(data)


class MatchPauseView(TOCBaseView):
    """S6-B4: Pause match (Match Medic)."""

    def post(self, request, slug, pk):
        try:
            data = TOCMatchesService.pause_match(pk, self.tournament)
            bump_toc_scopes(self.tournament.id, 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MatchResumeView(TOCBaseView):
    """S6-B5: Resume paused match."""

    def post(self, request, slug, pk):
        try:
            data = TOCMatchesService.resume_match(pk, self.tournament)
            bump_toc_scopes(self.tournament.id, 'matches', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MatchForceCompleteView(TOCBaseView):
    """S6-B6: Force-complete match."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.force_complete(pk, self.tournament, user_id=request.user.id)
        bump_toc_scopes(self.tournament.id, 'matches', 'brackets', 'overview', 'analytics')
        return Response(data)


class MatchResetView(TOCBaseView):
    """Reset scores and match verification artifacts."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.reset_match(pk, self.tournament, user_id=request.user.id)
        bump_toc_scopes(self.tournament.id, 'matches', 'disputes', 'overview', 'analytics')
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
        bump_toc_scopes(self.tournament.id, 'matches', 'overview', 'analytics')
        return Response(data, status=status.HTTP_201_CREATED)


class MatchForfeitView(TOCBaseView):
    """S6-B8: Declare forfeit."""

    def post(self, request, slug, pk):
        try:
            forfeiter_id = int(request.data.get('forfeiter_id'))
        except (TypeError, ValueError):
            return Response({'error': 'forfeiter_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = TOCMatchesService.forfeit_match(
                match_id=pk,
                tournament=self.tournament,
                forfeiter_id=forfeiter_id,
                user_id=request.user.id,
            )
            bump_toc_scopes(self.tournament.id, 'matches', 'brackets', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MatchNoteView(TOCBaseView):
    """S6-B9: Add match note."""

    def post(self, request, slug, pk):
        data = TOCMatchesService.add_note(
            match_id=pk,
            tournament=self.tournament,
            text=request.data.get('text', ''),
            user_id=request.user.id,
        )
        bump_toc_scopes(self.tournament.id, 'matches')
        return Response(data)


class MatchMediaView(TOCBaseView):
    """S6-B10: List and upload match media."""

    def get(self, request, slug, pk):
        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('matches', self.tournament.id, 'media', pk, cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCMatchesService.get_media(pk, self.tournament)
        payload = {'media': data}
        cache.set(cache_key, payload, timeout=12)
        return Response(payload)

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
        bump_toc_scopes(self.tournament.id, 'matches', 'disputes')
        return Response(data, status=status.HTTP_201_CREATED)


# ── Sprint 9: Match Verification Split-Screen ────────────────


class MatchDetailView(TOCBaseView):
    """S9-B1: Composite match detail (submissions, media, disputes, notes)."""

    def get(self, request, slug, pk):
        try:
            cache_bucket = int(timezone.now().timestamp() // 8)
            cache_key = toc_cache_key('matches', self.tournament.id, 'detail', pk, cache_bucket)
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            data = TOCMatchesService.get_match_detail(pk, self.tournament)
            cache.set(cache_key, data, timeout=12)
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


class MatchVerifyView(TOCBaseView):
    """S9-B2: Verification action (confirm / dispute / note)."""

    def post(self, request, slug, pk):
        action = request.data.get('action')
        if action not in ('confirm', 'dispute', 'note'):
            return Response(
                {'error': 'action must be confirm, dispute, or note'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        p1_score = None
        p2_score = None
        if action in ('confirm', 'dispute'):
            raw_p1 = request.data.get('participant1_score')
            raw_p2 = request.data.get('participant2_score')
            try:
                p1_score = int(raw_p1)
                p2_score = int(raw_p2)
            except (TypeError, ValueError):
                return Response(
                    {'error': 'participant1_score and participant2_score must be integers'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if p1_score < 0 or p2_score < 0:
                return Response(
                    {'error': 'Scores must be non-negative'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            data = TOCMatchesService.verify_match(
                match_id=pk,
                tournament=self.tournament,
                action=action,
                user_id=request.user.id,
                p1_score=p1_score,
                p2_score=p2_score,
                notes=request.data.get('notes', ''),
                reason_code=request.data.get('reason_code', 'other'),
            )
            bump_toc_scopes(self.tournament.id, 'matches', 'brackets', 'disputes', 'overview', 'analytics')
            return Response(data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------------------------------------------------
# Series (BO3/BO5) endpoints
# ------------------------------------------------------------------

class MatchSeriesStatusView(TOCBaseView):
    """GET /api/toc/{slug}/matches/{pk}/series/ — Return series status."""

    def get(self, request, slug, pk):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.match_service import MatchService

        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('matches', self.tournament.id, 'series_status', pk, cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            match = Match.objects.get(pk=pk, tournament=self.tournament, is_deleted=False)
        except Match.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)
        data = MatchService.get_series_status(match)
        cache.set(cache_key, data, timeout=12)
        return Response(data)

    def patch(self, request, slug, pk):
        """PATCH /series/ with {best_of: 1|3|5} to set series format."""
        from apps.tournaments.models.match import Match
        try:
            match = Match.objects.get(pk=pk, tournament=self.tournament, is_deleted=False)
        except Match.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)
        best_of = request.data.get('best_of')
        if best_of not in (1, 3, 5):
            return Response({'error': 'best_of must be 1, 3, or 5'}, status=status.HTTP_400_BAD_REQUEST)
        match.best_of = best_of
        match.save(update_fields=['best_of'])
        from apps.tournaments.services.match_service import MatchService
        bump_toc_scopes(self.tournament.id, 'matches')
        return Response(MatchService.get_series_status(match))


class MatchSeriesGameView(TOCBaseView):
    """POST /api/toc/{slug}/matches/{pk}/series/game/ — Submit a single game score."""

    def post(self, request, slug, pk):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.match_service import MatchService
        from django.core.exceptions import ValidationError
        try:
            match = Match.objects.get(pk=pk, tournament=self.tournament, is_deleted=False)
        except Match.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            game_number = int(request.data.get('game_number', 0))
            p1_score = int(request.data.get('participant1_score', 0))
            p2_score = int(request.data.get('participant2_score', 0))
            match = MatchService.submit_game_score(
                match=match,
                game_number=game_number,
                participant1_score=p1_score,
                participant2_score=p2_score,
                submitted_by_id=request.user.id,
            )
            bump_toc_scopes(self.tournament.id, 'matches', 'overview', 'analytics')
            return Response(MatchService.get_series_status(match))
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError) as e:
            return Response({'error': f'Invalid data: {e}'}, status=status.HTTP_400_BAD_REQUEST)


class MatchSubmissionOCRScanView(TOCBaseView):
    """
    POST /api/toc/<slug>/matches/<pk>/submissions/<sub_id>/scan/

    P3 — Admin-triggered OCR scan of a participant-uploaded result
    screenshot. Routes the file through the appropriate screenshot
    service based on game category, persists extraction results on the
    submission row (``ocr_status`` / ``ocr_extracted`` / etc.), and
    returns a summary for the FE to display.

    Pass ``?force=1`` to re-run even when status is already 'completed'.
    No automatic match-state advancement happens here — staff decides.
    """

    def post(self, request, slug, pk, sub_id):
        from apps.tournaments.models.match import Match
        from apps.tournaments.models.result_submission import MatchResultSubmission
        from apps.tournaments.services.ocr_pipeline import run_ocr_for_submission

        try:
            match = Match.objects.get(pk=pk, tournament=self.tournament, is_deleted=False)
        except Match.DoesNotExist:
            return Response({"error": "Match not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            submission = MatchResultSubmission.objects.get(pk=sub_id, match=match)
        except MatchResultSubmission.DoesNotExist:
            return Response({"error": "Submission not found for this match."},
                            status=status.HTTP_404_NOT_FOUND)

        force = str(request.GET.get("force") or request.data.get("force") or "").strip().lower() in {"1", "true", "yes"}
        try:
            result = run_ocr_for_submission(submission.id, force=force)
        except Exception as exc:
            return Response({"error": f"OCR pipeline failed: {exc}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        bump_toc_scopes(self.tournament.id, "matches")
        return Response(result)


class MatchTeam5v5RostersView(TOCBaseView):
    """
    GET /api/toc/<slug>/matches/<pk>/team-5v5-rosters/

    Returns the candidate starter rosters for both teams on a 5v5 team match,
    so the TOC KDA grid can populate its user-picker dropdowns *before* (or
    independently of) running the AI OCR. Same shape as the
    ``participant{1,2}_candidates`` arrays in the OCR response.

    Also returns previously-saved ``MatchPlayerStat`` rows under
    ``participant{1,2}_players`` (same shape as the OCR response's player
    arrays) so the grid pre-fills with stored stats on revisit. Empty arrays
    when nothing has been saved yet — the frontend treats them as "no AI run".

    Response 200:
        {
          "match_id": <int>,
          "participant1_id":   <int|None>,
          "participant1_name": "<str>",
          "participant2_id":   <int|None>,
          "participant2_name": "<str>",
          "participant1_candidates": [{"user_id": <int>, "label": "<str>"}, ...],
          "participant2_candidates": [{"user_id": <int>, "label": "<str>"}, ...],
          "participant1_players":    [{"user_id": <int>, "agent": "<str>", "kills": <int>, ...}, ...],
          "participant2_players":    [...]
        }
    """

    def get(self, request, slug, pk):
        from apps.tournaments.models.match import Match
        from apps.tournaments.models.match_player_stats import MatchPlayerStat
        from apps.tournaments.services.team_5v5_screenshot_service import (
            build_team_rosters,
        )

        try:
            match = Match.objects.get(
                id=int(pk),
                tournament=self.tournament,
                is_deleted=False,
            )
        except (Match.DoesNotExist, TypeError, ValueError):
            return Response({"error": "Match not found."},
                            status=status.HTTP_404_NOT_FOUND)

        team1, team2 = build_team_rosters(
            tournament=self.tournament,
            participant1_id=match.participant1_id,
            participant2_id=match.participant2_id,
        )

        # Pre-load saved stats — split by team_id so the grid panels can pre-fill.
        # Order matches the table default (-acs) so the highest-impact row shows
        # at the top of each panel, like a real scoreboard.
        saved = list(MatchPlayerStat.objects.filter(match=match).order_by('-acs'))

        def _serialize(team_id):
            out = []
            for s in saved:
                if s.team_id != team_id:
                    continue
                extra = s.extra_stats if isinstance(s.extra_stats, dict) else {}
                out.append({
                    "user_id":     s.player_id,
                    "agent":       s.agent or "",
                    "kills":       s.kills,
                    "deaths":      s.deaths,
                    "assists":     s.assists,
                    "acs":         int(s.acs),
                    "econ":        int(extra.get("econ") or 0),
                    "fb":          s.first_kills,
                    "plants":      s.plants,
                    "defuses":     s.defuses,
                    # The grid uses this to decide whether to render the row
                    # "locked" (green border). Saved stats are always locked.
                    "mapping_confidence": "high",
                })
            return out

        return Response({
            "match_id":                match.id,
            "participant1_id":         match.participant1_id,
            "participant1_name":       match.participant1_name or "",
            "participant2_id":         match.participant2_id,
            "participant2_name":       match.participant2_name or "",
            "participant1_candidates": team1,
            "participant2_candidates": team2,
            "participant1_players":    _serialize(match.participant1_id),
            "participant2_players":    _serialize(match.participant2_id),
        })


class MatchTeam5v5PlayerStatsView(TOCBaseView):
    """
    POST /api/toc/<slug>/matches/<pk>/team-5v5-player-stats/

    Persists the per-player KDA grid for a 5v5 team match. The request body is
    the grid state — same shape as the OCR response's ``participant{1,2}_players``
    arrays — and replaces all existing ``MatchPlayerStat`` rows for this match
    in a single transaction. The grid IS the source of truth; if the admin
    removed a row, it goes away.

    Request body:
        {
          "participant1_players": [
            {"user_id": <int>, "agent": "<str>", "kills": <int>, "deaths": <int>,
             "assists": <int>, "acs": <int>, "econ": <int>, "fb": <int>,
             "plants": <int>, "defuses": <int>},
            ... up to 5
          ],
          "participant2_players": [... up to 5]
        }

    Rows without a ``user_id`` are silently skipped (the admin left the
    dropdown empty — no DB identity to persist against). The unique
    constraint is (match, player), so each user appears at most once per side.

    Response 200:
        {
          "match_id": <int>,
          "saved_count": <int>,        # total rows actually written
          "participant1_saved": <int>, # per-side breakdown
          "participant2_saved": <int>
        }
    """

    # Field-by-field clamps mirror the OCR validator ceilings. Anything higher
    # is operator error, not a real game.
    _MAX_KDA = 99
    _MAX_ACS = 200_000  # MLBB gold can hit ~30k; Valorant ACS ~400 — give headroom.

    def _clamp_int(self, raw, low, high):
        try:
            n = int(raw or 0)
        except (TypeError, ValueError):
            return low
        if n < low:
            return low
        if n > high:
            return high
        return n

    def post(self, request, slug, pk):
        from django.db import transaction
        from apps.tournaments.models.match import Match
        from apps.tournaments.models.match_player_stats import MatchPlayerStat

        try:
            match = Match.objects.get(
                id=int(pk),
                tournament=self.tournament,
                is_deleted=False,
            )
        except (Match.DoesNotExist, TypeError, ValueError):
            return Response({"error": "Match not found."},
                            status=status.HTTP_404_NOT_FOUND)

        body = request.data if isinstance(request.data, dict) else {}
        p1_raw = body.get("participant1_players") or []
        p2_raw = body.get("participant2_players") or []
        if not isinstance(p1_raw, list) or not isinstance(p2_raw, list):
            return Response(
                {"error": "participant1_players and participant2_players must be lists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _normalize(rows, team_id):
            """Yield (player_id, row_dict) for valid rows; skip those without a user_id."""
            seen_users = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    user_id = int(row.get("user_id") or 0)
                except (TypeError, ValueError):
                    continue
                if user_id <= 0 or user_id in seen_users:
                    continue
                seen_users.add(user_id)

                # ``econ`` has no first-class column; route it through extra_stats.
                # Keep any pre-existing JSON the admin might have set elsewhere — but
                # since we replace the whole row, just start fresh.
                extra = {"econ": self._clamp_int(row.get("econ"), 0, self._MAX_KDA)}
                yield user_id, {
                    "team_id":     team_id,
                    "agent":       str(row.get("agent") or "")[:30],
                    "kills":       self._clamp_int(row.get("kills"),   0, self._MAX_KDA),
                    "deaths":      self._clamp_int(row.get("deaths"),  0, self._MAX_KDA),
                    "assists":     self._clamp_int(row.get("assists"), 0, self._MAX_KDA),
                    "acs":         self._clamp_int(row.get("acs"),     0, self._MAX_ACS),
                    "first_kills": self._clamp_int(row.get("fb"),      0, self._MAX_KDA),
                    "plants":      self._clamp_int(row.get("plants"),  0, self._MAX_KDA),
                    "defuses":     self._clamp_int(row.get("defuses"), 0, self._MAX_KDA),
                    "extra_stats": extra,
                }

        p1_rows = list(_normalize(p1_raw, match.participant1_id))
        p2_rows = list(_normalize(p2_raw, match.participant2_id))

        # Cross-side dedupe — same user can't appear on both teams in one match.
        # Drop conflicts from side 2 (side 1 wins on tie; admin can re-pick).
        side1_users = {uid for uid, _ in p1_rows}
        p2_rows = [(uid, payload) for uid, payload in p2_rows if uid not in side1_users]

        with transaction.atomic():
            MatchPlayerStat.objects.filter(match=match).delete()
            created = 0
            for uid, payload in p1_rows + p2_rows:
                MatchPlayerStat.objects.create(
                    match=match,
                    player_id=uid,
                    **payload,
                )
                created += 1

        return Response({
            "match_id":           match.id,
            "saved_count":        created,
            "participant1_saved": len(p1_rows),
            "participant2_saved": len(p2_rows),
        })
