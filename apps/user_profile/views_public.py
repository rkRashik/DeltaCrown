from __future__ import annotations
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Q, Count
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

    # Aggregate basic player stats from tournaments.Match if available
    stats = None
    match_history = []
    try:
        from apps.tournaments.models.match import Match
        if profile:
            qs = Match.objects.filter(
                Q(user_a=profile) | Q(user_b=profile)
            ).order_by("-created_at")
            total = qs.count()
            wins = qs.filter(winner_user=profile).count()
            win_rate = round((wins / total) * 100) if total else 0
            stats = {
                "matches": total,
                "win_rate": win_rate,
                "rank": None,
            }

            # shape minimal history for the template
            for m in qs[:6]:
                match_history.append({
                    "tournament_name": getattr(m.tournament, "name", "Tournament"),
                    "result": ("Win" if getattr(m, "winner_user_id", None) == profile.id else ("Loss" if m.winner_user_id else "-")),
                    "game": getattr(m.tournament, "game", None) or "—",
                    "played_at": getattr(m, "created_at", None),
                    "url": f"/tournaments/{getattr(m.tournament, 'id', '')}/matches/{m.id}/" if getattr(m, 'id', None) else "#",
                    "summary": "",
                })
    except Exception:
        pass

    # Social links from profile fields → list of dicts expected by template
    social = []
    if profile and show_socials:
        try:
            if getattr(profile, "youtube_link", ""):
                social.append({"platform": "YouTube", "handle": "", "url": profile.youtube_link})
            if getattr(profile, "twitch_link", ""):
                social.append({"platform": "Twitch", "handle": "", "url": profile.twitch_link})
            if getattr(profile, "discord_id", ""):
                discord_handle = profile.discord_id
                social.append({"platform": "Discord", "handle": discord_handle, "url": f"https://discord.com/users/{discord_handle}"})
        except Exception:
            # Be resilient to any unexpected data
            social = []

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
        # added pipeline data
        "stats": stats,
        "match_history": match_history,
        "activity": [],
        "teams": [],
        "highlights": [],
        "achievements": [],
        "social": social,
    }

    return render(request, "users/public_profile.html", context)
