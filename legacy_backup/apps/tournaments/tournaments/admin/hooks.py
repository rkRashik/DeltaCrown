# apps/tournaments/admin/hooks.py
from django.contrib import admin

from .exports import export_matches_csv, export_disputes_csv

def attach_match_export_action(admin_site: admin.AdminSite) -> None:
    """
    Attach 'export_matches_csv' to an existing Match admin or register a minimal admin.
    """
    try:
        from ..models import Match as MatchModel
    except Exception:
        MatchModel = None

    if not MatchModel:
        return

    existing = admin_site._registry.get(MatchModel)
    if existing:
        existing.actions = list(set((existing.actions or []) + [export_matches_csv]))
    else:
        @admin.register(MatchModel)
        class _MatchAdmin(admin.ModelAdmin):
            list_display = ("id",)
            actions = [export_matches_csv]


def attach_dispute_export_action(admin_site: admin.AdminSite) -> None:
    """
    Attach 'export_disputes_csv' to an existing Dispute/MatchDispute admin or register a minimal admin.
    """
    DisputeModel = None
    try:
        from ..models import Dispute as _DisputeModel
        DisputeModel = _DisputeModel
    except Exception:
        try:
            from ..models import MatchDispute as _DisputeModel
            DisputeModel = _DisputeModel
        except Exception:
            DisputeModel = None

    if not DisputeModel:
        return

    existing = admin_site._registry.get(DisputeModel)
    if existing:
        existing.actions = list(set((existing.actions or []) + [export_disputes_csv]))
    else:
        @admin.register(DisputeModel)
        class _DisputeAdmin(admin.ModelAdmin):
            list_display = ("id",)
            actions = [export_disputes_csv]
