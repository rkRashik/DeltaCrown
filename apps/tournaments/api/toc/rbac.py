"""
TOC Sprint 10 — RBAC & Economy API Views
==========================================
S10-B1  Staff role management
S10-B2  Permission checker
S10-B3  DeltaCoin balance
S10-B4  DeltaCoin transactions
"""

from rest_framework import status
from rest_framework.response import Response

from .base import TOCBaseView
from .rbac_service import TOCRBACService


# ------------------------------------------------------------------
# S10-B1  Staff roles
# ------------------------------------------------------------------
class StaffListView(TOCBaseView):
    """GET — list staff  |  POST — assign staff."""

    def get(self, request, slug):
        svc = TOCRBACService(self.tournament)
        return Response(svc.list_staff())

    def post(self, request, slug):
        svc = TOCRBACService(self.tournament)
        result = svc.assign_staff(
            request.data.get("user_id"),
            request.data.get("role_id"),
        )
        return Response(result, status=status.HTTP_201_CREATED)


class StaffDetailView(TOCBaseView):
    """DELETE — remove staff assignment."""

    def delete(self, request, slug, pk):
        svc = TOCRBACService(self.tournament)
        svc.remove_staff(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListView(TOCBaseView):
    """GET — list available roles."""

    def get(self, request, slug):
        svc = TOCRBACService(self.tournament)
        return Response(svc.list_roles())


# ------------------------------------------------------------------
# S10-B2  Permission checker
# ------------------------------------------------------------------
class PermissionsView(TOCBaseView):
    """GET — current user's permissions for this tournament."""

    def get(self, request, slug):
        svc = TOCRBACService(self.tournament)
        return Response(svc.get_user_permissions(request.user))


# ------------------------------------------------------------------
# S10-B3/B4  Economy
# ------------------------------------------------------------------
class DeltaCoinBalanceView(TOCBaseView):
    """GET — user's DeltaCoin balance."""

    def get(self, request, slug, user_id):
        svc = TOCRBACService(self.tournament)
        return Response(svc.get_deltacoin_balance(user_id))


class DeltaCoinTransactionsView(TOCBaseView):
    """GET — user's transaction history."""

    def get(self, request, slug, user_id):
        svc = TOCRBACService(self.tournament)
        return Response(svc.get_transactions(user_id))


class EntryFeeView(TOCBaseView):
    """POST — process entry fee deduction."""

    def post(self, request, slug):
        svc = TOCRBACService(self.tournament)
        result = svc.process_entry_fee(
            request.data.get("user_id"),
            request.data.get("amount"),
        )
        return Response(result)


class PrizeDistributeView(TOCBaseView):
    """POST — distribute DeltaCoin prize."""

    def post(self, request, slug):
        svc = TOCRBACService(self.tournament)
        result = svc.distribute_prize(
            request.data.get("user_id"),
            request.data.get("amount"),
            request.data.get("description", ""),
        )
        return Response(result)
