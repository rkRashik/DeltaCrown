from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

User = get_user_model()

import logging
from django.db import DatabaseError

logger = logging.getLogger(__name__)


def _get_profile(user) -> Optional[object]:
    # Try user.profile first (typical OneToOne related_name)
    try:
        prof = getattr(user, "profile", None)
    except DatabaseError:
        # If the profile table/schema is inconsistent (missing columns), avoid raising.
        logger.warning("UserProfile access failed for user %s due to database schema mismatch.", getattr(user, 'username', user))
        return None
    if prof is not None:
        return prof

    # Fallback: query explicit model if needed — guard DB errors gracefully
    try:
        from apps.user_profile.models import UserProfile
        return UserProfile.objects.filter(user=user).first()
    except DatabaseError:
        # If the table schema doesn't match the model (missing column), return None
        return None
    except Exception:
        return None

def public_profile(request: HttpRequest, username: str) -> HttpResponse:
    user = User.objects.filter(username=username).first()
    if not user:
        raise Http404("User not found")

    profile = _get_profile(user)

    # If profile exists and is private, show a minimal card
    is_private = bool(getattr(profile, "is_private", False))
    if is_private:
        return render(request, "user_profile/profile.html", {
            "public_user": user,
            "profile": profile,
            "is_private": True,
        })

    # Render with field-level toggles
    show_email = bool(getattr(profile, "show_email", False))
    show_phone = bool(getattr(profile, "show_phone", False))
    show_socials = getattr(profile, "show_socials", True)

    # Best-effort fields (won't crash if missing)
    phone = getattr(profile, "phone", None)
    socials = getattr(profile, "socials", None)  # dict/json or string
    discord_id = getattr(profile, "discord_id", None)

    # Prefer new `game_profiles` pluggable system for in-game IDs
    ign = None
    riot_id = None
    efootball_id = None
    if profile is not None:
        try:
            gp = None
            if hasattr(profile, 'get_game_profile'):
                gp = profile.get_game_profile('valorant')
            if gp:
                ign = gp.get('ign')
            else:
                # Fallback to legacy field if game_profiles not populated
                riot_id = getattr(profile, 'riot_id', None)

            ef = None
            if hasattr(profile, 'get_game_profile'):
                ef = profile.get_game_profile('efootball')
            if ef:
                efootball_id = ef.get('ign')
            else:
                efootball_id = getattr(profile, 'efootball_id', None)
        except Exception:
            # Be resilient to any DB/schema issues
            ign = None
            riot_id = None
            efootball_id = None

    # Add `profile_user` alias for templates expecting that name
    context = {
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
        "profile_user": user,
    }

    return render(request, "user_profile/profile.html", context)
