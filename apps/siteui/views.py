from __future__ import annotations
from datetime import datetime, time, timedelta
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.shortcuts import render, redirect
from django.utils import timezone
from django.apps import apps
from django.contrib.auth import get_user_model
from .services import compute_stats, get_spotlight, get_timeline
from django.apps import apps as django_apps
from typing import Any, Iterable
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Count
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from .utils.embeds import build_embed_url



def home(request):
    """DeltaCrown homepage - Modern newspaper-style esports platform."""
    from .homepage_context import get_homepage_context
    context = get_homepage_context()
    return render(request, "home.html", context)


def privacy(request):
    return render(request, "legal/privacy_policy.html")


def terms(request):
    return render(request, "legal/terms_of_service.html")


def cookies(request):
    return render(request, "legal/cookie_policy.html")

def ui_showcase(request):
    game_opts = [
        ("valorant", "Valorant", True),
        ("efootball", "eFootball", False),
        ("pubg", "PUBG Mobile", False),
    ]
    radio_opts = [
        ("mode-solo", "solo", "Solo", True),
        ("mode-duo", "duo", "Duo", False),
        ("mode-squad", "squad", "Squad", False),
    ]
    return render(request, "ui_showcase.html", {"game_opts": game_opts, "radio_opts": radio_opts})

def about(request):
    # Optionally compute stats here
    stats = {
        "players": None,
        "matches": None,
        "prize_paid": None,
        "streams": None,
    }
    return render(request, "about.html", {"stats": stats})




def _get_model(candidates):
    """Return the first model that exists from [(app_label, model_name), ...]."""
    for app_label, model_name in candidates:
        try:
            return django_apps.get_model(app_label, model_name)
        except Exception:
            continue
    return None

def community(request):
    """
    Community Hub — initial page load.
    Serves the shell template; all data is loaded via the JSON API.
    """
    return render(request, 'pages/community.html')


# ── Community JSON API ──────────────────────────────────────────────────────

def _serialize_post(post, request_user=None):
    """Serialize a CommunityPost to a JSON-safe dict."""
    author = post.author
    avatar_url = None
    if author and getattr(author, 'avatar', None):
        try:
            avatar_url = author.avatar.url
        except (ValueError, AttributeError):
            pass

    display_name = ''
    username = ''
    if author and author.user:
        display_name = author.display_name or author.user.get_full_name() or author.user.username
        username = author.user.username

    media_list = []
    for m in post.media.all():
        try:
            media_list.append({
                'id': m.id,
                'type': m.media_type,
                'url': m.file.url,
                'alt': m.alt_text or '',
            })
        except (ValueError, AttributeError):
            pass

    liked_by_me = False
    if request_user and request_user.is_authenticated:
        profile = getattr(request_user, 'profile', None)
        if profile:
            liked_by_me = post.likes.filter(user=profile).exists()

    # Team info (if posted on behalf of a team)
    team_data = None
    if post.team_id:
        t = post.team
        team_logo = None
        if t and t.logo:
            try:
                team_logo = t.logo.url
            except (ValueError, AttributeError):
                pass
        if t:
            team_data = {
                'id': t.id,
                'name': t.name,
                'slug': t.slug,
                'tag': t.tag or '',
                'logo_url': team_logo,
            }

    return {
        'id': post.id,
        'title': post.title or '',
        'content': post.content,
        'game': post.game or '',
        'visibility': post.visibility,
        'is_pinned': post.is_pinned,
        'is_featured': post.is_featured,
        'likes_count': post.likes_count,
        'comments_count': post.comments_count,
        'shares_count': post.shares_count,
        'created_at': post.created_at.isoformat(),
        'author': {
            'username': username,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'profile_url': f'/profile/{username}/' if username else '#',
        },
        'team': team_data,
        'media': media_list,
        'liked_by_me': liked_by_me,
    }


def _serialize_comment(comment):
    """Serialize a CommunityPostComment."""
    author = comment.author
    avatar_url = None
    if author and getattr(author, 'avatar', None):
        try:
            avatar_url = author.avatar.url
        except (ValueError, AttributeError):
            pass
    display_name = ''
    username = ''
    if author and author.user:
        display_name = author.display_name or author.user.get_full_name() or author.user.username
        username = author.user.username

    return {
        'id': comment.id,
        'content': comment.content,
        'parent_id': comment.parent_id,
        'created_at': comment.created_at.isoformat(),
        'author': {
            'username': username,
            'display_name': display_name,
            'avatar_url': avatar_url,
        },
    }


def community_api_feed(request):
    """
    GET /community/api/feed/?page=1&game=&q=
    Returns paginated posts as JSON.
    """
    from django.http import JsonResponse
    from .models import CommunityPost

    page = int(request.GET.get('page', 1))
    per_page = 10
    game = request.GET.get('game', '').strip()
    q = request.GET.get('q', '').strip()

    qs = CommunityPost.objects.filter(
        visibility='public', is_approved=True
    ).select_related('author', 'author__user', 'team').prefetch_related('media', 'likes').order_by(
        '-is_pinned', '-is_featured', '-created_at'
    )

    if game:
        qs = qs.filter(game__iexact=game)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(content__icontains=q) |
            Q(author__user__username__icontains=q)
        )

    total = qs.count()
    start = (page - 1) * per_page
    posts = list(qs[start:start + per_page])

    return JsonResponse({
        'posts': [_serialize_post(p, request.user) for p in posts],
        'page': page,
        'total': total,
        'has_next': (start + per_page) < total,
    })


