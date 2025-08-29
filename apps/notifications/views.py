from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Notification
from apps.user_profile.models import UserProfile  # add this

@login_required
def list_view(request):
    # use the correct reverse accessor; create if missing
    p = getattr(request.user, "profile", None)
    if p is None:
        p, _ = UserProfile.objects.get_or_create(
            user=request.user, defaults={"display_name": request.user.username}
        )
    qs = Notification.objects.filter(recipient=p).order_by("-created_at")
    return render(request, "notifications/list.html", {"notifications": qs})

@login_required
def mark_all_read(request):
    p = getattr(request.user, "profile", None)
    if p is None:
        p, _ = UserProfile.objects.get_or_create(
            user=request.user, defaults={"display_name": request.user.username}
        )
    Notification.objects.filter(recipient=p, is_read=False).update(is_read=True)
    return redirect("notifications:list")
