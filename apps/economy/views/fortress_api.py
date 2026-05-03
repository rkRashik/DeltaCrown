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
# POST /fortress/api/pin/verify/   (Phase D)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_pin_verify(request) -> JsonResponse:
    """
    Server-side Fortress PIN verification.

    Replaces the insecure client-side MASTER_PIN comparison.

    Body (JSON)
    -----------
    pin : str   The 4-8 digit PIN to verify.

    Session keys used
    -----------------
    _fortress_pin_attempts   : int   — wrong-attempt counter
    _fortress_pin_locked_until : str  — ISO timestamp of lock expiry

    Returns
    -------
    { ok: true,  data: { verified: true } }  on success
    { ok: false, error: "...", locked_until?: "ISO" }  on failure
    """
    from django.utils import timezone as tz
    from apps.economy.models.config import EconomyConfig

    # ── Brute-force guard ────────────────────────────────────────────────
    locked_until_str = request.session.get("_fortress_pin_locked_until")
    if locked_until_str:
        import datetime
        locked_until = datetime.datetime.fromisoformat(locked_until_str)
        if tz.now() < locked_until:
            return JsonResponse(
                {"ok": False, "error": "Too many failed attempts. Try again later.",
                 "locked_until": locked_until_str},
                status=429,
            )
        # Lock has expired — reset counters
        request.session.pop("_fortress_pin_locked_until", None)
        request.session["_fortress_pin_attempts"] = 0

    # ── Extract PIN ───────────────────────────────────────────────────────
    try:
        body = _json_body(request)
        pin  = str(body.get("pin", "")).strip()
    except ValueError as exc:
        return _err(f"Bad request: {exc}")

    if not pin:
        return _err("PIN is required.")

    # ── Load config + verify ──────────────────────────────────────────────
    config = EconomyConfig.get_solo()

    if not config.fortress_pin_hash:
        logger.warning("[FORTRESS] PIN verify attempted but no PIN is set in EconomyConfig.")
        return _err("Fortress PIN has not been configured. Set it in Admin → Economy Config.", status=503)

    if config.check_fortress_pin(pin):
        # Success — reset attempts counter and mark session as verified
        request.session["_fortress_pin_attempts"]  = 0
        request.session["_fortress_verified"]       = True
        logger.info("[FORTRESS] PIN verified OK for user=%s ip=%s",
                    request.user.username, request.META.get("REMOTE_ADDR"))
        return _ok({"verified": True})

    # ── Wrong PIN ─────────────────────────────────────────────────────────
    attempts = request.session.get("_fortress_pin_attempts", 0) + 1
    request.session["_fortress_pin_attempts"] = attempts
    max_attempts = config.fortress_pin_max_attempts

    logger.warning("[FORTRESS] Wrong PIN attempt=%s/%s user=%s ip=%s",
                   attempts, max_attempts, request.user.username, request.META.get("REMOTE_ADDR"))

    if attempts >= max_attempts:
        locked_until = tz.now() + __import__("datetime").timedelta(seconds=60)
        request.session["_fortress_pin_locked_until"] = locked_until.isoformat()
        request.session["_fortress_pin_attempts"]     = 0
        return JsonResponse(
            {"ok": False,
             "error": f"Too many failed attempts ({max_attempts}). Locked for 60 seconds.",
             "locked_until": locked_until.isoformat()},
            status=429,
        )

    remaining = max_attempts - attempts
    return _err(f"Incorrect PIN. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")


# ---------------------------------------------------------------------------
# POST /fortress/api/pin/set/   (Phase D)
# ---------------------------------------------------------------------------

