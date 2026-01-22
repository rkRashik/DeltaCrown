from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.urls import reverse
from django.apps import apps
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from .decorators import require_auth_json

Notification = apps.get_model("notifications", "Notification")
UserProfile = apps.get_model("user_profile", "UserProfile")


def _user(user):
    # Recipient FK now targets the custom accounts.User
    return user


@login_required
def list_view(request):
    u = _user(request.user)
    qs = Notification.objects.filter(recipient=u).order_by("-created_at")
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "notifications/list_modern.html", {"page": page})


@require_auth_json
def mark_all_read(request):
    """
    Mark all notifications as read for the current user.
    Phase 4 Step 1.1: Returns JSON instead of redirect for API usage.
    """
    u = _user(request.user)
    if request.method == "POST":
        updated_count = Notification.objects.filter(recipient=u, is_read=False).update(is_read=True)
        return JsonResponse({
            "success": True,
            "message": "All notifications marked as read.",
            "updated_count": updated_count
        })
    
    # GET request (legacy behavior)
    return JsonResponse({
        "success": False,
        "error": "method_not_allowed",
        "message": "Use POST to mark notifications as read"
    }, status=405)


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


@require_auth_json
def nav_preview(request):
    """
    API endpoint for navigation bell dropdown.
    Returns recent notifications + follow request count.
    
    GET /notifications/api/nav-preview/
    Returns JSON:
    {
        "success": true,
        "unread_count": int,
        "pending_follow_requests": int,
        "items": [
            {
                "id": int,
                "type": str,
                "title": str,
                "message": str,
                "url": str,
                "created_at": ISO timestamp,
                "is_read": bool,
                "action_label": str (optional),
                "action_url": str (optional)
            }
        ]
    }
    """
    u = _user(request.user)
    
    try:
        # Get recent notifications (limit 10 for dropdown)
        notifications = Notification.objects.filter(recipient=u).order_by("-created_at")[:10]
        
        # Count unread
        unread_count = Notification.objects.filter(recipient=u, is_read=False).count()
        
        # Count pending follow requests
        pending_follow_requests = 0
        try:
            FollowRequest = apps.get_model("user_profile", "FollowRequest")
            user_profile = UserProfile.objects.filter(user=u).first()
            if user_profile:
                pending_follow_requests = FollowRequest.objects.filter(
                    target=user_profile,
                    status='PENDING'
                ).count()
        except Exception:
            pass
        
        # Serialize notifications
        items = []
        for n in notifications:
            item = {
                "id": n.id,
                "type": n.type,
                "event": n.event,
                "title": n.title,
                "message": getattr(n, 'message', '') or n.body,
                "url": n.url,
                "created_at": n.created_at.isoformat(),
                "is_read": n.is_read,
                "action_label": getattr(n, 'action_label', '') or "",
                "action_url": getattr(n, 'action_url', '') or ""
            }
            # Include follow_request_id for follow_request notifications
            if n.type == 'follow_request' and hasattr(n, 'action_object_id') and n.action_object_id:
                item["follow_request_id"] = n.action_object_id
            items.append(item)
        
        return JsonResponse({
            "success": True,
            "unread_count": unread_count,
            "pending_follow_requests": pending_follow_requests,
            "items": items
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@require_POST
@login_required
def delete_notification(request, pk):
    """
    Delete a single notification.
    POST /notifications/<id>/delete/
    Returns JSON for AJAX calls or redirects for form submissions.
    """
    u = _user(request.user)
    n = get_object_or_404(Notification, id=pk, recipient=u)
    n.delete()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": "Notification deleted"
        })
    
    messages.success(request, "Notification deleted.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:list"))


@require_POST
@login_required
def clear_all_notifications(request):
    """
    Delete all notifications for the current user.
    POST /notifications/clear-all/
    Returns JSON for AJAX calls.
    """
    u = _user(request.user)
    deleted_count = Notification.objects.filter(recipient=u).delete()[0]
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": f"Deleted {deleted_count} notifications",
            "deleted_count": deleted_count
        })
    
    messages.success(request, f"Deleted {deleted_count} notifications.")
    return redirect(reverse("notifications:list"))


@require_POST
@require_auth_json
def accept_follow_request_inline(request, request_id):
    """
    Accept a follow request directly from notification.
    POST /notifications/api/follow-request/<id>/accept/
    """
    try:
        FollowRequest = apps.get_model("user_profile", "FollowRequest")
        Follow = apps.get_model("user_profile", "Follow")
        
        user_profile = UserProfile.objects.filter(user=_user(request.user)).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "Profile not found"}, status=404)
        
        follow_request = get_object_or_404(FollowRequest, id=request_id, target=user_profile)
        
        if follow_request.status != 'PENDING':
            return JsonResponse({"success": False, "error": "Request already processed"}, status=400)
        
        # Accept the request
        follow_request.status = 'APPROVED'
        follow_request.save()
        
        # Create follow relationship
        Follow.objects.get_or_create(
            follower=follow_request.requester.user,
            following=user_profile.user
        )
        
        return JsonResponse({
            "success": True,
            "message": "Follow request accepted"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@require_POST
@require_auth_json
def reject_follow_request_inline(request, request_id):
    """
    Reject a follow request directly from notification.
    POST /notifications/api/follow-request/<id>/reject/
    """
    try:
        FollowRequest = apps.get_model("user_profile", "FollowRequest")
        
        user_profile = UserProfile.objects.filter(user=_user(request.user)).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "Profile not found"}, status=404)
        
        follow_request = get_object_or_404(FollowRequest, id=request_id, target=user_profile)
        
        if follow_request.status != 'PENDING':
            return JsonResponse({"success": False, "error": "Request already processed"}, status=400)
        
        # Reject the request
        follow_request.status = 'REJECTED'
        follow_request.save()
        
        return JsonResponse({
            "success": True,
            "message": "Follow request rejected"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
