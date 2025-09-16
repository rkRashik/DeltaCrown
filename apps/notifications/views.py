from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.urls import reverse
from django.apps import apps
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

Notification = apps.get_model("notifications", "Notification")


def _user(user):
    # Return the auth user (Notification.recipient targets AUTH_USER_MODEL)
    return user


@login_required
def list_view(request):
    u = _user(request.user)
    qs = Notification.objects.filter(recipient=u).order_by("-created_at")
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"page": page})


@login_required
def mark_all_read(request):
    u = _user(request.user)
    if request.method == "POST":
        Notification.objects.filter(recipient=u, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:list"))


@login_required
def mark_read(request, pk):
    u = _user(request.user)
    n = get_object_or_404(Notification, id=pk, recipient=u)
    if request.method == "POST" and not getattr(n, "is_read", False):
        n.is_read = True
        n.save(update_fields=["is_read"])
        messages.success(request, "Notification marked as read.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("notifications:list")
    return redirect(next_url)


@login_required
@cache_page(30)
def unread_count(request):
    u = _user(request.user)
    count = 0
    try:
        count = Notification.objects.filter(recipient=u, is_read=False).count()
    except Exception:
        count = 0
    return JsonResponse({"count": count})
