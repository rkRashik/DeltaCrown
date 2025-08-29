from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Tournament

def tournament_list(request):
    qs = Tournament.objects.all().order_by("-created_at")
    paginator = Paginator(qs, 9)  # 9 per page
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "tournaments/list.html", {
        "tournaments": page_obj.object_list,
        "page_obj": page_obj,
    })

def tournament_detail(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/detail.html", {"t": t})
