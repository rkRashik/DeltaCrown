"""Apply researched football catalog metadata without reseeding game behavior."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.cache import cache

from apps.games.management.commands.seed_games import Command as SeedCommand
from apps.games.models import Game
from apps.user_profile.models import GameChoiceConfig


class Command(BaseCommand):
    help = 'Preview football metadata updates; use --apply to save only these two games.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        fields = (
            'name', 'display_name', 'platforms', 'description',
            'developer', 'publisher', 'official_website', 'release_date',
        )
        seeds = SeedCommand().get_games_data()
        with transaction.atomic():
            games = {
                game.slug: game for game in Game.objects.select_for_update().filter(
                    slug__in=['ea-fc', 'efootball']
                )
            }
            if set(games) != {'ea-fc', 'efootball'}:
                raise CommandError('Both canonical football records must exist; nothing changed.')
            for slug, game in games.items():
                changes = {
                    field: {'before': getattr(game, field), 'after': seeds[slug][field]}
                    for field in fields if getattr(game, field) != seeds[slug][field]
                }
                self.stdout.write(f'{slug}: {json.dumps(changes, default=str)}')
                if options['apply'] and changes:
                    # Keep PK, slug, short_code, media, and competition/identity rules intact.
                    for field, change in changes.items():
                        setattr(game, field, change['after'])
                    game.save(update_fields=[*changes, 'updated_at'])

            config = GameChoiceConfig.objects.select_for_update().filter(
                game=games['ea-fc']
            ).first()
            if config:
                choices = list(config.platform_choices or [])
                for choice in seeds['ea-fc']['dropdown_choices']['platform_choices']:
                    index = next((i for i, item in enumerate(choices) if item['value'] == choice['value']), None)
                    if index is None:
                        choices.append(choice)
                    elif choice['value'] == 'PC':
                        choices[index] = {**choices[index], **choice}
                if choices != config.platform_choices:
                    self.stdout.write('ea-fc: update PC store label and add missing console platform choices')
                    if options['apply']:
                        config.platform_choices = choices
                        config.save(update_fields=['platform_choices'])
        self.stdout.write(self.style.SUCCESS('Applied.' if options['apply'] else 'Preview only; use --apply to save.'))
        if options['apply']:
            try:
                cache.delete_many(['context_active_games', 'homepage_context_v2', 'homepage_extras_v2', 'homepage_extras_v3'])
            except Exception as exc:
                self.stderr.write(f'Metadata saved; cache refresh failed: {exc}')
