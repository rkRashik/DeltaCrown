from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import UserProfile


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
            TeamMembership.objects.filter(user=p).values_list("team_id", flat=True)
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "region", "avatar", "bio", "discord_id", "riot_id", "efootball_id"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.Select(attrs={"class": "form-select"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Short bio"}),
            "discord_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "yourname#1234"}),
            "riot_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "Name#TAG"}),
            "efootball_id": forms.TextInput(attrs={"class": "form-control"}),
        }

class MyProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = "user_profile/profile_edit.html"
    success_url = reverse_lazy("user_profile:edit")  # stay on the edit page

    def get_object(self, queryset=None):
        # Always edit your own profile
        return self.request.user.profile

User = get_user_model()

def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile = getattr(user, "userprofile", None) or getattr(user, "profile", None)

    # Gather team memberships (active only) for display
    try:
        from apps.teams.models import TeamMembership
        memberships = list(
            TeamMembership.objects.select_related("team")
            .filter(profile=profile, status="ACTIVE")
            .order_by("role", "joined_at")
        )
    except Exception:
        memberships = []

    # Gather recent tournaments from registrations (solo + team)
    try:
        from apps.tournaments.models import Registration
        team_ids = [m.team_id for m in memberships]
        regs = (
            Registration.objects.select_related("tournament")
            .filter(
                Q(user=profile) | Q(team_id__in=team_ids)
            )
            .order_by("-created_at")[:8]
        )
        registrations = list(regs)
    except Exception:
        registrations = []

    ctx = {
        "profile": profile,
        "memberships": memberships,
        "registrations": registrations,
    }
    return render(request, "user_profile/profile.html", ctx)

@login_required
def my_tournaments_view(request):
    """
    (Existing) My tournaments page – unchanged.
    """
    try:
        from django.apps import apps
        Registration = apps.get_model("tournaments", "Registration")
        TeamMembership = apps.get_model("teams", "TeamMembership")

        profile = request.user.profile
        team_ids = list(TeamMembership.objects.filter(user=profile).values_list("team_id", flat=True))

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
