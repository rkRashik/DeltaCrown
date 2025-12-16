# apps/user_profile/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import UserProfile
from .forms import UserProfileForm
import logging

logger = logging.getLogger(__name__)


def _should_debug(request=None):
    """Return True if we should print debug logs for this request.
    We allow debug logs if Django settings.DEBUG is True or the request user is a superuser.
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


def _get_upcoming_matches_for_user(user, limit=5):
    """
    Best-effort query for a user's active/upcoming matches.
    Safe against schema differences; returns [] on any issue.
    
    NOTE: Tournament system moved to legacy - this function disabled.
    """
    # Tournament system moved to legacy - no longer displaying match data
    return []


# ProfileForm moved to forms.py as UserProfileForm



class MyProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "users/profile_edit_modern.html"
    success_url = reverse_lazy("user_profile:edit")  # stay on the edit page

    class Meta:
        model = UserProfile
        fields = [
            "display_name", "region", "avatar", "bio",
            "discord_id", "riot_id", "efootball_id",
            # add privacy flags:
            "is_private", "show_email", "show_phone", "show_socials",
        ]

    def get_object(self, queryset=None):
        # Always edit your own profile
        return self.request.user.profile

    def post(self, request, *args, **kwargs):
        """
        If this POST only includes the 4 privacy flags, update them directly and skip
        the form (which requires other profile fields). Otherwise, fall back to the
        standard UpdateView form handling for full profile edits.
        """
        privacy_keys = {"is_private", "show_email", "show_phone", "show_socials"}
        posted_keys = set(k for k in request.POST.keys() if k != "csrfmiddlewaretoken")

        # If it's purely a privacy toggle POST, persist flags directly.
        if posted_keys and posted_keys.issubset(privacy_keys):
            is_private = bool(request.POST.get("is_private"))
            show_email = bool(request.POST.get("show_email"))
            show_phone = bool(request.POST.get("show_phone"))
            show_socials = bool(request.POST.get("show_socials"))

            # Write via the user relation to avoid any pk/instance drift
            UserProfile.objects.filter(user_id=request.user.id).update(
                is_private=is_private,
                show_email=show_email,
                show_phone=show_phone,
                show_socials=show_socials,
            )

            messages.success(request, "Your privacy settings have been saved.")
            return redirect(self.success_url)

        # Otherwise, proceed with normal form-driven update (full profile edits)
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Redirect GET requests for legacy edit page to the unified settings page
        from django.urls import reverse
        return redirect(reverse("user_profile:settings"))


User = get_user_model()


@login_required  
def profile_view(request, username=None):
    """
    Main profile view - displays user profile with all components.
    Phase 3 Implementation - Full backend integration.
    Phase 4 Fix: Corrected user lookup and profile access.
    DEBUG MODE: Extensive logging enabled.
    """
    import datetime
    from django.utils import timezone
    
    _debug_log(request, "profile_view() called")
    _debug_log(request, "" + "="*80)
    _debug_log(request, f"DEBUG [1]: Requested username: {username}")
    _debug_log(request, f"DEBUG [1]: Request.user: {request.user} (authenticated: {request.user.is_authenticated})")
    _debug_log(request, f"DEBUG [1]: Request.path: {request.path}")
    
    # Determine which user's profile to show
    if username is None:
        _debug_log(request, "DEBUG [2]: No username provided, redirecting to own profile")
        from django.shortcuts import redirect
        return redirect('user_profile:profile', username=request.user.username)
    
    # Get the user being viewed
    profile_user = get_object_or_404(User, username=username)
    _debug_log(request, f"DEBUG [3]: Found User: {profile_user} (ID: {profile_user.id})")
    _debug_log(request, f"DEBUG [3]: Profile User Email: {profile_user.email}")
    
    # Get the UserProfile instance (related_name='profile')
    try:
        profile = profile_user.profile
        _debug_log(request, f"DEBUG [4]: Profile found: {profile} (ID: {profile.id})")
        _debug_log(request, f"DEBUG [4]: Profile.display_name: {profile.display_name}")
        _debug_log(request, f"DEBUG [4]: Profile.bio: {profile.bio[:50] if profile.bio else 'None'}...")
    except UserProfile.DoesNotExist:
        _debug_log(request, "DEBUG [4]: Profile does NOT exist, creating new one...")
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=profile_user)
        _debug_log(request, f"DEBUG [4]: Profile created: {profile}")

    # Check if viewing own profile
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    _debug_log(request, f"DEBUG [5]: Request User: {request.user} vs Profile User: {profile_user}")
    _debug_log(request, f"DEBUG [5]: is_own_profile calculated as: {is_own_profile}")
    try:
        _debug_log(request, f"DEBUG [5]: Comparison: {request.user.id} == {profile_user.id} ? {request.user.id == profile_user.id}")
    except Exception:
        _debug_log(request, 'DEBUG [5]: Request.user may not have id attribute (Anonymous)')
    
    # ===== IDENTITY CARD DATA =====
    # Uses: profile.bio, profile.country, profile.city, profile.pronouns, 
    #       profile.age, profile.show_age (from property and PrivacySettings)
    
    # ===== VITAL STATS =====
    from apps.user_profile.models import Follow
    
    # Calculate real follower/following counts from Follow model
    follower_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()
    is_following = False
    if request.user.is_authenticated and not is_own_profile:
        is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    
    tournaments_played = 0
    total_matches = 0
    win_rate = 0
    total_earnings = 0
    
    if profile:
        # Follower/Following (placeholder - implement social system later)
        try:
            follower_count = profile.followers.count() if hasattr(profile, 'followers') else 0
            following_count = profile.following.count() if hasattr(profile, 'following') else 0
        except Exception as e:
            logger.warning(f"Error reading follower/following counts: {e}")
            follower_count = 0
            following_count = 0
        
        # Tournaments (placeholder - link to tournament system)
        try:
            tournaments_played = profile.tournament_participations.count()
        except Exception as e:
            logger.warning(f"Error reading tournaments_played: {e}")
            tournaments_played = 0
        
        # Match stats
        try:
            from apps.user_profile.models import Match
            total_matches = Match.objects.filter(user=profile_user).count()
            if total_matches > 0:
                wins = Match.objects.filter(user=profile_user, result='win').count()
                win_rate = int((wins / total_matches) * 100)
        except Exception as e:
            logger.warning(f"Error reading match stats: {e}")
            total_matches = 0
            win_rate = 0
        
        # Earnings (use total_earnings property from Phase 3)
        try:
            total_earnings = profile.total_earnings if hasattr(profile, 'total_earnings') else 0
        except Exception as e:
            logger.warning(f"Error reading total earnings: {e}")
            total_earnings = 0
    
    # ===== SOCIAL LINKS =====
    social_links = []
    if profile:
        try:
            from apps.user_profile.models import SocialLink
            social_links = SocialLink.objects.filter(user=profile_user).order_by('platform')
            _debug_log(request, f"DEBUG [6]: Social Links Count: {social_links.count()}")
            if social_links.exists():
                _debug_log(request, f"DEBUG [6]: First Social Link: {social_links.first().platform} - {social_links.first().url}")
        except Exception as e:
            logger.warning(f"DEBUG [6]: Error loading social links: {e}")
            social_links = []
    
    # ===== TROPHY SHELF (ACHIEVEMENTS) =====
    achievements = []
    if profile:
        try:
            from apps.user_profile.models import Achievement
            achievements = Achievement.objects.filter(user=profile_user).order_by('-earned_at')
            _debug_log(request, f"DEBUG [7]: Achievements Count: {achievements.count()}")
        except Exception as e:
            logger.warning(f"DEBUG [7]: Error loading achievements: {e}")
            achievements = []
    
    # ===== GAME PASSPORT =====
    game_profiles = []
    if profile:
        try:
            from apps.user_profile.models import GameProfile
            game_profiles = GameProfile.objects.filter(user=profile_user).order_by('-updated_at')
            _debug_log(request, f"DEBUG [8]: Game Profiles Count: {game_profiles.count()}")
            if game_profiles.exists():
                _debug_log(request, f"DEBUG [8]: First Game: {game_profiles.first().game} - {game_profiles.first().in_game_name}")
        except Exception as e:
            logger.warning(f"DEBUG [8]: Error loading game profiles: {e}")
            game_profiles = []
    
    # ===== MATCH HISTORY =====
    matches = []
    if profile:
        try:
            from apps.user_profile.models import Match
            matches = Match.objects.filter(user=profile_user).order_by('-played_at')[:5]
            _debug_log(request, f"DEBUG [9]: Match History Count: {matches.count()}")
        except Exception as e:
            logger.warning(f"DEBUG [9]: Error loading match history: {e}")
            matches = []
    
    # ===== TEAM CARD =====
    current_teams = []
    if profile:
        try:
            from apps.teams.models import TeamMembership
            active_memberships = TeamMembership.objects.filter(
                profile=profile,
                status='ACTIVE'
            ).select_related('team').order_by('-joined_at')
            current_teams = list(active_memberships)
            _debug_log(request, f"DEBUG [10]: Current Teams Count: {len(current_teams)}")
        except Exception as e:
            logger.warning(f"DEBUG [10]: Error loading team data: {e}")
            logger.warning(f"DEBUG [10]: Exception type: {type(e).__name__}")
            current_teams = []
    
    # ===== WALLET (OWNER ONLY) =====
    wallet = None
    recent_transactions = []
    usd_equivalent = 0
    if is_own_profile and profile:
        _debug_log(request, f"DEBUG [11]: Loading wallet for owner...")
        try:
            from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
            wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
            _debug_log(request, f"DEBUG [11]: Wallet Object: {wallet} (Balance: {wallet.cached_balance if wallet else 'N/A'})")
            _debug_log(request, f"DEBUG [11]: Wallet Created: {created}")
            
            # Compute USD equivalent (1 DC = $0.10 as per Phase 3 spec)
            if wallet and wallet.cached_balance:
                usd_equivalent = float(wallet.cached_balance) * 0.10
            
            recent_transactions = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).order_by('-created_at')[:3]
            _debug_log(request, f"DEBUG [11]: Recent Transactions Count: {recent_transactions.count()}")
        except Exception as e:
            logger.warning(f"DEBUG [11]: Error loading wallet data: {e}")
            logger.warning(f"DEBUG [11]: Exception type: {type(e).__name__}")
            wallet = None
            recent_transactions = []
    else:
        _debug_log(request, f"DEBUG [11]: Wallet NOT loaded (is_own_profile={is_own_profile})")
    
    # ===== CERTIFICATES =====
    certificates = []
    if profile:
        try:
            from apps.user_profile.models import Certificate
            certificates = Certificate.objects.filter(user=profile_user).order_by('-issued_at')
        except Exception as e:
            logger.warning(f"Error loading certificates: {e}")
            certificates = []
    
    # ===== NOTIFICATIONS (OWNER ONLY) =====
    unread_notification_count = 0
    if is_own_profile:
        try:
            from apps.notifications.models import Notification
            # Notification.recipient expects a User not a UserProfile
            unread_notification_count = Notification.objects.filter(
                recipient=profile_user,
                is_read=False
            ).count()
            _debug_log(request, f"DEBUG [12]: Unread Notifications: {unread_notification_count}")
        except Exception as e:
            logger.warning(f"Error loading notifications: {e}")
            unread_notification_count = 0
    
    # ===== CONTEXT FOR TEMPLATE =====
    _debug_log(request, "\nDEBUG [13]: Building context dictionary...")
    _debug_log(request, f"  - profile_user: {profile_user}")
    _debug_log(request, f"  - profile: {profile}")
    _debug_log(request, f"  - is_own_profile: {is_own_profile}")
    _debug_log(request, f"  - social_links: {len(list(social_links))} items")
    _debug_log(request, f"  - game_profiles: {len(list(game_profiles))} items")
    _debug_log(request, f"  - achievements: {len(list(achievements))} items")
    _debug_log(request, f"  - matches: {len(list(matches))} items")
    _debug_log(request, f"  - wallet: {wallet}")
    _debug_log(request, f"  - current_teams: {len(current_teams)} items")
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'user_profile': profile,  # COMPATIBILITY: Template may use either name
        'is_own_profile': is_own_profile,
        'is_following': is_following,
        
        # Force template refresh
        'current_time': timezone.now(),
        'debug_timestamp': datetime.datetime.now().isoformat(),
        
        # Vital Stats
        'follower_count': follower_count,
        'following_count': following_count,
        'tournaments_played': tournaments_played,
        'total_matches': total_matches,
        'win_rate': win_rate,
        'total_earnings': total_earnings,
        
        # Components
        'social_links': social_links,
        'achievements': achievements,
        'game_profiles': game_profiles,
        'matches': matches,
        'current_teams': current_teams,
        'wallet': wallet,
        'recent_transactions': recent_transactions,
        'usd_equivalent': usd_equivalent,
        'certificates': certificates,
        
        # Notifications
        'unread_notification_count': unread_notification_count,
        'debug': settings.DEBUG,
    }
    
    _debug_log(request, "\nDEBUG [14]: Context dictionary complete")
    _debug_log(request, "DEBUG [14]: Rendering template: user_profile/profile.html")
    _debug_log(request, "="*80 + "\n")
    
    return render(request, 'user_profile/profile.html', context)


@login_required
def my_tournaments_view(request):
    """
    Shows tournaments the current user is registered in (either solo or via teams).
    
    NOTE: Tournament system moved to legacy - this function disabled.
    """
    # Tournament system moved to legacy - no longer displaying tournament data
    regs = []
    return render(request, "user_profile/my_tournaments.html", {"registrations": regs})


# --------------------------- Notifications helper (unchanged) ---------------------------

def _recent_notifications_for_user(user, limit=10):
    try:
        from django.apps import apps
        Notification = apps.get_model("notifications", "Notification")
        # Prefer recipient Profile, but fall back to user if your Notification model uses user FK
        recipient_field = None
        for f in ("recipient", "user", "profile", "user_profile"):
            try:
                Notification._meta.get_field(f)
                recipient_field = f
                break
            except Exception:
                continue
        if recipient_field is None:
            return []

        target = user
        if recipient_field in ("profile", "user_profile"):
            target = getattr(user, "userprofile", None) or getattr(user, "profile", None)
            if not target:
                return []

        try:
            # Build a filter dict dynamically: {recipient_field: target}
            qs = Notification.objects.filter(**{recipient_field: target})
            # Try common created/ordering fields; otherwise fallback by id
            ordering = None
            for f in ("-created_at", "-created", "-created_on", "-timestamp", "-id"):
                try:
                    # quick check: raise if field not present
                    Notification._meta.get_field(f.lstrip("-"))
                    ordering = f
                    break
                except Exception:
                    continue
            if ordering:
                qs = qs.order_by(ordering)
            return list(qs[:limit])
        except Exception:
            return []
    except Exception:
        return []


# ============================================================================
# KYC VERIFICATION VIEWS
# ============================================================================

@login_required
def kyc_upload_view(request):
    """
    View for users to upload KYC verification documents.
    Users can submit ID documents and a selfie for verification.
    """
    from .forms import KYCUploadForm
    from .models import VerificationRecord
    
    profile = request.user.profile
    
    # Get or create verification record
    verification_record, created = VerificationRecord.objects.get_or_create(
        user_profile=profile,
        defaults={'status': 'unverified'}
    )
    
    # Don't allow resubmission if already verified
    if verification_record.status == 'verified':
        messages.info(request, 'Your KYC verification is already approved.')
        return redirect('user_profile:profile')
    
    # Don't allow resubmission while pending
    if verification_record.status == 'pending':
        messages.info(request, 'Your KYC verification is currently under review. Please wait for admin approval.')
        return redirect('user_profile:kyc_status')
    
    if request.method == 'POST':
        form = KYCUploadForm(request.POST, request.FILES, instance=verification_record)
        if form.is_valid():
            verification_record = form.save(commit=False)
            # Submit for review
            try:
                verification_record.submit_for_review()
                messages.success(
                    request, 
                    'KYC documents submitted successfully! Our team will review your submission within 24-48 hours.'
                )
                return redirect('user_profile:kyc_status')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = KYCUploadForm(instance=verification_record)
    
    context = {
        'form': form,
        'verification_record': verification_record,
        'profile': profile,
    }
    return render(request, 'user_profile/kyc_upload.html', context)


@login_required
def kyc_status_view(request):
    """
    View to display current KYC verification status.
    Shows pending/approved/rejected status with details.
    """
    from .models import VerificationRecord
    
    profile = request.user.profile
    
    try:
        verification_record = VerificationRecord.objects.get(user_profile=profile)
    except VerificationRecord.DoesNotExist:
        verification_record = None
    
    context = {
        'verification_record': verification_record,
        'profile': profile,
    }
    return render(request, 'user_profile/kyc_status.html', context)


# ============================================================================
# PRIVACY SETTINGS VIEWS
# ============================================================================

@login_required
def privacy_settings_view(request):
    """
    View for users to manage their privacy settings.
    Controls what information is visible to other users.
    """
    from .forms import PrivacySettingsForm
    from .models import PrivacySettings
    
    profile = request.user.profile
    
    # Get or create privacy settings
    privacy_settings, created = PrivacySettings.objects.get_or_create(
        user_profile=profile
    )
    
    if request.method == 'POST':
        form = PrivacySettingsForm(request.POST, instance=privacy_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Privacy settings updated successfully!')
            return redirect('user_profile:privacy_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PrivacySettingsForm(instance=privacy_settings)
    
    context = {
        'form': form,
        'privacy_settings': privacy_settings,
        'profile': profile,
    }
    return render(request, 'user_profile/privacy_settings.html', context)


@login_required
def settings_view(request):
    """
    Modular settings page with all settings sections in one place.
    Provides a unified interface for Profile, Privacy, KYC, Payment, Security, and Game Accounts.
    """
    from .models import PrivacySettings, VerificationRecord
    
    profile = request.user.profile
    
    # Get or create privacy settings
    privacy_settings, _ = PrivacySettings.objects.get_or_create(
        user_profile=profile
    )
    
    # Get verification record if exists
    verification_record = VerificationRecord.objects.filter(user_profile=profile).first()
    
    # Get existing game profiles
    from .models import GameProfile
    game_profiles = GameProfile.objects.filter(user=request.user).order_by('game')
    
    if request.method == 'POST':
        # Handle profile updates
        try:
            display_name = request.POST.get('display_name')
            bio = request.POST.get('bio')
            country = request.POST.get('country')
            city = request.POST.get('city')
            real_full_name = request.POST.get('real_full_name')
            date_of_birth = request.POST.get('date_of_birth')
            nationality = request.POST.get('nationality')
            # Update profile fields if present
            changed = False
            if display_name is not None:
                profile.display_name = display_name.strip()[:80]
                changed = True
            if bio is not None:
                profile.bio = bio.strip()[:500]
                changed = True
            if country is not None:
                profile.country = country.strip()
                changed = True
            if city is not None:
                profile.city = city.strip()
                changed = True
            if real_full_name is not None:
                # lock if KYC verified: follow existing behavior
                if not profile.is_kyc_verified:
                    profile.real_full_name = real_full_name.strip()
                    changed = True
            if date_of_birth:
                try:
                    from django.utils.dateparse import parse_date
                    parsed = parse_date(date_of_birth)
                    profile.date_of_birth = parsed
                    changed = True
                except Exception:
                    pass
            if nationality is not None:
                profile.nationality = nationality.strip()
                changed = True

            # Files: avatar/banner
            if request.FILES.get('avatar'):
                profile.avatar = request.FILES.get('avatar')
                changed = True
            if request.FILES.get('banner'):
                profile.banner = request.FILES.get('banner')
                changed = True

            # Game ID updates (legacy) - best effort
            riot_id = request.POST.get('riot_id')
            if riot_id is not None:
                profile.riot_id = riot_id.strip()
                changed = True
            steam_id = request.POST.get('steam_id')
            if steam_id is not None:
                profile.steam_id = steam_id.strip()
                changed = True
            mlbb_id = request.POST.get('mlbb_id')
            if mlbb_id is not None:
                profile.mlbb_id = mlbb_id.strip()
                changed = True
            ea_id = request.POST.get('ea_id')
            if ea_id is not None:
                profile.ea_id = ea_id.strip()
                changed = True
            pubg_mobile_id = request.POST.get('pubg_mobile_id')
            if pubg_mobile_id is not None:
                profile.pubg_mobile_id = pubg_mobile_id.strip()
                changed = True

            if changed:
                try:
                    profile.save()
                except Exception as e:
                    logger.warning(f"Error saving profile data: {e}")

        except Exception as e:
            logger.warning(f"Error handling profile update POST: {e}")

        # Handle privacy settings POST
        try:
            from .models import PrivacySettings
            privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
            privacy_settings.show_email = bool(request.POST.get('show_email'))
            privacy_settings.show_phone = bool(request.POST.get('show_phone'))
            privacy_settings.show_real_name = bool(request.POST.get('show_real_name'))
            privacy_settings.show_age = bool(request.POST.get('show_age'))
            privacy_settings.show_country = bool(request.POST.get('show_country'))
            privacy_settings.show_social_links = bool(request.POST.get('show_socials'))
            privacy_settings.allow_friend_requests = bool(request.POST.get('allow_friend_requests'))
            # Profile-level 'is_private' lives on the UserProfile model
            profile.is_private = bool(request.POST.get('is_private'))
            privacy_settings.save()
            profile.save()
        except Exception as e:
            logger.warning(f"Error saving privacy settings: {e}")

        messages.success(request, 'Your settings have been updated.')
        return redirect('user_profile:settings')

    # Get all game profiles from the unified game_profiles JSON field
    from apps.games.constants import ALL_GAMES, SUPPORTED_GAMES
    game_profile_data = {}
    for game_slug in ALL_GAMES:
        game_data = profile.get_game_profile(game_slug)
        if game_data:
            game_profile_data[f'{game_slug}_profile'] = game_data

    context = {
        'profile': profile,
        'privacy_settings': privacy_settings,
        'verification_record': verification_record,
        'game_profiles': game_profiles,
        **game_profile_data,  # Add all game profile data to context
    }

    return render(request, 'user_profile/settings.html', context)


@login_required
def save_game_profiles(request):
    """
    Handle saving all 11 game profiles from the unified settings form.
    Uses the game_profiles JSONField to store all game data.
    """
    if request.method != 'POST':
        return redirect('user_profile:settings')
    
    from apps.games.constants import ALL_GAMES
    profile = request.user.profile
    
    # Process each of the 11 games
    for game_slug in ALL_GAMES:
        ign = request.POST.get(f'game_{game_slug}_ign', '').strip()
        role = request.POST.get(f'game_{game_slug}_role', '').strip()
        rank = request.POST.get(f'game_{game_slug}_rank', '').strip()
        platform = request.POST.get(f'game_{game_slug}_platform', '').strip()
        
        # For MLBB, also capture server_id
        metadata = {}
        if game_slug == 'mlbb':
            server_id = request.POST.get('game_mlbb_server', '').strip()
            if server_id:
                metadata['server_id'] = server_id
        
        # If IGN is provided, save/update the profile
        if ign:
            profile.set_game_profile(game_slug, {
                'game': game_slug,
                'ign': ign,
                'role': role or None,
                'rank': rank or None,
                'platform': platform or None,
                'is_verified': False,
                'metadata': metadata
            })
        else:
            # If no IGN, remove the profile if it exists
            profile.remove_game_profile(game_slug)
    
    profile.save()
    messages.success(request, '✅ Game profiles saved successfully!')
    return redirect('user_profile:settings')


# ============================================================================
# PHASE 3: MODAL ACTION VIEWS
# ============================================================================

@login_required
def update_bio(request):
    """
    Handle bio update from Edit Bio modal.
    Frontend: _identity_card.html edit bio modal
    """
    if request.method == 'POST':
        bio = request.POST.get('bio', '').strip()
        
        # Validate length (500 char limit enforced by frontend)
        if len(bio) > 500:
            messages.error(request, 'Bio must be 500 characters or less.')
            return redirect('user_profile:profile', username=request.user.username)
        
        profile = request.user.profile
        profile.bio = bio
        profile.save(update_fields=['bio', 'updated_at'])
        
        messages.success(request, 'Bio updated successfully!')
    
    return redirect('user_profile:profile', username=request.user.username)


@login_required
def add_social_link(request):
    """
    Handle social link addition from Add Social Link modal.
    Frontend: _social_links.html add social modal
    """
    if request.method == 'POST':
        from apps.user_profile.models import SocialLink
        
        platform = request.POST.get('platform', '').strip()
        url = request.POST.get('url', '').strip()
        handle = request.POST.get('handle', '').strip()
        
        # Validate required fields
        if not platform or not url:
            messages.error(request, 'Platform and URL are required.')
            return redirect('user_profile:profile', username=request.user.username)
        
        try:
            # Update or create social link
            social_link, created = SocialLink.objects.update_or_create(
                user=request.user,
                platform=platform,
                defaults={
                    'url': url,
                    'handle': handle,
                }
            )
            
            if created:
                messages.success(request, f'{social_link.get_platform_display()} link added successfully!')
            else:
                messages.success(request, f'{social_link.get_platform_display()} link updated successfully!')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error adding social link: {str(e)}')
    
    return redirect('user_profile:profile', username=request.user.username)


@login_required
def add_game_profile(request):
    """
    Handle game profile addition from Add Game Profile modal or settings page.
    Frontend: _game_passport.html add game modal OR settings page form
    """
    if request.method == 'POST':
        from apps.user_profile.models import GameProfile
        
        game = request.POST.get('game', '').strip()
        in_game_name = request.POST.get('in_game_name', '').strip()
        rank_name = request.POST.get('rank_name', '').strip()
        main_role = request.POST.get('main_role', '').strip()
        
        # Determine redirect target (settings or profile)
        redirect_to = request.POST.get('redirect_to', 'profile')
        
        # Validate required fields
        if not game or not in_game_name:
            messages.error(request, 'Game and in-game username are required.')
            if redirect_to == 'settings':
                return redirect('user_profile:settings')
            return redirect('user_profile:profile', username=request.user.username)
        
        try:
            # Check if this game already exists for this user
            existing = GameProfile.objects.filter(user=request.user, game=game).first()
            if existing:
                messages.warning(request, f'You already have a {existing.game_display_name} profile. Edit it instead.')
                if redirect_to == 'settings':
                    return redirect('user_profile:settings')
                return redirect('user_profile:profile', username=request.user.username)
            
            # Create new game profile
            game_profile = GameProfile.objects.create(
                user=request.user,
                game=game,
                in_game_name=in_game_name,
                rank_name=rank_name,
                main_role=main_role,
            )
            
            messages.success(request, f'{game_profile.game_display_name} profile added successfully!')
                
        except Exception as e:
            messages.error(request, f'Error adding game profile: {str(e)}')
        
        if redirect_to == 'settings':
            return redirect('user_profile:settings')
        return redirect('user_profile:profile', username=request.user.username)
    
    # GET request - redirect to appropriate page
    return redirect('user_profile:settings')


@login_required
def edit_game_profile(request, profile_id):
    """
    Handle game profile editing from settings page.
    GET: Show edit form (or redirect to settings with modal data)
    POST: Update game profile
    """
    from apps.user_profile.models import GameProfile
    
    # Get the game profile or 404
    game_profile = get_object_or_404(GameProfile, id=profile_id, user=request.user)
    
    if request.method == 'POST':
        in_game_name = request.POST.get('in_game_name', '').strip()
        rank_name = request.POST.get('rank_name', '').strip()
        main_role = request.POST.get('main_role', '').strip()
        
        # Validate
        if not in_game_name:
            messages.error(request, 'In-game username is required.')
            return redirect('user_profile:settings')
        
        try:
            # Update fields
            game_profile.in_game_name = in_game_name
            game_profile.rank_name = rank_name
            game_profile.main_role = main_role
            game_profile.save()
            
            messages.success(request, f'{game_profile.game_display_name} profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating game profile: {str(e)}')
        
        return redirect('user_profile:settings')
    
    # GET: Render edit form (simple inline template or redirect back)
    # For now, redirect to settings with a message to use the form
    messages.info(request, f'Editing {game_profile.game_display_name} profile')
    return redirect('user_profile:settings')


@login_required
def delete_game_profile(request, profile_id):
    """
    Handle game profile deletion from settings page.
    POST only: Delete game profile
    """
    from apps.user_profile.models import GameProfile
    
    if request.method == 'POST':
        # Get the game profile or 404
        game_profile = get_object_or_404(GameProfile, id=profile_id, user=request.user)
        
        try:
            game_name = game_profile.game_display_name
            game_profile.delete()
            messages.success(request, f'{game_name} profile deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting game profile: {str(e)}')
    
    return redirect('user_profile:settings')


@login_required
def follow_user(request, username):
    """
    Follow a user (Ajax endpoint).
    """
    if request.method == 'POST':
        from apps.user_profile.models import Follow
        
        user_to_follow = get_object_or_404(User, username=username)
        
        if request.user == user_to_follow:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        
        try:
            follow, created = Follow.objects.get_or_create(
                follower=request.user,
                following=user_to_follow
            )
            
            if created:
                return JsonResponse({
                    'status': 'following',
                    'follower_count': user_to_follow.followers.count()
                })
            else:
                return JsonResponse({'error': 'Already following'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def unfollow_user(request, username):
    """
    Unfollow a user (Ajax endpoint).
    """
    if request.method == 'POST':
        from apps.user_profile.models import Follow
        
        user_to_unfollow = get_object_or_404(User, username=username)
        
        try:
            follow = Follow.objects.get(
                follower=request.user,
                following=user_to_unfollow
            )
            follow.delete()
            
            return JsonResponse({
                'status': 'unfollowed',
                'follower_count': user_to_unfollow.followers.count()
            })
        except Follow.DoesNotExist:
            return JsonResponse({'error': 'Not following'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def followers_list(request, username):
    """
    Instagram-style followers list modal view.
    """
    from apps.user_profile.models import Follow
    
    user = get_object_or_404(User, username=username)
    followers = Follow.objects.filter(following=user).select_related('follower__profile').order_by('-created_at')
    
    context = {
        'profile_user': user,
        'followers': followers,
        'is_own_profile': request.user == user,
    }
    
    return render(request, 'user_profile/followers_modal.html', context)


@login_required
def following_list(request, username):
    """
    Instagram-style following list modal view.
    """
    from apps.user_profile.models import Follow
    
    user = get_object_or_404(User, username=username)
    following = Follow.objects.filter(follower=user).select_related('following__profile').order_by('-created_at')
    
    context = {
        'profile_user': user,
        'following': following,
        'is_own_profile': request.user == user,
    }
    
    return render(request, 'user_profile/following_modal.html', context)


@login_required
def achievements_view(request, username):
    """
    View all achievements for a user.
    Full page view for trophy shelf.
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile
    is_own_profile = request.user == user
    
    from apps.user_profile.models import Achievement
    achievements = Achievement.objects.filter(user=user).order_by('-earned_at')
    
    context = {
        'profile_user': user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'achievements': achievements,
    }
    
    return render(request, 'user_profile/achievements.html', context)


@login_required
def match_history_view(request, username):
    """
    View full match history for a user.
    Full page view for match history.
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile
    is_own_profile = request.user == user
    
    from apps.user_profile.models import Match
    matches = Match.objects.filter(user=user).order_by('-played_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(matches, 25)  # 25 matches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile_user': user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'matches': page_obj,
    }
    
    return render(request, 'user_profile/match_history.html', context)


@login_required
def certificates_view(request, username):
    """
    View all certificates for a user.
    Full page view for certificates.
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile
    is_own_profile = request.user == user
    
    from apps.user_profile.models import Certificate
    certificates = Certificate.objects.filter(user=user).order_by('-issued_at')
    
    context = {
        'profile_user': user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'certificates': certificates,
    }
    
    return render(request, 'user_profile/certificates.html', context)


