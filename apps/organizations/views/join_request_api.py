"""POST /organizations/api/join-request/<id>/withdraw/ — withdraw a join request."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def join_request_withdraw(request, jr_id):
    try:
        from apps.organizations.models.join_request import TeamJoinRequest
        jr = TeamJoinRequest.objects.filter(id=jr_id, user=request.user).first()
        if not jr:
            return JsonResponse({"ok": False, "error": "Not found"}, status=404)
        if jr.status != "PENDING":
            return JsonResponse({"ok": False, "error": "Cannot withdraw a non-pending request"}, status=400)
        jr.status = "WITHDRAWN"
        jr.save(update_fields=["status"])
        return JsonResponse({"ok": True})
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("join_request_withdraw error")
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