def community_api_create_post(request):
    """
    POST /community/api/posts/create/
    JSON body: {title, content, game, visibility}
    """
    from django.http import JsonResponse
    import json

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    from apps.user_profile.models import UserProfile
    from .models import CommunityPost, CommunityPostMedia

    try:
        # Support both JSON and multipart
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        content = (data.get('content') or '').strip()
        if not content:
            return JsonResponse({'error': 'Content is required.'}, status=400)

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'display_name': request.user.get_full_name() or request.user.username}
        )

        # Team posting support
        team_id = data.get('team_id')
        team_obj = None
        if team_id:
            from apps.organizations.models import Team
            from apps.organizations.models.membership import TeamMembership
            try:
                team_obj = Team.objects.get(pk=int(team_id))
                # Verify user has permission (OWNER or MANAGER)
                has_perm = TeamMembership.objects.filter(
                    team=team_obj, user=request.user,
                    status='ACTIVE', role__in=['OWNER', 'MANAGER']
                ).exists()
                if not has_perm:
                    return JsonResponse({'error': 'You do not have permission to post for this team.'}, status=403)
            except (Team.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Team not found.'}, status=404)

        post = CommunityPost.objects.create(
            author=profile,
            team=team_obj,
            title=(data.get('title') or '').strip(),
            content=content,
            game=(data.get('game') or '').strip(),
            visibility=data.get('visibility', 'public'),
        )

        files = request.FILES.getlist('media_files')
        for f in files:
            CommunityPostMedia.objects.create(
                post=post, file=f,
                media_type='image' if f.content_type.startswith('image/') else 'video',
            )

        return JsonResponse({
            'success': True,
            'post': _serialize_post(post, request.user),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def community_api_like(request, post_id):
    """
    POST /community/api/posts/<id>/like/
    Toggle like. Returns new like count.
    """
    from django.http import JsonResponse
    from .models import CommunityPost, CommunityPostLike

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.user_profile.models import UserProfile
    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'display_name': request.user.username}
        )

    try:
        post = CommunityPost.objects.get(id=post_id, visibility='public', is_approved=True)
    except CommunityPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)

    existing = CommunityPostLike.objects.filter(post=post, user=profile).first()
    if existing:
        existing.delete()
        post.likes_count = max(0, post.likes_count - 1)
        post.save(update_fields=['likes_count'])
        return JsonResponse({'liked': False, 'likes_count': post.likes_count})
    else:
        CommunityPostLike.objects.create(post=post, user=profile)
        post.likes_count = post.likes_count + 1
        post.save(update_fields=['likes_count'])
        return JsonResponse({'liked': True, 'likes_count': post.likes_count})


def community_api_comments(request, post_id):
    """
    GET  /community/api/posts/<id>/comments/  — list comments
    POST /community/api/posts/<id>/comments/  — add comment
    """
    from django.http import JsonResponse
    import json
    from .models import CommunityPost, CommunityPostComment

    try:
        post = CommunityPost.objects.get(id=post_id, visibility='public', is_approved=True)
    except CommunityPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)

    if request.method == 'GET':
        comments = CommunityPostComment.objects.filter(
            post=post, is_approved=True
        ).select_related('author', 'author__user').order_by('created_at')[:100]
        return JsonResponse({
            'comments': [_serialize_comment(c) for c in comments],
        })

    # POST — add comment
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.user_profile.models import UserProfile
    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'display_name': request.user.username}
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Content is required.'}, status=400)

    parent_id = data.get('parent_id')
    parent = None
    if parent_id:
        parent = CommunityPostComment.objects.filter(id=parent_id, post=post).first()

    comment = CommunityPostComment.objects.create(
        post=post, author=profile, content=content, parent=parent,
    )
    post.comments_count = post.comments_count + 1
    post.save(update_fields=['comments_count'])

    return JsonResponse({
        'success': True,
        'comment': _serialize_comment(comment),
        'comments_count': post.comments_count,
    })


def community_api_sidebar(request):
    """
    GET /community/api/sidebar/
    Featured teams, games, stats for the sidebar widgets.
    """
    from django.http import JsonResponse
    from apps.organizations.models import Team
    from apps.organizations.choices import TeamStatus
    from apps.games.models import Game as GameModel
    from .models import CommunityPost
    from django.db.models import Count

    # Featured teams (active, with most members)
    teams = (
        Team.objects.filter(status=TeamStatus.ACTIVE)
        .annotate(member_count=Count('vnext_memberships'))
        .order_by('-member_count')[:6]
    )

    # Pre-fetch game names for teams that reference a game_id (int FK)
    game_ids = [t.game_id for t in teams if t.game_id]
    game_map = {}
    if game_ids:
        for g in GameModel.objects.filter(pk__in=game_ids):
            game_map[g.pk] = g.display_name or g.name

    teams_data = []
    for t in teams:
        logo_url = None
        if t.logo:
            try:
                logo_url = t.logo.url
            except (ValueError, AttributeError):
                pass
        teams_data.append({
            'name': t.name,
            'slug': t.slug,
            'tag': t.tag or '',
            'logo_url': logo_url,
            'game': game_map.get(t.game_id, ''),
            'member_count': t.member_count,
        })

    # Games
    games = GameModel.objects.filter(is_active=True).order_by('name')
    games_data = []
    for g in games:
        icon_url = None
        if g.icon:
            try:
                icon_url = g.icon.url
            except (ValueError, AttributeError):
                pass
        games_data.append({
            'name': g.display_name or g.name,
            'slug': g.slug,
            'icon_url': icon_url,
        })

    # Stats
    total_posts = CommunityPost.objects.filter(visibility='public', is_approved=True).count()
    total_teams = Team.objects.filter(status=TeamStatus.ACTIVE).count()

    return JsonResponse({
        'teams': teams_data,
        'games': games_data,
        'stats': {
            'total_posts': total_posts,
            'total_teams': total_teams,
            'total_games': len(games_data),
        },
    })


def community_api_delete_post(request, post_id):
    """
    POST /community/api/posts/<id>/delete/
    Delete own post.
    """
    from django.http import JsonResponse
    from .models import CommunityPost

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        post = CommunityPost.objects.get(id=post_id)
    except CommunityPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)

    if post.author.user != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    post.delete()
    return JsonResponse({'success': True})


def community_api_user_teams(request):
    """
    GET /community/api/user-teams/
    Returns teams the current user can post on behalf of (OWNER or MANAGER role).
    """
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'teams': []})

    from apps.organizations.models.membership import TeamMembership
    memberships = TeamMembership.objects.filter(
        user=request.user, status='ACTIVE', role__in=['OWNER', 'MANAGER']
    ).select_related('team')

    teams_data = []
    for m in memberships:
        t = m.team
        logo_url = None
        if t.logo:
            try:
                logo_url = t.logo.url
            except (ValueError, AttributeError):
                pass
        teams_data.append({
            'id': t.id,
            'name': t.name,
            'slug': t.slug,
            'tag': t.tag or '',
            'logo_url': logo_url,
            'role': m.role,
        })

    return JsonResponse({'teams': teams_data})


