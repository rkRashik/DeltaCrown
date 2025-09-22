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
from django.http import JsonResponse
from django.urls import reverse



def home(request):
    """Premium homepage: dynamic NEXT EVENT + live stats.
    Picks nearest upcoming tournament (settings.start_at >= now) else latest.
    """
    ft = None
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        qs = Tournament.objects.select_related("settings")
        now = timezone.now()
        nearest = qs.filter(settings__start_at__gte=now).order_by("settings__start_at").first()
        t = nearest or qs.order_by("-id").first()
        if t:
            # Compute derived fields for the hero
            start_dt = getattr(getattr(t, "settings", None), "start_at", None) or getattr(t, "start_at", None)
            try:
                start_iso = start_dt.isoformat() if start_dt else ""
            except Exception:
                start_iso = ""
            reg_open = getattr(getattr(t, "settings", None), "reg_open_at", None) or getattr(t, "reg_open_at", None)
            reg_close = getattr(getattr(t, "settings", None), "reg_close_at", None) or getattr(t, "reg_close_at", None)
            is_open = False
            if reg_open and reg_close:
                try:
                    is_open = reg_open <= now <= reg_close
                except Exception:
                    is_open = False
            start = getattr(getattr(t, "settings", None), "start_at", None) or getattr(t, "start_at", None)
            end = getattr(getattr(t, "settings", None), "end_at", None) or getattr(t, "end_at", None)
            is_live = False
            if start and end:
                try:
                    is_live = start <= now <= end
                except Exception:
                    is_live = False
            ft = {
                "name": getattr(t, "name", None) or "Tournament",
                "start_iso": start_iso,
                "registration_open": is_open,
                "is_live": is_live,
                "register_url": getattr(t, "register_url", None) or (f"/tournaments/{t.slug}/register/" if getattr(t, "slug", None) else "/tournaments/"),
                "stream_url": getattr(t, "stream_url", None) or "/tournaments/",
                "detail_url": getattr(t, "detail_url", None) or (f"/tournaments/{t.slug}/" if getattr(t, "slug", None) else "/tournaments/"),
            }
    except Exception:
        ft = None

    # Community stats mapped to expected keys
    raw_stats = compute_stats()  # players, prize_bdt
    community_stats = {
        "players": raw_stats.get("players", 0),
        "prizes_bdt": raw_stats.get("prize_bdt", 0),
        "payout_accuracy": 98,  # default showcase value
    }
    games_strip = [
        {"slug": "efootball", "name": "eFootball", "image": "img/efootball.jpeg"},
        {"slug": "valorant", "name": "Valorant", "image": "img/Valorant.jpg"},
        {"slug": "fc26", "name": "FC 26", "image": "img/FC26.jpg"},
        {"slug": "pubg", "name": "PUBG Mobile", "image": "img/PUBG.jpeg"},
        {"slug": "mlbb", "name": "Mobile Legend", "image": "img/MobileLegend.jpg"},
        {"slug": "cs2", "name": "CS2", "image": "img/CS2.jpg"},
    ]

    ctx = {
        "featured_tournament": ft,
        "community_stats": community_stats,
        "spotlight": get_spotlight(3),
        "timeline": get_timeline(6),
        "games_strip": games_strip,
    }
    return render(request, "home.html", ctx)


def privacy(request):
    return render(request, "legal/privacy.html")


