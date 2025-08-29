from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from .models import UserProfile
from django import forms
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from apps.tournaments.models import Registration


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "region", "discord_id", "riot_id", "efootball_id"]  # add avatar later if you want

class MyProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = "user_profile/profile_edit.html"
    success_url = reverse_lazy("user_profile:edit")

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, "user_profile/profile.html", {"profile": user.profile})

@login_required
def my_tournaments_view(request):
    regs = Registration.objects.filter(user=request.user.profile)
    return render(request, "user_profile/my_tournaments.html", {"registrations": regs})