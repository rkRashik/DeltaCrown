"""
Management command to mark games as passport-supported.

Usage:
    python manage.py mark_passport_supported
    python manage.py mark_passport_supported --game valorant --enable
    python manage.py mark_passport_supported --game unsupported_game --disable
    python manage.py mark_passport_supported --all
"""

from django.core.management.base import BaseCommand
from apps.games.models import Game


class Command(BaseCommand):
    help = "Mark games as passport-supported (or unsupported)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--game',
            type=str,
            help='Game slug to update'
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Enable passport support'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable passport support'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Mark all games with schemas as passport-supported'
        )

    def handle(self, *args, **options):
        if options['all']:
            self.mark_all_with_schemas()
        elif options['game']:
            self.mark_single_game(
                options['game'],
                enable=options['enable'],
                disable=options['disable']
            )
        else:
            self.stdout.write(self.style.WARNING("Please specify --game or --all"))

    def mark_all_with_schemas(self):
        """Mark all games that have passport schemas as supported"""
        from apps.user_profile.models import GamePassportSchema
        
        schemas = GamePassportSchema.objects.select_related('game').all()
        
        if not schemas.exists():
            self.stdout.write(self.style.WARNING("⚠️  No passport schemas found. Run seed_game_passport_schemas first."))
            return
        
        count = 0
        for schema in schemas:
            game = schema.game
            if not game.is_passport_supported:
                game.is_passport_supported = True
                game.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Enabled passport support for {game.display_name}"))
        
        if count == 0:
            self.stdout.write("All games with schemas are already marked as passport-supported.")
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"🎉 Marked {count} games as passport-supported"))
    
    def mark_single_game(self, game_slug, enable=False, disable=False):
        """Mark a single game as supported or unsupported"""
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Game '{game_slug}' not found"))
            return
        
        if enable and disable:
            self.stdout.write(self.style.ERROR("❌ Cannot use both --enable and --disable"))
            return
        
        if enable:
            game.is_passport_supported = True
            game.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Enabled passport support for {game.display_name}"))
        elif disable:
            game.is_passport_supported = False
            game.save()
            self.stdout.write(self.style.WARNING(f"⚠️  Disabled passport support for {game.display_name}"))
        else:
            status = "ENABLED" if game.is_passport_supported else "DISABLED"
            self.stdout.write(f"{game.display_name}: Passport support is {status}")
