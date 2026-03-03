"""
TOC Sprint 10 — RBAC & Economy Service
========================================
S10-B1  Staff role assignment (uses existing TournamentStaffAssignment)
S10-B2  Permission checker overlay (enhances TOCBaseView)
S10-B3  DeltaCoin balance check (reads from Economy app)
S10-B4  DeltaCoin transaction endpoint
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class TOCRBACService:
    """RBAC & Economy integration for TOC."""

    def __init__(self, tournament):
        self.tournament = tournament

    # ------------------------------------------------------------------
    # S10-B1  Staff role management
    # ------------------------------------------------------------------
    def list_staff(self):
        from apps.tournaments.models import TournamentStaffAssignment

        qs = TournamentStaffAssignment.objects.filter(
            tournament=self.tournament
        ).select_related("user", "role").order_by("role__name", "user__username")

        return [
            {
                "id": s.pk,
                "user_id": s.user_id,
                "username": getattr(s.user, "username", ""),
                "display_name": getattr(s.user, "display_name", getattr(s.user, "username", "")),
                "role_id": s.role_id,
                "role_name": getattr(s.role, "name", ""),
                "assigned_at": str(s.assigned_at) if hasattr(s, "assigned_at") else None,
            }
            for s in qs
        ]

    def assign_staff(self, user_id, role_id):
        from apps.tournaments.models import TournamentStaffAssignment

        obj, created = TournamentStaffAssignment.objects.get_or_create(
            tournament=self.tournament,
            user_id=user_id,
            defaults={"role_id": role_id},
        )
        if not created and obj.role_id != role_id:
            obj.role_id = role_id
            obj.save(update_fields=["role_id"])
        return {"id": obj.pk, "user_id": user_id, "role_id": role_id, "created": created}

    def remove_staff(self, assignment_id):
        from apps.tournaments.models import TournamentStaffAssignment

        TournamentStaffAssignment.objects.filter(
            pk=assignment_id, tournament=self.tournament
        ).delete()

    def list_roles(self):
        from apps.tournaments.models import StaffRole

        return list(
            StaffRole.objects.all().order_by("name").values(
                "id", "name", "code", "description", "capabilities",
                "is_referee_role",
            )
        )

    # ------------------------------------------------------------------
    # S10-B2  Permission checker (capability-based)
    # ------------------------------------------------------------------

    # Maps capability flags -> which TOC tabs they unlock
    CAPABILITY_TAB_MAP = {
        "full_access": "*",
        "edit_settings": ["settings"],
        "manage_registrations": ["overview", "participants"],
        "approve_payments": ["overview", "payments"],
        "manage_brackets": ["overview", "brackets", "matches", "schedule"],
        "resolve_disputes": ["disputes"],
        "make_announcements": ["announcements"],
        "view_all": ["overview"],
    }

    def get_user_permissions(self, user):
        """Return tabs, capabilities, and actions this user can access."""
        # Superuser / staff / organizer = full access
        if user.is_superuser or user.is_staff:
            return {
                "tabs": "*",
                "capabilities": ["full_access"],
                "is_organizer": True,
            }
        if self.tournament.organizer_id == user.id:
            return {
                "tabs": "*",
                "capabilities": ["full_access"],
                "is_organizer": True,
            }

        from apps.tournaments.models import TournamentStaffAssignment

        assignments = TournamentStaffAssignment.objects.filter(
            tournament=self.tournament, user=user
        ).select_related("role")

        if not assignments.exists():
            return {"tabs": [], "capabilities": ["view_all"], "is_organizer": False}

        # Merge capabilities from all assigned roles
        merged_caps = set()
        for a in assignments:
            caps = getattr(a.role, "capabilities", {}) or {}
            for cap_name, enabled in caps.items():
                if enabled:
                    merged_caps.add(cap_name)

        # Full access shortcut
        if "full_access" in merged_caps:
            return {
                "tabs": "*",
                "capabilities": sorted(merged_caps),
                "is_organizer": False,
            }

        # Resolve tabs from capabilities
        tabs = set()
        for cap in merged_caps:
            allowed = self.CAPABILITY_TAB_MAP.get(cap, [])
            if allowed == "*":
                return {
                    "tabs": "*",
                    "capabilities": sorted(merged_caps),
                    "is_organizer": False,
                }
            tabs.update(allowed)

        return {
            "tabs": sorted(tabs),
            "capabilities": sorted(merged_caps),
            "is_organizer": False,
        }

    # ------------------------------------------------------------------
    # S10-B3  DeltaCoin balance
    # ------------------------------------------------------------------
    def get_deltacoin_balance(self, user_id):
        """Retrieve user's DeltaCoin wallet balance from Economy app."""
        try:
            from apps.economy.models import Wallet
            wallet = Wallet.objects.filter(user_id=user_id).first()
            if wallet:
                return {
                    "user_id": user_id,
                    "balance": str(wallet.balance),
                    "currency": "DeltaCoin",
                }
        except (ImportError, Exception) as e:
            logger.debug("Economy wallet lookup failed: %s", e)

        return {"user_id": user_id, "balance": "0.00", "currency": "DeltaCoin"}

    # ------------------------------------------------------------------
    # S10-B4  DeltaCoin transactions
    # ------------------------------------------------------------------
    def get_transactions(self, user_id, limit=50):
        """List recent DeltaCoin transactions for a user."""
        try:
            from apps.economy.models import Transaction
            qs = Transaction.objects.filter(
                user_id=user_id
            ).order_by("-created_at")[:limit]
            return [
                {
                    "id": t.pk,
                    "amount": str(t.amount),
                    "transaction_type": getattr(t, "transaction_type", ""),
                    "description": getattr(t, "description", ""),
                    "created_at": str(t.created_at),
                }
                for t in qs
            ]
        except (ImportError, Exception) as e:
            logger.debug("Economy transaction lookup failed: %s", e)
            return []

    def process_entry_fee(self, user_id, amount=None):
        """Deduct tournament entry fee from user's DeltaCoin wallet."""
        fee = amount or self.tournament.entry_fee_amount
        if not fee:
            return {"status": "no_fee", "message": "No entry fee configured"}

        try:
            from apps.economy.models import Wallet, Transaction
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user_id=user_id)
                if wallet.balance < fee:
                    return {"status": "insufficient", "balance": str(wallet.balance), "required": str(fee)}
                wallet.balance -= fee
                wallet.save(update_fields=["balance"])
                Transaction.objects.create(
                    user_id=user_id,
                    amount=-fee,
                    transaction_type="entry_fee",
                    description=f"Entry fee for {self.tournament.name}",
                )
                return {"status": "success", "deducted": str(fee), "new_balance": str(wallet.balance)}
        except (ImportError, Exception) as e:
            logger.warning("Entry fee processing failed: %s", e)
            return {"status": "error", "message": str(e)}

    def distribute_prize(self, user_id, amount, description=""):
        """Credit DeltaCoin prize to user wallet."""
        try:
            from apps.economy.models import Wallet, Transaction
            with transaction.atomic():
                wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
                wallet.balance += Decimal(str(amount))
                wallet.save(update_fields=["balance"])
                Transaction.objects.create(
                    user_id=user_id,
                    amount=amount,
                    transaction_type="prize",
                    description=description or f"Prize from {self.tournament.name}",
                )
                return {"status": "success", "credited": str(amount), "new_balance": str(wallet.balance)}
        except (ImportError, Exception) as e:
            logger.warning("Prize distribution failed: %s", e)
            return {"status": "error", "message": str(e)}
