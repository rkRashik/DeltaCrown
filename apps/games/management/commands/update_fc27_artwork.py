"""Refresh FC27 card/banner media using the checked-in publisher key art."""

from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.games.models import Game


class Command(BaseCommand):
    help = 'Preview FC27 card/banner refresh; --apply uploads the official bundled image.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        source = Path(settings.BASE_DIR) / 'static/img/games/fc27-key-art.jpg'
        if not source.is_file():
            raise CommandError('Bundled official FC27 key art is missing.')
        with transaction.atomic():
            game = Game.objects.select_for_update().get(slug='ea-fc')
            fields = [field for field in ['card_image', 'banner']
                      if 'fc27-20261018' not in (getattr(game, field).name or '')]
            self.stdout.write(f'FC27 media fields to refresh: {fields}')
            if not options['apply']:
                self.stdout.write('Preview only; use --apply to upload and save.')
                return
            for field in fields:
                getattr(game, field).save('fc27-20261018.jpg', ContentFile(source.read_bytes()), save=False)
            if fields:
                game.save(update_fields=[*fields, 'updated_at'])
        try:
            cache.delete_many(['context_active_games', 'homepage_context_v2', 'homepage_extras_v2', 'homepage_extras_v3'])
        except Exception as exc:
            self.stderr.write(f'Media saved; cache refresh failed: {exc}')
        self.stdout.write(self.style.SUCCESS('FC27 artwork is current.'))
