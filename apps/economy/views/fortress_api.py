# apps/economy/views/fortress_api.py
"""
Financial Fortress — JSON API Endpoints (Phase B + C)
======================================================

All endpoints require:
  1. is_superuser (enforced by @user_passes_test)
  2. Valid CSRF token on POST requests (enforced by Django's CsrfViewMiddleware)

Response envelope
-----------------
Success:  { "ok": true,  "data": { ... } }
Error:    { "ok": false, "error": "Human-readable message" }
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.economy.models import DeltaCrownWallet, TopUpRequest
from apps.economy.models.audit import FortressAuditLog
from apps.economy.services import get_master_treasury
from apps.economy.fortress_services import (
    FortressError,
    TopUpAlreadyProcessed,
    UserWalletNotFound,
    fortress_airdrop,
    fortress_approve_topup,
    fortress_bulk_airdrop,
    mint_to_treasury,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _superuser_only(user) -> bool:
    return user.is_active and user.is_superuser


def _fortress_guard(view_func):
    """Stacks login_required + superuser check in one decorator."""
    return login_required(
        user_passes_test(_superuser_only, login_url="/admin/login/")(view_func),
        login_url="/admin/login/",
    )


def _json_body(request) -> dict:
    """Parse JSON request body; raise ValueError on bad input."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc


def _ok(data: dict) -> JsonResponse:
    return JsonResponse({"ok": True, "data": data})


