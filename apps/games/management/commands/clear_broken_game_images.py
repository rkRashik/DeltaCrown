"""
Clear broken Game image references (icon/logo/banner/card_image).

Some legacy rows have file paths stored as Cloudinary-style identifiers
with a leading ``media/`` prefix and no extension (e.g.,
``media/games/icons/Valorant_icon_ztarm7``). When the local environment
falls back to ``FileSystemStorage`` (no ``CLOUDINARY_URL`` env var),
Django joins MEDIA_ROOT (``media/``) with that stored path and gets
``media/media/games/icons/...`` — a doubled-prefix path that doesn't
exist. The Django admin then crashes with ``FileNotFoundError`` when
rendering the change form because ``ClearableFileInput`` calls
``getsize()`` on the broken file.

This command identifies image fields on Game whose files cannot be
located locally and NULLs them so the admin can render. The user then
re-uploads via the Game change page (which now also includes the
GameMapPool image upload inline).

Safe to run repeatedly: only clears fields whose files don't exist.
Does NOT touch the underlying storage — if you're connected to a real
Cloudinary account, the assets in Cloudinary are unaffected; you can
re-link them by setting ``CLOUDINARY_URL`` instead of running this.

Usage::

    python manage.py clear_broken_game_images           # dry-run, lists only
    python manage.py clear_broken_game_images --apply   # actually NULL the fields
"""

import os

from django.core.management.base import BaseCommand

from apps.games.models.game import Game


IMAGE_FIELDS = ("icon", "logo", "banner", "card_image")


class Command(BaseCommand):
    help = "Clear Game image fields whose files cannot be located on local storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually NULL the broken fields. Without --apply this is a dry run.",
        )

    def handle(self, *args, **opts):
        apply_changes = bool(opts.get("apply"))
        clear_count = 0

        for game in Game.objects.all().order_by("slug"):
            broken_fields = []
            for field_name in IMAGE_FIELDS:
                field = getattr(game, field_name, None)
                if not field or not getattr(field, "name", ""):
                    continue
                try:
                    path = field.path  # may itself raise on unusual storage
                except Exception:
                    broken_fields.append(field_name)
                    continue
                if not os.path.exists(path):
                    broken_fields.append(field_name)

            if not broken_fields:
                continue

            self.stdout.write(self.style.WARNING(
                f"{game.slug} (id={game.id}): broken fields {broken_fields}"
            ))
            if apply_changes:
                update_fields = []
                for field_name in broken_fields:
                    setattr(game, field_name, None)
                    update_fields.append(field_name)
                game.save(update_fields=update_fields + ["updated_at"])
                clear_count += len(update_fields)
                self.stdout.write(self.style.SUCCESS(f"  -> cleared {len(update_fields)} field(s)"))

        if apply_changes:
            self.stdout.write(self.style.SUCCESS(
                f"\nDone. Cleared {clear_count} broken image reference(s)."
            ))
            self.stdout.write(
                "Re-upload images via the Game change page in the admin "
                "(now includes GameMapPool inline with image upload column)."
            )
        else:
            self.stdout.write(self.style.NOTICE(
                "\nDry run. Re-run with --apply to actually clear the fields."
            ))
