"""Management command: flush_cache
Completely clears the Django default cache (Redis on production,
LocMemCache in local dev). Run this from Render's Shell tab whenever
you need to resync the live site after a database restore or PITR swap.

Usage:
    python manage.py flush_cache
"""

import os

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Flush the entire Django default cache (Redis on production)."

    def handle(self, *args, **options):
        redis_url = os.getenv("REDIS_URL", "")
        backend = cache.__class__.__module__

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("  DeltaCrown — flush_cache"))
        self.stdout.write(f"  Backend : {backend}")
        self.stdout.write(f"  Redis   : {redis_url[:40] + '…' if len(redis_url) > 40 else redis_url or '(not set)'}")
        self.stdout.write(self.style.WARNING("=" * 60))

        try:
            cache.clear()
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(self.style.ERROR(f"  Cache flush FAILED: {exc}"))
            raise SystemExit(1) from exc

        self.stdout.write(self.style.SUCCESS("  ✓ Cache cleared successfully."))
        self.stdout.write("")