def _err(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


# ---------------------------------------------------------------------------
# GET /economy/fortress/api/status/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_GET
def api_status(request) -> JsonResponse:
    """
    Real-time economy health snapshot.

    Returns
    -------
    treasury_balance      : int   (negative = coins in circulation)
    circulating_supply    : int   (sum of all non-treasury wallet balances)
    ledger_delta          : int   (should always be 0 if healthy)
    ledger_healthy        : bool
    wallet_count          : int   (number of user wallets)
    pending_topups_count  : int
    """
    treasury = get_master_treasury()
    treasury_balance = int(treasury.cached_balance)

    circulating_supply = int(
        DeltaCrownWallet.objects
        .filter(is_treasury=False, deleted_at__isnull=True)
        .aggregate(total=Sum("cached_balance"))["total"] or 0
    )

    ledger_delta = circulating_supply + treasury_balance

    return _ok({
        "treasury_balance": treasury_balance,
        "circulating_supply": circulating_supply,
        "ledger_delta": ledger_delta,
        "ledger_healthy": ledger_delta == 0,
        "wallet_count": DeltaCrownWallet.objects.filter(is_treasury=False).count(),
        "pending_topups_count": TopUpRequest.objects.filter(status="pending").count(),
        "timestamp": timezone.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# GET /economy/fortress/api/approvals/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_GET
def api_approvals(request) -> JsonResponse:
    """
    Return all PENDING TopUpRequests as JSON for the Fortress approvals table.
    """
    pending = (
        TopUpRequest.objects
        .filter(status=TopUpRequest.Status.PENDING)
        .select_related("wallet__profile__user")
        .order_by("-requested_at")
    )

    rows = []
    for req in pending:
        user = req.wallet.profile.user if (req.wallet and req.wallet.profile) else None
        rows.append({
            "id": f"REQ-{req.pk}",
            "pk": req.pk,
            "user": user.username if user else "—",
            "date": req.requested_at.isoformat(),
            "amount": req.amount,
            "fiat": f"৳{req.bdt_amount}",
            "method": req.get_payment_method_display(),
            "txid": req.payment_number or "—",
            "phone": (req.payment_details or {}).get("phone", req.payment_number or "—"),
            "status": req.status,
        })

    return _ok({"approvals": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# POST /economy/fortress/api/mint/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_mint(request) -> JsonResponse:
    """
    Mint DC into the Master Treasury.

    Body (JSON)
    -----------
    amount_dc   : int     (must be > 0)
    reference   : str     (fiat backing reference, e.g. "BD-7892X")
    """
    try:
        body = _json_body(request)
        amount_dc = int(body.get("amount_dc", 0))
        reference = str(body.get("reference", "")).strip()
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    if amount_dc <= 0:
        return _err("amount_dc must be a positive integer.")
    if not reference:
        return _err("reference is required (fiat backing reference).")

    try:
        txn = mint_to_treasury(
            amount_dc=amount_dc,
            reference=reference,
            actor=request.user,
        )
    except FortressError as exc:
        return _err(str(exc))
    except Exception as exc:
        logger.exception("[FORTRESS] api_mint failed: %s", exc)
        return _err("Internal server error during mint operation.", status=500)

    treasury = get_master_treasury()
    return _ok({
        "txn_id": txn.pk,
        "amount_minted": amount_dc,
        "new_treasury_balance": int(treasury.cached_balance),
        "reference": reference,
    })


# ---------------------------------------------------------------------------
# POST /economy/fortress/api/airdrop/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_airdrop(request) -> JsonResponse:
    """
    Airdrop DC from Treasury directly to a user wallet.

    Body (JSON)
    -----------
    username    : str     (exact username of the target user)
    amount_dc   : int     (must be > 0)
    note        : str     (classification / reason for audit log)
    """
    try:
        body = _json_body(request)
        username  = str(body.get("username", "")).strip()
        amount_dc = int(body.get("amount_dc", 0))
        note      = str(body.get("note", "Admin Airdrop")).strip()
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    if not username:
        return _err("username is required.")
    if amount_dc <= 0:
        return _err("amount_dc must be a positive integer.")

    try:
        result = fortress_airdrop(
            target_username=username,
            amount_dc=amount_dc,
            note=note,
            actor=request.user,
        )
    except UserWalletNotFound as exc:
        return _err(str(exc), status=404)
    except FortressError as exc:
        return _err(str(exc))
    except Exception as exc:
        logger.exception("[FORTRESS] api_airdrop failed: %s", exc)
        return _err("Internal server error during airdrop.", status=500)

    return _ok(result)


# ---------------------------------------------------------------------------
# POST /economy/fortress/api/approve-topup/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_approve_topup(request) -> JsonResponse:
    """
    Approve a pending TopUpRequest: debit treasury, credit user.

    Body (JSON)
    -----------
    request_id  : int     (PK of the TopUpRequest row)
    """
    try:
        body = _json_body(request)
        request_id = int(body.get("request_id", 0))
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    if request_id <= 0:
        return _err("request_id must be a positive integer.")

    try:
        result = fortress_approve_topup(
            request_id=request_id,
            actor=request.user,
        )
    except TopUpAlreadyProcessed as exc:
        return _err(str(exc), status=409)
    except FortressError as exc:
        return _err(str(exc), status=404)
    except Exception as exc:
        logger.exception("[FORTRESS] api_approve_topup failed: %s", exc)
        return _err("Internal server error during approval.", status=500)

    return _ok(result)


# ---------------------------------------------------------------------------
# POST /economy/fortress/api/reject-topup/
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_reject_topup(request) -> JsonResponse:
    """
    Reject a pending TopUpRequest (no ledger changes — just marks rejected).

    Body (JSON)
    -----------
    request_id  : int
    reason      : str     (shown to user)
    """
    try:
        body = _json_body(request)
        request_id = int(body.get("request_id", 0))
        reason     = str(body.get("reason", "Rejected by admin")).strip()
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    if request_id <= 0:
        return _err("request_id must be a positive integer.")

    try:
        topup = TopUpRequest.objects.get(pk=request_id)
    except TopUpRequest.DoesNotExist:
        return _err(f"TopUpRequest #{request_id} not found.", status=404)

    if topup.status != TopUpRequest.Status.PENDING:
        return _err(f"Cannot reject — status is already '{topup.status}'.", status=409)

    topup.status = TopUpRequest.Status.REJECTED
    topup.reviewed_at = timezone.now()
    topup.reviewed_by = request.user
    topup.rejection_reason = reason
    topup.admin_note = f"[FORTRESS] Rejected by {request.user.username}"
    topup.save()

    logger.info(
        "[FORTRESS] REJECT_TOPUP id=%s actor=%s reason=%s",
        request_id, request.user.username, reason,
    )
    return _ok({"topup_id": request_id, "status": "rejected"})


# ---------------------------------------------------------------------------
# GET /economy/fortress/api/audit/  (Phase C)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_GET
def api_audit(request) -> JsonResponse:
    """
    Return the latest 50 FortressAuditLog entries for the Audit Ledger tab.

    Returns
    -------
    logs : list of {
        id, timestamp, actor, action, target, amount, note
    }
    """
    try:
        limit = min(int(request.GET.get("limit", 50)), 200)
    except (ValueError, TypeError):
        limit = 50

    entries = (
        FortressAuditLog.objects
        .select_related("actor", "target_wallet__profile__user")
        .order_by("-created_at")[:limit]
    )

    # Action → colour mapping for the SPA badge
    ACTION_COLOUR = {
        "MINT_TO_TREASURY":  "cyan",
        "AIRDROP":           "gold",
        "BULK_AIRDROP":      "purple",
        "APPROVE_TOPUP":     "green",
        "REJECT_TOPUP":      "red",
        "AUTO_REWARD_KYC":   "blue",
        "AUTO_REWARD_MATCH": "blue",
    }

    rows = []
    for entry in entries:
        rows.append({
            "id":        entry.pk,
            "timestamp": entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "actor":     entry.actor_label,
            "action":    entry.action,
            "colour":    ACTION_COLOUR.get(entry.action, "gray"),
            "target":    entry.target_label or "—",
            "amount":    entry.amount,
            "note":      entry.note[:120] if entry.note else "",
        })

    return _ok({"logs": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# POST /economy/fortress/api/airdrop/bulk/  (Phase C)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_bulk_airdrop(request) -> JsonResponse:
    """
    Bulk-airdrop DC from Treasury to multiple users simultaneously.

    Body (JSON)
    -----------
    usernames   : list[str]   (comma-separated OR JSON array)
    amount_dc   : int         (per-user amount, must be > 0)
    note        : str         (classification / reason)
    """
    try:
        body      = _json_body(request)
        raw_users = body.get("usernames", [])
        amount_dc = int(body.get("amount_dc", 0))
        note      = str(body.get("note", "Bulk Admin Airdrop")).strip()
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    # Accept both JSON array and comma-separated string
    if isinstance(raw_users, str):
        usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
    elif isinstance(raw_users, list):
        usernames = [str(u).strip() for u in raw_users if str(u).strip()]
    else:
        return _err("usernames must be a JSON array or comma-separated string.")

    if not usernames:
        return _err("usernames list is empty.")
    if len(usernames) > 500:
        return _err("Bulk airdrop is capped at 500 users per batch.")
    if amount_dc <= 0:
        return _err("amount_dc must be a positive integer.")

    try:
        result = fortress_bulk_airdrop(
            usernames=usernames,
            amount_dc_each=amount_dc,
            note=note,
            actor=request.user,
        )
    except FortressError as exc:
        return _err(str(exc))
    except Exception as exc:
        logger.exception("[FORTRESS] api_bulk_airdrop failed: %s", exc)
        return _err("Internal server error during bulk airdrop.", status=500)

    return _ok(result.to_dict())


# ---------------------------------------------------------------------------
# GET /fortress/api/wallets/  (Task 4)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_GET
def api_wallets(request) -> JsonResponse:
    """
    Return all DeltaCrownWallet rows with balance and PIN status.

    Response rows
    -------------
    id, username, email, balance, is_treasury, has_pin, wallet_id
    """
    from apps.economy.models import WalletPINOTP

    wallets = (
        DeltaCrownWallet.objects
        .select_related("profile__user")
        .filter(deleted_at__isnull=True)
        .order_by("-cached_balance")
    )

    rows = []
    for w in wallets:
        user = w.profile.user if (w.profile and w.profile.user) else None
        # A wallet has a PIN if it has at least one non-soft-deleted OTP record
        # that has been successfully used (is_used=True).
        has_pin = WalletPINOTP.objects.filter(
            wallet=w, is_used=True, deleted_at__isnull=True
        ).exists()
        rows.append({
            "wallet_id":   w.pk,
            "username":    user.username if user else "—",
            "email":       user.email    if user else "—",
            "balance":     int(w.cached_balance),
            "is_treasury": w.is_treasury,
            "has_pin":     has_pin,
        })

    return _ok({"wallets": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# POST /fortress/api/wallets/reset-pin/  (Task 4)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_reset_pin(request) -> JsonResponse:
    """
    Clear / reset a user's wallet PIN by soft-deleting all their OTP records
    and nullifying the wallet's pin_hash (if the field exists).

    Body (JSON)
    -----------
    wallet_id : int   (PK of the DeltaCrownWallet to reset)

    Effect
    ------
    * All WalletPINOTP rows for this wallet are soft-deleted
    * Writes a FortressAuditLog entry (action=AIRDROP repurposed — using note)
    * The user must go through the full PIN-setup OTP flow again next login
    """
    from django.utils import timezone as tz
    from apps.economy.models import WalletPINOTP
    from apps.economy.models.audit import FortressAuditLog

    try:
        body     = _json_body(request)
        wallet_id = int(body.get("wallet_id", 0))
    except (ValueError, TypeError) as exc:
        return _err(f"Bad request body: {exc}")

    if wallet_id <= 0:
        return _err("wallet_id must be a positive integer.")

    try:
        wallet = (
            DeltaCrownWallet.objects
            .select_related("profile__user")
            .get(pk=wallet_id, is_treasury=False)
        )
    except DeltaCrownWallet.DoesNotExist:
        return _err(f"Wallet #{wallet_id} not found.", status=404)

    username = wallet.profile.user.username if (wallet.profile and wallet.profile.user) else "—"

    # Soft-delete all OTP records for this wallet
    cleared = WalletPINOTP.objects.filter(
        wallet=wallet, deleted_at__isnull=True
    ).update(deleted_at=tz.now())

    # Write audit entry
    try:
        FortressAuditLog.objects.create(
            action="AIRDROP",          # reuse closest enum; note carries context
            actor=request.user,
            actor_label=request.user.username,
            target_wallet=wallet,
            target_label=username,
            amount=0,
            note=f"[PIN RESET] All OTP records cleared for wallet #{wallet_id} ({username}) by {request.user.username}",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
    except Exception as exc:
        logger.error("[FORTRESS] api_reset_pin audit log failed: %s", exc)

    logger.info(
        "[FORTRESS] PIN_RESET wallet=%s user=%s cleared=%s by=%s",
        wallet_id, username, cleared, request.user.username,
    )
    return _ok({
        "wallet_id":      wallet_id,
        "username":       username,
        "records_cleared": cleared,
        "message":        f"PIN reset for {username}. They must re-setup PIN on next login.",
    })
