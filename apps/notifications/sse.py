"""
SSE (Server-Sent Events) endpoint for live notifications.
Streams notification counts to keep UI updated without refresh.
"""
import json
import time
import logging
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from apps.notifications.models import Notification
from apps.user_profile.models_main import FollowRequest

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def notification_stream(request):
    """
    SSE endpoint that streams notification counts to client.
    
    GET /api/notifications/stream/
    
    Streams JSON events every 5 seconds:
    {
        "unread_notifications": 5,
        "pending_follow_requests": 2
    }
    """
    def event_stream():
        """Generator that yields SSE events"""
        try:
            while True:
                # Get counts
                unread_count = Notification.objects.filter(
                    recipient=request.user,
                    is_read=False
                ).count()
                
                # Get pending follow requests for this user
                pending_requests_count = FollowRequest.objects.filter(
                    target__user=request.user,
                    status=FollowRequest.STATUS_PENDING
                ).count()
                
                # Format as SSE event
                data = json.dumps({
                    'unread_notifications': unread_count,
                    'pending_follow_requests': pending_requests_count
                })
                
                yield f"data: {data}\n\n"
                
                # Wait 5 seconds before next update
                time.sleep(5)
                
        except GeneratorExit:
            # Client disconnected
            logger.debug(f"SSE stream closed for user {request.user.id}")
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    
    return response
