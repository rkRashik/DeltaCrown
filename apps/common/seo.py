from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse


DEFAULT_TITLE = "DeltaCrown"
DEFAULT_DESCRIPTION = (
    "DeltaCrown is a Bangladesh-first esports ecosystem for tournaments, teams, "
    "Crown Points rankings, Game Passport profiles, and competitive operations."
)
DEFAULT_IMAGE = "siteui/og/default.png"


NOINDEX_PREFIXES = (
    "/account/",
    "/accounts/",
    "/admin/",
    "/api/",
    "/ckeditor5/",
    "/crownstore/",
    "/dashboard/",
    "/healthz/",
    "/me/",
    "/notifications/",
    "/readiness/",
    "/search/",
    "/toc/",
    "/wallet/",
)

NOINDEX_EXACT = (
    "/favicon-test/",
    "/teams/create/",
    "/teams/filter/",
    "/teams/invites/",
    "/orgs/create/",
    "/tournaments/create/",
    "/tournaments/my/",
    "/tournaments/my/matches/",
)

NOINDEX_CONTAINS = (
    "/manage/",
    "/control-plane/",
    "/settings/",
    "/invites/",
    "/follow-requests/",
    "/register/",
    "/lobby/",
    "/match-room/",
    "/submit-result/",
    "/report-dispute/",
)


def site_url() -> str:
    return str(getattr(settings, "SITE_URL", "https://deltacrown.xyz")).rstrip("/")


def absolute_url(path_or_url: str | None = None) -> str:
    if not path_or_url:
        return f"{site_url()}/"
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = f"/{path_or_url}"
    return urljoin(f"{site_url()}/", path_or_url.lstrip("/"))


def absolute_static(path: str = DEFAULT_IMAGE) -> str:
    return absolute_url(static(path))


def reverse_absolute(viewname: str, kwargs: dict[str, Any] | None = None) -> str:
    return absolute_url(reverse(viewname, kwargs=kwargs))


def truncate_meta(value: str, length: int = 155) -> str:
    value = " ".join((value or "").split())
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip(" .,;:-") + "..."


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def schema_json(schema: dict[str, Any] | list[dict[str, Any]] | None) -> list[str]:
    if not schema:
        return []
    schemas = schema if isinstance(schema, list) else [schema]
    return [
        json.dumps(item, ensure_ascii=False, default=_json_default, separators=(",", ":"))
        for item in schemas
        if item
    ]


def should_noindex_path(path: str, query_string: str = "") -> bool:
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized in NOINDEX_EXACT:
        return True
    if any(normalized.startswith(prefix) for prefix in NOINDEX_PREFIXES):
        return True
    if any(part in normalized for part in NOINDEX_CONTAINS):
        return True
    if query_string:
        low_value_params = (
            "q=",
            "search=",
            "filter=",
            "sort=",
            "format=json",
            "tier=",
            "verified_only=",
            "season_id=",
        )
        if any(token in query_string for token in low_value_params):
            return True
    return False


def breadcrumb_schema(items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": absolute_url(url),
            }
            for index, (name, url) in enumerate(items, start=1)
        ],
    }


def build_seo(
    *,
    title: str | None = None,
    description: str | None = None,
    path: str | None = None,
    canonical: str | None = None,
    robots: str | None = None,
    noindex: bool = False,
    og_title: str | None = None,
    og_description: str | None = None,
    og_image: str | None = None,
    og_type: str = "website",
    twitter_card: str = "summary_large_image",
    schema: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved_title = title or DEFAULT_TITLE
    resolved_description = truncate_meta(description or DEFAULT_DESCRIPTION)
    resolved_canonical = canonical or absolute_url(path)
    resolved_robots = robots or ("noindex, nofollow" if noindex else "index, follow")
    resolved_image = absolute_url(og_image) if og_image else absolute_static(DEFAULT_IMAGE)
    return {
        "title": resolved_title,
        "description": resolved_description,
        "canonical": resolved_canonical,
        "robots": resolved_robots,
        "og_title": og_title or resolved_title,
        "og_description": truncate_meta(og_description or resolved_description),
        "og_image": resolved_image,
        "og_type": og_type,
        "twitter_card": twitter_card,
        "twitter_title": og_title or resolved_title,
        "twitter_description": truncate_meta(og_description or resolved_description),
        "twitter_image": resolved_image,
        "schema_json": schema_json(schema),
    }


def default_seo_for_request(request) -> dict[str, Any]:
    return build_seo(
        path=request.path,
        noindex=should_noindex_path(request.path, request.META.get("QUERY_STRING", "")),
    )


def website_schema() -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "DeltaCrown",
        "url": absolute_url("/"),
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{absolute_url('/search/')}?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }


def organization_schema() -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "DeltaCrown",
        "url": absolute_url("/"),
        "logo": absolute_static("img/favicon/favicon-180x180.png"),
        "description": DEFAULT_DESCRIPTION,
    }


def safe_reverse(viewname: str, kwargs: dict[str, Any] | None = None) -> str | None:
    try:
        return reverse(viewname, kwargs=kwargs)
    except NoReverseMatch:
        return None
