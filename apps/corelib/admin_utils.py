# apps/corelib/admin_utils.py
from typing import Iterable
from django.db.models import QuerySet


def _path_exists(model, path: str) -> bool:
    """
    Verify a select_related path exists on 'model', supporting spans like 'profile__user'.
    We walk the model's fields hop-by-hop and ensure relations are followed correctly.
    """
    parts = path.split("__")
    current_model = model
    for i, part in enumerate(parts):
        try:
            field = current_model._meta.get_field(part)
        except Exception:
            return False

        is_last = (i == len(parts) - 1)
        if field.is_relation:
            # follow the relation for the next hop
            current_model = field.related_model
            if current_model is None:
                return False
        else:
            # non-relational field is only valid if it's the terminal segment
            if not is_last:
                return False
    return True


def _safe_select_related(qs: QuerySet, *paths: Iterable[str]) -> QuerySet:
    """
    Return qs.select_related(*existing_paths). Any invalid paths are ignored safely.
    """
    if not paths:
        return qs
    model = qs.model
    valid = [p for p in paths if _path_exists(model, p)]
    return qs.select_related(*valid) if valid else qs
