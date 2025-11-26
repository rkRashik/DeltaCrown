# apps/user_profile/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import UserProfile
from .forms import UserProfileForm


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
    if username is None:
        # If no username provided, show current user's profile
        user = request.user
    else:
        user = get_object_or_404(User, username=username)
    profile = getattr(user, "userprofile", None) or getattr(user, "profile", None)

    # Check if viewing own profile
    is_own_profile = request.user.is_authenticated and request.user == user

    # Try showing user's upcoming matches widget on their private dashboard/profile page
    upcoming = _get_upcoming_matches_for_user(user, limit=5)
    
    # Get team information
    teams = []
    current_teams = []
    
    try:
        if profile:
            from apps.teams.models import TeamMembership
            
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
                
    except Exception as e:
        print(f"Error loading team data: {e}")
        teams = []
        current_teams = []

    # Get economy information
    wallet_balance = 0
    recent_transactions = []
    
    try:
        if profile:
            from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
            
            # Get or create wallet
            wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
            wallet_balance = wallet.cached_balance
            
            # Get recent transactions
            # NOTE: tournament, registration, match are now IntegerFields, not ForeignKeys
            recent_transactions = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).order_by('-created_at')[:10]
            
    except Exception as e:
        print(f"Error loading economy data: {e}")
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
        print(f"Error loading ecommerce data: {e}")
        recent_orders = []
        total_orders = 0
    
    # Get badges and gamification data
    earned_badges = []
    pinned_badges = []
    total_badges = 0
    badge_stats = {}
    
    try:
        if profile:
            from apps.user_profile.models import UserBadge, Badge
            
            # Get all earned badges
            earned_badges = UserBadge.objects.filter(
                user=user
            ).select_related('badge').order_by('-earned_at')
            
            total_badges = earned_badges.count()
            
            # Get pinned badges
            pinned_badges = profile.get_pinned_badges()
            
            # Calculate badge statistics
            badge_stats = {
                'total': total_badges,
                'common': earned_badges.filter(badge__rarity='common').count(),
                'rare': earned_badges.filter(badge__rarity='rare').count(),
                'epic': earned_badges.filter(badge__rarity='epic').count(),
                'legendary': earned_badges.filter(badge__rarity='legendary').count(),
            }
            
    except Exception as e:
        print(f"Error loading badge data: {e}")
        earned_badges = []
        pinned_badges = []
        total_badges = 0
        badge_stats = {}
    
    # Get privacy settings
    privacy_settings = None
    try:
        if profile:
            from apps.user_profile.models import PrivacySettings
            privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
    except Exception as e:
        print(f"Error loading privacy settings: {e}")
        privacy_settings = None
    
    # Get verification status
    verification_record = None
    try:
        if profile:
            from apps.user_profile.models import VerificationRecord
            verification_record = VerificationRecord.objects.filter(user_profile=profile).first()
    except Exception as e:
        print(f"Error loading verification data: {e}")
        verification_record = None
    
    # Get game profiles from the new pluggable system
    game_profiles = []
    if profile and profile.game_profiles:
        game_profiles = profile.game_profiles
    
    # Calculate tournament stats (placeholder for now)
    tournament_stats = {
        'total_wins': 0,
        'total_tournaments': 0,
        'win_rate': 0
    }
    
    # Social links
    social = []
    if profile and profile.show_socials:
        try:
            if profile.youtube_link:
                social.append({"platform": "YouTube", "handle": "", "url": profile.youtube_link})
            if profile.twitch_link:
                social.append({"platform": "Twitch", "handle": "", "url": profile.twitch_link})
            if profile.discord_id:
                social.append({"platform": "Discord", "handle": profile.discord_id, "url": f"https://discord.com/users/{profile.discord_id}"})
            if profile.facebook:
                social.append({"platform": "Facebook", "handle": "", "url": profile.facebook})
            if profile.instagram:
                social.append({"platform": "Instagram", "handle": "", "url": profile.instagram})
            if profile.twitter:
                social.append({"platform": "Twitter", "handle": "", "url": profile.twitter})
        except Exception as e:
            print(f"Error loading social links: {e}")
            social = []

    return render(
        request,
        "user_profile/profile.html",
        {
            "profile_user": user,
            "profile": profile,
            "is_own_profile": is_own_profile,
            "upcoming_matches": upcoming,
            "teams": teams,
            "current_teams": current_teams,
            "wallet_balance": wallet_balance,
            "recent_transactions": recent_transactions,
            "recent_orders": recent_orders,
            "total_orders": total_orders,
            "earned_badges": earned_badges,
            "pinned_badges": pinned_badges,
            "total_badges": total_badges,
            "badge_stats": badge_stats,
            "privacy_settings": privacy_settings,
            "verification_record": verification_record,
            "game_profiles": game_profiles,
            "tournament_stats": tournament_stats,
            "social": social,
            "match_history": [],
            "tournament_history": [],
        },
    )


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
                profile.save()
        except Exception as e:
            print(f"Error saving profile data: {e}")

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
            print(f"Error saving privacy settings: {e}")

        messages.success(request, 'Your settings have been updated.')
        return redirect('user_profile:settings')

    context = {
        'profile': profile,
        'privacy_settings': privacy_settings,
        'verification_record': verification_record,
    }

    return render(request, 'user_profile/settings.html', context)


