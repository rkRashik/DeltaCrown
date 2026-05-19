from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.http import HttpResponse
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
        loc = absolute_url(reverse("sitemap_section", kwargs={"section": section}))
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
    urls = list(_section_urls(section))
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


def _section_urls(section: str) -> Iterable[SitemapUrl]:
    if section == "static":
        yield from _static_urls()
    elif section == "tournaments":
        yield from _tournament_urls()
    elif section == "teams":
        yield from _team_urls()
    elif section == "orgs":
        yield from _org_urls()
    elif section == "profiles":
        yield from _profile_urls()
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
        ("/competition/leaderboards/", "daily", "0.8"),
        ("/competition/ranking/about/", "monthly", "0.5"),
        ("/arena/", "daily", "0.5"),
    ]
    for path, changefreq, priority in static_pages:
        yield SitemapUrl(absolute_url(path), changefreq=changefreq, priority=priority)


def _tournament_urls() -> Iterable[SitemapUrl]:
    try:
        from apps.tournaments.models import Tournament

        public_statuses = [
            Tournament.PUBLISHED,
            Tournament.REGISTRATION_OPEN,
            Tournament.REGISTRATION_CLOSED,
            Tournament.LIVE,
            Tournament.COMPLETED,
            Tournament.ARCHIVED,
        ]
        for tournament in (
            Tournament.objects.filter(status__in=public_statuses)
            .only("slug", "updated_at", "published_at", "status", "tournament_start")
            .order_by("-tournament_start")[:5000]
        ):
            yield SitemapUrl(
                absolute_url(reverse("tournaments:detail", kwargs={"slug": tournament.slug})),
                lastmod=tournament.updated_at or tournament.published_at,
                changefreq="daily" if tournament.status in {Tournament.REGISTRATION_OPEN, Tournament.LIVE} else "weekly",
                priority="0.8",
            )
    except Exception:
        return


def _team_urls() -> Iterable[SitemapUrl]:
    try:
        from django.db.models import Q
        from apps.organizations.choices import TeamStatus
        from apps.organizations.models import Team

        for team in (
            Team.objects.filter(status=TeamStatus.ACTIVE, visibility="PUBLIC", is_temporary=False)
            .filter(Q(description__gt="") | Q(tagline__gt="") | Q(logo__isnull=False))
            .select_related("organization")
            .only("slug", "updated_at", "organization__slug")
            .order_by("-updated_at")[:5000]
        ):
            yield SitemapUrl(absolute_url(team.get_absolute_url()), lastmod=team.updated_at, changefreq="weekly", priority="0.7")
    except Exception:
        return


def _org_urls() -> Iterable[SitemapUrl]:
    try:
        from django.db.models import Q
        from apps.organizations.models import Organization

        for org in Organization.objects.filter(Q(description__gt="") | Q(teams__status="ACTIVE")).distinct().only("slug", "updated_at").order_by("-updated_at")[:2000]:
            yield SitemapUrl(
                absolute_url(reverse("organizations:organization_detail", kwargs={"org_slug": org.slug})),
                lastmod=org.updated_at,
                changefreq="weekly",
                priority="0.7",
            )
    except Exception:
        return


def _profile_urls() -> Iterable[SitemapUrl]:
    try:
        from django.db.models import Q
        from apps.user_profile.models import PrivacySettings, UserProfile

        for profile in (
            UserProfile.objects.select_related("user", "privacy_settings")
            .filter(user__is_active=True)
            .filter(Q(bio__gt="") | Q(about_bio__gt=""))
            .exclude(privacy_settings__visibility_preset=PrivacySettings.PRESET_PRIVATE)
            .only("updated_at", "display_name", "user__username", "privacy_settings__visibility_preset")
            .order_by("-updated_at")[:5000]
        ):
            yield SitemapUrl(
                absolute_url(f"/@{profile.user.username}/"),
                lastmod=profile.updated_at,
                changefreq="weekly",
                priority="0.5",
            )
    except Exception:
        return


def _ranking_urls() -> Iterable[SitemapUrl]:
    try:
        from apps.competition.services.competition_service import CompetitionService
        from apps.competition.models import GameRankingConfig

        global_rankings = CompetitionService.get_global_rankings(limit=1, offset=0)
        if global_rankings.total_count > 0:
            yield SitemapUrl(absolute_url("/competition/leaderboards/"), changefreq="daily", priority="0.8")

        for config in GameRankingConfig.objects.filter(is_active=True).only("game_id", "updated_at").order_by("game_name"):
            rankings = CompetitionService.get_game_rankings(config.game_id, limit=1, offset=0)
            if rankings.total_count <= 0:
                continue
            yield SitemapUrl(
                absolute_url(reverse("competition:leaderboard_game", kwargs={"game_id": config.game_id})),
                lastmod=config.updated_at,
                changefreq="daily",
                priority="0.7",
            )
    except Exception:
        return
