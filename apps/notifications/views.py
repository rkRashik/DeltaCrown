from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods


def _get_profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


@login_required
def list_view(request):
    Notification = apps.get_model("notifications", "Notification")
    profile = _get_profile(request.user)
    qs = Notification.objects.filter(recipient=profile).order_by("-created_at")
    # Mark unread as read when opening? Keep as-is (read on list open)
    qs.filter(is_read=False).update(is_read=True)
    return render(request, "notifications/list.html", {"notifications": qs})


@login_required
@require_http_methods(["GET", "POST"])
def mark_all_read(request):
    """
    Mark all notifications for the current user as read.
    Accept GET for compatibility with existing templates; prefer POST in forms.
    """
    Notification = apps.get_model("notifications", "Notification")
    profile = _get_profile(request.user)
    Notification.objects.filter(recipient=profile, is_read=False).update(is_read=True)

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("notifications:list")
    return redirect(next_url)


@login_required
@require_http_methods(["GET", "POST"])
def mark_read(request, pk: int):
    """
    Mark a single notification as read.
    """
    Notification = apps.get_model("notifications", "Notification")
    profile = _get_profile(request.user)
    n = get_object_or_404(Notification, pk=pk, recipient=profile)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("notifications:list")
    return redirect(next_url)