def terms(request):
    return render(request, "legal/terms.html")

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
    Community hub displaying both user posts and team posts
    """
    from django.core.paginator import Paginator
    from django.db import models
    from django.contrib.auth.decorators import login_required
    from apps.teams.models.social import TeamPost
    from apps.teams.models import Team
    from .models import CommunityPost
    from .forms import CommunityPostCreateForm
    from itertools import chain
    from operator import attrgetter
    
    # Handle POST requests for creating community posts
    if request.method == 'POST' and request.user.is_authenticated:
        return handle_community_post_creation(request)
    
    # Get search and filter parameters
    search_query = request.GET.get('q', '')
    current_game = request.GET.get('game', '')
    
    # Base queryset for public team posts
    team_posts = TeamPost.objects.filter(
        visibility='public'
    ).select_related(
        'team', 'author', 'author__user'
    ).prefetch_related(
        'media', 'likes', 'comments'
    ).order_by('-created_at')
    
    # Base queryset for public community posts
    community_posts = CommunityPost.objects.filter(
        visibility='public',
        is_approved=True
    ).select_related(
        'author', 'author__user'
    ).prefetch_related(
        'media', 'likes', 'comments'
    ).order_by('-created_at')
    
    # Apply search filter to both post types
    if search_query:
        team_posts = team_posts.filter(
            models.Q(title__icontains=search_query) | 
            models.Q(content__icontains=search_query) |
            models.Q(team__name__icontains=search_query)
        )
        community_posts = community_posts.filter(
            models.Q(title__icontains=search_query) | 
            models.Q(content__icontains=search_query) |
            models.Q(author__user__username__icontains=search_query) |
            models.Q(author__user__first_name__icontains=search_query) |
            models.Q(author__user__last_name__icontains=search_query)
        )
    
    # Apply game filter to both post types
    if current_game:
        team_posts = team_posts.filter(team__game=current_game)
        community_posts = community_posts.filter(game=current_game)
    
    # Get available games for filter dropdown with proper mapping
    raw_games = Team.objects.values_list('game', flat=True).distinct()
    raw_games = [game for game in raw_games if game]  # Remove empty values
    
    # Game mapping to handle duplicates and provide proper display info
    game_mapping = {
        'valorant': {
            'display_name': 'Valorant',
            'logo': 'img/game_logos/Valorant_logo.jpg',
            'aliases': ['valorant', 'Valorant', 'VALORANT']
        },
        'efootball': {
            'display_name': 'eFootball',
            'logo': 'img/game_logos/efootball_logo.jpeg',
            'aliases': ['efootball', 'eFootball', 'Efootball', 'EFOOTBALL']
        },
        'cs2': {
            'display_name': 'Counter-Strike 2',
            'logo': 'img/game_logos/CS2_logo.jpeg',
            'aliases': ['cs2', 'CS2', 'counter-strike 2', 'Counter-Strike 2']
        },
        'fc26': {
            'display_name': 'FC 26',
            'logo': 'img/game_logos/fc26_logo.jpg',
            'aliases': ['fc26', 'FC26', 'fc 26', 'FC 26']
        },
        'pubg': {
            'display_name': 'PUBG',
            'logo': 'img/game_logos/PUBG_logo.jpg',
            'aliases': ['pubg', 'PUBG', 'pubg mobile', 'PUBG Mobile']
        },
        'mobile_legends': {
            'display_name': 'Mobile Legends',
            'logo': 'img/game_logos/mobile_legend_logo.jpeg',
            'aliases': ['mobile legends', 'Mobile Legends', 'mobile_legends', 'ml']
        }
    }
    
    # Create unique games list based on raw data
    unique_games = {}
    for raw_game in raw_games:
        # Find matching game in mapping
        matched_key = None
        for key, game_info in game_mapping.items():
            if raw_game.lower() in [alias.lower() for alias in game_info['aliases']]:
                matched_key = key
                break
        
        if matched_key and matched_key not in unique_games:
            unique_games[matched_key] = game_mapping[matched_key]
            unique_games[matched_key]['raw_name'] = raw_game
    
    games = list(unique_games.values())
    
    # Combine and sort posts by creation date
    # Add a post_type attribute to differentiate in templates
    for post in team_posts:
        post.post_type = 'team'
        post.display_author = post.team.name
        post.author_avatar = post.team.logo
        post.author_url = f"/teams/{post.team.slug}/"
    
    for post in community_posts:
        post.post_type = 'user'
        post.display_author = post.author.user.get_full_name() or post.author.user.username
        post.author_avatar = getattr(post.author, 'avatar', None)
        post.author_url = f"/profile/{post.author.user.username}/"
    
    # Combine posts and sort by creation date
    all_posts = sorted(
        chain(team_posts, community_posts),
        key=attrgetter('created_at'),
        reverse=True
    )
    
    # Paginate combined posts (10 per page)
    paginator = Paginator(all_posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    # Get featured teams for sidebar
    featured_teams = Team.objects.filter(
        is_verified=True
    ).select_related().order_by('?')[:5]  # Random featured teams
    
    if not featured_teams.exists():
        # Fallback to recent teams if no verified teams
        featured_teams = Team.objects.order_by('-created_at')[:5]

    context = {
        'posts': posts,
        'search_query': search_query,
        'current_game': current_game,
        'games': games,
        'featured_teams': featured_teams,
        'community_post_form': CommunityPostCreateForm(),
    }
    return render(request, 'pages/community.html', context)


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
        ("tournaments", "Tournament", Q(start_at__gte=now), "-start_at"),
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
            messages.success(request, f"🎉 Welcome to the DeltaCrown Gaming Hub! We've added {email} to our newsletter. Get ready for exclusive tournaments, esports news, and gaming updates!")
            
            # Optional: Log the subscription for tracking
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Newsletter subscription: {email}")
    
    # Redirect back to the referring page or home
    return redirect(request.META.get('HTTP_REFERER', '/'))