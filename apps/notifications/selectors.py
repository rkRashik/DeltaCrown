from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable
from urllib.parse import quote_plus

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.utils.html import escape, strip_tags

from .models import Notification


@dataclass(frozen=True)
class NotificationFeedPage:
    items: list[dict]
    page: int
    page_size: int
    total: int
    has_next: bool


_CANONICAL_TYPES = {
    Notification.NotificationCategory.TOURNAMENT,
    Notification.NotificationCategory.TEAM,
    Notification.NotificationCategory.ECONOMY,
    Notification.NotificationCategory.SOCIAL,
    Notification.NotificationCategory.SYSTEM,
    Notification.NotificationCategory.WARNING,
}

_LEGACY_TYPE_MAP = {
    "tournament": Notification.NotificationCategory.TOURNAMENT,
    "tournaments": Notification.NotificationCategory.TOURNAMENT,
    "match": Notification.NotificationCategory.TOURNAMENT,
    "bracket": Notification.NotificationCategory.TOURNAMENT,
    "checkin": Notification.NotificationCategory.TOURNAMENT,
    "team": Notification.NotificationCategory.TEAM,
    "roster": Notification.NotificationCategory.TEAM,
    "invite": Notification.NotificationCategory.TEAM,
    "economy": Notification.NotificationCategory.ECONOMY,
    "payment": Notification.NotificationCategory.ECONOMY,
    "payout": Notification.NotificationCategory.ECONOMY,
    "withdraw": Notification.NotificationCategory.ECONOMY,
    "coin": Notification.NotificationCategory.ECONOMY,
    "social": Notification.NotificationCategory.SOCIAL,
    "follow": Notification.NotificationCategory.SOCIAL,
    "like": Notification.NotificationCategory.SOCIAL,
    "comment": Notification.NotificationCategory.SOCIAL,
    "mention": Notification.NotificationCategory.SOCIAL,
    "warning": Notification.NotificationCategory.WARNING,
    "alert": Notification.NotificationCategory.WARNING,
    "danger": Notification.NotificationCategory.WARNING,
    "error": Notification.NotificationCategory.WARNING,
    "info": Notification.NotificationCategory.SYSTEM,
    "system": Notification.NotificationCategory.SYSTEM,
    "generic": Notification.NotificationCategory.SYSTEM,
}


@dataclass
class EntityContext:
    ref_type: str = ""
    actor_username: str = ""
    actor_name: str = ""
    actor_avatar: str = ""
    team_slug: str = ""
    team_name: str = ""
    team_logo: str = ""
    tournament_slug: str = ""
    tournament_name: str = ""
    tournament_image: str = ""
    organization_slug: str = ""
    organization_name: str = ""
    organization_logo: str = ""


def build_notification_queryset(user) -> QuerySet[Notification]:
    """Base optimized queryset for notification list/preview endpoints."""
    return (
        Notification.objects.filter(recipient=user)
        .select_related("recipient")
        .only(
            "id",
            "type",
            "category",
            "notification_type",
            "title",
            "body",
            "message",
            "html_text",
            "url",
            "avatar_url",
            "image_url",
            "action_label",
            "action_url",
            "action_data",
            "action_object_id",
            "action_type",
            "tournament_id",
            "is_read",
            "created_at",
            "priority",
            "is_actionable",
            "recipient_id",
        )
        .order_by("-created_at")
    )


def _safe_media_url(media_field) -> str:
    if not media_field:
        return ""
    try:
        return media_field.url
    except Exception:
        return ""


