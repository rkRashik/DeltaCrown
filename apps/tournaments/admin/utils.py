# apps/tournaments/admin/utils.py

def _path_exists(model, path: str) -> bool:
    """
    Verify a select_related path exists on 'model', supporting spans like 'profile__user'.
    Each segment must be a real field; for relation fields we walk to the related model.
    """
    parts = path.split("__")
    m = model
    for p in parts:
        try:
            f = m._meta.get_field(p)
        except Exception:
            return False
        # If it's a relation, walk to the related model; otherwise keep current model
        if hasattr(f, "related_model") and f.related_model:
            m = f.related_model
    return True


def _safe_select_related(qs, candidate_paths):
    """
    Apply select_related only for paths that exist on the queryset's model.
    Keeps admin list/export code resilient if models evolve.
    """
    model = qs.model
    valid = [p for p in candidate_paths if _path_exists(model, p)]
    return qs.select_related(*valid) if valid else qs


def _safe_message(modeladmin, request, msg, level=None):
    """
    Call ModelAdmin.message_user safely (works in tests or when middleware is absent).
    """
    try:
        modeladmin.message_user(request, msg, level=level)
    except Exception:
        pass
