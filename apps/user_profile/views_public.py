from __future__ import annotations
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _should_debug(request=None):
    """Return True if we should show debug logs for this request.
    Allow debug output if Django settings.DEBUG or the requesting user is a superuser.
    """
    from django.conf import settings as _settings
    if getattr(_settings, "DEBUG", False):
        return True
    if request is None:
        return False
    try:
        return getattr(request, "user", None) and getattr(request.user, "is_superuser", False)
    except Exception:
        return False


def _debug_log(request, *args, **kwargs):
    if _should_debug(request):
        logger.debug(*args, **kwargs)

User = get_user_model()


def _get_profile(user) -> Optional[object]:
    # Try common OneToOne related_name
    prof = getattr(user, "profile", None)
    if prof is not None:
        return prof
    # Fallback to explicit model if present
    try:
        from apps.user_profile.models import UserProfile
        return UserProfile.objects.filter(user=user).first()
    except Exception:
        return None


def public_profile(request: HttpRequest, username: str) -> HttpResponse:
    user = User.objects.filter(username=username).first()
    if not user:
        raise Http404("User not found")

    profile = _get_profile(user)

    # Debugging: log request info so we can track public profile requests
    _debug_log(request, f'public_profile called for username={username}, request.user={request.user}, authenticated={getattr(request.user, "is_authenticated", False)}')
    _debug_log(request, '\n' + '='*80)
    _debug_log(request, 'DEBUG: public_profile() called')
    _debug_log(request, '='*80)
    _debug_log(request, f"DEBUG [1]: Requested username: {username}")
    _debug_log(request, f"DEBUG [1]: Request.user: {request.user} (authenticated: {getattr(request.user, 'is_authenticated', False)})")
    _debug_log(request, f"DEBUG [1]: Request.path: {request.path}")

    # If profile exists and is private, render minimal card
    is_private = bool(getattr(profile, "is_private", False))
    if is_private:
        return render(request, "user_profile/profile.html", {
            "public_user": user,
            "profile": profile,
            "is_private": True,
        })

    # Ownership: whether the current viewer is the profile owner
    is_own_profile = request.user.is_authenticated and request.user == user
    _debug_log(request, f"DEBUG [5]: is_own_profile calculated as: {is_own_profile}")
    _debug_log(request, f"DEBUG [5]: Request User: {request.user} vs Profile User: {user}")

    # Field-level toggles
    show_email = bool(getattr(profile, "show_email", False))
    show_phone = bool(getattr(profile, "show_phone", False))
    show_socials = getattr(profile, "show_socials", True)

    # Optional fields (best-effort)
    phone = getattr(profile, "phone", None)
    socials = getattr(profile, "socials", None)

    # Initialize social_links to prevent UnboundLocalError
    social_links = []
    ign = getattr(profile, "ign", None)
    riot_id = getattr(profile, "riot_id", None)
    efootball_id = getattr(profile, "efootball_id", None)
    discord_id = getattr(profile, "discord_id", None)

    # Tournament system moved to legacy - player stats disabled
    stats = None
    match_history = []
    # try:
    #     from apps.tournaments.models.match import Match
    #     if profile:
    #         qs = Match.objects.filter(
    #             Q(user_a=profile) | Q(user_b=profile)
    #         ).order_by("-created_at")
    #         total = qs.count()
    #         wins = qs.filter(winner_user=profile).count()
    #         win_rate = round((wins / total) * 100) if total else 0
    #         stats = {
    #             "matches": total,
    #             "win_rate": win_rate,
    #             "rank": None,
    #         }
    #         # shape minimal history for the template
    #         for m in qs[:6]:
    #             match_history.append({
    #                 "tournament_name": getattr(m.tournament, "name", "Tournament"),
    #                 "result": ("Win" if getattr(m, "winner_user_id", None) == profile.id else ("Loss" if m.winner_user_id else "-")),
    #                 "game": getattr(m.tournament, "game", None) or "—",
    #                 "played_at": getattr(m, "created_at", None),
    #                 "url": f"/tournaments/{getattr(m.tournament, 'id', '')}/matches/{m.id}/" if getattr(m, 'id', None) else "#",
    #                 "summary": "",
    #             })
    # except Exception:
    #     pass

    # Social links from profile fields → list of dicts expected by template
    social = []
    if profile and show_socials:
        try:
            if getattr(profile, "youtube_link", ""):
                social.append({"platform": "YouTube", "handle": "", "url": profile.youtube_link})
            if getattr(profile, "twitch_link", ""):
                social.append({"platform": "Twitch", "handle": "", "url": profile.twitch_link})
            if getattr(profile, "discord_id", ""):
                discord_handle = profile.discord_id
                social.append({"platform": "Discord", "handle": discord_handle, "url": f"https://discord.com/users/{discord_handle}"})
        except Exception:
            # Be resilient to any unexpected data
            social = []

    # Now compute social_links for the template (prefer explicit profile.socials if present)
    try:
        if profile and show_socials:
            if socials:
                # Profile may store socials as a list or QuerySet-like object
                try:
                    social_links = list(socials)
                except Exception:
                    social_links = socials
            else:
                social_links = social or []
        else:
            social_links = []
    except Exception:
        social_links = social or []

    # Get team memberships for the user
    teams = []
    current_teams = []
    team_history = []
    
    try:
        if profile:
            from apps.teams.models import TeamMembership, Team
            
            # Get active team memberships
            active_memberships = TeamMembership.objects.filter(
                profile=profile, 
                status=TeamMembership.Status.ACTIVE
            ).select_related('team').order_by('-joined_at')
            
            for membership in active_memberships:
                team_data = {
                    'team': membership.team,
                    'role': membership.get_role_display(),
                    'role_code': membership.role,
                    'joined_at': membership.joined_at,
                    'is_captain': membership.role == TeamMembership.Role.CAPTAIN,
                    'game': membership.team.get_game_display() if membership.team.game else None,
                    'logo_url': membership.team.logo.url if membership.team.logo else None,
                }
                current_teams.append(team_data)
                teams.append(team_data)
            
            # Get team history (past teams)
            past_memberships = TeamMembership.objects.filter(
                profile=profile, 
                status__in=[TeamMembership.Status.REMOVED]
            ).select_related('team').order_by('-joined_at')[:5]
            
            for membership in past_memberships:
                team_data = {
                    'team': membership.team,
                    'role': membership.get_role_display(),
                    'joined_at': membership.joined_at,
                    'left_team': True,
                    'game': membership.team.get_game_display() if membership.team.game else None,
                    'logo_url': membership.team.logo.url if membership.team.logo else None,
                }
                team_history.append(team_data)
                
    except Exception as e:
        # Fail gracefully if team models aren't available
        logger.warning(f"Error loading team data: {e}")
        teams = []
        current_teams = []
        team_history = []
    
    # Get tournament registrations
    tournament_history = []
    upcoming_tournaments = []
    
    try:
        # Tournament system moved to legacy - no longer displaying registration data
        pass
                    
    except Exception as e:
        # Fail gracefully if tournament models aren't available
        logger.warning(f"Error loading tournament data: {e}")
        tournament_history = []
        upcoming_tournaments = []
    
    # Get economy information
    wallet_balance = 0
    recent_transactions = []
    
    try:
        if profile:
            from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
            
            # Get or create wallet
            wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
            wallet_balance = wallet.cached_balance
            # Compute USD equivalent for display purposes (simple conversion rate: 1 DC = 0.01 USD)
            try:
                usd_equivalent = float(wallet_balance) * 0.01
            except Exception:
                usd_equivalent = 0.0
            
            # Get recent transactions
            # NOTE: tournament, registration, match are now IntegerFields, not ForeignKeys
            recent_transactions = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).order_by('-created_at')[:10]
            
    except Exception as e:
        logger.warning(f"Error loading economy data: {e}")
        wallet_balance = 0
        recent_transactions = []
    
    # Get ecommerce information  
    recent_orders = []
    total_orders = 0
    
    try:
        if profile:
            from apps.ecommerce.models import Order
            
            # Get recent orders
            recent_orders = Order.objects.filter(
                user=profile
            ).prefetch_related('items__product').order_by('-created_at')[:5]
            
            total_orders = Order.objects.filter(user=profile).count()
            
    except Exception as e:
        logger.warning(f"Error loading ecommerce data: {e}")
        recent_orders = []
        total_orders = 0
    
    # Get recent activity/achievements
    achievements = []
    activity = []
    
    try:
        if profile:
            # Get team posts by user
            from apps.teams.models.social import TeamPost, TeamActivity
            
            recent_posts = TeamPost.objects.filter(
                author=profile,
                published_at__isnull=False
            ).select_related('team').order_by('-published_at')[:5]
            
            for post in recent_posts:
                activity.append({
                    'type': 'team_post',
                    'description': f'Posted in {post.team.name}',
                    'title': post.title or post.content[:50] + '...' if len(post.content) > 50 else post.content,
                    'date': post.published_at,
                    'team': post.team,
                    'url': f'/teams/{post.team.slug}/social/'
                })
            
            # Get recent team activities involving this user
            team_activities = TeamActivity.objects.filter(
                actor=profile,
                is_public=True
            ).select_related('team').order_by('-created_at')[:5]
            
            for act in team_activities:
                activity.append({
                    'type': 'team_activity', 
                    'description': act.description,
                    'date': act.created_at,
                    'team': act.team,
                    'url': f'/teams/{act.team.slug}/'
                })
            
            # Add coin transactions to activity
            for transaction in recent_transactions[:3]:
                activity.append({
                    'type': 'coin_transaction',
                    'description': f'{transaction.get_reason_display()}',
                    'title': f'{"+" if transaction.amount > 0 else ""}{transaction.amount} DeltaCoins',
                    'date': transaction.created_at,
                    'amount': transaction.amount,
                    'tournament': transaction.tournament,
                    'url': f'/economy/transactions/' if transaction.tournament else None
                })
            
            # Add ecommerce orders to activity  
            for order in recent_orders[:2]:
                activity.append({
                    'type': 'ecommerce_order',
                    'description': f'Order #{order.id} - {order.get_status_display()}',
                    'title': f'${order.total_price} • {order.items.count()} items',
                    'date': order.created_at,
                    'order': order,
                    'url': f'/shop/orders/{order.id}/'
                })
            
            # Sort activity by date
            activity.sort(key=lambda x: x['date'], reverse=True)
                
    except Exception as e:
        logger.warning(f"Error loading activity data: {e}")
        activity = []

    # Get game profiles from the new pluggable system
    game_profiles = []
    if profile and profile.game_profiles:
        game_profiles = profile.game_profiles
    
    # Calculate tournament stats (placeholder for now)
    tournament_stats = {
        'total_wins': 0,
        'total_tournaments': len(tournament_history),
        'win_rate': 0
    }
    
    # Get badges data
    pinned_badges = []
    try:
        if profile:
            from apps.user_profile.models import UserBadge
            pinned_badges = UserBadge.objects.filter(
                user=user,
                is_pinned=True
            ).select_related('badge').order_by('-earned_at')[:5]
    except Exception as e:
        logger.warning(f"Error loading badge data: {e}")
        pinned_badges = []
    
    context = {
        "public_user": user,
        "profile": profile,
        "is_private": False,
            # Aliases expected by templates
            'profile_user': user,
            'is_own_profile': is_own_profile,
            'social_links': social_links,
            'matches': match_history,
        "show_email": show_email,
        "show_phone": show_phone,
        "show_socials": show_socials,
        "phone": phone,
        "socials": socials,
        "ign": ign,
        "riot_id": riot_id,
        "efootball_id": efootball_id,
        "discord_id": discord_id,
        # added pipeline data
        "stats": stats,
        "match_history": match_history,
        "activity": activity,
        "teams": teams,
        "current_teams": current_teams,
        "team_history": team_history,
        "tournament_history": tournament_history,
        "upcoming_tournaments": upcoming_tournaments,
        "highlights": [],
        "achievements": achievements,
        "social": social,
        # economy & ecommerce data
        "wallet_balance": wallet_balance,
        "usd_equivalent": usd_equivalent,
        "recent_transactions": recent_transactions,
        "recent_orders": recent_orders,
        "total_orders": total_orders,
        # new template context
        "game_profiles": game_profiles,
        "tournament_stats": tournament_stats,
        "pinned_badges": pinned_badges,
        'debug': settings.DEBUG,
    }

    # Provide wallet & notification info for owners (best-effort)
    try:
        context['unread_notification_count'] = 0
        context['wallet'] = None
        context['recent_transactions'] = []
        if is_own_profile and profile:
            from apps.notifications.models import Notification
            # Notification.recipient is a ForeignKey to User, not UserProfile
            context['unread_notification_count'] = Notification.objects.filter(recipient=user, is_read=False).count()
            from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
            wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
            context['wallet'] = wallet
            context['recent_transactions'] = list(DeltaCrownTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:3])
    except Exception as e:
        logger.warning(f"Error loading owner-specific data: {e}")
        # gracefully ignore missing apps/models
        context['unread_notification_count'] = context.get('unread_notification_count', 0)
        context['wallet'] = context.get('wallet', None)
        context['recent_transactions'] = context.get('recent_transactions', [])

    # Add internal instrumentation variables
    from django.utils import timezone
    context['debug_timestamp'] = timezone.now().isoformat()

    # Add alias expected by template
    context['profile_user'] = user
    return render(request, "user_profile/profile.html", context)


