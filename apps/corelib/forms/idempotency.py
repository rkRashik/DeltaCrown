# apps/corelib/forms/idempotency.py
from __future__ import annotations
from typing import Dict, Any
import secrets

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Relative import so IDEs and Python resolve it reliably within the package
from ..models.idempotency import IdempotencyKey


class IdempotentAutofillMixin(forms.Form):
    """
    - Adds a hidden idempotency token field to prevent duplicate POSTs.
    - Autofills initial values from request.user / request.user.profile on GET.

    Behavior:
      • On GET (unbound), generates a random token (NOT persisted).
      • On POST, if the token has NOT been seen recently, we persist it and accept.
      • On POST, if the token HAS been seen recently, we raise a duplicate-submission error.

    Backward-compatibility:
      • Field is stored as 'idem' internally.
      • Alias '__idem' is also provided so templates/tests using {{ form.__idem }} still work.
    """

    # Use a safe, non-mangled name for the actual field
    idem = forms.CharField(widget=forms.HiddenInput, required=False)

    # --- configuration ---
    IDEM_SCOPE = "form.generic"   # override in subclasses
    AUTOFILL_MAP: Dict[str, Any] = {}  # e.g. {"phone": "profile.phone"}

    # Helper: decide which field name we should use at runtime
    def _idem_field_name(self) -> str:
        # Prefer '__idem' if alias exists (so templates/tests keep passing)
        return "__idem" if "__idem" in self.fields else "idem"

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._request = request

        # Create an alias so both 'idem' and '__idem' work.
        if "__idem" not in self.fields and "idem" in self.fields:
            self.fields["__idem"] = self.fields["idem"]

        # Seed token only on initial (unbound) render or when no value provided.
        # IMPORTANT: do NOT persist here; persisting is done on first valid POST.
        field_name = self._idem_field_name()
        try:
            current_val = self[field_name].value()
        except Exception:
            current_val = None

        if not current_val:
            tok = secrets.token_urlsafe(24)
            self.fields["idem"].initial = tok
            if "__idem" in self.fields:
                self.fields["__idem"].initial = tok

        # Apply autofill only on non-bound forms (GET/initial render)
        if not self.is_bound:
            self._apply_autofill()

    # --- Autofill helpers ---
    def _apply_autofill(self):
        req = getattr(self, "_request", None)
        u = getattr(req, "user", None) if req else None
        if not (u and getattr(u, "is_authenticated", False)):
            return

        for field, source in (self.AUTOFILL_MAP or {}).items():
            if field not in self.fields:
                continue
            value = None
            try:
                if callable(source):
                    value = source(u)
                elif isinstance(source, str):
                    obj = u
                    for part in source.split("."):
                        obj = getattr(obj, part, None)
                        if obj is None:
                            break
                    value = obj() if callable(obj) else obj
            except Exception:
                value = None

            if value not in (None, ""):
                # Don't overwrite explicit initial values the view might have set
                self.initial.setdefault(field, value)

    # --- Idempotency validation ---
    def clean(self):
        data = super().clean()

        # Read token from whichever field name is active
        field_name = self._idem_field_name()
        token = data.get(field_name) or self.fields["idem"].initial

        user = getattr(getattr(self, "_request", None), "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            # If token not seen recently, record it now so this exact POST becomes “used”.
            # If already seen, raise a validation error (duplicate submit).
            if not token or not IdempotencyKey.is_recently_used(user, self.IDEM_SCOPE, token, window_minutes=10):
                if token:
                    IdempotencyKey.objects.get_or_create(user=user, scope=self.IDEM_SCOPE, token=token)
            else:
                raise ValidationError(_("Duplicate submission detected. Please do not resubmit the same form."))

        return data
