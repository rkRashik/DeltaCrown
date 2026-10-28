from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.http import HttpResponse, Http404
from django.core.paginator import Paginator, InvalidPage
from django.urls import reverse
from django.utils.html import escape
from django.utils.cache import patch_vary_headers

from apps.common.seo import absolute_url


@dataclass(frozen=True)
class SitemapUrl:
    loc: str
    lastmod: object | None = None
    changefreq: str | None = None
    priority: str | None = None


SITEMAP_PAGE_SIZE = 1000

SITEMAP_SECTIONS = ("static", "tournaments", "teams", "orgs", "profiles", "rankings")


def _xml_response(body: str) -> HttpResponse:
    response = HttpResponse(body, content_type="application/xml; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300, no-transform"
    patch_vary_headers(response, ("Accept-Encoding",))
    return response


def _text_response(body: str) -> HttpResponse:
    response = HttpResponse(body, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300, no-transform"
    patch_vary_headers(response, ("Accept-Encoding",))
    return response


def _format_lastmod(value) -> str:
    if not value:
        return ""
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /account/",
        "Disallow: /accounts/",
        "Disallow: /api/",
        "Disallow: /dashboard/",
        "Disallow: /me/",
        "Disallow: /notifications/",
        "Disallow: /search/",
        "Disallow: /toc/",
        "Disallow: /wallet/",
        "Disallow: /ws/",
        "Disallow: /media/",
        "Disallow: /*/hub/",
        "Disallow: /*/checkout/",
        "Disallow: /*/cart/",
        "Disallow: /*/manage/",
        "Disallow: /*/control-plane/",
        "Disallow: /*?q=",
        "Disallow: /*?search=",
        "Disallow: /*?filter=",
        "Allow: /",
        "",
        f"Sitemap: {absolute_url('/sitemap.xml')}",
        "",
    ]
    return _text_response("\n".join(lines))


def sitemap_index(request):
    items = []
    for section in SITEMAP_SECTIONS:
        pages = _section_page_count(section)
        for page in range(1, pages + 1):
            loc = absolute_url(reverse("sitemap_section", kwargs={"section": section}))
            if page > 1:
                loc += f"?page={page}"
            items.append(f"  <sitemap><loc>{escape(loc)}</loc></sitemap>")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(items)
        + "\n</sitemapindex>\n"
    )
    return _xml_response(body)


def sitemap_section(request, section: str):
    if section not in SITEMAP_SECTIONS:
        return HttpResponse(status=404)
    try:
        page = int(request.GET.get("page", "1"))
        if page < 1:
            raise ValueError
    except (ValueError, TypeError):
        raise Http404("Invalid sitemap page")
    urls = list(_section_urls(section, page))
    rows = []
    for item in urls:
        rows.append("  <url>")
        rows.append(f"    <loc>{escape(item.loc)}</loc>")
        lastmod = _format_lastmod(item.lastmod)
        if lastmod:
            rows.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
        if item.changefreq:
            rows.append(f"    <changefreq>{escape(item.changefreq)}</changefreq>")
        if item.priority:
            rows.append(f"    <priority>{escape(item.priority)}</priority>")
        rows.append("  </url>")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    return _xml_response(body)


def _section_page_count(section):
    queryset = _public_queryset(section)
    return Paginator(queryset, SITEMAP_PAGE_SIZE).num_pages if queryset is not None else 1


def _public_queryset(section):
    from django.db.models import Q
    if section == "tournaments":
        from apps.tournaments.models import Tournament
        return Tournament.objects.filter(is_deleted=False, status__in=[
            Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN,
            Tournament.REGISTRATION_CLOSED, Tournament.LIVE, Tournament.COMPLETED,
        ]).only("slug", "updated_at").order_by("pk")
    if section == "teams":
        from apps.organizations.models import Team
        return Team.objects.filter(status="ACTIVE", visibility="PUBLIC", is_temporary=False).filter(
            Q(description__gt="") | Q(tagline__gt="")
        ).select_related("organization").only("slug", "updated_at", "organization__slug").order_by("pk")
    if section == "orgs":
        from apps.organizations.models import Organization
        # A conservative subset of public pages with meaningful authored content.
        return Organization.objects.filter(description__gt="").only("slug", "updated_at").order_by("pk")
    if section == "profiles":
        from apps.user_profile.models import UserProfile, PrivacySettings
        return UserProfile.objects.filter(
            user__is_active=True,
            privacy_settings__visibility_preset=PrivacySettings.PRESET_PUBLIC,
            privacy_settings__is_private_account=False,
        ).filter(Q(bio__gt="") | Q(about_bio__gt="")).select_related("user").only(
            "updated_at", "user__username"
        ).order_by("pk")
    return None


def _section_urls(section, page=1) -> Iterable[SitemapUrl]:
    queryset = _public_queryset(section)
    if queryset is not None:
        try:
            records = Paginator(queryset, SITEMAP_PAGE_SIZE).page(page).object_list
        except InvalidPage:
            raise Http404("Invalid sitemap page")
        for obj in records:
            if section == "tournaments":
                path = reverse("tournaments:detail", kwargs={"slug": obj.slug})
            elif section == "profiles":
                path = reverse("user_profile:public_profile", kwargs={"username": obj.user.username})
            else:
                path = obj.get_absolute_url()
            yield SitemapUrl(absolute_url(path), lastmod=obj.updated_at, changefreq="weekly")
    elif page != 1:
        raise Http404("Invalid sitemap page")
    elif section == "static":
        yield from _static_urls()
    elif section == "rankings":
        yield from _ranking_urls()


def _static_urls() -> Iterable[SitemapUrl]:
    static_pages = [
        ("/", "daily", "1.0"),
        ("/about/", "monthly", "0.8"),
        ("/faq/", "monthly", "0.6"),
        ("/rules/", "monthly", "0.6"),
        ("/contact/", "monthly", "0.5"),
        ("/terms/", "yearly", "0.4"),
        ("/privacy/", "yearly", "0.4"),
        ("/cookies/", "yearly", "0.3"),
        ("/moderation/", "monthly", "0.5"),
        ("/tournaments/", "daily", "0.9"),
        ("/teams/", "daily", "0.8"),
        ("/teams/directory/", "daily", "0.7"),
        ("/orgs/", "weekly", "0.7"),
        ("/competition/ranking/about/", "monthly", "0.5"),
        ("/arena/", "daily", "0.5"),
    ]
    for path, changefreq, priority in static_pages:
        yield SitemapUrl(absolute_url(path), changefreq=changefreq, priority=priority)


def _ranking_urls() -> Iterable[SitemapUrl]:
    from django.apps import apps
    if not apps.is_installed("apps.competition"):
        return
    from apps.competition.services.competition_service import CompetitionService
    from apps.competition.models import GameRankingConfig

    if CompetitionService.get_global_rankings(limit=1, offset=0).total_count > 0:
        yield SitemapUrl(absolute_url("/competition/leaderboards/"), changefreq="daily")
    for config in GameRankingConfig.objects.filter(is_active=True).only("game_id", "updated_at").order_by("pk"):
        if CompetitionService.get_game_rankings(config.game_id, limit=1, offset=0).total_count > 0:
            yield SitemapUrl(absolute_url(reverse("competition:leaderboard_game", kwargs={"game_id": config.game_id})), lastmod=config.updated_at, changefreq="daily")
