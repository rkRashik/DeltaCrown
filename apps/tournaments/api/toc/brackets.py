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
from rest_framework.parsers import FormParser, MultiPartParser
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
    """
    S5-B2: POST /api/toc/<slug>/brackets/reset/

    Body: ``{"force": true|false}`` (optional, default false)

    Response codes:
    * 200 — reset succeeded
    * 409 ``code='fixtures_in_progress'`` — matches are dirty; frontend must
      prompt for admin force-confirm and retry with ``{"force": true}``
    * 403 ``code='force_requires_admin'`` — force was attempted by a
      non-admin actor (organizer cannot override the safety gate)
    * 423 ``code='tournament_finalized'`` — tournament is COMPLETED/ARCHIVED;
      no reset path available, frontend must offer Archive-and-Clone
    """

    def post(self, request, slug):
        from apps.tournaments.api.toc.brackets_service import FixtureResetBlockedError

        body  = request.data if isinstance(request.data, dict) else {}
        force = bool(body.get("force"))
        try:
            data = TOCBracketsService.reset_bracket(
                self.tournament, request.user, force=force
            )
        except FixtureResetBlockedError as exc:
            status_code = {
                "fixtures_in_progress":  status.HTTP_409_CONFLICT,
                "force_requires_admin":  status.HTTP_403_FORBIDDEN,
                "tournament_finalized":  status.HTTP_423_LOCKED,
            }.get(exc.code, status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status_code,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics', 'standings')
        return Response(data)


class BracketFormatConfigView(TOCBaseView):
    """
    GET / POST /api/toc/<slug>/brackets/format-config/

    Read or save format-specific options (rounds, advancement, tiebreakers, etc.)
    onto ``tournament.config['format_options']``. The option keys vary per
    format and are merged into the strategy's ``generate_fixtures(options)``
    call, so generation reflects the saved settings.

    Body: arbitrary dict of format option keys (validated per-format below).
    """

    # Whitelist of option keys per format — anything else is ignored to prevent
    # config injection.
    ALLOWED_KEYS = {
        'round_robin': {
            'rounds',                 # 1 (single RR) or 2 (double RR)
            'advancement_count',      # top N advance to next stage
            'points_system',          # {"win": 3, "draw": 1, "loss": 0}
            'tiebreaker_rules',       # ordered list of tiebreaker keys
            'match_format',           # 'bo1' | 'bo3' | 'bo5'
        },
        'swiss': {
            'total_rounds',
            'tiebreaker_rules',
            'drop_after_losses',
        },
        'single_elimination': {
            'third_place_match_enabled',
            'seeding_method',
        },
        'double_elimination': {
            'seeding_method',
            'grand_final_reset_enabled',
        },
        'group_playoff': set(),  # group_playoff uses the legacy /groups/configure/ endpoint
        'battle_royale': {
            'scoring_matrix',
            'lobbies_per_match_day',
            'advancement_count',
            'tiebreaker_rules',
            'is_screenshot_required',
        },
    }

    def get(self, request, slug):
        config = (self.tournament.config or {}) if isinstance(self.tournament.config, dict) else {}
        return Response({
            'tournament_format': self.tournament.format,
            'format_options': config.get('format_options') or {},
        })

    def post(self, request, slug):
        body = request.data if isinstance(request.data, dict) else {}
        fmt = self.tournament.format
        allowed = self.ALLOWED_KEYS.get(fmt, set())

        # Filter to whitelist
        cleaned = {k: v for k, v in body.items() if k in allowed}

        # Coerce rounds to int 1..2 for RR, else reject
        if fmt == 'round_robin' and 'rounds' in cleaned:
            try:
                rounds = int(cleaned['rounds'])
                if rounds not in (1, 2):
                    return Response({"error": "rounds must be 1 (single RR) or 2 (double RR)."}, status=status.HTTP_400_BAD_REQUEST)
                cleaned['rounds'] = rounds
            except (TypeError, ValueError):
                return Response({"error": "rounds must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if 'advancement_count' in cleaned:
            try:
                ac = int(cleaned['advancement_count'])
                if ac < 1:
                    return Response({"error": "advancement_count must be >= 1."}, status=status.HTTP_400_BAD_REQUEST)
                cleaned['advancement_count'] = ac
            except (TypeError, ValueError):
                return Response({"error": "advancement_count must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if 'is_screenshot_required' in cleaned:
            cleaned['is_screenshot_required'] = bool(cleaned['is_screenshot_required'])

        config = dict(self.tournament.config or {})
        existing = dict(config.get('format_options') or {})
        existing.update(cleaned)
        config['format_options'] = existing
        self.tournament.config = config
        self.tournament.save(update_fields=['config'])

        bump_toc_scopes(self.tournament.id, 'brackets', 'overview')
        return Response({
            'tournament_format': fmt,
            'format_options': existing,
            'updated_keys': list(cleaned.keys()),
        })


class BracketBRScoreEntryView(TOCBaseView):
    """
    POST /api/toc/<slug>/brackets/br-score-entry/

    Submit per-team placement + kills for a single Battle Royale lobby session.

    Body:
        {
            "match_id": 1234,                         # the lobby session Match
            "results": [
                {"participant_id": 99, "placement": 1, "kills": 12},
                {"participant_id": 88, "placement": 2, "kills": 8},
                ...
            ],
            "map_name":      "Erangel"   # optional, persisted onto Match.lobby_info
        }

    Response (200):
        {"status": "applied", "match_id": ..., "rows_applied": N, "winner_id": ...}

    Errors:
        400  validation failure (invalid results, wrong tournament, etc.)
        409  match not in a state where results can be applied
    """

    def post(self, request, slug):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.br_scoring_service import BRScoringService

        body = request.data if isinstance(request.data, dict) else {}
        match_id = body.get("match_id")
        results  = body.get("results")
        map_name = (body.get("map_name") or "").strip()

        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            return Response({"error": "match_id is required and must be int."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            match = Match.objects.get(
                id=match_id,
                tournament=self.tournament,
                is_deleted=False,
            )
        except Match.DoesNotExist:
            return Response({"error": "Lobby session not found."},
                            status=status.HTTP_404_NOT_FOUND)

        info = match.lobby_info or {}
        if not info.get("br_session"):
            return Response(
                {"error": "This match is not a Battle Royale lobby session."},
                status=status.HTTP_409_CONFLICT,
            )

        # Persist optional metadata before scoring (so failures still save the map name).
        if map_name and map_name != info.get("map_name"):
            info["map_name"] = map_name
            match.lobby_info = info
            match.save(update_fields=["lobby_info"])

        try:
            data = BRScoringService.apply_lobby_results(match, results)
        except (ValueError, ValidationError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'standings', 'analytics')
        return Response(data)


class BracketBRScreenshotExtractView(TOCBaseView):
    """
    POST /api/toc/<slug>/brackets/br-score-screenshot/

    AI-assisted score entry. Admin uploads an end-of-match screenshot from a
    Battle Royale game (PUBG Mobile / FreeFire). The pipeline:

        1. Validates the uploaded match is a BR lobby session.
        2. Pushes the image to Supabase Storage as a temporary audit copy.
        3. Calls Gemini Vision with the bytes + a candidate participant list.
        4. Deletes the Supabase object (best-effort, in finally).
        5. Returns parsed ``{results, map_name}`` so the admin can review/edit
           in the grid before the actual submission to ``br-score-entry/``.

    This endpoint does NOT mutate the leaderboard. It's a read-only AI helper.
    The follow-up POST to ``/brackets/br-score-entry/`` is where results are
    actually applied.

    Request (multipart/form-data):
        match_id   : int     (the BR lobby Match)
        screenshot : file    (image: jpg / png / webp)

    Responses:
        200  → {"results": [...], "map_name": "...", "audit": {...}}
        400  → bad input / no candidates / empty upload
        404  → match not found in this tournament
        409  → match is not a BR lobby session
        422  → Gemini failed to return parseable JSON (frontend should fall
               back to the manual grid)
        503  → server is missing GEMINI_API_KEY / SUPABASE_* env vars
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.br_screenshot_service import (
            BRScreenshotConfigError,
            BRScreenshotError,
            BRScreenshotExtractionError,
            BRScreenshotUploadError,
            process_br_screenshot,
        )

        # Parse match_id from form-data (it arrives as string).
        match_id_raw = request.data.get("match_id")
        try:
            match_id = int(match_id_raw)
        except (TypeError, ValueError):
            return Response({"error": "match_id is required and must be int."},
                            status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("screenshot")
        if upload is None:
            return Response({"error": "screenshot file is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Hard ceiling — protect 512MB Render container from large uploads.
        max_bytes = 8 * 1024 * 1024
        if getattr(upload, "size", 0) and upload.size > max_bytes:
            return Response(
                {"error": f"Screenshot too large (max {max_bytes // (1024 * 1024)} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match = Match.objects.get(
                id=match_id,
                tournament=self.tournament,
                is_deleted=False,
            )
        except Match.DoesNotExist:
            return Response({"error": "Lobby session not found."},
                            status=status.HTTP_404_NOT_FOUND)

        info = match.lobby_info or {}
        if not info.get("br_session"):
            return Response(
                {"error": "This match is not a Battle Royale lobby session."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            image_bytes = upload.read()
        except Exception as exc:
            return Response(
                {"error": f"Could not read uploaded file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = process_br_screenshot(
                tournament=self.tournament,
                match=match,
                image_bytes=image_bytes,
                content_type=getattr(upload, "content_type", "") or "image/jpeg",
                original_filename=getattr(upload, "name", "") or "",
            )
        except BRScreenshotConfigError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except BRScreenshotExtractionError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except BRScreenshotUploadError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except BRScreenshotError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Echo the match_id back so the frontend can pre-select it on the grid.
        data["match_id"] = match.id
        data["session_number"] = (match.lobby_info or {}).get("session_number")
        return Response(data)


class BracketSportsScreenshotExtractView(TOCBaseView):
    """
    POST /api/toc/<slug>/brackets/sports-score-screenshot/

    AI-assisted score entry for 1v1 sports games (eFootball / EA SPORTS FC 26)
    in any bracket-style format (SE / DE / RR / Swiss / GP). Admin uploads a
    final-whistle result screen; pipeline:

        1. Validates the match belongs to this tournament and is NOT a BR
           lobby session (those use ``br-score-screenshot/`` instead).
        2. Pushes the image to Supabase Storage as a temporary audit copy.
        3. Calls Gemini Vision with a strict-shape prompt + the two
           participant names as hints.
        4. Deletes the Supabase object (best-effort, in finally).
        5. Fuzzy-maps home/away → participant1/participant2 using
           ``difflib.SequenceMatcher``. Returns ``mapping_confidence`` so the
           frontend can decide whether to auto-fill or just suggest.

    This endpoint is read-only. The follow-up POST to ``matches/<pk>/score/``
    is where scores actually land.

    Request (multipart/form-data):
        match_id   : int     (the SE/DE/RR/Swiss/GP Match)
        screenshot : file    (image: jpg / png / webp)

    Responses:
        200  → {
                 "match_id": ...,
                 "home_team": "...", "home_score": ..., "away_team": "...", "away_score": ...,
                 "participant1_name": "...", "participant1_score": <int|None>,
                 "participant2_name": "...", "participant2_score": <int|None>,
                 "mapping_confidence": "high"|"low"|"none",
                 "audit": { ... }
               }
        400  → bad input / empty upload
        404  → match not found in this tournament
        409  → match is a BR lobby session (use the BR endpoint instead)
        422  → Gemini failed to return parseable JSON / hallucinated scores
        502  → Supabase upload failed
        503  → server is missing GEMINI_API_KEY / SUPABASE_* env vars
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.sports_screenshot_service import (
            SportsScreenshotConfigError,
            SportsScreenshotError,
            SportsScreenshotExtractionError,
            SportsScreenshotUploadError,
            process_sports_screenshot,
        )

        match_id_raw = request.data.get("match_id")
        try:
            match_id = int(match_id_raw)
        except (TypeError, ValueError):
            return Response({"error": "match_id is required and must be int."},
                            status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("screenshot")
        if upload is None:
            return Response({"error": "screenshot file is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Same 8 MB ceiling as the BR endpoint — protect the 512 MB Render box
        # from oversized uploads.
        max_bytes = 8 * 1024 * 1024
        if getattr(upload, "size", 0) and upload.size > max_bytes:
            return Response(
                {"error": f"Screenshot too large (max {max_bytes // (1024 * 1024)} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match = Match.objects.get(
                id=match_id,
                tournament=self.tournament,
                is_deleted=False,
            )
        except Match.DoesNotExist:
            return Response({"error": "Match not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # Refuse BR lobby sessions — they use the dedicated BR endpoint that
        # operates on a leaderboard candidate list, not p1/p2 slots.
        info = match.lobby_info or {}
        if info.get("br_session"):
            return Response(
                {"error": "This match is a Battle Royale lobby session. Use /brackets/br-score-screenshot/ instead.",
                 "code": "not_a_sports_match"},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            image_bytes = upload.read()
        except Exception as exc:
            return Response(
                {"error": f"Could not read uploaded file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = process_sports_screenshot(
                tournament=self.tournament,
                match=match,
                image_bytes=image_bytes,
                content_type=getattr(upload, "content_type", "") or "image/jpeg",
                original_filename=getattr(upload, "name", "") or "",
            )
        except SportsScreenshotConfigError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SportsScreenshotExtractionError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except SportsScreenshotUploadError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except SportsScreenshotError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(data)


class BracketTeam5v5ScreenshotExtractView(TOCBaseView):
    """
    POST /api/toc/<slug>/brackets/team-5v5-score-screenshot/

    AI-assisted score + KDA entry for 5v5 team formats (MLBB, Valorant, CS2,
    CoD). Admin uploads an end-of-match scoreboard; pipeline:

        1. Validates the match belongs to this tournament and is NOT a BR
           lobby session.
        2. Pushes the image to Supabase Storage as a temporary audit copy
           under ``team_5v5/...``.
        3. Calls Gemini Vision with both teams' rosters as hints.
        4. Deletes the Supabase object (best-effort, in finally).
        5. Fuzzy-maps team_a/team_b → participant1/participant2 using
           ``difflib.SequenceMatcher``; per-team, fuzzy-maps each AI player
           row to a user_id on that team's starter roster.

    Read-only — admin reviews + corrects in the TOC grid before submitting
    the actual score via ``matches/<pk>/score/`` (and per-player KDA via the
    series / stats endpoints).

    Request (multipart/form-data):
        match_id   : int     (the SE/DE/RR/Swiss/GP team match)
        screenshot : file    (image: jpg / png / webp)

    Responses:
        200  → see ``process_team_5v5_screenshot`` for the full shape
        400  → bad input / empty upload
        404  → match not found in this tournament
        409  → match is a BR lobby session (use the BR endpoint instead)
        422  → Gemini failed to return parseable JSON / hallucinated values
        502  → Supabase upload failed
        503  → server is missing GEMINI_API_KEY / SUPABASE_* env vars
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.team_5v5_screenshot_service import (
            Team5v5ScreenshotConfigError,
            Team5v5ScreenshotError,
            Team5v5ScreenshotExtractionError,
            Team5v5ScreenshotUploadError,
            process_team_5v5_screenshot,
        )

        match_id_raw = request.data.get("match_id")
        try:
            match_id = int(match_id_raw)
        except (TypeError, ValueError):
            return Response({"error": "match_id is required and must be int."},
                            status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("screenshot")
        if upload is None:
            return Response({"error": "screenshot file is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        max_bytes = 8 * 1024 * 1024
        if getattr(upload, "size", 0) and upload.size > max_bytes:
            return Response(
                {"error": f"Screenshot too large (max {max_bytes // (1024 * 1024)} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match = Match.objects.get(
                id=match_id,
                tournament=self.tournament,
                is_deleted=False,
            )
        except Match.DoesNotExist:
            return Response({"error": "Match not found."},
                            status=status.HTTP_404_NOT_FOUND)

        info = match.lobby_info or {}
        if info.get("br_session"):
            return Response(
                {"error": "This match is a Battle Royale lobby session. Use /brackets/br-score-screenshot/ instead.",
                 "code": "not_a_team_match"},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            image_bytes = upload.read()
        except Exception as exc:
            return Response(
                {"error": f"Could not read uploaded file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = process_team_5v5_screenshot(
                tournament=self.tournament,
                match=match,
                image_bytes=image_bytes,
                content_type=getattr(upload, "content_type", "") or "image/jpeg",
                original_filename=getattr(upload, "name", "") or "",
            )
        except Team5v5ScreenshotConfigError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Team5v5ScreenshotExtractionError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Team5v5ScreenshotUploadError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Team5v5ScreenshotError as exc:
            return Response(
                {"error": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
