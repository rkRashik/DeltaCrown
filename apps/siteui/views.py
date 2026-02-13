from __future__ import annotations
from django.shortcuts import render
from django.utils import timezone
from django.apps import apps
from .services import compute_stats, get_spotlight, get_timeline
from django.apps import apps as django_apps
from typing import Any, Iterable
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
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

# ---- Data sources (try a few common patterns, choose whatever exists) --------

def query_streams_and_vods(q: str | None, game: str | None):
    """
    Try multiple potential models; return (live_streams, vods).
    Adjust/extend the SOURCES list to match your schema.
    """
    filters = Q()
    if q:
        filters &= Q(title__icontains=q) | Q(name__icontains=q) | Q(channel__icontains=q)
    if game:
        filters &= Q(game__iexact=game) | Q(game_name__iexact=game) | Q(category__iexact=game)

    SOURCES = [
        # (app_label, model_name, live_filter, vod_filter, order_field_desc)
        ("media", "Broadcast", Q(is_live=True), Q(is_live=False), "-start_time"),
        ("streams", "Stream", Q(is_live=True), Q(is_live=False), "-created_at"),
        ("siteui", "Broadcast", Q(is_live=True), Q(is_live=False), "-start_time"),
        ("tournaments", "MatchStream", Q(is_live=True), Q(is_live=False), "-created_at"),
        ("videos", "Vod", None, Q(), "-published_at"),
    ]

    live = []
    vods = []
    for app_label, model_name, live_q, vod_q, order in SOURCES:
        Model = try_get_model(app_label, model_name)
        if not Model:
            continue
        try:
            if live_q is not None:
                qs_live = Model.objects.filter(live_q).filter(filters).order_by(order)[:12]
                live.extend(list(qs_live))
            if vod_q is not None:
                qs_vod = Model.objects.filter(vod_q).filter(filters).order_by(order)[:60]
                vods.extend(list(qs_vod))
        except Exception:
            # Model exists but fields differ; skip silently
            continue

    return live, vods

def query_upcoming(q: str | None, game: str | None):
    filters = Q()
    now = timezone.now()
    if q:
        filters &= Q(title__icontains=q) | Q(name__icontains=q) | Q(channel__icontains=q)
    if game:
        filters &= Q(game__iexact=game) | Q(game_name__iexact=game) | Q(category__iexact=game)

    CANDIDATES = [
        ("media", "Broadcast", Q(scheduled_for__gte=now), "-scheduled_for"),
        # ("tournaments", "Tournament", Q(start_at__gte=now), "-start_at"),  # Tournament system moved to legacy
        ("events", "Event", Q(start_time__gte=now), "-start_time"),
    ]
    items = []
    for app_label, model_name, cond, order in CANDIDATES:
        Model = try_get_model(app_label, model_name)
        if not Model:
            continue
        try:
            items.extend(list(Model.objects.filter(cond).filter(filters).order_by(order)[:20]))
        except Exception:
            continue
    return items

def derive_games(*lists):
    """Collect unique game labels from normalized items."""
    seen = {}
    for lst in lists:
        for it in lst:
            g = it.get("game")
            if g and g not in seen:
                seen[g] = {"name": g, "slug": g.lower().replace(" ", "-")}
    return list(seen.values())[:24]

# ---- View -------------------------------------------------------------------

def watch(request):
    q = request.GET.get("q") or ""
    game = request.GET.get("game") or ""

    # Query raw objects
    raw_live, raw_vods = query_streams_and_vods(q, game)
    raw_upcoming = query_upcoming(q, game)

    # Normalize
    live_streams = [normalize_stream(o, request) for o in raw_live]
    vods_all = [normalize_vod(o, request) for o in raw_vods]
    upcoming = [normalize_upcoming(o) for o in raw_upcoming]

    # Featured: prefer live, else newest vod
    featured_stream = live_streams[0] if live_streams else (vods_all[0] if vods_all else None)

    # Games list (for filter chips)
    games = derive_games(live_streams, vods_all, upcoming)

    # Paginate VODs
    paginator = Paginator(vods_all, 12)
    page = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page)
        vods = page_obj.object_list
    except EmptyPage:
        page_obj = paginator.page(1)
        vods = page_obj.object_list

    context = {
        "live_streams": live_streams[:8],
        "featured_stream": featured_stream,
        "upcoming_streams": upcoming[:10],
        "vods": vods,
        "page_obj": page_obj if paginator.num_pages > 1 else None,
        "games": games,
    }

    # Optional: small sample content in DEBUG so the page doesn't look empty
    if settings.DEBUG and not (live_streams or vods_all or upcoming):
        host = request.get_host().split(":")[0]
        ytembed, _ = build_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        tt, _ = build_embed_url(f"https://www.twitch.tv/esl_csgo", host_for_twitch_parent=host)
        fb, _ = build_embed_url("https://www.facebook.com/facebookapp/videos/10153231379946729/")

        context["live_streams"] = [
            {"title":"Sample Twitch Live","embed_url":tt,"watch_url":"https://www.twitch.tv/esl_csgo","thumbnail_url":"","channel":"ESL","game":"CS2","viewers":4200,"tags":["english"],"is_live":True,"start_time":timezone.now(),"platform":"Twitch"},
        ]
        context["featured_stream"] = {"title":"Sample YouTube","embed_url":ytembed,"watch_url":"https://youtu.be/dQw4w9WgXcQ","thumbnail_url":"","channel":"DeltaCrown","game":"eFootball","viewers":1200,"tags":["finals"],"is_live":False,"start_time":timezone.now(),"platform":"YouTube"}
        context["upcoming_streams"] = [
            {"title":"Open Qualifiers Day 1","game":"Valorant","scheduled_for":timezone.now()+timezone.timedelta(days=1),"channel":"DC Events","platform":"YouTube","cta_url":"#"}
        ]
        context["vods"] = [
            {"title":"Grand Final Highlights","thumbnail_url":"","duration":"12:34","published_at":timezone.now()-timezone.timedelta(days=1),"channel":"DeltaCrown","watch_url":"https://youtu.be/dQw4w9WgXcQ"},
        ]
        context["games"] = [{"name":"Valorant","slug":"valorant"},{"name":"eFootball","slug":"efootball"}]

    # Navbar flag (you can also move this to a context processor below)
    context["nav_live"] = bool(live_streams)

    return render(request, "Arena.html", context)


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