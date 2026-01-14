"""
Public Profile Views (UP-FE-MVP-01 + Phase 5B Privacy Enforcement)

Privacy-safe profile views using profile_context service + ProfilePermissionChecker.
Server-side privacy enforcement with can_view_* flags passed to template.

Views:
- public_profile_view: Public profile page (✅ Phase 5B privacy-aware)
- profile_activity_view: Activity feed page
- profile_settings_view: Owner-only settings page
- profile_privacy_view: Owner-only privacy settings page

Architecture:
- Uses ProfilePermissionChecker for all permission decisions
- Passes can_view_* flags to template for server-side enforcement
- NO CSS-only privacy (sections not rendered if private)
- Enforces authentication/ownership where required
- Returns safe primitives/JSON only
- Backward compatible with existing URLs (redirects)
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
import logging
import os

from apps.user_profile.services.profile_context import build_public_profile_context
from apps.user_profile.services.follow_service import FollowService  # Phase 6B: Follow request status
from apps.user_profile.services.profile_permissions import ProfilePermissionChecker
from apps.user_profile.models import UserProfile, SocialLink

logger = logging.getLogger(__name__)


def public_profile_view(request: HttpRequest, username: str) -> HttpResponse:
    """
    Public profile page - Phase 5B privacy-aware with permission enforcement.
    
    Route: /@<username>/
    
    Privacy Enforcement (Phase 5B):
    - Uses ProfilePermissionChecker to compute can_view_* flags
    - Passes permissions to template for server-side conditional rendering
    - NO CSS-only privacy (sections not rendered if private)
    - Viewer roles: owner / follower / visitor / anonymous
    
    Shows (if permitted):
    - Display name, avatar, bio, verification badges
    - Game passports (if can_view_game_passports)
    - Achievements (if can_view_achievements)
    - Teams (if can_view_teams)
    - Social links (if can_view_social_links)
    - Wallet (owner only)
    - Activity feed preview
    
    Args:
        request: HTTP request
        username: Username of profile to view
        
    Returns:
        Rendered profile.html template with permission flags
    """
    # Get user and profile
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        profile_user = User.objects.get(username=username)
        user_profile = UserProfile.objects.get(user=profile_user)
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        raise Http404(f"User @{username} not found")
    
    # Phase 5B: Compute permissions using ProfilePermissionChecker
    permission_checker = ProfilePermissionChecker(
        viewer=request.user if request.user.is_authenticated else None,
        profile=user_profile
    )
    permissions = permission_checker.get_all_permissions()
    
    # Phase 6B: Add follow request status for private account button states
    if request.user.is_authenticated and request.user != profile_user:
        permissions['is_following'] = FollowService.is_following(
            follower_user=request.user,
            followee_user=profile_user
        )
        permissions['has_pending_request'] = FollowService.has_pending_follow_request(
            requester_user=request.user,
            target_user=profile_user
        )
    else:
        permissions['is_following'] = False
        permissions['has_pending_request'] = False
    
    # Block access if profile is private
    if not permissions['can_view_profile']:
        return render(request, 'user_profile/profile_private.html', {
            'profile_user': profile_user,
            'profile': user_profile,
            'viewer_role': permissions['viewer_role'],
            'has_pending_request': permissions.get('has_pending_request', False),
        })
    
    # Build safe context (existing logic)
    context = build_public_profile_context(
        viewer=request.user if request.user.is_authenticated else None,
        username=username,
        requested_sections=['basic', 'stats', 'games', 'social', 'activity'],
        activity_page=1,
        activity_per_page=10  # Preview only (show last 10)
    )
    
    # Phase 5B: Add permission flags to context
    context.update(permissions)
    
    # UP.2 FIX: Add explicit is_owner (alias for is_own_profile) + user_profile for template
    context['is_owner'] = permissions.get('is_own_profile', False)
    context['user_profile'] = user_profile  # For level, kyc_status access
    
    # UP.2 HOTFIX: Compute wallet_balance safely (prevent VariableDoesNotExist crash)
    wallet_balance = 0
    if context['is_owner']:
        dc_wallet = getattr(user_profile, 'dc_wallet', None)
        if dc_wallet:
            wallet_balance = dc_wallet.cached_balance or dc_wallet.balance or 0
    
    context['wallet_balance'] = wallet_balance  # Safe int for template
    
    # UP.2 FIX PASS #2 + #5: Social Links proper wiring with URL filtering
    from apps.user_profile.models import SocialLink
    
    discord_handle = ''
    discord_url = ''
    social_links_renderable = []
    
    if context['is_owner'] or permissions.get('can_view_social_links'):
        social_links = SocialLink.objects.filter(user=profile_user).order_by('platform')
        
        for link in social_links:
            url = (link.url or '').strip()
            handle = (link.handle or '').strip()
            
            # UP.2 FIX PASS #5 PART B: Normalize URL only if missing scheme
            if url and not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            # UP.2 FIX PASS #5 PART A: Extract Discord separately for copy button
            if link.platform == 'discord':
                discord_handle = handle
                discord_url = url
            
            # UP.2 FIX PASS #5 PART C: Only include if URL exists (no blanks)
            if url:
                social_links_renderable.append({
                    'platform': link.platform,
                    'url': url,
                    'handle': handle
                })
        
        # Debug logging for verification (remove after testing)
        logger.info(f"[UP.2 FIX PASS #5] Social links for {profile_user.username}: {social_links_renderable}")
        
        # Build platform map for backward compatibility
        social_links_map = {link.platform: link for link in social_links}
        context['social_links'] = list(social_links)
        context['social_links_map'] = social_links_map
    else:
        context['social_links'] = []
        context['social_links_map'] = {}
    
    # UP.2 FIX PASS #5: Pass filtered data to template
    context['discord_handle'] = discord_handle
    context['discord_url'] = discord_url
    context['social_links_renderable'] = social_links_renderable
    
    # UP.2 FIX PASS #2: Hardware Gear wiring (PART 4)
    from apps.user_profile.models import HardwareGear
    # Owner always sees gear, visitors only if profile public (no specific gear privacy setting)
    if context['is_owner'] or permissions.get('can_view_profile'):
        hardware_gears = HardwareGear.objects.filter(
            user=profile_user,
            is_public=True
        ).order_by('category')
        context['hardware_gears'] = list(hardware_gears)
    else:
        context['hardware_gears'] = []
    
    # UP.2 FIX PASS #3: Connections context (CANONICAL UserProfile fields + SocialLink)
    # CANONICAL FIELDS (apps/user_profile/models_main.py):
    #   - phone (CharField, line 122)
    #   - whatsapp (CharField, line 128)
    #   - secondary_email (EmailField, line 134) - public/contact email
    #   - preferred_contact_method (CharField with choices: email/phone/whatsapp/discord/facebook, line 143)
    #   - discord_id (CharField, DEPRECATED legacy field, line 222 - use SocialLink instead)
    # SOCIAL LINKS: SocialLink model (platform, url, handle)
    # PRIVACY: show_preferred_contact (PrivacySettings.show_preferred_contact, line 987)
    
    privacy_settings = user_profile.privacy_settings
    connections = {
        'public_email': user_profile.secondary_email if user_profile.secondary_email_verified else '',
        'phone': user_profile.phone if (context['is_owner'] or privacy_settings.show_preferred_contact) else '',
        'whatsapp': user_profile.whatsapp if (context['is_owner'] or privacy_settings.show_preferred_contact) else '',
        'preferred_method': user_profile.preferred_contact_method,
        'social': {}  # Will be populated from SocialLink
    }
    
    # Build social dict from SocialLink (canonical storage for social URLs)
    if context['is_owner'] or permissions.get('can_view_social_links'):
        for link in context.get('social_links', []):
            connections['social'][link.platform] = {
                'url': link.url,
                'handle': link.handle
            }
    
    context['connections'] = connections
    
    # Compute preferred_contact for Hero button
    preferred_contact = {'label': '', 'href': '', 'icon': ''}
    pref_method = user_profile.preferred_contact_method
    
    if pref_method == 'email' and connections['public_email']:
        preferred_contact = {
            'label': 'Email',
            'href': f"mailto:{connections['public_email']}",
            'icon': 'fa-solid fa-envelope'
        }
    elif pref_method == 'phone' and connections['phone']:
        preferred_contact = {
            'label': 'Call',
            'href': f"tel:{connections['phone']}",
            'icon': 'fa-solid fa-phone'
        }
    elif pref_method == 'whatsapp' and connections['whatsapp']:
        # Strip + and spaces for wa.me link
        wa_number = connections['whatsapp'].replace('+', '').replace(' ', '').replace('-', '')
        preferred_contact = {
            'label': 'WhatsApp',
            'href': f"https://wa.me/{wa_number}",
            'icon': 'fa-brands fa-whatsapp'
        }
    elif pref_method == 'discord' and 'discord' in connections['social']:
        preferred_contact = {
            'label': 'Discord',
            'href': connections['social']['discord']['url'],
            'icon': 'fa-brands fa-discord'
        }
    elif pref_method == 'facebook' and 'facebook' in connections['social']:
        preferred_contact = {
            'label': 'Facebook',
            'href': connections['social']['facebook']['url'],
            'icon': 'fa-brands fa-facebook'
        }
    elif 'discord' in connections['social']:  # Fallback to Discord if available
        preferred_contact = {
            'label': 'Discord',
            'href': connections['social']['discord']['url'],
            'icon': 'fa-brands fa-discord'
        }
    # else: preferred_contact stays empty (button will be hidden)
    
    context['preferred_contact'] = preferred_contact
    
    # P0 SAFETY: Wallet data ONLY for owner (never expose to non-owners)
    if context['is_owner']:
        try:
            from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
            wallet, _ = DeltaCrownWallet.objects.get_or_create(user=profile_user)
            
            # Owner-only wallet data
            context['wallet'] = wallet
            context['wallet_visible'] = True
            context['wallet_transactions'] = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).order_by('-created_at')[:10]  # Last 10 transactions
            
            # BDT conversion rate (example: 1 DeltaCoin = 0.10 BDT)
            context['bdt_conversion_rate'] = 0.10
        except Exception as e:
            logger.warning(f"Failed to load wallet data for {username}: {e}")
            context['wallet'] = None
            context['wallet_visible'] = False
            context['wallet_transactions'] = []
    else:
        # Non-owner: NO wallet data in context
        context['wallet'] = None
        context['wallet_visible'] = False
        context['wallet_transactions'] = []
    
    # Add page metadata
    context['page_title'] = f"@{username} - DeltaCrown Esports"
    context['current_page'] = 'profile'
    
    # GP-FE-MVP-01: Add game passports with pinned/unpinned separation
    # GP-FINAL-01: Add team badge integration
    # UP-UI-REBIRTH-01: Remove role from passport display (role belongs to team)
    from apps.user_profile.services.game_passport_service import GamePassportService
    
    try:
        # Reuse profile_user and user_profile from earlier in function (lines 70-72)
        # DO NOT re-query - causes UnboundLocalError
        all_passports = GamePassportService.get_all_passports(user=profile_user)
        
        # UP-UI-REBIRTH-02: Add profile_user to context for template access
        context['profile_user'] = profile_user
        # PHASE-3.7.1 FIX: DO NOT overwrite context['profile'] dict!
        # The build_public_profile_context() already created a safe profile dict
        # with avatar_url and banner_url. Overwriting with ORM object breaks image rendering.
        # Templates that need ORM fields should use profile_user instead.
        
        # Attach team badge data to each passport (NO ROLE - role belongs to team context)
        if user_profile:
            from apps.teams.models import TeamMembership
            for passport in all_passports:
                # Get active team for this game
                team_membership = TeamMembership.objects.filter(
                    profile=user_profile,
                    team__game=passport.game,
                    status=TeamMembership.Status.ACTIVE
                ).select_related('team').first()
                
                if team_membership:
                    passport.current_team = team_membership.team
                    # UP-UI-REBIRTH-01: Do NOT attach role to passport
                else:
                    passport.current_team = None
        
        # Separate pinned and unpinned
        pinned_passports = [p for p in all_passports if p.is_pinned]
        unpinned_passports = [p for p in all_passports if not p.is_pinned]
        
        context['pinned_passports'] = pinned_passports
        context['unpinned_passports'] = unpinned_passports
        context['MAX_PINNED_GAMES'] = 6  # From GameProfile model constant
    except Exception as e:
        # Defensive: Catch any passport service errors
        logger.warning(f"Failed to load game passports for {username}: {e}")
        context['pinned_passports'] = []
        context['unpinned_passports'] = []
        context['MAX_PINNED_GAMES'] = 6
    
    # UP-UI-REBIRTH-01: Add dashboard navigation sections
    nav_sections = [
        {'id': 'stats', 'label': 'Stats'},
        {'id': 'passports', 'label': 'Passports'},
        {'id': 'teams', 'label': 'Teams'},
        {'id': 'tournaments', 'label': 'Tournaments'},
    ]
    
    if context.get('is_owner'):
        nav_sections.extend([
            {'id': 'economy', 'label': 'Economy'},
            {'id': 'shop', 'label': 'Shop'},
        ])
    
    nav_sections.extend([
        {'id': 'activity', 'label': 'Activity'},
        {'id': 'about', 'label': 'About'},
    ])
    
    if context.get('achievements'):
        nav_sections.insert(-2, {'id': 'achievements', 'label': 'Achievements'})
    
    context['nav_sections'] = nav_sections
    
    # UP-TEAM-DISPLAY-01: Add user's teams data
    if user_profile:
        from apps.teams.models import TeamMembership
        user_teams = TeamMembership.objects.filter(
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).select_related('team').order_by('-team__created_at')[:10]
        
        # Get game display names from Game model
        from apps.games.models import Game
        games_map = {g.slug: g.display_name for g in Game.objects.all()}
        
        context['user_teams'] = [
            {
                'id': tm.team.id,
                'slug': tm.team.slug,
                'name': tm.team.name,
                'tag': tm.team.tag,
                'game': games_map.get(tm.team.game, tm.team.game),
                'game_slug': tm.team.game,
                'role': tm.role,
                'logo_url': tm.team.logo.url if tm.team.logo else None,
                'is_captain': tm.role == 'CAPTAIN',
            }
            for tm in user_teams
        ]
    else:
        context['user_teams'] = []
    
    # PHASE-4D: Career Context Service - Modern portfolio view
    from apps.user_profile.services.career_context import build_career_context, get_game_passports_for_career
    
    career_data = build_career_context(user_profile, is_owner=permissions.get('is_owner', False))
    context.update(career_data)  # Adds current_teams, team_history, career_timeline, has_teams
    
    # Add game passports preview for Career tab (top 3)
    context['career_passports'] = get_game_passports_for_career(profile_user, limit=3)
    
    # UP-TOURNAMENT-DISPLAY-01: Add user's tournaments data
    # TODO: Implement tournament participation query when tournament app is ready
    
    # PHASE-4C: About Data Command Center - Privacy-Aware Fields
    from apps.user_profile.models import PrivacySettings, CareerProfile, HardwareLoadout
    
    privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=user_profile)
    career_profile, _ = CareerProfile.objects.get_or_create(user_profile=user_profile)
    hardware_loadout, _ = HardwareLoadout.objects.get_or_create(user_profile=user_profile)
    
    is_owner = permissions.get('is_owner', False)
    
    # Build privacy-aware about_fields dict
    about_fields = {
        'personal': {
            'country': {
                'value': user_profile.country,
                'visible': bool(user_profile.country) and (is_owner or privacy_settings.show_country),
                'icon': 'fa-location-dot',
                'label': 'Location'
            },
            'pronouns': {
                'value': user_profile.pronouns,
                'visible': bool(user_profile.pronouns) and (is_owner or privacy_settings.show_pronouns),
                'icon': 'fa-id-badge',
                'label': 'Pronouns'
            },
            'nationality': {
                'value': user_profile.nationality,
                'visible': bool(user_profile.nationality) and (is_owner or privacy_settings.show_nationality),
                'icon': 'fa-flag',
                'label': 'Nationality'
            },
            'age': {
                'value': f"{user_profile.age} years" if user_profile.age else None,
                'visible': bool(user_profile.age) and (is_owner or privacy_settings.show_age),
                'icon': 'fa-cake-candles',
                'label': 'Age'
            },
        },
        'competitive': {
            'device_platform': {
                'value': user_profile.get_device_platform_display() if user_profile.device_platform else None,
                'visible': bool(user_profile.device_platform) and (is_owner or privacy_settings.show_device_platform),
                'icon': 'fa-gamepad',
                'label': 'Platform'
            },
            'play_style': {
                'value': user_profile.get_play_style_display() if user_profile.play_style else None,
                'visible': bool(user_profile.play_style) and (is_owner or privacy_settings.show_play_style),
                'icon': 'fa-bolt',
                'label': 'Play Style'
            },
            'lan_availability': {
                'value': 'LAN Ready' if user_profile.lan_availability else None,
                'visible': bool(user_profile.lan_availability) and (is_owner or privacy_settings.show_active_hours),
                'icon': 'fa-tower-broadcast',
                'label': 'LAN Status',
                'badge': True
            },
            'main_role': {
                'value': user_profile.main_role,
                'visible': bool(user_profile.main_role) and (is_owner or privacy_settings.show_roles),
                'icon': 'fa-chess-king',
                'label': 'Main Role'
            },
            'secondary_role': {
                'value': user_profile.secondary_role,
                'visible': bool(user_profile.secondary_role) and (is_owner or privacy_settings.show_roles),
                'icon': 'fa-chess-rook',
                'label': 'Secondary Role'
            },
            'career_status': {
                'value': career_profile.get_career_status_display() if career_profile.career_status else None,
                'visible': bool(career_profile.career_status),
                'icon': 'fa-briefcase',
                'label': 'Career Status'
            },
        },
        'logistics': {
            'communication_languages': {
                'value': ', '.join(user_profile.communication_languages) if user_profile.communication_languages else None,
                'visible': bool(user_profile.communication_languages),
                'icon': 'fa-language',
                'label': 'Languages'
            },
            'active_hours': {
                'value': user_profile.active_hours,
                'visible': bool(user_profile.active_hours) and (is_owner or privacy_settings.show_active_hours),
                'icon': 'fa-clock',
                'label': 'Active Hours'
            },
        },
        'contact': {
            'preferred_contact': {
                'value': user_profile.get_preferred_contact_method_display() if user_profile.preferred_contact_method else None,
                'visible': bool(user_profile.preferred_contact_method) and (is_owner or privacy_settings.show_preferred_contact),
                'icon': 'fa-message',
                'label': 'Preferred Contact'
            },
            'discord_id': {
                'value': user_profile.discord_id,
                'visible': bool(user_profile.discord_id) and user_profile.preferred_contact_method == 'DISCORD' and (is_owner or privacy_settings.show_preferred_contact),
                'icon': 'fa-brands fa-discord',
                'label': 'Discord ID'
            },
            'whatsapp': {
                'value': user_profile.whatsapp,
                'visible': bool(user_profile.whatsapp) and user_profile.preferred_contact_method == 'WHATSAPP' and (is_owner or privacy_settings.show_preferred_contact),
                'icon': 'fa-brands fa-whatsapp',
                'label': 'WhatsApp'
            },
        }
    }
    
    context['about_fields'] = about_fields
    
    # PHASE-4C: Profile Completeness Calculator
    total_fields = 25  # Approximate count of profile fields
    filled_fields = 0
    
    # Count filled fields
    if user_profile.display_name: filled_fields += 1
    if user_profile.bio: filled_fields += 1
    if user_profile.country: filled_fields += 1
    if user_profile.city: filled_fields += 1
    if user_profile.pronouns: filled_fields += 1
    if user_profile.nationality: filled_fields += 1
    if user_profile.device_platform: filled_fields += 1
    if user_profile.play_style: filled_fields += 1
    if user_profile.main_role: filled_fields += 1
    if user_profile.secondary_role: filled_fields += 1
    if user_profile.communication_languages: filled_fields += 1
    if user_profile.active_hours: filled_fields += 1
    if user_profile.discord_id: filled_fields += 1
    if user_profile.avatar: filled_fields += 1
    if user_profile.banner: filled_fields += 1
    if all_passports: filled_fields += 2  # Game IDs worth 2 points
    if context['user_teams']: filled_fields += 2  # Teams worth 2 points
    if hardware_loadout.is_complete: filled_fields += 2  # Complete loadout worth 2 points
    if career_profile.career_status: filled_fields += 1
    if career_profile.primary_roles: filled_fields += 1
    if career_profile.availability: filled_fields += 1
    
    profile_completeness = int((filled_fields / total_fields) * 100)
    
    context['profile_completeness'] = profile_completeness
    context['profile_completeness_filled'] = filled_fields
    context['profile_completeness_total'] = total_fields
    
    # PHASE-4C: Hardware Loadout for preview cards
    context['hardware_loadout'] = hardware_loadout
    context['career_settings'] = career_profile  # Alias for template compatibility
    context['user_tournaments'] = []
    
    # Phase 5B Workstream 3: Add follower count for real follow button
    from apps.user_profile.models import Follow, PrivacySettings
    context['follower_count'] = Follow.objects.filter(following=profile_user).count()
    context['following_count'] = Follow.objects.filter(follower=profile_user).count()
    context['is_following'] = False
    if request.user.is_authenticated and request.user != profile_user:
        context['is_following'] = Follow.objects.filter(
            follower=request.user,
            following=profile_user
        ).exists()
    
    # Add privacy settings to context for follower/following visibility
    try:
        privacy_settings = PrivacySettings.objects.get(user_profile=user_profile)
        context['privacy'] = {
            'show_followers_count': privacy_settings.show_followers_count if hasattr(privacy_settings, 'show_followers_count') else True,
            'show_following_count': privacy_settings.show_following_count if hasattr(privacy_settings, 'show_following_count') else True,
            'show_followers_list': privacy_settings.show_followers_list if hasattr(privacy_settings, 'show_followers_list') else True,
            'show_following_list': privacy_settings.show_following_list if hasattr(privacy_settings, 'show_following_list') else True,
        }
    except PrivacySettings.DoesNotExist:
        # Default to public if no settings
        context['privacy'] = {
            'show_followers_count': True,
            'show_following_count': True,
            'show_followers_list': True,
            'show_following_list': True,
        }
    
    # UP-PHASE14C: Add ProfileShowcase data for About section
    from apps.user_profile.models import ProfileShowcase
    try:
        showcase = ProfileShowcase.objects.get(user_profile=user_profile)
        context['showcase'] = {
            'enabled_sections': showcase.get_enabled_sections(),
            'section_order': showcase.section_order or [],
            'featured_team_id': showcase.featured_team_id,
            'featured_team_role': showcase.featured_team_role,
            'featured_passport_id': showcase.featured_passport_id,
            'highlights': showcase.highlights or []
        }
    except ProfileShowcase.DoesNotExist:
        # Create default showcase
        context['showcase'] = {
            'enabled_sections': ProfileShowcase.get_default_sections(),
            'section_order': [],
            'featured_team_id': None,
            'featured_team_role': '',
            'featured_passport_id': None,
            'highlights': []
        }
    
    # UP-PHASE14C: Add real achievements data (if user has permission to view)
    if permissions.get('can_view_achievements'):
        from apps.user_profile.models import UserBadge
        achievements = UserBadge.objects.filter(
            user=profile_user
        ).select_related('badge').order_by('-earned_at')[:12]
        context['achievements'] = [
            {
                'id': badge.id,
                'name': badge.badge.name,
                'description': badge.badge.description,
                'icon': badge.badge.icon,
                'awarded_at': badge.earned_at,
                'rarity': getattr(badge.badge, 'rarity', 'common')
            }
            for badge in achievements
        ]
    else:
        context['achievements'] = None  # Blocked by privacy
    
    # UP-PHASE14C: Add real social links data (respecting privacy)
    if permissions.get('can_view_social_links'):
        from apps.user_profile.models import SocialLink
        social_links = SocialLink.objects.filter(
            user=profile_user
        ).order_by('platform')
        context['social_links'] = [
            {
                'platform': link.platform,
                'url': link.url,
                'handle': link.handle
            }
            for link in social_links
        ]
    else:
        context['social_links'] = None  # Blocked by privacy
    
    # UP-PHASE14C: Add real stats data
    from apps.user_profile.models import UserProfileStats
    try:
        stats = UserProfileStats.objects.get(user_profile=user_profile)
        context['user_stats'] = {
            'total_matches': stats.total_matches,
            'total_wins': stats.total_wins,
            'win_rate': round((stats.total_wins / stats.total_matches * 100) if stats.total_matches > 0 else 0, 1),
            'tournaments_played': stats.tournaments_played,
            'tournaments_won': stats.tournaments_won,
            'total_kills': getattr(stats, 'total_kills', 0),
            'total_deaths': getattr(stats, 'total_deaths', 0),
            'kd_ratio': round((getattr(stats, 'total_kills', 0) / getattr(stats, 'total_deaths', 1)) if getattr(stats, 'total_deaths', 0) > 0 else 0, 2)
        }
    except UserProfileStats.DoesNotExist:
        # No stats yet
        context['user_stats'] = {
            'total_matches': 0,
            'total_wins': 0,
            'win_rate': 0,
            'tournaments_played': 0,
            'tournaments_won': 0,
            'total_kills': 0,
            'total_deaths': 0,
            'kd_ratio': 0
        }
    
    # UP-PHASE14C: Add match history data (respect privacy)
    if permissions.get('can_view_match_history'):
        from apps.tournaments.models import Match, Registration
        from django.db.models import Q
        
        # Get user's registrations
        user_registration_ids = list(
            Registration.objects.filter(
                user=profile_user,
                is_deleted=False
            ).values_list('id', flat=True)
        )
        
        # Get recent matches where user participated (via Registration)
        if user_registration_ids:
            matches = Match.objects.filter(
                Q(participant1_id__in=user_registration_ids) | Q(participant2_id__in=user_registration_ids),
                state__in=['completed', 'disputed'],
                is_deleted=False
            ).select_related('tournament').order_by('-scheduled_time')[:10]
            
            context['match_history'] = [
                {
                    'id': match.id,
                    'tournament_name': match.tournament.name if match.tournament else 'Unknown',
                    'game': match.tournament.game if match.tournament else None,
                    'participant1_name': match.participant1_name or 'Participant 1',
                    'participant2_name': match.participant2_name or 'Participant 2',
                    'participant1_score': match.participant1_score,
                    'participant2_score': match.participant2_score,
                    'winner_id': match.winner_id,
                    'scheduled_time': match.scheduled_time,
                    'state': match.state,
                    'is_user_winner': match.winner_id in user_registration_ids if match.winner_id else False
                }
                for match in matches
            ]
        else:
            context['match_history'] = []  # No registrations found
    else:
        context['match_history'] = None  # Blocked by privacy
    
    # UP-PHASE15: Add About items (Facebook-style About section)
    from apps.user_profile.models import ProfileAboutItem
    is_follower = permissions.get('is_follower', False)
    
    # Query About items (with privacy filtering)
    about_items = ProfileAboutItem.objects.filter(
        user_profile=user_profile,
        is_active=True
    ).order_by('order_index', '-created_at')
    
    # Filter by viewer permissions
    filtered_about_items = []
    for item in about_items:
        viewer_user = request.user if request.user.is_authenticated else None
        if item.can_be_viewed_by(viewer_user, is_follower):
            filtered_about_items.append({
                'id': item.id,
                'item_type': item.item_type,
                'display_text': item.display_text,
                'icon_emoji': item.icon_emoji,
                'visibility': item.visibility
            })
    
    context['about_items'] = filtered_about_items
    
    # ========================================================================
    # 06c: STREAM CONTEXT (Live Stream Embed)
    # ========================================================================
    from apps.user_profile.models import StreamConfig
    try:
        stream_config = StreamConfig.objects.select_related('user').get(
            user=profile_user,
            is_active=True
        )
        context['stream_config'] = {
            'platform': stream_config.platform,
            'embed_url': stream_config.embed_url,
            'title': stream_config.title or f"{profile_user.username}'s stream",
            'stream_url': stream_config.stream_url,
        }
    except StreamConfig.DoesNotExist:
        context['stream_config'] = None
    
    # ========================================================================
    # 06c: HIGHLIGHTS CONTEXT (Pinned + All Clips)
    # ========================================================================
    from apps.user_profile.models import HighlightClip, PinnedHighlight
    
    # Get pinned highlight
    try:
        pinned = PinnedHighlight.objects.select_related('clip', 'clip__game').get(user=profile_user)
        context['pinned_highlight'] = {
            'id': pinned.clip.id,
            'title': pinned.clip.title,
            'embed_url': pinned.clip.embed_url,
            'thumbnail_url': pinned.clip.thumbnail_url,
            'platform': pinned.clip.platform,
            'game': pinned.clip.game.display_name if pinned.clip.game else None,
            'created_at': pinned.clip.created_at,
        }
    except PinnedHighlight.DoesNotExist:
        context['pinned_highlight'] = None
    
    # Get all highlight clips (ordered by display_order)
    highlights = HighlightClip.objects.filter(
        user=profile_user
    ).select_related('game').order_by('display_order', '-created_at')[:20]
    
    context['highlight_clips'] = [
        {
            'id': clip.id,
            'title': clip.title,
            'description': getattr(clip, 'description', ''),
            'embed_url': clip.embed_url,
            'thumbnail_url': clip.thumbnail_url,
            'platform': clip.platform,
            'video_id': clip.video_id,
            'game': clip.game.display_name if clip.game else None,
            'display_order': clip.display_order,
            'created_at': clip.created_at,
            'is_pinned': context['pinned_highlight'] and clip.id == context['pinned_highlight']['id'],
        }
        for clip in highlights
    ]
    context['can_add_more_clips'] = len(context['highlight_clips']) < 20
    
    # ========================================================================
    # 06c: LOADOUT CONTEXT (Hardware + Game Configs)
    # ========================================================================
    from apps.user_profile.services import loadout_service
    
    # Get complete loadout (hardware + game configs)
    # Only show public items for non-owners
    loadout_data = loadout_service.get_complete_loadout(
        user=profile_user,
        public_only=not permissions.get('is_owner', False)
    )
    
    def serialize_hardware(hw_item):
        """Convert HardwareGear ORM object into JSON-safe dict for template."""
        if not hw_item:
            return None
        return {
            'id': hw_item.id,
            'category': hw_item.category,
            'brand': hw_item.brand,
            'model': hw_item.model,
            'specs': hw_item.specs or {},
            'purchase_url': hw_item.purchase_url,
            'is_public': hw_item.is_public,
            'updated_at': hw_item.updated_at.isoformat(),
        }

    context['hardware_gear'] = {
        'mouse': serialize_hardware(loadout_data['hardware'].get('MOUSE')),
        'keyboard': serialize_hardware(loadout_data['hardware'].get('KEYBOARD')),
        'headset': serialize_hardware(loadout_data['hardware'].get('HEADSET')),
        'monitor': serialize_hardware(loadout_data['hardware'].get('MONITOR')),
        'mousepad': serialize_hardware(loadout_data['hardware'].get('MOUSEPAD')),
    }
    context['has_loadout'] = loadout_service.has_loadout(profile_user)
    
    # Game configs (per-game settings)
    context['game_configs'] = [
        {
            'id': config.id,
            'game': config.game.display_name,
            'game_slug': config.game.slug,
            'settings': config.settings,
            'notes': config.notes,
            'is_public': config.is_public,
            'updated_at': config.updated_at.isoformat(),
        }
        for config in loadout_data['game_configs']
    ]
    
    # ========================================================================
    # 06c: SHOWCASE CONTEXT (Trophy Showcase - Equipped + Unlocked)
    # ========================================================================
    from apps.user_profile.services import trophy_showcase_service
    
    showcase_data = trophy_showcase_service.get_showcase_data(profile_user)
    
    context['trophy_showcase'] = {
        'equipped_border': showcase_data['equipped']['border'],
        'equipped_frame': showcase_data['equipped']['frame'],
        'unlocked_borders': showcase_data['unlocked']['borders'],
        'unlocked_frames': showcase_data['unlocked']['frames'],
        'pinned_badges': showcase_data.get('pinned_badges', []),
    }
    
    # ========================================================================
    # 06c: ENDORSEMENTS CONTEXT (Peer Recognition)
    # ========================================================================
    from apps.user_profile.services import endorsement_service
    
    endorsements_summary = endorsement_service.get_endorsements_summary(profile_user)
    
    context['endorsements'] = {
        'total_count': endorsements_summary['total_count'],
        'by_skill': endorsements_summary['by_skill'],  # Dict: {'aim': 15, 'clutch': 8, ...}
        'top_skill': endorsements_summary.get('top_skill'),  # Most endorsed skill
        'recent_endorsements': [
            {
                'skill': e.skill_name,
                'skill_display': e.get_skill_name_display(),
                'endorser': e.endorser.username,
                'match_id': e.match_id,
                'created_at': e.created_at,
            }
            for e in endorsements_summary.get('recent_endorsements', [])[:5]
        ],
    }
    
    # ========================================================================
    # 06c: BOUNTIES CONTEXT (Peer Challenges)
    # ========================================================================
    from apps.user_profile.services import bounty_service
    
    # Bounty stats
    bounty_stats = bounty_service.get_user_bounty_stats(profile_user)
    context['bounty_stats'] = {
        'created_count': bounty_stats['created_count'],
        'accepted_count': bounty_stats['accepted_count'],
        'won_count': bounty_stats['won_count'],
        'lost_count': bounty_stats['lost_count'],
        'win_rate': bounty_stats['win_rate'],
        'total_earnings': bounty_stats['total_earnings'],
        'total_wagered': bounty_stats['total_wagered'],
    }
    
    # Active bounties
    active_bounties = bounty_service.get_active_bounties(profile_user)
    context['active_bounties'] = [
        {
            'id': bounty.id,
            'title': bounty.title,
            'game': bounty.game.display_name if bounty.game else None,
            'stake_amount': bounty.stake_amount,
            'status': bounty.status,
            'status_display': bounty.get_status_display(),
            'creator': bounty.creator.username,
            'creator_id': bounty.creator.id,
            'acceptor': bounty.acceptor.username if bounty.acceptor else None,
            'acceptor_id': bounty.acceptor.id if bounty.acceptor else None,
            'created_at': bounty.created_at,
            'expires_at': bounty.expires_at,
            'is_expired': bounty.is_expired,
            'can_dispute': bounty.can_dispute if hasattr(bounty, 'can_dispute') else False,
        }
        for bounty in active_bounties[:10]
    ]
    
    # Completed bounties (last 5 for profile display)
    completed_bounties = bounty_service.get_completed_bounties(profile_user)
    context['completed_bounties'] = [
        {
            'id': bounty.id,
            'title': bounty.title,
            'game': bounty.game.display_name if bounty.game else None,
            'stake_amount': bounty.stake_amount,
            'payout_amount': bounty.payout_amount,
            'winner': bounty.winner.username if bounty.winner else None,
            'completed_at': bounty.completed_at,
            'was_winner': bounty.winner_id == profile_user.id if bounty.winner_id else False,
        }
        for bounty in completed_bounties[:5]
    ]
    
    # Render new Zenith profile template (Phase 2B.1)
    return render(request, 'user_profile/profile/public_profile.html', context)


def profile_activity_view(request: HttpRequest, username: str) -> HttpResponse:
    """
    Activity feed page - paginated activity timeline.
    
    Route: /@<username>/activity/
    
    Shows:
    - Full activity feed (paginated)
    - Event types: tournaments, matches, achievements, badges, level ups
    - Public: only public events
    - Owner: all events
    
    Privacy:
    - Activity events filtered by is_owner
    - Pagination: 25 events per page
    - NO raw Activity objects in context
    
    Args:
        request: HTTP request
        username: Username of profile to view
        
    Returns:
        Rendered profile_activity.html template
    """
    # Get page number from query params
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    # Build safe context (activity-focused)
    context = build_public_profile_context(
        viewer=request.user if request.user.is_authenticated else None,
        username=username,
        requested_sections=['basic', 'activity'],
        activity_page=page,
        activity_per_page=25
    )
    
    # Check if profile was found
    if not context['can_view'] or context.get('error'):
        if context.get('error') == f'User @{username} not found':
            raise Http404(f"User @{username} not found")
        else:
            messages.error(request, context.get('error', 'Profile could not be loaded'))
            return redirect('home')
    
    # Add page metadata
    context['page_title'] = f"@{username} Activity - DeltaCrown Esports"
    context['current_page'] = 'activity'
    
    return render(request, 'user_profile/profile/activity.html', context)


@login_required
def profile_settings_view(request: HttpRequest) -> HttpResponse:
    """
    Profile settings page - owner-only.
    
    Route: /me/settings/
    
    Shows:
    - Display name, bio, avatar, banner (edit forms)
    - Game profiles (add/edit/remove)
    - Social links (add/edit/remove)
    - Location (country, region)
    
    Privacy:
    - Owner-only (requires authentication)
    - Uses build_public_profile_context with owner_only section
    - POST to save settings via settings_tab routing (Phase 4C.1.2)
    
    Args:
        request: HTTP request (must be authenticated)
        
    Returns:
        Rendered profile_settings.html template (GET) or JSON response (POST)
    """
    from apps.user_profile.models import UserProfile, PrivacySettings
    from apps.user_profile.forms import UserProfileSettingsForm, AboutSettingsForm
    from django.http import JsonResponse
    import logging
    
    logger = logging.getLogger(__name__)
    user_profile = UserProfile.objects.get(user=request.user)
    
    # PHASE 4C.1.2: Handle POST requests for settings tabs
    if request.method == 'POST':
        settings_tab = request.POST.get('settings_tab', 'identity')
        
        try:
            if settings_tab == 'about':
                # Phase 4C.1.2 FIX: Use dedicated AboutSettingsForm to avoid requiring unrelated fields
                form = AboutSettingsForm(
                    request.POST, 
                    instance=user_profile
                )
                
                if form.is_valid():
                    form.save()
                    logger.info(f"About settings saved by user {request.user.username}")
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'About settings saved successfully'
                    })
                else:
                    # Form validation failed
                    error_messages = []
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_messages.append(f"{field}: {error}")
                    
                    logger.warning(f"About form validation failed: {error_messages}")
                    logger.debug(f"POST data: {request.POST}")
                    
                    return JsonResponse({
                        'success': False,
                        'error': '; '.join(error_messages),
                        'errors': form.errors
                    }, status=400)
                    
            elif settings_tab in ['identity', 'connections', 'social', 'platform']:
                # Profile settings (other tabs)
                form = UserProfileSettingsForm(
                    request.POST, 
                    request.FILES, 
                    instance=user_profile
                )
                
                if form.is_valid():
                    # Handle KYC-locked fields
                    if user_profile.is_kyc_verified and 'real_full_name' in form.changed_data:
                        return JsonResponse({
                            'success': False,
                            'error': 'Cannot change legal name after KYC verification.'
                        }, status=400)
                    
                    form.save()
                    logger.info(f"Settings saved for tab '{settings_tab}' by user {request.user.username}")
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'{settings_tab.title()} settings saved successfully'
                    })
                else:
                    # Form validation failed
                    error_messages = []
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_messages.append(f"{field}: {error}")
                    
                    logger.warning(f"Form validation failed for tab '{settings_tab}': {error_messages}")
                    
                    return JsonResponse({
                        'success': False,
                        'error': '; '.join(error_messages),
                        'errors': form.errors
                    }, status=400)
            else:
                # Unknown tab
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown settings tab: {settings_tab}'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error saving {settings_tab} settings: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)
    
    # GET request - render settings page
    username = request.user.username
    
    # Build safe context (owner view with edit permissions)
    context = build_public_profile_context(
        viewer=request.user,
        username=username,
        requested_sections=['basic', 'games', 'social', 'owner_only']
    )
    
    # UP.2 FIX PASS #6: Add ALL social platform links to context (not just Discord)
    from apps.user_profile.models import SocialLink
    
    # Fetch all social links for the user
    social_links = SocialLink.objects.filter(user=request.user)
    social_links_map = {link.platform: link for link in social_links}
    
    # Add to context for template access
    context['social_links_map'] = social_links_map
    
    # Individual variables for backward compatibility (template may reference these)
    context['discord_link'] = social_links_map.get('discord')
    context['youtube_link'] = social_links_map.get('youtube')
    context['twitch_link'] = social_links_map.get('twitch')
    context['twitter_link'] = social_links_map.get('twitter')
    context['facebook_link'] = social_links_map.get('facebook')
    context['instagram_link'] = social_links_map.get('instagram')
    context['tiktok_link'] = social_links_map.get('tiktok')
    
    logger.info(f"[UP.2 FIX PASS #6] Settings context for {request.user.username}: {list(social_links_map.keys())}")

    
    # Verify owner (should always be true due to @login_required + using request.user.username)
    if not context['is_owner']:
        messages.error(request, 'You can only edit your own profile')
        return redirect(reverse('user_profile:public_profile', kwargs={'username': username}))
    
    # Add page metadata
    context['page_title'] = 'Profile Settings - DeltaCrown Esports'
    context['current_page'] = 'settings'
    
    # Add UserProfile object for template access to FileFields (avatar, banner)
    context['user_profile'] = user_profile
    
    # Add privacy settings (for Control Deck)
    privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=user_profile)
    context['privacy_settings'] = privacy_settings
    
    # Add wallet (for Control Deck billing section)
    from apps.economy.models import DeltaCrownWallet
    try:
        wallet = DeltaCrownWallet.objects.get(profile=user_profile)
        context['wallet'] = wallet
    except DeltaCrownWallet.DoesNotExist:
        context['wallet'] = None
    
    # Add game profiles (for Control Deck passports section)
    from apps.user_profile.models import GameProfile
    game_profiles = GameProfile.objects.filter(
        user=request.user
    ).select_related('game').order_by(
        '-is_pinned',           # Pinned first
        'pinned_order',         # Then by pinned order
        'sort_order',           # Then by general sort order
        '-updated_at'           # Newest first as fallback
    )
    context['game_profiles'] = game_profiles
    
    # Add CSRF token (for forms)
    # Add available games list (for game profile form)
    from apps.games.constants import SUPPORTED_GAMES
    from apps.games.models import Game
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import SocialLink
    import json
    
    # TASK 1 FIX: Pass actual Game objects for template loop + schema matrix
    supported_game_slugs = list(SUPPORTED_GAMES.keys())
    games_queryset = Game.objects.filter(slug__in=supported_game_slugs).order_by('name')
    
    # Build schema matrix for dynamic field rendering
    game_schemas = {}
    for game in games_queryset:
        identity_configs = game.identity_configs.all().order_by('order')
        schema_fields = []
        for config in identity_configs:
            schema_fields.append({
                'field_name': config.field_name,
                'display_name': config.display_name,
                'field_type': config.field_type,
                'is_required': config.is_required,
                'placeholder': config.placeholder,
                'help_text': config.help_text,
                'validation_regex': config.validation_regex or '',
                'min_length': config.min_length,
                'max_length': config.max_length,
            })
        
        game_schemas[game.slug] = {
            'game_id': game.id,
            'name': game.name,
            'display_name': game.display_name,
            'fields': schema_fields,
            'platforms': game.platforms or [],
        }
    
    context['games'] = games_queryset  # For template loop in modal
    context['game_schemas_json'] = json.dumps(game_schemas)  # For JS dynamic fields
    context['available_games'] = SUPPORTED_GAMES  # Legacy compatibility
    
    # GP-FE-MVP-01: Add passport management data
    all_passports = GamePassportService.get_all_passports(user=request.user)
    pinned_passports = [p for p in all_passports if p.is_pinned]
    unpinned_passports = [p for p in all_passports if not p.is_pinned]
    
    context['all_passports'] = all_passports
    context['passports'] = all_passports  # UP-UI-REBIRTH-01: Alias for settings template
    context['pinned_passports'] = pinned_passports
    context['unpinned_passports'] = unpinned_passports
    context['MAX_PINNED_GAMES'] = 6
    context['VISIBILITY_CHOICES'] = GameProfile.VISIBILITY_CHOICES
    
    # UP-SETTINGS-UI-01: Add social links data for settings template
    context['social_links'] = SocialLink.objects.filter(user=request.user)
    context['social_platforms'] = SocialLink.PLATFORM_CHOICES
    
    # UP-2025-REDESIGN: Add user game profiles for settings template
    context['user_passports'] = GameProfile.objects.filter(
        user=request.user
    ).select_related('game').order_by('-created_at')
    
    # UP-PHASE15-SESSION3: Add JSON data for Vanilla JS controller
    context['profile_data'] = json.dumps({
        'display_name': user_profile.display_name or request.user.username,
        'bio': user_profile.bio or '',
        'country': user_profile.country or '',
        'pronouns': user_profile.pronouns or '',
    })
    
    # Notification preferences (dummy data for MVP - actual implementation later)
    context['notification_data'] = json.dumps({
        'email': {
            'tournaments': True,
            'matches': True,
            'team_invites': True,
        },
        'platform': {
            'in_app': True,
            'browser': False,
        }
    })
    
    # Platform preferences
    context['platform_data'] = json.dumps({
        'preferred_language': getattr(user_profile, 'preferred_language', 'en'),
        'timezone_pref': getattr(user_profile, 'timezone_pref', 'Asia/Dhaka'),
        'time_format': getattr(user_profile, 'time_format', '12h'),
        'theme_preference': getattr(user_profile, 'theme_preference', 'dark'),
    })
    
    # Wallet settings (dummy data - actual implementation later)
    context['wallet_data'] = json.dumps({
        'bkash_account': getattr(user_profile, 'bkash_account', ''),
        'nagad_account': getattr(user_profile, 'nagad_account', ''),
        'rocket_account': getattr(user_profile, 'rocket_account', ''),
    })
    
    # UP-PHASE2A: Career & Matchmaking settings
    from apps.user_profile.models import (
        CareerProfile, MatchmakingPreferences,
        CAREER_STATUS_CHOICES, AVAILABILITY_CHOICES, 
        CONTRACT_TYPE_CHOICES, RECRUITER_VISIBILITY_CHOICES
    )
    
    career_settings, _ = CareerProfile.objects.get_or_create(user_profile=user_profile)
    matchmaking_settings, _ = MatchmakingPreferences.objects.get_or_create(user_profile=user_profile)
    
    context['career_settings'] = career_settings
    context['matchmaking_settings'] = matchmaking_settings
    context['career_status_choices'] = CAREER_STATUS_CHOICES
    context['availability_choices'] = AVAILABILITY_CHOICES
    context['contract_type_choices'] = CONTRACT_TYPE_CHOICES
    context['recruiter_visibility_choices'] = RECRUITER_VISIBILITY_CHOICES
    
    # Role choices for career settings
    ROLE_CHOICES = [
        'IGL',
        'Duelist',
        'Support',
        'AWPer',
        'Entry Fragger',
        'Anchor',
        'Flex',
        'Controller',
        'Initiator',
        'Sentinel',
        'Rifler',
        'Lurker',
    ]
    context['role_choices'] = ROLE_CHOICES
    
    # UP-PHASE2B: Notification settings
    from apps.user_profile.models import NotificationPreferences
    notification_settings, _ = NotificationPreferences.objects.get_or_create(user_profile=user_profile)
    context['notification_settings'] = notification_settings
    
    # Phase 4C.1: Add communication_languages as comma-separated string for template
    comm_langs = user_profile.communication_languages
    if isinstance(comm_langs, list) and comm_langs:
        context['communication_languages_str'] = ', '.join(comm_langs)
    else:
        context['communication_languages_str'] = ''
    context['notification_settings'] = notification_settings
    
    # UP-PHASE2B: Dynamic games list for matchmaking
    from apps.games.models import Game
    available_games = Game.objects.filter(is_active=True).order_by('name')
    context['available_games_for_matchmaking'] = available_games
    
    # PHASE 1C FIX: Add hardware_gear context for loadout display
    from apps.user_profile.services import loadout_service
    
    loadout_data = loadout_service.get_complete_loadout(
        user=request.user,
        public_only=False  # Owner view - show all
    )
    
    def serialize_hardware(hw_item):
        """Convert HardwareGear ORM object into JSON-safe dict for template."""
        if not hw_item:
            return None
        return {
            'id': hw_item.id,
            'category': hw_item.category,
            'brand': hw_item.brand,
            'model': hw_item.model,
            'specs': hw_item.specs or {},
            'purchase_url': hw_item.purchase_url,
            'is_public': hw_item.is_public,
            'updated_at': hw_item.updated_at.isoformat(),
        }
    
    context['hardware_gear'] = {
        'mouse': serialize_hardware(loadout_data['hardware'].get('MOUSE')),
        'keyboard': serialize_hardware(loadout_data['hardware'].get('KEYBOARD')),
        'headset': serialize_hardware(loadout_data['hardware'].get('HEADSET')),
        'monitor': serialize_hardware(loadout_data['hardware'].get('MONITOR')),
    }
    
    # Feature flag: Switch to Control Deck template
    from django.conf import settings as django_settings
    if django_settings.SETTINGS_CONTROL_DECK_ENABLED:
        template = 'user_profile/profile/settings_control_deck.html'
    else:
        template = 'user_profile/profile/settings_v4.html'
    
    return render(request, template, context)


@login_required
def profile_privacy_view(request: HttpRequest) -> HttpResponse:
    """
    Privacy settings page - owner-only.
    
    Route: /me/privacy/
    
    Shows:
    - Profile visibility (public, friends_only, private)
    - Field visibility (show_email, show_phone, show_real_name)
    - Social privacy (allow_friend_requests, show_online_status)
    
    Privacy:
    - Owner-only (requires authentication)
    - Uses build_public_profile_context with owner_only section
    - POST to safe endpoint: privacy_settings_save_safe
    
    Args:
        request: HTTP request (must be authenticated)
        
    Returns:
        Rendered profile_privacy.html template
    """
    username = request.user.username
    
    # Build safe context (owner view with privacy settings)
    context = build_public_profile_context(
        viewer=request.user,
        username=username,
        requested_sections=['basic', 'owner_only']
    )
    
    # Verify owner
    if not context['is_owner']:
        messages.error(request, 'You can only edit your own privacy settings')
        return redirect(reverse('user_profile:public_profile', kwargs={'username': username}))
    
    # Add page metadata
    context['page_title'] = 'Privacy Settings - DeltaCrown Esports'
    context['current_page'] = 'privacy'
    
    # UP-SETTINGS-UI-01: Add privacy_settings object for enhanced privacy template
    from apps.user_profile.models import PrivacySettings
    from apps.user_profile.utils import get_user_profile_safe
    
    # Fix: PrivacySettings is linked by user_profile, not user
    user_profile = get_user_profile_safe(request.user)
    privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=user_profile)
    context['privacy_settings'] = privacy_settings
    
    return render(request, 'user_profile/profile/privacy.html', context)


# ============================================
# MUTATION ENDPOINTS (UP-FE-MVP-02)
# ============================================

@login_required
def update_basic_info(request: HttpRequest) -> HttpResponse:
    """
    Update basic profile information (POST only).
    
    Route: POST /me/settings/basic/
    
    Fields:
    - display_name (required, max 50 chars)
    - bio (optional, max 500 chars)
    - country (optional, max 100 chars)
    - pronouns (optional, max 50 chars)
    - city (optional, max 100 chars)
    - postal_code (optional, max 20 chars)
    - address (optional, max 300 chars)
    - phone (optional, max 20 chars)
    - real_full_name (optional, max 200 chars)
    - date_of_birth (optional, YYYY-MM-DD format)
    - nationality (optional, max 100 chars)
    - gender (optional, from GENDER_CHOICES)
    - emergency_contact_name (optional, max 200 chars)
    - emergency_contact_phone (optional, max 20 chars)
    - emergency_contact_relation (optional, max 50 chars)
    
    Security:
    - CSRF protected (Django's @login_required + POST)
    - Input validation (server-side)
    - Audit logging with before/after snapshots
    
    Returns:
        JSON: {success: true, message: '...'}
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    import json
    from django.http import JsonResponse
    from apps.user_profile.utils import get_user_profile_safe
    from datetime import datetime
    
    profile = get_user_profile_safe(request.user)
    
    try:
        # Accept both JSON and form data (check content-type before accessing body)
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        elif request.content_type and 'multipart/form-data' in request.content_type:
            # FormData from frontend
            data = request.POST.dict()
        else:
            # Regular form POST or empty content-type
            data = request.POST.dict() if request.POST else {}
        
        # Capture before state for audit
        before_snapshot = {
            'display_name': profile.display_name,
            'bio': profile.bio,
            'country': profile.country,
            'pronouns': profile.pronouns,
        }
        
        # ===== BASIC PROFILE =====
        display_name = data.get('display_name', '').strip()
        if not display_name:
            return JsonResponse({'success': False, 'error': 'Display name is required'}, status=400)
        if len(display_name) > 80:
            return JsonResponse({'success': False, 'error': 'Display name must be 80 characters or less'}, status=400)
        profile.display_name = display_name
        
        bio = data.get('bio', '').strip()
        if len(bio) > 500:
            return JsonResponse({'success': False, 'error': 'Bio must be 500 characters or less'}, status=400)
        profile.bio = bio
        
        pronouns = data.get('pronouns', '').strip()
        if len(pronouns) > 50:
            return JsonResponse({'success': False, 'error': 'Pronouns must be 50 characters or less'}, status=400)
        profile.pronouns = pronouns
        
        # ===== LOCATION =====
        country = data.get('country', '').strip()
        if len(country) > 100:
            return JsonResponse({'success': False, 'error': 'Country must be 100 characters or less'}, status=400)
        profile.country = country
        
        city = data.get('city', '').strip()
        if len(city) > 100:
            return JsonResponse({'success': False, 'error': 'City must be 100 characters or less'}, status=400)
        profile.city = city
        
        postal_code = data.get('postal_code', '').strip()
        if len(postal_code) > 20:
            return JsonResponse({'success': False, 'error': 'Postal code must be 20 characters or less'}, status=400)
        profile.postal_code = postal_code
        
        address = data.get('address', '').strip()
        if len(address) > 300:
            return JsonResponse({'success': False, 'error': 'Address must be 300 characters or less'}, status=400)
        profile.address = address
        
        # ===== CONTACT =====
        phone = data.get('phone', '').strip()
        if len(phone) > 20:
            return JsonResponse({'success': False, 'error': 'Phone must be 20 characters or less'}, status=400)
        profile.phone = phone
        
        # WhatsApp (separate from phone)
        whatsapp = data.get('whatsapp', '').strip()
        if len(whatsapp) > 20:
            return JsonResponse({'success': False, 'error': 'WhatsApp must be 20 characters or less'}, status=400)
        profile.whatsapp = whatsapp
        
        # Secondary/Public Email (requires verification for display)
        secondary_email = data.get('secondary_email', '').strip()
        if secondary_email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as EmailValidationError
            try:
                validate_email(secondary_email)
                # If email changed, mark as unverified
                if profile.secondary_email != secondary_email:
                    profile.secondary_email = secondary_email
                    profile.secondary_email_verified = False
                    # TODO: Send OTP verification email
            except EmailValidationError:
                return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)
        else:
            profile.secondary_email = ''
            profile.secondary_email_verified = False
        
        # Preferred Contact Method
        preferred_contact = data.get('preferred_contact_method', '').strip()
        valid_methods = ['email', 'phone', 'whatsapp', 'discord', 'facebook']
        if preferred_contact and preferred_contact not in valid_methods:
            return JsonResponse({'success': False, 'error': 'Invalid contact method'}, status=400)
        profile.preferred_contact_method = preferred_contact
        
        # UP.2 FIX PASS #6: Save ALL social media platforms to SocialLink
        # Placeholder URLs to reject
        PLATFORM_PLACEHOLDERS = [
            'https://youtube.com/@username',
            'https://www.youtube.com/@username',
            'https://tiktok.com/@username',
            'https://www.tiktok.com/@username',
            'https://twitter.com/username',
            'https://x.com/username',
            'https://twitch.tv/username',
            'https://www.twitch.tv/username',
            'https://facebook.com/username',
            'https://www.facebook.com/username',
            'https://instagram.com/username',
            'https://www.instagram.com/username',
        ]
        
        # Define all platforms to process
        social_platforms = {
            'discord': {'url_field': 'discord_link', 'handle_field': 'discord_username'},
            'youtube': {'url_field': 'youtube_link', 'handle_field': None},
            'twitch': {'url_field': 'twitch_link', 'handle_field': None},
            'twitter': {'url_field': 'twitter', 'handle_field': None},
            'facebook': {'url_field': 'facebook', 'handle_field': None},
            'instagram': {'url_field': 'instagram', 'handle_field': None},
            'tiktok': {'url_field': 'tiktok', 'handle_field': None},
        }
        
        for platform, fields in social_platforms.items():
            url = data.get(fields['url_field'], '').strip()
            handle = data.get(fields['handle_field'], '').strip() if fields['handle_field'] else ''
            
            # Normalize URL (add https if missing)
            if url and not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            # Reject placeholder URLs
            if url.lower() in [p.lower() for p in PLATFORM_PLACEHOLDERS]:
                url = ''
            
            # Reject URLs containing literal '@username'
            if '@username' in url.lower():
                url = ''
            
            # Save or delete
            if url or handle:
                SocialLink.objects.update_or_create(
                    user=profile.user,
                    platform=platform,
                    defaults={
                        'url': url,
                        'handle': handle
                    }
                )
            else:
                # If both fields are empty, delete the link
                SocialLink.objects.filter(user=profile.user, platform=platform).delete()
        
        logger.info(f"[UP.2 FIX PASS #6] Saved SocialLinks for {profile.user.username}:")
        for link in SocialLink.objects.filter(user=profile.user):
            logger.info(f"  {link.platform}: url={link.url}, handle={link.handle}")
        
        # ===== LEGAL IDENTITY & KYC =====
        # Only allow updating if not KYC verified
        if profile.kyc_status != 'verified':
            real_full_name = data.get('real_full_name', '').strip()
            if len(real_full_name) > 200:
                return JsonResponse({'success': False, 'error': 'Full name must be 200 characters or less'}, status=400)
            profile.real_full_name = real_full_name
            
            nationality = data.get('nationality', '').strip()
            if len(nationality) > 100:
                return JsonResponse({'success': False, 'error': 'Nationality must be 100 characters or less'}, status=400)
            profile.nationality = nationality
            
            # Date of birth
            dob_str = data.get('date_of_birth', '').strip()
            if dob_str:
                try:
                    profile.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
            else:
                profile.date_of_birth = None
        
        # ===== DEMOGRAPHICS =====
        gender = data.get('gender', '').strip()
        if gender:
            from apps.user_profile.models_main import GENDER_CHOICES
            valid_genders = [choice[0] for choice in GENDER_CHOICES]
            if gender not in valid_genders:
                return JsonResponse({'success': False, 'error': 'Invalid gender selection'}, status=400)
            profile.gender = gender
        else:
            profile.gender = ''
        
        # ===== EMERGENCY CONTACT =====
        emergency_contact_name = data.get('emergency_contact_name', '').strip()
        if len(emergency_contact_name) > 200:
            return JsonResponse({'success': False, 'error': 'Emergency contact name must be 200 characters or less'}, status=400)
        profile.emergency_contact_name = emergency_contact_name
        
        emergency_contact_phone = data.get('emergency_contact_phone', '').strip()
        if len(emergency_contact_phone) > 20:
            return JsonResponse({'success': False, 'error': 'Emergency contact phone must be 20 characters or less'}, status=400)
        profile.emergency_contact_phone = emergency_contact_phone
        
        emergency_contact_relation = data.get('emergency_contact_relation', '').strip()
        if len(emergency_contact_relation) > 50:
            return JsonResponse({'success': False, 'error': 'Emergency contact relation must be 50 characters or less'}, status=400)
        profile.emergency_contact_relation = emergency_contact_relation
        
        # ===== SOCIAL MEDIA LINKS =====
        # UP.2 FIX PASS #6: DEPRECATED - These legacy fields are no longer saved
        # All social media URLs now saved to SocialLink model (see above)
        # Legacy fields remain on model for migration compatibility only
        # DO NOT SAVE TO: profile.youtube_link, profile.twitch_link, etc.
        
        # ===== DISCORD ID (legacy field for bot integration) =====
        discord_id = data.get('discord_id', '').strip()
        if len(discord_id) > 64:
            return JsonResponse({'success': False, 'error': 'Discord ID must be 64 characters or less'}, status=400)
        profile.discord_id = discord_id
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
def update_social_links(request: HttpRequest) -> HttpResponse:
    """
    Update social media links (POST only).
    
    Route: POST /me/settings/social/
    
    Fields:
    - youtube (optional, URL)
    - twitch (optional, URL)
    - twitter (optional, URL)
    - discord (optional, string)
    - instagram (optional, URL)
    
    Security:
    - CSRF protected (Django's @login_required + POST)
    - URL validation (server-side)
    - Audit logging with before/after snapshots
    
    Returns:
        Redirect to settings page with success/error message
    """
    if request.method != 'POST':
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Get user profile safely
    from apps.user_profile.utils import get_user_profile_safe
    profile = get_user_profile_safe(request.user)
    
    # Capture before state for audit
    before_snapshot = {
        'youtube_link': profile.youtube_link,
        'twitch_link': profile.twitch_link,
        'twitter': profile.twitter,
        'discord_id': profile.discord_id,
        'instagram': profile.instagram
    }
    
    # Validate and update fields
    youtube = request.POST.get('youtube', '').strip()
    twitch = request.POST.get('twitch', '').strip()
    twitter = request.POST.get('twitter', '').strip()
    discord = request.POST.get('discord', '').strip()
    instagram = request.POST.get('instagram', '').strip()
    
    # Basic URL validation (must start with http:// or https:// if provided)
    for field_name, field_value in [('YouTube', youtube), ('Twitch', twitch), 
                                     ('Twitter', twitter), ('Instagram', instagram)]:
        if field_value and not (field_value.startswith('http://') or field_value.startswith('https://')):
            messages.error(request, f'{field_name} must be a valid URL (http:// or https://)')
            return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Update profile
    profile.youtube_link = youtube
    profile.twitch_link = twitch
    profile.twitter = twitter
    profile.discord_id = discord
    profile.instagram = instagram
    profile.save()
    
    # Capture after state
    after_snapshot = {
        'youtube_link': profile.youtube_link,
        'twitch_link': profile.twitch_link,
        'twitter': profile.twitter,
        'discord_id': profile.discord_id,
        'instagram': profile.instagram
    }
    
    # Write audit event
    from apps.user_profile.services.audit_service import AuditService
    AuditService.log_event(
        user=request.user,
        event_type='profile.social_links_updated',
        before_state=before_snapshot,
        after_state=after_snapshot,
        request_meta={
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'path': request.path,
            'method': request.method
        }
    )
    
    messages.success(request, 'Social links updated successfully')
    return redirect(reverse('user_profile:profile_settings_v2'))
