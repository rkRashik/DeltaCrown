from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.urls import reverse
from django.apps import apps

Notification = apps.get_model("notifications", "Notification")
UserProfile = apps.get_model("user_profile", "UserProfile")

def _profile(user):
    p = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if p:
        return p
    p, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": getattr(user, "username", "Player")}
    )
    return p

@login_required
def list_view(request):
    p = _profile(request.user)
    qs = Notification.objects.filter(recipient=p).order_by("-created_at")

    paginator = Paginator(qs, 15)  # 15 per page
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "notifications/list.html",
        {"notifications": page_obj.object_list, "page_obj": page_obj},
    )

@login_required
def mark_all_read(request):
    p = _profile(request.user)
    Notification.objects.filter(recipient=p, is_read=False).update(is_read=True)
    return redirect("notifications:list")

@login_required
def mark_read(request, pk):
    p = _profile(request.user)
    n = get_object_or_404(Notification, id=pk, recipient=p)
    if request.method == "POST" and not getattr(n, "is_read", False):
        n.is_read = True
        n.save(update_fields=["is_read"])
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("notifications:list")
    return redirect(next_url)
