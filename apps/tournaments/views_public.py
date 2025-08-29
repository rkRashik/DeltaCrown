from django.shortcuts import render, get_object_or_404
from .models import Tournament

def tournament_list(request):
    qs = Tournament.objects.all().order_by("-created_at")
    return render(request, "tournaments/list.html", {"tournaments": qs})

def tournament_detail(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/detail.html", {"t": t})
