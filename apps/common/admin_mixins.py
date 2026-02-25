"""
Shared admin mixins for DeltaCrown.

SafeUploadMixin
===============
Wraps ``save_model`` so that storage-level failures (Cloudinary timeout,
network blip, rate limit …) are caught and surfaced as a friendly admin
error message instead of crashing with a bare 500.

Usage
-----
Combine with ``unfold.admin.ModelAdmin`` (or plain ``django ModelAdmin``)::

    from apps.common.admin_mixins import SafeUploadMixin

    class MyModelAdmin(SafeUploadMixin, ModelAdmin):
        ...
"""

import logging

from django.contrib import messages

logger = logging.getLogger(__name__)


class SafeUploadMixin:
    """Catch storage/upload exceptions in admin save and show an error message.

    For *existing* objects (change) the exception is swallowed — the admin
    redirects back with the error banner and the old data remains intact.

    For *new* objects (add) we must re-raise because Django needs a saved PK
    to proceed with inline formsets.  The exception is still logged / shown.
    """

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as exc:
            logger.error(
                "%s.save_model failed for %s (pk=%s): %s",
                self.__class__.__name__,
                obj,
                obj.pk,
                exc,
                exc_info=True,
            )
            messages.error(
                request,
                f"Save failed — please try again. "
                f"({exc.__class__.__name__}: {exc})",
            )
            if not change:
                # New object — we have to re-raise or Django will crash
                # trying to save inlines against a non-existent PK.
                raise
            # Existing object — swallow, so the admin redirects cleanly
            # with the error message visible.  Old DB data is untouched.
