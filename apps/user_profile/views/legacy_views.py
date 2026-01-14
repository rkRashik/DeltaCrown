# apps/user_profile/views/legacy_views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.user_profile.models import UserProfile
from apps.user_profile.forms import UserProfileForm
from apps.user_profile.decorators import deprecate_route
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
        ]

    def get_object(self, queryset=None):
        # Always edit your own profile
        return self.request.user.profile

    def post(self, request, *args, **kwargs):
        """
        Legacy privacy flag handling removed - privacy settings now managed
        via PrivacySettings model and /me/settings/privacy/ endpoint.
        This view only handles basic profile updates.
        """
        # Standard form-driven update for profile edits
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Redirect GET requests for legacy edit page to the unified settings page
        from django.urls import reverse
        return redirect(reverse("user_profile:settings"))


User = get_user_model()


@login_required
@deprecate_route(
    replacement="/@{username}/",
    reason="Legacy profile view bypasses privacy enforcement. Use views/public.py ProfileDetailView.",
    log_only=True
)
def profile_view(request, username=None):
    """
    Main profile view - displays user profile with all components.
    Phase 3 Implementation - Full backend integration.
    Phase 4 Fix: Corrected user lookup and profile access.
    DEBUG MODE: Extensive logging enabled.
    
    DEPRECATED: UP-CLEANUP-02 Phase A
    - No privacy filtering via PrivacyService
    - Direct model access
    - Replacement: views/public.py ProfileDetailView
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
    from apps.user_profile.forms import KYCUploadForm
    from apps.user_profile.models import VerificationRecord
    
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
    from apps.user_profile.models import VerificationRecord
    
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
# REMOVED (2026-01-14 C1 Cleanup): privacy_settings_view and settings_view
# Both functions were DEAD CODE - routes commented out in urls.py (lines 368, 371)
# Replaced by: profile_privacy_view and profile_settings_view respectively
# ============================================================================



@login_required
@deprecate_route(
    replacement="/api/v1/user_profile/game-id/<game_code>/",
    reason="Legacy game profile save lacks validation. Use api/game_id_api.py.",
    log_only=True
)
def save_game_profiles(request):
    """
    Handle saving all 11 game profiles from the unified settings form.
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService.
    """
    if request.method != 'POST':
        return redirect('user_profile:settings')
    
    from apps.games.constants import ALL_GAMES
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import GameProfile
    from django.core.exceptions import ValidationError
    
    created_count = 0
    updated_count = 0
    deleted_count = 0
    errors = []
    
    # Collect submitted games
    submitted_games = set()
    
    # Process each of the 11 games
    for game_slug in ALL_GAMES:
        ign = request.POST.get(f'game_{game_slug}_ign', '').strip()
        
        if not ign:
            continue
            
        submitted_games.add(game_slug)
        
        # Prepare metadata
        metadata = {}
        if game_slug == 'mlbb':
            server_id = request.POST.get('game_mlbb_server', '').strip()
            if server_id:
                metadata['zone_id'] = server_id
        
        try:
            # Check if passport exists
            existing = GameProfile.objects.filter(user=request.user, game=game_slug).first()
            
            if existing:
                # Update existing passport
                if existing.in_game_name != ign:
                    GamePassportService.update_passport_identity(
                        user=request.user,
                        game=game_slug,
                        new_in_game_name=ign,
                        new_metadata=metadata if metadata else None,
                        reason='Settings form update',
                        actor_user_id=request.user.id,
                        request_ip=request.META.get('REMOTE_ADDR')
                    )
                    updated_count += 1
            else:
                # Create new passport
                GamePassportService.create_passport(
                    user=request.user,
                    game=game_slug,
                    in_game_name=ign,
                    metadata=metadata,
                    actor_user_id=request.user.id,
                    request_ip=request.META.get('REMOTE_ADDR')
                )
                created_count += 1
        except ValidationError as e:
            errors.append(f"{game_slug}: {str(e)}")
        except Exception as e:
            errors.append(f"{game_slug}: Unexpected error")
            logger.error(f"Error saving {game_slug} for user {request.user.id}: {e}", exc_info=True)
    
    # Delete passports not in submitted data
    existing_passports = GameProfile.objects.filter(user=request.user)
    for passport in existing_passports:
        if passport.game not in submitted_games:
            try:
                passport.delete()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting {passport.game}")
    
    # Show results
    if errors:
        messages.warning(request, f'⚠️ Saved with errors: {created_count} created, {updated_count} updated, {deleted_count} deleted. Errors: {"; ".join(errors)}')
    else:
        messages.success(request, f'✅ Game profiles saved successfully! ({created_count} created, {updated_count} updated, {deleted_count} deleted)')
    
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
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService.
    """
    if request.method == 'POST':
        from apps.user_profile.models import GameProfile
        from apps.user_profile.services.game_passport_service import GamePassportService
        from django.core.exceptions import ValidationError
        
        game = request.POST.get('game', '').strip()
        in_game_name = request.POST.get('in_game_name', '').strip()
        
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
            
            # Create new game passport via service
            game_profile = GamePassportService.create_passport(
                user=request.user,
                game=game,
                in_game_name=in_game_name,
                metadata={},
                actor_user_id=request.user.id,
                request_ip=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'{game_profile.game_display_name} profile added successfully!')
                
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error adding game profile: {str(e)}')
            logger.error(f"Error adding game profile for user {request.user.id}: {e}", exc_info=True)
        
        if redirect_to == 'settings':
            return redirect('user_profile:settings')
        return redirect('user_profile:profile', username=request.user.username)
    
    # GET request - redirect to appropriate page
    return redirect('user_profile:settings')


