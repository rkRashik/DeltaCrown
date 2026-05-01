# apps/economy/models/documentation.py
"""
Economy Playbook — Internal Admin Documentation Model.

Provides a lightweight, admin-editable knowledge base for platform financial
rules, treasury mechanics, and compliance limits.  Admins read and update
these entries directly inside the Django admin interface; they are never
exposed to end-users.

Usage examples:
  - "DC Minting Procedure"
  - "Prize Claim Disbursement SOP"
  - "Escrow Wager Limits (Manual vs API Games)"
  - "KYC Verification Checklist"
  - "Closed-Loop Economy Compliance Policy"
"""
from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class EconomyPlaybook(models.Model):
    """
    A single internal documentation article for the economy admin team.

    Content is stored as plain-text / Markdown so admins can use headings,
    bullet lists, and code blocks.  The admin interface renders it in a
    <textarea> that can be widened — no third-party Markdown renderer needed.

    Fields:
        title:      Human-readable article title (e.g. "Prize Claim SOP").
        slug:       URL-safe identifier, auto-generated from title.
        content:    Full Markdown/plain-text body of the article.
        updated_at: Auto-updated on every save — shows freshness at a glance.
    """

    title = models.CharField(
        max_length=255,
        unique=True,
        help_text='Short, descriptive title for this playbook entry'
    )
    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True,
        help_text='Auto-generated from title.  Used as a stable identifier.'
    )
    content = models.TextField(
        help_text=(
            'Full content in Markdown or plain text.  Use ## headings, '
            '- bullet lists, and ``` code blocks for structure.'
        )
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Automatically updated whenever the article is saved'
    )

    class Meta:
        ordering = ['title']
        verbose_name = 'Economy Playbook'
        verbose_name_plural = 'Economy Playbook'  # Intentional: reads as one collection

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """Auto-generate slug from title if not already set."""
        if not self.slug:
            base = slugify(self.title)
            unique = base
            counter = 1
            while EconomyPlaybook.objects.filter(slug=unique).exclude(pk=self.pk).exists():
                unique = f"{base}-{counter}"
                counter += 1
            self.slug = unique
        super().save(*args, **kwargs)
