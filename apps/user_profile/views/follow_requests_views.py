"""
Follow Requests Page View
==========================

Display pending follow requests for the authenticated user.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth import get_user_model

from apps.user_profile.models_main import FollowRequest, UserProfile

User = get_user_model()


@login_required
def follow_requests_page(request, username=None):
    """
    Display follow requests page.
    
    URL: /@username/follow-requests/
    """
    # Get the authenticated user's profile
    user_profile = UserProfile.objects.select_related('user').get(user=request.user)
    
    # Get pending follow requests
    follow_requests = FollowRequest.objects.filter(
        target=user_profile,
        status=FollowRequest.STATUS_PENDING
    ).select_related(
        'requester__user'
    ).order_by('-created_at')
    
    # Enrich with avatar URLs
    enriched_requests = []
    for req in follow_requests:
        # Get avatar URL directly from profile
        if hasattr(req.requester, 'avatar') and req.requester.avatar:
            req.requester.avatar_url = req.requester.avatar.url
        else:
            req.requester.avatar_url = '/static/images/default-avatar.png'
        req.requester.is_verified = req.requester.kyc_status == 'verified'
        enriched_requests.append(req)
    
    context = {
        'view_user': request.user,
        'follow_requests': enriched_requests,
        'pending_count': follow_requests.count()
    }
    
    return render(request, 'user_profile/follow_requests.html', context)
