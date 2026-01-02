"""
Phase 6A: Follow Request API Endpoints

API endpoints for handling follow requests and private account follow approval workflow.

Endpoints:
- POST /profiles/<username>/follow/ - Follow user (or create follow request if private)
- POST /profiles/<username>/follow/respond/ - Approve/reject follow request  
- GET /me/follow-requests/ - List incoming follow requests
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
import json
import logging

from apps.user_profile.services.follow_service import FollowService
from apps.user_profile.models_main import Follow, FollowRequest

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def follow_user_api(request, username):
    """
    Follow a user (or create follow request if private account).
    
    POST /profiles/<username>/follow/
    
    Response:
        {
            "success": true,
            "action": "followed" | "request_sent",
            "is_following": true | false,
            "has_pending_request": true | false,
            "message": "..."
        }
    
    Errors:
        400: Invalid request
        403: Cannot follow user (permissions)
        404: User not found
    """
    try:
        result = FollowService.follow_user(
            follower_user=request.user,
            followee_username=username,
            request_id=request.META.get('HTTP_X_REQUEST_ID'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        obj, created = result
        
        # Determine if this is a Follow or FollowRequest
        if isinstance(obj, Follow):
            # Public account: immediate follow
            return JsonResponse({
                'success': True,
                'action': 'followed',
                'is_following': True,
                'has_pending_request': False,
                'message': f'You are now following @{username}' if created else f'Already following @{username}'
            })
        else:
            # Private account: follow request created
            return JsonResponse({
                'success': True,
                'action': 'request_sent',
                'is_following': False,
                'has_pending_request': True,
                'message': f'Follow request sent to @{username}' if created else f'Follow request already pending'
            })
    
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error in follow_user_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def respond_to_follow_request_api(request, username):
    """
    Approve or reject a follow request.
    
    POST /profiles/<username>/follow/respond/
    Body:
        {
            "request_id": 123,
            "action": "approve" | "reject"
        }
    
    Response:
        {
            "success": true,
            "action": "approved" | "rejected",
            "is_following": true | false,
            "message": "..."
        }
    
    Errors:
        400: Invalid request
        403: Not authorized
        404: Request not found
    """
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        action = data.get('action')
        
        if not request_id or action not in ['approve', 'reject']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request: must provide request_id and action (approve/reject)'
            }, status=400)
        
        if action == 'approve':
            follow = FollowService.approve_follow_request(
                target_user=request.user,
                request_id=request_id,
                request_id_audit=request.META.get('HTTP_X_REQUEST_ID'),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return JsonResponse({
                'success': True,
                'action': 'approved',
                'is_following': True,
                'message': f'Follow request approved. @{follow.follower.username} is now following you.'
            })
        
        else:  # reject
            follow_request = FollowService.reject_follow_request(
                target_user=request.user,
                request_id=request_id,
                request_id_audit=request.META.get('HTTP_X_REQUEST_ID'),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return JsonResponse({
                'success': True,
                'action': 'rejected',
                'is_following': False,
                'message': f'Follow request from @{follow_request.requester.user.username} rejected.'
            })
    
    except FollowRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Follow request not found'
        }, status=404)
    
    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error in respond_to_follow_request_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_follow_requests_api(request):
    """
    Get incoming follow requests for the authenticated user.
    
    GET /me/follow-requests/
    Query params:
        - status: 'PENDING' | 'APPROVED' | 'REJECTED' (optional, defaults to PENDING)
    
    Response:
        {
            "success": true,
            "requests": [
                {
                    "id": 123,
                    "requester": {
                        "username": "alice",
                        "display_name": "Alice Smith",
                        "avatar_url": "...",
                        "public_id": "DC-26-000001"
                    },
                    "status": "PENDING",
                    "created_at": "2026-01-02T10:30:00Z",
                    "resolved_at": null
                },
                ...
            ],
            "count": 5
        }
    """
    try:
        status_filter = request.GET.get('status', FollowRequest.STATUS_PENDING)
        
        if status_filter and status_filter not in [FollowRequest.STATUS_PENDING, 
                                                     FollowRequest.STATUS_APPROVED, 
                                                     FollowRequest.STATUS_REJECTED]:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status filter. Must be PENDING, APPROVED, or REJECTED.'
            }, status=400)
        
        follow_requests = FollowService.get_incoming_follow_requests(
            user=request.user,
            status=status_filter
        )
        
        requests_data = []
        for fr in follow_requests:
            requester_profile = fr.requester
            requests_data.append({
                'id': fr.id,
                'requester': {
                    'username': requester_profile.user.username,
                    'display_name': requester_profile.display_name,
                    'avatar_url': requester_profile.avatar.url if requester_profile.avatar else None,
                    'public_id': requester_profile.public_id
                },
                'status': fr.status,
                'created_at': fr.created_at.isoformat(),
                'resolved_at': fr.resolved_at.isoformat() if fr.resolved_at else None
            })
        
        return JsonResponse({
            'success': True,
            'requests': requests_data,
            'count': len(requests_data)
        })
    
    except Exception as e:
        logger.error(f"Error in get_follow_requests_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while fetching follow requests'
        }, status=500)
