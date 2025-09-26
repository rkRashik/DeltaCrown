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
    """
    try:
        from django.apps import apps
        Match = apps.get_model("tournaments", "Match")
        TeamMembership = apps.get_model("teams", "TeamMembership")

        # Get profile safely
        p = getattr(user, "userprofile", None) or getattr(user, "profile", None)
        if not p:
            return []

        team_ids = list(
            TeamMembership.objects.filter(profile=p, status="ACTIVE").values_list("team_id", flat=True)
        )

        qs = (
            Match.objects.filter(state__in=["PENDING", "SCHEDULED"])
            .filter(
                Q(user_a=p) | Q(user_b=p) | Q(team_a_id__in=team_ids) | Q(team_b_id__in=team_ids)
            )
            .select_related("tournament", "user_a", "user_b", "team_a", "team_b")
            .order_by("round_no", "id")[:limit]
        )
        return list(qs)
    except Exception:
        # If schema/fields differ, fail silently and show an empty state.
        return []


# ProfileForm moved to forms.py as UserProfileForm
        help_texts = {
            "is_private": "Hide entire profile from public.",
            "show_email": "Allow showing my email on public profile.",
            "show_phone": "Allow showing my phone on public profile.",
            "show_socials": "Allow showing my social links/IDs on public profile.",
        }



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


User = get_user_model()


@login_required  
def profile_view(request, username=None):
    if username is None:
        # If no username provided, show current user's profile
        user = request.user
    else:
        user = get_object_or_404(User, username=username)
    profile = getattr(user, "userprofile", None) or getattr(user, "profile", None)

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
            recent_transactions = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).select_related('tournament', 'registration', 'match').order_by('-created_at')[:10]
            
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

    return render(
        request,
        "user_profile/profile_modern.html",
        {
            "profile_user": user,
            "profile": profile,
            "upcoming_matches": upcoming,
            "teams": teams,
            "current_teams": current_teams,
            "wallet_balance": wallet_balance,
            "recent_transactions": recent_transactions,
            "recent_orders": recent_orders,
            "total_orders": total_orders,
        },
    )


@login_required
def my_tournaments_view(request):
    """
    Shows tournaments the current user is registered in (either solo or via teams).
    """
    try:
        from django.apps import apps
        Registration = apps.get_model("tournaments", "Registration")
        TeamMembership = apps.get_model("teams", "TeamMembership")

        profile = getattr(request.user, "userprofile", None) or getattr(request.user, "profile", None)
        if not profile:
            return render(request, "user_profile/my_tournaments.html", {"registrations": []})

        team_ids = list(
            TeamMembership.objects.filter(profile=profile, status="ACTIVE").values_list("team_id", flat=True)
        )

        regs = (
            Registration.objects.filter(Q(user=profile) | Q(team_id__in=team_ids))
            .select_related("tournament")
            .order_by("-created_at")
        )
    except Exception:
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
