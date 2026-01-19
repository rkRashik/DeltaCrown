# apps/economy/views/wallet.py
from __future__ import annotations

import csv
import datetime as dt
from typing import Optional

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

from apps.economy.models import DeltaCrownTransaction
from apps.economy.services import wallet_for


def _current_profile(user):
    """Get or lazily create the user's profile."""
    UserProfile = apps.get_model("user_profile", "UserProfile")
    profile = getattr(user, "userprofile", None)
    if profile:
        return profile
    # Fallback: get_or_create by user
    profile, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": getattr(user, "username", str(user.pk))}
    )
    return profile


def _parse_date(val: Optional[str]) -> Optional[dt.date]:
    if not val:
        return None
    try:
        return dt.datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def wallet_view(request: HttpRequest) -> HttpResponse:
    """
    UP PHASE 7.7: Old wallet page redirects to Settings → Wallet menu.
    
    The PIN setup UI has been moved to Settings for better UX.
    This redirect ensures old links still work.
    """
    messages.info(request, 'Wallet PIN settings have moved to Settings → Wallet menu.')
    # Redirect to user's settings page, Wallet tab
    return redirect(f'{reverse("user_profile:profile_settings")}#billing')


@login_required
def wallet_transactions_view(request: HttpRequest) -> HttpResponse:
    """
    Wallet transaction history (formerly at /wallet/, now at /transactions/).
    
    GET params:
      - reason: transaction reason (one of model choices)
      - start: YYYY-MM-DD (inclusive)
      - end: YYYY-MM-DD (inclusive)
      - page: int (1-based)
      - format=csv: export the filtered rows
    """
    profile = _current_profile(request.user)
    wallet = wallet_for(profile)

    qs = (
        DeltaCrownTransaction.objects.filter(wallet=wallet)
        .select_related("tournament", "registration", "match")
        .order_by("-created_at", "-id")
    )

    # Filters
    reason = request.GET.get("reason") or ""
    reason_choices = [("", "All reasons")] + list(DeltaCrownTransaction.Reason.choices)
    valid_reasons = {k for k, _ in DeltaCrownTransaction.Reason.choices}
    if reason and reason in valid_reasons:
        qs = qs.filter(reason=reason)

    start = _parse_date(request.GET.get("start"))
    end = _parse_date(request.GET.get("end"))
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    # CSV export
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"wallet_{profile.id}_{timezone.now().date().isoformat()}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(resp)
        writer.writerow(
            ["created_at", "amount", "reason", "note", "tournament", "registration_id", "match_id", "idempotency_key"]
        )
        for tx in qs.iterator():
            writer.writerow(
                [
                    timezone.localtime(tx.created_at).strftime("%Y-%m-%d %H:%M"),
                    tx.amount,
                    tx.reason,
                    tx.note or "",
                    getattr(tx.tournament, "name", "") if tx.tournament_id else "",
                    tx.registration_id or "",
                    tx.match_id or "",
                    tx.idempotency_key or "",
                ]
            )
        return resp

    # Pagination
    paginator = Paginator(qs, 20)
    page_no = request.GET.get("page") or "1"
    try:
        page = paginator.page(page_no)
    except EmptyPage:
        page = paginator.page(paginator.num_pages or 1)

    ctx = {
        "wallet": wallet,
        "page_obj": page,
        "paginator": paginator,
        "reason": reason,
        "reason_choices": reason_choices,
        "start": start.isoformat() if start else "",
        "end": end.isoformat() if end else "",
    }
    return render(request, "economy/transaction_history.html", ctx)
