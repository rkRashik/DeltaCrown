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
        from apps.tournaments.models import Match
        from apps.teams.models import TeamMembership

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
    return render(request, "user_profile/profile.html", {"profile": user.profile})

@login_required
def my_tournaments_view(request):
    from apps.tournaments.models import Registration
    regs = Registration.objects.filter(user=request.user.profile).select_related("tournament")
    return render(request, "user_profile/my_tournaments.html", {"registrations": regs})


@login_required
def dashboard(request):
    """
    Minimal user dashboard: now includes 'upcoming_matches' (read-only).
    """
    upcoming = _get_upcoming_matches_for_user(request.user, limit=5)
    ctx = {"upcoming_matches": upcoming}
    return render(request, "user_profile/dashboard.html", ctx)