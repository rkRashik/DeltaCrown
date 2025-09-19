from __future__ import annotations
from typing import Any, Dict, Optional
from django.apps import apps
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .helpers import read_title, read_fee_amount, register_url, coin_policy_of

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
PaymentVerification = apps.get_model("tournaments", "PaymentVerification")


def register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Minimal, robust registration view.
    - GET: show form
    - POST: create Registration + PaymentVerification(pending when fee>0), then redirect to receipt/status
    """
    t = get_object_or_404(Tournament, slug=slug)
    title = read_title(t)
    entry_fee = read_fee_amount(t)
    reg_url = register_url(t)

    if request.method == "POST":
        # ——— validate minimal fields (extend as needed) ———
        display_name = (request.POST.get("display_name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        email = (request.POST.get("email") or "").strip()
        team_name = (request.POST.get("team_name") or "").strip()

        if not display_name or not phone:
            messages.error(request, "Please provide your display name and contact number.")
            return redirect(reg_url)

        # ——— create Registration (best-effort; tolerate model variations) ———
        reg = None
        try:
            reg_kwargs = {
                "tournament": t,
                "user": getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
                "display_name": display_name,
                "phone": phone,
                "email": email or None,
                "team_name": team_name or None,
                "status": "submitted",
            }
            # Filter only fields that exist on the model
            model_fields = {f.name for f in Registration._meta.get_fields()}
            reg = Registration.objects.create(**{k: v for k, v in reg_kwargs.items() if k in model_fields})
        except Exception:
            messages.error(request, "Could not save your registration. Please try again.")
            return redirect(reg_url)

        # ——— payments (optional) ———
        txn = (request.POST.get("txn") or "").strip()
        method = (request.POST.get("method") or "").strip()

        if entry_fee and entry_fee > 0:
            try:
                pv_kwargs = {
                    "registration": reg,
                    "status": "pending",
                    "provider": method or None,
                    "transaction_id": txn or None,
                }
                pv_fields = set()
                try:
                    pv_fields = {f.name for f in PaymentVerification._meta.get_fields()}
                except Exception:
                    pv_fields = set()
                if pv_fields:
                    PaymentVerification.objects.create(**{k: v for k, v in pv_kwargs.items() if k in pv_fields})
            except Exception:
                # Non-fatal: registration saved anyway
                pass

        messages.success(request, "Registration submitted. You can see the status in your Dashboard.")
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
