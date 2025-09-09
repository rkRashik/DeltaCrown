from django.shortcuts import render

def home(request):
    """
    Minimal home: uses SITE from context processor; featured=None (safe fallback).
    """
    ctx = {
        "featured": None,  # contracts require this key to exist
        "signals": [],     # optional ticker
    }
    return render(request, "home.html", ctx)

def ui_showcase(request):
    game_opts = [
        ("valorant", "Valorant", True),
        ("efootball", "eFootball", False),
        ("pubg", "PUBG Mobile", False),
    ]
    radio_opts = [
        ("mode-solo", "solo", "Solo", True),
        ("mode-duo", "duo", "Duo", False),
        ("mode-squad", "squad", "Squad", False),
    ]
    return render(request, "ui_showcase.html", {"game_opts": game_opts, "radio_opts": radio_opts})
