from __future__ import annotations
from typing import Optional

from django.contrib.auth import get_user_model
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

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

    # If profile exists and is private, render minimal card
    is_private = bool(getattr(profile, "is_private", False))
    if is_private:
        return render(request, "users/public_profile.html", {
            "public_user": user,
            "profile": profile,
            "is_private": True,
        })

    # Field-level toggles
    show_email = bool(getattr(profile, "show_email", False))
    show_phone = bool(getattr(profile, "show_phone", False))
    show_socials = getattr(profile, "show_socials", True)

    # Optional fields (best-effort)
    phone = getattr(profile, "phone", None)
    socials = getattr(profile, "socials", None)
    ign = getattr(profile, "ign", None)
    riot_id = getattr(profile, "riot_id", None)
    efootball_id = getattr(profile, "efootball_id", None)
    discord_id = getattr(profile, "discord_id", None)

    return render(request, "users/public_profile.html", {
        "public_user": user,
        "profile": profile,
        "is_private": False,
        "show_email": show_email,
        "show_phone": show_phone,
        "show_socials": show_socials,
        "phone": phone,
        "socials": socials,
        "ign": ign,
        "riot_id": riot_id,
        "efootball_id": efootball_id,
        "discord_id": discord_id,
    })
