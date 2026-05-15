"""
Shared admin mixins for DeltaCrown.

SafeUploadMixin
===============
Wraps ``save_model`` so that storage-level failures (Cloudinary timeout,
network blip, rate limit …) are caught and surfaced as a friendly admin
error message instead of crashing with a bare 500.

Also installs a tolerant ImageField/FileField widget so the admin
change-form renders even when a referenced file is MISSING on disk
(e.g., dev environment running without ``CLOUDINARY_URL`` while the DB
still carries Cloudinary identifiers from a production export). Without
this guard, Django's ``ClearableFileInput`` calls ``getsize()`` on the
existing file to display the "Currently:" link and crashes with
``FileNotFoundError`` on Windows / posix.

Usage
-----
Combine with ``unfold.admin.ModelAdmin`` (or plain ``django ModelAdmin``)::

    from apps.common.admin_mixins import SafeUploadMixin

    class MyModelAdmin(SafeUploadMixin, ModelAdmin):
        ...
"""

import logging
import os

from django.contrib import messages
from django.db import models
from django.forms.widgets import ClearableFileInput

logger = logging.getLogger(__name__)


class _TolerantClearableFileInput(ClearableFileInput):
    """A ``ClearableFileInput`` that doesn't crash when the stored file is missing.

    Django's stock widget calls ``value.url`` and (indirectly) ``value.size``
    when rendering the "Currently:" link. If the file is gone from storage,
    ``getsize()`` raises ``FileNotFoundError``. We short-circuit by checking
    file existence first and rendering an inline "missing" hint instead.
    """

    def get_context(self, name, value, attrs):
        try:
            return super().get_context(name, value, attrs)
        except (FileNotFoundError, OSError) as exc:
            logger.warning(
                "TolerantClearableFileInput: missing file for field=%s value=%r err=%s",
                name, getattr(value, "name", value), exc,
            )
            # Re-render with the value treated as "no file" so the form
            # still renders. The admin can save a new file or clear the field.
            context = ClearableFileInput.get_context(self, name, None, attrs)
            # Surface the broken path inline so admin knows why the slot is empty.
            broken = ""
            try:
                broken = str(getattr(value, "name", "") or "")
            except Exception:
                broken = ""
            if broken:
                context["widget"]["hint"] = (
                    f"Stored file '{broken}' is missing on local storage. "
                    "Upload a new file to replace it."
                )
            return context


class SafeUploadMixin:
    """Catch storage/upload exceptions in admin save and show an error message.

    For *existing* objects (change) the exception is swallowed — the admin
    redirects back with the error banner and the old data remains intact.

    For *new* objects (add) we must re-raise because Django needs a saved PK
    to proceed with inline formsets.  The exception is still logged / shown.
    """

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Install the tolerant widget on every ImageField/FileField."""
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, (models.ImageField, models.FileField)) and formfield is not None:
            # Only swap if the existing widget is the stock ClearableFileInput
            # (don't clobber custom widgets a subclass may have installed).
            current_widget = formfield.widget
            if isinstance(current_widget, ClearableFileInput) and not isinstance(current_widget, _TolerantClearableFileInput):
                formfield.widget = _TolerantClearableFileInput(
                    attrs=getattr(current_widget, "attrs", {}),
                )
        return formfield

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