def _first_non_empty(*values) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_int(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _extract_action_data(notification: Notification) -> dict:
    raw = getattr(notification, "action_data", None)
    return raw if isinstance(raw, dict) else {}


def _pick(data: dict, *keys) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _pick_int(data: dict, *keys) -> int | None:
    for key in keys:
        casted = _coerce_int(data.get(key))
        if casted is not None:
            return casted
    return None


def _extract_refs(notification: Notification) -> dict:
    data = _extract_action_data(notification)
    return {
        "ref_type": _pick(data, "ref_type", "entity_type", "object_type", "target_type", "context_type").lower(),
        "actor_username": _pick(
            data,
            "actor_username",
            "username",
            "sender_username",
            "user_username",
            "requester_username",
            "inviter_username",
            "actor",
            "user",
        ).lstrip("@"),
        "actor_name": _pick(data, "actor_name", "display_name", "sender_name", "user_display_name", "requester_name"),
        "actor_avatar": _pick(data, "actor_avatar", "avatar_url", "user_avatar", "sender_avatar", "profile_image"),
        "team_slug": _pick(data, "team_slug", "slug", "target_team_slug", "entity_slug"),
        "team_name": _pick(data, "team_name", "target_team_name", "team", "entity_name"),
        "team_logo": _pick(data, "team_logo", "team_image", "logo_url"),
        "team_id": _pick_int(data, "team_id", "target_team_id", "entity_id"),
        "tournament_slug": _pick(data, "tournament_slug", "t_slug", "event_slug"),
        "tournament_name": _pick(data, "tournament_name", "event_name", "tournament"),
        "tournament_image": _pick(data, "tournament_logo", "game_icon", "banner_url", "image_url"),
        "tournament_id": _pick_int(data, "tournament_id", "tournamentId") or _coerce_int(getattr(notification, "tournament_id", None)),
        "organization_slug": _pick(data, "organization_slug", "org_slug"),
        "organization_name": _pick(data, "organization_name", "org_name"),
        "organization_logo": _pick(data, "organization_logo", "org_logo"),
        "organization_id": _pick_int(data, "organization_id", "org_id"),
    }


def _extract_username_from_text(notification: Notification) -> str:
    for text in (
        str(getattr(notification, "title", "") or ""),
        str(getattr(notification, "message", "") or ""),
        str(getattr(notification, "body", "") or ""),
    ):
        mention = re.search(r"@([A-Za-z0-9_.-]+)", text)
        if mention:
            return mention.group(1)
        leading_actor = re.match(r"^([A-Za-z0-9_.-]{2,40})\s+(joined|accepted|followed|invited|requested|liked|commented)\b", text, re.IGNORECASE)
        if leading_actor:
            return leading_actor.group(1)
    return ""


def _extract_slug_from_url(url: str, section: str) -> str:
    if not url:
        return ""
    parts = [p for p in str(url).split("/") if p]
    for idx, part in enumerate(parts):
        if part == section and idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _build_related_maps(items: Iterable[Notification]) -> tuple[dict[int, dict], dict[int, dict], dict[str, dict], dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Batch-fetch structured user/team/tournament/org references for payload rendering."""
    FollowRequest = apps.get_model("user_profile", "FollowRequest")
    TeamInvite = apps.get_model("organizations", "TeamInvite")

    follow_ids: list[int] = []
    invite_ids: list[int] = []

    usernames: set[str] = set()
    team_slugs: set[str] = set()
    team_ids: set[int] = set()
    tournament_ids: set[int] = set()
    tournament_slugs: set[str] = set()
    organization_slugs: set[str] = set()
    organization_ids: set[int] = set()

    action_refs: dict[int, dict] = {}

    for n in items:
        refs = _extract_refs(n)
        action_refs[n.id] = refs

        if n.type == Notification.Type.FOLLOW_REQUEST and n.action_object_id:
            follow_ids.append(n.action_object_id)
        if n.type == Notification.Type.INVITE_SENT and n.action_type == "team_invite" and n.action_object_id:
            invite_ids.append(n.action_object_id)

        if refs["actor_username"]:
            usernames.add(refs["actor_username"].lower())
        fallback_actor = _extract_username_from_text(n)
        if fallback_actor:
            usernames.add(fallback_actor.lower())
        if refs["team_slug"]:
            team_slugs.add(refs["team_slug"])
        if refs["team_id"] is not None:
            team_ids.add(refs["team_id"])
        if refs["tournament_id"] is not None:
            tournament_ids.add(refs["tournament_id"])
        if refs["tournament_slug"]:
            tournament_slugs.add(refs["tournament_slug"])
        if refs["organization_slug"]:
            organization_slugs.add(refs["organization_slug"])
        if refs["organization_id"] is not None:
            organization_ids.add(refs["organization_id"])

        url = _first_non_empty(getattr(n, "action_url", ""), getattr(n, "url", ""))
        if "/teams/" in url:
            parts = [p for p in url.split("/") if p]
            if len(parts) >= 2 and parts[0] == "teams":
                team_slugs.add(parts[1])
        if "/@" in url:
            u = _extract_slug_from_url(url, "@")
            if u:
                usernames.add(u.lower())
        if "/tournaments/" in url:
            parts = [p for p in url.split("/") if p]
            if len(parts) >= 2 and parts[0] == "tournaments":
                tournament_slugs.add(parts[1])
        if "/orgs/" in url:
            parts = [p for p in url.split("/") if p]
            if len(parts) >= 2 and parts[0] == "orgs":
                organization_slugs.add(parts[1])

    follow_map: dict[int, dict] = {}
    if follow_ids:
        follow_rows = (
            FollowRequest.objects.filter(id__in=follow_ids)
            .select_related("requester", "requester__user")
            .only("id", "status", "requester__display_name", "requester__avatar", "requester__user__username")
        )
        for row in follow_rows:
            requester_name = getattr(row.requester, "display_name", "") or row.requester.user.username
            requester_username = getattr(row.requester.user, "username", "")
            avatar_url = _safe_media_url(getattr(row.requester, "avatar", None))
            if not avatar_url:
                avatar_url = _safe_media_url(getattr(row.requester.user, "avatar", None))
            follow_map[row.id] = {
                "actor": requester_name,
                "username": requester_username,
                "avatar": avatar_url,
                "is_pending": row.status == getattr(FollowRequest, "STATUS_PENDING", "PENDING"),
            }
            if requester_username:
                usernames.add(requester_username.lower())

    invite_map: dict[int, dict] = {}
    if invite_ids:
        invite_rows = (
            TeamInvite.objects.filter(id__in=invite_ids)
            .select_related("team", "inviter", "inviter__profile")
            .only(
                "id",
                "status",
                "role",
                "team__id",
                "team__name",
                "team__slug",
                "team__logo",
                "inviter__username",
                "inviter__profile__avatar",
            )
        )
        for row in invite_rows:
            logo_url = _safe_media_url(getattr(row.team, "logo", None))
            inviter_avatar = ""
            profile = getattr(row.inviter, "profile", None)
            if profile is not None:
                inviter_avatar = _safe_media_url(getattr(profile, "avatar", None))
            if not inviter_avatar and row.inviter is not None:
                inviter_avatar = _safe_media_url(getattr(row.inviter, "avatar", None))
            invite_map[row.id] = {
                "team": row.team.name if row.team else "Team",
                "team_slug": row.team.slug if row.team else "",
                "team_id": row.team.id if row.team else None,
                "image": logo_url,
                "avatar": inviter_avatar,
                "inviter": row.inviter.username if row.inviter else "",
                "role": row.role,
                "is_pending": row.status == "PENDING",
            }
            if row.team:
                team_slugs.add(row.team.slug)
                team_ids.add(row.team.id)
            if row.inviter and row.inviter.username:
                usernames.add(row.inviter.username.lower())

    user_map: dict[str, dict] = {}
    if usernames:
        try:
            User = apps.get_model("accounts", "User")
            user_rows = User.objects.filter(username__in=usernames).select_related("profile")
            for user in user_rows:
                profile = getattr(user, "profile", None)
                avatar = _safe_media_url(getattr(profile, "avatar", None)) if profile else ""
                if not avatar:
                    avatar = _safe_media_url(getattr(user, "avatar", None))
                user_map[user.username.lower()] = {
                    "username": user.username,
                    "name": getattr(profile, "display_name", "") if profile else "",
                    "avatar": avatar,
                }
        except Exception:
            user_map = {}

    team_map: dict[str, dict] = {}
    try:
        Team = apps.get_model("organizations", "Team")
        team_qs = Team.objects.none()
        if team_slugs and team_ids:
            team_qs = Team.objects.filter(slug__in=team_slugs) | Team.objects.filter(id__in=team_ids)
        elif team_slugs:
            team_qs = Team.objects.filter(slug__in=team_slugs)
        elif team_ids:
            team_qs = Team.objects.filter(id__in=team_ids)

        for team in team_qs:
            logo = _safe_media_url(getattr(team, "logo", None))
            team_map[f"slug:{team.slug}"] = {
                "slug": team.slug,
                "name": getattr(team, "name", "Team"),
                "logo": logo,
                "id": getattr(team, "id", None),
            }
            team_map[f"id:{team.id}"] = team_map[f"slug:{team.slug}"]
            org_id = getattr(team, "organization_id", None)
            if org_id:
                organization_ids.add(org_id)
    except LookupError:
        team_map = {}

    tournament_map: dict[str, dict] = {}
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        tournament_qs = Tournament.objects.none()
        if tournament_ids and tournament_slugs:
            tournament_qs = Tournament.objects.filter(id__in=tournament_ids) | Tournament.objects.filter(slug__in=tournament_slugs)
        elif tournament_ids:
            tournament_qs = Tournament.objects.filter(id__in=tournament_ids)
        elif tournament_slugs:
            tournament_qs = Tournament.objects.filter(slug__in=tournament_slugs)

        for row in tournament_qs.select_related("game"):
            image = ""
            game_obj = getattr(row, "game", None)
            for field_name in ("icon", "logo", "banner", "card_image"):
                image = _safe_media_url(getattr(game_obj, field_name, None)) if game_obj else ""
                if image:
                    break
            if not image:
                for field_name in ("banner", "cover_image", "image", "logo"):
                    image = _safe_media_url(getattr(row, field_name, None))
                    if image:
                        break

            payload = {
                "id": getattr(row, "id", None),
                "slug": getattr(row, "slug", ""),
                "name": getattr(row, "name", "Tournament"),
                "image": image,
            }
            tournament_map[f"id:{row.id}"] = payload
            tournament_map[f"slug:{row.slug}"] = payload
    except LookupError:
        tournament_map = {}

    organization_map: dict[str, dict] = {}
    try:
        Organization = apps.get_model("organizations", "Organization")
        org_qs = Organization.objects.none()
        if organization_slugs and organization_ids:
            org_qs = Organization.objects.filter(slug__in=organization_slugs) | Organization.objects.filter(id__in=organization_ids)
        elif organization_slugs:
            org_qs = Organization.objects.filter(slug__in=organization_slugs)
        elif organization_ids:
            org_qs = Organization.objects.filter(id__in=organization_ids)

        for org in org_qs:
            logo = _safe_media_url(getattr(org, "logo", None))
            payload = {
                "id": getattr(org, "id", None),
                "slug": getattr(org, "slug", ""),
                "name": getattr(org, "name", "Organization"),
                "logo": logo,
            }
            organization_map[f"id:{org.id}"] = payload
            organization_map[f"slug:{org.slug}"] = payload
    except LookupError:
        organization_map = {}

    return follow_map, invite_map, user_map, team_map, tournament_map, organization_map


def _normalize_notification_type(notification: Notification) -> str:
    raw_candidates = [
        str(getattr(notification, "notification_type", "") or "").strip(),
        str(getattr(notification, "category", "") or "").strip(),
        str(getattr(notification, "type", "") or "").strip(),
        str(getattr(notification, "event", "") or "").strip(),
    ]

    for value in raw_candidates:
        upper = value.upper()
        if upper in _CANONICAL_TYPES:
            return upper

    for value in raw_candidates:
        lower = value.lower()
        for key, mapped in _LEGACY_TYPE_MAP.items():
            if key in lower:
                return mapped

    return Notification.NotificationCategory.SYSTEM


def _user_span(username: str) -> str:
    username_clean = str(username or "").lstrip("@")
    if not username_clean:
        return '<a href="/" class="hl-user" data-inline-link="1" onclick="event.stopPropagation();">@Player</a>'
    escaped_username = escape(username_clean)
    return (
        f'<a href="/@{escaped_username}/" class="hl-user" data-inline-link="1" onclick="event.stopPropagation();">'
        f"@{escaped_username}</a>"
    )


def _user_span_label(username: str, label: str, include_at: bool = False) -> str:
    username_clean = str(username or "").lstrip("@")
    if not username_clean:
        return '<a href="/" class="hl-user" data-inline-link="1" onclick="event.stopPropagation();">Player</a>'
    escaped_username = escape(username_clean)
    visible = escape(label or username_clean)
    if include_at and not visible.startswith("@"):
        visible = f"@{visible}"
    return (
        f'<a href="/@{escaped_username}/" class="hl-user" data-inline-link="1" onclick="event.stopPropagation();">'
        f"{visible}</a>"
    )


def _ui_avatar_url(label: str, background: str) -> str:
    safe_label = quote_plus((label or "Player")[:48])
    return f"https://ui-avatars.com/api/?name={safe_label}&background={background}&color=fff&size=128&bold=true"


def _team_span(team_name: str, team_slug: str) -> str:
    escaped_name = escape(team_name or "Team")
    escaped_slug = escape(team_slug or "")
    if escaped_slug:
        return (
            f'<a href="/teams/{escaped_slug}/" class="hl-team" data-inline-link="1" onclick="event.stopPropagation();">'
            f"{escaped_name}</a>"
        )
    return f'<a href="/teams/" class="hl-team" data-inline-link="1" onclick="event.stopPropagation();">{escaped_name}</a>'


def _tourney_span(name: str, slug: str) -> str:
    escaped_name = escape(name or "Tournament")
    escaped_slug = escape(slug or "")
    if escaped_slug:
        return (
            f'<a href="/tournaments/{escaped_slug}/hub/" class="hl-tourney" data-inline-link="1" onclick="event.stopPropagation();">'
            f"{escaped_name}</a>"
        )
    return f'<a href="/tournaments/" class="hl-tourney" data-inline-link="1" onclick="event.stopPropagation();">{escaped_name}</a>'


def _org_span(name: str, slug: str) -> str:
    escaped_name = escape(name or "Organization")
    escaped_slug = escape(slug or "")
    if escaped_slug:
        return (
            f'<a href="/orgs/{escaped_slug}/" class="hl-org" data-inline-link="1" onclick="event.stopPropagation();">'
            f"{escaped_name}</a>"
        )
    return f'<a href="/orgs/" class="hl-org" data-inline-link="1" onclick="event.stopPropagation();">{escaped_name}</a>'


def _resolve_entity_context(
    notification: Notification,
    follow_meta: dict | None,
    invite_meta: dict | None,
    user_map: dict[str, dict],
    team_map: dict[str, dict],
    tournament_map: dict[str, dict],
    organization_map: dict[str, dict],
) -> EntityContext:
    refs = _extract_refs(notification)
    ctx = EntityContext(ref_type=refs["ref_type"])

    if follow_meta:
        ctx.actor_username = follow_meta.get("username", "")
        ctx.actor_name = follow_meta.get("actor", "")
        ctx.actor_avatar = follow_meta.get("avatar", "")

    if invite_meta:
        ctx.team_slug = invite_meta.get("team_slug", "")
        ctx.team_name = invite_meta.get("team", "")
        ctx.team_logo = invite_meta.get("image", "")
        if not ctx.actor_username:
            ctx.actor_username = invite_meta.get("inviter", "")
        if not ctx.actor_name:
            ctx.actor_name = invite_meta.get("inviter", "")
        if not ctx.actor_avatar:
            ctx.actor_avatar = invite_meta.get("avatar", "")

    ctx.actor_username = _first_non_empty(ctx.actor_username, refs["actor_username"]).lstrip("@")
    ctx.actor_name = _first_non_empty(ctx.actor_name, refs["actor_name"])
    ctx.actor_avatar = _first_non_empty(ctx.actor_avatar, refs["actor_avatar"])

    ctx.team_slug = _first_non_empty(ctx.team_slug, refs["team_slug"])
    ctx.team_name = _first_non_empty(ctx.team_name, refs["team_name"])
    ctx.team_logo = _first_non_empty(ctx.team_logo, refs["team_logo"])

    ctx.tournament_slug = _first_non_empty(refs["tournament_slug"])
    ctx.tournament_name = _first_non_empty(refs["tournament_name"])
    ctx.tournament_image = _first_non_empty(refs["tournament_image"])

    ctx.organization_slug = _first_non_empty(refs["organization_slug"])
    ctx.organization_name = _first_non_empty(refs["organization_name"])
    ctx.organization_logo = _first_non_empty(refs["organization_logo"])

    fallback_actor = _extract_username_from_text(notification)
    ctx.actor_username = _first_non_empty(ctx.actor_username, fallback_actor).lstrip("@")

    if ctx.actor_username:
        actor_meta = user_map.get(ctx.actor_username.lower())
        if actor_meta:
            ctx.actor_name = _first_non_empty(ctx.actor_name, actor_meta.get("name", ""), actor_meta.get("username", ""))
            ctx.actor_username = _first_non_empty(actor_meta.get("username", ""), ctx.actor_username)
            ctx.actor_avatar = _first_non_empty(ctx.actor_avatar, actor_meta.get("avatar", ""))

    team_meta = None
    if ctx.team_slug:
        team_meta = team_map.get(f"slug:{ctx.team_slug}")
    if not team_meta and refs["team_id"] is not None:
        team_meta = team_map.get(f"id:{refs['team_id']}")
    if team_meta:
        ctx.team_slug = _first_non_empty(ctx.team_slug, team_meta.get("slug", ""))
        ctx.team_name = _first_non_empty(ctx.team_name, team_meta.get("name", ""))
        ctx.team_logo = _first_non_empty(ctx.team_logo, team_meta.get("logo", ""))

    direct_url = _first_non_empty(notification.action_url, notification.url)
    if not ctx.team_slug:
        url_team_slug = _extract_slug_from_url(direct_url, "teams")
        if url_team_slug:
            ctx.team_slug = url_team_slug
            url_team_meta = team_map.get(f"slug:{url_team_slug}")
            if url_team_meta:
                ctx.team_name = _first_non_empty(ctx.team_name, url_team_meta.get("name", ""))
                ctx.team_logo = _first_non_empty(ctx.team_logo, url_team_meta.get("logo", ""))

    tournament_meta = None
    if refs["tournament_id"] is not None:
        tournament_meta = tournament_map.get(f"id:{refs['tournament_id']}")
    if not tournament_meta and ctx.tournament_slug:
        tournament_meta = tournament_map.get(f"slug:{ctx.tournament_slug}")
    if tournament_meta:
        ctx.tournament_slug = _first_non_empty(ctx.tournament_slug, tournament_meta.get("slug", ""))
        ctx.tournament_name = _first_non_empty(ctx.tournament_name, tournament_meta.get("name", ""))
        ctx.tournament_image = _first_non_empty(ctx.tournament_image, tournament_meta.get("image", ""))

    if not ctx.tournament_slug:
        url_tournament_slug = _extract_slug_from_url(direct_url, "tournaments")
        if url_tournament_slug:
            ctx.tournament_slug = url_tournament_slug
            url_tournament_meta = tournament_map.get(f"slug:{url_tournament_slug}")
            if url_tournament_meta:
                ctx.tournament_name = _first_non_empty(ctx.tournament_name, url_tournament_meta.get("name", ""))
                ctx.tournament_image = _first_non_empty(ctx.tournament_image, url_tournament_meta.get("image", ""))

    organization_meta = None
    if refs["organization_id"] is not None:
        organization_meta = organization_map.get(f"id:{refs['organization_id']}")
    if not organization_meta and ctx.organization_slug:
        organization_meta = organization_map.get(f"slug:{ctx.organization_slug}")
    if organization_meta:
        ctx.organization_slug = _first_non_empty(ctx.organization_slug, organization_meta.get("slug", ""))
        ctx.organization_name = _first_non_empty(ctx.organization_name, organization_meta.get("name", ""))
        ctx.organization_logo = _first_non_empty(ctx.organization_logo, organization_meta.get("logo", ""))

    if not ctx.organization_slug:
        url_org_slug = _extract_slug_from_url(direct_url, "orgs")
        if url_org_slug:
            ctx.organization_slug = url_org_slug
            url_org_meta = organization_map.get(f"slug:{url_org_slug}")
            if url_org_meta:
                ctx.organization_name = _first_non_empty(ctx.organization_name, url_org_meta.get("name", ""))
                ctx.organization_logo = _first_non_empty(ctx.organization_logo, url_org_meta.get("logo", ""))

    if not ctx.actor_username and "/@" in direct_url:
        url_user = _extract_slug_from_url(direct_url, "@")
        if url_user:
            ctx.actor_username = url_user
            actor_meta = user_map.get(url_user.lower())
            if actor_meta:
                ctx.actor_name = _first_non_empty(ctx.actor_name, actor_meta.get("name", ""), actor_meta.get("username", ""))
                ctx.actor_avatar = _first_non_empty(ctx.actor_avatar, actor_meta.get("avatar", ""))

    return ctx


def _resolve_title(notification: Notification, notification_type: str, follow_meta: dict | None, invite_meta: dict | None) -> str:
    if notification.title:
        return notification.title
    if follow_meta and notification.type == Notification.Type.USER_FOLLOWED:
        return "New Follower"
    if follow_meta:
        return "Follow Request"
    if invite_meta:
        return "Team Join Request"
    if notification_type == Notification.NotificationCategory.ECONOMY:
        return "DeltaCoin Update"
    if notification_type == Notification.NotificationCategory.SOCIAL:
        return "Community Update"
    if notification_type == Notification.NotificationCategory.TEAM:
        return "Roster Update"
    if notification_type == Notification.NotificationCategory.WARNING:
        return "Account Warning"
    return "Notification"


def _inject_known_entity_links(base_text: str, ctx: EntityContext) -> tuple[str, bool]:
    text = escape(base_text)
    replaced = False

    def replace_all_ci(target: str, replacement: str):
        nonlocal text, replaced
        if not target:
            return
        safe_target = escape(target.strip())
        if not safe_target:
            return
        new_text, count = re.subn(re.escape(safe_target), replacement, text, flags=re.IGNORECASE)
        if count > 0:
            text = new_text
            replaced = True

    if ctx.actor_username:
        mention_link = _user_span_label(ctx.actor_username, ctx.actor_username, include_at=True)
        plain_label = ctx.actor_name or ctx.actor_username
        plain_link = _user_span_label(ctx.actor_username, plain_label, include_at=False)
        mention_token = f"@{ctx.actor_username}"
        if re.search(re.escape(escape(mention_token)), text, flags=re.IGNORECASE):
            replace_all_ci(mention_token, mention_link)
        else:
            replace_all_ci(ctx.actor_name, plain_link)
            replace_all_ci(ctx.actor_username, plain_link)

    if ctx.team_slug or ctx.team_name:
        team_link = _team_span(ctx.team_name or "Team", ctx.team_slug)
        replace_all_ci(ctx.team_name, team_link)

    if ctx.tournament_slug or ctx.tournament_name:
        tournament_link = _tourney_span(ctx.tournament_name or "Tournament", ctx.tournament_slug)
        replace_all_ci(ctx.tournament_name, tournament_link)

    if ctx.organization_slug or ctx.organization_name:
        org_link = _org_span(ctx.organization_name or "Organization", ctx.organization_slug)
        replace_all_ci(ctx.organization_name, org_link)

    return text, replaced


def _build_related_links(ctx: EntityContext) -> str:
    links: list[str] = []
    if ctx.actor_username:
        links.append(_user_span(ctx.actor_username))
    if ctx.team_slug or ctx.team_name:
        links.append(_team_span(ctx.team_name or "Team", ctx.team_slug))
    if ctx.tournament_slug or ctx.tournament_name:
        links.append(_tourney_span(ctx.tournament_name or "Tournament", ctx.tournament_slug))
    if ctx.organization_slug or ctx.organization_name:
        links.append(_org_span(ctx.organization_name or "Organization", ctx.organization_slug))
    return " <span class=\"text-slate-500\">&middot;</span> ".join(links)


def _build_html_text(notification: Notification, ctx: EntityContext) -> str:
    source_text = _first_non_empty(notification.message, notification.body, strip_tags(notification.html_text), notification.title)
    if not source_text:
        return _build_related_links(ctx)

    linked_text, _ = _inject_known_entity_links(source_text, ctx)
    return linked_text


def _build_title_html(notification: Notification, title_text: str, ctx: EntityContext) -> str:
    linked_title, _ = _inject_known_entity_links(title_text, ctx)
    return linked_title


def _resolve_action_link(notification: Notification, notification_type: str, ctx: EntityContext) -> str:
    direct = _first_non_empty(notification.action_url, notification.url)

    if ctx.ref_type == "tournament" and ctx.tournament_slug:
        return f"/tournaments/{ctx.tournament_slug}/hub/"
    if ctx.ref_type == "team" and ctx.team_slug:
        return f"/teams/{ctx.team_slug}/"
    if ctx.ref_type == "organization" and ctx.organization_slug:
        return f"/orgs/{ctx.organization_slug}/"
    if ctx.ref_type == "user" and ctx.actor_username:
        return f"/@{ctx.actor_username}/"

    if notification_type in {Notification.NotificationCategory.TOURNAMENT, Notification.NotificationCategory.ECONOMY} and ctx.tournament_slug:
        return f"/tournaments/{ctx.tournament_slug}/hub/"
    if notification_type == Notification.NotificationCategory.TEAM and ctx.team_slug:
        return f"/teams/{ctx.team_slug}/"
    if notification_type == Notification.NotificationCategory.SOCIAL and ctx.actor_username:
        return f"/@{ctx.actor_username}/"

    if ctx.team_slug:
        return f"/teams/{ctx.team_slug}/"
    if ctx.tournament_slug:
        return f"/tournaments/{ctx.tournament_slug}/hub/"
    if ctx.organization_slug:
        return f"/orgs/{ctx.organization_slug}/"
    if ctx.actor_username:
        return f"/@{ctx.actor_username}/"

    return direct


def _build_actions(notification: Notification, follow_meta: dict | None, invite_meta: dict | None) -> list[dict]:
    raw_action_data = getattr(notification, "action_data", None)
    if isinstance(raw_action_data, list):
        return [action for action in raw_action_data if isinstance(action, dict)]
    if isinstance(raw_action_data, dict):
        actions = raw_action_data.get("actions")
        if isinstance(actions, list):
            return [action for action in actions if isinstance(action, dict)]

    if follow_meta and follow_meta.get("is_pending"):
        request_id = notification.action_object_id
        return [
            {"label": "Accept", "style": "primary", "icon": "check", "id": f"follow_accept_{request_id}"},
            {"label": "Decline", "style": "secondary", "icon": "x", "id": f"follow_reject_{request_id}"},
        ]

    if invite_meta and invite_meta.get("is_pending"):
        invite_id = notification.action_object_id
        return [
            {"label": "Accept", "style": "primary", "icon": "check", "id": f"invite_accept_{invite_id}"},
            {"label": "Decline", "style": "secondary", "icon": "x", "id": f"invite_decline_{invite_id}"},
        ]

    if notification.is_actionable and (notification.action_url or notification.url):
        return [
            {
                "label": notification.action_label or "View Details",
                "style": "secondary",
                "icon": "eye",
                "id": f"open_{notification.id}",
            }
        ]

    return []


def map_notifications_to_payload(items: Iterable[Notification]) -> list[dict]:
    item_list = list(items)
    follow_map, invite_map, user_map, team_map, tournament_map, organization_map = _build_related_maps(item_list)

    payload: list[dict] = []
    for n in item_list:
        follow_meta = follow_map.get(n.action_object_id) if n.action_object_id else None
        invite_meta = invite_map.get(n.action_object_id) if n.action_object_id else None

        notification_type = _normalize_notification_type(n)
        ctx = _resolve_entity_context(n, follow_meta, invite_meta, user_map, team_map, tournament_map, organization_map)

        action_link = _resolve_action_link(n, notification_type, ctx)
        html_text = _build_html_text(n, ctx)
        title_text = _resolve_title(n, notification_type, follow_meta, invite_meta)
        title_html = _build_title_html(n, title_text, ctx)

        is_invite = bool(invite_meta) or n.type in {
            Notification.Type.INVITE_SENT,
            Notification.Type.JOIN_REQUEST_RECEIVED,
            Notification.Type.JOIN_REQUEST_ACCEPTED,
            Notification.Type.JOIN_REQUEST_DECLINED,
        }

        entry = {
            "id": n.id,
            "type": notification_type,
            "notification_type": notification_type,
            "read": n.is_read,
            "timestamp": n.created_at.isoformat(),
            "title": title_text,
            "titleHtml": title_html,
            "title_html": title_html,
            "htmlText": html_text,
            "html_text": html_text,
            "avatar": None,
            "avatar_url": None,
            "image": None,
            "image_url": None,
            "actionLink": action_link or "",
            "actions": _build_actions(n, follow_meta, invite_meta),
            "action_data": n.action_data if isinstance(n.action_data, (dict, list)) else {},
            "isInvite": is_invite,
            "priority": n.priority,
        }

        ref_pref = ctx.ref_type
        if not ref_pref:
            if notification_type == Notification.NotificationCategory.SOCIAL and ctx.actor_username:
                ref_pref = "user"
            elif notification_type == Notification.NotificationCategory.TEAM and (ctx.team_slug or ctx.team_name):
                ref_pref = "team"
            elif notification_type in {Notification.NotificationCategory.TOURNAMENT, Notification.NotificationCategory.ECONOMY} and (
                ctx.tournament_slug or ctx.tournament_name
            ):
                ref_pref = "tournament"

        avatar = _first_non_empty(n.avatar_url)
        image = _first_non_empty(n.image_url)

        if ref_pref == "user" and (ctx.actor_avatar or avatar):
            avatar = _first_non_empty(ctx.actor_avatar, avatar)
            if not avatar and ctx.actor_username:
                avatar = _ui_avatar_url(ctx.actor_name or ctx.actor_username, "334155")
        elif ref_pref == "team" and (ctx.team_logo or image):
            image = _first_non_empty(ctx.team_logo, image)
            if not image and (ctx.team_name or ctx.team_slug):
                image = _ui_avatar_url(ctx.team_name or ctx.team_slug, "4c1d95")
        elif ref_pref == "tournament" and (ctx.tournament_image or image):
            image = _first_non_empty(ctx.tournament_image, image)
            if not image and (ctx.tournament_name or ctx.tournament_slug):
                image = _ui_avatar_url(ctx.tournament_name or ctx.tournament_slug, "92400e")
        elif ref_pref == "organization" and (ctx.organization_logo or image):
            image = _first_non_empty(ctx.organization_logo, image)
            if not image and (ctx.organization_name or ctx.organization_slug):
                image = _ui_avatar_url(ctx.organization_name or ctx.organization_slug, "0e7490")
        else:
            if ctx.actor_avatar:
                avatar = _first_non_empty(ctx.actor_avatar, avatar)
            elif ctx.team_logo:
                image = _first_non_empty(ctx.team_logo, image)
            elif ctx.tournament_image:
                image = _first_non_empty(ctx.tournament_image, image)
            elif ctx.organization_logo:
                image = _first_non_empty(ctx.organization_logo, image)

            if not avatar and ctx.actor_username:
                avatar = _ui_avatar_url(ctx.actor_name or ctx.actor_username, "334155")
            elif not image and (ctx.team_name or ctx.team_slug):
                image = _ui_avatar_url(ctx.team_name or ctx.team_slug, "4c1d95")
            elif not image and (ctx.tournament_name or ctx.tournament_slug):
                image = _ui_avatar_url(ctx.tournament_name or ctx.tournament_slug, "92400e")
            elif not image and (ctx.organization_name or ctx.organization_slug):
                image = _ui_avatar_url(ctx.organization_name or ctx.organization_slug, "0e7490")

        if avatar:
            entry["avatar"] = avatar
            entry["avatar_url"] = avatar
        elif image:
            entry["image"] = image
            entry["image_url"] = image

        payload.append(entry)

    return payload


def get_feed_page(user, page: int = 1, page_size: int = 20) -> NotificationFeedPage:
    safe_page_size = max(1, min(page_size, 50))
    paginator = Paginator(build_notification_queryset(user), safe_page_size)
    current_page = paginator.get_page(page)
    mapped = map_notifications_to_payload(current_page.object_list)
    return NotificationFeedPage(
        items=mapped,
        page=current_page.number,
        page_size=safe_page_size,
        total=paginator.count,
        has_next=current_page.has_next(),
    )


def get_preview_payload(user, limit: int = 8) -> list[dict]:
    safe_limit = max(1, min(limit, 20))
    queryset = build_notification_queryset(user)[:safe_limit]
    return map_notifications_to_payload(queryset)
