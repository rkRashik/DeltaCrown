from __future__ import annotations
from typing import Any, Dict, Optional

from django.apps import apps
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .helpers import read_title, read_fee_amount, register_url, coin_policy_of, first

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
PaymentVerification = apps.get_model("tournaments", "PaymentVerification")


def _is_window_open(t) -> bool:
    """Best-effort registration window check."""
    now = timezone.now()
    open_at = getattr(t, "reg_open_at", None)
    close_at = getattr(t, "reg_close_at", None)
    if open_at and now < open_at:
        return False
    if close_at and now > close_at:
        return False
    return True


def _has_capacity(t) -> bool:
    """Check capacity if defined (via t or t.settings)."""
    try:
        cap = first(getattr(t, "capacity", None), getattr(getattr(t, "settings", None), "capacity", None))
        if not cap:
            return True
        # Find a registrations-like relation to count
        for name in ("registrations", "participants", "teams"):
            if hasattr(t, name):
                rel = getattr(t, name)
                if hasattr(rel, "count"):
                    return rel.count() < int(cap)
        return True
    except Exception:
        return True


def register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Robust registration view.
    - GET: show form
    - POST: validate & create/attach Registration; if fee>0, require txn and create PaymentVerification(pending)
    - Idempotent: if a registration by this user already exists, update/continue it
    """
    t = get_object_or_404(Tournament, slug=slug)
    title = read_title(t)
    entry_fee = read_fee_amount(t)
    reg_url = register_url(t)

    # Window & capacity checks (best-effort)
    if request.method == "POST":
        if not _is_window_open(t):
            messages.error(request, "Registration is not open right now.")
            return redirect(reg_url)
        if not _has_capacity(t):
            messages.error(request, "Registration is full. No slots left.")
            return redirect(reg_url)

    if request.method == "POST":
        # ——— required minimal fields ———
        display_name = (request.POST.get("display_name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        email = (request.POST.get("email") or "").strip()
        team_name = (request.POST.get("team_name") or "").strip()

        if not display_name or not phone:
            messages.error(request, "Please provide your display name and contact number.")
            return redirect(reg_url)

        # ——— payments (require txn if fee>0) ———
        txn = (request.POST.get("txn") or "").strip()
        method = (request.POST.get("method") or "").strip()

        if entry_fee and entry_fee > 0 and not txn:
            messages.error(request, "Please provide your transaction ID to confirm your payment.")
            return redirect(reg_url)

        # ——— idempotent registration (reuse if already exists) ———
        reg = None
        try:
            user = getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None
            if user:
                reg = Registration.objects.filter(tournament=t, user=user).first()
            # fallback by phone if your model stores it (best-effort)
            if not reg and hasattr(Registration, "phone"):
                reg = Registration.objects.filter(tournament=t, phone=phone).first()
        except Exception:
            reg = None

        model_fields = set()
        try:
            model_fields = {f.name for f in Registration._meta.get_fields()}
        except Exception:
            model_fields = set()

        reg_payload = {
            "tournament": t,
            "user": getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
            "display_name": display_name,
            "phone": phone,
            "email": email or None,
            "team_name": team_name or None,
            "status": "submitted",
        }
        reg_payload = {k: v for k, v in reg_payload.items() if k in model_fields}

        try:
            if reg:
                # update basic fields if already registered
                for k, v in reg_payload.items():
                    setattr(reg, k, v)
                try:
                    reg.save()
                except Exception:
                    pass
            else:
                reg = Registration.objects.create(**reg_payload)
        except Exception:
            messages.error(request, "Could not save your registration. Please try again.")
            return redirect(reg_url)

        # ——— payments (create/update PaymentVerification) ———
        if entry_fee and entry_fee > 0:
            pv_fields = set()
            try:
                pv_fields = {f.name for f in PaymentVerification._meta.get_fields()}
            except Exception:
                pv_fields = set()

            if pv_fields:
                try:
                    pv = PaymentVerification.objects.filter(registration=reg).first()
                    pv_payload = {
                        "registration": reg,
                        "status": "pending",
                        "provider": method or None,
                        "transaction_id": txn or None,
                    }
                    pv_payload = {k: v for k, v in pv_payload.items() if k in pv_fields}
                    if pv:
                        for k, v in pv_payload.items():
                            setattr(pv, k, v)
                        pv.save()
                    else:
                        PaymentVerification.objects.create(**pv_payload)
                except Exception:
                    # non-fatal
                    pass

        messages.success(request, "Registration submitted. You can check your status anytime.")
        # Try to redirect to receipt if route exists
        try:
            return redirect("tournaments:registration_receipt", slug=t.slug)
        except Exception:
            return redirect(reg_url)  # fallback (GET shows "submitted" state)

    # GET
    ctx = {
        "t": t,
        "title": title,
        "entry_fee": entry_fee,
        "register_url": reg_url,
        "coin_policy": coin_policy_of(t),
    }
    return render(request, "tournaments/register.html", ctx)