def handle_community_post_creation(request):
    """Handle AJAX request for creating community posts"""
    from django.http import JsonResponse
    from django.urls import reverse
    from .models import CommunityPostMedia
    from .forms import CommunityPostCreateForm
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        form = CommunityPostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            # Get or create user profile
            user_profile = getattr(request.user, 'profile', None)
            if not user_profile:
                # If no profile exists, create one
                from apps.user_profile.models import UserProfile
                user_profile, created = UserProfile.objects.get_or_create(
                    user=request.user,
                    defaults={'display_name': request.user.get_full_name() or request.user.username}
                )
            
            # Create the community post
            post = form.save(commit=False)
            post.author = user_profile
            post.save()
            
            # Handle multiple file uploads
            files = request.FILES.getlist('media_files')
            for file in files:
                CommunityPostMedia.objects.create(
                    post=post,
                    file=file,
                    media_type='image' if file.content_type.startswith('image/') else 'video'
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Post created successfully!',
                'redirect': reverse('siteui:community')
            })
        else:
            return JsonResponse({
                'error': 'Invalid form data',
                'errors': form.errors
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)


# ---- Helpers ----------------------------------------------------------------

def first_attr(obj: Any, names: Iterable[str], default=None):
    """Return the first present attribute/attr.url from `names` on `obj`."""
    for name in names:
        try:
            v = getattr(obj, name)
        except Exception:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        if hasattr(v, "url"):  # FileField or ImageField
            try:
                return v.url
            except Exception:
                pass
        if v not in (None, ""):
            return v
    return default

def to_strlist(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        # split by space or comma
        parts = [x.strip() for x in val.replace(",", " ").split() if x.strip()]
        return parts
    if isinstance(val, (list, tuple, set)):
        return [str(x) for x in val if x is not None]
    return [str(val)]

def normalize_stream(obj, request=None) -> dict[str, Any]:
    """
    Normalize any 'stream-like' object into the template dict:
    title, embed_url, watch_url, thumbnail_url, channel, game,
    viewers, tags, is_live, start_time, platform.
    """
    url = first_attr(obj, ("embed_url", "watch_url", "url", "video_url", "stream_url"), "")
    embed_url, platform = build_embed_url(url, host_for_twitch_parent=(request.get_host() if request else None))
    return {
        "title": first_attr(obj, ("title", "name"), "Stream"),
        "embed_url": embed_url or None,
        "watch_url": first_attr(obj, ("watch_url", "url", "permalink"), url),
        "thumbnail_url": first_attr(obj, ("thumbnail_url", "thumbnail", "cover_url", "image_url", "image")),
        "channel": first_attr(obj, ("channel", "channel_name", "owner", "organizer", "author")),
        "game": first_attr(obj, ("game", "game_name", "category")),
        "viewers": first_attr(obj, ("viewers", "viewer_count", "concurrent_viewers")),
        "tags": to_strlist(first_attr(obj, ("tags",), [])),
        "is_live": bool(first_attr(obj, ("is_live", "live"), False)),
        "start_time": first_attr(obj, ("start_time", "started_at", "created_at", "start_at")),
        "platform": platform or first_attr(obj, ("platform",), ""),
    }

def normalize_vod(obj, request=None) -> dict[str, Any]:
    url = first_attr(obj, ("embed_url", "watch_url", "url", "video_url"), "")
    embed_url, platform = build_embed_url(url, host_for_twitch_parent=(request.get_host() if request else None))
    return {
        "title": first_attr(obj, ("title", "name"), "Replay"),
        "embed_url": embed_url or None,
        "watch_url": first_attr(obj, ("watch_url", "url", "permalink"), url),
        "thumbnail_url": first_attr(obj, ("thumbnail_url", "thumbnail", "cover_url", "image_url", "image")),
        "channel": first_attr(obj, ("channel", "channel_name", "owner", "organizer", "author")),
        "game": first_attr(obj, ("game", "game_name", "category")),
        "duration": first_attr(obj, ("duration", "length", "duration_str")),
        "published_at": first_attr(obj, ("published_at", "created_at", "start_time")),
        "platform": platform or first_attr(obj, ("platform",), ""),
    }

def normalize_upcoming(obj) -> dict[str, Any]:
    return {
        "title": first_attr(obj, ("title", "name"), "Upcoming broadcast"),
        "game": first_attr(obj, ("game", "game_name", "category")),
        "scheduled_for": first_attr(obj, ("scheduled_for", "start_at", "starts_at", "start_time")),
        "channel": first_attr(obj, ("channel", "channel_name", "organizer")),
        "platform": first_attr(obj, ("platform",), ""),
        "cta_url": first_attr(obj, ("cta_url", "notify_url", "url")),
    }

def try_get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None

# ---- Arena selectors ---------------------------------------------------------

ARENA_LIVE_STATES = ("live", "pending_result")
ARENA_UPCOMING_STATES = ("scheduled", "check_in", "ready")
ARENA_RESULT_STATES = ("completed", "disputed", "forfeit", "cancelled")
ARENA_AJAX_TRUE_VALUES = {"1", "true", "yes", "on"}


def _is_arena_async_request(request) -> bool:
    ajax_hint = (request.GET.get("ajax") or "").strip().lower()
    if ajax_hint in ARENA_AJAX_TRUE_VALUES:
        return True

    requested_with = (request.headers.get("x-requested-with") or "").strip().lower()
    return requested_with == "xmlhttprequest"


def _group_matches_by_tournament(matches):
    grouped = []
    for match in matches:
        contract = _to_arena_match_contract(match)
        grouper = (match.get("tournament_name") or "").strip() or "Tournament"
        if grouped and grouped[-1]["grouper"] == grouper:
            grouped[-1]["list"].append(contract)
            if not grouped[-1].get("game_icon_url") and contract.get("game_icon_url"):
                grouped[-1]["game_icon_url"] = contract.get("game_icon_url")
            continue
        grouped.append({
            "grouper": grouper,
            "game_icon_url": contract.get("game_icon_url") or "",
            "list": [contract],
        })
    return grouped


def _to_arena_match_contract(match):
    return {
        "team_a": match.get("team_a") or "TBD",
        "team_b": match.get("team_b") or "TBD",
        "game_name": match.get("game_name") or "",
        "team_a_logo": match.get("team_a_logo") or "",
        "team_b_logo": match.get("team_b_logo") or "",
        "team_a_tag": match.get("team_a_tag") or "A",
        "team_b_tag": match.get("team_b_tag") or "B",
        "score_a": match.get("score_a"),
        "score_b": match.get("score_b"),
        "is_live": bool(match.get("is_live")),
        "scheduled_time": match.get("scheduled_time"),
        "match_url": match.get("match_url") or "",
        "stream_url": match.get("stream_url") or "",
        "embed_url": match.get("embed_url") or "",
        "game_icon_url": match.get("game_icon_url") or "",
        "details": match.get("details") or "",
        "subtext": match.get("details") or "",
    }


def _build_arena_async_payload(
    request,
    *,
    selected_game: str,
    selected_tab: str,
    search_query: str,
    selected_date=None,
):
    match_payload = _fetch_arena_matches(
        request,
        selected_game=selected_game,
        search_query=search_query,
        selected_date=selected_date,
        include_logos=True,
        only_tab=selected_tab,
    )

    if selected_tab == "upcoming":
        tab_matches = match_payload["upcoming_matches"]
    elif selected_tab == "results":
        tab_matches = match_payload["result_matches"]
    else:
        tab_matches = match_payload["live_matches"]

    return {
        "groups": _group_matches_by_tournament(tab_matches),
    }


def _safe_queryset_list(queryset, limit=None):
    try:
        if limit is not None:
            queryset = queryset[:limit]
        return list(queryset)
    except (ProgrammingError, OperationalError):
        return []


def _safe_reverse(url_name, **kwargs):
    try:
        return reverse(url_name, kwargs=kwargs)
    except Exception:
        return "#"


def _with_twitch_parent(embed_url: str, provider: str, host: str) -> str:
    clean_embed = (embed_url or "").strip()
    if not clean_embed:
        return ""

    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider != "twitch" and "player.twitch.tv" not in clean_embed:
        return clean_embed

    parent_host = (host or "").split(":")[0] or "localhost"
    if "__PARENT_HOST__" in clean_embed:
        return clean_embed.replace("__PARENT_HOST__", parent_host)
    if "parent=" in clean_embed:
        return clean_embed
    separator = "&" if "?" in clean_embed else "?"
    return f"{clean_embed}{separator}parent={parent_host}"


def _with_youtube_origin(embed_url: str, request) -> str:
    clean_embed = (embed_url or "").strip()
    if not clean_embed:
        return ""

    lower_embed = clean_embed.lower()
    is_youtube_embed = (
        "youtube.com/embed/" in lower_embed
        or "youtube-nocookie.com/embed/" in lower_embed
    )
    if not is_youtube_embed:
        return clean_embed

    origin = f"{request.scheme}://{request.get_host()}"
    parts = urlsplit(clean_embed)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    query.setdefault("autoplay", "1")
    query.setdefault("mute", "1")
    query.setdefault("rel", "0")
    query.setdefault("enablejsapi", "1")
    query["origin"] = origin
    query["widget_referrer"] = origin

    normalized_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))


