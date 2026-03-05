"""
TOC API Views — Sprint 10G: Settings & Configuration (1:1 Database Parity).

S8-B1 GET/PUT  settings/               — Tournament settings CRUD
S8-B2 GET/PUT  settings/game-config/   — Game match config
S8-B3 GET/POST settings/map-pool/      — Map pool list / add
S8-B3 PUT/PATCH/DEL settings/map-pool/<id>/ — Map update / delete
S8-B3 POST     settings/map-pool/reorder/ — Reorder maps
S8-B4 GET/POST settings/veto/<match_id>/ — Veto session read/create
S8-B4 POST     settings/veto/<match_id>/advance/ — Advance veto step
S8-B5 GET/POST settings/regions/       — Server region list / save
S8-B5 DELETE   settings/regions/<id>/  — Delete region
S8-B6 GET/POST settings/rulebook/      — Rulebook version list / create
S8-B6 PUT      settings/rulebook/<id>/ — Update version
S8-B6 POST     settings/rulebook/<id>/publish/ — Publish version
S8-B7 GET/PUT  settings/br-scoring/    — BR scoring matrix
S10G  GET/POST settings/payment-methods/ — Payment method list / add
S10G  DELETE   settings/payment-methods/<id>/ — Delete payment method
S10G  POST     settings/upload/        — File upload (banner, thumbnail, pdfs)
"""

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
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
    """PUT/PATCH to update map / DELETE to remove."""

    def put(self, request, slug, pk):
        result = TOCSettingsService.update_map(str(pk), request.data)
        return Response(result)

    def patch(self, request, slug, pk):
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


# ------------------------------------------------------------------
# S10G: Payment Methods (TournamentPaymentMethod CRUD)
# ------------------------------------------------------------------

class PaymentMethodListView(TOCBaseView):
    """GET all payment methods / POST to add a new one."""

    def get(self, request, slug):
        data = TOCSettingsService.get_payment_methods(self.tournament)
        return Response(data)

    def post(self, request, slug):
        result = TOCSettingsService.add_payment_method(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class PaymentMethodDeleteView(TOCBaseView):
    """DELETE a payment method."""

    def delete(self, request, slug, pk):
        result = TOCSettingsService.delete_payment_method(int(pk))
        return Response(result)


# ------------------------------------------------------------------
# S10G: File Upload (banner, thumbnail, rules_pdf, terms_pdf)
# ------------------------------------------------------------------

class SettingsFileUploadView(TOCBaseView):
    """POST multipart file upload for tournament image/file fields."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        field_name = request.data.get("field")
        uploaded_file = request.FILES.get("file")
        if not field_name or not uploaded_file:
            return Response(
                {"error": "Both 'field' and 'file' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = TOCSettingsService.upload_file(self.tournament, field_name, uploaded_file)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


# ── S28: Tournament Cloning ───────────────────────────────────────

class CloneTournamentView(TOCBaseView):
    """
    POST /api/toc/<slug>/settings/clone/
    Deep-clone tournament (all settings, format config, scoring, map pool, etc.).
    Returns new tournament slug for immediate redirect.

    Body (optional):
        name  — override name for the clone (default: "<name> (Copy)")
    """

    def post(self, request, slug):
        from apps.tournaments.services.tournament_cloning_service import TournamentCloningService

        overrides = {}
        if "name" in request.data:
            overrides["name"] = request.data["name"]

        try:
            clone = TournamentCloningService.clone(
                source=self.tournament,
                organizer=request.user,
                overrides=overrides,
            )
        except Exception as exc:
            return Response(
                {"error": f"Clone failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "slug": clone.slug,
            "name": clone.name,
            "id": clone.id,
            "message": f'Tournament cloned as "{clone.name}"',
        }, status=status.HTTP_201_CREATED)


# ── S28: Webhook Configuration ────────────────────────────────────

class WebhookConfigView(TOCBaseView):
    """
    GET/POST /api/toc/<slug>/settings/webhooks/
    Manage outgoing webhooks for external integrations.
    """

    def get(self, request, slug):
        config = self.tournament.config or {}
        webhooks = config.get('webhooks', [])
        return Response({'webhooks': webhooks})

    def post(self, request, slug):
        config = self.tournament.config or {}
        webhooks = request.data.get('webhooks', [])

        # Validate
        valid = []
        for wh in webhooks:
            if isinstance(wh, dict) and wh.get('url'):
                valid.append({
                    'url': wh['url'],
                    'events': wh.get('events', ['all']),
                    'enabled': wh.get('enabled', True),
                    'secret': wh.get('secret', ''),
                    'name': wh.get('name', 'Webhook'),
                })

        config['webhooks'] = valid
        self.tournament.config = config
        self.tournament.save(update_fields=['config'])
        return Response({'webhooks': valid, 'message': 'Webhooks updated'})


# ── S28: Danger Zone ──────────────────────────────────────────────

class DangerZoneDeleteView(TOCBaseView):
    """
    POST /api/toc/<slug>/settings/danger/delete/
    Permanently delete tournament (requires confirmation token).
    """

    def post(self, request, slug):
        confirm = request.data.get('confirm_slug', '')
        if confirm != self.tournament.slug:
            return Response(
                {'error': f'Type "{self.tournament.slug}" to confirm deletion'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = self.tournament.name
        self.tournament.delete()
        return Response({'message': f'Tournament "{name}" permanently deleted'})


class DangerZoneArchiveView(TOCBaseView):
    """
    POST /api/toc/<slug>/settings/danger/archive/
    Archive tournament (set status to archived).
    """

    def post(self, request, slug):
        self.tournament.status = 'archived'
        self.tournament.save(update_fields=['status'])
        return Response({'message': 'Tournament archived', 'status': 'archived'})


# ------------------------------------------------------------------
# Discord Webhook Test
# ------------------------------------------------------------------

class DiscordWebhookTestView(TOCBaseView):
    """
    POST /api/toc/<slug>/settings/discord-webhook-test/
    Send a test message to verify the configured Discord webhook URL.
    """

    def post(self, request, slug):
        webhook_url = request.data.get('webhook_url') or getattr(self.tournament, 'discord_webhook_url', '')
        if not webhook_url:
            return Response(
                {'error': 'No webhook URL provided'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.tournaments.services.discord_webhook import DiscordWebhookService
        result = DiscordWebhookService.test_webhook(webhook_url, self.tournament.name)
        if result.get('success'):
            return Response({'message': 'Test message sent successfully!', 'success': True})
        else:
            return Response(
                {'error': result.get('error', 'Unknown error'), 'success': False},
                status=status.HTTP_400_BAD_REQUEST,
            )