@login_required
def edit_game_profile(request, profile_id):
    """
    Handle game profile editing from settings page.
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService.
    """
    from apps.user_profile.models import GameProfile
    from apps.user_profile.services.game_passport_service import GamePassportService
    from django.core.exceptions import ValidationError
    
    # Get the game profile or 404
    game_profile = get_object_or_404(GameProfile, id=profile_id, user=request.user)
    
    if request.method == 'POST':
        in_game_name = request.POST.get('in_game_name', '').strip()
        
        # Validate
        if not in_game_name:
            messages.error(request, 'In-game username is required.')
            return redirect('user_profile:settings')
        
        try:
            # Update via service if name changed
            if game_profile.in_game_name != in_game_name:
                GamePassportService.update_passport_identity(
                    user=request.user,
                    game=game_profile.game,
                    new_in_game_name=in_game_name,
                    reason='Settings form edit',
                    actor_user_id=request.user.id,
                    request_ip=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, f'{game_profile.game_display_name} profile updated successfully!')
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating game profile: {str(e)}')
            logger.error(f"Error updating game profile {profile_id} for user {request.user.id}: {e}", exc_info=True)
        
        return redirect('user_profile:settings')
    
    # GET: Render edit form (simple inline template or redirect back)
    # For now, redirect to settings with a message to use the form
    messages.info(request, f'Editing {game_profile.game_display_name} profile')
    return redirect('user_profile:settings')


