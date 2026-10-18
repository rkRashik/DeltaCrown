"""Update existing catalog metadata without reseeding competition settings."""

import json

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.games.catalog_metadata import CATALOG_METADATA
from apps.games.models import Game


class Command(BaseCommand):
    help = 'Preview publisher-verified catalog metadata (2026-10-18); --apply saves it.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        changed = 0
        with transaction.atomic():
            games = Game.objects.filter(slug__in=CATALOG_METADATA)
            if options['apply']:
                games = games.select_for_update()
            by_slug = {game.slug: game for game in games}
            missing = set(CATALOG_METADATA) - set(by_slug)
            if missing:
                raise CommandError(f'Missing catalog games: {sorted(missing)}. Nothing changed.')
            for slug, metadata in CATALOG_METADATA.items():
                game = by_slug[slug]
                changes = {
                    field: {'before': getattr(game, field), 'after': value}
                    for field, value in metadata.items() if getattr(game, field) != value
                }
                self.stdout.write(f'{slug}: {json.dumps(changes, default=str)}')
                if changes:
                    changed += 1
                if options['apply'] and changes:
                    for field, change in changes.items():
                        setattr(game, field, change['after'])
                    game.save(update_fields=[*changes, 'updated_at'])
        if options['apply']:
            try:
                cache.delete_many(['context_active_games', 'homepage_context_v2', 'homepage_extras_v2', 'homepage_extras_v3'])
            except Exception as exc:
                self.stderr.write(f'Metadata saved; cache refresh failed: {exc}')
        self.stdout.write(self.style.SUCCESS(
            f'{"Applied" if options["apply"] else "Preview only"}: {changed} game(s).'
        ))
