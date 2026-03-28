"""
SSE (Server-Sent Events) endpoint for live notifications.
Streams notification counts to keep UI updated without refresh.
"""
import json
import os
import time
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from apps.notifications.models import Notification
from apps.user_profile.models_main import FollowRequest
from apps.notifications.selectors import get_preview_payload

logger = logging.getLogger(__name__)


def _open_optional_sse_pubsub(user_id: int):
    """Open optional Redis pubsub channel for SSE wakeups; return (client, pubsub, channel)."""
    if not getattr(settings, "NOTIFICATIONS_SSE_USE_REDIS", False):
        return None, None, None

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None, None, None

    try:
        import redis

        client = redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        channel = f"notifications:sse:user:{user_id}"
        pubsub.subscribe(channel)
        return client, pubsub, channel
    except Exception:
        logger.warning(
            "notification_sse_redis_unavailable user_id=%s",
            user_id,
            exc_info=True,
        )
        return None, None, None


@login_required
@require_http_methods(["GET"])
def notification_stream(request):
    """
    SSE endpoint that streams notification counts to client.

    Primary route: GET /notifications/stream/
    Backward-compatible alias: GET /api/notifications/stream/
    
    Streams JSON events every 5 seconds:
    {
        "unread_notifications": 5,
        "pending_follow_requests": 2
    }
    """
    if not getattr(settings, "NOTIFICATIONS_SSE_ENABLED", False):
        # 204 is a terminal response for EventSource clients (no reconnect loop).
        return HttpResponse(status=204)

    user_id = request.user.id
    logger.info("notification_sse_open user_id=%s", user_id)

    def event_stream():
        """Generator that yields SSE events"""
        previous_unread_count = None
        redis_client, pubsub, channel_name = _open_optional_sse_pubsub(user_id)
        if channel_name:
            logger.info(
                "notification_sse_subscribed user_id=%s channel=%s",
                user_id,
                channel_name,
            )

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
                    'pending_follow_requests': pending_requests_count,
                    'new_items': []
                })

                if previous_unread_count is None:
                    previous_unread_count = unread_count
                elif unread_count > previous_unread_count:
                    delta = unread_count - previous_unread_count
                    preview = get_preview_payload(request.user, limit=max(1, min(delta, 5)))
                    data = json.dumps({
                        'unread_notifications': unread_count,
                        'pending_follow_requests': pending_requests_count,
                        'new_items': preview,
                    })
                    previous_unread_count = unread_count
                elif unread_count < previous_unread_count:
                    previous_unread_count = unread_count
                
                yield f"data: {data}\n\n"
                
                # Wait before next update. If Redis pubsub is available,
                # block on it so we can wake up early and minimize polling.
                if pubsub is not None:
                    try:
                        pubsub.get_message(timeout=5.0)
                    except Exception:
                        logger.warning(
                            "notification_sse_pubsub_wait_failed user_id=%s",
                            user_id,
                            exc_info=True,
                        )
                        time.sleep(5)
                else:
                    time.sleep(5)
                
        except GeneratorExit:
            logger.info("notification_sse_client_disconnected user_id=%s", user_id)
        except Exception:
            logger.exception("notification_sse_stream_error user_id=%s", user_id)
        finally:
            # Release external resources immediately on disconnect.
            if pubsub is not None:
                try:
                    pubsub.close()
                except Exception:
                    logger.warning("notification_sse_pubsub_close_failed user_id=%s", user_id, exc_info=True)
            if redis_client is not None:
                try:
                    redis_client.close()
                except Exception:
                    logger.warning("notification_sse_redis_close_failed user_id=%s", user_id, exc_info=True)
            close_old_connections()
            logger.info("notification_sse_closed user_id=%s", user_id)
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    
    return response