@_fortress_guard
@require_POST
def api_pin_set(request) -> JsonResponse:
    """
    Rotate the Fortress master PIN without touching Django Admin.

    Body (JSON)
    -----------
    current_pin : str   Must match the existing hash (or be blank if no PIN set yet).
    new_pin     : str   4-8 digits. Will be hashed with Django's default hasher.

    Effect
    ------
    * Updates EconomyConfig.fortress_pin_hash
    * Writes a FortressAuditLog entry
    * Resets any active lockout in the current session
    """
    from apps.economy.models.config import EconomyConfig
    from apps.economy.models.audit import FortressAuditLog

    try:
        body        = _json_body(request)
        current_pin = str(body.get("current_pin", "")).strip()
        new_pin     = str(body.get("new_pin", "")).strip()
    except ValueError as exc:
        return _err(f"Bad request: {exc}")

    if not new_pin or len(new_pin) < 4 or len(new_pin) > 8 or not new_pin.isdigit():
        return _err("new_pin must be 4-8 digits.")

    config = EconomyConfig.get_solo()

    # Allow setting a PIN for the first time (no current hash)
    if config.fortress_pin_hash:
        if not config.check_fortress_pin(current_pin):
            return _err("Current PIN is incorrect.")

    config.set_fortress_pin(new_pin)
    config.save(update_fields=["fortress_pin_hash", "updated_at"])

    # Clear session lock counters
    request.session.pop("_fortress_pin_attempts", None)
    request.session.pop("_fortress_pin_locked_until", None)
    request.session["_fortress_verified"] = True

    try:
        FortressAuditLog.objects.create(
            action=FortressAuditLog.Action.AIRDROP,   # closest enum; note carries context
            actor=request.user,
            actor_label=request.user.username,
            amount=0,
            note=f"[PIN ROTATED] Fortress master PIN changed by {request.user.username}",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
    except Exception as exc:
        logger.error("[FORTRESS] api_pin_set audit log failed: %s", exc)

    logger.info("[FORTRESS] PIN_ROTATE by user=%s ip=%s", request.user.username, request.META.get("REMOTE_ADDR"))
    return _ok({"rotated": True, "message": "Fortress PIN updated successfully."})


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
    total_inflow          : int   (sum of approved TopUpRequest amounts)
    admin_outflow         : int   (sum of Airdrop/BulkAirdrop audit amounts)
    distribution          : dict  (user_wallets, org_treasuries, escrow amounts + %)
    """
    from django.db.models import Q
    from apps.economy.models.audit import FortressAuditLog

    treasury = get_master_treasury()
    treasury_balance = int(treasury.cached_balance)

    # All non-treasury wallets
    user_wallets_qs = DeltaCrownWallet.objects.filter(
        is_treasury=False, deleted_at__isnull=True
    )

    circulating_supply = int(
        user_wallets_qs.aggregate(total=Sum("cached_balance"))["total"] or 0
    )

    ledger_delta = circulating_supply + treasury_balance

    # ── Macro stats ──────────────────────────────────────────────────────────
    # Total fiat-backed inflow = sum of all approved top-up requests
    total_inflow = int(
        TopUpRequest.objects
        .filter(status=TopUpRequest.Status.APPROVED)
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    # Admin outflow = all airdrop-type audit log amounts
    admin_outflow = int(
        FortressAuditLog.objects
        .filter(action__in=[
            FortressAuditLog.Action.AIRDROP,
            FortressAuditLog.Action.BULK_AIRDROP,
            FortressAuditLog.Action.AUTO_REWARD_KYC,
            FortressAuditLog.Action.AUTO_REWARD_MATCH,
        ])
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    # ── Circulation distribution ─────────────────────────────────────────────
    # Org/team treasuries: wallets linked to an org profile
    try:
        from apps.organizations.models import Organization  # noqa: F401
        org_wallet_ids = list(
            DeltaCrownWallet.objects
            .filter(is_treasury=False, deleted_at__isnull=True)
            .filter(profile__organization__isnull=False)
            .values_list('pk', flat=True)
        )
    except Exception:
        org_wallet_ids = []

    # Escrow: wallets involved in active escrow locks
    try:
        from apps.economy.models import DeltaCrownTransaction
        from django.db.models import OuterRef, Subquery
        escrow_wallet_ids = list(
            DeltaCrownWallet.objects
            .filter(is_treasury=False, deleted_at__isnull=True)
            .filter(
                transactions__reason=DeltaCrownTransaction.Reason.ESCROW_LOCK,
            )
            .values_list('pk', flat=True)
            .distinct()
        )
    except Exception:
        escrow_wallet_ids = []

    org_supply = int(
        DeltaCrownWallet.objects
        .filter(pk__in=org_wallet_ids, deleted_at__isnull=True)
        .aggregate(total=Sum("cached_balance"))["total"] or 0
    ) if org_wallet_ids else 0

    escrow_supply = int(
        DeltaCrownWallet.objects
        .filter(pk__in=escrow_wallet_ids, deleted_at__isnull=True)
        .aggregate(total=Sum("cached_balance"))["total"] or 0
    ) if escrow_wallet_ids else 0

    user_supply = max(0, circulating_supply - org_supply - escrow_supply)

    total_c = circulating_supply or 1  # avoid div/0
    distribution = {
        "user_wallets":    {"amount": user_supply,   "pct": round(user_supply   / total_c * 100, 1)},
        "org_treasuries":  {"amount": org_supply,    "pct": round(org_supply    / total_c * 100, 1)},
        "escrow":          {"amount": escrow_supply, "pct": round(escrow_supply / total_c * 100, 1)},
    }

    return _ok({
        "treasury_balance":    treasury_balance,
        "circulating_supply":  circulating_supply,
        "ledger_delta":        ledger_delta,
        "ledger_healthy":      ledger_delta == 0,
        "wallet_count":        user_wallets_qs.count(),
        "pending_topups_count": TopUpRequest.objects.filter(status="pending").count(),
        "total_inflow":        total_inflow,
        "admin_outflow":       admin_outflow,
        "distribution":        distribution,
        "timestamp":           timezone.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# GET /fortress/api/users/search/?q=<query>
# ---------------------------------------------------------------------------

@_fortress_guard
@require_GET
def api_user_search(request) -> JsonResponse:
    """
    Fuzzy user search for the Airdrop autocomplete dropdown.

    Query params
    ------------
    q : str   Search string (username prefix match). Min 1 char, max 5 results.

    Returns
    -------
    users : list of { id, username, avatar_url }
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    User = get_user_model()
    q = request.GET.get("q", "").strip()

    if not q:
        return _ok({"users": []})

    matches = (
        User.objects
        .filter(
            Q(username__icontains=q) | Q(email__icontains=q),
            is_active=True,
        )
        .exclude(is_superuser=True)           # don't expose superuser accounts
        .select_related("profile")
        .order_by("username")
        [:5]
    )

    users = []
    for user in matches:
        # Resolve avatar URL safely
        avatar_url = None
        try:
            prof = getattr(user, "profile", None)
            if prof:
                av = getattr(prof, "avatar", None)
                if av and hasattr(av, "url"):
                    avatar_url = av.url
        except Exception:
            pass

        users.append({
            "id":         user.pk,
            "username":   user.username,
            "avatar_url": avatar_url,
        })

    return _ok({"users": users})


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
