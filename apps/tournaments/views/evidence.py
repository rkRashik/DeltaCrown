from __future__ import annotations

from django.http import Http404, FileResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required

from ..models import MatchDisputeEvidence
from ..utils.signed_urls import verify_signature


@login_required
def evidence_download(request: HttpRequest, evidence_id: int):
    exp = request.GET.get("exp")
    sig = request.GET.get("sig")
    if not (exp and sig) or not verify_signature("evidence", int(evidence_id), int(exp), sig):
        raise Http404("Invalid or expired link")

    ev = get_object_or_404(MatchDisputeEvidence, pk=evidence_id)
    # Authorization: only dispute participants or staff
    disp = ev.dispute
    m = disp.match
    user = request.user
    is_staff = getattr(user, "is_staff", False)
    # Basic participant check: compare to match participants if available
    ok = is_staff
    if not ok:
        prof = getattr(user, "profile", None) or getattr(user, "userprofile", None)
        if prof is not None:
            ok = prof in [getattr(m, "user_a", None), getattr(m, "user_b", None)]
            if not ok:
                team_a = getattr(m, "team_a", None)
                team_b = getattr(m, "team_b", None)
                cap_a = getattr(team_a, "captain", None)
                cap_b = getattr(team_b, "captain", None)
                ok = prof in [cap_a, cap_b]
    if not ok:
        raise Http404()

    f = default_storage.open(ev.file.name, "rb")
    resp = FileResponse(f, content_type=ev.content_type or "application/octet-stream")
    resp["Content-Length"] = str(ev.size or 0)
    resp["Content-Disposition"] = f"inline; filename=\"{ev.file.name.split('/')[-1]}\""
    return resp

