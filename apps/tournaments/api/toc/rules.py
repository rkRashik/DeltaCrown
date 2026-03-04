"""
TOC API Views — Sprint 28: Rules & Info tab.

GET   rules/                  — Full rules dashboard
POST  rules/sections/<id>/    — Update/create section
DEL   rules/sections/<id>/    — Delete section
POST  rules/faq/              — Add FAQ
PUT   rules/faq/<id>/         — Update FAQ
DEL   rules/faq/<id>/         — Delete FAQ
POST  rules/publish/          — Publish new version
POST  rules/prize-info/       — Update prize info
POST  rules/quick-reference/  — Update quick reference
POST  rules/acknowledge/      — Acknowledge rules
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.rules_service import TOCRulesService


class RulesDashboardView(TOCBaseView):
    """Full rules & info dashboard."""

    def get(self, request, slug):
        result = TOCRulesService.get_rules_dashboard(self.tournament)
        return Response(result)


class RulesSectionView(TOCBaseView):
    """Update or create a rulebook section."""

    def post(self, request, slug, section_id):
        result = TOCRulesService.update_section(
            self.tournament, section_id=section_id, data=request.data,
        )
        return Response(result)

    def delete(self, request, slug, section_id):
        result = TOCRulesService.delete_section(self.tournament, section_id=section_id)
        return Response(result)


class RulesFaqView(TOCBaseView):
    """Add a FAQ entry."""

    def post(self, request, slug):
        result = TOCRulesService.add_faq(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class RulesFaqDetailView(TOCBaseView):
    """Update / delete a FAQ entry."""

    def put(self, request, slug, faq_id):
        result = TOCRulesService.update_faq(
            self.tournament, faq_id=faq_id, data=request.data,
        )
        return Response(result)

    def delete(self, request, slug, faq_id):
        result = TOCRulesService.delete_faq(self.tournament, faq_id=faq_id)
        return Response(result)


class RulesPublishView(TOCBaseView):
    """Publish a new version of the rules."""

    def post(self, request, slug):
        data = request.data.copy()
        data["published_by"] = request.user.username
        result = TOCRulesService.publish_version(self.tournament, data)
        return Response(result)


class RulesPrizeInfoView(TOCBaseView):
    """Update prize distribution info."""

    def post(self, request, slug):
        result = TOCRulesService.update_prize_info(self.tournament, request.data)
        return Response(result)


class RulesQuickReferenceView(TOCBaseView):
    """Update quick reference card."""

    def post(self, request, slug):
        result = TOCRulesService.update_quick_reference(self.tournament, request.data)
        return Response(result)


class RulesAcknowledgeView(TOCBaseView):
    """Record that a user has acknowledged the rules."""

    def post(self, request, slug):
        result = TOCRulesService.acknowledge_rules(
            self.tournament, user_id=request.user.id,
        )
        return Response(result)
