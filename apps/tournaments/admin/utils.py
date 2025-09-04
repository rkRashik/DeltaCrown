# apps/tournaments/admin/utils.py
from __future__ import annotations

from typing import Iterable, List
from django.contrib import messages
from django.db import models


def _is_forward_relation(field: models.Field) -> bool:
    """
    True if this model field is a concrete forward relation suitable for select_related()
    (i.e., ForeignKey / OneToOneField). Excludes M2M and reverse relations.
    """
    remote = getattr(field, "remote_field", None)
    return bool(remote) and not getattr(field, "many_to_many", False)


def _path_exists(model: type[models.Model], path: str) -> bool:
    """
    Verify that a select_related path exists (supports spans like 'a__b__c').
    Walks forward relations only.
    """
    parts = path.split("__")
    m = model
    for p in parts:
        try:
            f = m._meta.get_field(p)
        except Exception:
            return False
        if _is_forward_relation(f) and getattr(f, "remote_field", None):
            m = f.remote_field.model  # follow to next model
        else:
            # Not a relation: only acceptable if this is the last segment.
            if p != parts[-1]:
                return False
    return True


def safe_select_related(qs, model: type[models.Model], names: Iterable[str]):
    """
    Apply select_related() only for relation names/paths that truly exist on `model`.
    Silently ignores bad names to avoid FieldError.
    """
    if not names:
        return qs
    valid: List[str] = []
    for name in names:
        try:
            if _path_exists(model, name):
                valid.append(name)
        except Exception:
            # Be defensive: ignore anything unexpected.
            continue
    return qs.select_related(*valid) if valid else qs


# --- Backward compatibility alias (other modules import this name) ---
# e.g., from .utils import _safe_select_related
_safe_select_related = safe_select_related


def _safe_message(modeladmin, request, msg: str, level=None):
    """
    Call ModelAdmin.message_user safely (also works in tests when middleware may differ).
    """
    try:
        modeladmin.message_user(request, msg, level=level or messages.INFO)
    except Exception:
        pass
