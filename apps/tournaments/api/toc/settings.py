"""
TOC API Views — Sprint 8: Settings & Configuration.

S8-B1 GET/PUT  settings/               — Tournament settings CRUD
S8-B2 GET/PUT  settings/game-config/   — Game match config
S8-B3 GET/POST settings/map-pool/      — Map pool list / add
S8-B3 PUT/DEL  settings/map-pool/<id>/ — Map update / delete
S8-B3 POST     settings/map-pool/reorder/ — Reorder maps
S8-B4 GET/POST settings/veto/<match_id>/ — Veto session read/create
S8-B4 POST     settings/veto/<match_id>/advance/ — Advance veto step
S8-B5 GET/POST settings/regions/       — Server region list / save
S8-B5 DELETE   settings/regions/<id>/  — Delete region
S8-B6 GET/POST settings/rulebook/      — Rulebook version list / create
S8-B6 PUT      settings/rulebook/<id>/ — Update version
S8-B6 POST     settings/rulebook/<id>/publish/ — Publish version
S8-B7 GET/PUT  settings/br-scoring/    — BR scoring matrix
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.settings_service import TOCSettingsService


# ------------------------------------------------------------------
# S8-B1: Tournament Settings
# ------------------------------------------------------------------

class SettingsView(TOCBaseView):
    """GET tournament settings / PUT to update."""

    def get(self, request, slug):
        data = TOCSettingsService.get_settings(self.tournament)
        return Response(data)

    def put(self, request, slug):
        result = TOCSettingsService.update_settings(self.tournament, request.data)
        return Response(result)


# ------------------------------------------------------------------
# S8-B2: Game Match Config
# ------------------------------------------------------------------

class GameConfigView(TOCBaseView):
    """GET game config / PUT to save."""

    def get(self, request, slug):
        data = TOCSettingsService.get_game_config(self.tournament)
        return Response(data or {})

    def put(self, request, slug):
        result = TOCSettingsService.save_game_config(self.tournament, request.data)
        return Response(result)


# ------------------------------------------------------------------
# S8-B3: Map Pool Management
# ------------------------------------------------------------------

class MapPoolListView(TOCBaseView):
    """GET map pool / POST to add map."""

    def get(self, request, slug):
        data = TOCSettingsService.get_map_pool(self.tournament)
        return Response(data)

    def post(self, request, slug):
        result = TOCSettingsService.add_map(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class MapPoolDetailView(TOCBaseView):
    """PUT to update map / DELETE to remove."""

    def put(self, request, slug, pk):
        result = TOCSettingsService.update_map(str(pk), request.data)
        return Response(result)

    def delete(self, request, slug, pk):
        result = TOCSettingsService.delete_map(str(pk))
        return Response(result)


class MapPoolReorderView(TOCBaseView):
    """POST to reorder map pool."""

    def post(self, request, slug):
        ordered_ids = request.data.get("ordered_ids", [])
        result = TOCSettingsService.reorder_maps(self.tournament, ordered_ids)
        return Response(result)


# ------------------------------------------------------------------
# S8-B4: Veto Sessions
# ------------------------------------------------------------------

class VetoSessionView(TOCBaseView):
    """GET veto session for match / POST to create."""

    def get(self, request, slug, match_pk):
        data = TOCSettingsService.get_veto_session(str(match_pk))
        return Response(data or {})

    def post(self, request, slug, match_pk):
        result = TOCSettingsService.create_veto_session(str(match_pk), request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class VetoAdvanceView(TOCBaseView):
    """POST to advance a veto step."""

    def post(self, request, slug, match_pk):
        result = TOCSettingsService.advance_veto(str(match_pk), request.data)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


# ------------------------------------------------------------------
# S8-B5: Server Regions
# ------------------------------------------------------------------

class RegionListView(TOCBaseView):
    """GET regions / POST to create/update."""

    def get(self, request, slug):
        data = TOCSettingsService.get_regions(self.tournament)
        return Response(data)

    def post(self, request, slug):
        result = TOCSettingsService.save_region(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class RegionDeleteView(TOCBaseView):
    """DELETE a region."""

    def delete(self, request, slug, pk):
        result = TOCSettingsService.delete_region(str(pk))
        return Response(result)


# ------------------------------------------------------------------
# S8-B6: Rulebook Versions
# ------------------------------------------------------------------

class RulebookListView(TOCBaseView):
    """GET all versions / POST to create new version."""

    def get(self, request, slug):
        data = TOCSettingsService.get_rulebook_versions(self.tournament)
        return Response(data)

    def post(self, request, slug):
        result = TOCSettingsService.create_rulebook_version(
            self.tournament, request.data, user=request.user,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class RulebookDetailView(TOCBaseView):
    """PUT to update a version."""

    def put(self, request, slug, pk):
        result = TOCSettingsService.update_rulebook_version(str(pk), request.data)
        return Response(result)


class RulebookPublishView(TOCBaseView):
    """POST to publish a specific version."""

    def post(self, request, slug, pk):
        result = TOCSettingsService.publish_rulebook(str(pk))
        return Response(result)


# ------------------------------------------------------------------
# S8-B7: BR Scoring Matrix
# ------------------------------------------------------------------

class BRScoringView(TOCBaseView):
    """GET / PUT BR scoring matrix."""

    def get(self, request, slug):
        data = TOCSettingsService.get_br_scoring(self.tournament)
        return Response(data or {})

    def put(self, request, slug):
        result = TOCSettingsService.save_br_scoring(self.tournament, request.data)
        return Response(result)
