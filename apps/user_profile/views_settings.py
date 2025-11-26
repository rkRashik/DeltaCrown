# apps/user_profile/views_settings.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.apps import apps

from .forms import PrivacySettingsForm

UserProfile = apps.get_model("user_profile", "UserProfile")


def _get_profile_for(user):
    """
    Support both .profile and .userprofile attribute names; create if missing.
    """
    obj = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if obj is None:
        obj, _ = UserProfile.objects.get_or_create(user=user)
    return obj


class MyProfileUpdateView(LoginRequiredMixin, View):
    """
    Render privacy settings on GET (ModelForm).
    On POST, persist booleans by selecting the row via user_id to avoid any pk/instance drift.
    Route: /user/me/edit/  (name: user_profile:edit)
    """

    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("user_profile:edit")

    def get(self, request, *args, **kwargs):
        # Redirect legacy edit URL to the new unified settings page
        return redirect(reverse("user_profile:settings"))

    def post(self, request, *args, **kwargs):
        # Interpret checkbox presence as boolean
        is_private = bool(request.POST.get("is_private"))
        show_email = bool(request.POST.get("show_email"))
        show_phone = bool(request.POST.get("show_phone"))
        show_socials = bool(request.POST.get("show_socials"))

        # Write by user relation to guarantee we hit the correct row
        UserProfile.objects.filter(user_id=request.user.id).update(
            is_private=is_private,
            show_email=show_email,
            show_phone=show_phone,
            show_socials=show_socials,
        )

        messages.success(request, "Your privacy settings have been saved.")
        # After saving privacy fields, send user to the new unified settings page
        return redirect(reverse("user_profile:settings"))
