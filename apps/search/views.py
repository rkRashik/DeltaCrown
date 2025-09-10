from __future__ import annotations
from django.shortcuts import render
from django.apps import apps
from django.db.models import Q


def search(request):
    q = (request.GET.get("q") or "").strip()
    ftype = (request.GET.get("type") or "").strip().lower()  # 'tournaments' | 'teams' | ''

    tournaments = []
    teams = []
    if q:
        # Tournaments
        if ftype in ("", "tournaments"):
            try:
                T = apps.get_model("tournaments", "Tournament")
                tqs = T.objects.select_related("settings").filter(Q(name__icontains=q) | Q(slug__icontains=q)).order_by("-id")[:25]
                tournaments = list(tqs)
            except Exception:
                tournaments = []
        # Teams
        if ftype in ("", "teams"):
            try:
                Team = apps.get_model("teams", "Team")
                tqs = Team.objects.select_related("captain__user").filter(Q(name__icontains=q) | Q(tag__icontains=q) | Q(slug__icontains=q)).order_by("name")[:25]
                teams = list(tqs)
            except Exception:
                teams = []

    ctx = {"q": q, "type": ftype, "tournaments": tournaments, "teams": teams}
    return render(request, "search/index.html", ctx)