@login_required
def delete_game_profile(request, profile_id):
    """
    Handle game profile deletion from settings page.
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService auditing.
    """
    from apps.user_profile.models import GameProfile
    from apps.user_profile.services.audit import AuditService
    from apps.user_profile.models.audit import UserAuditEvent
    
    if request.method == 'POST':
        # Get the game profile or 404
        game_profile = get_object_or_404(GameProfile, id=profile_id, user=request.user)
        
        try:
            game_name = game_profile.game_display_name
            game_code = game_profile.game
            
            # Audit before deletion
            AuditService.record_event(
                subject_user_id=request.user.id,
                event_type='game_passport.deleted',
                source_app='user_profile',
                object_type='GameProfile',
                object_id=game_profile.id,
                actor_user_id=request.user.id,
                before_snapshot={
                    'game': game_code,
                    'in_game_name': game_profile.in_game_name
                },
                metadata={
                    'deleted_via': 'settings_form',
                    'game_display_name': game_name
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            game_profile.delete()
            messages.success(request, f'{game_name} profile deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting game profile: {str(e)}')
            logger.error(f"Error deleting game profile {profile_id} for user {request.user.id}: {e}", exc_info=True)
    
    return redirect('user_profile:settings')


@login_required
@deprecate_route(
    replacement="/api/v1/user_profile/follow/{username}/",
    reason="Legacy follow endpoint lacks proper validation. Use services/follow_service.py.",
    log_only=True
)
def follow_user(request, username):
    """
    Follow a user (Ajax endpoint).
    
    DEPRECATED: UP-CLEANUP-02 Phase A
    - No validation for circular follows
    - No rate limiting
    - Replacement: services/follow_service.py
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
@deprecate_route(
    replacement="/@{username}/followers/",
    reason="Legacy followers list bypasses privacy checks. Use services/follow_service.py.",
    log_only=True
)
def followers_list(request, username):
    """
    Instagram-style followers list modal view.
    
    DEPRECATED: UP-CLEANUP-02 Phase A
    - No privacy filtering for follower visibility
    - Direct model access
    - Replacement: services/follow_service.py get_followers
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


# ============================================================================
# UP-CLEANUP-04 PHASE C PART 1: SAFE MUTATION ENDPOINTS
# ============================================================================

@login_required
def privacy_settings_save_safe(request):
    """
    Safe privacy settings update with audit trail.
    Replacement for privacy_settings_view POST handler.
    
    UP-CLEANUP-04 Phase C Part 1:
    - Uses PrivacySettingsService (audit trail)
    - Safe profile accessor
    - Backward compatible with existing forms
    """
    if request.method != 'POST':
        return redirect('user_profile:privacy_settings')
    
    settings_dict = {
        'show_email': bool(request.POST.get('show_email')),
        'show_phone': bool(request.POST.get('show_phone')),
        'show_real_name': bool(request.POST.get('show_real_name')),
        'show_age': bool(request.POST.get('show_age')),
        'show_country': bool(request.POST.get('show_country')),
        'show_social_links': bool(request.POST.get('show_socials')),
        'allow_friend_requests': bool(request.POST.get('allow_friend_requests')),
    }
    
    # Get request metadata for audit
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT')
    
    from apps.user_profile.services.privacy_settings_service import PrivacySettingsService
    PrivacySettingsService.update_settings(
        user=request.user,
        settings_dict=settings_dict,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    messages.success(request, 'Privacy settings updated successfully!')
    return redirect('user_profile:privacy_settings')


@login_required
def follow_user_safe(request, username):
    """
    Safe follow with privacy enforcement + audit.
    Replacement for follow_user.
    
    UP-CLEANUP-04 Phase C Part 1:
    - Uses FollowService (privacy + audit)
    - Safe profile accessors
    - Idempotent
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    from django.core.exceptions import PermissionDenied
    from apps.user_profile.services.follow_service import FollowService
    
    try:
        follow, created = FollowService.follow_user(
            follower_user=request.user,
            followee_username=username,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        followee_user = User.objects.get(username=username)
        
        return JsonResponse({
            'success': True,
            'status': 'following',
            'message': f'Following @{username}',
            'follower_count': followee_user.followers.count()
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


@login_required
def unfollow_user_safe(request, username):
    """
    Safe unfollow with audit trail (idempotent).
    Replacement for unfollow_user.
    
    UP-CLEANUP-04 Phase C Part 1:
    - Uses FollowService (audit trail)
    - Safe profile accessors
    - Idempotent (returns 200 even if not following)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    from apps.user_profile.services.follow_service import FollowService
    
    try:
        unfollowed = FollowService.unfollow_user(
            follower_user=request.user,
            followee_username=username,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        followee_user = User.objects.get(username=username)
        
        return JsonResponse({
            'success': True,
            'status': 'unfollowed',
            'message': f'Unfollowed @{username}',
            'follower_count': followee_user.followers.count(),
            'was_following': unfollowed
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


# ============================================================================
# UP-CLEANUP-04 PHASE C PART 2: SAFE MUTATION ENDPOINTS (Game Profiles)
# ============================================================================

@login_required
def save_game_profiles_safe(request):
    """
    Safe game profiles batch save with validation, deduplication, and audit.
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService.
    
    POST /actions/game-profiles/save/
    Accepts same params as legacy: game_{slug}_ign, game_{slug}_role, etc.
    """
    if request.method != 'POST':
        return redirect('user_profile:settings')
    
    from apps.games.constants import ALL_GAMES
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import GameProfile
    from django.core.exceptions import ValidationError
    
    created_count = 0
    updated_count = 0
    deleted_count = 0
    errors = []
    submitted_games = set()
    
    # Parse POST data for each game
    for game_slug in ALL_GAMES:
        ign = request.POST.get(f'game_{game_slug}_ign', '').strip()
        
        if not ign:
            continue
            
        submitted_games.add(game_slug)
        
        # For MLBB, capture zone_id
        metadata = {}
        if game_slug == 'mlbb':
            server_id = request.POST.get('game_mlbb_server', '').strip()
            if server_id:
                metadata['zone_id'] = server_id
        
        try:
            existing = GameProfile.objects.filter(user=request.user, game=game_slug).first()
            
            if existing:
                if existing.in_game_name != ign:
                    GamePassportService.update_passport_identity(
                        user=request.user,
                        game=game_slug,
                        new_in_game_name=ign,
                        new_metadata=metadata if metadata else None,
                        reason='Batch save',
                        actor_user_id=request.user.id,
                        request_ip=request.META.get('REMOTE_ADDR')
                    )
                    updated_count += 1
            else:
                GamePassportService.create_passport(
                    user=request.user,
                    game=game_slug,
                    in_game_name=ign,
                    metadata=metadata,
                    actor_user_id=request.user.id,
                    request_ip=request.META.get('REMOTE_ADDR')
                )
                created_count += 1
        except ValidationError as e:
            errors.append(f"{game_slug}: {str(e)}")
        except Exception as e:
            errors.append(f"{game_slug}: Unexpected error")
            logger.error(f"Error saving {game_slug}: {e}", exc_info=True)
    
    # Remove game profiles not in submitted data
    existing_passports = GameProfile.objects.filter(user=request.user)
    for passport in existing_passports:
        if passport.game not in submitted_games:
            try:
                from apps.user_profile.services.audit import AuditService
                AuditService.record_event(
                    subject_user_id=request.user.id,
                    event_type='game_passport.deleted',
                    source_app='user_profile',
                    object_type='GameProfile',
                    object_id=passport.id,
                    actor_user_id=request.user.id,
                    before_snapshot={
                        'game': passport.game,
                        'in_game_name': passport.in_game_name
                    },
                    metadata={'deleted_via': 'batch_save'},
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                passport.delete()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting {passport.game}")
    
    if errors:
        messages.warning(request, f'⚠️ Saved with errors: {created_count} created, {updated_count} updated, {deleted_count} deleted. Errors: {"; ".join(errors)}')
    else:
        messages.success(request, f'✅ Game profiles saved successfully! ({created_count} created, {updated_count} updated, {deleted_count} deleted)')
    
    return redirect('user_profile:settings')


@login_required
@require_http_methods(["POST"])
def update_game_id_safe(request):
    """
    Safe game ID update with validation, privacy enforcement, and audit.
    MIGRATED: GP-STABILIZE-02 - Now uses GamePassportService.
    
    POST /api/profile/update-game-id-safe/
    Body: {"game": "valorant", "ign": "Player#123", "role": "Duelist"}
    """
    import json
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import GameProfile
    from django.core.exceptions import ValidationError
    
    try:
        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        
        game_slug = data.get('game', '').lower().strip()
        ign = data.get('ign', '').strip()
        
        if not game_slug:
            return JsonResponse({
                'success': False,
                'error': 'Game code is required'
            }, status=400)
        
        if not ign:
            return JsonResponse({
                'success': False,
                'error': 'In-game name is required'
            }, status=400)
        
        # Prepare metadata
        metadata = data.get('metadata', {})
        
        # Check if passport exists
        existing = GameProfile.objects.filter(user=request.user, game=game_slug).first()
        
        if existing:
            # Update existing passport
            if existing.in_game_name != ign:
                game_profile = GamePassportService.update_passport_identity(
                    user=request.user,
                    game=game_slug,
                    new_in_game_name=ign,
                    new_metadata=metadata if metadata else None,
                    reason='API update',
                    actor_user_id=request.user.id,
                    request_ip=request.META.get('REMOTE_ADDR')
                )
                created = False
            else:
                game_profile = existing
                created = False
        else:
            # Create new passport
            game_profile = GamePassportService.create_passport(
                user=request.user,
                game=game_slug,
                in_game_name=ign,
                metadata=metadata,
                actor_user_id=request.user.id,
                request_ip=request.META.get('REMOTE_ADDR')
            )
            created = True
        
        return JsonResponse({
            'success': True,
            'message': f'Game ID {"created" if created else "updated"} successfully',
            'game': game_profile.game,
            'ign': game_profile.in_game_name
        })
    
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating game ID: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred updating game ID'
        }, status=500)