def profile_api(request: HttpRequest, profile_id: str) -> HttpResponse:
    """API endpoint for profile data used in team roster modals."""
    from django.http import JsonResponse
    from django.db.models import Count, Q, F
    import hashlib
    
    try:
        from apps.user_profile.models import UserProfile
        profile = UserProfile.objects.select_related('user').get(id=profile_id)
        
        # Verify user exists
        if not profile.user:
            raise Exception(f"Profile {profile_id} has no associated user")
        
        # Check if requester is a team member (shares a team with this profile)
        show_game_ids = False
        if request.user.is_authenticated:
            try:
                from apps.teams.models import TeamMembership
                # Check if users share any active team
                requester_profile = UserProfile.objects.filter(user=request.user).first()
                if requester_profile:
                    shared_teams = TeamMembership.objects.filter(
                        team__in=profile.team_memberships.filter(status='ACTIVE').values_list('team', flat=True),
                        profile=requester_profile,
                        status='ACTIVE'
                    ).exists()
                    show_game_ids = shared_teams or request.user.is_staff
            except Exception as e:
                # Log but don't fail
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Error checking authorization for profile {profile_id}: {str(e)}')
        
        # Tournament system moved to legacy - use fallback data
        # Fallback to consistent fake data based on user ID
        user_hash = int(hashlib.md5(f"{profile.user.username}{profile_id}".encode()).hexdigest()[:8], 16)
        matches_played = (user_hash % 200) + 50  # 50-250 matches
        win_rate = 0.4 + ((user_hash % 400) / 1000)  # 40-80% win rate
        wins = int(matches_played * win_rate)
        rating = 1200 + (user_hash % 800)  # 1200-2000 rating
        
        # Get team information with game IDs if authorized
        try:
            current_teams = profile.team_memberships.filter(status='ACTIVE').select_related('team')
            team_info = []
            for membership in current_teams:
                team_data = {
                    'name': membership.team.name,
                    'role': membership.get_role_display(),
                    'game': membership.team.get_game_display() if membership.team.game else None
                }
                # Add game ID if authorized and available
                if show_game_ids and membership.team.game:
                    game_id = profile.get_game_id(membership.team.game)
                    if game_id:
                        team_data['game_id'] = game_id
                        team_data['game_id_label'] = profile.get_game_id_label(membership.team.game)
                        if membership.team.game == 'mlbb' and profile.mlbb_server_id:
                            team_data['mlbb_server_id'] = profile.mlbb_server_id
                team_info.append(team_data)
        except Exception:
            team_info = []
        
        data = {
            'display_name': profile.display_name or profile.user.username,
            'username': profile.user.username,
            'bio': profile.bio or f'Professional {", ".join([t["game"] for t in team_info if t["game"]]) or "Esports"} Player',
            'avatar_url': profile.avatar.url if profile.avatar else None,
            'matches_played': matches_played,
            'wins': wins,
            'rating': rating,
            'win_rate': f"{(wins/matches_played*100):.1f}%" if matches_played > 0 else "0%",
            'region': profile.get_region_display() if profile.region else 'Global',
            'teams': team_info,
            'joined_date': profile.created_at.strftime('%b %Y'),
        }
        
        # Add social links if authorized
        if show_game_ids:
            # Only add social links that actually exist in the model
            data['discord_id'] = profile.discord_id if profile.discord_id else None
            data['youtube_link'] = profile.youtube_link if profile.youtube_link else None
            data['twitch_link'] = profile.twitch_link if profile.twitch_link else None
            # Note: twitter and instagram fields don't exist in UserProfile model yet
            # data['twitter'] = profile.twitter if hasattr(profile, 'twitter') and profile.twitter else None
            # data['instagram'] = profile.instagram if hasattr(profile, 'instagram') and profile.instagram else None
        
        return JsonResponse(data)
        
    except UserProfile.DoesNotExist:
        # Generate consistent fake data for non-existent profiles
        fake_hash = int(hashlib.md5(f"fake{profile_id}".encode()).hexdigest()[:8], 16)
        matches = (fake_hash % 200) + 50
        win_rate = 0.4 + ((fake_hash % 400) / 1000)
        wins = int(matches * win_rate)
        
        return JsonResponse({
            'display_name': f'Player{profile_id}',
            'username': f'player{profile_id}',
            'bio': 'Esports Player',
            'avatar_url': None,
            'matches_played': matches,
            'wins': wins,
            'rating': 1200 + (fake_hash % 800),
            'win_rate': f"{(win_rate*100):.1f}%",
            'region': 'Global',
            'teams': [],
            'joined_date': 'Jan 2024',
        })
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in profile_api for profile_id {profile_id}: {str(e)}')
        logger.error(traceback.format_exc())
        return JsonResponse({
            'error': 'Profile not available',
            'detail': str(e),
            'profile_id': profile_id
        }, status=500)