def _derive_team_tag(name: str) -> str:
    if not name:
        return "TBD"
    compact = "".join(ch for ch in name.upper() if ch.isalnum())
    if len(compact) >= 3:
        return compact[:3]
    words = [part for part in name.split() if part]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return compact[:3] or "TBD"


def _resolve_tournament_stream_url(tournament) -> str:
    return (
        (tournament.stream_youtube_url or "").strip()
        or (tournament.stream_twitch_url or "").strip()
    )


def _resolve_match_stream_url(match) -> str:
    return (match.stream_url or "").strip() or _resolve_tournament_stream_url(match.tournament)


def _resolve_arena_match_details(match) -> str:
    explicit = ""
    for attr in ("details", "subtext", "subtitle", "round_label"):
        value = getattr(match, attr, None)
        if not value:
            continue
        explicit = str(value).strip()
        if explicit:
            return explicit

    bo_text = ""
    best_of = getattr(match, "best_of", None)
    if isinstance(best_of, int) and best_of > 1:
        bo_text = f"BO{best_of} Series"

    round_text = ""
    round_number = getattr(match, "round_number", None)
    bracket = getattr(match, "bracket", None)
    if bracket and round_number:
        try:
            round_name = bracket.get_round_name(round_number)
            if round_name:
                round_text = str(round_name).strip()
        except Exception:
            round_text = ""
    if not round_text and round_number:
        round_text = f"Round {round_number}"

    parts = [part for part in (bo_text, round_text) if part]
    return " · ".join(parts)


def _resolve_participant_logo(match, participant_id, team_logo_map, user_avatar_map, team_avatar_fallback_map):
    if not participant_id:
        return None

    participation_type = str(getattr(match.tournament, "participation_type", "") or "").lower()
    if participation_type == "team":
        logo = team_logo_map.get(participant_id)
        if logo:
            return logo
        return team_avatar_fallback_map.get((match.tournament_id, participant_id))
    return user_avatar_map.get(participant_id)


