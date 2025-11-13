"""
Admin Read-Only Webhook Inspection API.

Provides Django Admin-authenticated endpoints for inspecting:
- Recent webhook deliveries (last 24h)
- Specific webhook by ID
- Circuit breaker status
- Retry chains
- Failure statistics

Read-only (GET only). No mutations. Uses existing webhook models.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta
from apps.notifications.models import WebhookDelivery


@staff_member_required
def webhook_deliveries_list(request):
    """
    GET /admin/api/webhooks/deliveries
    
    List recent webhook deliveries with filtering and pagination.
    
    Query Parameters:
    - event: Filter by event type (e.g., "payment_verified")
    - status: Filter by status ("success", "failed", "retrying")
    - endpoint: Filter by endpoint URL (partial match)
    - since: ISO timestamp (default: 24 hours ago)
    - page: Page number (default: 1)
    - page_size: Results per page (default: 50, max: 200)
    
    Returns:
    {
      "count": 150,
      "page": 1,
      "page_size": 50,
      "total_pages": 3,
      "results": [
        {
          "id": "uuid",
          "event": "payment_verified",
          "endpoint": "https://api.example.com/webhooks",
          "status": "success",
          "status_code": 200,
          "created_at": "2025-11-13T14:42:15Z",
          "delivered_at": "2025-11-13T14:42:15.145Z",
          "latency_ms": 145,
          "retry_count": 0,
          "circuit_breaker_state": "closed"
        },
        ...
      ]
    }
    """
    # Parse filters
    event = request.GET.get("event")
    status = request.GET.get("status")
    endpoint = request.GET.get("endpoint")
    cb_state = request.GET.get("cb_state")  # CLOSED, HALF_OPEN, OPEN
    since = request.GET.get("since")
    
    # Default: last 24 hours
    if not since:
        since = timezone.now() - timedelta(hours=24)
    else:
        since = timezone.datetime.fromisoformat(since.replace("Z", "+00:00"))
    
    # Build query
    queryset = WebhookDelivery.objects.filter(created_at__gte=since)
    
    if event:
        queryset = queryset.filter(event=event)
    
    if status:
        status_map = {
            "success": Q(status_code__gte=200, status_code__lt=300),
            "failed": Q(status_code__gte=400) | Q(status_code__isnull=True),
            "retrying": Q(retry_count__gt=0, status_code__gte=400),
        }
        if status in status_map:
            queryset = queryset.filter(status_map[status])
    
    if endpoint:
        queryset = queryset.filter(endpoint__icontains=endpoint)
    
    if cb_state:
        state_map = {
            "CLOSED": "closed",
            "HALF_OPEN": "half_open",
            "OPEN": "open",
        }
        if cb_state.upper() in state_map:
            queryset = queryset.filter(circuit_breaker_state=state_map[cb_state.upper()])
    
    # Order by most recent first
    queryset = queryset.order_by("-created_at")
    
    # Pagination
    page_size = min(int(request.GET.get("page_size", 50)), 200)
    page = int(request.GET.get("page", 1))
    
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    # Serialize results
    results = []
    for delivery in page_obj:
        results.append({
            "id": str(delivery.id),
            "event": delivery.event,
            "endpoint": delivery.endpoint,
            "status": "success" if 200 <= delivery.status_code < 300 else "failed",
            "status_code": delivery.status_code,
            "created_at": delivery.created_at.isoformat(),
            "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            "latency_ms": delivery.latency_ms,
            "retry_count": delivery.retry_count,
            "circuit_breaker_state": delivery.circuit_breaker_state or "closed",
        })
    
    return JsonResponse({
        "count": paginator.count,
        "page": page,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": results,
    })


@staff_member_required
def webhook_delivery_detail(request, webhook_id):
    """
    GET /admin/api/webhooks/deliveries/<webhook_id>
    
    Get detailed information about a specific webhook delivery.
    
    Returns:
    {
      "id": "uuid",
      "event": "payment_verified",
      "endpoint": "https://api.example.com/webhooks",
      "status": "success",
      "status_code": 200,
      "created_at": "2025-11-13T14:42:15Z",
      "delivered_at": "2025-11-13T14:42:15.145Z",
      "latency_ms": 145,
      "retry_count": 0,
      "circuit_breaker_state": "closed",
      "payload": {
        "event": "payment_verified",
        "data": { ... }
      },
      "request_headers": {
        "Content-Type": "application/json",
        "X-Webhook-Signature": "***",
        "X-Webhook-Timestamp": "1700000000123"
      },
      "response_body": "OK",
      "error_message": null,
      "retries": [
        {
          "attempt": 1,
          "timestamp": "2025-11-13T14:42:00.142Z",
          "status_code": 503,
          "delay_seconds": 0
        },
        {
          "attempt": 2,
          "timestamp": "2025-11-13T14:42:02.280Z",
          "status_code": 503,
          "delay_seconds": 2
        },
        {
          "attempt": 3,
          "timestamp": "2025-11-13T14:42:06.425Z",
          "status_code": 200,
          "delay_seconds": 4
        }
      ]
    }
    """
    try:
        delivery = WebhookDelivery.objects.get(id=webhook_id)
    except WebhookDelivery.DoesNotExist:
        return JsonResponse({"error": "Webhook delivery not found"}, status=404)
    
    # Redact sensitive headers
    request_headers = delivery.request_headers or {}
    sensitive_headers = ["X-Webhook-Signature", "Authorization", "X-API-Key"]
    for header in sensitive_headers:
        if header in request_headers:
            request_headers[header] = "***REDACTED***"
    
    # Get retry history
    retries = []
    if hasattr(delivery, "retries"):
        for retry in delivery.retries.order_by("attempt"):
            retries.append({
                "attempt": retry.attempt,
                "timestamp": retry.created_at.isoformat(),
                "status_code": retry.status_code,
                "delay_seconds": retry.delay_seconds,
            })
    
    return JsonResponse({
        "id": str(delivery.id),
        "event": delivery.event,
        "endpoint": delivery.endpoint,
        "status": "success" if 200 <= delivery.status_code < 300 else "failed",
        "status_code": delivery.status_code,
        "created_at": delivery.created_at.isoformat(),
        "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
        "latency_ms": delivery.latency_ms,
        "retry_count": delivery.retry_count,
        "circuit_breaker_state": delivery.circuit_breaker_state or "closed",
        "payload": delivery.payload,
        "request_headers": request_headers,
        "response_body": delivery.response_body[:500] if delivery.response_body else None,  # Truncate large responses
        "error_message": delivery.error_message,
        "retries": retries,
    })


@staff_member_required
def webhook_statistics(request):
    """
    GET /admin/api/webhooks/statistics
    
    Get aggregated webhook statistics for last 24 hours.
    
    Query Parameters:
    - since: ISO timestamp (default: 24 hours ago)
    - event: Filter by event type (optional)
    
    Returns:
    {
      "time_range": {
        "start": "2025-11-12T14:30:00Z",
        "end": "2025-11-13T14:30:00Z"
      },
      "total_deliveries": 1250,
      "success_count": 1180,
      "failure_count": 70,
      "success_rate": 94.4,
      "latency": {
        "p50_ms": 145,
        "p95_ms": 412,
        "p99_ms": 1523,
        "avg_ms": 178,
        "min_ms": 98,
        "max_ms": 2104
      },
      "by_event": [
        {
          "event": "payment_verified",
          "count": 700,
          "success_count": 672,
          "success_rate": 96.0
        },
        {
          "event": "match_started",
          "count": 350,
          "success_count": 330,
          "success_rate": 94.3
        },
        ...
      ],
      "by_status_code": [
        {"code": 200, "count": 1150},
        {"code": 202, "count": 30},
        {"code": 503, "count": 60},
        {"code": 400, "count": 10}
      ],
      "circuit_breaker": {
        "opens_last_24h": 0,
        "currently_open_endpoints": []
      }
    }
    """
    # Parse filters
    since_param = request.GET.get("since")
    event_filter = request.GET.get("event")
    
    # Default: last 24 hours
    if not since_param:
        start = timezone.now() - timedelta(hours=24)
    else:
        start = timezone.datetime.fromisoformat(since_param.replace("Z", "+00:00"))
    
    end = timezone.now()
    
    # Build base query
    queryset = WebhookDelivery.objects.filter(created_at__gte=start, created_at__lte=end)
    
    if event_filter:
        queryset = queryset.filter(event=event_filter)
    
    # Total counts
    total_deliveries = queryset.count()
    success_count = queryset.filter(status_code__gte=200, status_code__lt=300).count()
    failure_count = queryset.filter(Q(status_code__gte=400) | Q(status_code__isnull=True)).count()
    success_rate = (success_count / total_deliveries * 100) if total_deliveries > 0 else 0
    
    # Latency stats (successful deliveries only)
    latency_queryset = queryset.filter(status_code__gte=200, status_code__lt=300, latency_ms__isnull=False)
    latency_stats = latency_queryset.aggregate(
        avg_ms=Avg("latency_ms"),
        min_ms=Min("latency_ms"),
        max_ms=Max("latency_ms"),
    )
    
    # Calculate percentiles (approximate using database)
    latency_values = list(latency_queryset.values_list("latency_ms", flat=True).order_by("latency_ms"))
    p50_ms = latency_values[int(len(latency_values) * 0.50)] if latency_values else None
    p95_ms = latency_values[int(len(latency_values) * 0.95)] if latency_values else None
    p99_ms = latency_values[int(len(latency_values) * 0.99)] if latency_values else None
    
    # By event
    by_event = []
    event_stats = queryset.values("event").annotate(
        count=Count("id"),
        success_count=Count("id", filter=Q(status_code__gte=200, status_code__lt=300))
    )
    for stat in event_stats:
        by_event.append({
            "event": stat["event"],
            "count": stat["count"],
            "success_count": stat["success_count"],
            "success_rate": (stat["success_count"] / stat["count"] * 100) if stat["count"] > 0 else 0,
        })
    
    # By status code
    by_status_code = []
    status_stats = queryset.values("status_code").annotate(count=Count("id")).order_by("-count")
    for stat in status_stats:
        by_status_code.append({
            "code": stat["status_code"],
            "count": stat["count"],
        })
    
    # Circuit breaker stats
    cb_opens_24h = queryset.filter(circuit_breaker_state="open").values("endpoint").distinct().count()
    currently_open = list(queryset.filter(
        circuit_breaker_state="open",
        created_at__gte=timezone.now() - timedelta(minutes=5)
    ).values_list("endpoint", flat=True).distinct())
    
    return JsonResponse({
        "time_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "total_deliveries": total_deliveries,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": round(success_rate, 1),
        "latency": {
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "p99_ms": p99_ms,
            "avg_ms": round(latency_stats["avg_ms"], 1) if latency_stats["avg_ms"] else None,
            "min_ms": latency_stats["min_ms"],
            "max_ms": latency_stats["max_ms"],
        },
        "by_event": by_event,
        "by_status_code": by_status_code,
        "circuit_breaker": {
            "opens_last_24h": cb_opens_24h,
            "currently_open_endpoints": currently_open,
        },
    })


@staff_member_required
def circuit_breaker_status(request):
    """
    GET /admin/api/webhooks/circuit-breaker
    
    Get current circuit breaker status for all endpoints.
    
    Returns:
    {
      "endpoints": [
        {
          "endpoint": "https://api.example.com/webhooks",
          "state": "closed",
          "failure_count": 0,
          "last_failure": null,
          "last_success": "2025-11-13T14:42:15Z",
          "opens_last_24h": 0,
          "half_open_probe_due": null
        },
        {
          "endpoint": "https://api.receiver2.com/hooks",
          "state": "open",
          "failure_count": 5,
          "last_failure": "2025-11-13T14:38:00Z",
          "last_success": "2025-11-13T14:30:00Z",
          "opens_last_24h": 2,
          "half_open_probe_due": "2025-11-13T14:39:00Z"
        }
      ]
    }
    """
    # Get unique endpoints
    endpoints = WebhookDelivery.objects.values("endpoint").distinct()
    
    results = []
    for endpoint_dict in endpoints:
        endpoint = endpoint_dict["endpoint"]
        
        # Get most recent delivery
        recent = WebhookDelivery.objects.filter(endpoint=endpoint).order_by("-created_at").first()
        
        # Count failures in last 5 minutes (failure threshold window)
        failure_count = WebhookDelivery.objects.filter(
            endpoint=endpoint,
            created_at__gte=timezone.now() - timedelta(minutes=5),
            status_code__gte=400
        ).count()
        
        # Last failure
        last_failure = WebhookDelivery.objects.filter(
            endpoint=endpoint,
            status_code__gte=400
        ).order_by("-created_at").first()
        
        # Last success
        last_success = WebhookDelivery.objects.filter(
            endpoint=endpoint,
            status_code__gte=200,
            status_code__lt=300
        ).order_by("-created_at").first()
        
        # Opens in last 24h
        opens_24h = WebhookDelivery.objects.filter(
            endpoint=endpoint,
            circuit_breaker_state="open",
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Determine state
        state = recent.circuit_breaker_state if recent else "closed"
        
        # Half-open probe due time (30 seconds after last failure if open)
        half_open_probe_due = None
        if state == "open" and last_failure:
            half_open_probe_due = (last_failure.created_at + timedelta(seconds=30)).isoformat()
        
        results.append({
            "endpoint": endpoint,
            "state": state,
            "failure_count": failure_count,
            "last_failure": last_failure.created_at.isoformat() if last_failure else None,
            "last_success": last_success.created_at.isoformat() if last_success else None,
            "opens_last_24h": opens_24h,
            "half_open_probe_due": half_open_probe_due,
        })
    
    return JsonResponse({"endpoints": results})
