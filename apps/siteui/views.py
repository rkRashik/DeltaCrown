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