def _media_field_url(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    try:
        return value.url
    except Exception:
        return ""


def _absolute_media_url(request, value) -> str:
    raw = _media_field_url(value)
    if not raw:
        return ""

    if raw.startswith(("http://", "https://")):
        return raw

    try:
        return request.build_absolute_uri(raw)
    except Exception:
        return raw


def _build_arena_match_logo_payload(matches):
    team_ids = set()
    solo_user_ids = set()
    team_tournament_ids = set()

    for match in matches:
        participation_type = str(getattr(match.tournament, "participation_type", "") or "").lower()
        for participant_id in (match.participant1_id, match.participant2_id):
            if not participant_id:
                continue
            if participation_type == "team":
                team_ids.add(participant_id)
                team_tournament_ids.add(match.tournament_id)
            else:
                solo_user_ids.add(participant_id)

    team_logo_map = {}
    if team_ids:
        try:
            from apps.organizations.models import Team

            teams = Team.objects.filter(id__in=team_ids).only("id", "logo")
            for team in teams:
                if getattr(team, "logo", None):
                    team_logo_map[int(team.id)] = team.logo
        except Exception:
            team_logo_map = {}

    team_avatar_fallback_map = {}
    missing_team_ids = team_ids.difference(team_logo_map.keys())
    if missing_team_ids and team_tournament_ids:
        try:
            from apps.tournaments.models.registration import Registration

            fallback_regs = (
                Registration.objects.filter(
                    tournament_id__in=team_tournament_ids,
                    team_id__in=missing_team_ids,
                    is_deleted=False,
                )
                .select_related("user", "user__profile")
                .order_by("id")
            )
            for reg in fallback_regs:
                if not reg.team_id:
                    continue
                key = (int(reg.tournament_id), int(reg.team_id))
                if key in team_avatar_fallback_map:
                    continue
                profile = getattr(reg.user, "profile", None)
                avatar = getattr(profile, "avatar", None) if profile else None
                if avatar:
                    team_avatar_fallback_map[key] = avatar
        except Exception:
            team_avatar_fallback_map = {}

    user_avatar_map = {}
    if solo_user_ids:
        try:
            users = get_user_model().objects.filter(id__in=solo_user_ids).select_related("profile")
            for user in users:
                profile = getattr(user, "profile", None)
                avatar = getattr(profile, "avatar", None) if profile else None
                if avatar:
                    user_avatar_map[int(user.id)] = avatar
        except Exception:
            user_avatar_map = {}

    payload = {}
    for match in matches:
        participant1_id = int(match.participant1_id) if match.participant1_id else None
        participant2_id = int(match.participant2_id) if match.participant2_id else None

        payload[match.id] = {
            "team_a_logo": _resolve_participant_logo(
                match,
                participant1_id,
                team_logo_map,
                user_avatar_map,
                team_avatar_fallback_map,
            ),
            "team_b_logo": _resolve_participant_logo(
                match,
                participant2_id,
                team_logo_map,
                user_avatar_map,
                team_avatar_fallback_map,
            ),
        }

    return payload


def _serialize_match_for_arena(match, request, logo_payload=None):
    logo_payload = logo_payload or {}
    stream_url = _resolve_match_stream_url(match)
    embed_url, platform = build_embed_url(
        stream_url,
        host_for_twitch_parent=request.get_host(),
    ) if stream_url else ("", "")
    embed_url = _with_youtube_origin(embed_url, request)
    game = getattr(match.tournament, "game", None)
    game_name = ""
    game_slug = ""
    if game:
        game_name = getattr(game, "name", "") or getattr(game, "display_name", "")
        game_slug = getattr(game, "slug", "") or ""
    if not game_name:
        game_name = "Esports"
    game_icon_url = _absolute_media_url(request, getattr(game, "icon", None)) if game else ""

    has_score = match.state in ARENA_LIVE_STATES or match.state in ARENA_RESULT_STATES
    tournament_url = _safe_reverse("tournaments:detail", slug=match.tournament.slug)
    match_url = _safe_reverse("tournaments:match_detail", slug=match.tournament.slug, match_id=match.id)
    details = _resolve_arena_match_details(match)

    return {
        "id": match.id,
        "tournament_name": match.tournament.name,
        "tournament_slug": match.tournament.slug,
        "tournament_url": tournament_url,
        "match_url": match_url,
        "game_name": game_name,
        "game_slug": game_slug,
        "game_icon_url": game_icon_url,
        "team_a": match.participant1_name or "TBD",
        "team_b": match.participant2_name or "TBD",
        "team_a_tag": _derive_team_tag(match.participant1_name or "TBD"),
        "team_b_tag": _derive_team_tag(match.participant2_name or "TBD"),
        "team_a_logo": _absolute_media_url(request, logo_payload.get("team_a_logo")),
        "team_b_logo": _absolute_media_url(request, logo_payload.get("team_b_logo")),
        "score_a": match.participant1_score,
        "score_b": match.participant2_score,
        "has_score": has_score,
        "state": match.state,
        "state_label": match.get_state_display(),
        "is_live": match.state == "live",
        "scheduled_time": match.scheduled_time,
        "round_number": match.round_number,
        "match_number": match.match_number,
        "best_of": match.best_of,
        "stream_url": stream_url,
        "embed_url": embed_url,
        "stream_embed_url": embed_url,
        "stream_platform": platform,
        "details": details,
        "thumbnail_url": (
            first_attr(match.tournament, ("banner_image", "thumbnail_image"))
            or first_attr(game, ("banner", "card_image", "icon"))
            or ""
        ),
    }


def _fetch_arena_matches(
    request,
    selected_game: str,
    search_query: str,
    *,
    selected_date=None,
    include_logos: bool = True,
    only_tab: str | None = None,
):
    from apps.tournaments.models import Match, Tournament

    base_qs = Match.objects.filter(
        is_deleted=False,
        tournament__is_deleted=False,
        tournament__status__in=[
            Tournament.REGISTRATION_OPEN,
            Tournament.REGISTRATION_CLOSED,
            Tournament.LIVE,
            Tournament.COMPLETED,
            Tournament.ARCHIVED,
        ],
    ).select_related("tournament", "tournament__game")

    if selected_game:
        base_qs = base_qs.filter(tournament__game__slug=selected_game)

    if search_query:
        base_qs = base_qs.filter(
            Q(tournament__name__icontains=search_query)
            | Q(participant1_name__icontains=search_query)
            | Q(participant2_name__icontains=search_query)
            | Q(tournament__game__name__icontains=search_query)
            | Q(tournament__game__display_name__icontains=search_query)
        )

    ordered_by_tournament_then_time = ("tournament__name", "scheduled_time", "id")
    live_raw = []
    upcoming_raw = []
    result_raw = []

    def _with_optional_arena_date_filter(queryset, destination: str):
        # Live tab intentionally ignores date filtering and always shows currently live matches.
        if not selected_date or destination == "live":
            return queryset

        local_tz = timezone.get_current_timezone()
        start_local = datetime.combine(selected_date, time.min)
        end_local = start_local + timedelta(days=1)
        start_dt = timezone.make_aware(start_local, local_tz)
        end_dt = timezone.make_aware(end_local, local_tz)

        return queryset.filter(
            scheduled_time__isnull=False,
            scheduled_time__gte=start_dt,
            scheduled_time__lt=end_dt,
        )

    normalized_tab = (only_tab or "").strip().lower()
    tab_config = {
        "live": (ARENA_LIVE_STATES, 18, "live"),
        "upcoming": (ARENA_UPCOMING_STATES, 24, "upcoming"),
        "results": (ARENA_RESULT_STATES, 24, "result"),
    }

    if normalized_tab in tab_config:
        states, limit, destination = tab_config[normalized_tab]
        filtered_qs = _with_optional_arena_date_filter(base_qs.filter(state__in=states), destination)
        rows = _safe_queryset_list(
            filtered_qs.order_by(*ordered_by_tournament_then_time),
            limit=limit,
        )
        if destination == "live":
            live_raw = rows
        elif destination == "upcoming":
            upcoming_raw = rows
        else:
            result_raw = rows
    else:
        live_raw = _safe_queryset_list(
            base_qs.filter(state__in=ARENA_LIVE_STATES).order_by(*ordered_by_tournament_then_time),
            limit=18,
        )
        upcoming_raw = _safe_queryset_list(
            _with_optional_arena_date_filter(base_qs.filter(state__in=ARENA_UPCOMING_STATES), "upcoming").order_by(*ordered_by_tournament_then_time),
            limit=24,
        )
        result_raw = _safe_queryset_list(
            _with_optional_arena_date_filter(base_qs.filter(state__in=ARENA_RESULT_STATES), "result").order_by(*ordered_by_tournament_then_time),
            limit=24,
        )

    logo_payload_by_match_id = {}
    if include_logos:
        all_matches = [*live_raw, *upcoming_raw, *result_raw]
        logo_payload_by_match_id = _build_arena_match_logo_payload(all_matches)

    return {
        "live_matches": [
            _serialize_match_for_arena(match, request, logo_payload=logo_payload_by_match_id.get(match.id))
            for match in live_raw
        ],
        "upcoming_matches": [
            _serialize_match_for_arena(match, request, logo_payload=logo_payload_by_match_id.get(match.id))
            for match in upcoming_raw
        ],
        "result_matches": [
            _serialize_match_for_arena(match, request, logo_payload=logo_payload_by_match_id.get(match.id))
            for match in result_raw
        ],
    }


def _fetch_top_live_streams(request, live_matches, selected_game: str, search_query: str):
    from apps.siteui.models import ArenaStream
    from apps.tournaments.models import Tournament

    seen_urls = set()
    top_streams = []
    host = request.get_host()
    now = timezone.now()

    for match in live_matches:
        stream_url = (match.get("stream_url") or "").strip()
        if not stream_url or stream_url in seen_urls:
            continue
        seen_urls.add(stream_url)
        top_streams.append({
            "id": f"match-{match['id']}",
            "title": f"{match['team_a']} vs {match['team_b']}",
            "subtitle": match["tournament_name"],
            "stream_url": stream_url,
            "embed_url": match.get("stream_embed_url") or "",
            "thumbnail_url": match.get("thumbnail_url") or "",
            "platform": match.get("stream_platform") or "",
            "channel_name": match["tournament_name"],
            "viewers_label": "",
            "game_name": match.get("game_name") or "",
            "game_slug": match.get("game_slug") or "",
            "team_a": match["team_a"],
            "team_b": match["team_b"],
            "team_a_tag": match["team_a_tag"],
            "team_b_tag": match["team_b_tag"],
            "score_a": match["score_a"],
            "score_b": match["score_b"],
            "has_score": match["has_score"],
            "details": f"R{match['round_number']} · M{match['match_number']}",
            "is_live": True,
            "source": "match",
            "target_url": match.get("match_url") or stream_url,
        })
        if len(top_streams) >= 8:
            return top_streams

    admin_stream_qs = ArenaStream.objects.filter(is_active=True, is_live=True).select_related("game").order_by(
        "-featured",
        "display_order",
        "-updated_at",
        "id",
    )
    admin_streams = _safe_queryset_list(admin_stream_qs, limit=18)
    for stream in admin_streams:
        if not stream.is_currently_live(now):
            continue

        stream_url = (stream.source_url or "").strip()
        if not stream_url or stream_url in seen_urls:
            continue

        game_slug = ""
        game_name = stream.effective_game_label or ""
        if stream.game_id:
            game_slug = stream.game.slug
        elif stream.game_label:
            game_slug = slugify(stream.game_label)

        if selected_game and game_slug != selected_game:
            continue
        if search_query:
            searchable = " ".join([
                stream.display_title,
                stream.subtitle,
                stream.channel_name,
                stream.game_label,
                game_name,
            ]).lower()
            if search_query.lower() not in searchable:
                continue

        embed_url = _with_twitch_parent(stream.safe_embed_url, stream.provider, host)
        if not embed_url:
            fallback_embed_url, _ = build_embed_url(stream_url, host_for_twitch_parent=host)
            embed_url = fallback_embed_url or stream_url
        embed_url = _with_youtube_origin(embed_url, request)
        seen_urls.add(stream_url)
        top_streams.append({
            "id": f"admin-{stream.id}",
            "title": stream.display_title,
            "subtitle": stream.subtitle,
            "stream_url": stream_url,
            "embed_url": embed_url,
            "thumbnail_url": stream.display_thumbnail,
            "platform": stream.effective_platform,
            "channel_name": stream.channel_name,
            "viewers_label": stream.viewers_label or (f"{stream.viewer_count:,}" if stream.viewer_count else ""),
            "game_name": game_name,
            "game_slug": game_slug,
            "team_a": "",
            "team_b": "",
            "team_a_tag": "",
            "team_b_tag": "",
            "score_a": None,
            "score_b": None,
            "has_score": False,
            "details": "",
            "is_live": True,
            "source": "admin",
            "target_url": stream_url,
        })
        if len(top_streams) >= 8:
            return top_streams

    tournament_qs = Tournament.objects.filter(
        is_deleted=False,
        status=Tournament.LIVE,
    ).select_related("game").order_by("-tournament_start", "id")

    if selected_game:
        tournament_qs = tournament_qs.filter(game__slug=selected_game)
    if search_query:
        tournament_qs = tournament_qs.filter(
            Q(name__icontains=search_query)
            | Q(game__name__icontains=search_query)
            | Q(game__display_name__icontains=search_query)
        )

    for tournament in _safe_queryset_list(tournament_qs, limit=18):
        stream_url = _resolve_tournament_stream_url(tournament)
        if not stream_url or stream_url in seen_urls:
            continue
        embed_url, platform = build_embed_url(stream_url, host_for_twitch_parent=host)
        embed_url = _with_youtube_origin(embed_url, request)
        game = tournament.game
        seen_urls.add(stream_url)
        top_streams.append({
            "id": f"tournament-{tournament.id}",
            "title": tournament.name,
            "subtitle": "Official tournament broadcast",
            "stream_url": stream_url,
            "embed_url": embed_url,
            "thumbnail_url": (
                first_attr(tournament, ("banner_image", "thumbnail_image"))
                or first_attr(game, ("banner", "card_image", "icon"))
                or ""
            ),
            "platform": platform,
            "channel_name": "DeltaCrown",
            "viewers_label": "",
            "game_name": (game.display_name or game.name) if game else "",
            "game_slug": game.slug if game else "",
            "team_a": "",
            "team_b": "",
            "team_a_tag": "",
            "team_b_tag": "",
            "score_a": None,
            "score_b": None,
            "has_score": False,
            "details": "",
            "is_live": True,
            "source": "tournament",
            "target_url": _safe_reverse("tournaments:detail", slug=tournament.slug),
        })
        if len(top_streams) >= 8:
            break

    return top_streams


def _fetch_arena_highlights(request):
    from apps.siteui.models import ArenaHighlight

    host = request.get_host()
    highlight_qs = ArenaHighlight.objects.filter(is_active=True).order_by("display_order", "-updated_at", "id")
    highlights = []
    for item in _safe_queryset_list(highlight_qs, limit=12):
        raw_video_url = (item.source_url or "").strip()
        final_embed_url = _with_twitch_parent(item.safe_embed_url, item.provider, host)
        if not final_embed_url:
            fallback_embed_url, _ = build_embed_url(raw_video_url, host_for_twitch_parent=host)
            final_embed_url = fallback_embed_url or raw_video_url
        final_embed_url = _with_youtube_origin(final_embed_url, request)
        highlights.append({
            "id": item.id,
            "title": item.display_title,
            "subtitle": item.subtitle,
            "watch_url": raw_video_url,
            "video_url": final_embed_url,
            "embed_url": final_embed_url,
            "platform": item.provider,
            "duration_label": item.duration_label,
            "views_label": item.views_label,
            "thumbnail_url": item.display_thumbnail,
        })
    return highlights


def _get_arena_voter_key(request, ensure_session: bool):
    if ensure_session and not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key or ""
    if not session_key and not request.user.is_authenticated:
        return ""

    fingerprint = "|".join([
        session_key,
        request.META.get("REMOTE_ADDR", ""),
        request.META.get("HTTP_USER_AGENT", "")[:180],
    ])
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _get_widget_vote_summary(widget):
    from apps.siteui.models import ArenaGlobalWidgetVote

    try:
        rows = list(
            ArenaGlobalWidgetVote.objects.filter(widget=widget)
            .values("selected_option")
            .annotate(total=Count("id"))
        )
    except (ProgrammingError, OperationalError):
        return {
            "a_votes": None,
            "b_votes": None,
            "total_votes": widget.vote_count,
            "a_percent": widget.option_a_percent,
            "b_percent": widget.option_b_percent,
        }

    if not rows:
        return {
            "a_votes": 0,
            "b_votes": 0,
            "total_votes": widget.vote_count,
            "a_percent": widget.option_a_percent,
            "b_percent": widget.option_b_percent,
        }

    a_votes = sum(row["total"] for row in rows if row["selected_option"] == "A")
    b_votes = sum(row["total"] for row in rows if row["selected_option"] == "B")
    total_votes = a_votes + b_votes
    if total_votes <= 0:
        return {
            "a_votes": 0,
            "b_votes": 0,
            "total_votes": widget.vote_count,
            "a_percent": widget.option_a_percent,
            "b_percent": widget.option_b_percent,
        }

    a_percent = round((a_votes * 100) / total_votes)
    b_percent = 100 - a_percent
    return {
        "a_votes": a_votes,
        "b_votes": b_votes,
        "total_votes": total_votes,
        "a_percent": a_percent,
        "b_percent": b_percent,
    }


def _resolve_user_widget_vote(widget, request):
    from apps.siteui.models import ArenaGlobalWidgetVote

    try:
        if request.user.is_authenticated:
            vote = ArenaGlobalWidgetVote.objects.filter(widget=widget, user=request.user).first()
            return vote.selected_option if vote else ""

        voter_key = _get_arena_voter_key(request, ensure_session=False)
        if not voter_key:
            return ""
        vote = ArenaGlobalWidgetVote.objects.filter(widget=widget, voter_key=voter_key).first()
        return vote.selected_option if vote else ""
    except (ProgrammingError, OperationalError):
        return ""


def _active_arena_widget_context(request):
    from apps.siteui.models import ArenaGlobalWidget

    now = timezone.now()
    widgets = _safe_queryset_list(
        ArenaGlobalWidget.objects.filter(is_active=True).order_by("display_order", "-updated_at", "id"),
        limit=10,
    )
    widget = None
    for candidate in widgets:
        if candidate.is_visible_now(now):
            widget = candidate
            break
    if not widget:
        return None

    summary = _get_widget_vote_summary(widget)
    return {
        "id": widget.id,
        "badge_label": widget.badge_label,
        "meta_label": widget.meta_label,
        "tournament_label": widget.tournament_label,
        "prompt_text": widget.prompt_text,
        "option_a_label": widget.option_a_label,
        "option_b_label": widget.option_b_label,
        "option_a_percent": summary["a_percent"],
        "option_b_percent": summary["b_percent"],
        "vote_count": summary["total_votes"],
        "vote_count_label": widget.vote_count_label,
        "selected_option": _resolve_user_widget_vote(widget, request),
        "vote_url": _safe_reverse("siteui:arena_widget_vote", widget_id=widget.id),
    }


def _refresh_widget_cached_vote_fields(widget):
    from apps.siteui.models import ArenaGlobalWidget

    summary = _get_widget_vote_summary(widget)
    if summary["a_votes"] is None:
        return
    ArenaGlobalWidget.objects.filter(pk=widget.pk).update(
        vote_count=summary["total_votes"],
        option_a_percent=summary["a_percent"],
        option_b_percent=summary["b_percent"],
    )


def _arena_games_payload():
    from apps.games.models.game import Game

    try:
        qs = Game.objects.filter(is_active=True).filter(
            Q(tournaments__is_deleted=False, tournaments__matches__is_deleted=False)
            | Q(arena_streams__is_active=True)
        ).distinct().order_by("display_name", "name")
        games = _safe_queryset_list(qs, limit=24)
        if not games:
            fallback_qs = Game.objects.filter(
                is_active=True,
                tournaments__is_deleted=False,
                tournaments__matches__is_deleted=False,
            ).distinct().order_by("display_name", "name")
            games = _safe_queryset_list(fallback_qs, limit=24)
    except Exception:
        qs = Game.objects.filter(
            is_active=True,
            tournaments__is_deleted=False,
            tournaments__matches__is_deleted=False,
        ).distinct().order_by("display_name", "name")
        games = _safe_queryset_list(qs, limit=24)

    return [
        {
            "slug": g.slug,
            "name": g.display_name or g.name,
            "primary_color": g.primary_color,
            "icon": g.icon,
        }
        for g in games
    ]


# ---- Arena views -------------------------------------------------------------

def watch(request):
    selected_game = (request.GET.get("game") or "").strip().lower()
    search_query = (request.GET.get("q") or "").strip()
    selected_date = parse_date((request.GET.get("date") or "").strip())
    selected_tab = (request.GET.get("tab") or "live").strip().lower()
    if selected_tab not in {"live", "upcoming", "results"}:
        selected_tab = "live"

    if _is_arena_async_request(request):
        payload = _build_arena_async_payload(
            request,
            selected_game=selected_game,
            selected_tab=selected_tab,
            search_query=search_query,
            selected_date=selected_date,
        )
        response = JsonResponse(payload)
        response["Cache-Control"] = "no-store, max-age=0"
        return response

    games = _arena_games_payload()
    if selected_game and not any(g["slug"] == selected_game for g in games):
        selected_game = ""

    match_payload = _fetch_arena_matches(
        request,
        selected_game=selected_game,
        search_query=search_query,
        selected_date=selected_date,
    )
    live_matches = match_payload["live_matches"]
    upcoming_matches = match_payload["upcoming_matches"]
    result_matches = match_payload["result_matches"]

    if selected_tab == "upcoming":
        selected_tab_matches = upcoming_matches
    elif selected_tab == "results":
        selected_tab_matches = result_matches
    else:
        selected_tab_matches = live_matches

    top_live_streams = _fetch_top_live_streams(
        request,
        live_matches=live_matches,
        selected_game=selected_game,
        search_query=search_query,
    )

    context = {
        "top_live_streams": top_live_streams,
        "live_matches": live_matches,
        "upcoming_matches": upcoming_matches,
        "result_matches": result_matches,
        "arena_highlights": _fetch_arena_highlights(request),
        "arena_poll_widget": _active_arena_widget_context(request),
        "games": games,
        "selected_game": selected_game,
        "selected_tab": selected_tab,
        "selected_tab_matches": selected_tab_matches,
        "search_query": search_query,
        "selected_date": selected_date,
        "arena_stats": {
            "live_streams": len(top_live_streams),
            "live_matches": len(live_matches),
            "upcoming_matches": len(upcoming_matches),
            "result_matches": len(result_matches),
        },
        "nav_live": bool(top_live_streams),
    }
    return render(request, "Arena.html", context)


def arena_async_data(request):
    selected_game = (request.GET.get("game") or "").strip().lower()
    search_query = (request.GET.get("q") or "").strip()
    selected_date = parse_date((request.GET.get("date") or "").strip())
    selected_tab = (request.GET.get("tab") or "live").strip().lower()
    if selected_tab not in {"live", "upcoming", "results"}:
        selected_tab = "live"

    payload = _build_arena_async_payload(
        request,
        selected_game=selected_game,
        selected_tab=selected_tab,
        search_query=search_query,
        selected_date=selected_date,
    )
    response = JsonResponse(payload)
    response["Cache-Control"] = "no-store, max-age=0"
    return response


def arena_widget_vote(request, widget_id: int):
    from apps.siteui.models import ArenaGlobalWidget, ArenaGlobalWidgetVote

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    selected_option = (request.POST.get("option") or "").strip().upper()
    if selected_option not in {"A", "B"}:
        return JsonResponse({"ok": False, "error": "Invalid option"}, status=400)

    try:
        widget = ArenaGlobalWidget.objects.get(pk=widget_id, is_active=True)
    except (ArenaGlobalWidget.DoesNotExist, ProgrammingError, OperationalError):
        return JsonResponse({"ok": False, "error": "Widget unavailable"}, status=404)

    if not widget.is_visible_now():
        return JsonResponse({"ok": False, "error": "Voting is not currently open"}, status=400)

    voter_key = _get_arena_voter_key(request, ensure_session=not request.user.is_authenticated)

    try:
        with transaction.atomic():
            if request.user.is_authenticated:
                ArenaGlobalWidgetVote.objects.update_or_create(
                    widget=widget,
                    user=request.user,
                    defaults={
                        "selected_option": selected_option,
                        "voter_key": voter_key,
                    },
                )
            else:
                if not voter_key:
                    return JsonResponse({"ok": False, "error": "Session unavailable"}, status=400)
                ArenaGlobalWidgetVote.objects.update_or_create(
                    widget=widget,
                    voter_key=voter_key,
                    defaults={"selected_option": selected_option},
                )
            _refresh_widget_cached_vote_fields(widget)
    except (ProgrammingError, OperationalError):
        return JsonResponse({"ok": False, "error": "Voting table is not ready yet"}, status=503)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "widget": _active_arena_widget_context(request),
        })

    next_url = request.POST.get("next") or _safe_reverse("siteui:arena")
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        next_url = _safe_reverse("siteui:arena")
    return redirect(next_url)


def newsletter_subscribe(request):
    """Newsletter subscription handler."""
    from django.contrib import messages
    from django.shortcuts import redirect
    import re
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email:
            messages.error(request, "Please enter your email address.")
        elif not re.match(email_pattern, email):
            messages.error(request, "Please enter a valid email address.")
        else:
            # For now, just simulate success (you can integrate with email service later)
            # TODO: Integrate with MailChimp, ConvertKit, or other email service
            messages.success(request, f"ðŸŽ‰ Welcome to the DeltaCrown Gaming Hub! We've added {email} to our newsletter. Get ready for exclusive tournaments, esports news, and gaming updates!")
            
            # Optional: Log the subscription for tracking
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Newsletter subscription: {email}")
    
    # Redirect back to the referring page or home
    return redirect(request.META.get('HTTP_REFERER', '/'))